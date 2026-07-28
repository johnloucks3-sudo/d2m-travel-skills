#!/usr/bin/env python3
"""
Minimal Email Scanner Fix
Add deduplication for wing_comms only.
"""

import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
SCANNER_FILE = THUNDERBIRD_DIR / "core" / "email" / "thunderbird_email_scanner_fixed.py"
BACKUP_FILE = SCANNER_FILE.with_suffix(
    f".py.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
)


def main():
    # Create backup
    import shutil

    shutil.copy2(SCANNER_FILE, BACKUP_FILE)
    print(f"Backup: {BACKUP_FILE}")

    # Read file
    with open(SCANNER_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find where to insert wing_comms deduplication function
    # Insert after check_duplicate_task function
    insert_line = -1
    for i, line in enumerate(lines):
        if "def check_duplicate_task(" in line:
            # Find end of this function (next function definition)
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("def ") and lines[j - 1].strip() == "":
                    insert_line = j
                    break
            break

    if insert_line == -1:
        print("Could not find where to insert deduplication function")
        return 1

    # Add the new function
    new_function = '''
def check_wing_comms_duplicate(message_id: str, staff: str, subject: str) -> bool:
    """Check if task already exists in wing_comms.md by message ID"""
    try:
        if not WING_COMMS.exists():
            return False
        
        with open(WING_COMMS, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Primary check: message ID
        if message_id and f"Message ID: {message_id}" in content:
            logger.info(f"Duplicate wing_comms task: {message_id}")
            return True
        
        # Secondary check: subject + staff  
        if f"Subject: {subject[:100]}" in content and f"to: {staff}" in content:
            logger.info(f"Duplicate wing_comms task: {staff} - {subject[:50]}...")
            return True
            
        return False
    except Exception as e:
        logger.error(f"wing_comms deduplication error: {e}")
        return False
'''

    # Insert the function
    lines.insert(insert_line, new_function)

    # Now add deduplication check to write_wing_comms_task
    for i, line in enumerate(lines):
        if "def write_wing_comms_task(" in line:
            # Find the try: line
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "try:":
                    # Insert deduplication before try
                    dedup_code = '''    # Check for duplicates in wing_comms
    if check_wing_comms_duplicate(
        classification.get("message_id", ""),
        classification["staff"],
        classification["subject"]
    ):
        logger.info(f"Duplicate task skipped for {classification['staff']}")
        return False, ""'''

                    lines.insert(j, dedup_code)
                    break
            break

    # Write back
    with open(SCANNER_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Added wing_comms deduplication")
    print("\nFixes applied:")
    print("1. Added check_wing_comms_duplicate() function")
    print("2. Added deduplication to write_wing_comms_task()")
    print("\nThis prevents duplicate tasks in wing_comms.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
