#!/usr/bin/env python3
"""
ELON Daily Synthesis Session
==============================
Replaces per-find mission-creation with a single EOD evaluation session.

Doctrine (SO_TECH_VANGUARD_ELEVATION_20260621):
  - One synthesis session runs across ALL new finds from today's waves.
  - Claude evaluates every find and decides: IMPLEMENT_NOW / ALREADY_COVERED / ESCALATE / WATCH
  - IMPLEMENT_NOW that needs multi-day work → mission board entry
  - ALREADY_COVERED → log entry only, no board noise
  - ESCALATE → Hale review (log + board entry)
  - WATCH → elon_watch_list.json with trigger condition
  - One session, one report, board shows outcomes not backlogs.

Entry point: run_elon_synthesis(wave_paths) -> dict | None
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────

SEARCH_DIR    = Path(__file__).parent
THUNDERBIRD   = Path("/home/john/Thunderbird")
MISSION_BOARD = THUNDERBIRD / "OpsCenter/mission_board.json"
ADOPT_LOG     = SEARCH_DIR / "elon_adopt_log.json"
WATCH_LIST    = SEARCH_DIR / "elon_watch_list.json"
ENV_FILE      = THUNDERBIRD / ".env"
LOG_DIR       = THUNDERBIRD / "logs"


# ── Env + credentials ─────────────────────────────────────────────────────────

def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _load_adopt_log() -> dict:
    if ADOPT_LOG.exists():
        try:
            return json.loads(ADOPT_LOG.read_text())
        except Exception:
            pass
    return {"promoted": {}}


def _save_adopt_log(log: dict) -> None:
    ADOPT_LOG.write_text(json.dumps(log, indent=2))


def _load_mission_board() -> dict:
    if MISSION_BOARD.exists():
        try:
            return json.loads(MISSION_BOARD.read_text())
        except Exception:
            pass
    return {"missions": []}


def _save_mission_board(mb: dict) -> None:
    MISSION_BOARD.write_text(json.dumps(mb, indent=2))


def _find_board_duplicate(missions: list, title: str):
    """Board-level one-and-done guard (MISSION-647): before appending a new
    mission, check the live board for an already-open mission with this title —
    the same guard mission_board_sync.cmd_add, the TCD Create Task path, and
    the weekly-report generator now use. This path already dedups by name via
    its own ``already_promoted`` log; this is the missing board-level backstop
    for when that log and the board diverge. Best-effort — an import/lookup
    failure never blocks promotion."""
    try:
        sys.path.insert(0, str(THUNDERBIRD / "OpsCenter"))
        import mission_board_sync as mbs
        return mbs._find_open_duplicate(missions, title)
    except Exception:
        return None


def _get_max_mission_id() -> int:
    if not MISSION_BOARD.exists():
        return 331
    try:
        mb = json.loads(MISSION_BOARD.read_text())
        ids = []
        for m in mb.get("missions", []):
            mid = m.get("id", "")
            if re.match(r"^MISSION-\d+$", mid):
                ids.append(int(mid.replace("MISSION-", "")))
        return max(ids) if ids else 331
    except Exception:
        return 331


def _load_watch_list() -> dict:
    if WATCH_LIST.exists():
        try:
            return json.loads(WATCH_LIST.read_text())
        except Exception:
            pass
    return {"watches": []}


def _save_watch_list(wl: dict) -> None:
    WATCH_LIST.write_text(json.dumps(wl, indent=2))


# ── Wave data collection ───────────────────────────────────────────────────────

def _collect_new_finds(wave_paths: list) -> list[dict]:
    """
    Pull all category results from today's wave files.
    Filters out items already in the adopt log (already evaluated).
    Returns list of {name, result, wave, score} dicts.
    """
    sys.path.insert(0, str(SEARCH_DIR))
    try:
        import inter_wave_analyst as analyst
    except ImportError as e:
        print(f"  [synthesis] inter_wave_analyst not found: {e}")
        return []

    adopt_log = _load_adopt_log()
    already_promoted = set(adopt_log.get("promoted", {}).keys())

    best_by_name: dict[str, dict] = {}

    for wp in wave_paths:
        wp = Path(wp)
        if not wp.exists():
            continue
        m = re.match(r"wave(\d+)", wp.name)
        wave_num = int(m.group(1)) if m else 0
        try:
            scored = analyst.analyze_wave(wp)
        except Exception as e:
            print(f"  [synthesis] Warning: could not score {wp.name}: {e}")
            continue

        for item in scored:
            name  = (item.get("name") or "").strip()
            score = item.get("score", 0.0)
            if not name or name in already_promoted:
                continue
            if name not in best_by_name or score > best_by_name[name]["score"]:
                best_by_name[name] = {
                    "name":   name,
                    "result": (item.get("result") or "")[:800],
                    "score":  score,
                    "wave":   wave_num,
                }

    return sorted(best_by_name.values(), key=lambda x: x["score"], reverse=True)


# ── Claude headless dispatch ───────────────────────────────────────────────────

def _build_synthesis_prompt(finds: list[dict], output_path: Path) -> str:
    """Build the evaluation prompt sent to the synthesis Claude session."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    finds_text = "\n\n".join(
        f"FIND #{i+1}: {f['name']}\n"
        f"Score: {f['score']:.0f}  Wave: {f['wave']}\n"
        f"Result: {f['result']}"
        for i, f in enumerate(finds)
    )

    return f"""You are ELON, A12 Innovation & Disruption officer for Dreams2Memories Travel (D2M), a luxury travel advisory.

DATE: {today}
TASK: Evaluate {len(finds)} tech/tool finds from today's intelligence waves. Decide the action for each.

## D2M's Current Stack (context for evaluation)
- Booking: TESS (host agency booking records), Centrav (air/hotel), Regent + Silversea + Viking portals
- AI: Claude Code (Sonnet/Haiku), OpenCode, headless claude -p dispatch
- Comms: Gmail (d2mconcierge + johnloucks3), Telegram (D2MC2C bot), SMS (Twilio)
- Infra: systemd timers, Python scripts, Qdrant (semantic memory), MCP servers
- Web: Playwright/Chrome debug port, Anansi (web search), Perplexity API
- Data: Google Drive, Google Sheets (commission tracking), JSON state files

## Decision Criteria (SO_TECH_VANGUARD_ELEVATION_20260621 — default is ADOPT)
- IMPLEMENT_NOW: Useful to D2M, no real cost, no client-PII risk. Even if "unproven" — try it.
- ALREADY_COVERED: D2M's stack already does this well. No action needed.
- ESCALATE: Costs real money, or routes through client-send path/PII. Goes to Hale for canary review.
- WATCH: Potentially useful but requires a specific trigger condition (release, price drop, maturity).

## Finds to Evaluate

{finds_text}

## Output Format

Write a JSON file to {output_path} with this exact structure:

{{
  "date": "{today}",
  "total_finds": {len(finds)},
  "decisions": [
    {{
      "name": "<find name>",
      "wave": <wave number>,
      "decision": "IMPLEMENT_NOW" | "ALREADY_COVERED" | "ESCALATE" | "WATCH",
      "rationale": "<1-2 sentences>",
      "implementation_notes": "<specific steps if IMPLEMENT_NOW, else null>",
      "trigger_condition": "<when to revisit if WATCH, else null>",
      "escalation_reason": "<why escalate if ESCALATE, else null>"
    }}
  ],
  "summary": {{
    "implement_now": <count>,
    "already_covered": <count>,
    "escalate": <count>,
    "watch": <count>
  }}
}}

WRITE your complete JSON output to {output_path}
Do not include any text outside the JSON file write. The file must be valid JSON.
"""


