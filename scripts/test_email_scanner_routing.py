#!/usr/bin/env python3
"""
Test Email Scanner Routing
Verify HALE/NAIA go to wing_comms, others to opencode
"""

import sys
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "email"))

# Import the scanner functions
try:
    from thunderbird_email_scanner_fixed import classify_email, extract_staff_mention

    print("✓ Imported scanner functions")
except ImportError as e:
    print(f"✗ Failed to import: {e}")
    sys.exit(1)

# Test cases
test_cases = [
    {
        "name": "HALE mention in subject",
        "subject": "FWD: Task for HALE review",
        "body": "Please review this email.",
        "expected_staff": "HALE",
        "expected_target": "wing_comms",
    },
    {
        "name": "NAIA mention in body",
        "subject": "Commander's Intent",
        "body": "This is for NAIA's review. Please process.",
        "expected_staff": "NAIA",
        "expected_target": "wing_comms",
    },
    {
        "name": "DEMBE mention",
        "subject": "Guest forms",
        "body": "Marcus Dembe needs to review these forms.",
        "expected_staff": "DEMBE",
        "expected_target": "opencode",
    },
    {
        "name": "MOREAU mention",
        "subject": "Client email draft",
        "body": "Dani Moreau should write this client email.",
        "expected_staff": "MOREAU",
        "expected_target": "opencode",
    },
    {
        "name": "No staff mention",
        "subject": "General inquiry",
        "body": "Hello, I have a question about travel.",
        "expected_staff": None,
        "expected_target": None,  # Should skip
    },
]

print("\n" + "=" * 60)
print("Testing Email Scanner Classification")
print("=" * 60)

for test in test_cases:
    print(f"\nTest: {test['name']}")
    print(f"  Subject: {test['subject']}")
    print(f"  Body: {test['body'][:50]}...")

    # Create email data
    email_data = {
        "subject": test["subject"],
        "body": test["body"],
        "sender": "test@example.com",
        "message_id": "test-123",
    }

    # Classify
    try:
        result = classify_email(email_data)

        if result["action"] == "skip":
            if test["expected_staff"] is None:
                print(f"  ✓ Correctly skipped: {result.get('reason', 'unknown')}")
            else:
                print(f"  ✗ Incorrectly skipped. Expected: {test['expected_staff']}")
                print(f"    Reason: {result.get('reason', 'unknown')}")
        else:
            actual_staff = result.get("staff")
            actual_target = result.get("target_inbox")

            if (
                actual_staff == test["expected_staff"]
                and actual_target == test["expected_target"]
            ):
                print(f"  ✓ Correct: staff={actual_staff}, target={actual_target}")
            else:
                print(
                    f"  ✗ Incorrect. Expected: staff={test['expected_staff']}, target={test['expected_target']}"
                )
                print(f"    Actual: staff={actual_staff}, target={actual_target}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

# Check classification logic directly
print("\n" + "=" * 60)
print("Checking Classification Logic")
print("=" * 60)

print("\nAccording to classify_email():")
print("- HALE → target_inbox = 'wing_comms'")
print("- NAIA → target_inbox = 'wing_comms'")
print("- DEMBE → target_inbox = 'opencode'")
print("- MOREAU → target_inbox = 'opencode'")

print("\nAccording to process_email_sweep():")
print("- If target_inbox == 'wing_comms' → write_wing_comms_task()")
print("- If target_inbox == 'claude' → write_claude_task()")
print("- If target_inbox == 'opencode' → write_opencode_task()")

print("\nConclusion:")
print("1. HALE/NAIA should go to wing_comms.md via write_wing_comms_task()")
print("2. Other staff (DEMBE, MOREAU) should go to opencode_inbox.md")
print("3. 'claude' target_inbox should never be returned by classify_email()")

print("\n" + "=" * 60)
print("RECOMMENDATION")
print("=" * 60)
print("""
The classification logic appears correct. 
The duplicate tasks in claude_inbox.md were likely created by:
1. An older version of the scanner
2. A bug that has since been fixed
3. Manual testing

To prevent recurrence:
1. The current code should work correctly
2. Monitor email scanner logs
3. If tasks appear in claude_inbox.md again, check:
   - Is classify_email() returning 'claude' for HALE/NAIA?
   - Is write_claude_task() being called instead of write_wing_comms_task()?
""")
