#!/usr/bin/env python3
"""
hale_touchpoint_proposer.py
Dreams2Memories Travel — Thunderbird Wing

When a new booking is detected (or called manually), Hale generates a
proposed touchpoint schedule and posts it to claude_inbox.md for John's
approval. Once approved, John runs this script with --approve to write
the client JSON that the draft engine uses.

Usage:
  python3 hale_touchpoint_proposer.py --client kuklinski --propose
  python3 hale_touchpoint_proposer.py --client kuklinski --approve
  python3 hale_touchpoint_proposer.py --client kuklinski --status
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CLIENTS_DIR      = THUNDERBIRD_ROOT / "D2M" / "clients"
INBOX_FILE       = THUNDERBIRD_ROOT / "OpsCenter" / "claude_inbox.md"
TEMPLATE_DIR     = THUNDERBIRD_ROOT / "D2M" / "email_templates"

# ── Arc date computation rules ─────────────────────────────────────────────────
# All offsets relative to embarkation_date unless noted.
# Negative = days before embarkation. Positive = days after booking_date.

TIMELINE_OFFSETS = {
    "TP-1":  {"ref": "booking_date",     "offset_days": 2,    "label": "Setup & Protection"},
    "TP-2":  {"ref": "embarkation_date", "offset_days": -230, "label": "Research Phase"},
    "TP-3":  {"ref": "embarkation_date", "offset_days": -169, "label": "Flight Planning"},
    "TP-4":  {"ref": "embarkation_date", "offset_days": -142, "label": "Excursion Booking"},
    "TP-5":  {"ref": "embarkation_date", "offset_days": -77,  "label": "Final Preparation"},
    "TP-6":  {"ref": "embarkation_date", "offset_days": -3,   "label": "Embarkation Brief"},
}

ARC_OFFSETS = {
    "ARC4-A": {"ref": "embarkation_date", "offset_days": -216, "label": "Dining Preferences"},
    "ARC4-B": {"ref": "embarkation_date", "offset_days": -200, "label": "Dining Candidates"},
    "ARC1-A": {"ref": "embarkation_date", "offset_days": -169, "label": "Airfare+Hotel Search"},
    "ARC1-B": {"ref": "embarkation_date", "offset_days": -163, "label": "Airfare+Hotel Candidates"},
    "ARC1-C": {"ref": "event",            "offset_days": 0,    "label": "Airfare+Hotel Confirmed"},
    "ARC1-D": {"ref": "event",            "offset_days": 30,   "label": "Airfare+Hotel Check-In"},
    "ARC2-A": {"ref": "embarkation_date", "offset_days": -142, "label": "Excursion Preferences"},
    "ARC2-B": {"ref": "embarkation_date", "offset_days": -142, "label": "Excursion Candidates"},
    "ARC2-C": {"ref": "embarkation_date", "offset_days": -137, "label": "Excursions Confirmed"},
    "ARC2-D": {"ref": "embarkation_date", "offset_days": -107, "label": "Excursion Check-In"},
    "ARC3-A": {"ref": "embarkation_date", "offset_days": -77,  "label": "Transfer Preferences"},
    "ARC3-B": {"ref": "embarkation_date", "offset_days": -73,  "label": "Transfer Candidates"},
    "ARC3-C": {"ref": "event",            "offset_days": 0,    "label": "Transfers Confirmed"},
    "ARC3-D": {"ref": "event",            "offset_days": 30,   "label": "Transfer Check-In"},
    "ARC4-C": {"ref": "event",            "offset_days": 0,    "label": "Dining Confirmed"},
    "ARC4-D": {"ref": "event",            "offset_days": 30,   "label": "Dining Check-In"},
}

# ── Client profile loader ──────────────────────────────────────────────────────

def load_client_profile(client_id: str) -> dict:
    """
    Load a minimal client profile for schedule generation.
    Profile lives at CLIENTS_DIR/kuklinski_profile.json (separate from touchpoints JSON).
    """
    profile_path = CLIENTS_DIR / f"{client_id}_profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Client profile not found: {profile_path}\n"
            f"Create it with: booking_date, embarkation_date, client_name, client_email, cruise_line, ship, itinerary"
        )
    return json.loads(profile_path.read_text())


# ── Schedule computation ───────────────────────────────────────────────────────

def compute_proposed_schedule(profile: dict) -> list[dict]:
    """Compute all fixed-date touchpoints from profile dates."""
    booking_date     = date.fromisoformat(profile["booking_date"])
    embarkation_date = date.fromisoformat(profile["embarkation_date"])
    today            = date.today()
    proposed         = []

    all_offsets = {**TIMELINE_OFFSETS, **ARC_OFFSETS}

    for tp_id, rule in all_offsets.items():
        ref = rule["ref"]

        if ref == "event":
            trigger = None  # Event-driven — no fixed date
        elif ref == "booking_date":
            trigger = booking_date + timedelta(days=rule["offset_days"])
        elif ref == "embarkation_date":
            trigger = embarkation_date + timedelta(days=rule["offset_days"])
        else:
            trigger = None

        status = "pending"
        if trigger and trigger < today:
            status = "overdue"

        proposed.append({
            "id":            tp_id,
            "label":         rule["label"],
            "trigger_date":  trigger.isoformat() if trigger else None,
            "status":        status,
            "note":          "EVENT-DRIVEN — trigger manually" if trigger is None else "",
        })

    return proposed


# ── Inbox proposal writer ──────────────────────────────────────────────────────

def write_proposal_to_inbox(client_id: str, profile: dict, schedule: list[dict]):
    """Format proposed schedule as a readable inbox message for John."""
    client_name = profile.get("client_name", client_id)
    embark      = profile.get("embarkation_date")

    lines = [
        f"\n## 📅 HALE TOUCHPOINT PROPOSAL — {client_id.upper()} — {date.today().isoformat()}",
        f"**Client:** {client_name}  |  **Embarkation:** {embark}",
        f"**Ship:** {profile.get('ship', '?')}  |  **Itinerary:** {profile.get('itinerary', '?')}",
        "",
        "Review the proposed send dates below. To approve and write the schedule JSON:",
        f"  `python3 hale_touchpoint_proposer.py --client {client_id} --approve`",
        "",
        "To modify dates before approving, edit the profile JSON and re-run `--propose`.",
        "",
        "| ID | Label | Proposed Date | Status |",
        "|---|---|---|---|",
    ]

    for tp in schedule:
        date_str = tp["trigger_date"] or "EVENT-DRIVEN"
        flag     = "⚠️ OVERDUE" if tp["status"] == "overdue" else ""
        lines.append(f"| {tp['id']} | {tp['label']} | {date_str} | {flag} |")

    lines += [
        "",
        f"**Total touchpoints:** {len(schedule)}  |  "
        f"**Fixed-date:** {sum(1 for t in schedule if t['trigger_date'])}  |  "
        f"**Event-driven:** {sum(1 for t in schedule if not t['trigger_date'])}",
        "",
        "---",
    ]

    proposal_text = "\n".join(lines)

    if INBOX_FILE.exists():
        with open(INBOX_FILE, "a") as f:
            f.write(proposal_text)
        print(f"✅ Proposal written to {INBOX_FILE}")
    else:
        print(proposal_text)
        print(f"\n⚠️  Inbox file not found at {INBOX_FILE} — printed above instead")


# ── JSON writer (on approval) ──────────────────────────────────────────────────

def write_approved_json(client_id: str, profile: dict, schedule: list[dict]):
    """
    Write the approved touchpoint JSON to CLIENTS_DIR.
    Merges computed dates into the full touchpoint template structure.
    """
    # Load the full touchpoint template (Kuklinski JSON as the canonical template)
    template_path = CLIENTS_DIR / "kuklinski_touchpoints.json"
    if not template_path.exists():
        print(f"❌ Base template not found: {template_path}")
        sys.exit(1)

    base = json.loads(template_path.read_text())

    # Update profile fields
    base.update({
        "client_id":         client_id,
        "client_name":       profile.get("client_name"),
        "client_email":      profile.get("client_email"),
        "cruise_line":       profile.get("cruise_line"),
        "style_template":    profile.get("style_template", "VIKING"),
        "ship":              profile.get("ship"),
        "itinerary":         profile.get("itinerary"),
        "embarkation_date":  profile.get("embarkation_date"),
        "disembarkation_date": profile.get("disembarkation_date"),
        "booking_ids":       profile.get("booking_ids", []),
        "guests":            profile.get("guests"),
        "suites":            profile.get("suites"),
        "total_paid":        profile.get("total_paid"),
        "approved_by_john":  True,
        "approved_date":     date.today().isoformat(),
    })

    # Inject computed dates into touchpoints
    schedule_map = {tp["id"]: tp for tp in schedule}
    for tp in base["touchpoints"]:
        tp_id = tp["id"]
        if tp_id in schedule_map and schedule_map[tp_id]["trigger_date"]:
            tp["trigger_date"] = schedule_map[tp_id]["trigger_date"]
        tp["status"] = "pending"
        tp["sent_date"] = None

    out_path = CLIENTS_DIR / f"{client_id}_touchpoints.json"
    out_path.write_text(json.dumps(base, indent=2))
    print(f"✅ Approved touchpoint JSON written → {out_path}")


# ── Status reporter ────────────────────────────────────────────────────────────

def print_status(client_id: str):
    """Print current touchpoint status for a client."""
    tp_path = CLIENTS_DIR / f"{client_id}_touchpoints.json"
    if not tp_path.exists():
        print(f"No touchpoint file found for {client_id}")
        return

    data = json.loads(tp_path.read_text())
    today = date.today()
    print(f"\n📋 {data['client_name']} — {data['ship']} — {data['embarkation_date']}")
    print(f"{'─'*65}")
    print(f"{'ID':<10} {'Label':<35} {'Date':<12} {'Status'}")
    print(f"{'─'*65}")

    for tp in data["touchpoints"]:
        tp_id    = tp["id"]
        label    = tp["label"][:33]
        trigger  = tp.get("trigger_date") or "EVENT"
        status   = tp.get("status", "pending")

        # Flag overdue
        if trigger != "EVENT" and status == "pending":
            if date.fromisoformat(trigger) < today:
                status = "⚠️ OVERDUE"

        symbol = {"sent": "✅", "draft_created": "📝", "skipped": "⏭️"}.get(
            tp.get("status", ""), "⬜"
        )
        print(f"{tp_id:<10} {label:<35} {trigger:<12} {symbol} {status}")

    print(f"{'─'*65}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hale Touchpoint Proposer — generate and approve client schedules"
    )
    parser.add_argument("--client",  required=True, help="Client ID (e.g. kuklinski)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--propose",  action="store_true", help="Generate and post proposed schedule to inbox")
    group.add_argument("--approve",  action="store_true", help="Write approved schedule JSON")
    group.add_argument("--status",   action="store_true", help="Print current touchpoint status")
    args = parser.parse_args()

    if args.status:
        print_status(args.client)
        sys.exit(0)

    profile  = load_client_profile(args.client)
    schedule = compute_proposed_schedule(profile)

    if args.propose:
        write_proposal_to_inbox(args.client, profile, schedule)
        print(f"\nReview the proposal in your inbox, then run:")
        print(f"  python3 hale_touchpoint_proposer.py --client {args.client} --approve")

    elif args.approve:
        write_approved_json(args.client, profile, schedule)
        print(f"\nHale draft engine will now pick up {args.client} on its next daily run.")
        print(f"Check status anytime:")
        print(f"  python3 hale_touchpoint_proposer.py --client {args.client} --status")
