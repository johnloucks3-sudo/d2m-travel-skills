#!/usr/bin/env python3
"""
ELON INTEGRATE_NOW Adopt Pipeline
==================================
Doctrine (SO_TECH_VANGUARD_ELEVATION_20260621 §2b — THREE CASES ONLY):
  - A find is INTEGRATE_NOW unless EXACTLY ONE of three things is true:
      1. Costs real money → Commander financial gate
      2. Touches client-send path or client PII → 7-day internal canary (adopts immediately on internal traffic)
      3. Sterling shows concrete, proven harm (security exposure or breakage — NOT worry/complexity/"unverified")
  - "Unverified," "fit unproven," "measure first," "needs a wrapper," "already covered" are NOT demotion reasons.
  - "Already covered" = INTEGRATE_NOW Case 1 (adopt + audit old within 7 days). Never a skip.
  - Every find reported — adopted or declined. No silent rejections.
  - Replacement policy: Case 1 (direct swap) decommission old. Case 2/3 integrate + audit old within 7 days.
  - Escalation: ELON → Hale → Commander
  - CI: 14-day data window before any decommission recommendation.

Entry point: run_adopt_pipeline(wave_paths, dry_run=False) -> dict
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Paths ────────────────────────────────────────────────────────────────────

SEARCH_DIR    = Path(__file__).parent
MISSION_BOARD = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
ADOPT_LOG     = SEARCH_DIR / "elon_adopt_log.json"
THUNDERBIRD   = Path("/home/john/Thunderbird")
ENV_FILE      = THUNDERBIRD / ".env"

# ── Hard prohibit keywords (exact match on category name / result text) ───────

# Keywords checked against the RESULT TEXT only (not category name).
# Category names are descriptive labels — "pricing" in a name means the research
# covers pricing comparison, not that the tool costs money. Only fire on explicit
# cost/PII-handling language in the actual result content.
MONEY_KEYWORDS_IN_RESULT = [
    "requires payment", "no free tier", "costs $", "per seat charge",
    "enterprise only", "paid license required", "monthly fee required",
    "annual subscription required", "must purchase",
]

PII_SEND_KEYWORDS_IN_RESULT = [
    "sends client email", "client send path", "routes client pii",
    "uploads passenger data", "transmits booking records",
    "credit card number", "passenger data to third party",
]

# Keywords checked against CATEGORY NAME — must be unambiguous financial commitment
# language in the name itself (not descriptive/research category names).
MONEY_KEYWORDS_IN_NAME = [
    "paid only", "no free tier", "enterprise license",
]


def _load_env() -> dict:
    """Load key=value pairs from .env file."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _hits_hard_prohibit(item: dict) -> Optional[str]:
    """
    Returns a reason string if the item hits a hard prohibit, else None.
    Hard prohibits: real money cost, or client-send/PII path.

    Name vs result checked separately — category names are descriptive labels.
    'pricing' in a name = research about pricing comparison, not a cost.
    'pii' in a name = security/governance category, not client PII exposure.
    """
    name_lc   = (item.get("name") or "").lower()
    result_lc = (item.get("result") or "").lower()

    for kw in MONEY_KEYWORDS_IN_NAME:
        if kw in name_lc:
            return f"financial: '{kw}' in category name — escalate to Commander"

    for kw in MONEY_KEYWORDS_IN_RESULT:
        if kw in result_lc:
            return f"financial: '{kw}' in result — escalate to Commander"

    for kw in PII_SEND_KEYWORDS_IN_RESULT:
        if kw in result_lc:
            return f"client-send/PII: '{kw}' in result — escalate to Hale (7-day canary)"

    return None


def _load_adopt_log() -> dict:
    """Load the adopt log, returning empty structure if not found."""
    if ADOPT_LOG.exists():
        try:
            return json.loads(ADOPT_LOG.read_text())
        except Exception:
            pass
    return {"promoted": {}}


def _save_adopt_log(log: dict) -> None:
    ADOPT_LOG.write_text(json.dumps(log, indent=2))


