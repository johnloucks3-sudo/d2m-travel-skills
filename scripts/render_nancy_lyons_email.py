#!/usr/bin/env python3
"""Render Dani Moreau introduction email to Nancy Lyons — Splendor Historic Horizons."""

import sys
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ROOT = Path.home() / "Thunderbird"
sys.path.insert(0, str(ROOT))

env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
template = env.get_template("dani_validation_email.html.j2")

output_dir = ROOT / "output" / "validation_emails"
output_dir.mkdir(parents=True, exist_ok=True)

logo_b64 = (ROOT / "output" / "logo_email_b64.txt").read_text().strip()
avatar_b64_path = ROOT / "output" / "dani_avatar_b64.txt"
avatar_b64 = avatar_b64_path.read_text().strip() if avatar_b64_path.exists() else ""

JOHNS_NOTE = (
    "Nancy — I wanted to introduce you to something new I\u2019m trying in my practice. "
    "Dani Moreau is an AI-powered concierge I\u2019ve built to help me stay on top of every "
    "detail for my clients\u2019 trips. I personally review everything she sends and stand behind "
    "every word. If getting an email from an AI feels strange or isn\u2019t your thing, I completely "
    "understand \u2014 just let me know and we\u2019ll keep everything direct. No hard feelings at all.\n\n"
    "I want to be clear: this is NOT a sales pitch or an attempt to sell you anything. You and "
    "Ken are friends, and this is simply a service I\u2019m offering because I can. If Dani can help "
    "make your Splendor voyage even a little more organized or enjoyable, that\u2019s a win. "
    "Think of it like having a friend who happens to have a really good travel assistant."
)

