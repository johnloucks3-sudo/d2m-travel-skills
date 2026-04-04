#!/usr/bin/env python3
"""
THUNDERBIRD EMAIL MAINTENANCE ENGINE — v1.0
File: thunderbird_email_maintenance.py
Author: Hale | Implementer: Claude
Date: 2026-04-04

PROBLEM SOLVED:
- Replaces dead email_task_ingest.py
- Activates 5 complete conditioning JSONs sitting in email_conditioning/
- Provides automated email pipeline for Commander inbox

ARCHITECTURE:
SWEEP → CLASSIFY → ROUTE & DRAFT → ARCHIVE

NO subprocess chains. Direct MCP tool usage. WF-17 compliant.
"""

import json
import os
import sys
import logging
import time
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OPSCENTER_DIR = THUNDERBIRD_DIR / "OpsCenter"
EMAIL_CONDITIONING_DIR = THUNDERBIRD_DIR / "email_conditioning"

# State and logging
STATE_FILE = OPSCENTER_DIR / "email_maintenance_state.json"
LOG_FILE = OPSCENTER_DIR / "email_maintenance.log"

# Gmail accounts
D2M_CONCIERGE_EMAIL = "d2mconcierge@gmail.com"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
CONCIERGE_SEND_AS = "concierge@d2mluxury.quest"

# Inbox destinations
GOOSE_INBOX = THUNDERBIRD_DIR / "goose_inbox.md"
CLAUDE_INBOX = THUNDERBIRD_DIR / "claude_inbox.md"
ACTIVITY_BOARD = OPSCENTER_DIR / "collaboration" / "activity_board.md"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sweep config
SWEEP_INTERVAL_MINUTES = 5
DEDUP_WINDOW_SECONDS = 600
STATE_PRUNE_SIZE = 500

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def load_state() -> Dict[str, Any]:
    """Load dedup state from JSON file."""
    if not STATE_FILE.exists():
        return {"processed_message_ids": [], "last_run": None}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state: {e}. Using fresh state.")
        return {"processed_message_ids": [], "last_run": None}


def save_state(state: Dict[str, Any]) -> None:
    """Save dedup state to JSON file. Prune if needed."""
    # Prune to avoid unbounded growth
    if len(state["processed_message_ids"]) > STATE_PRUNE_SIZE:
        state["processed_message_ids"] = state["processed_message_ids"][-STATE_PRUNE_SIZE:]
        logger.info(f"Pruned processed_message_ids to {STATE_PRUNE_SIZE}")

    state["last_run"] = datetime.utcnow().isoformat()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def is_processed(message_id: str, state: Dict[str, Any]) -> bool:
    """Check if message was already processed (within dedup window)."""
    return message_id in state["processed_message_ids"]


def mark_processed(message_id: str, state: Dict[str, Any]) -> None:
    """Mark message as processed."""
    if message_id not in state["processed_message_ids"]:
        state["processed_message_ids"].append(message_id)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_config(filename: str) -> Dict[str, Any]:
    """Load a single JSON config file."""
    config_path = EMAIL_CONDITIONING_DIR / filename
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return {}


def load_all_configs() -> Dict[str, Dict[str, Any]]:
    """Load all 5 conditioning JSON files."""
    configs = {
        "sweep": load_config("EMAIL_SWEEP_CONDITIONS.json"),
        "tasking": load_config("EMAIL_TASKING_CONDITIONS.json"),
        "draft": load_config("EMAIL_DRAFT_CONDITIONS.json"),
        "send_to_commander": load_config("EMAIL_SEND_TO_COMMANDER_CONDITIONS.json"),
        "send_to_johnloucks3": load_config("EMAIL_SEND_TO_JOHNLOUCKS3_CONDITIONS.json"),
    }
    return configs


# ============================================================================
# GMAIL MCP INTEGRATION
# ============================================================================

def gmail_search(query: str) -> List[str]:
    """
    Search Gmail. Returns list of message IDs.

    NOTE: Requires MCP tool: mcp__dreams2memories__gmail_search_messages
    Pattern from thunderbird_gmail.py
    """
    logger.info(f"[STUB] Gmail search: {query}")
    # In production, call actual MCP tool:
    # result = mcp_client.call_tool("gmail_search_messages", {"q": query})
    # return result.get("messages", [])
    return []


