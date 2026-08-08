#!/usr/bin/env python3
"""Booking-calendar-triggered port/excursion intel freshness check.

Autonomy item #18 (2026-08-07 War Room). Gap closed: nobody currently
triggers port/excursion intel research off a booking's calendar — it only
happens if a staffer remembers to ask. This scans anchor-date windows for
bookings entering the pre-trip planning zone (E-120 to E-90, matching the
existing "client_care"/"documents" anchor labels in
core/scheduling/thunderbird_anchor_dates.py) and flags any booking that
enters that window without a port_data file in dossiers/port_data/.

Scope note: this is detection + notify, not auto-generated port research.
Reliable per-booking port lists live in dossiers (freeform markdown) or
TESS, not in the anchor engine's EARA row (client/supplier/dates only).
Auto-extracting ports and calling get_port_city_intel per port is a real
next step but needs dossier-format parsing or a TESS itinerary read this
script does not attempt — flagging that as a scoped-out extension rather
than silently guessing at ports.

Runs weekly via d2m-port-intel-freshness.timer.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD))

PORT_DATA_DIR = THUNDERBIRD / "dossiers" / "port_data"
TRIGGER_WINDOW_LABELS = (
    "E-120: Pre-trip call / planning session",
    "E-90: All docs confirmed, ancillary bookings locked",
)
FRESHNESS_DAYS = 180


def _client_key(booking_label: str) -> str:
    """First token of 'Client Name | Supplier CONF' label, normalized for fuzzy match."""
    client = booking_label.split("|")[0].strip()
    return re.sub(r"[^a-z]", "", client.lower())


def _has_fresh_port_data(client_key: str) -> bool:
    if not PORT_DATA_DIR.exists():
        return False
    cutoff = date.today() - timedelta(days=FRESHNESS_DAYS)
    for f in PORT_DATA_DIR.glob("*_ports.md"):
        fname_key = re.sub(r"[^a-z]", "", f.stem.split("_")[0].lower())
        if fname_key and fname_key in client_key:
            mtime = date.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                return True
    return False


def run() -> dict:
    from core.scheduling.thunderbird_anchor_dates import (
        compute_all_known_anchors, scan_all_bookings_due,
    )

    all_anchors = compute_all_known_anchors()
    report = scan_all_bookings_due(all_anchors)

    flagged = []
    checked = set()
    for bucket in ("due_today", "due_this_week", "due_next_week", "upcoming_14_days"):
        for entry in report.get(bucket, []):
            if entry.get("label") not in TRIGGER_WINDOW_LABELS:
                continue
            booking_label = entry.get("booking_label", "")
            if booking_label in checked:
                continue
            checked.add(booking_label)
            client_key = _client_key(booking_label)
            if not client_key or _has_fresh_port_data(client_key):
                continue
            flagged.append({
                "booking_label": booking_label,
                "anchor": entry["label"],
                "anchor_date": entry["date"],
            })

    return {"scan_date": report["scan_date"], "checked": len(checked), "flagged": flagged}


def notify_flags(result: dict) -> None:
    if not result["flagged"]:
        return
    from core.comms.commander_channel import notify

    lines = [
        f"Port/excursion intel freshness check — {result['scan_date']}",
        f"{len(result['flagged'])} booking(s) entering pre-trip planning window with no port_data on file (>{FRESHNESS_DAYS}d or missing):",
        "",
    ]
    for f in result["flagged"]:
        lines.append(f"- {f['booking_label']} — anchor: {f['anchor']} ({f['anchor_date']})")
    lines.append("")
    lines.append("Route to Dembe (A2) for port/excursion research — no port list available from booking-calendar data alone.")

    notify(
        kind="ops",
        title=f"Port Intel Gap — {len(result['flagged'])} booking(s) need research",
        body_md="\n".join(lines),
        urgency="WINDOW",
        source="port_intel_freshness_trigger.py",
    )


def main():
    result = run()
    notify_flags(result)
    print(f"Checked {result['checked']} bookings in trigger window, flagged {len(result['flagged'])}")
    for f in result["flagged"]:
        print(f"  - {f['booking_label']} ({f['anchor']})")


if __name__ == "__main__":
    main()
