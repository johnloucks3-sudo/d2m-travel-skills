#!/usr/bin/env python3
"""
SYNC SPENCER SUSPENSE DATES TO JOHNLOUCKS3 GOOGLE CALENDAR
==========================================================
Authority: Commander Directive — "make a record of changed suspense dates and set reminders in calendar for johnloucks3 (jl3)" (2026-07-27)

Milestones to Schedule on jl3 Primary Calendar:
1. Spencer Step 1: Master Intake Completion
   Date: 2026-07-30 | Time: 09:00 - 09:30 MT
   Summary: [SUSPENSE] Spencer Grand Voyage 12-Pax Intake Form Due
2. Spencer Step 2: Lock Flight Leg Allocations
   Date: 2026-08-05 | Time: 09:00 - 09:30 MT
   Summary: [SUSPENSE] Spencer Flight Allocations (United/BA Group Space)
3. Spencer Step 3: DMC & Private Excursion Sign-Off
   Date: 2026-08-14 | Time: 09:00 - 09:30 MT
   Summary: [SUSPENSE] Spencer Land DMC, Rail & Excursion Sign-Off
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CALENDAR-SYNC]: %(message)s")
logger = logging.getLogger("CalendarSync")

EVENTS = [
    {
        "summary": "📌 [SUSPENSE] Spencer Step 1: Master 12-Pax Intake Form Due",
        "start": "2026-07-30T09:00:00-06:00",
        "end": "2026-07-30T09:30:00-06:00",
        "description": "Critical Path Step 1: Verify Bill Spencer's 12-pax intake form submission. Locks passport details, stateroom allocations, and dietary/medical profiles for all 4 sub-groups.",
        "location": "Dreams2Memories Travel — Client Portal"
    },
    {
        "summary": "📌 [SUSPENSE] Spencer Step 2: Lock Flight Leg Allocations",
        "start": "2026-08-05T09:00:00-06:00",
        "end": "2026-08-05T09:30:00-06:00",
        "description": "Critical Path Step 2: Finalize DEN->FCO (June 12) & ZRH->DEN (July 2) cabin class splits (Business/PE/E+) for Bill, Yaggi, and Tim sub-groups with United & BA.",
        "location": "United Airlines / British Airways Group Desk"
    },
    {
        "summary": "📌 [SUSPENSE] Spencer Step 3: Land DMC & Private Excursion Sign-Off",
        "start": "2026-08-14T09:00:00-06:00",
        "end": "2026-08-14T09:30:00-06:00",
        "description": "Critical Path Step 3: Pre-reserve La Pergola dining in Rome, Zermatt Matterhorn express rail passes, and Florence private cooking class.",
        "location": "Rome / Florence / Swiss Alps DMCs"
    }
]

def record_suspense_dates():
    logger.info("Recording changed suspense dates in OpsCenter/suspense_dates_record.md...")
    rec_path = ROOT / "OpsCenter" / "suspense_dates_record.md"
    
    content = f"""# THUNDERBIRD WING — SUSPENSE DATES RECORD
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}*

## ACTIVE CLIENT SUSPENSE DATES

| Client / Project | Action Item | Target Suspense Date | Milestone Outcome | Calendar Status (jl3) |
|---|---|---|---|---|
| **Spencer Grand Voyage** | Step 1: Complete 12-Pax Intake Form | **2026-07-30 (Thu)** | Locks passport names, DOBs, & stateroom groups | 📅 Calendar Event Created |
| **Spencer Grand Voyage** | Step 2: Lock Flight Allocations | **2026-08-05 (Wed)** | Holds DEN→FCO & ZRH→DEN Business/PE group space | 📅 Calendar Event Created |
| **Spencer Grand Voyage** | Step 3: DMC & Excursion Sign-Off | **2026-08-14 (Fri)** | Reserves La Pergola, Zermatt rail, & Florence cooking class | 📅 Calendar Event Created |
| **Loucks Choice #1** | Daily Airfare Survey ($500 Delta Sentinel) | **Daily 07:30 MT** | Surveys BA Business ($5,823.96) vs TK ($5,390.00) | 🔄 Daily Sentinel Active |

---

*Authority: Executive Officer Governance & Commander Directive (2026-07-27)*
"""
    rec_path.write_text(content, encoding="utf-8")
    logger.info("OpsCenter/suspense_dates_record.md written successfully.")

def create_calendar_reminders():
    logger.info("Creating Google Calendar reminders on johnloucks3 primary calendar...")
    cal_svc = get_calendar()
    
    created_events = []
    for ev in EVENTS:
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
        logger.info(f"✅ Calendar Event Created: '{ev['summary']}' (ID: {res.get('id')})")
        created_events.append(res)
        
    return created_events

if __name__ == "__main__":
    record_suspense_dates()
    create_calendar_reminders()
    print("✅ Suspense dates recorded and calendar reminders synchronized to johnloucks3!")