def _get_max_mission_id() -> int:
    """Get the highest numeric MISSION-NNN id from mission_board.json."""
    if not MISSION_BOARD.exists():
        return 331  # fallback baseline
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


def _load_mission_board() -> dict:
    if MISSION_BOARD.exists():
        try:
            return json.loads(MISSION_BOARD.read_text())
        except Exception:
            pass
    return {"missions": []}


def _save_mission_board(mb: dict) -> None:
    MISSION_BOARD.write_text(json.dumps(mb, indent=2))


def _extract_wave_number(wave_path: Path) -> int:
    """Extract wave number from filename like wave10_2026-06-21_2307.json"""
    m = re.match(r"wave(\d+)", wave_path.name)
    return int(m.group(1)) if m else 0


# ── Core pipeline ─────────────────────────────────────────────────────────────

def run_adopt_pipeline(wave_paths: list, dry_run: bool = False) -> dict:
    """
    Main entry point.

    Args:
        wave_paths: list of Path objects pointing to wave*.json files
        dry_run:    if True, compute results but do NOT write mission board or log

    Returns:
        {
          "adopted": [{"name", "score", "mission_id", "preview", "wave"}],
          "declined": [{"name", "score", "reason", "wave"}],
          "skipped_already_promoted": int,
        }
    """
    # Lazy import — must be importable when called from same dir
    sys.path.insert(0, str(SEARCH_DIR))
    try:
        import inter_wave_analyst as analyst
    except ImportError as e:
        raise RuntimeError(f"inter_wave_analyst not found in {SEARCH_DIR}: {e}")

    adopt_log = _load_adopt_log()
    already_promoted = adopt_log.get("promoted", {})

    # ── Step 1: Score ALL items across all wave_paths ────────────────────────
    best_by_name: dict[str, dict] = {}  # dedup by category name, keep highest score

    for wp in wave_paths:
        wp = Path(wp)
        if not wp.exists():
            continue
        wave_num = _extract_wave_number(wp)
        try:
            scored = analyst.analyze_wave(wp)
        except Exception as e:
            print(f"  [adopt] Warning: could not score {wp.name}: {e}")
            continue

        for item in scored:
            name  = item.get("name", "").strip()
            score = item.get("score", 0.0)
            if not name:
                continue
            if name not in best_by_name or score > best_by_name[name]["score"]:
                best_by_name[name] = {
                    "name":           name,
                    "score":          score,
                    "wave":           wave_num,
                    "id":             item.get("id"),
                    "result":         item.get("result") or "",
                    "result_preview": item.get("result_preview") or (item.get("result") or "")[:400],
                }

    # ── Step 2: Classify every find ──────────────────────────────────────────
    adopted  = []
    declined = []
    skipped  = 0

    now_iso = datetime.now(timezone.utc).isoformat()

    # Pre-load mission board once; we'll append and save at end
    mb       = _load_mission_board()
    missions = mb.get("missions", [])
    next_id  = _get_max_mission_id() + 1

    for item in sorted(best_by_name.values(), key=lambda x: x["score"], reverse=True):
        name  = item["name"]
        score = item["score"]
        wave  = item["wave"]

        # Already promoted? Skip
        if name in already_promoted:
            skipped += 1
            continue

        # Hard prohibit check
        prohibit_reason = _hits_hard_prohibit(item)
        if prohibit_reason:
            declined.append({
                "name":   name,
                "score":  score,
                "wave":   wave,
                "reason": prohibit_reason,
            })
            continue

        # ── INTEGRATE_NOW ────────────────────────────────────────────────────
        mission_id    = f"MISSION-{next_id}"
        preview_text  = (item.get("result_preview") or item.get("result") or "")[:400]
        description   = (
            f"INTEGRATE_NOW — wave{wave} signal (score={score:.0f}). "
            f"{preview_text}\n\n"
            f"Action: ELON 10-agent fleet evaluates, trials, and implements. Report to Hale."
        )

        mission_entry = {
            "id":           mission_id,
            "title":        f"INTEGRATE_NOW: {name}",
            "status":       "active",
            "priority":     "P1",
            "assigned_to":  "ELON",
            "description":  description,
            "deliverables": [
                "Evaluate the tool/API/pattern",
                "Trial it against a real Thunderbird task",
                "Implement or escalate with concrete reason (not 'unverified')",
                "Report outcome to Hale → Commander brief",
            ],
            "dependencies":    [],
            "suspense_date":   None,
            "escalation_rule": "Risk>benefit → Hale. Financial commitment → Commander.",
            "logs":            [],
            "created_at":      now_iso,
            "updated_at":      now_iso,
        }

        if not dry_run:
            missions.append(mission_entry)

        adopted.append({
            "name":       name,
            "score":      score,
            "wave":       wave,
            "mission_id": mission_id,
            "preview":    preview_text[:200],
        })

        # Update adopt log
        already_promoted[name] = {
            "mission_id":  mission_id,
            "score":       score,
            "wave":        wave,
            "promoted_at": now_iso,
            "tier":        "ADOPT",
        }

        next_id += 1

    # ── Step 3: Persist ──────────────────────────────────────────────────────
    if not dry_run:
        mb["missions"] = missions
        _save_mission_board(mb)

        adopt_log["promoted"] = already_promoted
        _save_adopt_log(adopt_log)

    return {
        "adopted":                  adopted,
        "declined":                 declined,
        "skipped_already_promoted": skipped,
    }


