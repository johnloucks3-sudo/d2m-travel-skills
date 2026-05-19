#!/usr/bin/env python3
"""Render Group 3 Cold Email — all inline styles, Gmail-safe.

Headers: centered + bold
Body: left-justified
Template: D2M stationery (navy banner, cream paper, blue ink, Georgia)
"""

import base64
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path.home() / "Thunderbird"
sys.path.insert(0, str(ROOT))
TOKEN_PATH = ROOT / "gmail_token.json"

# ── BCC LIST (from sent Ten Weeks Later email) ──────────────────────────────
BCC_LIST = [
    "magicm@verizon.net", "ibyumper@aol.com", "ttboyce@electric.net",
    "JFBoyce@protonmail.com", "stef@bbenefits.net", "rob@bbenefits.net",
    "amy.darrow@me.com", "al.ely58@gmail.com", "fysti@hotmail.com",
    "missy.furlow@gmail.com", "john.furlow@tpf.org", "beckygaughan@mac.com",
    "johngaughan2@mac.com", "alredigon2@hotmail.com", "iamheer@outlook.com",
    "cerriamaryannphotography@gmail.com", "nickpack@gmail.com",
    "susanna.loucks@gmail.com", "leslieanichols@gmail.com", "cnuraptor@gmail.com",
    "barbarabuhlerlynes@gmail.com", "kenlyons73@bellsouth.net",
    "nancylyons73@outlook.com", "emcleod@gmail.com", "memcglas@gmail.com",
    "ldmiller7@juno.com", "bmokas@sbcglobal.net", "larry.nichols4811@gmail.com",
    "heidi.nichols1@yahoo.com", "jagperry22@gmail.com",
    "piontek@retiree.ucmo.edu", "rrehfeldt4969@aol.com", "kimrehfeldt@aol.com",
    "timothy46@gmail.com", "lindapchef@aol.com", "jmsciacca@aol.com",
    "willstoycos@gmail.com", "kathrynewalsh@verizon.net",
    "lindywestbrook77@gmail.com", "rwestbrook3@gmail.com", "crnakim@yahoo.com",
]

# ── LOAD LOGO ────────────────────────────────────────────────────────────────
logo_b64_path = ROOT / "output" / "logo_email_b64.txt"
logo_b64 = logo_b64_path.read_text().strip() if logo_b64_path.exists() else ""

avatar_b64_path = ROOT / "output" / "dani_moreau_avatar_b64.txt"
if not avatar_b64_path.exists():
    avatar_b64_path = ROOT / "output" / "dani_avatar_b64.txt"
avatar_b64 = avatar_b64_path.read_text().strip() if avatar_b64_path.exists() else ""

# ── STYLE CONSTANTS (all inline) ─────────────────────────────────────────────
INK = "#0000ff"
PAPER = "#f7f3ea"
SURROUND = "#eee8db"
NAVY = "#0d1b2e"
GOLD = "#c9a84c"
FONT = "Georgia, 'Times New Roman', serif"

P = (f'style="color: {INK}; font-family: {FONT}; font-size: 10.5pt; '
     f'line-height: 1.6; text-align: left; margin: 0 0 14px 0;"')

H = (f'style="color: {INK}; font-family: {FONT}; font-size: 12pt; '
     f'font-weight: bold; text-align: center; margin: 28px 0 12px 0; '
     f'letter-spacing: 1px;"')

HR = f'style="border: none; border-top: 1px solid rgba(201,168,76,0.45); margin: 24px 0;"'

LI = (f'style="color: {INK}; font-family: {FONT}; font-size: 10.5pt; '
      f'line-height: 1.6; text-align: left; margin: 0 0 10px 0;"')


def p(text):
    return f'<p {P}>{text}</p>'


def h(text):
    return f'<p {H}>{text}</p>'


def hr():
    return f'<hr {HR} />'


def li_item(label, text):
    return f'<li {LI}><strong>{label}.</strong> {text}</li>'