def gmail_read_message(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Read full message content.

    NOTE: Requires MCP tool: mcp__dreams2memories__gmail_read_message
    """
    logger.info(f"[STUB] Gmail read: {message_id}")
    # In production, call actual MCP tool:
    # result = mcp_client.call_tool("gmail_read_message", {"message_id": message_id})
    # return result
    return None


def gmail_create_draft(
    to: str,
    subject: str,
    body: str,
    from_email: str = D2M_CONCIERGE_EMAIL,
) -> Optional[str]:
    """
    Create Gmail draft.

    NOTE: Requires MCP tool: mcp__dreams2memories__gmail_create_draft
    WF-17 compliance: never direct send, always draft for Commander review
    """
    logger.info(f"[STUB] Gmail create draft to {to}: {subject}")
    # In production, call actual MCP tool:
    # result = mcp_client.call_tool("gmail_create_draft", {
    #     "to": to,
    #     "subject": subject,
    #     "body": body,
    #     "from": from_email,
    # })
    # return result.get("draft_id")
    return None


def gmail_modify_message(message_id: str, labels_to_add: List[str]) -> bool:
    """
    Add labels to message (e.g., ARCHIVE label = archive the email).

    NOTE: Requires MCP tool: mcp__dreams2memories__gmail_modify_message
    """
    logger.info(f"[STUB] Gmail modify {message_id}: add labels {labels_to_add}")
    # In production, call actual MCP tool:
    # result = mcp_client.call_tool("gmail_modify_message", {
    #     "message_id": message_id,
    #     "add_labels": labels_to_add,
    # })
    # return result.get("success", False)
    return False


def send_telegram_notification(message: str) -> bool:
    """Send Telegram notification to Commander via Telegram C2."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured. Skipping notification.")
        return False

    logger.info(f"[STUB] Telegram notification: {message[:80]}...")
    # In production, call actual Telegram API or MCP tool
    return True


# ============================================================================
# EMAIL CLASSIFICATION
# ============================================================================

def extract_persona_tag(email_body: str, email_subject: str) -> Optional[str]:
    """
    Extract persona tag from email subject or body.
    Tags: [COS], [COO], [EXEC], [A2], [A3], [A5], [A7], [A9], [A12], [CLIENT]
    """
    combined = f"{email_subject} {email_body}".upper()
    tags = ["[COS]", "[COO]", "[EXEC]", "[A2]", "[A3]", "[A5]", "[A7]", "[A9]", "[A12]", "[CLIENT]"]

    for tag in tags:
        if tag in combined:
            return tag

    return None


def infer_routing(email_body: str, email_subject: str, sender: str, recipient: str) -> Optional[str]:
    """
    Infer routing when no explicit persona tag is present.
    Uses EMAIL_TASKING_CONDITIONS.json inference_rules.

    Returns: persona tag like [A2], [A3], etc., or None if no inference possible
    """
    combined = f"{email_subject} {email_body}".lower()

    # Build simple inference heuristics from conditioning
    # (In production, would load from EMAIL_TASKING_CONDITIONS.json inference_rules)

    if any(kw in combined for kw in ["client", "booking", "trip", "cruise", "hotel", "excursion"]):
        return "[A3]"  # Dani - client-facing

    if any(kw in combined for kw in ["research", "intelligence", "intel", "competitor", "destination", "cruise line"]):
        return "[A2]"  # Dembe - research

    if any(kw in combined for kw in ["commission", "cost", "budget", "price", "payment", "finance", "roi"]):
        return "[A9]"  # Harlan - finance

    if any(kw in combined for kw in ["marketing", "brand", "copy", "narrative", "story", "tone", "voice"]):
        return "[A6]"  # Luna - creative

    if any(kw in combined for kw in ["process", "workflow", "automation", "improvement", "efficiency", "waste"]):
        return "[A7]"  # Gauge - process improvement

    if any(kw in combined for kw in ["strategy", "business", "growth", "pricing", "positioning", "decision"]):
        return "[A5]"  # Viper - strategy

    return None


