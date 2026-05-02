#!/usr/bin/env python3
"""
D2M Validation Email Generator
Dani Moreau voice · Kit A–F checklist · Commander-review output

Usage:
    python3 validation_email_generator.py <dossier_path> [--days-out N]
    python3 validation_email_generator.py --demo kuklinski|mcleod|loucks

Kit Definitions:
    Kit A — Cruise & Voyage (booking, stateroom, payment)
    Kit B — Flights (PNRs, seats, routes)
    Kit C — Hotels (pre/post, confirmation, benefits)
    Kit D — Transfers (all ground transport legs)
    Kit E — Excursions & Dining (port excursions, specialty restaurants)
    Kit F — Insurance & Documents (coverage, passports, guest forms)

Voice Rules (Standing Order 25 MAR 2026):
    1. No ⚠ WARNING flags on unpaid items — list clearly, no alarm bells
    2. Never "happy to help" / "glad to assist" — use direct action language
    3. Don't announce the concierge relationship — start with what's known
    4. One-line close — no superlatives ("extraordinary," "magnificent")
    5. Guest form emails → reference OA portal link (24-hour expiry)

Gold Standard: McLeod Mediterranean v3 (Commander tone directive 16 MAR 2026)
    - "I'd like to suggest" not "you need to"
    - "When you're ready" not "please do this by"
    - Present → suggest → defer, never direct
"""

import re
import sys
import json
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

KIT_LABELS = {
    "A": "Cruise & Voyage",
    "B": "Flights",
    "C": "Hotels",
    "D": "Transfers",
    "E": "Excursions & Dining",
    "F": "Insurance & Documents",
}

STATUS_CONFIRMED = "✅ Confirmed"
STATUS_PENDING   = "Pending your decision"
STATUS_OPEN      = "Not yet arranged"
STATUS_DEFERRED  = "Deferred — revisit later"

FROM_ADDRESS = "concierge@d2mluxury.quest (d2mconcierge@gmail.com)"
SIGN_OFF = "Thanks"
SIGNATURE = "Dani Moreau\nDreams2Memories Travel, LLC\nconcierge@d2mluxury.quest"


# ─── Voice Rules Engine ───────────────────────────────────────────────────────

VOICE_VIOLATIONS = [
    # Rule 1: No ⚠ on unpaid
    (r"⚠\s*[A-Z ]*NOT YET PAID[A-Z ]*", ""),
    (r"⚠\s*UNPAID", ""),
    # Rule 2: No "happy/glad to help"
    (r"\bhappy to help\b", "I can"),
    (r"\bglad to help\b", "I can"),
    (r"\bpleased to assist\b", ""),
    (r"\bwe will be (happy|glad)\b", "I'm happy"),
    (r"\bwe('ll| will) be happy to\b", "I can"),
    # Rule 3: No concierge announcement
    (r"As your (travel concierge|concierge|travel advisor),?\s*", ""),
    (r"We('re| are) here to help (you )?(with )?", ""),
    # Misc cleaning
    (r"\n{3,}", "\n\n"),
]


def apply_voice_rules(text: str) -> str:
    """Scrub all voice violations. Safe to run on any draft."""
    for pattern, replacement in VOICE_VIOLATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


# ─── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class KitItem:
    """Single checklist item within a kit."""
    label: str
    status: str  # Use STATUS_* constants or custom string
    detail: str = ""
    action_needed: bool = False
    action_text: str = ""


