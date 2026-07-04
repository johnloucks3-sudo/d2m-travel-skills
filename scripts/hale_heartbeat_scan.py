#!/usr/bin/env python3
"""
hale_heartbeat_scan.py — the between-sessions initiative mechanism.

Wakes 4x/day (03:00/09:00/15:00/21:00 MT via hale-heartbeat.timer), scans for
patterns the Commander shouldn't have to notice and report himself, and exits
QUIETLY if nothing crosses threshold — no output, no page, no token spend
beyond the scan itself.

Scans (v0, all read-only, no network, <1s):
  1. Repeat alerts    — same alert firing N+ times in overnight_ops_log.json
  2. Stale CI tools   — config/ci_registry.json entries not re-evaluated in
                        reeval_cadence_days
  3. Aging P0/P1      — mission_board.json items open > N days untouched
  4. Overdue suspenses — mission_board.json suspense_date passed on a still-OPEN
                        item (terminal statuses excluded — a closed mission with
                        a stale suspense_date is not a finding, just old data)

Every finding is logged to OpsCenter/state/heartbeat_scan_latest.json for the
next morning brief to pick up. NEW aging-P0 findings (not seen in the prior
run) additionally page Telegram immediately — same dedup-until-resolved
pattern as scripts/credentials_health_check.py. Stale CI tools and repeat
alerts are brief-only (lower urgency, no page).

Dreams2Memories Travel, LLC · 2026-07-04 — wired to hale-heartbeat.timer
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPEAT_ALERT_THRESHOLD = 3
STALE_MISSION_DAYS = 7
TERMINAL_STATUSES = {
    "completed", "complete", "closed", "archived",
    "closed_duplicate", "resolved_new_finding",
    "archived_noise", "killed", "eliminated",
}
# Deliberately NOT terminal: parked, suspended, deferred, hold_until_*,
# pending_review, pending_commander, commander_review_pending,
# awaiting_commander_decision, backlog, reply_drafted, in_progress, active,
# monitoring — these are "come back later" states where a passed
# suspense_date is exactly the review trigger, not stale noise.
STATE_FILE = ROOT / "OpsCenter/state/heartbeat_scan_latest.json"
DEDUP_FILE = ROOT / "OpsCenter/state/heartbeat_p0_dedup.json"


def scan_repeat_alerts() -> list[dict]:
    p = ROOT / "OpsCenter/state/overnight_ops_log.json"
    if not p.exists():
        return []
    entries = json.loads(p.read_text())
    counts: dict[str, int] = {}
    for e in entries:
        for d in e.get("details", []):
            counts[d] = counts.get(d, 0) + 1
    findings = []
    for detail, count in counts.items():
        if count >= REPEAT_ALERT_THRESHOLD:
            findings.append({
                "category": "repeat_alert",
                "what": f'"{detail}" appeared {count}x in the ops log',
                "why": f"crossed repeat threshold ({REPEAT_ALERT_THRESHOLD}+)",
                "action": "Flag for root-cause pass — same shape as the 2026-07-04 credential doomsday",
                "file": str(p),
            })
    return findings


def scan_stale_ci_tools() -> list[dict]:
    p = ROOT / "config/ci_registry.json"
    if not p.exists():
        return []
    reg = json.loads(p.read_text())
    now = datetime.now(timezone.utc)
    findings = []
    for s in reg.get("skills", []):
        last_reeval = s.get("last_reeval")
        cadence = s.get("reeval_cadence_days")
        if not cadence:
            continue
        # Prefer the first wrapped script (the actual tool) over the registry
        # file itself — that's what the Commander needs to look at.
        wraps = s.get("wraps") or []
        tool_file = str(ROOT / wraps[0]) if wraps else str(p)
        if not last_reeval:
            findings.append({
                "category": "stale_ci_tool",
                "what": f"{s.get('name', s.get('id'))} has NEVER been re-evaluated",
                "why": "no last_reeval timestamp on record",
                "action": f"Route to Whetstone for currency check",
                "file": tool_file,
            })
            continue
        try:
            last_dt = datetime.fromisoformat(last_reeval.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_days = (now - last_dt).days
            if age_days > cadence:
                findings.append({
                    "category": "stale_ci_tool",
                    "what": f"{s.get('name', s.get('id'))} last re-evaluated {age_days}d ago (cadence: {cadence}d)",
                    "why": f"exceeds its own {cadence}-day reeval cadence by {age_days - cadence}d",
                    "action": "Route to Whetstone for currency check",
                    "file": tool_file,
                })
        except (ValueError, AttributeError):
            continue
    return findings


_DOSSIER_DIR = ROOT / "dossiers"
_DOSSIER_STEMS = None  # lazy-built cache: {lowercase surname: full path}


_DOSSIER_STOPWORDS = {
    "atlas", "claude", "dossier", "grandeur", "group",
    "prospect", "scandi", "silvernova",
}  # dossier filename first-tokens that are ship names / generic labels, not
   # client surnames — matching these produces false positives (2026-07-04:
   # "United Group Desk" in a mission title matched GROUP_Kuklinski_*.md)


def _mission_file_link(title: str, mission_board_path: Path) -> str:
    """Best-effort: link to a matching client dossier if the mission title
    names one, else fall back to the mission board itself. Same pattern the
    brief's anchor card already uses for booking dossiers."""
    global _DOSSIER_STEMS
    if _DOSSIER_STEMS is None:
        _DOSSIER_STEMS = {}
        if _DOSSIER_DIR.exists():
            for f in _DOSSIER_DIR.glob("*.md"):
                stem = f.stem.split("_")[0].lower()
                if stem and stem not in _DOSSIER_STOPWORDS and len(stem) >= 4:
                    _DOSSIER_STEMS.setdefault(stem, f)
    for word in title.replace("—", " ").replace("-", " ").split():
        hit = _DOSSIER_STEMS.get(word.strip(",.").lower())
        if hit:
            return str(hit)
    return str(mission_board_path)


