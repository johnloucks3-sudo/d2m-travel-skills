#!/usr/bin/env python3
"""
d2m_lifecycle_scheduler.py
Dreams2Memories Travel — Thunderbird Wing
COS Hale's Lifecycle Automation Engine

Daily scheduler that reads ALL client touchpoint JSONs and fires:
  1. Search window initiations (starts research tasks)
  2. Weekly intel reports during active search windows (Mondays)
  3. Portal opening alerts (excursions, culinary, dining, check-in)
  4. TP email placement (drafts in d2mconcierge or SEND to johnloucks3)
  5. Payment sequence alerts
  6. Monthly validation reminders

Run daily via systemd timer at 0530 MDT (before Commander's 0600 coffee):
  systemctl --user start d2m-lifecycle.service

Usage:
  python3 d2m_lifecycle_scheduler.py              # Normal daily run
  python3 d2m_lifecycle_scheduler.py --dry-run     # Preview without actions
  python3 d2m_lifecycle_scheduler.py --client loucks_regent  # Single client
  python3 d2m_lifecycle_scheduler.py --report      # Generate status report only
  python3 d2m_lifecycle_scheduler.py --force TP-2.1  # Force-fire a specific TP

Standing Order 2026-04-17: COS Hale has COO authority over day-to-day operations.
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────────

THUNDERBIRD_ROOT    = Path("/home/john/Thunderbird")
TOUCHPOINTS_DIR     = THUNDERBIRD_ROOT / "D2M" / "clients"
EMAIL_DRAFTS_DIR    = THUNDERBIRD_ROOT / "output"
LOG_FILE            = THUNDERBIRD_ROOT / "logs" / "lifecycle_scheduler.log"
STATE_FILE          = THUNDERBIRD_ROOT / "state" / "lifecycle_scheduler_state.json"
INBOX_FILE          = THUNDERBIRD_ROOT / "OpsCenter" / "claude_inbox.md"
WING_COMMS          = THUNDERBIRD_ROOT / "OpsCenter" / "collaboration" / "wing_comms.md"

COMMANDER_EMAIL     = "johnloucks3@gmail.com"
CONCIERGE_EMAIL     = "d2mconcierge@gmail.com"

# ── Logging ────────────────────────────────────────────────────────────────────

os.makedirs(THUNDERBIRD_ROOT / "logs", exist_ok=True)
os.makedirs(THUNDERBIRD_ROOT / "state", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("lifecycle_scheduler")


# ── State Management ──────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load persistent state (tracks what's been fired)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"fired_actions": {}, "last_run": None, "weekly_reports_sent": {}}


def save_state(state: dict):
    """Persist state to disk."""
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ── Touchpoint Loading ────────────────────────────────────────────────────────

def load_all_touchpoints(client_filter: Optional[str] = None) -> list[dict]:
    """Load all touchpoint JSON files. Returns list of (client_data, tp) tuples."""
    results = []
    for json_file in sorted(TOUCHPOINTS_DIR.glob("*_touchpoints.json")):
        client_id = json_file.stem.replace("_touchpoints", "")
        if client_filter and client_filter != client_id:
            continue
        try:
            data = json.loads(json_file.read_text())
            for tp in data.get("touchpoints", []):
                results.append({
                    "client_id": data.get("client_id", client_id),
                    "client_name": data.get("client_name", client_id),
                    "client_email": data.get("client_email", ""),
                    "advisor_email": data.get("advisor_email", ""),
                    "cruise_line": data.get("cruise_line", ""),
                    "ship": data.get("ship", ""),
                    "embarkation_date": data.get("embarkation_date", ""),
                    "owner_client_protocol": data.get("owner_client_protocol", ""),
                    "email_drafts_doc": data.get("email_drafts_doc", ""),
                    "tp": tp,
                    "source_file": str(json_file),
                })
        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"Failed to load {json_file}: {e}")
    return results


# ── Date Helpers ──────────────────────────────────────────────────────────────

def parse_date(date_str: str) -> Optional[date]:
    """Parse YYYY-MM-DD date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def is_monday() -> bool:
    return date.today().weekday() == 0


def is_first_of_month() -> bool:
    return date.today().day == 1


# ── Action Classifiers ────────────────────────────────────────────────────────