@dataclass
class ValidationData:
    """Structured input for one validation email."""
    # Identity
    client_name: str
    greeting: str                    # "Erik and Melissa" / "Kyle" / "John and Susan"
    to_addresses: list[str]
    cc_addresses: list[str]

    # Trip
    ship: str
    cruise_line: str
    voyage: str
    embarkation: str
    disembarkation: str
    departure_date: date
    booking_ref: str
    days_out: int

    # Kit A — Cruise
    staterooms: list[dict]           # [{"guests": ..., "cabin": ..., "status": ...}]
    payment_total: str
    payment_status: str              # "PAID IN FULL" / "Balance due: $X by DATE"
    cruise_inclusions: list[str]     # ["All meals", "Shore excursions", ...]

    # Kit B — Flights
    flights: list[dict]              # [{"leg": "OUT", "flight": ..., "route": ..., ...}]

    # Kit C — Hotels
    hotels: list[dict]               # [{"name": ..., "dates": ..., "room": ..., "status": ...}]

    # Kit D — Transfers
    transfers: list[dict]            # [{"segment": ..., "status": ..., "detail": ...}]

    # ── Fields with defaults below (must follow non-defaults) ──
    flight_notes: str = ""
    hotel_notes: str = ""
    transfer_notes: str = ""

    # Kit E — Excursions + Dining
    excursions: list[dict] = field(default_factory=list)
    dining: list[dict] = field(default_factory=list)
    onboard_charges_total: str = ""

    # Kit F — Insurance + Documents
    insurance_status: str = ""
    insurance_note: str = ""
    passport_status: str = ""
    guest_form_status: str = ""

    # Open items for client action
    open_items: list[str] = field(default_factory=list)

    # Next milestone dates
    upcoming_dates: list[dict] = field(default_factory=list)  # [{"date": ..., "label": ...}]

    # Custom closing line (one sentence, no superlatives)
    close_line: str = ""


# ─── Section Builders ─────────────────────────────────────────────────────────

def build_subject(data: ValidationData) -> str:
    return f"{data.ship} {data.voyage} — Where Everything Stands"


def build_kit_a(data: ValidationData) -> str:
    """Cruise & Voyage section."""
    lines = [f"**{KIT_LABELS['A']}**", ""]
    lines.append(
        f"{data.ship} ({data.cruise_line}), {data.embarkation} to {data.disembarkation} — "
        f"departing {data.departure_date.strftime('%B %-d, %Y')}. "
        f"*{data.payment_total} — {data.payment_status}.*"
    )
    lines.append("")

    if len(data.staterooms) > 1:
        lines.append("| Guests | Stateroom | Status |")
        lines.append("|--------|-----------|--------|")
        for sr in data.staterooms:
            lines.append(f"| {sr['guests']} | {sr['cabin']} | {sr['status']} |")
    elif data.staterooms:
        sr = data.staterooms[0]
        lines.append(f"*{sr['cabin']}* — {sr['status']}")

    if data.cruise_inclusions:
        lines.append("")
        lines.append("What's included: " + " · ".join(data.cruise_inclusions))

    return "\n".join(lines)


def build_kit_b(data: ValidationData) -> str:
    """Flights section."""
    lines = [f"**{KIT_LABELS['B']}**", ""]

    if not data.flights:
        if data.flight_notes:
            lines.append(data.flight_notes)
        else:
            lines.append(
                "No flights booked yet. When you're ready to start on those, "
                "I'll pull options together — routing, timing, and class."
            )
        return "\n".join(lines)

    for f in data.flights:
        leg_label = f.get("leg_label", f.get("leg", ""))
        lines.append(
            f"- *{leg_label}:* {f.get('flight', '')} — {f.get('route', '')}"
            + (f", {f['date']}" if f.get('date') else "")
            + (f" ({f['time']})" if f.get('time') else "")
            + (f" · Seats: {f['seats']}" if f.get('seats') else "")
            + (f" · PNR: {f['pnr']}" if f.get('pnr') else "")
        )

    if data.flight_notes:
        lines.append("")
        lines.append(data.flight_notes)

    return "\n".join(lines)


def build_kit_c(data: ValidationData) -> str:
    """Hotels section."""
    lines = [f"**{KIT_LABELS['C']}**", ""]

    if not data.hotels:
        if data.hotel_notes:
            lines.append(data.hotel_notes)
        else:
            lines.append("No hotel stays arranged yet. I'll research options once flights are confirmed.")
        return "\n".join(lines)

    for h in data.hotels:
        name = h.get("name", "")
        dates = h.get("dates", "")
        room = h.get("room", "")
        status = h.get("status", "")
        benefits = h.get("benefits", [])

        lines.append(f"- *{h.get('label', 'Hotel')}:* {name} — {room}, {dates}. {status}.")
        if benefits:
            lines.append(f"  Benefits: {', '.join(benefits)}.")

    if data.hotel_notes:
        lines.append("")
        lines.append(data.hotel_notes)

    return "\n".join(lines)


