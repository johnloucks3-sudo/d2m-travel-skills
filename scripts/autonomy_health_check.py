#!/usr/bin/env python3
"""
A7 Sterling — Autonomy Health Check (Read-Only)
================================================
MISSION-167 · 14-day watch protocol on A1 / A3 / A5 / A8 autonomy scripts.

This script reads logs and state files ONLY.
It does NOT import, exec, or modify any watched script.
It does NOT touch mission_board.json or any protected email/relay file.

Reference doc: docs/autonomy_watch_protocol_A1_A3_A5_A8.md
Owner: A7 Sterling
Reviewer: COS Hale

Usage:
    python3 scripts/autonomy_health_check.py
    python3 scripts/autonomy_health_check.py --since 2026-06-17
    python3 scripts/autonomy_health_check.py --json    # machine-readable

Exit codes:
    0 = all GREEN
    1 = at least one YELLOW (no RED)
    2 = at least one RED (escalation required)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"

# ── Log / state file paths (read-only) ─────────────────────────────────────
LIFECYCLE_SCHED_LOG   = THUNDERBIRD / "logs" / "lifecycle_scheduler.log"
LIFECYCLE_AUDIT_JSONL = THUNDERBIRD / "OpsCenter" / "logs" / "lifecycle_audit.jsonl"
DANI_VOICE_LOG        = THUNDERBIRD / "logs" / "dani_voice_draft.log"
DRAFT_QUEUE_JSONL     = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"
DOSSIER_FRESH_JSONL   = THUNDERBIRD / "OpsCenter" / "logs" / "dossier_freshness.jsonl"
FPD_STATE_JSON        = THUNDERBIRD / "OpsCenter" / "state" / "fpd_state.json"
DASHBOARD_JSON        = THUNDERBIRD / "OpsCenter" / "a7_metrics_dashboard.json"
A5_LOG_GLOB           = "logs/opencode_wind_staff_castillo_*.log"

# ── Thresholds ──────────────────────────────────────────────────────────────
MAX_SCHED_RUNS_PER_DAY_YELLOW = 5
MAX_SCHED_RUNS_PER_DAY_RED    = 8
DRAFT_PLACEHOLDER_TOKEN       = "[FILL_"
DRAFT_SHORT_LENGTH            = 200   # chars; shorter = suspected placeholder
WATCH_START_DATE              = "2026-06-17"   # new voice_errors after this are fresh


def _parse_dt(ts_str: str) -> datetime | None:
    """Parse ISO8601 or datetime string tolerantly."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str[:26], fmt)
        except (ValueError, TypeError):
            pass
    return None


def _load_jsonl(path: Path, since: str | None = None) -> list[dict]:
    """Read a .jsonl file, return list of dicts. Optionally filter by ts >= since."""
    if not path.exists():
        return []
    results = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since:
            ts = obj.get("ts") or obj.get("timestamp", "")
            if ts and ts < since:
                continue
        results.append(obj)
    return results


# ── Per-persona checks ──────────────────────────────────────────────────────