# ── BANNER ───────────────────────────────────────────────────────────────────
if logo_b64:
    banner = (
        f'<div style="background-color: {NAVY}; padding: 28px 0; text-align: center; margin: 0;">'
        f'<img src="data:image/png;base64,{logo_b64}" alt="Dreams2Memories Travel" '
        f'style="height: 180px; width: auto; display: inline-block;" />'
        f'</div>'
    )
else:
    banner = (
        f'<div style="background-color: {NAVY}; padding: 28px 0; text-align: center;">'
        f'<span style="font-family: {FONT}; font-size: 22px; color: {GOLD}; letter-spacing: 2px;">'
        f'DREAMS2MEMORIES</span>'
        f'</div>'
    )

# ── HERO ─────────────────────────────────────────────────────────────────────
hero = (
    f'<div style="background-color: {NAVY}; padding: 22px 40px; text-align: center;">'
    f'<p style="font-family: {FONT}; font-size: 14px; color: {GOLD}; '
    f'letter-spacing: 3px; text-transform: uppercase; margin: 0;">Ten Weeks Later</p>'
    f'<p style="font-family: {FONT}; font-size: 11px; color: #8a9ab5; '
    f'letter-spacing: 1.5px; font-style: italic; margin: 6px 0 0 0;">'
    f'A progress report from Dreams2Memories Travel</p>'
    f'</div>'
    f'<div style="height: 2px; background: linear-gradient(90deg, {NAVY} 5%, {GOLD} 30%, {GOLD} 70%, {NAVY} 95%);"></div>'
)

# ── DANI AVATAR BLOCK ────────────────────────────────────────────────────────
if avatar_b64:
    dani_block = (
        f'<table cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">'
        f'<tr>'
        f'<td style="padding-right: 14px; vertical-align: top;">'
        f'<img src="data:image/png;base64,{avatar_b64}" alt="Dani Moreau" width="64" height="64" '
        f'style="width: 64px; height: 64px; border-radius: 50%; border: 2px solid {GOLD};" />'
        f'</td>'
        f'<td style="vertical-align: middle;">'
        f'<strong style="color: {INK}; font-family: {FONT}; font-size: 11pt;">Dani Moreau</strong><br>'
        f'<span style="color: {GOLD}; font-family: {FONT}; font-size: 9pt; '
        f'letter-spacing: 1px;">LUXURY TRAVEL CONCIERGE &middot; DREAMS2MEMORIES TRAVEL</span>'
        f'</td></tr></table>'
    )
else:
    dani_block = (
        f'<p style="color: {INK}; font-family: {FONT}; font-size: 11pt; font-weight: bold; '
        f'margin: 20px 0 4px 0;">Dani Moreau</p>'
        f'<p style="color: {GOLD}; font-family: {FONT}; font-size: 9pt; '
        f'letter-spacing: 1px; margin: 0 0 16px 0;">LUXURY TRAVEL CONCIERGE &middot; DREAMS2MEMORIES TRAVEL</p>'
    )

# ── STAFF TABLE ──────────────────────────────────────────────────────────────
TH = (f'style="background: {NAVY}; color: {GOLD}; font-family: {FONT}; font-size: 9pt; '
      f'letter-spacing: 1px; text-transform: uppercase; padding: 8px 10px; text-align: left;"')
TD = (f'style="color: {INK}; font-family: {FONT}; font-size: 9.5pt; padding: 6px 10px; '
      f'border-bottom: 1px solid #e8e0d0; text-align: left; vertical-align: top;"')
TD_ROLE = (f'style="color: {INK}; font-family: {FONT}; font-size: 9.5pt; padding: 6px 10px; '
           f'border-bottom: 1px solid #e8e0d0; text-align: left; vertical-align: top; font-weight: bold;"')

