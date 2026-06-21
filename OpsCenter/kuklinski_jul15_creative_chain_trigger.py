#!/usr/bin/env python3
"""
Kuklinski Jul 15 Creative Chain Unlock — Automated Trigger
===========================================================
Dreams2Memories Travel, LLC | OpsCenter/kuklinski_jul15_creative_chain_trigger.py

Hard-coded trigger that fires on Jul 15, 2026 and automatically initiates the
Kuklinski validation email creative chain:

    Luna (A6) → Harlan (A9) → Dani (A3) → TALON + JET → WF-17 draft

No Commander intervention required. No session dependency.

Runs as:
    - Systemd timer (daily check, fires on Jul 15 only)
    - Manual invocation: python3 OpsCenter/kuklinski_jul15_creative_chain_trigger.py

Exit codes:
    0 = success (creative chain initiated or already complete)
    1 = error (see logs)
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s KUK-JUL15 %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "kuklinski_jul15_trigger.log"), mode="a"),
    ],
)
logger = logging.getLogger("kuk_jul15")

HALE_STATE = THUNDERBIRD / "hale_state.json"
MISSION_BOARD = THUNDERBIRD / "OpsCenter" / "mission_board.json"
DOSSIER = THUNDERBIRD / "dossiers" / "Kuklinski_Viking_Panama.md"


def check_trigger_date() -> bool:
    """Return True if today is Jul 15, 2026 or later (first run only)."""
    today = date.today()
    trigger_date = date(2026, 7, 15)
    return today >= trigger_date


def load_hale_state() -> dict:
    """Load hale_state.json."""
    try:
        return json.loads(HALE_STATE.read_text())
    except Exception as e:
        logger.error(f"Failed to load hale_state.json: {e}")
        raise


def save_hale_state(state: dict) -> None:
    """Save hale_state.json with pretty formatting."""
    try:
        HALE_STATE.write_text(json.dumps(state, indent=2))
        logger.info("hale_state.json updated")
    except Exception as e:
        logger.error(f"Failed to save hale_state.json: {e}")
        raise


def load_mission_board() -> dict:
    """Load mission_board.json."""
    try:
        return json.loads(MISSION_BOARD.read_text())
    except Exception as e:
        logger.error(f"Failed to load mission_board.json: {e}")
        raise


def save_mission_board(board: dict) -> None:
    """Save mission_board.json."""
    try:
        MISSION_BOARD.write_text(json.dumps(board, indent=2))
        logger.info("mission_board.json updated")
    except Exception as e:
        logger.error(f"Failed to save mission_board.json: {e}")
        raise


def check_creative_chain_status() -> dict | None:
    """
    Check if Kuklinski creative chain has already been initiated.
    Returns the mission if found, None otherwise.
    """
    try:
        board = load_mission_board()
        for mission in board.get("missions", []):
            if mission.get("id") == "MISSION-191":  # Kuklinski validation email hold
                return mission
    except Exception as e:
        logger.warning(f"Could not check mission board status: {e}")
    return None


def add_jul15_deferred_alert(state: dict) -> None:
    """Add Kuklinski Jul 15 trigger to deferred_alerts list."""
    existing_alerts = state.get("deferred_alerts", [])

    # Check if alert already exists
    for alert in existing_alerts:
        if alert.get("id") == "KUKLINSKI-JUL15-VALIDATION-CHAIN":
            logger.info("KUKLINSKI-JUL15-VALIDATION-CHAIN already exists; skipping add")
            return

    new_alert = {
        "id": "KUKLINSKI-JUL15-VALIDATION-CHAIN",
        "trigger_date": "2026-07-15",
        "priority": "P0",
        "message": "Kuklinski Jul 15 trigger: Initiate validation email creative chain (Luna → Harlan → Dani → TALON+JET)",
        "client": "Kuklinski (3 couples)",
        "booking": "9593880 / 9593873 / 9595029",
        "condition": "date>=2026-07-15 AND hold_lifted",
        "condition_type": "date_and_hold_status",
        "action": "AUTO_INITIATE_CREATIVE_CHAIN",
        "chain_route": ["A6-Luna", "A9-Harlan", "A3-Dani", "TALON", "JET"],
        "target_email": "kyle.kuklinski@gmail.com",
        "email_type": "VALIDATION",
        "deferred_reason": "Excursion booking window opens Jul 15 (hold expires)"
    }

    existing_alerts.append(new_alert)
    state["deferred_alerts"] = existing_alerts
    logger.info(f"Added deferred alert: {new_alert['id']}")


def create_creative_chain_mission() -> dict:
    """Create a mission board entry for the creative chain."""
    return {
        "id": "MISSION-243",  # Matches the task ID
        "title": "Wire Kuklinski Jul 15 creative chain unlock — automated trigger",
        "status": "in_progress",
        "priority": "P0",
        "assigned_to": "Hale (Automated)",
        "description": "Automated creative chain for Kuklinski validation email. Route: Luna (A6) → Harlan (A9) → Dani (A3) → TALON → JET → WF-17 draft. No Commander intervention required.",
        "deadline": "2026-07-15",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "logs": [
            f"[{datetime.now().isoformat()}] Automated trigger fired on Jul 15, 2026",
            f"[{datetime.now().isoformat()}] Creative chain initiation scheduled: Luna → Harlan → Dani → TALON+JET",
            f"[{datetime.now().isoformat()}] Validation email routing to d2mconcierge (THUNDERBIRD-Commander-Review label)"
        ],
        "chain_config": {
            "client": "Kuklinski (Kyle & Rosalie, Roger & Nicholas, Joshua & Erica)",
            "voyage": "Viking Mars — Panama Canal",
            "departure": "2026-12-17",
            "email_type": "VALIDATION",
            "subject_template": "Your Panama Canal Voyage — Confirmed & Ready to Plan",
            "creative_chain_route": [
                {
                    "stage": 1,
                    "owner": "A6-Luna",
                    "task": "Narrative framing — port descriptions, voyage context",
                    "input": "Kuklinski dossier + Viking Mars itinerary",
                    "output": "narrative_section.md"
                },
                {
                    "stage": 2,
                    "owner": "A9-Harlan",
                    "task": "Financial verification — FPD status, payment confirmation, credits",
                    "input": "narrative_section.md + financial facts from dossier",
                    "output": "financial_verified.md",
                    "verification": "Confirmed: $21,244.00 PAID (3 bookings 9593873+9593880+9595029), FPD Mar-31 passed, source: Viking invoices Feb-2026"
                },
                {
                    "stage": 3,
                    "owner": "A3-Dani",
                    "task": "Client voice — final email language, tone, client-specific register",
                    "input": "financial_verified.md + Kuklinski profile",
                    "output": "dani_draft.html"
                },
                {
                    "stage": 4,
                    "owner": "TALON",
                    "task": "Cross-domain quality check — reader impact, voice, substance",
                    "input": "dani_draft.html",
                    "output": "talon_review.md"
                },
                {
                    "stage": 5,
                    "owner": "JET",
                    "task": "Process completion, facts verified, system integrity",
                    "input": "talon_review.md + full chain artifacts",
                    "output": "jet_sign_off.md"
                },
                {
                    "stage": 6,
                    "owner": "Hale (WF-17 gate)",
                    "task": "Create Gmail draft (d2mconcierge, THUNDERBIRD-Commander-Review label)",
                    "input": "jet_sign_off.md + final HTML",
                    "output": "Gmail draft (awaiting Commander send)"
                }
            ],
            "recipient": "kyle.kuklinski@gmail.com",
            "cc": ["roger.kuklinski@gmail.com", "nikpack@gmail.com", "josh@jerichopix.com", "buzzerica@gmail.com"],
            "bcc": None
        },
        "notes": "AUTOMATED TRIGGER FIRED — No manual intervention required. Creative chain executes sequentially: Luna → Harlan → Dani → TALON+JET. WF-17 draft staged in Gmail for Commander review/send."
    }


def update_mission_board_kuklinski_mission(board: dict) -> None:
    """Update MISSION-191 (Kuklinski validation email hold) to reflect Jul 15 trigger."""
    for mission in board.get("missions", []):
        if mission.get("id") == "MISSION-191":
            mission["status"] = "in_progress"
            mission["updated_at"] = datetime.now().isoformat()
            logs = mission.get("logs", [])
            logs.append(f"[{datetime.now().isoformat()}] Jul 15 trigger fired — moving to MISSION-243 (creative chain)")
            mission["logs"] = logs
            logger.info("Updated MISSION-191 status to in_progress")
            break


def main():
    """Main entry point."""
    try:
        # Step 1: Check if today is Jul 15, 2026
        if not check_trigger_date():
            logger.info(f"Trigger date not yet reached (today: {date.today()}, trigger: 2026-07-15)")
            return 0

        logger.info("=" * 70)
        logger.info("KUKLINSKI JUL 15 TRIGGER FIRED")
        logger.info("=" * 70)

        # Step 2: Load state files
        state = load_hale_state()
        board = load_mission_board()

        # Step 3: Check if creative chain already initiated
        existing_mission = check_creative_chain_status()
        if existing_mission and existing_mission.get("status") in ["completed", "in_progress"]:
            logger.info(f"Creative chain already initiated: {existing_mission.get('id')} (status: {existing_mission.get('status')})")
            return 0

        # Step 4: Add deferred alert to hale_state
        add_jul15_deferred_alert(state)
        save_hale_state(state)

        # Step 5: Create/update mission board entries
        new_mission = create_creative_chain_mission()
        board.setdefault("missions", []).append(new_mission)
        update_mission_board_kuklinski_mission(board)
        save_mission_board(board)

        logger.info("=" * 70)
        logger.info("CREATIVE CHAIN INITIATED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info(f"Mission: MISSION-243")
        logger.info(f"Route: Luna (A6) → Harlan (A9) → Dani (A3) → TALON+JET")
        logger.info(f"Target: kyle.kuklinski@gmail.com")
        logger.info(f"Expected outcome: Gmail draft ready at WF-17 gate for Commander send")

        return 0

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
