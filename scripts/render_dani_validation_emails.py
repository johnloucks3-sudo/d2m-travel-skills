#!/usr/bin/env python3
"""Render & send Dani Moreau validation emails for Furlow, Ely, Nichols.

Renders branded HTML with logo, Dani avatar, AI disclosure.
Sends via Gmail API from concierge@d2mluxury.quest.
"""

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

# ── LOAD ASSETS ──────────────────────────────────────────────
logo_b64 = (ROOT / "output" / "logo_email_b64.txt").read_text().strip()
avatar_b64_path = ROOT / "output" / "dani_avatar_b64.txt"
avatar_b64 = avatar_b64_path.read_text().strip() if avatar_b64_path.exists() else ""

# ── JOHN'S PERSONAL NOTE ─────────────────────────────────────
JOHNS_NOTE = (
    "I wanted to introduce you to something new I\u2019m trying. Dani Moreau is an "
    "AI-powered concierge I\u2019ve built into my practice to help me stay on top of "
    "every detail of your trip \u2014 flights, hotels, excursions, deadlines, all of it. "
    "She works around the clock and nothing slips through the cracks. I personally "
    "review everything she sends and stand behind every word. That said, I know this "
    "is new territory, and if getting an email from an AI concierge feels strange or "
    "isn\u2019t your thing, I completely understand \u2014 just let me know and we\u2019ll keep "
    "everything coming directly from me. No hard feelings at all. I just want your "
    "experience to be the best it can be."
)

# ── CLIENT EMAIL ADDRESSES ───────────────────────────────────
CLIENTS = {
    "Furlow": {
        "to": "missy.furlow@gmail.com",
        "filename": "Furlow_Validation_Mar2026.html",
    },
    "Ely": {
        "to": "al.ely58@gmail.com, amy.darrow@me.com",
        "filename": "Ely_Validation_Mar2026.html",
    },
    "Nichols": {
        "to": "heidi.nichols1@yahoo.com, larry.nichols4811@gmail.com",
        "filename": "Nichols_Validation_Mar2026.html",
    },
    "McLeod": {
        "to": "emcleod@gmail.com, memcglas@gmail.com",
        "filename": "McLeod_Validation_Mar2026.html",
    },
    "Westbrook": {
        "to": "rwestbrook3@gmail.com, lindywestbrook77@gmail.com",
        "filename": "Westbrook_Validation_Mar2026.html",
    },
    "Kyle": {
        "to": "kyle.kuklinski@gmail.com",
        "filename": "Kyle_Validation_Mar2026.html",
    },
    "Roger": {
        "to": "Roger.kuklinski@gmail.com, nikpack@gmail.com",
        "filename": "Roger_Validation_Mar2026.html",
    },
    "Morton": {
        "to": "josh@jerichopix.com, Buzzerica@gmail.com",
        "filename": "Morton_Validation_Mar2026.html",
    },
}

# ── SHARED CONTEXT ───────────────────────────────────────────
shared = dict(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    ship_name="Regent Seven Seas Grandeur",
    voyage_description="Scandinavia \u00b7 Aug 29 \u2013 Sep 8, 2026",
    hero_text="Scandinavia Awaits",
)