def classify_tp_today(tp_data: dict, today: date) -> list[str]:
    """
    Classify what actions should fire for this touchpoint today.
    Returns list of action types.
    """
    tp = tp_data["tp"]
    actions = []

    trigger_date = parse_date(tp.get("trigger_date", ""))
    search_start = parse_date(tp.get("search_start", ""))
    search_end = parse_date(tp.get("search_end", ""))
    status = tp.get("status", "pending")

    # Skip already-sent touchpoints
    if status == "sent":
        return actions

    # 1. TRIGGER DATE — TP email is due today
    if trigger_date and trigger_date == today:
        actions.append("TRIGGER_EMAIL")

    # 2. OVERDUE — TP was due but not sent (within 7-day grace)
    if trigger_date and today > trigger_date and (today - trigger_date).days <= 7:
        if status != "sent":
            actions.append("OVERDUE_ALERT")

    # 3. SEARCH WINDOW START — Research should begin
    if search_start and search_start == today:
        actions.append("SEARCH_WINDOW_OPEN")

    # 4. ACTIVE SEARCH WINDOW — Monday weekly report
    if search_start and search_end:
        if search_start <= today <= search_end and is_monday():
            if tp.get("weekly_reports", False):
                actions.append("WEEKLY_REPORT_DUE")

    # 5. SEARCH WINDOW CLOSING — 3-day warning
    if search_end and search_end == today + timedelta(days=3):
        actions.append("SEARCH_WINDOW_CLOSING")

    # 6. MONTHLY VALIDATION — fires on 1st of each month
    if tp.get("cadence") == "monthly_1st" and is_first_of_month():
        instances = tp.get("instances", [])
        today_str = today.isoformat()
        if today_str in instances:
            actions.append("MONTHLY_VALIDATION")

    # 7. PORTAL OPENING ALERT — fires day-of for portal dates
    # (These are critical — excursions sell out)
    portal_alerts = _check_portal_dates(tp_data, today)
    actions.extend(portal_alerts)

    # 8. PAYMENT CRITICAL — FPD day
    if tp.get("category") == "payment" and trigger_date == today:
        if "FINAL" in tp.get("label", "").upper() or "DUE" in tp.get("subject", "").upper():
            actions.append("PAYMENT_CRITICAL")

    return actions


def _check_portal_dates(tp_data: dict, today: date) -> list[str]:
    """Check if any Regent/Viking portal dates match today."""
    actions = []
    # Portal dates are stored at the client level, not TP level
    # We check the excursion/culinary/dining TPs for portal-date awareness
    tp = tp_data["tp"]
    category = tp.get("category", "")

    if category == "excursions" and "portal" in tp.get("notes", "").lower():
        trigger = parse_date(tp.get("trigger_date", ""))
        if trigger and trigger == today:
            actions.append("PORTAL_OPENING_EXCURSIONS")

    if category == "culinary":
        trigger = parse_date(tp.get("trigger_date", ""))
        if trigger and trigger == today:
            actions.append("PORTAL_OPENING_CULINARY")

    if category == "dining":
        trigger = parse_date(tp.get("trigger_date", ""))
        if trigger and trigger == today:
            actions.append("PORTAL_OPENING_DINING")

    return actions


# ── Action Executors ──────────────────────────────────────────────────────────

def execute_action(action: str, tp_data: dict, state: dict, dry_run: bool = False):
    """Execute a lifecycle action."""
    tp = tp_data["tp"]
    client = tp_data["client_name"]
    tp_id = tp.get("id", "UNKNOWN")
    label = tp.get("label", "")
    is_owner_client = "Commander IS" in tp_data.get("owner_client_protocol", "")

    action_key = f"{tp_data['client_id']}:{tp_id}:{action}:{date.today().isoformat()}"

    # Skip if already fired today
    if action_key in state.get("fired_actions", {}):
        log.info(f"  ⏭  Already fired: {action_key}")
        return

    log.info(f"  🔥 {action} — {client} — {tp_id} {label}")

    if action == "TRIGGER_EMAIL":
        _fire_trigger_email(tp_data, is_owner_client, dry_run)
    elif action == "OVERDUE_ALERT":
        _fire_overdue_alert(tp_data, dry_run)
    elif action == "SEARCH_WINDOW_OPEN":
        _fire_search_window_open(tp_data, dry_run)
    elif action == "WEEKLY_REPORT_DUE":
        _fire_weekly_report(tp_data, dry_run)
    elif action == "SEARCH_WINDOW_CLOSING":
        _fire_search_closing(tp_data, dry_run)
    elif action == "MONTHLY_VALIDATION":
        _fire_monthly_validation(tp_data, dry_run)
    elif action.startswith("PORTAL_OPENING"):
        _fire_portal_alert(tp_data, action, dry_run)
    elif action == "PAYMENT_CRITICAL":
        _fire_payment_critical(tp_data, dry_run)

    if not dry_run:
        state.setdefault("fired_actions", {})[action_key] = datetime.now().isoformat()


