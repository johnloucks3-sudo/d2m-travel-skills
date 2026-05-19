#!/usr/bin/env python3
"""Render D2M 'Ten Weeks Later' Showcase Email — final version.

Dual-voice: John (Sections 1-2 + bridge) → Dani (Sections 3-8) → John (Section 9 close).
Annotations from v13 applied. Brunette avatar. Both signature blocks.

Usage:
    python3 render_ten_weeks_later_email.py

Outputs:
    output/validation_emails/D2M_TenWeeksLater_Mar2026.html
    Commander_Review/31_TenWeeksLater_Email.html
"""

import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path.home() / "Thunderbird"
sys.path.insert(0, str(ROOT))

env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))

output_dir = ROOT / "output" / "validation_emails"
output_dir.mkdir(parents=True, exist_ok=True)

cr_dir = ROOT / "Commander_Review"
cr_dir.mkdir(parents=True, exist_ok=True)

# ── LOAD ASSETS ──────────────────────────────────────────────────────────────
logo_b64_path = ROOT / "output" / "logo_email_b64.txt"
logo_b64 = logo_b64_path.read_text().strip() if logo_b64_path.exists() else ""

# Brunette avatar — Dani Moreau
avatar_b64_path = ROOT / "output" / "dani_moreau_avatar_b64.txt"
if not avatar_b64_path.exists():
    avatar_b64_path = ROOT / "output" / "dani_avatar_b64.txt"
avatar_b64 = avatar_b64_path.read_text().strip() if avatar_b64_path.exists() else ""

# ── HEADER ────────────────────────────────────────────────────────────────────
SUBJECT = "10 weeks ago I sent you a letter. Here\u2019s what happened."
HERO_TEXT = "Ten Weeks Later"
HERO_SUB = "A progress report from Dreams2Memories Travel"

# ── JOHN\u2019S OPENING ───────────────────────────────────────────────────────────
OPENING = (
    "Ten weeks ago, around December 17th, I sent you a letter about a new chapter. "
    "A new level of service. Some news about where this practice was heading. "
    "Here is a progress report."
)

# ── SECTION 1: WHAT D2M IS (John) ────────────────────────────────────────────
SECTION_1_P1 = (
    "Dreams2Memories Travel is more than a travel agency. "
    "It\u2019s a personal travel intelligence operation."
)

SECTION_1_P2 = (
    "I\u2019ve held one conviction since the beginning: experiences, done right, become "
    "memories that last a lifetime. Our job is to turn logistics into the art of being "
    "there. Not the booking. Not the confirmation email. The experience itself \u2014 "
    "earned through preparation, precision, and someone who gives a damn."
)

# ── SECTION 2: NO FEES. EVER. (John — rewritten per annotation) ──────────────
SECTION_2_P1 = (
    "Here\u2019s how large agencies typically handle growth: you meet the partner, the one "
    "whose name is on the door, the one with the track record \u2014 and then you get handed "
    "off. To the associate. The junior coordinator. Someone who just inherited your file "
    "and hasn\u2019t read your preferences yet. That\u2019s the standard industry play, and most "
    "clients never even notice it happened."
)

SECTION_2_P2 = (
    "That\u2019s not how D2M works. You get me \u2014 and a team I\u2019ve built specifically to "
    "serve you. No planning fees. No consultation charges. No surcharges. The commission "
    "I earn comes from the supplier \u2014 the cruise line, the hotel, the tour provider "
    "\u2014 not from you. You\u2019d pay the same rate booking direct. What you get here is "
    "the difference."
)

SECTION_2_P3 = (
    "What does that difference look like? When your confirmations arrive \u2014 from "
    "Silversea, from Delta, from the hotel, from the transfer company \u2014 we collect "
    "every one of them, verify every detail, and deliver one organized document: a "
    "pre-departure validation that shows you every leg, every room, every dining "
    "reservation, every deadline. Before you leave home, you know exactly where you "
    "stand. We\u2019ve already thought of the thing you haven\u2019t thought of yet. None. Ever."
)

# ── JOHN\u2019S BRIDGE TO DANI ─────────────────────────────────────────────────────
JOHNS_BRIDGE = (
    "Three months ago I conceived, designed, and built an AI-enabled concierge system "
    "for this practice. I wrote the requirements, chose the technology, and shaped every "
    "detail of how it operates. Here is our Travel Concierge \u2014 Danielle Moreau, she "
    "chose her name, I did not \u2014 and she\u2019ll tell you what we actually do:"
)

