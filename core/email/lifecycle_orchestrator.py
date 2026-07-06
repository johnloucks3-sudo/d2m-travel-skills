#!/usr/bin/env python3
"""
Lifecycle Orchestrator — feeds the 35-touchpoint schedule into the staff
creative-chain workflow (A2 research -> A6 narrative -> A9 financial -> A3 voice).

Enforces the 2-week draft rule (draft complete 14 days before send) with the
insurance exception (7 days, TP 0.3 pre-existing-condition waiver window).

Input:  a phase assignment (from scripts/lifecycle_phase_assignment.py) plus
        the active touchpoints for that client.
Output: task cards queued to the owning role, written to
        OpsCenter/state/lifecycle_task_queue.json.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE_PATH = ROOT / "OpsCenter" / "state" / "lifecycle_task_queue.json"

STANDARD_DRAFT_RULE_DAYS = 14
INSURANCE_DRAFT_RULE_DAYS = 7
INSURANCE_TOUCHPOINT_IDS = {"TP 0.3"}

# Chain order for content_type == "email" (and proposal): every non-None owner
# in the touchpoint, in creative-chain sequence, ending with A3 (client voice).
CHAIN_ORDER = ["A2", "A6", "A9", "A3"]


def _draft_rule_days(touchpoint_id: str) -> int:
    return INSURANCE_DRAFT_RULE_DAYS if touchpoint_id in INSURANCE_TOUCHPOINT_IDS else STANDARD_DRAFT_RULE_DAYS


def _owners_in_chain_order(tp: dict) -> list[str]:
    named = {o.strip() for o in [tp.get("owner_primary")] + (tp.get("owner_secondary") or "").split(",") if o and o.strip()}
    ordered = [o for o in CHAIN_ORDER if o in named]
    # Any owner not in the standard chain (e.g. COS, Commander) still gets a card, appended.
    ordered += [o for o in named if o not in CHAIN_ORDER]
    return ordered


def build_task_cards(touchpoint: dict, send_date: date, client: str, booking_ref: str = "") -> dict:
    """Build the full set of task cards for a single touchpoint occurrence."""
    draft_days = _draft_rule_days(touchpoint["touchpoint_id"])
    draft_due = send_date - timedelta(days=draft_days)
    owners = _owners_in_chain_order(touchpoint)

    cards = []
    for i, owner in enumerate(owners):
        cards.append({
            "owner": owner,
            "sequence": i + 1,
            "of": len(owners),
            "action": f"{'Draft' if owner != 'A3' or i < len(owners) - 1 else 'Finalize'} {touchpoint['touchpoint_id']} ({touchpoint['content_type']})",
            "description": touchpoint["description"],
            "status": "queued",
        })

    return {
        "client": client,
        "booking_ref": booking_ref,
        "touchpoint_id": touchpoint["touchpoint_id"],
        "zone": touchpoint["zone"],
        "content_type": touchpoint["content_type"],
        "send_date": send_date.isoformat(),
        "draft_rule_days": draft_days,
        "draft_due": draft_due.isoformat(),
        "draft_rule_exception": touchpoint["touchpoint_id"] in INSURANCE_TOUCHPOINT_IDS,
        "chain": cards,
        "gate": "WF-17",
        "created_at": date.today().isoformat(),
    }


def queue_touchpoints(client: str, booking_ref: str, phase_assignment: dict) -> list[dict]:
    """
    Take a phase_assignment result (from lifecycle_phase_assignment.assign_phase,
    which includes resolved next_touchpoints with dates) and produce task cards
    for each, queued to the owning staff roles.
    """
    cards = []
    for tp_summary in phase_assignment.get("next_touchpoints", []):
        # tp_summary has touchpoint_id/date/owner_primary/content_type/description
        # (the compact form returned by next_touchpoints()) — rebuild a minimal
        # touchpoint dict adequate for chain-building.
        tp = {
            "touchpoint_id": tp_summary["touchpoint_id"],
            "zone": tp_summary["zone"],
            "content_type": tp_summary["content_type"],
            "description": tp_summary["description"],
            "owner_primary": tp_summary["owner_primary"],
            "owner_secondary": tp_summary.get("owner_secondary"),
        }
        send_date = date.fromisoformat(tp_summary["date"])
        cards.append(build_task_cards(tp, send_date, client, booking_ref))
    return cards


def _load_queue() -> list[dict]:
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH) as f:
            return json.load(f)
    return []


def _save_queue(queue: list[dict]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(queue, f, indent=2)
    tmp.replace(QUEUE_PATH)


def enqueue(client: str, booking_ref: str, phase_assignment: dict) -> list[dict]:
    """Compute task cards and append them (dedup by client+touchpoint_id+send_date) to the queue file."""
    new_cards = queue_touchpoints(client, booking_ref, phase_assignment)
    queue = _load_queue()
    existing_keys = {(c["client"], c["touchpoint_id"], c["send_date"]) for c in queue}
    added = []
    for card in new_cards:
        key = (card["client"], card["touchpoint_id"], card["send_date"])
        if key not in existing_keys:
            queue.append(card)
            existing_keys.add(key)
            added.append(card)
    _save_queue(queue)
    return added


# ---------------------------------------------------------------------------
# CLI / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    from lifecycle_phase_assignment import assign_phase  # noqa: E402

    import argparse
    parser = argparse.ArgumentParser(description="Lifecycle orchestrator")
    parser.add_argument("--test", action="store_true", help="Run built-in 3-client self-test")
    args = parser.parse_args()

    if args.test:
        today = date(2026, 7, 6)
        cases = [
            ("Kuklinski", "Viking 9593880", date(2026, 2, 7), date(2026, 3, 31), date(2026, 12, 17), date(2026, 12, 27)),
            ("McLeod", "Regent 2984034", date(2026, 1, 1), date(2026, 7, 22), date(2026, 12, 19), date(2026, 12, 29)),
            ("Furlow", "Regent 3071222", date(2025, 9, 10), date(2026, 4, 1), date(2026, 8, 29), date(2026, 9, 8)),
        ]
        for client, ref, booking, fpd, embark, disembark in cases:
            phase = assign_phase(booking, fpd, embark, disembark, today=today)
            added = enqueue(client, ref, phase)
            print(f"\n=== {client} ({ref}) — phase {phase['current_phase']} ===", file=sys.stderr)
            for card in added:
                exc = " [7-DAY EXCEPTION]" if card["draft_rule_exception"] else ""
                print(f"  {card['touchpoint_id']}: send {card['send_date']}, draft due {card['draft_due']}{exc}"
                      f" -> chain: {' -> '.join(c['owner'] for c in card['chain'])}", file=sys.stderr)
        print(f"\nQueue written to {QUEUE_PATH}", file=sys.stderr)