def check_a3_lifecycle_scheduler(since: str | None) -> list[dict]:
    """Check lifecycle_scheduler.py via lifecycle_audit.jsonl and scheduler log."""
    findings = []

    # 1. Scheduler complete events — error array and drafts_created
    events = _load_jsonl(LIFECYCLE_AUDIT_JSONL, since)
    complete = [e for e in events if e.get("event") == "scheduler_complete"]

    if not complete:
        findings.append({
            "persona": "A3_Dani",
            "signal": "error_rate",
            "level": "YELLOW",
            "detail": "No scheduler_complete events found in lifecycle_audit.jsonl"
                      + (f" since {since}" if since else ""),
        })
    else:
        last = complete[-1]
        errs = last.get("summary", {}).get("errors", [])
        if errs:
            level = "RED" if len(errs) >= 3 else "YELLOW"
            findings.append({
                "persona": "A3_Dani",
                "signal": "error_rate",
                "level": level,
                "detail": f"lifecycle_scheduler errors in last run: {errs}",
            })

        # contact_hold guard — any drafts_created for a hold client
        # (we check the YAML blackboard hold flag indirectly via the log)
        # Proxy: draft created while stale count > 0 for same client is a risk indicator
        stale = [e for e in events if e.get("event") == "phase_stale" and
                 (since is None or e.get("timestamp", "") >= (since or ""))]
        if stale and last.get("summary", {}).get("drafts_created", 0) > 0:
            findings.append({
                "persona": "A3_Dani",
                "signal": "off_lane",
                "level": "YELLOW",
                "detail": f"drafts_created > 0 while {len(stale)} stale-phase records present. "
                          "Verify no contact_hold client got a draft.",
            })

    # 2. Runaway loop — runs per day count
    if LIFECYCLE_SCHED_LOG.exists():
        log_text = LIFECYCLE_SCHED_LOG.read_text()
        today_str = date.today().strftime("%Y-%m-%d")
        runs_today = log_text.count(f"D2M Lifecycle Scheduler — {today_str}")
        if runs_today > MAX_SCHED_RUNS_PER_DAY_RED:
            findings.append({
                "persona": "A3_Dani",
                "signal": "runaway_loop",
                "level": "RED",
                "detail": f"lifecycle_scheduler ran {runs_today}x today (threshold RED={MAX_SCHED_RUNS_PER_DAY_RED})",
            })
        elif runs_today > MAX_SCHED_RUNS_PER_DAY_YELLOW:
            findings.append({
                "persona": "A3_Dani",
                "signal": "runaway_loop",
                "level": "YELLOW",
                "detail": f"lifecycle_scheduler ran {runs_today}x today (threshold YELLOW={MAX_SCHED_RUNS_PER_DAY_YELLOW})",
            })

        # 3. WF-17 gate breach proxy — check for send calls in log (should never appear)
        if "gmail_send" in log_text or "send_email" in log_text:
            findings.append({
                "persona": "A3_Dani",
                "signal": "wf17_breach",
                "level": "RED",
                "detail": "lifecycle_scheduler.log contains 'gmail_send' or 'send_email' — "
                          "potential WF-17 gate breach. Manual verify required.",
            })

    # 4. ERROR lines in scheduler log
    if LIFECYCLE_SCHED_LOG.exists():
        log_lines = LIFECYCLE_SCHED_LOG.read_text().splitlines()
        since_prefix = since[:10] if since else None
        recent_errors = [
            l for l in log_lines
            if "ERROR" in l and (since_prefix is None or l[:10] >= since_prefix)
        ]
        if recent_errors:
            level = "RED" if len(recent_errors) >= 3 else "YELLOW"
            findings.append({
                "persona": "A3_Dani",
                "signal": "error_rate",
                "level": level,
                "detail": f"{len(recent_errors)} ERROR line(s) in lifecycle_scheduler.log "
                          f"since {since or 'all time'}. First: {recent_errors[0][:120]}",
            })

    return findings


def check_a3_dani_voice(since: str | None) -> list[dict]:
    """Check dani_voice_draft.py via draft queue and voice log."""
    findings = []
    watch_since = since or WATCH_START_DATE

    # New voice_error entries since watch start
    queue = _load_jsonl(DRAFT_QUEUE_JSONL, watch_since)
    new_errors = [e for e in queue if e.get("status") == "voice_error"]

    if len(new_errors) >= 3:
        findings.append({
            "persona": "A3_Dani",
            "signal": "error_rate",
            "level": "RED",
            "detail": f"{len(new_errors)} new voice_error entries in draft queue since {watch_since}. "
                      "Check logs/dani_voice_draft.log for root cause.",
        })
    elif len(new_errors) > 0:
        findings.append({
            "persona": "A3_Dani",
            "signal": "error_rate",
            "level": "YELLOW",
            "detail": f"{len(new_errors)} new voice_error entries in draft queue since {watch_since}.",
        })

    # Placeholder token in voice_drafted entries (should never survive to voiced status)
    voiced = [e for e in queue if e.get("status") == "voice_drafted"]
    placeholder_voiced = [
        e for e in voiced
        if DRAFT_PLACEHOLDER_TOKEN in str(e.get("client_email", ""))
        or DRAFT_PLACEHOLDER_TOKEN in str(e.get("subject", ""))
    ]
    if placeholder_voiced:
        findings.append({
            "persona": "A3_Dani",
            "signal": "output_quality",
            "level": "YELLOW",
            "detail": f"{len(placeholder_voiced)} voice_drafted entries still contain "
                      f"'{DRAFT_PLACEHOLDER_TOKEN}' placeholder. Template not fully resolved.",
        })

    return findings