def build_kit_d(data: ValidationData) -> str:
    """Transfers section."""
    lines = [f"**{KIT_LABELS['D']}**", ""]

    if not data.transfers:
        if data.transfer_notes:
            lines.append(data.transfer_notes)
        else:
            lines.append("Transfers not yet arranged. I'll coordinate these once flights and hotels are confirmed.")
        return "\n".join(lines)

    confirmed = [t for t in data.transfers if t.get("confirmed")]
    open_legs  = [t for t in data.transfers if not t.get("confirmed")]

    for t in confirmed:
        lines.append(f"✅ {t['segment']}" + (f" — {t.get('detail', '')}" if t.get('detail') else ""))
    for t in open_legs:
        lines.append(f"- *Open:* {t['segment']}" + (f" — {t.get('detail', '')}" if t.get('detail') else ""))

    if data.transfer_notes:
        lines.append("")
        lines.append(data.transfer_notes)

    return "\n".join(lines)


def build_kit_e(data: ValidationData) -> str:
    """Excursions & Dining section."""
    lines = [f"**{KIT_LABELS['E']}**", ""]

    if data.excursions:
        lines.append(f"*Shore Excursions ({len(data.excursions)} booked)*")
        lines.append("")
        for ex in data.excursions:
            cost_str = f" (${ex['cost']:,.0f})" if ex.get('cost') else " (included)"
            lines.append(f"- {ex['date']} {ex['port']}: {ex['name']}{cost_str}")
        lines.append("")
    else:
        lines.append("Shore excursions not yet selected. I'll put together port-by-port options when you're ready.")
        lines.append("")

    if data.dining:
        lines.append(f"*Specialty Dining ({len(data.dining)} reservations)*")
        lines.append("")
        for d in data.dining:
            cost_str = f" (${d['cost']:,.0f})" if d.get('cost') else " (included)"
            lines.append(f"- {d['date']}: {d['restaurant']}{cost_str}")
        lines.append("")
    else:
        lines.append("Specialty dining not yet reserved. I'll share recommendations when you're ready to book.")
        lines.append("")

    if data.onboard_charges_total:
        lines.append(f"*Total onboard charges (excursions + dining): {data.onboard_charges_total} — settled onboard at the end of the voyage.*")

    return "\n".join(lines)


def build_kit_f(data: ValidationData) -> str:
    """Insurance & Documents section."""
    lines = [f"**{KIT_LABELS['F']}**", ""]

    insurance_line = data.insurance_status or "Travel insurance status unknown — worth confirming before departure."
    lines.append(f"- *Travel Insurance:* {insurance_line}")
    if data.insurance_note:
        lines.append(f"  {data.insurance_note}")

    passport_line = data.passport_status or "Passport validity not yet confirmed — please verify expiry dates."
    lines.append(f"- *Passports:* {passport_line}")

    guest_form_line = data.guest_form_status or "Guest forms not yet submitted — due at E-60."
    lines.append(f"- *Guest Forms:* {guest_form_line}")

    return "\n".join(lines)


def build_upcoming_dates(data: ValidationData) -> str:
    """Coming up next section."""
    if not data.upcoming_dates:
        return ""
    lines = ["**What's Coming Up**", ""]
    for item in data.upcoming_dates:
        lines.append(f"- **{item['date']}:** {item['label']}")
    return "\n".join(lines)


# ─── Email Assembler ──────────────────────────────────────────────────────────