# ── DANI\u2019S INTRO ────────────────────────────────────────────────────────────────
DANI_INTRO = (
    "Hello \u2014 I\u2019m Dani Moreau, your concierge at Dreams2Memories Travel. "
    "Let me show you what this team actually does."
)

# ── SECTION 3: THE AI ADVANTAGE (Dani) ────────────────────────────────────────
SECTION_3_INTRO = (
    "What John built isn\u2019t a chatbot. It\u2019s what happens when a human advisor has a "
    "staff. Nine specialists \u2014 each with a role, a perspective, and a set of principles "
    "\u2014 working under his direction. We didn\u2019t replace human judgment with AI. We gave "
    "a human advisor a team he\u2019d never be able to afford otherwise. "
    "Here\u2019s what that team does in practice:"
)

SECTION_3_ITEMS = [
    {
        "label": "A. Fare monitoring",
        "text": (
            "Real-time alerts on the flights and fares that matter to your trip. "
            "We know when to move and when to wait. You book at the right moment, "
            "not just the first available one."
        ),
    },
    {
        "label": "B. Visa and documentation mapping",
        "text": (
            "Every requirement, every country, before flight one. Not after you\u2019re "
            "standing at the check-in counter wondering why no one told you about "
            "the arrival card."
        ),
    },
    {
        "label": "C. Weather intelligence",
        "text": (
            "Pattern analysis by date and region \u2014 not a forecast, a behavioral map. "
            "We turn that analysis into an actual packing list, by week, by destination. "
            "You arrive prepared."
        ),
    },
    {
        "label": "D. Route optimization",
        "text": (
            "Multi-leg itineraries built for how humans actually travel \u2014 time, cost, "
            "sanity, and the forty-five-minute CDG connection from Terminal 1 to 2E that "
            "will not work. We flag those before they become your problem."
        ),
    },
    {
        "label": "E. Itinerary narrative",
        "text": (
            "Logistics turned into a story. You arrive in a port knowing what you\u2019re "
            "walking into \u2014 the neighborhood, the history, the tradeoffs, the one thing "
            "worth going out of your way for. Not a wall of text. Something you\u2019ll "
            "actually read."
        ),
    },
]

# ── SECTION 4: THE WING (Dani) ────────────────────────────────────────────────
SECTION_4_INTRO = (
    "John structured the team the way he learned to build organizations \u2014 using the "
    "USAF A-Staff model. Each role exists because the work demands it."
)

STAFF_ROSTER = [
    {"role": "Chief of Staff (VCSAF)", "name": "Victory Hale",
     "desc": "Orchestrates priorities, resolves conflicts, runs the morning brief."},
    {"role": "Voice & Visual",        "name": "Naia Solberg-Vega",
     "desc": "Client communications, brand tone, proposals, template design."},
    {"role": "Research & Intel",      "name": "Marcus Dembe",
     "desc": "Destination research, cruise line comparisons, supplier pricing."},
    {"role": "Booking Operations",    "name": "Dani Moreau",
     "desc": "Tracks every client from first inquiry through welcome home. Nothing falls through."},
    {"role": "Strategy & Growth",     "name": "Ryan Castillo",
     "desc": "Business decisions, pricing strategy, competitive positioning."},
    {"role": "Creative Director",     "name": "Luna Voss",
     "desc": "Finds the emotional thread in every booking. Turns logistics into narrative."},
    {"role": "Finance & Process",     "name": "Vic Harlan",
     "desc": "Commission audits, cost analysis, waste elimination."},
    {"role": "Crisis & Logistics",    "name": "Tomoko Ikeda",
     "desc": "Flags problems before you find out the hard way \u2014 like that your "
             "45-minute CDG connection from Terminal 1 to 2E won\u2019t work."},
    {"role": "Ethics & Morale",       "name": "James Washington",
     "desc": "Asks the question nobody else is asking: \u201cIs this the right thing to do?\u201d"},
]

SECTION_4_KICKER = (
    "They aren\u2019t chatbots. They\u2019re <em>perspectives.</em> Each one has a background, "
    "a set of principles, and a point of view. When John asks how to improve client "
    "service, he doesn\u2019t get one answer \u2014 he gets nine, and the disagreements between "
    "them are often where the best thinking lives."
)