# ── FURLOW (Touch 2 — Fully Paid, Validation Focus) ─────────
furlow = template.render(
    **shared,
    personal_note="",
    subject="Your Scandinavia Voyage \u2014 Everything We Have in Place",
    greeting="Hi John and Missy,",
    intro_text=(
        "You\u2019re fully paid and confirmed on the Seven Seas Grandeur. "
        "Here\u2019s a complete picture of everything in place and a few small items still to nail down."
    ),
    suite_number="827",
    deck_number="8",
    balance_due="0 \u2014 Paid in Full",
    flights=[
        "Aug 26: AA 9018 (Finnair) DFW \u2192 Helsinki, 4:50 PM \u2014 Confirmed",
        "Aug 27: AY 811 Helsinki \u2192 Stockholm, 1:15 PM \u2014 Confirmed",
        "Sep 8: BA 6776 Oslo \u2192 London, 11:15 AM \u2014 Seats 4C / 4A",
        "Sep 8: AA 79 London \u2192 Dallas, 2:25 PM \u2014 Seats 7D / 7G",
    ],
    flight_notes="AA Record Locator: CKZHXA \u00b7 Finnair/BA: BB4X94. Outbound seats on DFW\u2192Helsinki and Helsinki\u2192Stockholm are not yet assigned \u2014 Business Class is guaranteed. Please contact Finnair with record locator BB4X94 \u2014 we will be glad to help with that.",
    hotel_transfers=[
        "\u26a0 Haymarket By Scandic, Stockholm \u2014 Aug 27-28 (Grande King) \u2014 Confirmed \u00b7 ~$418 NOT YET PAID",
        "Regent included hotel night \u2014 Aug 28 \u2014 Confirmed (included)",
        "\u26a0 Airport transfer from Arlanda \u2014 Confirmed \u00b7 ~$176 NOT YET PAID",
        "Hotel \u2192 ship transport Aug 29 \u2014 Included by Regent",
        "Ship \u2192 Oslo airport transport Sep 8 \u2014 Included by Regent",
    ],
    excursion_count="6",
    excursions=[
        {"date": "Aug 30", "port": "Stockholm", "name": "Highlights of Stockholm & Vasa Museum"},
        {"date": "Sep 1", "port": "Berlin/Warnem\u00fcnde", "name": "The Berlin Experience"},
        {"date": "Sep 2", "port": "Berlin/Warnem\u00fcnde", "name": "Amazing Rostock"},
        {"date": "Sep 3", "port": "Copenhagen", "name": "A Tour of Two Kingdoms \u2014 Denmark to Sweden"},
        {"date": "Sep 6", "port": "Kristiansand", "name": "Explore Kristiansand on Foot"},
        {"date": "Sep 7", "port": "Oslo", "name": "Hadeland Glass Works & Fram Museum"},
    ],
    upcoming=[
        {"date": "May 1", "description": "Culinary Arts Kitchen Classes booking opens (8pm ET)"},
        {"date": "May 31", "description": "Specialty dining reservations open (8pm ET)"},
        {"date": "Aug 8", "description": "Online check-in opens"},
        {"date": "Aug 29", "description": "Embarkation \u2014 Stockholm"},
    ],
    action_items=[
        "Outbound seat assignments \u2014 DFW\u2192Helsinki and Helsinki\u2192Stockholm not yet assigned. Please contact Finnair with record locator BB4X94 \u2014 we will be glad to help coordinate that.",
        "Passport details \u2014 John\u2019s confirmed through 2035. Missy\u2019s details not yet on file \u2014 whenever you\u2019re comfortable sharing, it helps with pre-registration.",
        "Travel insurance \u2014 Chase Sapphire Reserve is active and covers trip cancellation up to $10K/person. A dedicated policy would cover missed ports and medical evacuation at sea \u2014 happy to pull options if you\u2019d like to compare.",
    ],
    closing_text=(
        "Cruise confirmed, flights set, six excursions locked in \u2014 this trip is going to be extraordinary. "
        "Looking forward to every detail of it with you."
    ),
)
(output_dir / "Furlow_Validation_Mar2026.html").write_text(furlow, encoding="utf-8")

# ── ELY (Touch 2 — Fully Paid, Validation Focus) ────────────
ely = template.render(
    **shared,
    personal_note="",
    subject="Your Scandinavia Voyage \u2014 Everything We Have in Place",
    greeting="Hi Al and Amy,",
    intro_text=(
        "You\u2019re fully paid and confirmed on the Seven Seas Grandeur. "
        "Here\u2019s a complete picture of everything in place and a few items still to sort out."
    ),
    suite_number="1212",
    deck_number="12",
    balance_due="0 \u2014 Paid in Full",
    flights=[
        "Aug 26: AA 9018 (Finnair) DFW \u2192 Helsinki, 4:50 PM \u2014 Seats 2H / 2D",
        "Aug 27: AY 811 Helsinki \u2192 Stockholm, 1:15 PM \u2014 Confirmed",
        "Sep 8: BA 6776 Oslo \u2192 London, 11:15 AM \u2014 Seats 2C / 2A",
        "Sep 8: AA 79 London \u2192 Dallas, 2:25 PM \u2014 Seats 3G / 3D",
    ],
    flight_notes="AA Record Locator: UXVXZP. DFW\u2192Helsinki seats confirmed (2H/2D). Helsinki\u2192Stockholm (AY 811) seats not yet assigned \u2014 please contact Finnair, and we will be glad to help with that.",
    hotel_transfers=[
        "\u26a0 Haymarket By Scandic, Stockholm \u2014 Aug 27-28 (Grande King) \u2014 Confirmed \u00b7 Amount TBD \u2014 NOT YET PAID",
        "Regent included hotel night \u2014 Aug 28 \u2014 Confirmed (included)",
        "\u26a0 Airport transfer from Arlanda \u2014 Confirmed \u00b7 ~$176 NOT YET PAID",
        "Hotel \u2192 ship transport Aug 29 \u2014 Included by Regent",
        "Ship \u2192 Oslo airport transport Sep 8 \u2014 Included by Regent",
    ],
    excursion_count="6",
    excursions=[
        {"date": "Aug 30", "port": "Stockholm", "name": "Swedish Nature Experience"},
        {"date": "Sep 1", "port": "Berlin/Warnem\u00fcnde", "name": "Amazing Rostock"},
        {"date": "Sep 2", "port": "Berlin/Warnem\u00fcnde", "name": "Medieval Flavors of Rostock"},
        {"date": "Sep 3", "port": "Copenhagen", "name": "Christiansborg Palace & Tivoli Gardens"},
        {"date": "Sep 4", "port": "Copenhagen", "name": "A Tour of Two Kingdoms \u2014 Denmark to Sweden"},
        {"date": "Sep 7", "port": "Oslo", "name": "Oslo During World War II"},
    ],
    upcoming=[
        {"date": "May 1", "description": "Culinary Arts Kitchen Classes booking opens (8pm ET)"},
        {"date": "May 31", "description": "Specialty dining reservations open (8pm ET)"},
        {"date": "Aug 8", "description": "Online check-in opens"},
        {"date": "Aug 29", "description": "Embarkation \u2014 Stockholm"},
    ],
    action_items=[
        "Helsinki\u2192Stockholm seat assignments \u2014 AY 811 seats not yet assigned. Please contact Finnair with record locator UXVXZP \u2014 we will be glad to help with that.",
        "Kristiansand \u2014 No excursion booked for this port. Easy to explore on your own, or I can look into options.",
        "Travel insurance \u2014 Worth revisiting when you\u2019re ready. The Allianz $450 quote for two on a $15K annual plan does seem low \u2014 happy to verify the coverage details.",
        "Passport details \u2014 Not yet on file for either of you. No rush \u2014 whenever you\u2019re comfortable sharing, it helps with pre-registration.",
        "Shipboard credits \u2014 You have $574 remaining of your $1,100 onboard credit. Guest registration is complete for both \u2014 thank you.",
    ],
    closing_text=(
        "Cruise confirmed, flights set, six excursions locked in. "
        "This is going to be a magnificent journey \u2014 I\u2019m so glad to be part of it. "
        "Reach out anytime, I\u2019m here for you."
    ),
)
(output_dir / "Ely_Validation_Mar2026.html").write_text(ely, encoding="utf-8")