def dispatch_elon_synthesis(prompt: str, output_path: Path) -> bool:
    """Dispatch a headless Claude session using the approved thunderbird_headless_spawn wrapper.

    Upgraded from direct Popen to spawn wrapper per MISSION-437 / SO 24 APR 2026.
    Wrapper enforces: daemon verification, OAuth token injection, start_new_session=True.
    """
    sys.path.insert(0, str(THUNDERBIRD))
    try:
        from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
    except ImportError as e:
        print(f"  [synthesis] ERROR: Could not import headless spawn wrapper: {e}")
        return False

    print(f"  [synthesis] Dispatching Claude sonnet synthesis session (via headless_spawn)...")
    print(f"  [synthesis] Output: {output_path}")

    result = spawn_headless_claude(
        prompt=prompt,
        output_file=str(output_path),
        model="claude-sonnet-4-6",  # Sonnet: multi-find evaluation + implementation decisions
        task_name="elon-synthesis",
        background=False,
        timeout=600,
    )

    status = result.get("status", "")
    log_file = result.get("log_file", "")
    if log_file:
        print(f"  [synthesis] Log: {log_file}")

    if status in ("FATAL_PREREQ", "FATAL_CREDS"):
        print(f"  [synthesis] ERROR: Prereq/creds failure ({status}) — "
              f"{result.get('errors') or result.get('error')}")
        return False

    if status == "COMPLETED":
        return True

    # Non-fatal statuses (TIMEOUT, etc.) — check if output file was written anyway
    if status == "TIMEOUT":
        print(f"  [synthesis] WARNING: Timeout after 600s — checking for partial output")
    else:
        print(f"  [synthesis] WARNING: Unexpected status '{status}' — checking output file")

    return output_path.exists() and output_path.stat().st_size > 0