# ── Telegram formatting ───────────────────────────────────────────────────────

def build_telegram_message(results: dict) -> str:
    """
    Build Telegram HTML message summarizing pipeline results.
    """
    adopted  = results.get("adopted", [])
    declined = results.get("declined", [])
    skipped  = results.get("skipped_already_promoted", 0)

    lines = [
        "⚡ <b>ELON INTEGRATE_NOW PIPELINE — RESULTS</b>",
        "",
        f"<b>{len(adopted)} finds → mission board</b>  |  "
        f"{len(declined)} escalated  |  {skipped} already promoted",
        "",
    ]

    if adopted:
        lines.append("━━ INTEGRATE_NOW ━━")
        for item in adopted:
            score  = item["score"]
            name   = item["name"]
            mid    = item["mission_id"]
            wave   = item["wave"]
            lines.append(f"  [{score:.0f}] <b>{name}</b> → {mid} (wave{wave})")
        lines.append("")

    if declined:
        lines.append("━━ ESCALATED (hard prohibit) ━━")
        for item in declined:
            lines.append(f"  ⚠️ {item['name']} — {item['reason']}")
        lines.append("")

    lines += [
        "<i>Doctrine: All finds are INTEGRATE_NOW. Declines escalate to Hale.</i>",
        "<i>Escalation chain: ELON → Hale → Commander.</i>",
    ]

    return "\n".join(lines)


# ── Telegram send ─────────────────────────────────────────────────────────────

def _tg_send(token: str, chat_id: str, text: str, parse_mode: str = "") -> bool:
    """Send a single Telegram message. Returns True on success."""
    import urllib.request

    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload_dict: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload_dict["parse_mode"] = parse_mode
    payload = json.dumps(payload_dict).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            return bool(body.get("ok"))
    except Exception as e:
        print(f"  [adopt/telegram] send error: {e}")
        return False


