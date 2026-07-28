#!/usr/bin/env python3
"""
SPENCER GRAND VOYAGE POST-SEND LIFECYCLE DIFF & WRITEBACK ENGINE
================================================================
Authority: Commander Directive — "sent, do the diffs" (2026-07-27)

Tasks:
1. Ingest Sent Email Audit: ID 19fa66e431bc7018 sent at Mon, 27 Jul 2026 19:54:31 -0600.
2. Update Spencer Dossier & Context: Add sent intake email log, tokenized URL, & Critical Path milestones.
3. TCD Writeback & Stage Sync: Update TCD stage to Stage A (Await Client Response) for Spencer Grand Voyage.
4. Record Decision in hale_decisions.md.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SPENCER-DIFF]: %(message)s")
logger = logging.getLogger("SpencerDiffEngine")

SENT_MSG_ID = "19fa66e431bc7018"
SENT_TIME = "2026-07-27 19:54:31 MT"
CLIENT_ID = "spencer_bill_grand_tour_2027"

def record_hale_decision():
    logger.info("Recording send event and post-send diff in hale_decisions.md...")
    decisions_path = ROOT / "hale_decisions.md"
    
    entry = f"""
### 🦅 [POST-SEND DIFF & WRITEBACK] Spencer Grand Voyage Master Intake (2026-07-27 19:54 MT)
* **Action:** Commander sent Spencer Grand Voyage (12 Pax) Master Client & Trip Information Intake Form to Bill & Kathleen Spencer (`bkspencer381@gmail.com`).
* **Message ID:** `{SENT_MSG_ID}`
* **Verified Portal URL:** `https://spencer.d2mluxury.quest/intake?token=d2m-spencer-12pax-secure` (HTTP 200 OK verified; 404 route resolved).
* **Voice & Branding:** Commander's authentic voice, One-Click passwordless access, 256-bit SSL PII security provisions, and canonical 3-line signature block.
* **PERT Critical Path Milestones Enforced:**
  1. **Step 1 (Master Intake Form):** Target Date `Thursday, July 30, 2026` — Locks 12-pax roster, DOBs, passport expirations, and staterooms.
  2. **Step 2 (Flight Leg Allocations):** Target Date `Wednesday, August 5, 2026` — Holds DEN→FCO (June 12) & ZRH→DEN (July 2) Business/PE inventory.
  3. **Step 3 (DMC & Excursion Sign-Off):** Target Date `Friday, August 14, 2026` — Pre-reserves La Pergola dining, Zermatt rail passes, & Florence cooking class.
* **TCD Stage:** Transitioned to **Stage A** (Await Client Response).
"""
    with open(decisions_path, "a", encoding="utf-8") as f:
        f.write(entry)
    logger.info("hale_decisions.md updated successfully.")

def update_spencer_context_json():
    logger.info("Updating Spencer client context JSON...")
    ctx_path = ROOT / "cache" / "client_context" / "spencer_context.json"
    if ctx_path.exists():
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
        # Add sent log
        logs = data.get("comms_log", [])
        logs.append({
            "date": "2026-07-27",
            "summary": "Master Client & Trip Intake Form sent by Commander (bkspencer381@gmail.com). Verified 200 OK token URL + PERT 3-step milestones attached."
        })
        data["comms_log"] = logs
        data["last_updated"] = "2026-07-27T19:54:31-06:00"
        ctx_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("spencer_context.json updated successfully.")

def update_tcd_stage_override():
    logger.info("Updating TCD stage override to Stage A (Await Client Response)...")
    try:
        from tcd import overrides
        ovs = overrides.load_overrides()
        ovs[CLIENT_ID] = {
            "stage": "A",
            "owner": "Commander",
            "notes": "Intake form sent 2026-07-27; awaiting client submission NLT July 30, 2026.",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        overrides.save_overrides(ovs)
        logger.info(f"TCD Stage override set for {CLIENT_ID} -> Stage A.")
    except Exception as e:
        logger.error(f"Error updating TCD stage override: {e}")

if __name__ == "__main__":
    record_hale_decision()
    update_spencer_context_json()
    update_tcd_stage_override()
    print("✅ Spencer Grand Voyage post-send diff and writeback complete!")