def generate_email(data: ValidationData) -> tuple[str, str]:
    """
    Generate full validation email.
    Returns (commander_header, email_body) as separate strings.
    """
    now = datetime.now().strftime("%Y-%m-%d")

    # Commander header (not sent to client)
    cc_list = [a for a in (data.cc_addresses or ["johnloucks3@gmail.com"]) if a not in data.to_addresses]
    cc_str = ', '.join(cc_list) if cc_list else "(none — commander is primary recipient)"
    header = f"""## EMAIL HEADER (Commander Reference — do not send)
```
From: {FROM_ADDRESS}
To: {', '.join(data.to_addresses)}
Cc: {cc_str}
Subject: {build_subject(data)}
Date: {now}
Status: DRAFT — Commander Review
```

---
"""

    # Email body
    intro_line = (
        f"{data.days_out} days to embarkation — here's where everything stands."
        if data.days_out <= 90
        else f"You're {data.days_out} days out — here's where everything stands."
    )

    body_sections = [
        f"Hi {data.greeting},",
        "",
        intro_line,
        "",
        "---",
        "",
        build_kit_a(data),
        "",
        "---",
        "",
        build_kit_b(data),
        "",
        "---",
        "",
        build_kit_c(data),
        "",
        "---",
        "",
        build_kit_d(data),
        "",
        "---",
        "",
        build_kit_e(data),
        "",
        "---",
        "",
        build_kit_f(data),
    ]

    # Upcoming dates
    upcoming = build_upcoming_dates(data)
    if upcoming:
        body_sections += ["", "---", "", upcoming]

    # Open items
    if data.open_items:
        body_sections += [
            "",
            "---",
            "",
            "**A Few Things When You Get a Chance**",
            "",
        ]
        for i, item in enumerate(data.open_items, 1):
            body_sections.append(f"{i}. {item}")

    # Close
    close = data.close_line or "Looking forward to building this out with you."
    body_sections += [
        "",
        "---",
        "",
        close,
        "",
        SIGN_OFF + ",",
        "",
        SIGNATURE,
    ]

    body = apply_voice_rules("\n".join(body_sections))
    return header, body


# ─── Pre-Built Client Data ────────────────────────────────────────────────────

def kuklinski_data() -> ValidationData:
    """Kuklinski Group — Viking Mars Panama Canal Dec 17, 2026."""
    return ValidationData(
        client_name="Kuklinski Group",
        greeting="Kyle",
        to_addresses=["kyle.kuklinski@gmail.com"],
        cc_addresses=["johnloucks3@gmail.com"],
        ship="Viking Mars",
        cruise_line="Viking",
        voyage="Panama Canal",
        embarkation="Panama City (PTY)",
        disembarkation="Fort Lauderdale (FLL)",
        departure_date=date(2026, 12, 17),
        booking_ref="9593880 / 9593873 / 9595029",
        days_out=232,
        staterooms=[
            {"guests": "Kyle & Rosalie Kuklinski",       "cabin": "4122, DV1, Deck 4",        "status": "✅ Confirmed"},
            {"guests": "Roger & Dr. Nicholas Kuklinski", "cabin": "8012, DV1, Deck 8",        "status": "✅ Confirmed"},
            {"guests": "Joshua Morton & Erica Dodge",    "cabin": "3015, V1-Veranda, Deck 3", "status": "✅ Confirmed"},
        ],
        payment_total="$21,244",
        payment_status="paid in full",
        cruise_inclusions=[
            "All meals & beverages",
            "Shore excursions",
            "Wi-Fi",
            "Gratuities",
        ],
        flights=[],
        flight_notes=(
            "All three couples will need flights into Panama City (PTY) arriving by 1:00 PM on December 17 — "
            "3:00 PM is embarkation. Return is from Fort Lauderdale (FLL) on December 27. "
            "Whenever you're ready to get started, I'll put together options for everyone."
        ),
        hotels=[],
        hotel_notes=(
            "If any of the group is flying in the day before, a pre-cruise night in Panama City "
            "is worth considering — there are some good options near the Amador terminal. "
            "Just let me know if that's something you'd like me to look into."
        ),
        transfers=[],
        transfer_notes=(
            "Ground transfers (airport to cruise terminal in Panama City; "
            "Port Everglades to FLL airport on December 27) will be coordinated once flights are confirmed."
        ),
        excursions=[],
        dining=[],
        insurance_status="Not yet arranged",
        insurance_note=(
            "The pre-existing condition waiver window has passed (closed February 23), "
            "but post-departure coverage is still available. Worth a conversation when you're ready."
        ),
        passport_status="Not yet verified — need all six guests' expiry dates. Must be valid through June 2027.",
        guest_form_status="Five of six received. Josh Morton's form is still open — Kyle, you mentioned you'd help Josh get sorted.",
        open_items=[
            "Flights — whenever you're ready, I'll pull round-trip options for all three couples (PTY inbound, FLL return).",
            "Pre-cruise hotel in Panama City — worth a conversation if anyone is flying in December 16.",
            "Passport validity — could you confirm expiry dates for all six guests when you get a chance? We need validity through June 2027.",
            "Josh Morton's guest registration form — let me know once that's resolved and I'll close it out.",
        ],
        upcoming_dates=[
            {"date": "Dec 16", "label": "Recommended arrival in Panama City (if flying in a day early)"},
            {"date": "Dec 17", "label": "Embarkation — Panama City, 3:00 PM"},
            {"date": "Dec 27", "label": "Disembarkation — Fort Lauderdale (Port Everglades), 5:00 AM"},
        ],
        close_line="Panama City in December is going to be something — looking forward to building the rest of this out with you.",
    )