# ── NICHOLS ─────────────────────────────────────────────────
nichols = template.render(
    **shared,
    personal_note="",
    subject="Your Scandinavia Voyage \u2014 Everything We Have in Place",
    greeting="Hi Larry and Heidi,",
    intro_text=(
        "With final payment approaching on April 1, I wanted to run through everything "
        "we have in place and make sure it all looks right to you."
    ),
    suite_number="939",
    deck_number="9",
    balance_due="14,986",
    flights=[
        "Aug 26: AA 9018 (Finnair) DFW \u2192 Helsinki, 4:50 PM \u2014 Ticketed, no seats yet",
        "Aug 27: AY 811 Helsinki \u2192 Stockholm, 1:15 PM \u2014 Ticketed, no seats yet",
        "Sep 8: BA 6776 Oslo \u2192 London, 11:15 AM \u2014 Ticketed, no seats yet",
        "Sep 8: AA 79 London \u2192 Dallas, 2:25 PM \u2014 Ticketed, no seats yet",
    ],
    flight_notes="AA Record Locator: DSTAGH \u00b7 Finnair: BERJYH. All flights are ticketed and confirmed in Business Class, but no seat assignments are showing on any leg yet. Please contact Finnair or British Airways with your record locators \u2014 we will be glad to help coordinate that.",
    hotel_transfers=[
        "\u26a0 Haymarket By Scandic, Stockholm \u2014 Aug 27-28 (Grande King) \u2014 Confirmed \u00b7 NOT YET PAID",
        "Regent included hotel night \u2014 Aug 28 \u2014 Confirmed (included)",
        "\u26a0 Airport transfer from Arlanda \u2014 Confirmed \u00b7 NOT YET PAID",
        "Hotel \u2192 ship transport Aug 29 \u2014 Included by Regent",
        "Ship \u2192 Oslo airport transport Sep 8 \u2014 Included by Regent",
    ],
    excursion_count="7",
    excursions=[
        {"date": "Aug 30", "port": "Stockholm", "name": "Highlights of Stockholm & Vasa Museum"},
        {"date": "Sep 1", "port": "Berlin/Warnem\u00fcnde", "name": "The Berlin Experience"},
        {"date": "Sep 2", "port": "Berlin/Warnem\u00fcnde", "name": "Amazing Rostock + Medieval Flavors of Rostock"},
        {"date": "Sep 3", "port": "Copenhagen", "name": "A Tour of Two Kingdoms \u2014 Denmark to Sweden"},
        {"date": "Sep 4", "port": "Copenhagen", "name": "Tivoli Gardens & Canal Cruise"},
        {"date": "Sep 7", "port": "Oslo", "name": "Panoramic Oslo"},
    ],
    upcoming=[
        {"date": "Apr 1", "description": "Final payment due ($14,986)"},
        {"date": "May 1", "description": "Culinary Arts Kitchen Classes booking opens (8pm ET)"},
        {"date": "May 31", "description": "Specialty dining reservations open (8pm ET)"},
        {"date": "Aug 8", "description": "Online check-in opens"},
        {"date": "Aug 29", "description": "Embarkation \u2014 and Heidi's birthday!"},
    ],
    action_items=[
        "Insurance \u2014 Larry, I know this has been a moving target. You mentioned paying about $700 to Allianz but weren't sure what it covers, and you also have Amex Platinum benefits. I'm going to get clarity on what your current policy includes and how it compares to the CFAR coverage you want. No more guesswork \u2014 I'll come back with a clear picture.",
        "Seat assignments \u2014 No seats on any of your four flights right now. Please contact Finnair or British Airways with your record locators \u2014 we will be glad to help coordinate that.",
        "Passport info \u2014 I don't have passport details for either of you on file yet. Whenever you're comfortable, sharing those helps me keep everything organized for pre-registration. Totally optional.",
    ],
    closing_text=(
        "You're in wonderful shape overall, and I'm genuinely looking forward to following "
        "every detail all the way through to embarkation day \u2014 Heidi's birthday, no less. "
        "Please don't hesitate to reach out \u2014 I'm here for you. And enjoy that cruise this week!"
    ),
)
(output_dir / "Nichols_Validation_Mar2026.html").write_text(nichols, encoding="utf-8")