def _fire_trigger_email(tp_data: dict, is_owner_client: bool, dry_run: bool):
    """Place TP email in appropriate channel."""
    tp = tp_data["tp"]
    subject = tp.get("subject", f"TP {tp.get('id')} — {tp.get('label')}")

    if is_owner_client:
        # Loucks: SEND directly to Commander (not draft)
        channel = f"SEND to {COMMANDER_EMAIL}"
        log.info(f"    → Owner-client protocol: {channel}")
    else:
        # Client-facing: Create draft in d2mconcierge
        channel = f"DRAFT in {CONCIERGE_EMAIL}"
        log.info(f"    → WF-17 draft: {channel}")

    if dry_run:
        log.info(f"    [DRY RUN] Would {channel}: {subject}")
        return

    # Write task to claude_inbox for AI-assisted draft creation
    _post_to_inbox(
        f"## LIFECYCLE — TP EMAIL DUE\n"
        f"**Client:** {tp_data['client_name']}\n"
        f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
        f"**Subject:** {subject}\n"
        f"**Channel:** {channel}\n"
        f"**Email Drafts Doc:** {tp_data.get('email_drafts_doc', 'N/A')}\n"
        f"**Staff Lead:** {tp.get('staff_lead', 'Hale')}\n"
        f"**Notes:** {tp.get('notes', '')}\n"
        f"**Action:** Extract email from drafts doc, format with D2M stationery, "
        f"{'SEND to Commander' if is_owner_client else 'place in d2mconcierge drafts for Commander approval'}.\n"
    )


def _fire_overdue_alert(tp_data: dict, dry_run: bool):
    """Alert COS about overdue touchpoint."""
    tp = tp_data["tp"]
    days_overdue = (date.today() - parse_date(tp["trigger_date"])).days

    msg = (
        f"⚠️ OVERDUE: {tp_data['client_name']} — TP {tp['id']} {tp['label']} "
        f"— {days_overdue} days overdue. Staff: {tp.get('staff_lead', 'Hale')}"
    )
    log.warning(msg)

    if not dry_run:
        _post_to_inbox(f"## ⚠️ OVERDUE TOUCHPOINT\n{msg}\n**Action Required:** Immediate attention.\n")


def _fire_search_window_open(tp_data: dict, dry_run: bool):
    """Initiate research tasks for a new search window.

    Option C — Auto-Execute (SO 2026-04-17):
    If the touchpoint has an 'arc' field (arc1/arc2/arc3) AND arc_search_params,
    the ARC Price Dispatcher is launched as a background subprocess.
    Results cache to core/travel/data/ and post to wing_comms when ready.
    Falls back to manual wing_comms task if params not configured.
    """
    tp = tp_data["tp"]
    staff = tp.get("staff_lead", "A2 Dembe")
    arc = tp.get("arc", "")

    msg = (
        f"🔍 SEARCH WINDOW OPEN: {tp_data['client_name']} — TP {tp['id']} {tp['label']}\n"
        f"   Arc type: {arc or 'none (timeline TP)'}\n"
        f"   Staff: {staff}\n"
        f"   Window: {tp.get('search_start')} → {tp.get('search_end')}\n"
        f"   Send date: {tp.get('trigger_date')}\n"
        f"   Notes: {tp.get('notes', '')}"
    )
    log.info(msg)

    # ── Option C: ARC auto-execute ────────────────────────────────────────────
    if arc.startswith("arc") and not dry_run:
        try:
            # Import here to avoid hard dependency if dispatcher not installed
            import sys
            dispatcher_path = Path(__file__).parent / "arc_price_dispatcher.py"
            if dispatcher_path.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from arc_price_dispatcher import dispatch_arc  # type: ignore
                results_file = dispatch_arc(tp_data, tp_data, dry_run=False)
                if results_file:
                    log.info(f"  ARC dispatcher launched — results → {results_file}")
                    return  # dispatcher posted its own wing_comms notice
                # If dispatch_arc returned empty (no params), fall through to manual task
            else:
                log.warning("  arc_price_dispatcher.py not found — falling back to manual task")
        except Exception as e:
            log.error(f"  ARC dispatcher failed: {e} — falling back to manual task")

    if arc.startswith("arc") and dry_run:
        log.info(f"  [DRY RUN] Would dispatch ARC auto-execute for {tp['id']}")

    # ── Fallback / timeline TPs: manual wing_comms task ──────────────────────
    if not dry_run:
        _post_to_wing_comms(
            f"## RESEARCH TASK — {tp['id']} {tp['label']}\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**Assigned to:** {staff}\n"
            f"**Arc type:** {arc or 'timeline (no auto-execute)'}\n"
            f"**Window:** {tp.get('search_start')} → {tp.get('search_end')}\n"
            f"**Deliverable date:** {tp.get('trigger_date')}\n"
            f"**Weekly reports to Commander:** {'Yes — every Monday' if tp.get('weekly_reports') else 'No'}\n"
            f"**Notes:** {tp.get('notes', '')}\n"
            + (f"**Action:** Configure arc_search_params in touchpoints JSON to enable auto-execute.\n"
               if arc.startswith("arc") else "")
            + f"**Authority:** COS Hale (COO SO 2026-04-17)\n"
        )