def mcleod_data() -> ValidationData:
    """McLeod/McGlasson — Silver Muse Mediterranean Jun 23, 2026."""
    return ValidationData(
        client_name="McLeod / McGlasson",
        greeting="Erik and Melissa",
        to_addresses=["emcleod@gmail.com", "memcglas@gmail.com"],
        cc_addresses=["johnloucks3@gmail.com"],
        ship="Silver Muse",
        cruise_line="Silversea",
        voyage="Mediterranean",
        embarkation="Civitavecchia (Rome)",
        disembarkation="Fusina (Venice)",
        departure_date=date(2026, 6, 23),
        booking_ref="298475-25",
        days_out=55,
        staterooms=[
            {"guests": "Erik McLeod & Melissa McGlasson", "cabin": "Suite 617, Deck 6, Classic Veranda", "status": "✅ Confirmed"},
        ],
        payment_total="$27,813.32",
        payment_status="paid in full",
        cruise_inclusions=[
            "All meals & premium beverages",
            "Shore excursions",
            "Butler service",
            "Gratuities",
        ],
        flights=[
            {
                "leg":       "OUT",
                "leg_label": "Outbound",
                "flight":    "UA 177",
                "route":     "Denver → Rome FCO",
                "date":      "June 18",
                "time":      "5:45 PM",
                "seats":     "Pending",
                "pnr":       "NFBDP6",
            },
            {
                "leg":       "RET1",
                "leg_label": "Return Leg 1",
                "flight":    "AC 817",
                "route":     "Venice → Toronto",
                "date":      "July 6",
                "time":      "12:20 PM",
                "seats":     "Pending",
                "pnr":       "CXNT6Q",
            },
            {
                "leg":       "RET2",
                "leg_label": "Return Leg 2",
                "flight":    "AC 1041",
                "route":     "Toronto → Denver",
                "date":      "July 6",
                "time":      "6:40 PM (arr. 8:22 PM)",
                "seats":     "Pending",
                "pnr":       "CXNT6Q",
            },
        ],
        flight_notes=(
            "Seat assignments are still open on all three legs. "
            "I can call United and Air Canada to get those locked in — "
            "or if you'd prefer to handle it yourselves, that works too."
        ),
        hotels=[
            {
                "label": "Rome, Pre-Cruise",
                "name": "Baglioni Hotel Regina",
                "dates": "June 19–23 (4 nights)",
                "room": "Grand Deluxe Room",
                "status": "✅ Confirmed",
                "benefits": ["Daily breakfast", "$100 property credit", "Complimentary Wi-Fi", "Welcome prosecco"],
            },
            {
                "label": "Venice, Post-Cruise",
                "name": "Hilton Molino Stucky",
                "dates": "July 3–6 (3 nights)",
                "room": "Executive Suite",
                "status": "✅ Confirmed",
                "benefits": [],
            },
        ],
        hotel_notes=(
            "One question on Rome: your outbound flight arrives June 18 at 12:20 PM local time, "
            "but the Baglioni check-in is June 19. Would you like me to look at an option for June 18 night, "
            "or is that already sorted on your end?"
        ),
        transfers=[
            {"segment": "June 22: Silversea Private Executive Home Transfer",        "confirmed": True},
            {"segment": "June 23: Silversea group transfer — hotel to pier",          "confirmed": True},
            {"segment": "July 3: Silversea group transfer — pier to hotel",           "confirmed": True, "detail": "note: pier to Hilton Molino Stucky connection still to work out — a water taxi is one option"},
            {"segment": "July 3: Silversea Private Executive Home Transfer",          "confirmed": True},
            {"segment": "FCO Airport → Baglioni Regina (June 19)",                   "confirmed": False, "detail": "Baglioni concierge car at €110 — just need the green light"},
            {"segment": "Hilton Molino Stucky → VCE Airport (July 6)",               "confirmed": False, "detail": "water taxi is the most elegant option — putting together choices"},
        ],
        transfer_notes=(
            "The pier-to-hotel leg on July 3 gets you from Marghera, but the connection into "
            "the Hilton Molino Stucky is something I'd like to map out for you separately — "
            "a water taxi is actually a wonderful way to arrive in Venice."
        ),
        excursions=[
            {"date": "June 24",  "port": "Naples",         "name": "Ruins of Herculanum",              "cost": None},
            {"date": "June 25",  "port": "Giardini Naxos", "name": "Greek & Roman Taormina",           "cost": None},
            {"date": "June 26",  "port": "Siracusa",       "name": "Baroque Town of Noto",             "cost": None},
            {"date": "June 27",  "port": "Valletta",       "name": "Game of Thrones",                  "cost": None},
            {"date": "June 29",  "port": "Kotor",          "name": "Speedboat Adventure to Blue Cave", "cost": 318},
            {"date": "June 30",  "port": "Dubrovnik",      "name": "Day at the Beach Club",            "cost": 278},
            {"date": "July 1",   "port": "Split",          "name": "UNESCO World Heritage Sites",      "cost": None},
            {"date": "July 2",   "port": "Zadar",          "name": "Nin Salt Works & Royal Vineyards", "cost": None},
        ],
        dining=[
            {"date": "June 24", "restaurant": "La Dame",     "cost": 120},
            {"date": "June 26", "restaurant": "The Grill",   "cost": None},
            {"date": "June 28", "restaurant": "Silver Note", "cost": None},
            {"date": "July 1",  "restaurant": "La Terrazza", "cost": None},
        ],
        onboard_charges_total="$716",
        insurance_status="✅ Paid and confirmed",
        passport_status="Not yet confirmed — validity must extend through January 2027 (6-month rule from July 6 return).",
        guest_form_status="Please verify completion at my.silversea.com.",
        open_items=[
            "June 18 lodging — do you have somewhere to stay, or would you like me to look at options?",
            "Seat assignments — would you prefer I call United and Air Canada, or would you rather handle those?",
            "FCO airport transfer — Baglioni concierge car at €110. Just say the word and I'll arrange it.",
        ],
        upcoming_dates=[
            {"date": "May 1",   "label": "Confirm all seat assignments"},
            {"date": "June 18", "label": "Departure day — Denver to Rome"},
            {"date": "June 23", "label": "Embarkation — Civitavecchia"},
            {"date": "July 22", "label": "Regent Grandeur (Lesser Antilles) final payment due — $12,393.15"},
        ],
        close_line="Sicily, Malta, Kotor, Dubrovnik — looking forward to this one for you both.",
    )


