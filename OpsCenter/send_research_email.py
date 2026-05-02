#!/usr/bin/env python3
"""
SEND RESEARCH RESULTS EMAIL
============================
Sends the completed research findings to johnloucks3@gmail.com
Usage: python3 send_research_email.py [research_file_path]
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Gmail function from core
from core.email.thunderbird_gmail import gmail_send_from_wing

def send_research_email(research_file_path):
    """Send research findings via Gmail."""

    research_file = Path(research_file_path)
    if not research_file.exists():
        print(f"❌ Research file not found: {research_file}")
        return False

    # Read research content
    try:
        content = research_file.read_text()
    except Exception as e:
        print(f"❌ Failed to read research file: {e}")
        return False

    # Build email
    subject = f"Thunderbird Wing — Claude Integration Research ({research_file.name})"

    body = f"""Commander,

Research findings on 3rd-party Claude integrators, agentic models, and voice control have been completed and saved to the documentation folder.

FILE: {research_file.name}
LOCATION: {research_file}

---

{content}

---

Research completed via headless Claude."""

    # Send email directly from wing (d2mconcierge@gmail.com)
    try:
        print(f"[EMAIL] Sending from d2mconcierge to johnloucks3@gmail.com...")
        result = gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=subject,
            body=body,
            persona_id="COS"  # COS persona for system communications
        )

        if result.get("status") == "success":
            print(f"✅ Email sent successfully to johnloucks3@gmail.com")
            print(f"   Message ID: {result.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Email send failed: {result}")
            return False

    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 send_research_email.py [research_file_path]")
        sys.exit(1)

    research_file = sys.argv[1]
    success = send_research_email(research_file)
    sys.exit(0 if success else 1)
