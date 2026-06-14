#!/usr/bin/env python3
"""
d2m-post-trip-followup — Testimonial and follow-up queue at T+7, T+21, T+45 post-return.

Reads dossiers/Blackboard. If a client returned 7, 21, or 45 days ago
and no follow-up has been sent, queue a Gmail draft for Commander review.

Schedule: Daily 10:00 MDT via systemd timer
Output:   OpsCenter/logs/post_trip_followup.log
          OpsCenter/data/followup_ledger.json (tracks sent follow-ups)
          Gmail draft (d2mconcierge) for each due follow-up
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
DOSSIERS_DIR = ROOT / "dossiers"
LOG_PATH = ROOT / "OpsCenter/logs/post_trip_followup.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/post_trip_followup.jsonl"
LEDGER_FILE = ROOT / "OpsCenter/data/followup_ledger.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [POST-TRIP] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

# Days post-return to send follow-ups
FOLLOWUP_DAYS = [7, 21, 45]
FOLLOWUP_WINDOW = 2  # Accept ±2 days around each milestone


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def load_ledger() -> dict:
    try:
        if LEDGER_FILE.exists():
            return json.loads(LEDGER_FILE.read_text())
    except Exception:
        pass
    return {}


def save_ledger(ledger: dict) -> None:
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_FILE.write_text(json.dumps(ledger, indent=2))


def is_already_sent(ledger: dict, client_id: str, milestone: int) -> bool:
    return ledger.get(f"{client_id}:T+{milestone}") is not None


def mark_sent(ledger: dict, client_id: str, milestone: int) -> None:
    ledger[f"{client_id}:T+{milestone}"] = str(date.today())


FOLLOWUP_TEMPLATES = {
    7: {
        "subject": "We hope your trip was everything you dreamed of!",
        "body": """<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Dear [CLIENT],</p>
<p>It's been a week since you returned from your [DESTINATION] adventure — we hope you're still riding that wave of wonderful memories!</p>
<p>We'd love to hear how everything went. If you have a moment, we'd be grateful for a quick note about your experience. Your feedback helps us serve future travelers and means the world to us.</p>
<p>And if you're already dreaming of the next journey — we're here.</p>
<p>With warm regards,<br/>Dani<br/>Dreams2Memories Travel, LLC</p>
</div>""",
    },
    21: {
        "subject": "Three weeks home — and your next adventure awaits",
        "body": """<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Dear [CLIENT],</p>
<p>Three weeks back from [DESTINATION] — we hope the memories are still vivid. We've been thinking about you.</p>
<p>If you had a moment to share a testimonial or review, it would mean so much to us and help other travelers discover the magic you experienced.</p>
<p>And whenever you're ready to start planning your next chapter, we'd be honored to craft it with you.</p>
<p>With gratitude,<br/>Dani<br/>Dreams2Memories Travel, LLC</p>
</div>""",
    },
    45: {
        "subject": "45 days later — ready for the next great adventure?",
        "body": """<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Dear [CLIENT],</p>
<p>Can you believe it's been 45 days since you returned from [DESTINATION]? Time flies when life is full.</p>
<p>We'd love to reconnect. Whether you're ready to start planning your next journey or simply want to share how your trip has stayed with you, we're here.</p>
<p>We have some exciting 2027 sailings that might be perfect for you.</p>
<p>With warm wishes,<br/>Dani<br/>Dreams2Memories Travel, LLC</p>
</div>""",
    },
}


def get_returned_clients() -> list[dict]:
    import yaml

    today = date.today()
    clients = []

    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        bookings = data.get("bookings", [])
        if isinstance(bookings, dict):
            bookings = [bookings]

        for booking in bookings:
            if not isinstance(booking, dict):
                continue
            ret_str = booking.get("return_date") or booking.get("disembark_date") or booking.get("end_date")
            if not ret_str:
                continue
            ret_date = parse_date(str(ret_str))
            if not ret_date:
                continue
            days_since = (today - ret_date).days
            if days_since < 1 or days_since > 50:
                continue

            destination = (
                booking.get("destination")
                or booking.get("region")
                or booking.get("ship", "your recent voyage")
            )
            clients.append({
                "client_id": data.get("client_id", fp.stem),
                "client_name": data.get("name", data.get("client_name", fp.stem)),
                "return_date": str(ret_date),
                "days_since_return": days_since,
                "destination": destination,
            })

    return clients


def draft_followup(client: dict, milestone: int) -> None:
    template = FOLLOWUP_TEMPLATES.get(milestone)
    if not template:
        return

    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        body = template["body"].replace("[CLIENT]", client["client_name"]).replace(
            "[DESTINATION]", client["destination"]
        )
        subject = template["subject"]

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[T+{milestone}d] {client['client_name']} — {subject}",
            body=body,
        )
        log.info(f"Draft T+{milestone} created for {client['client_name']}")
    except Exception as e:
        log.warning(f"Could not create draft for {client['client_name']}: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Post-trip follow-up check — {run_dt.date()}")

    clients = get_returned_clients()
    ledger = load_ledger()
    drafted = []

    for client in clients:
        days = client["days_since_return"]
        for milestone in FOLLOWUP_DAYS:
            if abs(days - milestone) <= FOLLOWUP_WINDOW:
                if not is_already_sent(ledger, client["client_id"], milestone):
                    draft_followup(client, milestone)
                    mark_sent(ledger, client["client_id"], milestone)
                    drafted.append({**client, "milestone": milestone})
                    break

    save_ledger(ledger)

    entry = {
        "ts": run_dt.isoformat(),
        "clients_checked": len(clients),
        "drafted": len(drafted),
        "detail": drafted,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if drafted:
        log.info(f"{len(drafted)} follow-up draft(s) created")
    else:
        log.info("No follow-ups due today")

    return 0


if __name__ == "__main__":
    sys.exit(main())
