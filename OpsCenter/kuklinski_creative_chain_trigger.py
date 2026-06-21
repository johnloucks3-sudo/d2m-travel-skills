#!/usr/bin/env python3
"""
Kuklinski Jul 15 Creative Chain Trigger
========================================

Automatically initiates the Kuklinski validation email creative chain on Jul 15, 2026.
- Luna (A6) writes narrative/voice
- Harlan (A9) verifies financial data
- Dani (A3) finalizes client voice

Dispatches to OpenCode (Hale-OC) without Commander intervention.

Trigger date: 2026-07-15 (excursion booking window opens)
Status: One-time execution (fires once on date, idempotent thereafter)
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
THUNDERBIRD_PATH = Path("/home/john/Thunderbird")
HALE_STATE_PATH = THUNDERBIRD_PATH / "hale_state.json"
OPENCODE_INBOX_PATH = THUNDERBIRD_PATH / "OpsCenter/collaboration/opencode_inbox.md"
OUTPUT_LOG = THUNDERBIRD_PATH / "OpsCenter/logs/kuklinski_trigger.log"

def log_event(msg: str):
    """Log trigger events with timestamp."""
    ts = datetime.utcnow().isoformat()
    output_log = OUTPUT_LOG
    output_log.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")

def check_trigger_date() -> bool:
    """Check if today is Jul 15, 2026 or later."""
    today = datetime.utcnow().date()
    trigger_date = datetime(2026, 7, 15).date()
    return today >= trigger_date

def check_already_triggered() -> bool:
    """Check if creative chain was already initiated (idempotent)."""
    state_file = HALE_STATE_PATH

    if not state_file.exists():
        log_event("hale_state.json not found — cannot check trigger state")
        return False

    try:
        with open(state_file) as f:
            state = json.load(f)

        # Check if there's already an active mission for Kuklinski validation email
        if "open_tasks" in state:
            for task in state["open_tasks"]:
                if task.get("id") == "MISSION-191":
                    status = task.get("status", "").lower()
                    if status not in ["hold_until_2026-07-15", "complete"]:
                        log_event(f"MISSION-191 already in progress (status={status}) — skipping trigger")
                        return True

        return False
    except Exception as e:
        log_event(f"Error checking trigger state: {e}")
        return False

def create_opencode_task() -> str:
    """Create task entry in OpenCode inbox for creative chain."""
    task_id = "KUKLINSKI-VALIDATION-CHAIN-20260715"
    inbox_path = OPENCODE_INBOX_PATH
    inbox_path.parent.mkdir(parents=True, exist_ok=True)

    task_entry = f"""---
## TASK: {task_id}
status: DISPATCHED
created_at: {datetime.utcnow().isoformat()}Z
from: HALE-CC (Automated Trigger — kuklinski_creative_chain_trigger.py)
to: OpenCode/Personas (Luna→Harlan→Dani)
priority: P0
client: Kuklinski (Kyle, Roger, Joshua)
booking: 9593880 / 9593873 / 9595029 (Viking Mars Panama Dec 2026)
mission_ref: MISSION-191 (REACTIVATE on Jul 15)

task_summary: |
  KUKLINSKI VALIDATION EMAIL — CREATIVE CHAIN REACTIVATION

  **STANDING ORDER:** Commander 2026-06-04, confirmed 2026-06-12
  "HOLD ALL Kuklinski emails until 2026-07-15 (excursion booking window opens)"

  **REACTIVATION SEQUENCE (Jul 15):**
  1. Stage validation email → insurance email → Josh guest form in that order
  2. Validation email leads the chain

  **CREATIVE CHAIN (Standard):**
  - A6 Luna: Port narratives, dining copy, emotional layer, wave of ship narrative
  - A9 Harlan: Financial verification (FPD PAID $21,244, confirm portal balance)
  - A3 Dani: Final client voice, tone lock

  **CLIENT CONTEXT:**
  - 3 couples, AI-fluent (Kyle knows D2M uses AI)
  - FPD PAID Mar 27 2026 ($21,244 charged)
  - All 6 guests have portal accounts
  - Josh guest form still missing (deferred until now)
  - No flights/hotel/transfers booked yet (search windows: air open now, hotel 3+3 open Jun 17)

  **DELIVERABLES:**
  1. Validation email draft (with stationery, ready for WF-17)
  2. Insurance/pre-existing waiver email draft
  3. Josh guest form reminder email draft

  **NEXT:** After creative chain completes:
  - Push validation email to Gmail drafts (label: THUNDERBIRD-Commander-Review)
  - Surface to Commander for WF-17 approval + send
  - Trigger insurance email (A9→A3)
  - Trigger Josh guest form email (A9→A3)

  **SYSTEM NOTES:**
  - Automated trigger (no Commander intervention required)
  - Mission 191 status: change from HOLD_UNTIL_2026-07-15 to ACTIVE once this entry processes
  - Idempotent: if chain already started, abort (check mission 191 status first)
  - Log location: OpsCenter/logs/kuklinski_trigger.log