def loucks_data() -> ValidationData:
    """Loucks — Regent Seven Seas Grandeur Panama Canal Dec 29, 2026."""
    return ValidationData(
        client_name="John & Susan Loucks",
        greeting="John and Susan",
        to_addresses=["johnloucks3@gmail.com"],
        cc_addresses=[],
        ship="Seven Seas Grandeur",
        cruise_line="Regent Seven Seas",
        voyage="Panama Canal",
        embarkation="Fort Lauderdale (TBC with Regent)",
        disembarkation="Los Angeles or San Diego (TBC)",
        departure_date=date(2026, 12, 29),
        booking_ref="3122006",
        days_out=244,
        staterooms=[
            {"guests": "John & Susan Loucks", "cabin": "TBD — cabin assignment pending", "status": "✅ Confirmed"},
        ],
        payment_total="Balance TBD",
        payment_status="Final payment due September 30, 2026",
        cruise_inclusions=[
            "All meals & ultra-premium beverages",
            "Shore excursions",
            "Business class air (standard RSSC offer)",
            "Gratuities & butler service",
        ],
        flights=[],
        flight_notes=(
            "Flights not yet booked. I'd like to start researching options once we confirm "
            "which port Regent is using for embarkation — likely Fort Lauderdale. "
            "I'll get that confirmed and put some options together."
        ),
        hotels=[],
        hotel_notes=(
            "A pre-cruise night near the embarkation port is worth considering. "
            "Once the port is confirmed, I'll research a couple of options and share them."
        ),
        transfers=[],
        transfer_notes="All ground transfers will be coordinated once flights and embarkation port are confirmed.",
        excursions=[],
        dining=[],
        insurance_status="Not yet arranged",
        insurance_note=(
            "For a 16-night luxury trip, travel insurance is well worth having in place before the FPD. "
            "I'd suggest we look at options by late summer — I'll put together a comparison when you're ready."
        ),
        passport_status=(
            "Not yet verified — both passports must be valid through July 2027 "
            "(6-month rule from January 14, 2027 disembarkation)."
        ),
        guest_form_status="Guest forms due at E-60 (November 29, 2026) — I'll send instructions well ahead of that.",
        open_items=[
            "Susan's contact information — email and phone, whenever convenient. "
            "I'd like to make sure she's looped in on all correspondence.",
            "Cabin category preference — any strong preferences between veranda suite, concierge suite, or penthouse? "
            "Regent has several excellent options on the Grandeur.",
            "Embarkation port — I'll confirm with Regent which terminal they're using for this sailing.",
        ],
        upcoming_dates=[
            {"date": "Sep 30, 2026", "label": "Final payment due (hard deadline)"},
            {"date": "Oct 30, 2026", "label": "FPD verification + dining/excursion bookings open"},
            {"date": "Nov 29, 2026", "label": "Final itinerary delivery + guest forms due"},
            {"date": "Dec 29, 2026", "label": "Embarkation"},
        ],
        close_line="Sixteen nights through the Canal — this is going to be a remarkable voyage. Looking forward to building it out.",
    )


# ─── Demo Runner ──────────────────────────────────────────────────────────────

DEMO_CLIENTS = {
    "kuklinski": kuklinski_data,
    "mcleod":    mcleod_data,
    "loucks":    loucks_data,
}


def run_demo(client_key: str) -> str:
    """Generate and return a complete email for a named demo client."""
    if client_key not in DEMO_CLIENTS:
        return f"Unknown client '{client_key}'. Available: {', '.join(DEMO_CLIENTS)}"
    data = DEMO_CLIENTS[client_key]()
    header, body = generate_email(data)
    return header + "\n" + body


def main():
    args = sys.argv[1:]
    if "--demo" in args:
        idx = args.index("--demo")
        client = args[idx + 1] if idx + 1 < len(args) else ""
        print(run_demo(client.lower()))
    elif args:
        # Load from dossier file (basic mode — data still needs to be structured)
        dossier_path = args[0]
        print(f"[Generator] Dossier-parse mode: {dossier_path}")
        print("[Generator] For full auto-parse, use the pre-built demo clients or extend load_dossier().")
    else:
        print(__doc__)
        print("\nDemo clients:", ", ".join(DEMO_CLIENTS.keys()))


if __name__ == "__main__":
    main()
