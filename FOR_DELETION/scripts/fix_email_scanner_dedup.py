#!/usr/bin/env python3
"""
Fix Email Scanner Deduplication
Add deduplication for wing_comms.md and safety checks
"""

import re
import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
SCANNER_FILE = THUNDERBIRD_DIR / "core" / "email" / "thunderbird_email_scanner_fixed.py"
BACKUP_FILE = SCANNER_FILE.with_suffix(
    f".py.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
)


def add_wing_comms_dedup():
    """Add deduplication for wing_comms.md"""

    with open(SCANNER_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if deduplication for wing_comms already exists
    if "check_wing_comms_duplicate" in content:
        print("✓ wing_comms deduplication already exists")
        return False

    # Find where check_duplicate_task function is defined
    # and add a similar function for wing_comms
    duplicate_func_pattern = (
        r"def check_duplicate_task\(sender: str, subject: str, staff: str\) -> bool:"
    )

    if duplicate_func_pattern not in content:
        print("✗ Could not find check_duplicate_task function")
        return False

    # Add new function after check_duplicate_task
    new_function = '''
def check_wing_comms_duplicate(sender: str, subject: str, staff: str, message_id: str) -> bool:
    """
    Check if a similar task already exists in wing_comms.md
    Returns True if duplicate found, False otherwise.
    """
    try:
        if not WING_COMMS.exists():
            return False

        with open(WING_COMMS, "r") as f:
            content = f.read()

        # Check for duplicate by message ID (most reliable)
        if message_id and f"Message ID: {message_id}" in content:
            logger.info(f"Duplicate task detected in wing_comms for message ID: {message_id}")
            return True

        # Also check by subject and staff
        search_patterns = [
            f"Subject: {subject[:100]}",  # First 100 chars of subject
            f"to: {staff}",
            f"From: {sender}",
        ]

        # If any of these patterns exist in wing_comms, it's likely a duplicate
        for pattern in search_patterns:
            if pattern in content:
                logger.info(f"Duplicate wing_comms task detected for pattern: {pattern[:50]}...")
                return True

        return False
    except Exception as e:
        logger.error(f"wing_comms deduplication check failed: {e}")
        return False
'''

    # Insert new function after check_duplicate_task
    insert_pos = content.find(duplicate_func_pattern)
    if insert_pos == -1:
        print("✗ Could not find insert position")
        return False

    # Find the end of the check_duplicate_task function
    # Look for the next function definition
    lines = content.split("\n")
    in_function = False
    func_end_line = -1

    for i, line in enumerate(lines):
        if line.strip().startswith("def check_duplicate_task"):
            in_function = True
        elif (
            in_function
            and line.strip().startswith("def ")
            and i > 0
            and lines[i - 1].strip() == ""
        ):
            func_end_line = i - 1  # Line before next function
            break

    if func_end_line == -1:
        # If we can't find next function, add at end of file
        func_end_line = len(lines) - 1

    # Insert new function
    new_lines = (
        lines[:func_end_line]
        + [""]
        + new_function.strip().split("\n")
        + lines[func_end_line:]
    )
    content = "\n".join(new_lines)

    # Now update write_wing_comms_task to use deduplication
    write_wing_pattern = r"def write_wing_comms_task\(classification: Dict\[str, Any\]\) -> tuple\[bool, str\]:"

    if write_wing_pattern not in content:
        print("✗ Could not find write_wing_comms_task function")
        return False

    # Find the write_wing_comms_task function and add deduplication at the beginning
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "def write_wing_comms_task" in line:
            # Find where the function body starts
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("try:"):
                    # Insert deduplication check before try block
                    dedup_code = '''    # Deduplication check for wing_comms
    if check_wing_comms_duplicate(
        classification["sender"], 
        classification["subject"], 
        classification["staff"],
        classification.get("message_id", "")
    ):
        logger.info(
            f"Duplicate wing_comms task skipped for {classification['staff']} - {classification['subject'][:50]}..."
        )
        return False, ""'''

                    lines.insert(j, dedup_code)
                    break
            break

    content = "\n".join(lines)

    # Create backup
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        f.write(open(SCANNER_FILE, "r").read())

    # Write updated content
    with open(SCANNER_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ Added wing_comms deduplication")
    print(f"✓ Backup: {BACKUP_FILE}")
    return True


def add_safety_check():
    """Add safety check to prevent HALE/NAIA routing to claude"""

    with open(SCANNER_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the routing logic
    routing_pattern = r'if classification\["target_inbox"\] == "claude":'

    if routing_pattern not in content:
        print("✗ Could not find claude routing logic")
        return False

    # Add warning before claude routing
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if 'if classification["target_inbox"] == "claude":' in line:
            # Add safety check
            safety_check = """            # SAFETY CHECK: HALE/NAIA should never go to claude
            if classification["staff"] in ["HALE", "NAIA"]:
                logger.warning(f"SAFETY VIOLATION: HALE/NAIA ({classification['staff']}) routed to claude! Routing to wing_comms instead.")
                success, task_id = write_wing_comms_task(classification)
                action = "wing_comms (safety override)"
                # Log this violation
                with open(LOG_FILE, "a") as log_f:
                    log_f.write(f"{datetime.utcnow().isoformat()} | SAFETY_VIOLATION | {classification['staff']} | {classification['subject'][:50]}... | HALE/NAIA routed to claude, overridden to wing_comms\\\\n")
            else:"""

            # Insert safety check
            lines[i] = safety_check + "\n            " + lines[i]
            break

    content = "\n".join(lines)

    # Write updated content
    with open(SCANNER_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("✓ Added safety check for HALE/NAIA routing")
    return True


def main():
    print("=" * 60)
    print("FIXING EMAIL SCANNER DEDUPLICATION")
    print("=" * 60)

    if not SCANNER_FILE.exists():
        print(f"✗ Scanner file not found: {SCANNER_FILE}")
        return 1

    print(f"File: {SCANNER_FILE}")

    # 1. Add wing_comms deduplication
    print("\n1. Adding wing_comms deduplication...")
    dedup_added = add_wing_comms_dedup()

    # 2. Add safety check
    print("\n2. Adding safety check for HALE/NAIA routing...")
    safety_added = add_safety_check()

    print("\n" + "=" * 60)
    print("FIXES APPLIED")
    print("=" * 60)

    if dedup_added:
        print("✓ Added wing_comms deduplication")
        print("  - New function: check_wing_comms_duplicate()")
        print("  - Integrated into write_wing_comms_task()")

    if safety_added:
        print("✓ Added safety check for HALE/NAIA")
        print("  - Prevents HALE/NAIA routing to claude_inbox")
        print("  - Logs violations and routes to wing_comms instead")

    if not dedup_added and not safety_added:
        print("⚠ No fixes were applied (may already be implemented)")

    print(f"\nBackup: {BACKUP_FILE if BACKUP_FILE.exists() else 'Not created'}")

    print("\n" + "=" * 60)
    print("TESTING RECOMMENDATIONS")
    print("=" * 60)
    print("""
1. Run the email scanner test:
   python scripts/test_email_scanner_routing.py

2. Monitor the email scanner logs:
   tail -f OpsCenter/logs/email_scanner.log

3. Test actual email scanning (if possible):
   .venv/bin/python core/email/thunderbird_email_scanner_fixed.py --test

4. Check for duplicate prevention:
   - Run scanner twice on same emails
   - Verify no duplicate tasks in wing_comms.md
   - Check logs for "Duplicate task detected" messages
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