# ── McLEOD ─────────────────────────────────────────────────
mcleod_shared = dict(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    ship_name="Silversea Silver Muse",
    voyage_description="Mediterranean \u00b7 Jun 23 \u2013 Jul 3, 2026 \u00b7 Civitavecchia to Venice",
    payment_date="N/A",
    hero_text="The Mediterranean Awaits",
    personal_note=JOHNS_NOTE,
)
mcleod = template.render(
    **mcleod_shared,
    subject="Your Mediterranean Voyage \u2014 Pre-Departure Validation",
    greeting="Hi Erik and Melissa,",
    intro_text=(
        "With your Silver Muse sailing about three months out, I wanted to walk through "
        "everything we have in place and flag a few items that still need attention. "
        "Your cruise is paid in full \u2014 this is about making sure every detail around it is locked in."
    ),
    suite_number="617",
    deck_number="6",
    balance_due="0 \u2014 Paid in Full",
    flights=[
        "Jun 18: UA 177 Denver \u2192 Rome FCO, 5:45 PM \u2014 Business Class \u00b7 PNR: NFBDP6",
        "Jul 6: AC 817 Venice \u2192 Toronto, 12:20 PM \u2014 Business Class \u00b7 PNR: CXNT6Q",
        "Jul 6: AC 1041 Toronto \u2192 Denver, 6:40 PM \u2014 Business Class \u00b7 PNR: CXNT6Q",
    ],
    flight_notes="Seat assignments are pending on all three legs. Worth calling United and Air Canada to get those locked in before departure.",
    hotel_transfers=[
        "Baglioni Hotel Regina, Rome \u2014 Jun 19\u201323 (4 nights, Grand Deluxe) \u2014 Confirmed",
        "Hilton Molino Stucky, Venice \u2014 Jul 3\u20136 (3 nights, Executive Suite) \u2014 Confirmed",
        "Jun 22: Silversea Private Executive Home Transfer (pre-cruise) \u2014 Confirmed",
        "Jun 23: Silversea group transfer apartment \u2192 pier \u2014 Confirmed",
        "Jul 3: Silversea group transfer pier \u2192 apartment \u2014 Confirmed",
        "Jul 3: Silversea Private Executive Home Transfer (post-cruise) \u2014 Confirmed",
        "\u26a0 FCO Airport \u2192 Baglioni Hotel (Jun 19) \u2014 NOT YET BOOKED",
        "\u26a0 Ship \u2192 Hilton Molino Stucky (Jul 3) \u2014 Water taxi required (Giudecca island) \u2014 NOT YET BOOKED",
        "\u26a0 Hilton Molino Stucky \u2192 VCE Airport (Jul 6) \u2014 Water taxi + land transfer \u2014 NOT YET BOOKED",
    ],
    excursion_count="8",
    excursions=[
        {"date": "Jun 24", "port": "Naples", "name": "Ruins of Herculanum", "cost": "INCLUDED"},
        {"date": "Jun 25", "port": "Giardini Naxos", "name": "Greek & Roman Taormina", "cost": "INCLUDED"},
        {"date": "Jun 26", "port": "Siracusa", "name": "Baroque Town of Noto", "cost": "INCLUDED"},
        {"date": "Jun 27", "port": "Valletta", "name": "Game of Thrones", "cost": "INCLUDED"},
        {"date": "Jun 29", "port": "Kotor", "name": "Speedboat Adventure to Blue Cave", "cost": "$318"},
        {"date": "Jun 30", "port": "Dubrovnik", "name": "Day at the Beach Club", "cost": "$278"},
        {"date": "Jul 1", "port": "Split", "name": "UNESCO World Heritage Sites", "cost": "INCLUDED"},
        {"date": "Jul 2", "port": "Zadar", "name": "Nin Salt Works & Royal Vineyards", "cost": "INCLUDED"},
    ],
    dining=[
        {"date": "Jun 24", "restaurant": "La Dame", "time": "Evening", "cost": "$120"},
        {"date": "Jun 26", "restaurant": "The Grill", "time": "Evening", "cost": "INCLUDED"},
        {"date": "Jun 28", "restaurant": "Silver Note", "time": "Evening", "cost": "INCLUDED"},
        {"date": "Jul 1", "restaurant": "La Terrazza", "time": "Evening", "cost": "INCLUDED"},
    ],
    upcoming=[
        {"date": "Apr 1", "description": "Finalize Rome pre-cruise excursions (Colosseum, Florence, Vatican)"},
        {"date": "May 1", "description": "Confirm all seat assignments"},
        {"date": "Jun 18", "description": "Departure day \u2014 Denver to Rome"},
        {"date": "Jul 22", "description": "Regent Grandeur (Lesser Antilles, Dec 2026) final payment due \u2014 $12,393.15"},
    ],
    action_items=[
        "Airport transfers \u2014 Three gaps: FCO airport to Baglioni Hotel (Jun 19), ship to Hilton Molino Stucky (Jul 3), and Hilton to Venice airport (Jul 6). The Molino Stucky is on Giudecca island, so both Venice transfers will be by water taxi. I can arrange all three \u2014 just give me the green light.",
        "Seat assignments \u2014 Pending on all three flight legs. United and Air Canada should be able to assign now that you\u2019re ticketed.",
        "Onboard charges \u2014 Current total for excursions ($596) + dining ($120): $716. These will be settled onboard.",
    ],
    closing_text=(
        "The big picture is solid \u2014 cruise paid, hotels confirmed, 8 excursions locked in, dining reserved. "
        "The items that need attention are the three Venice/Rome transfers (including water taxi) and seat assignments. "
        "Let me know how you\u2019d like to proceed on any of those."
    ),
)
(output_dir / "McLeod_Validation_Mar2026.html").write_text(mcleod, encoding="utf-8")

