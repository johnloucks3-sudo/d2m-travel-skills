#!/usr/bin/env python3
"""
Create Kuklinski lifecycle email draft with 3 attachments
Uses USAFA template with full validation format
"""

import sys
from pathlib import Path

# Add Thunderbird to path
sys.path.insert(0, '/home/john/Thunderbird')

# Import the main draft creation function
from scripts.create_johnloucks3_draft import create_johnloucks3_draft

def main():
    """Main function to create Kuklinski lifecycle email draft"""
    
    print("=== KUKLINSKI LIFECYCLE EMAIL CREATOR ===")
    
    # Kuklinski configuration
    html_file = "/home/john/Thunderbird/output/KUKLINSKI_LIFECYCLE_EMAIL.html"
    to_email = "kyle.kuklinski@gmail.com"
    subject = "Your Panama Canal Cruise Planning Timeline & D2M Service Process"
    from_email = "d2mconcierge@gmail.com"
    
    # Verify files exist
    required_files = [
        html_file,
        "/home/john/Thunderbird/output/Kuklinski_Executive_Gantt.html",
        "/home/john/Thunderbird/output/Kuklinski_Timeline_Proposal.html", 
        "/home/john/Thunderbird/output/KUKLINSKI_DATE_UPDATES_SUMMARY.md"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ ERROR: Required file not found: {file_path}")
            return False
    
    print(f"📁 Using HTML file: {html_file}")
    print(f"📧 Draft will be created in: johnloucks3@gmail.com drafts folder")
    print(f"📝 From: {from_email}")
    print(f"📨 To: {to_email}")
    print(f"📋 Subject: {subject}")
    print(f"📎 Attachments: 3 files (Gantt, Timeline, Summary)")
    
    # Create the draft
    draft_id = create_johnloucks3_draft(html_file, to_email, subject, from_email)
    
    if draft_id:
        print(f"\n✅ SUCCESS! Kuklinski lifecycle draft created")
        print(f"Draft ID: {draft_id}")
        print(f"Attachments included: Executive Gantt, Timeline Proposal, Date Summary")
        return True
    else:
        print("❌ FAILED: Draft creation failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