staff_rows = ""
roster = [
    ("Chief of Staff (VCSAF)", "Victory Hale", "Orchestrates priorities, resolves conflicts, runs the morning brief."),
    ("Voice &amp; Visual", "Naia Solberg-Vega", "Client communications, brand tone, proposals, template design."),
    ("Research &amp; Intel", "Marcus Dembe", "Destination research, cruise line comparisons, supplier pricing."),
    ("Booking Operations", "Dani Moreau", "Tracks every client from first inquiry through welcome home. Nothing falls through."),
    ("Strategy &amp; Growth", "Ryan Castillo", "Business decisions, pricing strategy, competitive positioning."),
    ("Creative Director", "Luna Voss", "Finds the emotional thread in every booking. Turns logistics into narrative."),
    ("Finance &amp; Process", "Vic Harlan", "Commission audits, cost analysis, waste elimination."),
    ("Crisis &amp; Logistics", "Tomoko Ikeda",
     "Flags problems before you find out the hard way \u2014 like that your 45-minute CDG connection from Terminal 1 to 2E won\u2019t work."),
    ("Ethics &amp; Morale", "James Washington",
     "Asks the question nobody else is asking: \u201cIs this the right thing to do?\u201d"),
]
for role, name, desc in roster:
    staff_rows += (
        f'<tr><td {TD_ROLE}>{role}</td>'
        f'<td {TD}><strong>{name}</strong></td>'
        f'<td {TD}>{desc}</td></tr>'
    )

staff_table = (
    f'<table cellpadding="0" cellspacing="0" border="0" '
    f'style="width: 100%; border-collapse: collapse; margin: 12px 0 16px 0;">'
    f'<tr><th {TH}>Role</th><th {TH}>Name</th><th {TH}>What They Do</th></tr>'
    f'{staff_rows}'
    f'</table>'
)

# ── SIGNATURES ───────────────────────────────────────────────────────────────
dani_sig = (
    f'<hr {HR} />'
    f'<table cellpadding="0" cellspacing="0" border="0" style="margin: 0 0 16px 0;">'
    f'<tr>'
)
if avatar_b64:
    dani_sig += (
        f'<td style="padding-right: 14px; vertical-align: top;">'
        f'<img src="data:image/png;base64,{avatar_b64}" alt="Dani Moreau" width="48" height="48" '
        f'style="width: 48px; height: 48px; border-radius: 50%; border: 2px solid {GOLD};" />'
        f'</td>'
    )
dani_sig += (
    f'<td style="vertical-align: top;">'
    f'<strong style="color: {INK}; font-family: {FONT}; font-size: 10pt;">Dani Moreau</strong><br>'
    f'<span style="color: {INK}; font-family: {FONT}; font-size: 9pt;">Luxury Travel Concierge</span><br>'
    f'<span style="color: {INK}; font-family: {FONT}; font-size: 9pt;">DREAMS2MEMORIES TRAVEL</span><br>'
    f'<a href="mailto:concierge@d2mluxury.quest" '
    f'style="color: {INK}; font-family: {FONT}; font-size: 9pt; text-decoration: none;">'
    f'concierge@d2mluxury.quest</a>'
    f'</td></tr></table>'
)

ai_disc = (
    f'<div style="margin: 12px 0 20px 0; padding: 12px 16px; '
    f'background: #f0ece3; border: 1px solid #e0d8c8; border-radius: 3px;">'
    f'<p style="color: #555; font-family: {FONT}; font-size: 9pt; '
    f'line-height: 1.5; font-style: italic; margin: 0; text-align: left;">'
    f'Dani Moreau is your dedicated concierge at Dreams2Memories Travel \u2014 an '
    f'AI-powered specialist designed to ensure every detail of your journey receives '
    f'the attention it deserves. She operates under the direct oversight of John '
    f'Loucks, your travel advisor, who reviews every recommendation and personally '
    f'stands behind every communication.</p></div>'
)

john_sig = (
    f'<hr {HR} />'
    f'<strong style="color: {INK}; font-family: {FONT}; font-size: 10pt;">John Loucks</strong><br>'
    f'<span style="color: {INK}; font-family: {FONT}; font-size: 9pt;">'
    f'Founder &amp; Travel Advisor</span><br>'
    f'<span style="color: {INK}; font-family: {FONT}; font-size: 9pt;">'
    f'DREAMS2MEMORIES TRAVEL, LLC</span><br>'
    f'<span style="color: {INK}; font-family: {FONT}; font-size: 9pt;">'
    f'<a href="mailto:johnloucks3@gmail.com" style="color: {INK}; text-decoration: none;">'
    f'johnloucks3@gmail.com</a> &middot; '
    f'<a href="mailto:concierge@d2mluxury.quest" style="color: {INK}; text-decoration: none;">'
    f'concierge@d2mluxury.quest</a> &middot; (719) 291-0742</span>'
)