def scan_aging_missions() -> list[dict]:
    p = ROOT / "OpsCenter/mission_board.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    missions = d if isinstance(d, list) else d.get("missions", d.get("active", []))
    now = datetime.now(timezone.utc)
    findings = []
    for m in missions:
        if m.get("status") not in ("active", "in_progress"):
            continue
        if m.get("priority") not in ("P0", "P1"):
            continue
        created = m.get("created_at")
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_days = (now - created_dt).days
            if age_days >= STALE_MISSION_DAYS:
                findings.append({
                    "category": "aging_mission",
                    "what": f"{m.get('id')} ({m.get('priority')}) — \"{m.get('title', '')[:60]}\" open {age_days}d",
                    "why": f"P0/P1 untouched >= {STALE_MISSION_DAYS}d",
                    "action": "Surface in next brief with a status/kill recommendation, not just a re-list",
                    "file": _mission_file_link(m.get("title", ""), p),
                })
        except (ValueError, AttributeError):
            continue
    return findings


def scan_overdue_suspenses() -> list[dict]:
    """Overdue suspense_date on a still-OPEN mission. Terminal statuses excluded
    so a long-closed mission with a stale suspense_date isn't a false finding —
    the exact 'first pass counted 15, all already closed' mistake caught 2026-07-04
    while building this. 'parked' is intentionally NOT terminal — a parked item's
    suspense_date passing is precisely the review trigger."""
    p = ROOT / "OpsCenter/mission_board.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    missions = d if isinstance(d, list) else d.get("missions", d.get("active", []))
    today = datetime.now(timezone.utc).date()
    findings = []
    for m in missions:
        if m.get("status") in TERMINAL_STATUSES:
            continue
        sd = m.get("suspense_date")
        if not sd:
            continue
        try:
            sd_date = datetime.fromisoformat(sd.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            continue
        days_overdue = (today - sd_date).days
        if days_overdue > 0:
            findings.append({
                "category": "overdue_suspense",
                "what": f"{m.get('id')} ({m.get('priority')}/{m.get('status')}) — \"{m.get('title', '')[:60]}\" suspense {sd_date} ({days_overdue}d overdue)",
                "why": f"suspense_date passed {days_overdue}d ago, status still open ({m.get('status')})",
                "action": "Present as a decision-matrix item on next login (Commander directive 2026-07-04)",
                "file": _mission_file_link(m.get("title", ""), p),
            })
    return findings


def _page_new_p0_findings(aging_findings: list[dict]) -> None:
    """Page Telegram for aging-P0 findings not already paged (dedup by 'what' text,
    same one-and-done pattern as scripts/credentials_health_check.py)."""
    p0_findings = [f for f in aging_findings if "(P0)" in f["what"]]
    if not p0_findings:
        return

    dedup = json.loads(DEDUP_FILE.read_text()) if DEDUP_FILE.exists() else {}
    new = [f for f in p0_findings if f["what"] not in dedup]
    if not new:
        return

    try:
        from OpsCenter.hale_telegram_reporter import send_to_commander
        lines = ["⚡ HEARTBEAT — P0 aging without update\n"]
        for f in new:
            lines.append(f"🔴 {f['what']}")
            lines.append(f"   {f['action']}\n")
        sent = send_to_commander("\n".join(lines), message_type="alert", urgent=True)
        if sent:
            for f in new:
                dedup[f["what"]] = datetime.now(timezone.utc).isoformat()
            DEDUP_FILE.write_text(json.dumps(dedup, indent=1))
    except Exception as e:
        print(f"heartbeat page failed (not deduped, will retry next wake): {e}")

    # Prune dedup entries for findings that no longer exist (mission closed/updated)
    still_open = {f["what"] for f in p0_findings}
    pruned = {k: v for k, v in dedup.items() if k in still_open}
    if pruned != dedup:
        DEDUP_FILE.write_text(json.dumps(pruned, indent=1))


def main():
    repeat = scan_repeat_alerts()
    stale = scan_stale_ci_tools()
    aging = scan_aging_missions()
    overdue = scan_overdue_suspenses()
    all_findings = repeat + stale + aging + overdue

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "finding_count": len(all_findings),
        "findings": all_findings,
    }, indent=1))

    print(f"=== HALE HEARTBEAT SCAN — {datetime.now():%Y-%m-%d %H:%M} MT ===")
    if not all_findings:
        print("Nothing crossed threshold. QUIET EXIT — no page, no report.")
        return

    by_cat: dict[str, list] = {}
    for f in all_findings:
        by_cat.setdefault(f["category"], []).append(f)

    for cat, items in by_cat.items():
        print(f"\n[{cat}] {len(items)} finding(s):")
        for it in items:
            print(f"  • {it['what']}")
            print(f"    why: {it['why']}")
            print(f"    Hale's next action: {it['action']}")
            if it.get("file"):
                print(f"    file://{it['file']}")

    _page_new_p0_findings(aging)


if __name__ == "__main__":
    main()
