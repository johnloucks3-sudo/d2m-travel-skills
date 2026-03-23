#!/usr/bin/env python3
"""Create Lyons Athens Correspondence as a Google Doc."""

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

SERVICE_ACCOUNT_FILE = '/home/john/Thunderbird/config/service_account.json'

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

docs_service = build('docs', 'v1', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

# Create blank doc
doc = docs_service.documents().create(body={'title': 'Lyons Athens — Correspondence Draft (23 MAR 2026)'}).execute()
doc_id = doc['documentId']
print(f"Created doc: {doc_id}")

# Share with Commander
drive_service.permissions().create(
    fileId=doc_id,
    body={'type': 'user', 'role': 'writer', 'emailAddress': 'johnloucks3@gmail.com'},
    fields='id'
).execute()
print("Shared with johnloucks3@gmail.com")

# Build requests to populate the doc
requests = []

def heading1(text):
    return [
        {'insertText': {'location': {'index': 1}, 'text': text + '\n'}},
        {'updateParagraphStyle': {
            'range': {'startIndex': 1, 'endIndex': 1 + len(text) + 1},
            'paragraphStyle': {'namedStyleType': 'HEADING_1'},
            'fields': 'namedStyleType'
        }}
    ]

def heading2(text, idx):
    return [
        {'insertText': {'location': {'index': idx}, 'text': text + '\n'}},
        {'updateParagraphStyle': {
            'range': {'startIndex': idx, 'endIndex': idx + len(text) + 1},
            'paragraphStyle': {'namedStyleType': 'HEADING_2'},
            'fields': 'namedStyleType'
        }}
    ]

# Build content as a series of insertText requests (appended in reverse order since index=1 inserts at top)
# Easier: build full text, then insert, then apply styles

full_text = """CORRESPONDENCE DRAFT — Lyons Athens Pre-Cruise Night
Dossier: Nancy & Ken Lyons  |  Hotel Grande Bretagne  |  August 10, 2026
Prepared: March 23, 2026  |  Status: DRAFT — Pending Commander Review

───────────────────────────────────────────────────────────

EMAIL 1 OF 2 — Hotel Grande Bretagne (Vendor)
To: reservations@grandebretagne.gr (confirm before send)
CC: concierge@grandebretagne.gr
From: concierge@d2mluxury.quest
Subject: Dinner Reservation Request — GB Roof Garden — August 10, 2026 — Party of 2

Dear Grande Bretagne Reservations Team,

I am writing on behalf of Nancy and Ken Lyons, who will be your guests on the evening of August 10, 2026. They are checking in that day and will be boarding the Seven Seas Splendor the following morning for a transatlantic voyage.

We would like to request a dinner reservation at the GB Roof Garden for the evening of August 10 — party of two.

The Lyons are celebrating the beginning of a remarkable journey, and we would be grateful if the team could accommodate them with a table offering a view of the Acropolis, if available. They are gracious, easy guests — no dietary restrictions or special accommodations have been noted at this time.

If you are able to confirm availability, please reply with your preferred reservation time windows. We will align with the Lyons' arrival and prefer a seating no earlier than 7:00 PM.

Thank you in advance for your assistance. Dreams2Memories Travel is a luxury travel consultancy based in Colorado — we look forward to placing more guests at the Grande Bretagne and are grateful for any courtesy you can extend to our clients.

Thank you,

Danielle Moreau
Luxury Travel Concierge
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest

───────────────────────────────────────────────────────────

EMAIL 2 OF 2 — Nancy & Ken Lyons (Clients)
To: nancylyons73@outlook.com
CC: klyons3@bellsouth.net
From: concierge@d2mluxury.quest
Subject: Your Athens Evening — Dinner & Logistics Update

Dear Nancy,

John mentioned you'd been looking for help with your Athens night, and I'm so glad he connected us. You have a wonderful evening ahead of you — and I want to make sure everything is in place before you land.

Hotel Grande Bretagne — August 10
You're in wonderful hands. The Grande Bretagne is one of the grand dames of European hospitality — Syntagma Square, white-gloved service, and the Acropolis glowing just above the city. You couldn't ask for a better landing spot the night before you board Splendor.

Dinner — GB Roof Garden
I've reached out to the hotel's reservations team on your behalf to request a table at the GB Roof Garden — their rooftop restaurant with one of the most iconic Acropolis views in Athens. I'll follow up as soon as I have a confirmed time for you. In the meantime, if you have a seating preference (early, mid-evening, late), please let me know and I'll make sure to specify.

Transfers — Two Legs
I'm working on both legs of your ground transportation:
  • ATH airport → Hotel Grande Bretagne — August 10, arrival day
  • Hotel Grande Bretagne → Piraeus port — August 11, embarkation morning

To confirm your pickup time from the airport, could you share your arrival flight details when you have a moment? Even an approximate landing time is helpful — I'll build in buffer for customs and baggage.

The Piraeus transfer I'll size to your embarkation window once we have your boarding time from Regent.

What's Confirmed
  ✓ Hotel Grande Bretagne (August 10–11)
  ✓ Dinner request submitted to GB Roof Garden

What's In Progress
  • Dinner confirmation (awaiting hotel reply)
  • ATH arrival transfer (need your flight details)
  • Hotel → Piraeus transfer (sizing to embarkation window)

I'll be in touch as each piece locks in. You're in good hands, Nancy — just enjoy the journey.

Thank you,

Danielle
Luxury Travel Concierge
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest

───────────────────────────────────────────────────────────

COMMANDER REVIEW NOTES

• Email 1 (Hotel): Ready to send pending Commander approval. Confirm correct reservations email before deploying.
• Email 2 (Nancy): Warm Dani voice applied. Missing her flight arrival info — the email prompts her for it.
• Transfers: Not yet sourced — Blacklane/Welcome Pickups/Mozio search needed once Nancy provides flight details.
• Send Gate: Both addresses are OUTSIDE the wing. Commander approval required before any send.

───────────────────────────────────────────────────────────
Prepared by COS (Col Victoria Hale) — Thunderbird Wing
23 MAR 2026 · 01:16 UTC
"""

# Insert all text at once
requests = [
    {
        'insertText': {
            'location': {'index': 1},
            'text': full_text
        }
    }
]

# Apply heading style to title line (line 1)
title = 'CORRESPONDENCE DRAFT — Lyons Athens Pre-Cruise Night'
title_end = len(title) + 2  # +1 for \n, +1 for 1-based index start

requests.append({
    'updateParagraphStyle': {
        'range': {'startIndex': 1, 'endIndex': title_end},
        'paragraphStyle': {'namedStyleType': 'HEADING_1'},
        'fields': 'namedStyleType'
    }
})

result = docs_service.documents().batchUpdate(
    documentId=doc_id,
    body={'requests': requests}
).execute()

print(f"Content written. Doc URL: https://docs.google.com/document/d/{doc_id}/edit")