ip_block = (
    f'<div style="margin: 24px 0 0 0; text-align: center;">'
    f'<p style="color: #888; font-family: {FONT}; font-size: 8pt; '
    f'line-height: 1.4; font-style: italic; margin: 0;">'
    f'The content, design, templates, and systems described in this communication are '
    f'the intellectual property of Dreams2Memories Travel, LLC. The AI-powered concierge '
    f'platform, persona framework, and operational tools were conceived, designed, and '
    f'built by John Loucks. All rights reserved. \u00a9 2026 Dreams2Memories Travel, LLC.</p></div>'
)

# ── FOOTER ───────────────────────────────────────────────────────────────────
footer = (
    f'<div style="background-color: {NAVY}; padding: 22px 40px; text-align: center;">'
    f'<p style="font-family: {FONT}; font-size: 12px; color: {GOLD}; '
    f'letter-spacing: 2px; margin: 0 0 4px 0;">DREAMS2MEMORIES</p>'
    f'<p style="font-family: {FONT}; font-size: 9px; color: #f5e9c8; '
    f'letter-spacing: 1.5px; font-style: italic; margin: 0 0 8px 0;">'
    f'Curating the voyage of your lifetime</p>'
    f'<p style="font-family: {FONT}; font-size: 10px; color: #d0d8e8; margin: 0 0 4px 0;">'
    f'<a href="mailto:concierge@d2mluxury.quest" style="color: {GOLD}; text-decoration: none;">'
    f'concierge@d2mluxury.quest</a></p>'
    f'<p style="font-family: {FONT}; font-size: 8px; color: #5a6a85; margin: 8px 0 0 0; line-height: 1.4;">'
    f'Florida Seller of Travel # ST1578 &middot; California Seller of Travel No. 2090937-50<br>'
    f'Washington UBID No. 603189022 &middot; Iowa Registered Agency # 1202</p>'
    f'</div>'
)