def _fire_weekly_report(tp_data: dict, dry_run: bool):
    """Generate Monday weekly intel report during active search window."""
    tp = tp_data["tp"]

    msg = (
        f"📊 WEEKLY REPORT DUE: {tp_data['client_name']} — TP {tp['id']} {tp['label']}\n"
        f"   Staff: {tp.get('staff_lead')}\n"
        f"   Delivery: SEND to {COMMANDER_EMAIL}"
    )
    log.info(msg)

    if not dry_run:
        _post_to_inbox(
            f"## WEEKLY INTEL REPORT DUE\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
            f"**Staff:** {tp.get('staff_lead')}\n"
            f"**Action:** Compile this week's research findings into a weekly report. "
            f"SEND to {COMMANDER_EMAIL} (not draft — per intel full-send SO 27 MAR 2026).\n"
            f"**Format:** Subject: '[Week of DATE] {tp_data['client_name']} — {tp.get('label')} Intel Report'\n"
        )


def _fire_search_closing(tp_data: dict, dry_run: bool):
    """Warn that a search window is closing in 3 days."""
    tp = tp_data["tp"]
    log.warning(
        f"⏰ SEARCH CLOSING IN 3 DAYS: {tp_data['client_name']} — "
        f"TP {tp['id']} {tp['label']} — closes {tp.get('search_end')}"
    )

    if not dry_run:
        _post_to_inbox(
            f"## ⏰ SEARCH WINDOW CLOSING\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
            f"**Closes:** {tp.get('search_end')} (3 days)\n"
            f"**Staff:** {tp.get('staff_lead')}\n"
            f"**Action:** Finalize research. TP email due {tp.get('trigger_date')}.\n"
        )


def _fire_monthly_validation(tp_data: dict, dry_run: bool):
    """Fire monthly validation touchpoint."""
    tp = tp_data["tp"]
    log.info(
        f"📋 MONTHLY VALIDATION: {tp_data['client_name']} — "
        f"TP {tp['id']} {tp['label']} — {date.today().strftime('%B %Y')}"
    )

    if not dry_run:
        _post_to_inbox(
            f"## MONTHLY VALIDATION DUE\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**Month:** {date.today().strftime('%B %Y')}\n"
            f"**Action:** Compile validation matrix status for all tracked items "
            f"(payments, flights, hotels, transfers, excursions, dining, documents, guest registration). "
            f"Use the monthly validation template from the email drafts doc.\n"
        )


def _fire_portal_alert(tp_data: dict, action: str, dry_run: bool):
    """Alert about cruise line portal opening."""
    tp = tp_data["tp"]
    portal_type = action.replace("PORTAL_OPENING_", "").lower()

    log.warning(
        f"🚨 PORTAL OPENING TODAY: {tp_data['client_name']} — {portal_type} portal "
        f"— {tp_data.get('cruise_line')} — TP {tp['id']}"
    )

    if not dry_run:
        _post_to_inbox(
            f"## 🚨 PORTAL OPENING TODAY — {portal_type.upper()}\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**Cruise line:** {tp_data.get('cruise_line')}\n"
            f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
            f"**Action:** Execute bookings per Commander's confirmed preferences. "
            f"Popular items sell out within hours.\n"
            f"**Notes:** {tp.get('notes', '')}\n"
        )


def _fire_payment_critical(tp_data: dict, dry_run: bool):
    """Fire critical payment alert."""
    tp = tp_data["tp"]

    log.critical(
        f"💰 PAYMENT CRITICAL: {tp_data['client_name']} — {tp.get('subject')} — "
        f"CANCELLATION RISK IF NOT PAID TODAY"
    )

    if not dry_run:
        _post_to_inbox(
            f"## 💰 CRITICAL — FINAL PAYMENT DUE TODAY\n"
            f"**Client:** {tp_data['client_name']}\n"
            f"**Subject:** {tp.get('subject')}\n"
            f"**Action:** Verify payment received. If not, escalate immediately to Commander.\n"
            f"**Notes:** {tp.get('notes', '')}\n"
        )