# ── Result processing ──────────────────────────────────────────────────────────

def _process_synthesis_output(output_path: Path, finds: list[dict]) -> Optional[dict]:
    """Parse Claude's output JSON and return structured result."""
    if not output_path.exists():
        print(f"  [synthesis] Output file not found: {output_path}")
        return None

    try:
        data = json.loads(output_path.read_text())
    except Exception as e:
        print(f"  [synthesis] Could not parse output JSON: {e}")
        return None

    decisions = data.get("decisions", [])
    if not decisions:
        print(f"  [synthesis] No decisions in output")
        return None

    return data


def _apply_decisions(synthesis: dict) -> dict:
    """
    Apply the synthesis decisions to mission board, adopt log, and watch list.
    Returns counts of outcomes.
    """
    decisions = synthesis.get("decisions", [])
    now_iso   = datetime.now(timezone.utc).isoformat()

    adopt_log         = _load_adopt_log()
    already_promoted  = adopt_log.get("promoted", {})
    mb                = _load_mission_board()
    missions          = mb.get("missions", [])
    next_id           = _get_max_mission_id() + 1
    watch_list        = _load_watch_list()
    watches           = watch_list.get("watches", [])

    counts = {
        "implement_now":    0,
        "already_covered":  0,
        "escalated":        0,
        "watch":            0,
        "mission_ids":      [],
        "escalate_items":   [],
        "watch_items":      [],
    }

    for dec in decisions:
        name      = dec.get("name", "").strip()
        decision  = dec.get("decision", "").upper()
        rationale = dec.get("rationale", "")
        wave      = dec.get("wave", 0)

        if not name:
            continue

        if decision == "IMPLEMENT_NOW":
            counts["implement_now"] += 1
            title = f"IMPLEMENT_NOW: {name}"
            dup = _find_board_duplicate(missions, title)
            if dup is not None:
                dup.setdefault("logs", []).append(
                    f"[{now_iso[:19]}] ELON synthesis duplicate blocked — "
                    f"\"{title}\" already tracked here"
                )
                dup["updated_at"] = now_iso
                mission_id = dup["id"]
            else:
                mission_id = f"MISSION-{next_id}"
                impl_notes = dec.get("implementation_notes") or ""
                description = (
                    f"ELON SYNTHESIS: IMPLEMENT_NOW (wave{wave}).\n"
                    f"Rationale: {rationale}\n\n"
                    f"Implementation: {impl_notes}\n\n"
                    f"Action: ELON 10-agent fleet trials and implements. Report to Hale."
                )
                mission_entry = {
                    "id":           mission_id,
                    "title":        title,
                    "status":       "active",
                    "priority":     "P1",
                    "assigned_to":  "ELON",
                    "description":  description,
                    "deliverables": [
                        "Trial against a real Thunderbird task",
                        "Implement or escalate with concrete reason",
                        "Report outcome to Hale → Commander brief",
                    ],
                    "dependencies":    [],
                    "suspense_date":   None,
                    "escalation_rule": "Risk>benefit → Hale. Financial commitment → Commander.",
                    "logs":            [],
                    "created_at":      now_iso,
                    "updated_at":      now_iso,
                }
                missions.append(mission_entry)
                next_id += 1
            counts["mission_ids"].append(mission_id)

            already_promoted[name] = {
                "mission_id":  mission_id,
                "wave":        wave,
                "promoted_at": now_iso,
                "tier":        "IMPLEMENT_NOW",
                "rationale":   rationale,
            }

        elif decision == "ALREADY_COVERED":
            counts["already_covered"] += 1
            already_promoted[name] = {
                "mission_id":  None,
                "wave":        wave,
                "promoted_at": now_iso,
                "tier":        "ALREADY_COVERED",
                "rationale":   rationale,
            }

        elif decision == "ESCALATE":
            counts["escalated"] += 1
            escalation_reason = dec.get("escalation_reason") or rationale
            title = f"ELON ESCALATE: {name}"
            dup = _find_board_duplicate(missions, title)
            if dup is not None:
                dup.setdefault("logs", []).append(
                    f"[{now_iso[:19]}] ELON synthesis duplicate blocked — "
                    f"\"{title}\" already tracked here"
                )
                dup["updated_at"] = now_iso
                mission_id = dup["id"]
            else:
                mission_id = f"MISSION-{next_id}"
                description = (
                    f"ELON SYNTHESIS ESCALATION — wave{wave}.\n"
                    f"Reason: {escalation_reason}\n\n"
                    f"Action: Hale reviews. Client-path 7-day canary applies if touching send path."
                )
                mission_entry = {
                    "id":           mission_id,
                    "title":        title,
                    "status":       "active",
                    "priority":     "P1",
                    "assigned_to":  "HALE",
                    "description":  description,
                    "deliverables": [
                        "Hale reviews escalation reason",
                        "7-day canary if client-path tool",
                        "Commander notified if financial commitment required",
                    ],
                    "dependencies":    [],
                    "suspense_date":   None,
                    "escalation_rule": "Financial commitment → Commander.",
                    "logs":            [],
                    "created_at":      now_iso,
                    "updated_at":      now_iso,
                }
                missions.append(mission_entry)
                next_id += 1
            counts["escalate_items"].append({"name": name, "reason": escalation_reason, "mission_id": mission_id})

            already_promoted[name] = {
                "mission_id":  mission_id,
                "wave":        wave,
                "promoted_at": now_iso,
                "tier":        "ESCALATE",
                "rationale":   escalation_reason,
            }

        elif decision == "WATCH":
            counts["watch"] += 1
            trigger = dec.get("trigger_condition") or "Monitor for maturity/pricing changes"
            watches.append({
                "name":              name,
                "wave":              wave,
                "added_at":          now_iso,
                "trigger_condition": trigger,
                "rationale":         rationale,
            })
            counts["watch_items"].append({"name": name, "trigger": trigger})

            already_promoted[name] = {
                "mission_id":  None,
                "wave":        wave,
                "promoted_at": now_iso,
                "tier":        "WATCH",
                "rationale":   rationale,
            }

    # Persist all changes
    mb["missions"] = missions
    _save_mission_board(mb)

    adopt_log["promoted"] = already_promoted
    _save_adopt_log(adopt_log)

    watch_list["watches"] = watches
    _save_watch_list(watch_list)

    return counts