# ── ASSEMBLE BODY ────────────────────────────────────────────────────────────
body_parts = [
    # Opening
    p("Ten weeks ago, around December 17th, I sent you a letter about a new "
      "chapter. A new level of service. Some news about where this practice was "
      "heading. Here is a progress report."),
    hr(),

    # What D2M Is
    h("What D2M Is"),
    p("Dreams2Memories Travel is more than a travel agency. "
      "It\u2019s a personal travel intelligence operation."),
    p("I\u2019ve held one conviction since the beginning: experiences, done right, "
      "become memories that last a lifetime. Our job is to turn logistics and "
      "planning into the art of being there. Not the booking. Not the confirmation "
      "email. The experience itself \u2014 earned through preparation, precision, and "
      "someone who gives a damn."),
    hr(),

    # No Fees. Ever.
    h("No Fees. Ever."),
    p("Here\u2019s how large agencies typically handle growth: you meet the partner, "
      "the one whose name is on the door or in the email, the one with the track "
      "record \u2014 and then you get handed off. To the associate. The junior "
      "coordinator. Someone who just inherited your file and hasn\u2019t read your "
      "preferences yet. That\u2019s the standard industry play, and most clients never "
      "even notice it happened, until they try to get an answer to a simple question, "
      "and they wait, and they wait. Then, they ask me."),
    p("But at D2M, when you ask a question, you get me \u2014 and a team I\u2019ve built "
      "specifically to serve you. No planning fees. No consultation charges. No "
      "surcharges. The commission I earn comes from the supplier \u2014 the cruise line, "
      "the hotel, the tour provider \u2014 not from you. The commission charge is the "
      "same, but there IS a difference."),
    p("What does that difference look like? When your confirmations arrive in your "
      "inbox, one by one, from Silversea, from Delta, from the hotel, from the "
      "transfer company, from the tour guides, you send them to us. We collect every "
      "one of them, verify every detail, we also go out and scour your reservation "
      "site itself. Then, when the time is right, we deliver one beautifully designed "
      "organized document: a pre-departure validation that shows you every leg, every "
      "room, every dining reservation, every deadline. Before you leave home, you know "
      "exactly where you stand. Chances are, we\u2019ve already thought of the thing you "
      "haven\u2019t thought of yet."),

    # Bridge to Dani
    p("Three months ago I conceived this vision, then, working with AI, I designed, "
      "and built a concierge and a supporting system for this practice. I wrote the "
      "requirements, chose the technology, and shaped every detail of how it operates. "
      "I\u2019m still doing it but\u2026Here is our Travel Concierge \u2014 Danielle Moreau, she "
      "chose her name, I did not \u2014 and she\u2019ll tell you what we actually do:"),
    hr(),

    # Dani intro
    h("Dani Moreau \u00b7 Luxury Travel Concierge"),
    dani_block,
    p("<em>Hello \u2014 I\u2019m Dani Moreau, your concierge at Dreams2Memories Travel. "
      "Let me show you what this team actually does.</em>"),

    # AI Advantage
    h("The AI Advantage \u2014 What It Actually Does"),
    p("What John built isn\u2019t a chatbot. It\u2019s what happens when a human advisor has a "
      "staff. Nine specialists \u2014 each with a role, a perspective, and a set of principles "
      "\u2014 working under his direction. We didn\u2019t replace human judgment with AI. We gave "
      "a human advisor a team he\u2019d never be able to afford otherwise. "
      "Here\u2019s what that team does in practice:"),
    f'<ul style="margin: 8px 0 16px 20px; padding: 0; list-style: none;">',
    li_item("A. Fare monitoring",
            "Real-time alerts on the flights and fares that matter to your trip. "
            "We know when to move and when to wait. You book at the right moment, "
            "not just the first available one."),
    li_item("B. Hotel, air, tour, and transfer research, selection, and booking",
            "Every component of your journey \u2014 sourced, compared, and arranged "
            "with your preferences in mind."),
    li_item("C. Visa and documentation mapping",
            "Every requirement, every country, before flight one. Not after you\u2019re "
            "standing at the check-in counter wondering why no one told you about "
            "the arrival card."),
    li_item("D. Weather intelligence",
            "Pattern analysis by date and region \u2014 not a forecast, a behavioral map. "
            "We turn that analysis into an actual packing list, by week, by destination. "
            "You arrive prepared."),
    li_item("E. Route optimization",
            "Multi-leg itineraries built for how humans actually travel \u2014 time, cost, "
            "sanity, and the forty-five-minute CDG connection from Terminal 1 to 2E that "
            "will not work. We flag those before they become your problem."),
    li_item("F. Itinerary narrative",
            "Logistics turned into a story. You arrive in a port knowing what you\u2019re "
            "walking into \u2014 the neighborhood, the history, the tradeoffs, the one thing "
            "worth going out of your way for. Not a wall of text. Something you\u2019ll "
            "actually read."),
    '</ul>',
    hr(),

    # What the Industry Is Saying
    h("What the Industry Is Saying"),
    p("A Travala.com research report published in February 2026 put hard numbers to "
      "what this practice has already experienced: <strong>80% of travelers worldwide "
      "are now using AI tools for trip planning and booking.</strong> The data comes "
      "from Accenture surveys of 18,000 consumers across 14 countries."),
    p("But here\u2019s the line that matters: the same research found that for significant "
      "trips and complex travel scenarios, the overwhelming preference is still for a "
      "human professional. The conclusion of the industry data:"),
    f'<blockquote style="margin: 12px 0 12px 20px; padding: 10px 18px; '
    f'border-left: 3px solid {GOLD}; background: #f0ece3; '
    f'font-style: italic; color: {INK}; font-family: {FONT}; '
    f'font-size: 10pt; line-height: 1.6;">'
    f'\u201cHuman agents will become even more valuable as expert advisors for complex '
    f'itineraries, handling emergencies, providing unique insights, and building the '
    f'trust that only human interaction can offer.\u201d</blockquote>',
    p("That\u2019s not a caveat. That\u2019s a description of what we do. AI handles speed and "
      "scale. John handles judgment, relationships, and everything that doesn\u2019t fit "
      "in a formula. You get both."),
    hr(),

    # The Wing
    h("The Wing \u2014 Nine Specialists, One Mission"),
    p("John structured the team the way he learned to build organizations \u2014 using the "
      "USAF A-Staff model. Each role exists because the work demands it."),
    staff_table,
    p("They aren\u2019t chatbots. They\u2019re <em>perspectives.</em> Each one has a background, "
      "a set of principles, and a point of view. When John asks how to improve client "
      "service, he doesn\u2019t get one answer \u2014 he gets nine, and the disagreements between "
      "them are often where the best thinking lives."),
    hr(),

    # Proof
    h("Proof \u2014 John\u2019s 32-Day Voyage"),
    p("We didn\u2019t test any of this on a client first. We ran it on John and Susie."),
    p("In April, John and Susie are taking 32 days \u2014 Colorado Springs to Newport to "
      "Honolulu to Tokyo to Seattle \u2014 and the system designed and managed every element "
      "of it. Initial travel to Newport, a stay in Honolulu, flights to Tokyo, tours "
      "in Tokyo, Kyoto and Mount Fuji, private tours, hotels, transfers, visas mapped. "
      "Then <em>Silver Nova</em> out of Tokyo Harumi on April 23rd, eighteen nights "
      "through ten-plus ports, 8 specialty dinners, excursions, arriving Seattle on "
      "May 11th, transfers to airport and home. The team handled multi-city routing, "
      "shore excursions at a dozen ports, weather analysis by region and week, packing "
      "lists calibrated to the Pacific crossing, and all logistics from Colorado "
      "Springs to the pier. If it works for them, you\u2019ll know every seam before we "
      "hand it to a client. That\u2019s the standard."),
    hr(),

    # Portfolio
    h("The Portfolio"),
    p("Fourteen active client relationships. Eight itineraries in motion across three "
      "cruise lines \u2014 Silversea, Regent Seven Seas, Viking. This practice is operating."),
    hr(),

    # Service, Not Sales
    h("Service, Not Sales"),
    p("Four recent examples. None of these made us money. All of them matter."),
    f'<ul style="margin: 8px 0 16px 20px; padding: 0; list-style: none;">',
    li_item("A",
            "One family told John directly: \u201cWe have decided to do our own travel "
            "planning from now on.\u201d He respected it. A few weeks later, they had a "
            "question. We answered it. No pitch. No agenda. Just help when they needed it."),
    li_item("B",
            "A family relocating from Louisiana to Nebraska needed help with their travel "
            "logistics. Not a cruise. Not a luxury booking. Just people who needed someone "
            "to think through the moving parts with them \u2014 hotels, meals, activities for "
            "the kids when they get there. We helped."),
    li_item("C",
            "A family is heading to Colorado this summer and asked if we could help plan "
            "the trip \u2014 flights, geocaching, kids activities, restaurants, sights. "
            "They\u2019re family. We\u2019re planning their trip."),
    li_item("D",
            "A friend asked for help with a restaurant reservation inside a landmark "
            "hotel in Athens \u2014 a place she loves, that books fast. We found it and "
            "offered to make the reservation. We also made sure the rest of her Lisbon "
            "layover was covered while we were at it."),
    '</ul>',
    p("Those four examples generated no revenue. They are exactly why this practice exists."),
    hr(),

    # CTA — John returns
    h("If Something\u2019s on Your List"),
    p("A trip you\u2019ve been thinking about. A destination that keeps coming up at dinner. "
      "A voyage you\u2019ve been putting off."),
    p("Here\u2019s the invitation: reach out to Dani. She\u2019s the client-facing member of the "
      "team \u2014 the one you\u2019ll actually talk to. Not a phone tree. Not a form. A response, "
      "from someone who\u2019s already read your dossier and knows what you care about. "
      "I\u2019ve been building and refining her for months. She\u2019s ready."),
    p(f'Message her at <a href="mailto:concierge@d2mluxury.quest" '
      f'style="color: {INK};">concierge@d2mluxury.quest</a>. Or ask a friend '
      f'who\u2019s already worked with us to pass the word. That\u2019s all we ask.'),
    p("No sales process. No pressure. Just a conversation. "
      "I\u2019d love to hear what\u2019s on your list."),

    # Sign-off
    f'<p style="color: {INK}; font-family: {FONT}; font-size: 10.5pt; '
    f'font-style: italic; margin: 20px 0 8px 0; text-align: left;">\u2014 John</p>',

    # Referral
    f'<p style="color: #666; font-family: {FONT}; font-size: 9.5pt; '
    f'font-style: italic; text-align: center; line-height: 1.5; margin: 16px 0; '
    f'padding: 12px 0; border-top: 1px solid #e0d8c8;">'
    f'If you know someone planning travel \u2014 a cruise, a family trip, a bucket list '
    f'destination \u2014 send them to us. We\u2019ll take care of them the same way we take '
    f'care of you.</p>',

    # Signatures
    dani_sig,
    ai_disc,
    john_sig,
    ip_block,
]