def send_adopt_page(results: dict) -> bool:
    """
    Send pipeline results via Telegram.

    Routing (SO-TELEGRAM-ROUTING-20260622):
      - Full adopt count report → relay channel (-5248121475)
      - If hard-prohibit escalations exist → also send a short alert to Commander (7554895206)
    """
    sys.path.insert(0, str(THUNDERBIRD / "core" / "comms"))
    try:
        from tg_router import COMMANDER_CHAT_ID, RELAY_CHAT_ID
    except ImportError:
        COMMANDER_CHAT_ID = "7554895206"
        RELAY_CHAT_ID     = "-5248121475"

    env = _load_env()

    token = (
        env.get("TELEGRAM_D2MC2C_TOKEN")
        or env.get("TELEGRAM_BOT_TOKEN")
        or os.environ.get("TELEGRAM_D2MC2C_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )

    if not token:
        print("  [adopt/telegram] No token found — skipping send")
        return False

    adopted  = results.get("adopted", [])
    declined = results.get("declined", [])
    skipped  = results.get("skipped_already_promoted", 0)

    # ── Full report → relay ───────────────────────────────────────────────────
    lines = [
        "⚡ ELON INTEGRATE_NOW PIPELINE — RESULTS",
        "",
        f"{len(adopted)} finds → mission board  |  {len(declined)} escalated  |  {skipped} already promoted",
        "",
    ]
    if adopted:
        lines.append("━━ INTEGRATE_NOW ━━")
        for item in adopted:
            lines.append(f"  [{item['score']:.0f}] {item['name']} → {item['mission_id']} (wave{item['wave']})")
        lines.append("")
    if declined:
        lines.append("━━ ESCALATED (hard prohibit) ━━")
        for item in declined:
            lines.append(f"  ⚠ {item['name']} — {item['reason']}")
        lines.append("")
    lines += [
        "Doctrine: All finds are INTEGRATE_NOW. Declines escalate to Hale.",
        "Escalation chain: ELON → Hale → Commander.",
    ]

    full_text = "\n".join(lines)

    LIMIT = 4000
    chunks: list[str] = []
    current = ""
    for line in full_text.split("\n"):
        candidate = (current + "\n" + line).lstrip("\n") if current else line
        if len(candidate) > LIMIT:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    ok = True
    for chunk in chunks:
        if not _tg_send(token, RELAY_CHAT_ID, chunk):
            ok = False

    if ok:
        print(f"  [adopt/telegram] Relay: {len(chunks)} message(s) — {len(adopted)} missions")
    else:
        print("  [adopt/telegram] One or more relay sends failed")

    # ── Escalation alert → Commander (only when hard prohibits need decision) ──
    if declined:
        financial = [d for d in declined if d["reason"].startswith("financial")]
        if financial:
            esc_lines = ["⚡ ELON — Commander action required"]
            esc_lines.append(f"{len(financial)} adopt candidate(s) hit financial prohibit:")
            for item in financial:
                esc_lines.append(f"  • {item['name']}: {item['reason']}")
            esc_lines.append("Review adopt log. Escalation chain: ELON → Hale → Commander.")
            if not _tg_send(token, COMMANDER_CHAT_ID, "\n".join(esc_lines)):
                ok = False
            else:
                print(f"  [adopt/telegram] Commander: escalation alert sent ({len(financial)} items)")

    return ok


# ── CLI self-test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ELON INTEGRATE_NOW adopt pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Score only, do not write")
    parser.add_argument("--send", action="store_true", help="Send Telegram page after run")
    args = parser.parse_args()

    wave_paths = sorted(Path(__file__).parent.glob("wave*.json"))
    print(f"Processing {len(wave_paths)} wave files...")

    results = run_adopt_pipeline(wave_paths, dry_run=args.dry_run)

    print(f"\nAdopted:  {len(results['adopted'])}")
    print(f"Declined: {len(results['declined'])}")
    print(f"Skipped:  {results['skipped_already_promoted']}")

    for item in results["adopted"]:
        print(f"  [{item['score']:.0f}] {item['name']} → {item['mission_id']} (wave{item['wave']})")

    if results["declined"]:
        print("\nDeclined (hard prohibit):")
        for item in results["declined"]:
            print(f"  ⚠️  {item['name']}: {item['reason']}")

    msg = build_telegram_message(results)
    print("\n── Telegram message ──")
    print(msg)

    if args.send:
        ok = send_adopt_page(results)
        print(f"\nTelegram sent: {ok}")