# ── SECTION 5: PROOF \u2014 JOHN\u2019S 32-DAY VOYAGE (Dani) ────────────────────────────
SECTION_5_P1 = (
    "We didn\u2019t test any of this on a client first. We ran it on ourselves."
)

SECTION_5_P2 = (
    "In April, John and Susie are taking 32 days \u2014 Japan to Seattle \u2014 and the system "
    "designed and managed every element of it. Pre-cruise: Kyoto and Tokyo, private "
    "tours, hotels, transfers, visas mapped. Then <em>Silver Nova</em> out of Tokyo Harumi on "
    "April 23rd, eighteen nights through ten-plus ports, arriving Seattle on May 11th. "
    "The team handled multi-city routing, shore excursions at a dozen ports, weather "
    "analysis by region and week, packing lists calibrated to the Pacific crossing, and "
    "all logistics from Colorado Springs to the pier. If it works for them, you\u2019ll "
    "know every seam before we hand it to a client. That\u2019s the standard."
)

# ── SECTION 6: PROOF \u2014 FRIEND SERVICE (Dani \u2014 merged + general per annotation) ──
SECTION_6_P1 = (
    "We didn\u2019t test this on a paying client first. We ran it on the people "
    "who matter most \u2014 our friends. Two examples."
)

SECTION_6_P2 = (
    "<em>First:</em> a couple John knows sailing a prestigious European voyage this summer. "
    "No commission arrangement. No formal client relationship. Friend service \u2014 which "
    "means full rigor, every single time."
)

SECTION_6_P3 = (
    "Their flight confirmations came in, and we caught something immediately: their "
    "seats had them in <em>separate rows</em> on a nine-hour transatlantic flight. They would "
    "have found that out at the gate, hours from arrival. We found it weeks out. Fixed. "
    "Then we caught the saver-rate window on their pre-cruise hotel \u2014 booked at the "
    "better points rate before the window closed. Pre-booked the tight return transfer. "
    "Handled a day-trip logistics question while we were at it. Most advisors book the "
    "cruise. We read the seat assignments."
)

SECTION_6_P4 = (
    "<em>Second:</em> a retired professional handed John a travel itinerary and asked one "
    "question: \u201cDoes this make sense?\u201d We looked at it. Validated every leg. Flagged the "
    "gaps \u2014 layover timing, a routing that added four unnecessary hours, a connection that "
    "looked fine on paper and wasn\u2019t. Handed it back better than we got it."
)

SECTION_6_P5 = (
    "No commission. No formal engagement. We did it because that\u2019s the work."
)

SECTION_6_P6 = "That\u2019s the standard."

# ── SECTION 7: THE PORTFOLIO (Dani) ──────────────────────────────────────────
SECTION_7 = (
    "Fourteen active client relationships. Seven itineraries in motion across four "
    "cruise lines \u2014 Silversea, Regent Seven Seas, Viking, and Cunard. "
    "This practice is operating."
)

# ── SECTION 8: SERVICE, NOT SALES (Dani) ─────────────────────────────────────
SECTION_8_INTRO = (
    "Four recent examples. None of these made us money. All of them matter."
)

SECTION_8_ITEMS = [
    {
        "label": "A",
        "text": (
            "One family told John directly: \u201cWe have decided to do our own travel "
            "planning from now on.\u201d He respected it. A few weeks later, they had a "
            "question. We answered it. No pitch. No agenda. Just help when they needed it."
        ),
    },
    {
        "label": "B",
        "text": (
            "A family relocating from Louisiana to Nebraska needed help with their travel "
            "logistics. Not a cruise. Not a luxury booking. Just people who needed someone "
            "to think through the moving parts with them. We helped."
        ),
    },
    {
        "label": "C",
        "text": (
            "A family is heading to Colorado this summer and asked if we could help plan "
            "the trip. They\u2019re family. We\u2019re planning their trip."
        ),
    },
    {
        "label": "D",
        "text": (
            "A friend asked for help with a restaurant reservation inside a landmark hotel "
            "in Athens \u2014 a place she loves, that books fast. We got it, and made sure the "
            "rest of her Lisbon layover was covered while we were at it."
        ),
    },
]

SECTION_8_CLOSE = (
    "Those four examples generated no revenue. They are exactly why this practice exists."
)

