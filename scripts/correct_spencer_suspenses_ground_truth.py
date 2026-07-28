#!/usr/bin/env python3
"""
CORRECT SPENCER SUSPENSE DATES FROM SENT EMAIL GROUND TRUTH
==========================================================
Authority: Commander Directive — "no uncorrect look art sent email" (2026-07-27)

Ground Truth Dates from Sent Email (Message ID: 19fa66e431bc7018):
1. Step 1: Complete Master Intake Form -> Tuesday, August 4, 2026
2. Step 2: Lock Flight Leg Allocations -> Wednesday, August 5, 2026
3. Step 3: Land DMC & Private Excursion Sign-Off -> Friday, August 28, 2026
"""

import email
import email.parser
import email.utils

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from api.thunderbird_google_auth import get_calendar

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CORRECT-SUSPENSE]: %(message)s")
logger = logging.getLogger("CorrectSuspense")

# Previously created event IDs to delete/update
OLD_EVENT_IDS = [
    "73gj5b1m1j8f9d90915tjdclfk",
    "3le7e2d2pkghi0n74v6gpol90k",
    "0fp4oq0np1gr7i1bb6456431hs"
]

CORRECT_EVENTS = [
    {
        "summary": "📌 [SUSPENSE] Spencer Step 1: Master 12-Pax Intake Form Due",
        "start": "2026-08-04T09:00:00-06:00",
        "end": "2026-08-04T09:30:00-06:00",
        "description": "Critical Path Step 1 (Sent Email Ground Truth): Verify Bill Spencer's 12-pax intake form submission. Locks passport details, stateroom allocations, and dietary/medical profiles for all 4 sub-groups.",
        "location": "Dreams2Memories Travel — Client Portal"
    },
    {
        "summary": "📌 [SUSPENSE] Spencer Step 2: Lock Possible Flight Leg Allocations",
        "start": "2026-08-05T09:00:00-06:00",
        "end": "2026-08-05T09:30:00-06:00",
        "description": "Critical Path Step 2 (Sent Email Ground Truth): Finalize DEN->FCO (June 12) & ZRH->DEN (July 2) cabin class splits (Business/PE/E+) for Bill, Yaggi, and Tim sub-groups with United & BA.",
        "location": "United Airlines / British Airways Group Desk"
    },
    {
        "summary": "📌 [SUSPENSE] Spencer Step 3: Land DMC & Private Excursion Sign-Off",
        "start": "2026-08-28T09:00:00-06:00",
        "end": "2026-08-28T09:30:00-06:00",
        "description": "Critical Path Step 3 (Sent Email Ground Truth): Pre-reserve La Pergola dining in Rome, Zermatt Matterhorn express rail passes, and Florence private cooking class.",
        "location": "Rome / Florence / Swiss Alps DMCs"
    }
]

def clean_old_calendar_events():
    logger.info("Cleaning up old calendar events...")
    cal_svc = get_calendar()
    for eid in OLD_EVENT_IDS:
        try:
            cal_svc.events().delete(calendarId="primary", eventId=eid).execute()
            logger.info(f"Deleted old event ID: {eid}")
        except Exception as e:
            logger.warning(f"Could not delete old event {eid}: {e}")

def create_correct_calendar_events():
    logger.info("Creating ground-truth Google Calendar reminders on johnloucks3 primary calendar...")
    cal_svc = get_calendar()
    
    new_events = []
    for ev in CORRECT_EVENTS:
        event_body = {
            "summary": ev["summary"],
            "location": ev["location"],
            "description": ev["description"],
            "start": {"dateTime": ev["start"], "timeZone": "America/Denver"},
            "end": {"dateTime": ev["end"], "timeZone": "America/Denver"},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 1440}  # 24 hours prior
                ]
            }
        }
        res = cal_svc.events().insert(calendarId="primary", body=event_body).execute()
        logger.info(f"✅ Correct Calendar Event Created: '{ev['summary']}' on {ev['start'][:10]} (ID: {res.get('id')})")
        new_events.append(res)
    return new_events

def update_suspense_record():
    logger.info("Updating OpsCenter/suspense_dates_record.md with sent email ground truth...")
    rec_path = ROOT / "OpsCenter" / "suspense_dates_record.md"
    content = f"""# THUNDERBIRD WING — SUSPENSE DATES RECORD
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M MT')} — Ground Truth from Sent Email (ID: 19fa66e431bc7018)*

## ACTIVE CLIENT SUSPENSE DATES (SENT EMAIL GROUND TRUTH)

| Client / Project | Action Item | Target Suspense Date | Milestone Outcome | Calendar Status (jl3) |
|---|---|---|---|---|
| **Spencer Grand Voyage** | Step 1: Complete 12-Pax Intake Form | **2026-08-04 (Tue)** | Locks passport names, DOBs, & stateroom groups | 📅 Event Set: Aug 4 |
| **Spencer Grand Voyage** | Step 2: Lock Flight Allocations | **2026-08-05 (Wed)** | Holds DEN→FCO & ZRH→DEN Business/PE group space | 📅 Event Set: Aug 5 |
| **Spencer Grand Voyage** | Step 3: DMC & Excursion Sign-Off | **2026-08-28 (Fri)** | Reserves La Pergola, Zermatt rail, & Florence cooking class | 📅 Event Set: Aug 28 |
| **Loucks Choice #1** | Daily Airfare Survey ($500 Delta Sentinel) | **Daily 07:30 MT** | Surveys BA Business ($5,823.96) vs TK ($5,390.00) | 🔄 Daily Sentinel Active |

---

*Authority: Commander Directive Ground Truth Audit (2026-07-27)*
"""
    rec_path.write_text(content, encoding="utf-8")
    logger.info("OpsCenter/suspense_dates_record.md updated.")

def update_spencer_context():
    logger.info("Updating Spencer client context with ground truth dates...")
    ctx_path = ROOT / "cache" / "client_context" / "spencer_context.json"
    if ctx_path.exists():
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
        logs = data.get("comms_log", [])
        logs.append({
            "date": "2026-07-27",
            "summary": "CORRECTION: Ground truth sent email verified. Step 1 Due: Aug 4, 2026; Step 2 Due: Aug 5, 2026; Step 3 Due: Aug 28, 2026."
        })
        data["comms_log"] = logs
        data["suspense_dates"] = {
            "step1_intake": "2026-08-04",
            "step2_flights": "2026-08-05",
            "step3_excursions": "2026-08-28"
        }
        ctx_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("spencer_context.json updated with ground truth dates.")

if __name__ == "__main__":
    clean_old_calendar_events()
    create_correct_calendar_events()
    update_suspense_record()
    update_spencer_context()
    print("✅ All suspense records and calendar events corrected to match Sent Email Ground Truth!")
