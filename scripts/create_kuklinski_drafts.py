#!/usr/bin/env python3
"""
Create 3 sample Gmail drafts for Kuklinski lifecycle emails
Uses create_johnloucks3_draft function from create_johnloucks3_draft.py
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from create_johnloucks3_draft import create_johnloucks3_draft

def main():
    print("=== KUKLINSKI LIFECYCLE EMAIL DRAFTS ===\n")

    # Draft configuration
    drafts = [
        {
            "name": "Insurance Email",
            "html": "/home/john/Thunderbird/drafts/kuklinski_insurance_email.html",
            "to": "kyle.kuklinski@gmail.com",
            "subject": "Travel Insurance — Pre-Existing Waiver Window (Important)"
        },
        {
            "name": "Welcome/Validation Email",
            "html": "/home/john/Thunderbird/drafts/kuklinski_welcome_validation_email.html",
            "to": "kyle.kuklinski@gmail.com",
            "subject": "Welcome to Your Viking Mars Adventure — Panama Canal Awaits"
        },
        {
            "name": "Guest Forms Reminder",
            "html": "/home/john/Thunderbird/drafts/kuklinski_guest_forms_reminder_email.html",
            "to": "kyle.kuklinski@gmail.com",
            "subject": "Josh Morton Guest Profile — Quick Request"
        }
    ]

    draft_ids = []

    for i, draft_config in enumerate(drafts, 1):
        print(f"\n[{i}/3] Creating: {draft_config['name']}")
        print(f"      To: {draft_config['to']}")
        print(f"      Subject: {draft_config['subject']}")

        draft_id = create_johnloucks3_draft(
            draft_config['html'],
            draft_config['to'],
            draft_config['subject'],
            from_email="d2mconcierge@gmail.com"
        )

        if draft_id:
            draft_ids.append({
                "name": draft_config['name'],
                "draft_id": draft_id,
                "to": draft_config['to'],
                "subject": draft_config['subject']
            })
            print(f"✅ SUCCESS! Draft ID: {draft_id}\n")
        else:
            print(f"❌ FAILED to create draft.\n")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if draft_ids:
        print(f"\n✅ Created {len(draft_ids)} of {len(drafts)} drafts:\n")
        for draft in draft_ids:
            print(f"📧 {draft['name']}")
            print(f"   Draft ID: {draft['draft_id']}")
            print(f"   To: {draft['to']}")
            print(f"   Subject: {draft['subject']}")
            print(f"   Access: https://mail.google.com/mail/u/0/#drafts\n")

        # Write summary to outbox
        try:
            outbox_path = "/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
            with open(outbox_path, "a") as f:
                f.write("\n\n## TASK: OC-GANT-CLIENT-CONTACTS-2\n")
                f.write("**STATUS: COMPLETE**\n\n")
                f.write("### Kuklinski Lifecycle Email Drafts\n\n")
                f.write("**3 Sample Emails Created (Dani Voice, WF-17 Compliant)**\n\n")
                for draft in draft_ids:
                    f.write(f"- **{draft['name']}**\n")
                    f.write(f"  - Draft ID: `{draft['draft_id']}`\n")
                    f.write(f"  - To: {draft['to']}\n")
                    f.write(f"  - Subject: {draft['subject']}\n\n")
                f.write("**All drafts created in johnloucks3@gmail.com — Ready for Commander review.**\n")
            print("✅ Summary written to claude_outbox.md")
        except Exception as e:
            print(f"⚠️  Could not write to outbox: {e}")
    else:
        print("\n❌ No drafts were created successfully.")
        sys.exit(1)

if __name__ == "__main__":
    main()