# ── Communication Helpers ─────────────────────────────────────────────────────

def _post_to_inbox(message: str):
    """Append a task to claude_inbox.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n---\n**[LIFECYCLE SCHEDULER — {timestamp}]**\n{message}\n"
    with open(INBOX_FILE, "a") as f:
        f.write(entry)


def _post_to_wing_comms(message: str):
    """Post a staff tasking to wing_comms.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n---\n**[COS HALE — LIFECYCLE TASKING — {timestamp}]**\n{message}\n"
    with open(WING_COMMS, "a") as f:
        f.write(entry)


# ── Status Report ─────────────────────────────────────────────────────────────

def generate_status_report(all_tp_data: list[dict]) -> str:
    """Generate a comprehensive lifecycle status report."""
    today = date.today()
    lines = [
        f"# D2M LIFECYCLE STATUS REPORT",
        f"## Generated: {today.isoformat()} by COS Hale",
        f"",
    ]

    # Group by client
    clients = {}
    for td in all_tp_data:
        cid = td["client_id"]
        clients.setdefault(cid, {"name": td["client_name"], "tps": []})
        clients[cid]["tps"].append(td)

    for cid, cdata in sorted(clients.items()):
        lines.append(f"### {cdata['name']}")
        lines.append(f"| TP | Label | Trigger | Status | Actions Today |")
        lines.append(f"|-----|-------|---------|--------|---------------|")

        for td in sorted(cdata["tps"], key=lambda x: x["tp"].get("trigger_date") or "9999"):
            tp = td["tp"]
            actions = classify_tp_today(td, today)
            actions_str = ", ".join(actions) if actions else "—"
            trigger = tp.get("trigger_date", "—")
            status = tp.get("status", "pending")
            lines.append(
                f"| {tp.get('id', '?')} | {tp.get('label', '?')[:40]} | "
                f"{trigger} | {status} | {actions_str} |"
            )
        lines.append("")

    # Summary
    total_tps = len(all_tp_data)
    sent = sum(1 for td in all_tp_data if td["tp"].get("status") == "sent")
    pending = sum(1 for td in all_tp_data if td["tp"].get("status") == "pending")
    active = sum(1 for td in all_tp_data if td["tp"].get("status") == "active")

    lines.extend([
        f"---",
        f"**Total TPs:** {total_tps} | **Sent:** {sent} | **Active:** {active} | **Pending:** {pending}",
        f"**Clients:** {len(clients)}",
    ])

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2M Lifecycle Scheduler — COS Hale")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--client", type=str, help="Filter to single client ID")
    parser.add_argument("--report", action="store_true", help="Generate status report only")
    parser.add_argument("--force", type=str, help="Force-fire a specific TP ID")
    args = parser.parse_args()

    today = date.today()
    log.info(f"═══ D2M Lifecycle Scheduler — {today.isoformat()} ═══")
    log.info(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    # Load all touchpoints
    all_tp_data = load_all_touchpoints(args.client)
    log.info(f"  Loaded {len(all_tp_data)} touchpoints across {len(set(td['client_id'] for td in all_tp_data))} clients")

    if not all_tp_data:
        log.warning("  No touchpoints found. Check D2M/clients/ directory.")
        return

    # Report mode
    if args.report:
        report = generate_status_report(all_tp_data)
        print(report)
        report_path = THUNDERBIRD_ROOT / "output" / "lifecycle_status_report.md"
        report_path.write_text(report)
        log.info(f"  Report saved to {report_path}")
        return

    # Load state
    state = load_state()

    # Force mode
    if args.force:
        forced = [td for td in all_tp_data if td["tp"].get("id") == args.force]
        if not forced:
            log.error(f"  TP ID '{args.force}' not found")
            return
        for td in forced:
            log.info(f"  FORCING: {td['client_name']} — {args.force}")
            execute_action("TRIGGER_EMAIL", td, state, args.dry_run)
        save_state(state)
        return

    # Normal daily run — classify and execute all actions
    action_count = 0
    for td in all_tp_data:
        actions = classify_tp_today(td, today)
        for action in actions:
            execute_action(action, td, state, args.dry_run)
            action_count += 1

    log.info(f"  ═══ Complete: {action_count} actions fired ═══")

    # Save state
    if not args.dry_run:
        save_state(state)

    # If actions fired, log summary
    if action_count > 0:
        log.info(f"  Summary: {action_count} lifecycle actions executed for {today.isoformat()}")
    else:
        log.info(f"  No lifecycle actions due today.")


if __name__ == "__main__":
    main()
