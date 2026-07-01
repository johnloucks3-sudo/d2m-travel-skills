#!/usr/bin/env python3
"""
Booking Survey Generator — Preferences survey email for newly confirmed bookings.
Dreams2Memories Travel, LLC | scripts/booking_survey_generator.py

For each newly confirmed booking (active status + departure set, not yet surveyed),
stages a preferences survey draft to johnloucks3@gmail.com via d2m_email_builder.

State file: OpsCenter/state/booking_survey_state.json
Usage:
    python3 scripts/booking_survey_generator.py
    python3 scripts/booking_survey_generator.py --dry-run
    python3 scripts/booking_survey_generator.py --force
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD))

from core.booking.thunderbird_tp_scheduler import scan_dossiers
from scripts.d2m_email_builder import build_email_html, stage_draft

STATE_PATH = THUNDERBIRD / "OpsCenter" / "state" / "booking_survey_state.json"
DRAFTS_DIR = THUNDERBIRD / "drafts"
FORM_URL = "https://docs.google.com/forms/d/1Ni_MKR8gqfpVVlaNt3RUBfDFd4hcy4U5SSTse4RUpo8/viewform"


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def build_body_html(client_name: str, departure_date: str) -> str:
    return f"""<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:16px;">Dear {client_name},</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">Your voyage is confirmed — congratulations! To help us personalize every detail of your experience, please take a few minutes to share your preferences.</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">This short questionnaire covers dining preferences, accessibility needs, special occasions, and more:</p>
<div style="text-align:center;margin:24px 0;">
  <a href="{FORM_URL}"
     style="background:#4a90d9;color:#ffffff;padding:14px 28px;border-radius:6px;font-family:Georgia,serif;font-size:16px;text-decoration:none;display:inline-block;">
    Share Your Preferences →
  </a>
</div>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;font-style:italic;">Link: {FORM_URL}</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">Your voyage departs {departure_date}. We'll use your answers to craft a personalized experience from the moment you board.</p>"""


def main():
    parser = argparse.ArgumentParser(description="Stage preferences survey drafts for newly confirmed bookings")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be staged without staging")
    parser.add_argument("--force", action="store_true", help="Re-process all confirmed bookings regardless of prior state")
    args = parser.parse_args()

    state = load_state()
    entries = state.get("entries", {})

    records = scan_dossiers()

    confirmed = [
        rec for rec in records
        if rec.status == "active" and rec.departure is not None
    ]

    if args.force:
        new_bookings = confirmed
    else:
        new_bookings = [rec for rec in confirmed if str(rec.path) not in entries]

    evaluated = len(confirmed)
    staged_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for rec in new_bookings:
        departure_str = rec.departure.strftime("%B %-d, %Y")
        subject = f"Your Voyage Preferences — {rec.client}"
        body_html = build_body_html(rec.client, departure_str)
        full_html = build_email_html(body_html)

        ts = int(time.time())
        output_path = DRAFTS_DIR / f"survey_{rec.client.replace(' ', '_')}_{ts}.html"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

        if args.dry_run:
            print(f"[DRY RUN] Would stage survey for {rec.client} (departs {departure_str})")
        else:
            success = stage_draft(full_html, "johnloucks3@gmail.com", subject, output_path)
            if success:
                entries[str(rec.path)] = {
                    "client": rec.client,
                    "staged_at": now_iso,
                    "departure": str(rec.departure),
                }
                staged_count += 1
                print(f"Staged survey draft: {rec.client} → {output_path.name}")
            else:
                print(f"ERROR: Draft staging failed for {rec.client}", file=sys.stderr)

    state["last_run"] = now_iso
    state["evaluated"] = evaluated
    state["staged"] = state.get("staged", 0) + staged_count
    state["entries"] = entries

    if not args.dry_run:
        save_state(state)
        print(f"\nDone. evaluated={evaluated}, staged_this_run={staged_count}, total_staged={state['staged']}")
    else:
        print(f"\n[DRY RUN] evaluated={evaluated}, would_stage={len(new_bookings)}")


if __name__ == "__main__":
    main()