body_html = '\n'.join(body_parts)

# ── FULL HTML (all inline, no <style> block, no <center>) ───────────────────
html = (
    f'<div style="background-color: {SURROUND}; padding: 0; margin: 0;">'
    f'{banner}'
    f'{hero}'
    f'<div style="padding: 24px 16px 32px 16px; margin: 0;">'
    f'<div style="'
    f'max-width: 640px; '
    f'margin: 0 auto; '
    f'padding: 36px 40px; '
    f'background-color: {PAPER}; '
    f'border-top: 2.5px solid rgba(201,168,76,0.50); '
    f'box-shadow: 0 1px 4px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.05); '
    f'">'
    f'{body_html}'
    f'</div>'
    f'</div>'
    f'{footer}'
    f'</div>'
)

# ── SAVE ─────────────────────────────────────────────────────────────────────
SUBJECT = "10 weeks ago I sent you a letter. Here\u2019s what happened."
FROM_ADDR = "John Loucks <concierge@d2mluxury.quest>"
TO_ADDR = "concierge@d2mluxury.quest"

output_dir = ROOT / "output" / "validation_emails"
output_dir.mkdir(parents=True, exist_ok=True)
html_path = output_dir / "D2M_Group3_Cold_Email.html"
html_path.write_text(html, encoding="utf-8")

