import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.email.thunderbird_gmail import gmail_create_draft_sync

subject = "Your August 2026 Seven Seas Splendor Itinerary"
body = """Hi Nancy,

We have finalized the itinerary for your upcoming cruise on the Seven Seas Splendor! We've meticulously reviewed and included all the details you provided, verifying everything to ensure accuracy. 

Thank you so much for giving us access to your personal Regent account—it was immensely helpful in pulling everything together! We also searched for and included high-quality pictures of the Splendor and your ports of call to give you a great preview of the trip. 

Attached to this email, you'll find:
1. An HTML version of the itinerary, which is perfectly formatted for viewing on a phone or iPad.
2. A PDF version, which is ideal if you'd prefer to print it out.

We are more than willing and able to help you with any further planning you might need. Also, we are currently working on a Lisbon City Guide with ideas for sightseeing close to the port, which we will send over soon!

Please let us know if you have any questions or need any adjustments.

Best,
Dani & John
"""

try:
    draft = gmail_create_draft_sync(
        to="johnloucks3@gmail.com",
        subject=subject,
        body=body,
        attachment_paths=["/home/john/Thunderbird/cruises_web/itinerary_splendor_lyons.html", "/home/john/Thunderbird/cruises_web/itinerary_splendor_lyons.pdf"]
    )
    print("Draft response:")
    print(draft)
except Exception as e:
    print(f"Error: {e}")