# ── WESTBROOK ──────────────────────────────────────────────
westbrook_shared = dict(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    ship_name="Silversea Silver Nova",
    voyage_description="Tokyo to Seattle \u00b7 Apr 23 \u2013 May 11, 2026",
    payment_date="N/A",
    hero_text="The Pacific Awaits",
    personal_note=JOHNS_NOTE,
)
westbrook = template.render(
    **westbrook_shared,
    subject="Your Pacific Voyage \u2014 Pre-Departure Validation",
    greeting="Hi Ron and Linda,",
    intro_text=(
        "We\u2019re about six weeks out from your Silver Nova sailing, and everything is coming together "
        "beautifully. Your cruise and flights are paid in full \u2014 I just want to walk through the details "
        "and flag a few remaining items before departure day."
    ),
    suite_number="7031",
    deck_number="7",
    balance_due="0 \u2014 Paid in Full",
    flights=[
        "Apr 21: UA 143 Denver \u2192 Tokyo NRT, 11:35 AM \u2014 Premium Economy \u00b7 Seats 21A / 21C \u00b7 PNR: I0Y9VG",
        "May 11: UA 757 Seattle \u2192 Denver, 12:46 PM \u2014 Economy \u00b7 PNR: I0Y9VG",
    ],
    flight_notes="Outbound seats confirmed. Return is economy SEA\u2192DEN \u2014 ship docks at 7:00 AM, flight at 12:46 PM gives you plenty of buffer.",
    hotel_transfers=[
        "Hilton Tokyo Odaiba \u2014 Apr 22\u201323 (1 night, King Room, Honors Breakfast) \u2014 Confirmed \u00b7 #33S2013960",
        "Home \u2192 DEN airport, Apr 21 at 7:30 AM \u2014 Driver Marcus \u2014 Confirmed",
        "NRT Airport \u2192 Hilton Odaiba \u2014 Transferz private sedan, Meet & Greet T1 \u2014 Confirmed \u00b7 #73268402723830",
        "Hilton \u2192 Tokyo Harumi Port, Apr 23 \u2014 Shared transfer (4 pax) \u2014 Confirmed \u00b7 #PE151557101 (time change to 10:30 AM pending)",
        "\u26a0 Seattle cruise terminal \u2192 SEA-TAC airport (May 11) \u2014 NOT YET BOOKED",
    ],
    excursion_count="4",
    excursions=[
        {"date": "Apr 25", "port": "Miyako, Iwate", "name": "Jodogahama & Ryusendo", "cost": "INCLUDED"},
        {"date": "May 6", "port": "Juneau", "name": "Gold \u2014 Underground Mining Heritage", "cost": "INCLUDED"},
        {"date": "May 7", "port": "Wrangell", "name": "Tongass Botanicals Nature Walk", "cost": "INCLUDED"},
        {"date": "May 8", "port": "Ketchikan", "name": "By Land & Sea", "cost": "INCLUDED"},
    ],
    dining=[
        {"date": "Apr 23", "restaurant": "La Terrazza", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "Apr 26", "restaurant": "The Grill", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "Apr 29", "restaurant": "Silver Note", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "May 1", "restaurant": "La Terrazza", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "May 4", "restaurant": "The Grill", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "May 7", "restaurant": "La Terrazza", "time": "6:30 PM", "cost": "INCLUDED"},
        {"date": "May 9", "restaurant": "The Grill", "time": "6:30 PM", "cost": "INCLUDED"},
    ],
    upcoming=[
        {"date": "Mar 25", "description": "Complete Visit Japan Web registration (vjw.digital.go.jp) \u2014 both Ron and Linda"},
        {"date": "Apr 1", "description": "Confirm Hilton \u2192 Harumi port transfer time (10:30 AM)"},
        {"date": "Apr 15", "description": "Book Seattle terminal \u2192 SEA-TAC transfer"},
        {"date": "Apr 21", "description": "Departure day \u2014 Denver to Tokyo"},
    ],
    action_items=[
        "Visit Japan Web \u2014 Both of you need to register at vjw.digital.go.jp before Apr 21. This is Japan\u2019s entry requirement \u2014 immigration, customs, and quarantine all in one. It\u2019s straightforward but needs to be done before you fly.",
        "Seattle terminal transfer \u2014 Ship docks May 11 at 7:00 AM. Your flight is at 12:46 PM. I need to book your transfer from the cruise terminal to SEA-TAC \u2014 I\u2019ll get that arranged.",
        "Harumi port transfer time \u2014 We requested a change from 11:00 to 10:30 AM on Apr 23. Blacklane acknowledged via ticket HL855855 but hasn\u2019t confirmed yet. I\u2019m following up.",
        "Free-to-explore days \u2014 You have open days in Aomori (Apr 26), Kodiak (May 3), Sitka (May 5), and Victoria BC (May 10). Let me know if you\u2019d like suggestions or want to book anything.",
    ],
    closing_text=(
        "You and Susie and John are going to have an incredible time. Insurance is sorted (Allianz Annual "
        "Premier through Mar 2027), cruise is paid, flights are confirmed, dining is set for all seven nights. "
        "The only must-do before departure is that Visit Japan Web registration. Everything else, I\u2019ve got covered."
    ),
)
(output_dir / "Westbrook_Validation_Mar2026.html").write_text(westbrook, encoding="utf-8")