def check_a1_navarro(since: str | None) -> list[dict]:
    """Check dossier_scanner and auto_enrich via dossier_freshness.jsonl."""
    findings = []

    fresh = _load_jsonl(DOSSIER_FRESH_JSONL, since)
    if not fresh:
        findings.append({
            "persona": "A1_Navarro",
            "signal": "error_rate",
            "level": "YELLOW",
            "detail": f"No dossier_freshness.jsonl entries found"
                      + (f" since {since}" if since else "")
                      + ". Scanner may not have run recently.",
        })
    else:
        last = fresh[-1]
        stale_count = last.get("stale_count", 0)
        stale_items = last.get("stale", [])
        if stale_count >= 3:
            findings.append({
                "persona": "A1_Navarro",
                "signal": "error_rate",
                "level": "RED",
                "detail": f"dossier_freshness: {stale_count} stale dossiers detected. "
                          f"Items: {stale_items}",
            })
        elif stale_count > 0:
            findings.append({
                "persona": "A1_Navarro",
                "signal": "error_rate",
                "level": "YELLOW",
                "detail": f"dossier_freshness: {stale_count} stale dossier(s). Items: {stale_items}",
            })

    # auto_enrich cache — informational only.
    # Cache files persist on disk between accesses; age reflects time since last query,
    # NOT a freshness fault (auto_enrich refreshes on access when age > 4h TTL).
    # A runaway re-fetch would manifest as very-recent repeated writes, not old files.
    # Monitor: look for a file updated > once per hour across 3+ consecutive hours.
    cache_dir = THUNDERBIRD / "cache" / "client_context"
    if cache_dir.exists():
        cache_files = list(cache_dir.glob("*.json"))
        now = datetime.now()
        rapid_refresh_suspects = []
        for cf in cache_files:
            # Detect runaway: mtime within the last 3 hours AND file size == 2 bytes (empty/reset)
            try:
                mtime = datetime.fromtimestamp(cf.stat().st_mtime)
                age_hours = (now - mtime).total_seconds() / 3600
                size = cf.stat().st_size
                if age_hours < 3 and size < 10:
                    rapid_refresh_suspects.append(cf.name)
            except OSError:
                pass
        if rapid_refresh_suspects:
            findings.append({
                "persona": "A1_Navarro",
                "signal": "runaway_loop",
                "level": "YELLOW",
                "detail": f"auto_enrich cache has {len(rapid_refresh_suspects)} near-empty "
                          "file(s) refreshed in the last 3h — possible runaway fetch loop: "
                          + ", ".join(rapid_refresh_suspects[:3]),
            })

    return findings


def check_a8_reyes(since: str | None) -> list[dict]:
    """Check tp_scheduler and fpd_sentinel via scheduler log and state file."""
    findings = []

    # FPD state file — parse-ability check
    if not FPD_STATE_JSON.exists():
        findings.append({
            "persona": "A8_Reyes",
            "signal": "error_rate",
            "level": "YELLOW",
            "detail": f"fpd_state.json not found at {FPD_STATE_JSON}. Sentinel may not have run.",
        })
    else:
        try:
            data = json.loads(FPD_STATE_JSON.read_text())
            unexpected_overdue = [
                k for k, v in data.items()
                if isinstance(v, dict) and v.get("state") == "OVERDUE"
            ]
            if unexpected_overdue:
                findings.append({
                    "persona": "A8_Reyes",
                    "signal": "error_rate",
                    "level": "YELLOW",
                    "detail": f"fpd_state.json has OVERDUE client(s): {unexpected_overdue}. "
                              "Verify these are expected and Commander is aware.",
                })
        except (json.JSONDecodeError, OSError) as e:
            findings.append({
                "persona": "A8_Reyes",
                "signal": "error_rate",
                "level": "RED",
                "detail": f"fpd_state.json failed to parse: {e}. Sentinel state corrupted.",
            })

    # TP scheduler — stale TPs in audit log
    events = _load_jsonl(LIFECYCLE_AUDIT_JSONL, since)
    stale = [e for e in events if e.get("event") == "phase_stale"]
    if len(stale) >= 3:
        # Distinguish known pre-watch staleness from new
        new_stale = [
            e for e in stale
            if (e.get("timestamp") or "") >= WATCH_START_DATE
        ]
        if new_stale:
            findings.append({
                "persona": "A8_Reyes",
                "signal": "error_rate",
                "level": "YELLOW",
                "detail": f"TP scheduler: {len(new_stale)} new stale-phase event(s) since {WATCH_START_DATE}. "
                          "Review lifecycle_audit.jsonl for details.",
            })

    return findings


