#!/usr/bin/env python3
"""
Create 4 Spencer Grand Tour 2027 RFQ drafts in d2mconcierge.
Labels each THUNDERBIRD-Commander-Review.
"""

import sys
import os
sys.path.insert(0, '/home/john/Thunderbird')

from core.email.thunderbird_gmail import gmail_create_draft_sync

# ── RFQ 1 — Carrani Tours ──────────────────────────────────────────────────
rfq1_body = """Dear Carrani Tours Team,

Dreams2Memories Travel, LLC is a US-based luxury travel agency requesting a quote for a private Rome program on behalf of a multigenerational client group.

Details: 12 passengers, arriving Rome June 12, departing June 15, 2027. Group includes 2 young children (ages 5 and 2, with strollers). Celebration occasion — anniversary and birthday.

We are seeking a 3-day private program covering Vatican Museums (including Sistine Chapel), Colosseum, and Roman Forum. Requirements: private licensed guide, skip-the-line access throughout, and luxury motor coach or executive van transport sized for the group and stroller logistics.

Please quote two tiers: (1) standard luxury private program and (2) premium tier with after-hours or exclusive access options where available.

Please include per-person and group pricing, inclusions list, and availability confirmation.

Warm regards,
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
719-291-0742"""

# ── RFQ 2 — Renata Travel (web form) ──────────────────────────────────────
rfq2_body = """SUBMIT VIA: luxury.renatatraveldmc.com contact form | Paste body below into form message field

---

Dear Renata Travel Team,

Dreams2Memories Travel, LLC is a US-based luxury travel agency and we are building a bespoke Rome program for a high-value client group — 12 passengers, multigenerational family, June 12–15, 2027. Budget is open to premium experiences.

We are seeking a white-glove 3-day Rome program and request your proposal to include: private art historian guides, luxury transfer from Fiumicino (FCO) upon arrival, Vatican after-hours or exclusive-access options if available, and full family-friendly logistics (group includes 2 small children with strollers).

This is a milestone celebration (anniversary and birthday) and the client values meaningful, story-rich experiences over standard touring.

Please quote two service tiers: luxury private and ultra-premium. Include per-person pricing, full inclusions, and your availability for the dates noted.

We look forward to your response.

Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
719-291-0742"""

# ── RFQ 3 — Mama Florence (web form + phone) ──────────────────────────────
rfq3_body = """SUBMIT VIA: mamaflorence.com/contacts-mamaflorence OR call +39 055 221138 | Paste body below into form

---

Dear Mama Florence Team,

Dreams2Memories Travel, LLC is a US-based luxury travel agency requesting a quote for a private half-day cooking class in Florence for a client group.

Group size: 8–10 adults (part of a larger 12-pax multigenerational family traveling Italy in June 2027). Preferred window: June 13 or June 14, 2027 — flexible within those two dates. We are interested in a Tuscan-focused menu and a fully private session for the adult members of the group.

Please provide your group rate per person for a private class, available dates within the June 13–14 window, approximate duration, and what is included (market visit, menu, wine, printed recipes, etc.).

Thank you for your time. We look forward to your response.

Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
719-291-0742"""

# ── RFQ 4 — Artisans of Leisure (web form) ────────────────────────────────
rfq4_body = """SUBMIT VIA: artisansofleisure.com quote form | Paste body below into message field

---

Dear Artisans of Leisure Team,

Dreams2Memories Travel, LLC is a US-based luxury travel agency building a 10-day Switzerland program for 8 passengers (multigenerational family, including 2 young children), June 23 – July 2, 2027. Budget tier: ultra-luxury, no constraints.

We are requesting a comprehensive proposal covering: Interlaken, Zermatt, and Zurich with routing and pacing appropriate for a family with small children. Key inclusions requested: private guides and luxury private transport throughout, pre-vetted luxury hotel recommendations with family-appropriate accommodations, Matterhorn experience (Gornergrat or Matterhorn Glacier Paradise access as conditions allow in late June), and full luggage logistics in Zermatt given the car-free zone.

Please quote two service tiers: luxury private and ultra-premium with expanded exclusives.

Include daily structure overview, recommended hotels, per-person pricing, and any seasonal considerations for late June.

Thank you.

Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
719-291-0742"""

drafts = [
    {
        "to": "segreteria@carrani.com",
        "subject": "RFQ — Private Group Rome Program, 12 Pax, Jun 12–15, 2027",
        "body": rfq1_body,
        "label": "Draft 1 (Carrani Tours)"
    },
    {
        "to": "concierge@d2mluxury.quest",
        "subject": "[WEB FORM] RFQ — Luxury Private Rome Program, 12 Pax | luxury.renatatraveldmc.com/contact",
        "body": rfq2_body,
        "label": "Draft 2 (Renata Travel web form)"
    },
    {
        "to": "concierge@d2mluxury.quest",
        "subject": "[WEB FORM / PHONE] RFQ — Private Cooking Class, Mama Florence | mamaflorence.com/contacts-mamaflorence | +39 055 221138",
        "body": rfq3_body,
        "label": "Draft 3 (Mama Florence)"
    },
    {
        "to": "concierge@d2mluxury.quest",
        "subject": "[WEB FORM] RFQ — Luxury Switzerland Program, 8 Pax | artisansofleisure.com quote form",
        "body": rfq4_body,
        "label": "Draft 4 (Artisans of Leisure)"
    },
]

results = []

for i, d in enumerate(drafts, 1):
    print(f"\nCreating {d['label']}...")
    try:
        result = gmail_create_draft_sync(
            to=d["to"],
            subject=d["subject"],
            body=d["body"]
        )
        if result and result.get("id"):
            print(f"  OK — Draft ID: {result['id']}")
            results.append({"draft": d["label"], "id": result["id"], "status": "OK"})
        else:
            print(f"  WARN — Unexpected result: {result}")
            results.append({"draft": d["label"], "id": None, "status": "WARN", "result": str(result)})
    except Exception as e:
        print(f"  ERROR — {e}")
        results.append({"draft": d["label"], "id": None, "status": "ERROR", "error": str(e)})

print("\n\n=== SUMMARY ===")
for r in results:
    status = r["status"]
    draft_id = r.get("id", "N/A")
    print(f"  {r['draft']}: {status} | ID: {draft_id}")

# Write results to a temp file for the notification step
import json
with open("/tmp/spencer_rfq_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResults written to /tmp/spencer_rfq_results.json")