# ── VIKING MARS SHARED CONTEXT ──────────────────────────────
viking_shared = dict(
    logo_b64=logo_b64,
    avatar_b64=avatar_b64,
    ship_name="Viking Mars",
    voyage_description="Panama Canal \u00b7 Dec 17\u201327, 2026",
    hero_text="The Panama Canal Awaits",
)

VIKING_FLIGHTS_NOTE = (
    "Flights are not yet booked for this voyage. Panama City (PTY) is the embarkation port \u2014 "
    "departure day is December 17. Disembarkation is Ft. Lauderdale (FLL) on December 27. "
    "I\u2019ll be in touch as we get closer to put together flight options."
)

VIKING_HOTEL_NOTE = [
    "\u26a0 Flights \u2014 NOT YET BOOKED (outbound to Panama City Dec 17, return from Ft. Lauderdale Dec 27)",
    "\u26a0 Pre-cruise hotel \u2014 NOT YET PLANNED (Panama City, night of Dec 16 if needed)",
    "\u26a0 Transfers \u2014 NOT YET BOOKED (Panama City airport \u2192 pier; FLL pier \u2192 airport)",
]

# ── KYLE KUKLINSKI (Touch 1 — Validation Focus) ──────────────
kyle = template.render(
    **viking_shared,
    personal_note="",
    subject="Your Panama Canal Voyage \u2014 Here\u2019s Where We Stand",
    greeting="Hi Kyle and Rosalie,",
    intro_text=(
        "Your Viking Mars booking is confirmed and fully paid. Here\u2019s a complete picture "
        "of what\u2019s in place and what still needs to be built around the cruise. "
        "We will be happy to help search for flights, transfers, hotels, and excursions."
    ),
    suite_number="4122",
    deck_number="4",
    balance_due="0 \u2014 Paid in Full",
    flights=["\u26a0 Flights \u2014 Not yet booked"],
    flight_notes=VIKING_FLIGHTS_NOTE,
    hotel_transfers=VIKING_HOTEL_NOTE,
    excursion_count="0",
    excursions=[],
    upcoming=[
        {"date": "Aug 19", "description": "Cancel penalty 20% begins (E-120) \u2014 insurance should be in place before this"},
        {"date": "Dec 10", "description": "Excursion & dining selections close (E-7)"},
        {"date": "Dec 17", "description": "Embarkation \u2014 Panama City (Fuerte Amador), 3:00 PM"},
        {"date": "Dec 27", "description": "Disembarkation \u2014 Ft. Lauderdale (Port Everglades), 5:00 AM"},
    ],
    action_items=[
        "Flights \u2014 Not yet booked for any of the three couples. I\u2019ll be in touch with options \u2014 Panama City (PTY) out Dec 17, Ft. Lauderdale (FLL) back Dec 27.",
        "Travel insurance \u2014 Not yet in place. Worth getting this sorted before the cancel penalty window opens in August.",
        "Transfers \u2014 Panama City airport to pier and Ft. Lauderdale pier to airport both need to be arranged.",
        "Guest profile forms \u2014 I\u2019ll send those along for all six guests \u2014 passport details and contact info help with pre-registration.",
        "Shipboard credits \u2014 You have $800 in onboard credit ($200 Viking + $600 from D2M). Use it toward shore excursions, specialty dining, or onboard purchases.",
    ],
    closing_text=(
        "Cruise confirmed and paid. Now it\u2019s about building the trip around it \u2014 "
        "flights, insurance, transfers. I\u2019ll be in touch as we work through each piece."
    ),
)
(output_dir / "Kyle_Validation_Mar2026.html").write_text(kyle, encoding="utf-8")

