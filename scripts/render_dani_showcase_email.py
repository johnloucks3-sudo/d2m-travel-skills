#!/usr/bin/env python3
"""Render D2M Concierge Showcase Email v7 (dual-voice: John intro -> Dani takes over)
+ Attachment: Pre-Departure Validation — Loucks Pacific Journey.

Dual-voice structure:
  - JOHN: "A Note from John", "The Problem Worth Solving", handoff
  - TRANSITION: gold divider, Dani Moreau label
  - DANI: "How John Built It", "The Wing", "What This Means for You",
          "The Mission", attachment ref, CTA, signatures
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

# ── LOAD ASSETS ──────────────────────────────────────────────
logo_b64 = (ROOT / "output" / "logo_email_b64.txt").read_text().strip()
avatar_b64_path = ROOT / "output" / "dani_avatar_b64.txt"
avatar_b64 = avatar_b64_path.read_text().strip() if avatar_b64_path.exists() else ""

# ════════════════════════════════════════════════════════════════
# PART 1: SHOWCASE EMAIL (v7 — dual-voice)
# ════════════════════════════════════════════════════════════════

email_template = env.get_template("dani_showcase_email.html.j2")

# ── JOHN'S SECTION ──────────────────────────────────────────
JOHNS_NOTE = (
    "I want to show you something that will change your ideas about what "
    "a travel advisor can do for you."
)

JOHNS_NOTE_2 = (
    "Over the last three months, I\u2019ve designed, built, and refined an "
    "AI-enabled concierge system for my travel practice. I conceived the "
    "vision, wrote the requirements, chose the technology, and shaped every "
    "detail of how it works. The result is a team of nine AI specialists "
    "\u2014 each with a distinct role, personality, and perspective \u2014 working "
    "under my direction to deliver a level of service that no solo advisor "
    "could provide alone."
)

JOHNS_NOTE_3 = (
    "The persona you\u2019re about to meet is Dani Moreau. She is your Luxury "
    "Travel Concierge \u2014 she runs Booking Operations, tracking every client "
    "from first inquiry through welcome home. Flights, hotels, transfers, "
    "dining, excursions, deadlines \u2014 nothing falls through on her watch."
)

JOHNS_NOTE_4 = (
    "But before I hand you off to her, I want to tell you "
    "<em>why she exists.</em>"
)

PROBLEM_TEXT = (
    "When you book a $15,000\u201330,000 cruise suite, you deserve the attention of a "
    "full-service firm \u2014 a research team, a logistics coordinator, a financial analyst, "
    "and a client manager watching every detail. But no modern travel agency has that "
    "many people focused entirely on you. Your advisor books the cruise, handles payment, "
    "maybe helps with air, maybe advises on tours. But in reality, most of that work "
    "falls to you. And who said semi-retirement wasn\u2019t busy?"
)

PROBLEM_TEXT_2 = (
    "After three years as a travel advisor \u2014 and traveling the world with my wonderful "
    "wife, Susie \u2014 I decided it was time to do something different. So I built a staff, "
    "focused totally on you. <em>Their mission: Turning your Dreams2Memories.</em>"
)

JOHNS_HANDOFF = (
    "Now I\u2019d like you to meet Dani. I\u2019ll let her take it from here."
)

# ── DANI'S GREETING ─────────────────────────────────────────
DANI_GREETING = (
    "Hello \u2014 I\u2019m Dani Moreau, your concierge at Dreams2Memories Travel. "
    "John asked me to show you what we actually do for our clients. "
    "Let me walk you through it."
)

# ── HOW JOHN BUILT IT (Dani's voice) ────────────────────────
HOW_BUILT_1 = (
    "Here\u2019s what actually happens in the real world: Your booking confirmation arrives "
    "from Silversea. Your flight receipt comes from Delta. Your hotel confirms through "
    "Marriott. Your transfer company sends a WhatsApp with a pickup time. Tour directors "
    "email instructions. Insurance documents. Passport reminders. Visa requirements. All "
    "of it lands in different formats, different systems, at different times \u2014 and somehow "
    "it all has to come together in your notebook, your iPad, or your head. <em>Chaos.</em> "
    "We\u2019ve all been there."
)

HOW_BUILT_2 = (
    "John built a system that ends that chaos. You send us your confirmations \u2014 or just "
    "tell us what you\u2019ve booked \u2014 and the team takes it from there. Every detail gets "
    "extracted: flight numbers, seat assignments, confirmation codes, pickup times, driver "
    "names, cancellation deadlines. The system remembers that you had a terrible flight on "
    "United last year, so we avoid United. If something matters to you, we find it and we "
    "track it. Then we manage your trip like a project plan \u2014 a <em>deployment</em> \u2014 "
    "because that\u2019s how John learned to get things right."
)

HOW_BUILT_3 = (
    "We designed polished templates for client qualification, trip proposals, pre-departure "
    "validations, day-by-day itineraries, port-of-call touring guides, packing checklists, "
    "dining planners, and excursion briefings. Each one is clear, scannable, and useful "
    "\u2014 not a wall of text you\u2019ll never read."
)

HOW_BUILT_4 = (
    "Building just one of these documents by hand used to take John excruciating hours. "
    "The system we built produces them in minutes. <em>And it doesn\u2019t miss a thing.</em>"
)

# ── THE WING ─────────────────────────────────────────────────
WING_INTRO = (
    "John structured the team the way he learned it \u2014 using the USAF A-Staff model. "
    "Each position exists because the business needs that function. And we all work "
    "together \u2014 focused on you."
)

STAFF_ROSTER = [
    {"role": "Chief of Staff (VCSAF)", "name": "Victory Hale",
     "desc": "Orchestrates priorities, resolves conflicts, runs the morning brief."},
    {"role": "Voice & Visual", "name": "Naia Solberg-Vega",
     "desc": "Client-facing communications, brand tone, proposals, and template design."},
    {"role": "Research & Intel", "name": "Marcus Dembe",
     "desc": "Destination research, cruise line comparisons, supplier pricing."},
    {"role": "Booking Operations", "name": "Dani Moreau",
     "desc": "Tracks every client from first inquiry through welcome home. Nothing falls through."},
    {"role": "Strategy & Growth", "name": "Ryan Castillo",
     "desc": "Business decisions, pricing strategy, competitive positioning."},
    {"role": "Creative Director", "name": "Luna Voss",
     "desc": "Finds the emotional thread in every booking. Turns logistics into narrative."},
    {"role": "Finance & Process", "name": "Vic Harlan",
     "desc": "Commission audits, cost analysis, waste elimination."},
    {"role": "Crisis & Logistics", "name": "Tomoko Ikeda",
     "desc": "Flags problems before you find out the hard way \u2014 like that your "
     "45-minute CDG connection from Terminal 1 to 2E won\u2019t work."},
    {"role": "Ethics & Morale", "name": "James Washington",
     "desc": "Asks the question nobody else is asking: \u201cIs this the right thing to do?\u201d"},
]

WING_KICKER = (
    "They aren\u2019t chatbots. They\u2019re <em>perspectives.</em> Each one has a background "
    "story, a set of principles, and a personality. When John asks how we can improve our "
    "client service, we don\u2019t provide one answer \u2014 we provide at a minimum nine, and "
    "many of those ideas shaped the system you\u2019re reading about now."
)

# ── WHAT THIS MEANS FOR YOU ──────────────────────────────────
WHAT_WE_DO_INTRO = (
    "Most travel advisors can book a cruise. At D2M, we think about what happens "
    "before, during, and after \u2014 because we\u2019ve been the client, and we have the "
    "perspective of travelers across the world at our disposal."
)

WHAT_WE_DO_TEASER = (
    "<em>Ask me for a comparison between Regent Seven Seas Grandeur and "
    "Silversea Silver Nova. I\u2019ll have it for you by morning.</em>"
)

WHAT_WE_DO_BEFORE_TITLE = "Before you sail:"
WHAT_WE_DO_BEFORE = (
    "We capture what matters to you. <em>\u201cI cannot eat raw seafood.\u201d "
    "\u201cI want to go to the Palermo Opera House but only have 4 hours in port.\u201d "
    "\u201cI want to sail through the Corinthian Canal.\u201d</em> We ask the questions "
    "you\u2019d ask \u2014 <em>Are my layover times going to connect? Is the hotel close "
    "enough to the port to walk? Where is a great out-of-the-way place to eat "
    "in Venice?</em> (Answer: Frary\u2019s.) Every confirmation from every supplier gets "
    "collected, verified, and organized into one place. Nothing scattered across "
    "twenty emails you\u2019ll never find again."
)

WHAT_WE_DO_DURING_TITLE = "During your voyage:"
WHAT_WE_DO_DURING = (
    "We know ships. We track live positions. We know about the creaking in the aft "
    "of Silver Nova. We know about the slowdown in service in the Grand Dining Room "
    "on Vista. We watch for upgrade opportunities and know which specialty restaurants "
    "book out first. We\u2019ve studied the strengths and weaknesses of every ship in the "
    "Silversea, Regent, Viking, Cunard, Oceania, Seabourn, and AmaWaterways fleets. "
    "We monitor port weather. We have this intel because we\u2019ve collected it "
    "<em>systematically</em> \u2014 not because we happened to read the same brochure you did."
)

WHAT_WE_DO_AFTER_TITLE = "After you return:"
WHAT_WE_DO_AFTER = (
    "We don\u2019t disappear. We track your next voyage, maintain your preferences, "
    "remember that you liked La Terrazza on night three but the Kaiseki on night "
    "five was the one that stayed with you. We build on every trip to make the "
    "next one better."
)

# ── THE MISSION ──────────────────────────────────────────────
MISSION_QUOTE = (
    "We apply precision, attention to detail, and the perspective of someone who "
    "has been the client \u2014 not just the advisor \u2014 to every trip we touch."
)

MISSION_TEXT = (
    "This isn\u2019t about replacing human judgment with AI. It\u2019s about what happens when "
    "your travel advisor has a system that collects every supplier confirmation, "
    "extracts every detail, and organizes it all into polished, usable documents \u2014 "
    "itineraries, validation emails, touring guides, checklists \u2014 so that nothing "
    "gets lost and you always know exactly where you stand."
)

MISSION_TEXT_2 = (
    "The attached validation email took <em>four minutes</em> to produce from live data, "
    "on a template that took John two hours to design. Building it by hand would have taken "
    "the better part of <em>two days.</em> And it wouldn\u2019t have caught everything."
)

MISSION_CLOSER = "<em>That\u2019s what organized travel looks like.</em>"

# ── ATTACHMENT REFERENCE ─────────────────────────────────────
ATTACHMENT_INTRO = (
    "This is John and Susie\u2019s personal trip. Pricing removed. Everything else is "
    "exactly as I, with the help of the entire staff, designed, developed, "
    "and delivered it."
)

ATTACHMENT_SUMMARY = (
    "32 Days \u2014 Colorado Springs \u2192 Southern California \u2192 Hawaii \u2192 Tokyo "
    "\u2192 Silver Nova Pacific Crossing \u2192 Seattle \u2192 Home"
)

ATTACHMENT_STATS = (
    "4 Flights \u00b7 3 Hotels \u00b7 1 Cruise \u00b7 6 Shore Excursions "
    "\u00b7 2 Pre-Cruise Tours \u00b7 16 Dining Reservations"
)

# ── CTA ──────────────────────────────────────────────────────
CTA_TEXT = (
    "If this kind of service appeals to you \u2014 whether you have a trip on the "
    "horizon or are just starting to think about one \u2014 I\u2019d love to hear from you. "
    "Reply to this email, or reach out to John directly. No pitch. No obligation. "
    "No fees. Just a conversation about where your dreams are taking you and how "
    "we can help you get there."
)

CTA_REFERRAL = (
    "And if you know someone who could benefit from this kind of attention to "
    "their travel \u2014 please share this with them. The best introductions come "
    "from people like you."
)

# ── AI DISCLOSURE ────────────────────────────────────────────
AI_DISCLOSURE = (
    "Dani Moreau is your dedicated concierge at Dreams2Memories Travel \u2014 an "
    "AI-powered specialist designed to ensure every detail of your journey receives "
    "the attention it deserves. She operates under the direct oversight of John "
    "Loucks, your travel advisor, who reviews every recommendation and personally "
    "stands behind every communication."
)

# ── IP STATEMENT ─────────────────────────────────────────────
IP_STATEMENT = (
    "The content, design, templates, and systems described in this communication are "
    "the intellectual property of Dreams2Memories Travel, LLC. The AI-powered concierge "
    "platform, persona framework, and operational tools were conceived, designed, and "
    "built by John Loucks. All rights reserved. \u00a9 2026 Dreams2Memories Travel, LLC."
)

# ── RENDER EMAIL ─────────────────────────────────────────────
email_html = email_template.render(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    subject="What Organized Travel Actually Looks Like",
    hero_text="Your Voyage, Perfected",
    # John's section
    johns_note=JOHNS_NOTE,
    johns_note_2=JOHNS_NOTE_2,
    johns_note_3=JOHNS_NOTE_3,
    johns_note_4=JOHNS_NOTE_4,
    problem_text=PROBLEM_TEXT,
    problem_text_2=PROBLEM_TEXT_2,
    johns_handoff=JOHNS_HANDOFF,
    # Dani's section
    dani_greeting=DANI_GREETING,
    how_built_1=HOW_BUILT_1,
    how_built_2=HOW_BUILT_2,
    how_built_3=HOW_BUILT_3,
    how_built_4=HOW_BUILT_4,
    wing_intro=WING_INTRO,
    staff_roster=STAFF_ROSTER,
    wing_kicker=WING_KICKER,
    what_we_do_intro=WHAT_WE_DO_INTRO,
    what_we_do_teaser=WHAT_WE_DO_TEASER,
    what_we_do_before_title=WHAT_WE_DO_BEFORE_TITLE,
    what_we_do_before=WHAT_WE_DO_BEFORE,
    what_we_do_during_title=WHAT_WE_DO_DURING_TITLE,
    what_we_do_during=WHAT_WE_DO_DURING,
    what_we_do_after_title=WHAT_WE_DO_AFTER_TITLE,
    what_we_do_after=WHAT_WE_DO_AFTER,
    mission_quote=MISSION_QUOTE,
    mission_text=MISSION_TEXT,
    mission_text_2=MISSION_TEXT_2,
    mission_closer=MISSION_CLOSER,
    attachment_intro=ATTACHMENT_INTRO,
    attachment_summary=ATTACHMENT_SUMMARY,
    attachment_stats=ATTACHMENT_STATS,
    cta_text=CTA_TEXT,
    cta_referral=CTA_REFERRAL,
    ai_disclosure=AI_DISCLOSURE,
    ip_statement=IP_STATEMENT,
)

# Save email outputs
email_out_1 = output_dir / "D2M_Showcase_Mar2026.html"
email_out_1.write_text(email_html, encoding="utf-8")

email_out_2 = cr_dir / "29_D2M_Showcase_Email.html"
email_out_2.write_text(email_html, encoding="utf-8")

print("\u2713 Rendered D2M Showcase Email (v7 \u2014 dual-voice: John intro \u2192 Dani takes over):")
print(f"  \u2192 {email_out_1}")
print(f"  \u2192 {email_out_2}")


# ════════════════════════════════════════════════════════════════
# PART 2: ATTACHMENT — Pre-Departure Validation
# ════════════════════════════════════════════════════════════════

attachment_template = env.get_template("dani_showcase_attachment.html.j2")

JOURNEY_ROUTE = (
    "32 Days \u2014 Colorado Springs \u2192 Southern California \u2192 Hawaii "
    "\u2192 Tokyo \u2192 Silver Nova Pacific Crossing \u2192 Seattle \u2192 Home"
)

JOURNEY_STATS = (
    "4 Flights \u00b7 3 Hotels \u00b7 1 Cruise \u00b7 2 Pre-Cruise Tours "
    "\u00b7 6 Shore Excursions \u00b7 16 Dining Reservations"
)

FLIGHTS = [
    {"leg": "1", "flight": "G4 3212", "route": "COS \u2192 SNA",
     "date": "Apr 10, 2:37 PM", "class_info": "Economy"},
    {"leg": "2", "flight": "DL 443", "route": "LAX \u2192 HNL",
     "date": "Apr 13, 6:55 PM", "class_info": "First \u00b7 Seats 2C / 3A"},
    {"leg": "3", "flight": "JL 73", "route": "HNL \u2192 HND",
     "date": "Apr 18, 12:15 PM", "class_info": "Business Sky Suite III \u00b7 Seats 6G / 6D"},
    {"leg": "4", "flight": "TBD", "route": "SEA \u2192 COS",
     "date": "May 11", "class_info": "NOT YET BOOKED"},
]

FLIGHT_NOTE = (
    "JAL Business Sky Suite III \u2014 private suites with sliding doors, lie-flat beds, "
    "and Noritake tableware. Outbound connections confirmed. Return from Seattle needs "
    "booking \u2014 ship docks 7:00 AM, targeting afternoon departure."
)

HOTELS = [
    {"property": "Newport Beach Marriott Bayview", "dates": "Apr 10\u201313",
     "nights": "3", "room": "Standard", "status": "Confirmed"},
    {"property": "Hale Koa Hotel, Waikiki", "dates": "Apr 13\u201318",
     "nights": "5", "room": "Ocean View", "status": "Confirmed"},
    {"property": "Hilton Tokyo Odaiba", "dates": "Apr 19\u201323",
     "nights": "4", "room": "Twin Superior Deluxe, Honors Breakfast", "status": "Confirmed"},
]

PRECRUISE_EXCURSIONS = [
    {"date": "Apr 21", "name": "Kyoto Food Tour",
     "details": "3 hrs with guide Hiro, meeting at Matsumoto Kiyoshi Shijo Kawaramachi, 10 AM"},
    {"date": "Apr 22", "name": "Mt. Fuji & Hakone Day Tour",
     "details": "Full day, 7:50 AM departure"},
]

PRECRUISE_NOTE = (
    "Shinkansen membership (SmartEX) registered for independent Japan Rail travel "
    "between excursion days."
)

TRANSFERS = [
    {"segment": "Home \u2192 COS airport", "method": "Self-drive", "status": ""},
    {"segment": "NRT Airport \u2192 Hilton Odaiba",
     "method": "Private sedan, Meet & Greet Terminal 1", "status": "Confirmed"},
    {"segment": "Hilton \u2192 Tokyo Harumi Port, Apr 23",
     "method": "Shared minibus (4 pax), 10:30 AM (time change pending)", "status": "Confirmed"},
    {"segment": "Seattle cruise terminal \u2192 SEA-TAC",
     "method": "Needs booking", "status": "NOT YET BOOKED"},
]

SHORE_EXCURSIONS = [
    {"date": "Apr 25", "port": "Miyako, Iwate", "name": "Jodogahama & Ryusendo",
     "duration": "4 hrs", "waitlisted": False},
    {"date": "May 5", "port": "Sitka", "name": "Sitka\u2019s Culinary Adventure",
     "duration": "3 hrs", "waitlisted": True},
    {"date": "May 6", "port": "Juneau", "name": "Whale Watching & Wildlife Quest",
     "duration": "4 hrs", "waitlisted": False},
    {"date": "May 7", "port": "Wrangell", "name": "John Muir Hike",
     "duration": "1h 45m", "waitlisted": False},
    {"date": "May 8", "port": "Ketchikan", "name": "By Land & Sea",
     "duration": "1h 30m", "waitlisted": False},
    {"date": "May 10", "port": "Victoria", "name": "Victoria by Horse-Drawn Trolley",
     "duration": "1 hr", "waitlisted": False},
]

# Dining in two-column rows
DINING_ROWS = [
    {"date_l": "Apr 23", "rest_l": "La Terrazza", "wait_l": False,
     "date_r": "May 1",  "rest_r": "La Dame",     "wait_r": False},
    {"date_l": "Apr 24", "rest_l": "The Grill",    "wait_l": True,
     "date_r": "May 2",  "rest_r": "Silver Note",  "wait_r": False},
    {"date_l": "Apr 27", "rest_l": "Kaiseki",       "wait_l": False,
     "date_r": "May 3",  "rest_r": "The Grill",    "wait_r": False},
    {"date_l": "Apr 28", "rest_l": "S.A.L.T. Chef\u2019s Table", "wait_l": False,
     "date_r": "May 4",  "rest_r": "La Terrazza",  "wait_r": False},
    {"date_l": "Apr 29", "rest_l": "La Terrazza",   "wait_l": False,
     "date_r": "May 5",  "rest_r": "La Terrazza",  "wait_r": False},
    {"date_l": "Apr 30", "rest_l": "The Grill",     "wait_l": False,
     "date_r": "May 6",  "rest_r": "La Terrazza",  "wait_r": False},
    {"date_l": "",        "rest_l": "",              "wait_l": False,
     "date_r": "May 7",  "rest_r": "Kaiseki",      "wait_r": False},
    {"date_l": "",        "rest_l": "",              "wait_l": False,
     "date_r": "May 8",  "rest_r": "La Terrazza",  "wait_r": False},
    {"date_l": "",        "rest_l": "",              "wait_l": False,
     "date_r": "May 9",  "rest_r": "The Grill",    "wait_r": False},
    {"date_l": "",        "rest_l": "",              "wait_l": False,
     "date_r": "May 10", "rest_r": "La Terrazza",  "wait_r": False},
]

TIMELINE = [
    {"date": "Mar 25", "event": "Complete Visit Japan Web registration \u2014 both travelers"},
    {"date": "Apr 1",  "event": "Confirm Hilton \u2192 Harumi port transfer time (10:30 AM)"},
    {"date": "Apr 10", "event": "Departure day \u2014 Colorado Springs to Newport Beach"},
    {"date": "Apr 18", "event": "Hilton Odaiba cancel-free deadline (11:59 PM)"},
    {"date": "Apr 23", "event": "Embarkation \u2014 Tokyo Harumi, Silver Nova"},
]

ACTION_ITEMS = [
    {"title": "Visit Japan Web",
     "detail": "Both travelers need to register at vjw.digital.go.jp before Apr 21. "
               "Japan\u2019s digital entry requirement \u2014 immigration, customs, and quarantine in one form."},
    {"title": "Seattle return flight",
     "detail": "Ship docks May 11 at 7:00 AM. Need to book SEA \u2192 COS. "
               "Monitoring Southwest and United for best options."},
    {"title": "Port transfer time",
     "detail": "Change from 11:00 to 10:30 AM requested. Acknowledged but not yet confirmed. "
               "Following up with Project Expedition."},
    {"title": "Upgrade bid status",
     "detail": "Premium Medallion ($2,305) and Medallion ($1,600) bids submitted to "
               "Silversea Plusgrade. Awaiting results."},
    {"title": "Sitka excursion",
     "detail": "Waitlisted for Sitka\u2019s Culinary Adventure (May 5). Monitoring for opening."},
]

# ── RENDER ATTACHMENT ────────────────────────────────────────
attachment_html = attachment_template.render(
    logo_b64=logo_b64,
    journey_route=JOURNEY_ROUTE,
    journey_stats=JOURNEY_STATS,
    flights=FLIGHTS,
    flight_note=FLIGHT_NOTE,
    hotels=HOTELS,
    precruise_excursions=PRECRUISE_EXCURSIONS,
    precruise_note=PRECRUISE_NOTE,
    transfers=TRANSFERS,
    shore_excursions=SHORE_EXCURSIONS,
    dining_rows=DINING_ROWS,
    timeline=TIMELINE,
    action_items=ACTION_ITEMS,
    ip_statement=IP_STATEMENT,
)

attachment_out = cr_dir / "29_D2M_Showcase_Attachment.html"
attachment_out.write_text(attachment_html, encoding="utf-8")

print(f"\n\u2713 Rendered D2M Showcase Attachment (Pre-Departure Validation):")
print(f"  \u2192 {attachment_out}")