# ── Telegram helpers ──────────────────────────────────────────────────────────

def _tg_send(token: str, chat_id: str, text: str) -> bool:
    import urllib.request
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return bool(json.loads(resp.read()).get("ok"))
    except Exception as e:
        print(f"  [synthesis/telegram] send error: {e}")
        return False


def _chunk_text(text: str, limit: int = 4000) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = (current + "\n" + line).lstrip("\n") if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


# ── Telegram summary ───────────────────────────────────────────────────────────

def _send_synthesis_summary(synthesis: dict, counts: dict) -> bool:
    """
    Send EOD synthesis summary via Telegram.

    Routing (SO-TELEGRAM-ROUTING-20260622):
      - Full status report → relay channel (-5248121475)
      - Financial escalations needing Commander decision → also ping Commander (7554895206)
    """
    sys.path.insert(0, str(THUNDERBIRD / "core" / "comms"))
    try:
        from tg_router import COMMANDER_CHAT_ID, RELAY_CHAT_ID
    except ImportError:
        COMMANDER_CHAT_ID = "7554895206"
        RELAY_CHAT_ID     = "-5248121475"

    env   = _load_env()
    token = (
        env.get("TELEGRAM_D2MC2C_TOKEN")
        or env.get("TELEGRAM_BOT_TOKEN")
        or os.environ.get("TELEGRAM_D2MC2C_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )

    if not token:
        print("  [synthesis/telegram] No token found — skipping send")
        return False

    today     = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    implement = counts.get("implement_now", 0)
    covered   = counts.get("already_covered", 0)
    escalated = counts.get("escalated", 0)
    watch     = counts.get("watch", 0)
    total     = implement + covered + escalated + watch

    # ── Full status → relay ───────────────────────────────────────────────────
    lines = [
        f"⚡ ELON DAILY SYNTHESIS — {today}",
        "",
        f"{total} finds evaluated | {implement} implement | {covered} covered | {escalated} escalate | {watch} watch",
        "",
    ]

    if counts.get("mission_ids"):
        lines.append("── IMPLEMENT_NOW (mission board) ──")
        decisions = {d["name"]: d for d in synthesis.get("decisions", [])}
        for mid in counts["mission_ids"]:
            for name, dec in decisions.items():
                if dec.get("decision") == "IMPLEMENT_NOW":
                    lines.append(f"  {mid}: {name}")
                    break
        lines.append("")

    if counts.get("escalate_items"):
        lines.append("── ESCALATED TO HALE ──")
        for item in counts["escalate_items"]:
            lines.append(f"  {item['mission_id']}: {item['name']}")
            lines.append(f"    Reason: {item['reason'][:120]}")
        lines.append("")

    if counts.get("watch_items"):
        lines.append("── WATCH LIST ──")
        for item in counts["watch_items"]:
            lines.append(f"  {item['name']}: {item['trigger'][:100]}")
        lines.append("")

    lines.append("Board shows outcomes, not backlogs. One session, done.")

    ok = True
    for chunk in _chunk_text("\n".join(lines)):
        if not _tg_send(token, RELAY_CHAT_ID, chunk):
            ok = False

    if ok:
        print(f"  [synthesis/telegram] Relay: status sent")
    else:
        print(f"  [synthesis/telegram] One or more relay sends failed")

    # ── Escalation alert → Commander (financial commits requiring his decision) ─
    escalate_items = counts.get("escalate_items", [])
    if escalate_items:
        financial_esc = [
            i for i in escalate_items
            if "financial" in i.get("reason", "").lower()
            or "cost" in i.get("reason", "").lower()
        ]
        if financial_esc:
            esc_lines = [
                f"⚡ ELON SYNTHESIS — Commander action required",
                f"{len(financial_esc)} escalation(s) need financial decision:",
            ]
            for item in financial_esc:
                esc_lines.append(f"  • {item['name']} ({item['mission_id']})")
                esc_lines.append(f"    {item['reason'][:120]}")
            esc_lines.append("Hale has the full report. Your call on financial commitment.")
            if not _tg_send(token, COMMANDER_CHAT_ID, "\n".join(esc_lines)):
                ok = False
            else:
                print(f"  [synthesis/telegram] Commander: escalation alert sent ({len(financial_esc)} items)")

    return ok


# ── Main entry point ───────────────────────────────────────────────────────────

def run_elon_synthesis(wave_paths: list) -> Optional[dict]:
    """
    Main entry point for the daily ELON synthesis session.

    Args:
        wave_paths: list of Path objects for today's wave files

    Returns:
        Dict with implement_now, already_covered, escalated, watch counts.
        Returns None on hard failure (no finds, dispatch failure, parse failure).
    """
    today     = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path  = SEARCH_DIR / f"elon_synthesis_{today}.json"

    print(f"\n  ── ELON Daily Synthesis ──")

    # Collect new finds not yet in adopt log
    finds = _collect_new_finds(wave_paths)

    if not finds:
        print(f"  [synthesis] No new finds to evaluate — skipping session")
        return {"implement_now": 0, "already_covered": 0, "escalated": 0, "watch": 0}

    print(f"  [synthesis] {len(finds)} new finds to evaluate")

    # Build prompt and dispatch
    prompt = _build_synthesis_prompt(finds, out_path)
    success = dispatch_elon_synthesis(prompt, out_path)

    if not success:
        print(f"  [synthesis] Dispatch failed — falling back to adopt pipeline")
        return None

    # Give Claude a moment to flush the file write
    time.sleep(2)

    # Parse output
    synthesis = _process_synthesis_output(out_path, finds)
    if not synthesis:
        print(f"  [synthesis] Could not parse synthesis output — falling back")
        return None

    # Apply decisions to board, log, watch list
    counts = _apply_decisions(synthesis)

    print(f"  [synthesis] Complete: {counts['implement_now']} implement | "
          f"{counts['already_covered']} covered | "
          f"{counts['escalated']} escalated | "
          f"{counts['watch']} watch")

    # Send Telegram summary
    _send_synthesis_summary(synthesis, counts)

    return counts


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ELON Daily Synthesis — evaluate all wave finds in one session")
    parser.add_argument("--waves", nargs="*", help="Specific wave files (default: today's waves)")
    parser.add_argument("--dry-run", action="store_true", help="Show finds and prompt but do not dispatch")
    args = parser.parse_args()

    if args.waves:
        wave_paths = [Path(p) for p in args.waves]
    else:
        wave_paths = sorted(SEARCH_DIR.glob("wave*.json"))

    print(f"Wave files: {len(wave_paths)}")

    if args.dry_run:
        finds = _collect_new_finds(wave_paths)
        print(f"New finds: {len(finds)}")
        for f in finds:
            print(f"  [{f['score']:.0f}] {f['name']} (wave{f['wave']})")
        today    = datetime.now(timezone.utc).strftime("%Y%m%d")
        out_path = SEARCH_DIR / f"elon_synthesis_{today}.json"
        prompt   = _build_synthesis_prompt(finds, out_path)
        print(f"\n── Prompt (first 1000 chars) ──")
        print(prompt[:1000])
    else:
        result = run_elon_synthesis(wave_paths)
        if result:
            print(f"\nResult: {result}")
        else:
            print("\nSynthesis failed or no new finds.")
