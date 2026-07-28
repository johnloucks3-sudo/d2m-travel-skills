#!/usr/bin/env python3
"""
Delete Specific Drafts from Commander Gmail Account
===================================================
Targets draft numbers 10, 9, 8, 7, 6, 5, 1 from the active list:
1. r2417589787283613430 (Index 1) - Previous SSS Draft
2. r4395081059138232238 (Index 5) - Ron Westbrook
3. r-761577215575796200 (Index 6) - Amy Darrow
4. r4681709543589864382 (Index 7) - Heidi & Larry Nichols
5. r-5417723896558468424 (Index 8) - Al & Amy Ely
6. r-6771050604179169663 (Index 9) - Missy & John Furlow
7. r-7322300848616065868 (Index 10) - Melissa & John Furlow
"""

import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.thunderbird_google_auth import get_gmail

TARGET_DRAFT_IDS = [
    "r2417589787283613430",
    "r4395081059138232238",
    "r-761577215575796200",
    "r4681709543589864382",
    "r-5417723896558468424",
    "r-6771050604179169663",
    "r-7322300848616065868"
]

def purge_drafts():
    svc = get_gmail()
    deleted_count = 0
    for draft_id in TARGET_DRAFT_IDS:
        try:
            print(f"Deleting Draft ID: {draft_id}...")
            svc.users().drafts().delete(userId='me', id=draft_id).execute()
            deleted_count += 1
            print(f"Successfully deleted {draft_id}.")
        except Exception as e:
            print(f"Error deleting draft {draft_id}: {e}")
            
    print(f"\nPurge complete: Deleted {deleted_count} specified drafts.")

if __name__ == "__main__":
    purge_drafts()