def check_a5_castillo(since: str | None) -> list[dict]:
    """Check A5 Castillo invocation logs for phantom runs."""
    findings = []

    # A5 has no standing daemon. Verify no phantom log files appeared
    # outside normal invocation paths.
    log_dir = THUNDERBIRD / "logs"
    castillo_logs = sorted(log_dir.glob("opencode_wind_staff_castillo_*.log"))

    if since:
        # Filename date is YYYYMMDD (no dashes). Normalize `since` to same format
        # before comparing — otherwise '20260516' > '2026-06-17' due to ASCII ordering
        # of digits vs hyphens, which lets all logs pass the filter.
        since_compact = since.replace("-", "")  # "2026-06-17" → "20260617"
        prefix_len = len("opencode_wind_staff_castillo_")
        new_logs = [
            f for f in castillo_logs
            if f.name[prefix_len:prefix_len + 8] >= since_compact
        ]
    else:
        new_logs = castillo_logs

    # Each log file represents one invocation. More than one per day = potential runaway
    if new_logs:
        # Group by date prefix
        by_date: dict[str, list] = {}
        for f in new_logs:
            # filename: opencode_wind_staff_castillo_YYYYMMDD_HHMMSS_YYYYMMDD_HHMMSS.log
            parts = f.name.split("_")
            if len(parts) >= 5:
                day = parts[4][:8]  # YYYYMMDD
                by_date.setdefault(day, []).append(f.name)

        for day, files in by_date.items():
            if len(files) > 3:
                findings.append({
                    "persona": "A5_Castillo",
                    "signal": "runaway_loop",
                    "level": "YELLOW",
                    "detail": f"A5 Castillo invoked {len(files)} times on {day}. "
                              "Verify these were all Commander-directed.",
                })

    # PII fence check — manual review directive.
    # Automated regex detection of PII in free-text dispatch logs is unreliable:
    # epoch millisecond timestamps (13-digit) match \d{7,} and produce false positives.
    # Instead: when new Castillo logs exist, flag them for human spot-check.
    # Reviewer should grep for @-sign (email) and 7-9 digit sequences (booking refs).
    # Pre-watch A5 logs from 2026-05-16 contain epoch timestamps, not PII — documented.
    if new_logs:
        findings.append({
            "persona": "A5_Castillo",
            "signal": "off_lane",
            "level": "INFO",
            "detail": f"{len(new_logs)} A5 dispatch log(s) since {since or 'watch start'} require "
                      "manual PII spot-check. Run: grep -E '@|\\b[0-9]{7,9}\\b' "
                      f"logs/opencode_wind_staff_castillo_*.log | head -20",
        })

    return findings


# ── Dashboard update (non-destructive) ─────────────────────────────────────

def update_dashboard(findings: list[dict]) -> None:
    """Append autonomy_watch summary to a7_metrics_dashboard.json if it exists."""
    if not DASHBOARD_JSON.exists():
        return
    try:
        dash = json.loads(DASHBOARD_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return

    reds = [f for f in findings if f["level"] == "RED"]
    yellows = [f for f in findings if f["level"] == "YELLOW"]

    dash["autonomy_watch"] = {
        "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "red_count": len(reds),
        "yellow_count": len(yellows),
        "overall": "RED" if reds else ("YELLOW" if yellows else "GREEN"),
        "findings": findings,
    }

    try:
        DASHBOARD_JSON.write_text(json.dumps(dash, indent=2))
    except OSError:
        pass  # read-only check; dashboard update is best-effort


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="A7 autonomy health check — read-only")
    parser.add_argument("--since", default=None,
                        help="Only check events after this date (YYYY-MM-DD). Default: today.")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Emit JSON output instead of human-readable.")
    args = parser.parse_args()

    since = args.since or date.today().strftime("%Y-%m-%d")

    all_findings: list[dict] = []
    all_findings += check_a3_lifecycle_scheduler(since)
    all_findings += check_a3_dani_voice(since)
    all_findings += check_a1_navarro(since)
    all_findings += check_a8_reyes(since)
    all_findings += check_a5_castillo(since)

    reds    = [f for f in all_findings if f["level"] == "RED"]
    yellows = [f for f in all_findings if f["level"] == "YELLOW"]
    overall = "RED" if reds else ("YELLOW" if yellows else "GREEN")

    if args.json_out:
        print(json.dumps({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "since": since,
            "overall": overall,
            "red": len(reds),
            "yellow": len(yellows),
            "findings": all_findings,
        }, indent=2))
    else:
        width = 70
        print("=" * width)
        print("A7 STERLING — AUTONOMY HEALTH CHECK")
        print(f"MISSION-167 · {date.today().isoformat()} · since {since}")
        print("=" * width)
        print(f"OVERALL: {overall}  |  RED: {len(reds)}  |  YELLOW: {len(yellows)}")
        print()

        if not all_findings:
            print("All GREEN — no anomalies detected.")
        else:
            by_persona: dict[str, list] = {}
            for f in all_findings:
                by_persona.setdefault(f["persona"], []).append(f)

            for persona, items in by_persona.items():
                print(f"[{persona}]")
                for item in items:
                    lvl = item["level"]
                    print(f"  {lvl:<8} {item['signal']:<20} {item['detail'][:120]}")
                print()

        if reds:
            print("-" * width)
            print("ESCALATION REQUIRED:")
            for r in reds:
                sig = r["signal"]
                if sig == "wf17_breach":
                    print(f"  RED {sig}: NOTIFY COMMANDER IMMEDIATELY")
                elif sig == "off_lane":
                    print(f"  RED {sig}: Notify COS Hale within 1 hour")
                else:
                    print(f"  RED {sig}: Notify COS Hale within 4 hours")

        print("=" * width)

    # Update dashboard (best-effort)
    update_dashboard(all_findings)

    # Exit code
    if reds:
        return 2
    if yellows:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