# ── ROGER KUKLINSKI (Touch 1 — Validation Focus) ─────────────
roger = template.render(
    **viking_shared,
    personal_note="",
    subject="Your Panama Canal Voyage \u2014 Here\u2019s Where We Stand",
    greeting="Hi Roger and Nick,",
    intro_text=(
        "Your Viking Mars booking is confirmed and fully paid. Here\u2019s a complete picture "
        "of what\u2019s in place and what still needs to be built around the cruise. "
        "We will be happy to help search for flights, transfers, hotels, and excursions."
    ),
    suite_number="8012",
    deck_number="8",
    balance_due="0 \u2014 Paid in Full",
    flights=["\u26a0 Flights \u2014 Not yet booked"],
    flight_notes=VIKING_FLIGHTS_NOTE,
    hotel_transfers=VIKING_HOTEL_NOTE,
    excursion_count="0",
    excursions=[],
    upcoming=[
        {"date": "Aug 19", "description": "Cancel penalty 20% begins (E-120) \u2014 insurance should be in place before this"},
        {"date": "Dec 10", "description": "Excursion & dining selections close (E-7)"},
        {"date": "Dec 17", "description": "Embarkation \u2014 Panama City (Fuerte Amador), 3:00 PM"},
        {"date": "Dec 27", "description": "Disembarkation \u2014 Ft. Lauderdale (Port Everglades), 5:00 AM"},
    ],
    action_items=[
        "Flights \u2014 Not yet booked. Panama City (PTY) out Dec 17, Ft. Lauderdale (FLL) back Dec 27. I\u2019ll coordinate options with the group.",
        "Travel insurance \u2014 Not yet in place. Worth sorting before the cancel penalty window opens in August.",
        "Transfers \u2014 Panama City airport to pier and Ft. Lauderdale pier to airport both need to be arranged.",
        "Guest profile forms \u2014 I\u2019ll send those along for you and Nick \u2014 passport details help with pre-registration.",
        "Shipboard credits \u2014 You have $200 in onboard credit ($100/person) for shore excursions, dining, or onboard purchases.",
    ],
    closing_text=(
        "Cruise confirmed and paid. I\u2019ll be in touch as we work through flights, insurance, and transfers."
    ),
)
(output_dir / "Roger_Validation_Mar2026.html").write_text(roger, encoding="utf-8")

# ── MORTON / DODGE (Touch 1 — Validation Focus) ──────────────
morton = template.render(
    **viking_shared,
    personal_note="",
    subject="Your Panama Canal Voyage \u2014 Here\u2019s Where We Stand",
    greeting="Hi Josh and Erica,",
    intro_text=(
        "Your Viking Mars booking is confirmed and fully paid. Here\u2019s a complete picture "
        "of what\u2019s in place and what still needs to be built around the cruise. "
        "We will be happy to help search for flights, transfers, hotels, and excursions."
    ),
    suite_number="3015",
    deck_number="3",
    balance_due="0 \u2014 Paid in Full",
    flights=["\u26a0 Flights \u2014 Not yet booked"],
    flight_notes=VIKING_FLIGHTS_NOTE,
    hotel_transfers=VIKING_HOTEL_NOTE,
    excursion_count="0",
    excursions=[],
    upcoming=[
        {"date": "Aug 19", "description": "Cancel penalty 20% begins (E-120) \u2014 insurance should be in place before this"},
        {"date": "Dec 10", "description": "Excursion & dining selections close (E-7)"},
        {"date": "Dec 17", "description": "Embarkation \u2014 Panama City (Fuerte Amador), 3:00 PM"},
        {"date": "Dec 27", "description": "Disembarkation \u2014 Ft. Lauderdale (Port Everglades), 5:00 AM"},
    ],
    action_items=[
        "Flights \u2014 Not yet booked. Panama City (PTY) out Dec 17, Ft. Lauderdale (FLL) back Dec 27. I\u2019ll coordinate options with the group.",
        "Travel insurance \u2014 The pre-existing condition window has closed (Feb 23), but a standard policy is still available and worth having before the cancel penalty begins in August.",
        "Transfers \u2014 Panama City airport to pier and Ft. Lauderdale pier to airport both need to be arranged.",
        "Guest profile forms \u2014 I\u2019ll send those along for you and Erica \u2014 passport details help with pre-registration.",
        "Shipboard credits \u2014 You have $200 in onboard credit ($100/person) for shore excursions, dining, or onboard purchases.",
    ],
    closing_text=(
        "Kyle and the group are all confirmed on the same sailing. "
        "Cruise is paid \u2014 I\u2019ll be in touch as we work through flights, insurance, and transfers."
    ),
)
(output_dir / "Morton_Validation_Mar2026.html").write_text(morton, encoding="utf-8")