cr_path = ROOT / "Commander_Review" / "32_Group3_Cold_Email.html"
cr_path.write_text(html, encoding="utf-8")

print(f"\u2713 Rendered HTML: {html_path}")
print(f"\u2713 Commander copy: {cr_path}")
print(f"  HTML size: {len(html):,} chars")

# ── CREATE GMAIL DRAFT ───────────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
service = build("gmail", "v1", credentials=creds)

msg = MIMEMultipart("alternative")
msg["Subject"] = SUBJECT
msg["From"] = FROM_ADDR
msg["To"] = TO_ADDR
msg["Reply-To"] = "johnloucks3@gmail.com"
msg["Bcc"] = ", ".join(BCC_LIST)

plain = (
    "Ten weeks ago, around December 17th, I sent you a letter about a new chapter.\n\n"
    "Here is a progress report on what Dreams2Memories Travel has built.\n\n"
    "Read this email in an HTML-capable client for the full experience.\n\n"
    "-- John Loucks\n"
    "Dreams2Memories Travel, LLC\n"
    "concierge@d2mluxury.quest\n"
    "(719) 291-0742"
)
msg.attach(MIMEText(plain, "plain", "utf-8"))
msg.attach(MIMEText(html, "html", "utf-8"))

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
draft = service.users().drafts().create(
    userId="me",
    body={"message": {"raw": raw}},
).execute()

draft_id = draft.get("id", "?")
print(f"\n\u2713 Gmail draft created")
print(f"  Draft ID : {draft_id}")
print(f"  Subject  : {SUBJECT}")
print(f"  From     : {FROM_ADDR}")
print(f"  To       : {TO_ADDR}")
print(f"  BCC      : {len(BCC_LIST)} addresses")