nancy = template.render(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    ship_name="Regent Seven Seas Splendor",
    voyage_description="Historic Horizons \u00b7 Athens to New York \u00b7 Aug 11 \u2013 Sep 6, 2026 \u00b7 26 Nights",
    payment_date="N/A",
    balance_due="N/A \u2014 Your Booking",
    hero_text="Historic Horizons",
    personal_note=JOHNS_NOTE,
    subject="A Little Help for Your Splendor Voyage",
    greeting="Hi Nancy,",
    intro_text=(
        "My name is Dani Moreau, and I\u2019m the concierge intelligence behind Dreams2Memories Travel. "
        "John asked me to reach out because he\u2019d love to put together a complete itinerary package "
        "for your upcoming Splendor voyage \u2014 the kind of organized, all-in-one-place reference that "
        "makes a 26-night transatlantic feel effortless rather than overwhelming."
    ),
    suite_number="TBD",
    deck_number="TBD",
    flights=[
        "Outbound to Athens \u2014 send me your flight details when you have them",
        "Return from New York \u2014 same, whenever you\u2019re ready",
    ],
    flight_notes="No rush on any of this. Whenever you have details, just forward them my way and I\u2019ll build everything into one clean package.",
    hotel_transfers=[
        "Pre-cruise hotel in Athens? \u2014 let me know if you\u2019re staying",
        "Post-cruise in New York? \u2014 same",
        "Airport transfers \u2014 I can research and recommend options",
    ],
    excursion_count="26",
    excursions=[
        {"date": "Aug 11", "port": "Athens (Piraeus)", "name": "Embarkation \u2014 5:00 PM", "cost": ""},
        {"date": "Aug 13", "port": "Malta", "name": "8:00 AM \u2013 3:00 PM", "cost": ""},
        {"date": "Aug 14", "port": "Naples", "name": "11:00 AM \u2013 8:00 PM", "cost": ""},
        {"date": "Aug 15", "port": "Rome (Civitavecchia)", "name": "8:00 AM \u2013 8:00 PM", "cost": ""},
        {"date": "Aug 16", "port": "Florence/Pisa (Livorno)", "name": "8:00 AM \u2013 8:00 PM", "cost": ""},
        {"date": "Aug 17", "port": "Cannes", "name": "7:00 AM \u2013 6:00 PM", "cost": ""},
        {"date": "Aug 18\u201319", "port": "Barcelona", "name": "Overnight \u2014 11:00 AM to 8:00 PM", "cost": ""},
        {"date": "Aug 21", "port": "Malaga", "name": "8:00 AM \u2013 8:00 PM", "cost": ""},
        {"date": "Aug 22", "port": "Portim\u00e3o", "name": "10:00 AM \u2013 6:00 PM", "cost": ""},
        {"date": "Aug 23\u201324", "port": "Lisbon", "name": "Overnight \u2014 7:00 AM to 12:00 PM", "cost": ""},
        {"date": "Aug 26", "port": "Ponta Delgada (Azores)", "name": "10:00 AM \u2013 7:00 PM", "cost": ""},
        {"date": "Aug 30", "port": "St. John\u2019s, Newfoundland", "name": "7:00 AM \u2013 5:00 PM", "cost": ""},
        {"date": "Aug 31", "port": "Saint Pierre & Miquelon", "name": "8:00 AM \u2013 5:00 PM", "cost": ""},
        {"date": "Sep 1", "port": "Sydney, Nova Scotia", "name": "8:00 AM \u2013 5:00 PM", "cost": ""},
        {"date": "Sep 2", "port": "Halifax", "name": "10:00 AM \u2013 6:00 PM", "cost": ""},
        {"date": "Sep 3\u20134", "port": "Boston", "name": "Overnight \u2014 4:00 PM to 4:00 PM", "cost": ""},
        {"date": "Sep 5", "port": "Newport, Rhode Island", "name": "11:30 AM \u2013 6:30 PM", "cost": ""},
        {"date": "Sep 6", "port": "New York", "name": "Disembarkation \u2014 7:00 AM", "cost": ""},
    ],
    upcoming=[
        {"date": "Anytime", "description": "Send Dani your flight confirmations, hotel plans, or excursion picks"},
        {"date": "Anytime", "description": "Ask about port-specific dining, tours, or logistics for any of your 15 ports"},
        {"date": "Aug 11", "description": "Embarkation day \u2014 Athens"},
    ],
    action_items=[
        "Forward me any flight confirmations \u2014 I\u2019ll add them to your itinerary package.",
        "If you\u2019ve booked shore excursions through Regent or on your own, send those too \u2014 I\u2019ll organize everything by port and date.",
        "Interested in specialty dining onboard? I can help with recommendations and timing.",
        "Want city-specific tips for any of your ports? Barcelona, Lisbon, Boston, Newport \u2014 I\u2019ve got you. Just ask.",
        "If you reply to this email, I\u2019ll make sure John sees it right away.",
    ],
    closing_text=(
        "There\u2019s absolutely no obligation here \u2014 just a friend\u2019s offer to help make a spectacular "
        "voyage even better. Send me as much or as little as you\u2019d like, whenever you\u2019re ready. "
        "I\u2019m here for whatever you need."
    ),
)

# Save HTML
(output_dir / "Lyons_Splendor_Introduction.html").write_text(nancy, encoding="utf-8")

# Save to Commander Review
cr_dir = ROOT / "Commander_Review"
(cr_dir / "28_Lyons_Splendor_Introduction.html").write_text(nancy, encoding="utf-8")

print("\u2713 Rendered Nancy Lyons introduction email:")
print(f"  \u2192 {output_dir}/Lyons_Splendor_Introduction.html")
print(f"  \u2192 {cr_dir}/28_Lyons_Splendor_Introduction.html")

if "--send" in sys.argv:
    from thunderbird_gmail import _get_gmail_service
    service = _get_gmail_service()
    msg = MIMEMultipart("alternative")
    msg["to"] = "johnloucks3@gmail.com"
    msg["from"] = '"Dani Moreau \u2014 Concierge Intelligence" <concierge@d2mluxury.quest>'
    msg["reply-to"] = "johnloucks3@gmail.com"
    msg["subject"] = "[PREVIEW] Nancy Lyons: Splendor Historic Horizons \u2014 Dani Introduction"
    msg.attach(MIMEText("Preview of Nancy Lyons introduction email. Client To: nancylyons73@outlook.com. View in HTML.", "plain"))
    msg.attach(MIMEText(nancy, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"\u2713 SENT preview to Commander (ID: {sent.get('id')})")
    print(f"  Client To: nancylyons73@outlook.com")