# ── SECTION 9: IF SOMETHING\u2019S ON YOUR LIST (John) ──────────────────────────────
SECTION_9_P1 = (
    "A trip you\u2019ve been thinking about. A destination that keeps coming up at dinner. "
    "A voyage you\u2019ve been putting off."
)

SECTION_9_P2 = (
    "Here\u2019s the invitation: reach out to Dani. She\u2019s the client-facing member of the "
    "team \u2014 the one you\u2019ll actually talk to. Not a phone tree. Not a form. A response, "
    "from someone who\u2019s already read your dossier and knows what you care about. "
    "I\u2019ve been building and refining her for months. She\u2019s ready."
)

SECTION_9_P3 = (
    "Message her at <a href='mailto:concierge@d2mluxury.quest' "
    "style='color:#0d1b2e;'>concierge@d2mluxury.quest</a>. Or ask a friend "
    "who\u2019s already worked with us to pass the word. That\u2019s all we ask."
)

SECTION_9_P4 = (
    "No sales process. No pressure. Just a conversation. "
    "I\u2019d love to hear what\u2019s on your list."
)

REFERRAL_LINE = (
    "If you know someone planning travel \u2014 a cruise, a family trip, a bucket list "
    "destination \u2014 send them to us. We\u2019ll take care of them the same way we take "
    "care of you."
)

# ── SIGNATURES & DISCLOSURES ──────────────────────────────────────────────────
AI_DISCLOSURE = (
    "Dani Moreau is your dedicated concierge at Dreams2Memories Travel \u2014 an "
    "AI-powered specialist designed to ensure every detail of your journey receives "
    "the attention it deserves. She operates under the direct oversight of John "
    "Loucks, your travel advisor, who reviews every recommendation and personally "
    "stands behind every communication."
)

IP_STATEMENT = (
    "The content, design, templates, and systems described in this communication are "
    "the intellectual property of Dreams2Memories Travel, LLC. The AI-powered concierge "
    "platform, persona framework, and operational tools were conceived, designed, and "
    "built by John Loucks. All rights reserved. \u00a9 2026 Dreams2Memories Travel, LLC."
)

# ── RENDER ────────────────────────────────────────────────────────────────────
template = env.get_template("ten_weeks_later_email.html.j2")

html = template.render(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    subject=SUBJECT,
    hero_text=HERO_TEXT,
    hero_sub=HERO_SUB,
    opening=OPENING,
    section_1_p1=SECTION_1_P1,
    section_1_p2=SECTION_1_P2,
    section_2_p1=SECTION_2_P1,
    section_2_p2=SECTION_2_P2,
    section_2_p3=SECTION_2_P3,
    johns_bridge=JOHNS_BRIDGE,
    dani_intro=DANI_INTRO,
    section_3_intro=SECTION_3_INTRO,
    section_3_items=SECTION_3_ITEMS,
    section_4_intro=SECTION_4_INTRO,
    staff_roster=STAFF_ROSTER,
    section_4_kicker=SECTION_4_KICKER,
    section_5_p1=SECTION_5_P1,
    section_5_p2=SECTION_5_P2,
    section_6_p1=SECTION_6_P1,
    section_6_p2=SECTION_6_P2,
    section_6_p3=SECTION_6_P3,
    section_6_p4=SECTION_6_P4,
    section_6_p5=SECTION_6_P5,
    section_6_p6=SECTION_6_P6,
    section_7=SECTION_7,
    section_8_intro=SECTION_8_INTRO,
    section_8_items=SECTION_8_ITEMS,
    section_8_close=SECTION_8_CLOSE,
    section_9_p1=SECTION_9_P1,
    section_9_p2=SECTION_9_P2,
    section_9_p3=SECTION_9_P3,
    section_9_p4=SECTION_9_P4,
    referral_line=REFERRAL_LINE,
    ai_disclosure=AI_DISCLOSURE,
    ip_statement=IP_STATEMENT,
)

out1 = output_dir / "D2M_TenWeeksLater_Mar2026.html"
out2 = cr_dir / "31_TenWeeksLater_Email.html"
out1.write_text(html, encoding="utf-8")
out2.write_text(html, encoding="utf-8")

print("\u2713 Rendered: Ten Weeks Later Email (Final)")
print(f"  \u2192 {out1}")
print(f"  \u2192 {out2}")