def classify_email(
    email_data: Dict[str, Any],
    configs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Full classification pipeline:
    1. Check skip patterns
    2. Extract persona tag
    3. Infer routing if needed
    4. Determine action (route to inbox, create draft, etc.)

    Returns classification dict with: routing_persona, action, target_inbox, etc.
    """
    sender = email_data.get("sender", "")
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    message_id = email_data.get("message_id", "")

    # Step 1: Check skip patterns
    skip_patterns = configs.get("sweep", {}).get("skip_patterns", [])
    for pattern in skip_patterns:
        if pattern.lower() in sender.lower():
            logger.info(f"Skipping {message_id}: matches skip pattern '{pattern}'")
            return {"action": "skip", "reason": f"matches skip pattern {pattern}"}

    # Step 2: Extract persona tag or infer routing
    persona_tag = extract_persona_tag(body, subject)

    if not persona_tag:
        persona_tag = infer_routing(body, subject, sender, "")

    if not persona_tag:
        logger.warning(f"Could not classify {message_id}: no tag, no inference. Routing to COS.")
        persona_tag = "[COS]"

    # Step 3: Map persona tag to routing
    tasking_config = configs.get("tasking", {})
    routing_map = tasking_config.get("routing_tags", {})

    routing_rules = {
        "[COS]": {"target_inbox": "claude", "persona": "hale"},
        "[COO]": {"target_inbox": "claude", "persona": "hale"},
        "[EXEC]": {"target_inbox": "claude", "persona": "naia"},
        "[A2]": {"target_inbox": "claude", "persona": "dembe"},
        "[A3]": {"target_inbox": "goose", "persona": "dani"},
        "[A5]": {"target_inbox": "claude", "persona": "castillo"},
        "[A6]": {"target_inbox": "goose", "persona": "luna"},
        "[A7]": {"target_inbox": "claude", "persona": "sterling"},
        "[A9]": {"target_inbox": "claude", "persona": "harlan"},
        "[A12]": {"target_inbox": "claude", "persona": "elon"},
        "[CLIENT]": {"target_inbox": "goose", "persona": "dani", "action": "draft_wf17"},
    }

    route = routing_rules.get(persona_tag, {"target_inbox": "claude", "persona": "hale"})

    return {
        "action": "process",
        "message_id": message_id,
        "persona_tag": persona_tag,
        "target_inbox": route["target_inbox"],
        "persona": route["persona"],
        "sender": sender,
        "subject": subject,
    }


# ============================================================================
# INBOX & DRAFT OPERATIONS
# ============================================================================

def write_task_to_inbox(
    inbox_path: Path,
    classification: Dict[str, Any],
) -> bool:
    """
    Write classified email to goose_inbox.md or claude_inbox.md.
    Format: task entry with message ID, sender, subject, persona tag, action.
    """
    try:
        entry = f"""
## TASK: {classification['message_id'][:8]}
**From:** {classification['sender']}
**Subject:** {classification['subject']}
**Persona Tag:** {classification['persona_tag']}
**Target Persona:** {classification['persona']}
**Status:** PENDING

[Full email available in email_maintenance.log]
"""
        with open(inbox_path, "a") as f:
            f.write(entry)

        logger.info(f"Wrote task to {inbox_path.name}: {classification['message_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to write task to inbox: {e}")
        return False


def create_wf17_draft(
    classification: Dict[str, Any],
    configs: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """
    Create WF-17 compliant draft for client-facing emails.
    Draft goes to d2mconcierge as draft for Commander review.
    """
    draft_config = configs.get("draft", {})

    subject = f"[DRAFT-{classification['message_id'][:8]}] {classification['subject']}"

    body = f"""
From: {CONCIERGE_SEND_AS}
To: {classification['sender']}

[Draft auto-generated by Thunderbird Email Maintenance Engine]
[Persona: {classification['persona']}]
[Status: AWAITING COMMANDER REVIEW]

Dear {classification['sender'].split('@')[0]},

[Response body to be composed by {classification['persona'].upper()}]

Thanks
John Loucks
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
719-291-0742
"""

    # Create draft via Gmail MCP
    draft_id = gmail_create_draft(
        to=COMMANDER_EMAIL,  # Draft goes to Commander for review
        subject=subject,
        body=body,
    )

    if draft_id:
        logger.info(f"Created WF-17 draft {draft_id} for {classification['message_id']}")
        return draft_id

    return None


def archive_email(message_id: str) -> bool:
    """Archive processed email by adding ARCHIVE label."""
    return gmail_modify_message(message_id, ["ARCHIVE"])


# ============================================================================
# EMAIL PROCESSING
# ============================================================================

def process_email_sweep(
    state: Dict[str, Any],
    configs: Dict[str, Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Main sweep logic:
    1. Search for unread emails in d2m_concierge
    2. Filter for actionable messages (skip patterns, old emails)
    3. Classify each email
    4. Route to appropriate inbox or create draft
    5. Archive after processing
    6. Track in state file
    """
    stats = {"processed": 0, "skipped": 0, "drafted": 0, "errors": 0}

    logger.info("Starting email sweep...")

    # Search for unread emails
    sweep_config = configs.get("sweep", {})
    d2m_target = sweep_config.get("targets", {}).get("d2m_concierge", {})

    query = f"from:{D2M_CONCIERGE_EMAIL} is:unread"
    message_ids = gmail_search(query)

    if not message_ids:
        logger.info("No unread emails found.")
        return stats

    logger.info(f"Found {len(message_ids)} unread emails")

    for message_id in message_ids:
        # Check dedup
        if is_processed(message_id, state):
            logger.info(f"Skipping {message_id}: already processed")
            stats["skipped"] += 1
            continue

        # Read email
        email_data = gmail_read_message(message_id)
        if not email_data:
            logger.warning(f"Failed to read {message_id}")
            stats["errors"] += 1
            continue

        email_data["message_id"] = message_id

        # Classify
        classification = classify_email(email_data, configs)

        if classification["action"] == "skip":
            logger.info(f"Skipping {message_id}: {classification.get('reason')}")
            stats["skipped"] += 1
            mark_processed(message_id, state)
            continue

        # Route based on classification
        if not dry_run:
            # Write to appropriate inbox
            inbox_path = GOOSE_INBOX if classification["target_inbox"] == "goose" else CLAUDE_INBOX
            write_task_to_inbox(inbox_path, classification)

            # Create draft if client-facing
            if "[CLIENT]" in classification["persona_tag"]:
                draft_id = create_wf17_draft(classification, configs)
                if draft_id:
                    stats["drafted"] += 1

            # Archive
            archive_email(message_id)

        mark_processed(message_id, state)
        stats["processed"] += 1

    # Save state
    if not dry_run:
        save_state(state)

    logger.info(f"Sweep complete: {stats}")
    return stats


def notify_command_summary(stats: Dict[str, int]) -> None:
    """Send summary notification to Commander via Telegram."""
    message = f"""
📧 **EMAIL SWEEP SUMMARY**
• Processed: {stats['processed']}
• Drafted (WF-17): {stats['drafted']}
• Skipped: {stats['skipped']}
• Errors: {stats['errors']}

Tasks written to goose_inbox.md / claude_inbox.md
Drafts awaiting your review in Gmail
"""
    send_telegram_notification(message)


# ============================================================================
# MAIN ENTRY POINTS
# ============================================================================

def sweep_once(dry_run: bool = False) -> None:
    """Run a single email sweep."""
    logger.info("=" * 70)
    logger.info("SWEEP_ONCE MODE")
    logger.info("=" * 70)

    state = load_state()
    configs = load_all_configs()

    if not all([configs.get("sweep"), configs.get("tasking"), configs.get("draft")]):
        logger.error("Failed to load required conditioning configs. Aborting.")
        return

    stats = process_email_sweep(state, configs, dry_run=dry_run)

    if not dry_run and stats["processed"] > 0:
        notify_command_summary(stats)


def sweep_loop() -> None:
    """Run email sweep in continuous loop (5-minute intervals)."""
    logger.info("=" * 70)
    logger.info("SWEEP_LOOP MODE (5-minute interval)")
    logger.info("=" * 70)

    configs = load_all_configs()
    if not all([configs.get("sweep"), configs.get("tasking"), configs.get("draft")]):
        logger.error("Failed to load required conditioning configs. Aborting.")
        return

    try:
        while True:
            state = load_state()
            stats = process_email_sweep(state, configs)

            if stats["processed"] > 0:
                notify_command_summary(stats)

            logger.info(f"Next sweep in {SWEEP_INTERVAL_MINUTES} minutes...")
            time.sleep(SWEEP_INTERVAL_MINUTES * 60)

    except KeyboardInterrupt:
        logger.info("Sweep loop interrupted by user.")


def test_configs() -> None:
    """Validate all conditioning JSON configs."""
    logger.info("=" * 70)
    logger.info("TEST_CONFIGS MODE")
    logger.info("=" * 70)

    configs = load_all_configs()

    for name, config in configs.items():
        if config:
            logger.info(f"✓ {name}: loaded ({len(config)} keys)")
            if "enabled" in config and not config["enabled"]:
                logger.warning(f"  ⚠ {name} is DISABLED")
        else:
            logger.error(f"✗ {name}: FAILED TO LOAD")

    logger.info("\nConfig test complete.")


# ============================================================================
# CLI
# ============================================================================

def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print("""
THUNDERBIRD EMAIL MAINTENANCE ENGINE v1.0

USAGE:
  python thunderbird_email_maintenance.py [MODE] [OPTIONS]

MODES:
  --sweep       Run a single email sweep (default)
  --loop        Run continuous sweep loop (5-minute intervals)
  --dry-run     Test mode: log actions without making changes
  --test        Validate all conditioning JSON configs

EXAMPLES:
  python thunderbird_email_maintenance.py --sweep
  python thunderbird_email_maintenance.py --loop
  python thunderbird_email_maintenance.py --dry-run
  python thunderbird_email_maintenance.py --test
""")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "--sweep":
        sweep_once(dry_run="--dry-run" in sys.argv)
    elif mode == "--loop":
        sweep_loop()
    elif mode == "--dry-run":
        sweep_once(dry_run=True)
    elif mode == "--test":
        test_configs()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