---
"""

    try:
        with open(inbox_path, "a") as f:
            f.write(task_entry + "\n")
        log_event(f"OpenCode task created: {task_id}")
        return task_id
    except Exception as e:
        log_event(f"ERROR creating OpenCode task: {e}")
        raise

def update_hale_state(task_id: str):
    """Update hale_state.json to mark MISSION-191 as ACTIVE."""
    state_file = HALE_STATE_PATH

    if not state_file.exists():
        log_event("hale_state.json not found — cannot update state")
        return

    try:
        with open(state_file) as f:
            state = json.load(f)

        # Update MISSION-191 status
        if "open_tasks" in state:
            for task in state["open_tasks"]:
                if task.get("id") == "MISSION-191":
                    old_status = task.get("status")
                    task["status"] = "active"
                    task["reactivated_at"] = datetime.utcnow().isoformat()
                    task["trigger_task_id"] = task_id
                    log_event(f"MISSION-191 status changed: {old_status} → active")
                    break

        # Write updated state
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        log_event("hale_state.json updated successfully")
    except Exception as e:
        log_event(f"ERROR updating hale_state.json: {e}")
        raise

def add_deferred_alert():
    """Add deferred alert to hale_state.json for tracking."""
    state_file = HALE_STATE_PATH

    if not state_file.exists():
        return

    try:
        with open(state_file) as f:
            state = json.load(f)

        alert = {
            "id": "KUKLINSKI-VALIDATION-CHAIN-TRIGGERED",
            "trigger_date": "2026-07-15",
            "priority": "P0",
            "message": "Kuklinski validation email creative chain REACTIVATED. Excursion booking window now open. Validation email leads; followed by insurance email and Josh guest form.",
            "client": "Kuklinski (Kyle, Roger, Joshua)",
            "bookings": ["9593880", "9593873", "9595029"],
            "condition": "date>=2026-07-15 AND mission_191_active",
            "condition_type": "date_and_mission_status",
            "status": "triggered"
        }

        if "deferred_alerts" not in state:
            state["deferred_alerts"] = []

        # Don't duplicate if already present
        if not any(a.get("id") == alert["id"] for a in state["deferred_alerts"]):
            state["deferred_alerts"].append(alert)

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            log_event(f"Deferred alert added: {alert['id']}")
    except Exception as e:
        log_event(f"WARNING: Could not add deferred alert: {e}")

def main():
    """Main trigger logic."""
    log_event("=== KUKLINSKI CREATIVE CHAIN TRIGGER STARTED ===")

    # Check if today is the trigger date
    if not check_trigger_date():
        log_event("Trigger date not reached yet (before 2026-07-15) — exiting")
        return

    log_event("Trigger date reached (2026-07-15 or later)")

    # Check if already triggered (idempotent)
    if check_already_triggered():
        log_event("Creative chain already triggered — exiting (idempotent check)")
        return

    try:
        # Create OpenCode task
        task_id = create_opencode_task()
        log_event(f"OpenCode task dispatched: {task_id}")

        # Update state files
        update_hale_state(task_id)
        add_deferred_alert()

        log_event("=== TRIGGER COMPLETE ===")
        log_event(f"Kuklinski validation email creative chain now active")
        log_event(f"OpenCode will process: Luna → Harlan → Dani")
        log_event(f"Task reference: {task_id}")

    except Exception as e:
        log_event(f"FATAL ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