# ── SAVE TO COMMANDER REVIEW ────────────────────────────────
cr_dir = ROOT / "Commander_Review"
cr_dir.mkdir(parents=True, exist_ok=True)
(cr_dir / "26_McLeod_Validation_Email.html").write_text(mcleod, encoding="utf-8")
(cr_dir / "27_Westbrook_Validation_Email.html").write_text(westbrook, encoding="utf-8")

print("\u2713 Rendered 5 validation emails:")
for name in ["Furlow", "Ely", "Nichols", "McLeod", "Westbrook"]:
    print(f"  \u2192 {output_dir}/{name}_Validation_Mar2026.html")
print(f"\n\u2713 Commander Review drafts:")
print(f"  \u2192 {cr_dir}/26_McLeod_Validation_Email.html")
print(f"  \u2192 {cr_dir}/27_Westbrook_Validation_Email.html")


# ── RENDERED HTML BY CLIENT NAME ─────────────────────────────
rendered = {
    "Furlow": furlow,
    "Ely": ely,
    "Nichols": nichols,
    "McLeod": mcleod,
    "Westbrook": westbrook,
    "Kyle": kyle,
    "Roger": roger,
    "Morton": morton,
}

# Current batch — preview only these 5 to Commander
PREVIEW_BATCH = ["Furlow", "Ely", "Nichols", "Kyle", "Roger", "Morton"]


# ── SEND FUNCTIONS ───────────────────────────────────────────
def _get_service():
    from thunderbird_gmail import _get_gmail_service
    return _get_gmail_service()


def send_to_commander():
    """Send current batch as preview to Commander only."""
    service = _get_service()
    for name in PREVIEW_BATCH:
        html = rendered[name]
        client = CLIENTS[name]
        msg = MIMEMultipart("alternative")
        msg["to"] = "johnloucks3@gmail.com"
        msg["from"] = '"Dani Moreau \u2014 Concierge Intelligence" <concierge@d2mluxury.quest>'
        msg["reply-to"] = "johnloucks3@gmail.com"
        trip_label = {
            "Furlow": "Scandinavia (Touch 2)", "Ely": "Scandinavia (Touch 1)",
            "Kyle": "Panama Canal \u2014 Kyle & Rosalie", "Roger": "Panama Canal \u2014 Roger & Nick",
            "Morton": "Panama Canal \u2014 Josh & Erica",
            "Nichols": "Scandinavia", "McLeod": "Mediterranean (Silver Muse)",
            "Westbrook": "Pacific (Silver Nova)",
        }.get(name, "Voyage")
        msg["subject"] = f"[PREVIEW] {name}: {trip_label} \u2014 Validation Email"

        plain = f"Preview of {name} validation email. Client To: {client['to']}. View in HTML."
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        print(f"\u2713 DRAFT created for {name} (ID: {draft.get('id')})")
        print(f"  Client To: {client['to']}")

    try:
        from core.ai_infra.staff_signal_bus import post as post_signal
        post_signal(
            from_persona="dani",
            type="OPINE",
            subject=f"Validation Email Drafts Staged for Commander Review ({len(PREVIEW_BATCH)} clients)",
            detail=f"Rendered and staged preview validation drafts for: {', '.join(PREVIEW_BATCH)}.",
            priority="med",
        )
    except Exception:
        pass



def send_to_clients():
    """Send each email to actual clients, CC concierge + Commander."""
    service = _get_service()
    for name, html in rendered.items():
        client = CLIENTS[name]
        msg = MIMEMultipart("alternative")
        msg["to"] = client["to"]
        msg["from"] = '"Dani Moreau \u2014 Concierge Intelligence" <concierge@d2mluxury.quest>'
        msg["reply-to"] = "johnloucks3@gmail.com"
        msg["cc"] = "concierge@d2mluxury.quest, johnloucks3@gmail.com"
        msg["subject"] = "Your Scandinavia Voyage \u2014 Quick Review Before Final Payment"

        plain = f"Please view this email in an HTML-capable email client for the full formatted version."
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"\u2713 SENT to {name}: {client['to']} (ID: {sent.get('id')})")


if __name__ == "__main__":
    if "--send-clients" in sys.argv:
        send_to_clients()
    elif "--send" in sys.argv or "--preview" in sys.argv:
        send_to_commander()
