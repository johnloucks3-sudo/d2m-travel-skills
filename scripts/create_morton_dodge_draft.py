#!/usr/bin/env python3
"""
Create Morton & Dodge TP 0.5 Welcome Email Draft
Task: MISSION-115
Purpose: Draft the initial welcome/validation email for Joshua Morton & Erica Dodge
         Viking Mars Panama Canal, Dec 17-27, 2026
"""

import json
import sys
from pathlib import Path

# Add core modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.email.thunderbird_gmail import gmail_create_draft_sync

def main():
    # Read the existing HTML draft
    draft_file = Path(__file__).parent.parent / "drafts" / "Morton_Dodge_TP0.5_welcome_gmail.html"

    if not draft_file.exists():
        print(f"ERROR: Draft file not found: {draft_file}")
        return False

    with open(draft_file, 'r') as f:
        body_html = f.read()

    # Client email addresses
    to_addresses = "josh@jerichopix.com, buzzerica@gmail.com"

    # Subject line
    subject = "Welcome to Your Panama Canal Adventure — Viking Mars Dec 17–27"

    # Create draft with THUNDERBIRD-Commander-Review label
    try:
        result = gmail_create_draft_sync(
            to=to_addresses,
            subject=subject,
            body=body_html,
            from_address="concierge@d2mluxury.quest",
            label_review=True,  # Applies THUNDERBIRD-Commander-Review label
            notify_telegram=False,  # Don't page yet
            persona_display="Dani Moreau",
            product_type="TP_0_5_WELCOME",
            chain_status={
                "reyes": "experience_review_included",
                "luna": "narrative_included",
                "naia": "brand_pass_complete",
                "dani": "client_voice_complete",
                "talon_jet": "quality_check_pending_commander"
            }
        )

        print("✅ DRAFT CREATED SUCCESSFULLY")
        print(f"   Draft ID: {result.get('draft_id')}")
        print(f"   Subject: {result.get('subject')}")
        print(f"   To: {to_addresses}")
        print(f"   Label: THUNDERBIRD-Commander-Review")
        print(f"   Status: {result.get('status')}")
        print("\nNext: Commander reviews and sends from d2mconcierge")

        return True

    except Exception as e:
        print(f"❌ ERROR creating draft: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
