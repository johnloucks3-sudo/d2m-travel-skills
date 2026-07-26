#!/usr/bin/env python3
"""
Draft response for Amy Darrow special accommodations & room inquiries.
"""
from core.email.thunderbird_gmail import gmail_create_draft_sync

def main():
    to = "amy.darrow@me.com"
    subject = "Re: Special accommodations & Stateroom details — D2M Travel Services"
    body = """Dear Amy,

Thank you for reaching out! Here are the details regarding your special accommodations and stateroom amenities:

1. Special Accommodations (Flight & Cruise):
   - Airline & Cruise Port Assistance: We will submit wheelchair assistance requests for both your flights and pier embarkation/disembarkation. Priority boarding access will be linked directly to your booking profiles.

2. Stateroom Blow Dryer & Amenities:
   - All staterooms feature standard high-efficiency wall-mounted hair dryers. If you prefer professional salon-grade tools, you are welcome to bring your personal styling dryer (standard 110V/220V dual voltage supported).

3. Mattress & Bedding Requests:
   - Modern luxury vessels feature custom ergonomic mattresses. We can submit a pre-arrival request to the Chief Housekeeper for extra firm topper adjustments or additional supportive pillowing.

4. Advance In-Room Requests:
   - Special concierge requests (extra towels, specific minibar setups, distilled water, etc.) can be pre-loaded through our agency concierge channel before embarkation.

We will finalize these requests and confirm once all supplier confirmations are attached to your dossier.

Warm regards,

John Loucks
DREAMS2MEMORIES TRAVEL, LLC
Authorized by: John A Loucks III
Owner
"""
    draft = gmail_create_draft_sync(to, subject, body, persona_id='CONCIERGE')
    print(f"Draft created successfully: {draft}")

if __name__ == "__main__":
    main()
