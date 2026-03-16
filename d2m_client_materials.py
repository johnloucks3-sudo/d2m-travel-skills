"""
D2M Client Materials — OA Template Improvements (Item #3)
=========================================================

The "D2M Experience Layer" — supplementary luxury content that rides
alongside Outside Agents (OA / My Booking Genie) transactional portals.

OA handles: payments, e-signatures, booking confirmations.
D2M layers: destination guides, pre-departure packets, dining guides,
            welcome packets, and EXEC-voiced supplement emails.

Material Types:
  HOTEL_GUIDE       — existing pipeline (itinerary_finishing_pipeline.py)
  DESTINATION_GUIDE — curated local experiences, restaurants, cultural notes
  PRE_DEPARTURE     — packing, weather, visa, emergency contacts, connections
  DINING_GUIDE      — restaurant recs with reservation links
  WELCOME_PACKET    — combines all of the above into one package

Persona Integration:
  A2 (Dembe)  — destination research, visa/entry intel
  A10 (Ikeda) — connection times, logistics, crisis contacts
  EXEC        — narrative voice for all client-facing copy

MCP Tools:
  generate_client_materials  — full welcome packet for a booking
  generate_destination_guide — standalone destination guide

Integrates with: travel_mcp_server.py, thunderbird_personas.py
Dependencies: jinja2, weasyprint (optional for PDF)
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# MATERIAL TYPE ENUM
# ============================================================================

class MaterialType(str, Enum):
    """Types of supplementary D2M client materials."""
    HOTEL_GUIDE = "hotel_guide"
    DESTINATION_GUIDE = "destination_guide"
    PRE_DEPARTURE = "pre_departure"
    DINING_GUIDE = "dining_guide"
    WELCOME_PACKET = "welcome_packet"


# ============================================================================
# BRAND TOKENS — mirrors d2m_base.css.j2
# ============================================================================

D2M_CSS = """
:root {
    --navy: #0d1b2e;
    --navy2: #152540;
    --navy3: #1e3358;
    --gold: #c9a84c;
    --gold-light: #e8c97a;
    --gold-pale: #f5e9c8;
    --muted: #8a9ab5;
    --cream: #faf8f2;
    --text-primary: #2c2c2c;
    --text-secondary: #5a5a5a;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: var(--cream);
    color: var(--text-primary);
    line-height: 1.7;
    font-size: 15px;
}

.d2m-material {
    max-width: 900px;
    margin: 0 auto;
    background: white;
    box-shadow: 0 0 30px rgba(0,0,0,0.08);
}

/* Cover */
.material-cover {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy2) 60%, var(--navy3) 100%);
    color: white;
    text-align: center;
    padding: 70px 40px;
    border-bottom: 4px solid var(--gold);
}

.material-cover h1 {
    font-family: 'Playfair Display', 'Georgia', serif;
    font-size: 2.4em;
    font-weight: 700;
    margin-bottom: 10px;
    letter-spacing: -0.5px;
}

.material-cover .material-type-badge {
    display: inline-block;
    font-size: 0.7em;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--gold);
    border: 1px solid var(--gold);
    padding: 6px 18px;
    border-radius: 20px;
    margin-bottom: 20px;
}

.material-cover .subtitle {
    font-family: 'Cormorant Garamond', 'Georgia', serif;
    font-size: 1.2em;
    font-style: italic;
    color: rgba(255,255,255,0.8);
    margin-top: 15px;
}

.material-cover .meta-strip {
    font-size: 0.85em;
    color: rgba(255,255,255,0.55);
    margin-top: 20px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-top: 1px solid rgba(201,168,76,0.3);
    padding-top: 18px;
}

/* Sections */
.material-section {
    padding: 40px;
    border-bottom: 1px solid #eee;
}

.material-section:last-child {
    border-bottom: none;
}

.material-section h2 {
    font-family: 'Playfair Display', 'Georgia', serif;
    font-size: 1.6em;
    color: var(--navy);
    margin-bottom: 8px;
    font-weight: 600;
}

.material-section .section-accent {
    width: 50px;
    height: 3px;
    background: var(--gold);
    margin-bottom: 20px;
}

.material-section h3 {
    font-size: 1.1em;
    color: var(--navy2);
    margin: 20px 0 8px 0;
    font-weight: 600;
}

.material-section p, .material-section li {
    color: var(--text-secondary);
    line-height: 1.8;
    margin-bottom: 10px;
}

.material-section ul {
    padding-left: 24px;
}

/* Info cards */
.info-card {
    background: var(--cream);
    border-left: 4px solid var(--gold);
    border-radius: 8px;
    padding: 18px 22px;
    margin: 16px 0;
}

.info-card.emergency {
    border-left-color: #c0392b;
    background: #fef5f5;
}

.info-card.tip {
    border-left-color: #27ae60;
    background: #f0faf4;
}

.info-card h4 {
    font-size: 0.75em;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 8px;
    font-weight: 700;
}

.info-card.emergency h4 { color: #c0392b; }
.info-card.tip h4 { color: #27ae60; }

.info-card p {
    font-size: 0.95em;
    margin-bottom: 6px;
}

/* Restaurant cards */
.restaurant-card {
    background: white;
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 22px;
    margin: 14px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.restaurant-card h3 {
    color: var(--navy);
    margin: 0 0 6px 0;
    font-size: 1.15em;
}

.restaurant-card .cuisine-tag {
    display: inline-block;
    background: var(--gold-pale);
    color: var(--navy2);
    font-size: 0.75em;
    padding: 3px 10px;
    border-radius: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-right: 6px;
}

.restaurant-card .price-range {
    color: var(--gold);
    font-weight: 600;
    font-size: 0.9em;
}

.restaurant-card .ambiance {
    font-style: italic;
    color: var(--muted);
    font-size: 0.9em;
    margin-top: 6px;
}

/* Checklist */
.checklist {
    list-style: none;
    padding-left: 0;
}

.checklist li {
    padding: 6px 0 6px 28px;
    position: relative;
    border-bottom: 1px solid #f0f0f0;
}

.checklist li::before {
    content: '\\2610';
    position: absolute;
    left: 0;
    color: var(--gold);
    font-size: 1.2em;
}

/* Footer */
.material-footer {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy2) 100%);
    color: rgba(255,255,255,0.7);
    text-align: center;
    padding: 40px;
    font-size: 0.85em;
}

.material-footer .footer-brand {
    color: var(--gold);
    font-family: 'Playfair Display', 'Georgia', serif;
    font-size: 1.3em;
    margin-bottom: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
}

.material-footer a {
    color: var(--gold-light);
    text-decoration: none;
}

@media print {
    body { background: white; }
    .d2m-material { box-shadow: none; max-width: 100%; }
    .material-section { page-break-inside: avoid; }
}
"""


# ============================================================================
# PERSONA INTEGRATION
# ============================================================================

def _consult_persona(persona_id: str, query: str, max_tokens: int = 800) -> str:
    """Call a D2M persona via Groq and return the answer text.

    Falls back to a sensible default if the persona system is unavailable.
    """
    try:
        from thunderbird_personas import call_persona
        result = call_persona(persona_id, query, max_tokens=max_tokens)
        return result.get("answer", result.get("error", "No response."))
    except ImportError:
        logger.warning("thunderbird_personas not available — using fallback")
        return f"[Persona {persona_id} unavailable — manual input needed]"
    except Exception as e:
        logger.error(f"Persona {persona_id} call failed: {e}")
        return f"[Persona {persona_id} error: {e}]"


def _get_destination_intel(destination: str, dates: str, preferences: list = None) -> str:
    """A2 (Dembe) — destination research and intel."""
    pref_str = f" Client preferences: {', '.join(preferences)}." if preferences else ""
    query = (
        f"Provide a concise luxury travel briefing for {destination} "
        f"during {dates}.{pref_str} "
        f"Cover: key highlights, cultural context, seasonal considerations, "
        f"local transportation, safety notes, and any entry requirements. "
        f"Be specific and evidence-based. Confidence levels where appropriate."
    )
    return _consult_persona("A2", query, max_tokens=1000)


def _get_exec_narrative(topic: str, context: str) -> str:
    """EXEC (Solberg-Vega) — warm, literate client-facing voice."""
    query = (
        f"Write client-facing copy for a D2M luxury travel document. "
        f"Topic: {topic}\nContext: {context}\n"
        f"Voice: warm, literate, visually precise. Never corporate. Never generic. "
        f"Make the reader feel the anticipation of travel."
    )
    return _consult_persona("EXEC", query, max_tokens=800)


def _get_logistics_intel(booking_data: dict) -> str:
    """A10 (Ikeda) — connection times, logistics, crisis contacts."""
    dest = booking_data.get("destination", "unknown")
    dates = f"{booking_data.get('start_date', '?')} to {booking_data.get('end_date', '?')}"
    flights = booking_data.get("flights", "not specified")
    query = (
        f"Logistics briefing for client travel to {dest}, dates {dates}. "
        f"Flight info: {flights}. "
        f"Cover: connection time advice, airport tips, transfer logistics, "
        f"what can go wrong and how to handle it. Be specific and solutions-first."
    )
    return _consult_persona("A10", query, max_tokens=800)


# ============================================================================
# HTML HELPERS
# ============================================================================

def _wrap_html(title: str, material_type: str, subtitle: str,
               meta: str, body_html: str) -> str:
    """Wrap content in the D2M branded HTML shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{_esc(title)} — Dreams2Memories Travel</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800&family=Inter:wght@300;400;500;600&family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
    <style>{D2M_CSS}</style>
</head>
<body>
<div class="d2m-material">

    <div class="material-cover">
        <div class="material-type-badge">{_esc(material_type)}</div>
        <h1>{_esc(title)}</h1>
        <div class="subtitle">{_esc(subtitle)}</div>
        <div class="meta-strip">{_esc(meta)}</div>
    </div>

    {body_html}

    <div class="material-footer">
        <div class="footer-brand">Dreams2Memories Travel, LLC</div>
        <p><a href="mailto:johnloucks3@gmail.com">johnloucks3@gmail.com</a> &middot; (719) 291-0742</p>
        <p style="margin-top:8px;font-size:0.85em;opacity:0.5;">
            Generated {datetime.now().strftime('%B %d, %Y')} &middot; Confidential
        </p>
    </div>

</div>
</body>
</html>"""


def _section(title: str, content_html: str) -> str:
    """Render a branded section block."""
    return f"""
    <div class="material-section">
        <h2>{_esc(title)}</h2>
        <div class="section-accent"></div>
        {content_html}
    </div>"""


def _info_card(heading: str, body: str, card_class: str = "") -> str:
    """Render a branded info card."""
    cls = f"info-card {card_class}".strip()
    return f"""
        <div class="{cls}">
            <h4>{_esc(heading)}</h4>
            <p>{body}</p>
        </div>"""


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _prose_to_html(text: str) -> str:
    """Convert persona prose output to HTML paragraphs."""
    if not text:
        return ""
    # Strip model attribution line at the end
    lines = text.strip().split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("---") or stripped.startswith("_") and stripped.endswith("_"):
            continue
        if stripped:
            cleaned.append(stripped)
    paragraphs = "\n".join(cleaned).split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Detect bullet lists
        if p.startswith("- ") or p.startswith("* "):
            items = [li.lstrip("-* ").strip() for li in p.split("\n") if li.strip()]
            html_parts.append("<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>")
        else:
            html_parts.append(f"<p>{_esc(p)}</p>")
    return "\n".join(html_parts)


# ============================================================================
# MATERIAL GENERATORS
# ============================================================================

def generate_destination_guide(destination: str, dates: str,
                               preferences: list = None) -> str:
    """Generate a curated destination guide.

    Calls A2 (Dembe) for intel, EXEC for narrative voice.
    Returns formatted HTML ready for PDF rendering.
    """
    logger.info(f"Generating destination guide: {destination} ({dates})")

    # Gather intel from personas
    intel = _get_destination_intel(destination, dates, preferences)
    overview_narrative = _get_exec_narrative(
        f"Destination overview for {destination}",
        f"Travel dates: {dates}. Intel: {intel[:500]}"
    )

    pref_note = ""
    if preferences:
        pref_note = f"<p><strong>Your Interests:</strong> {', '.join(preferences)}</p>"

    body = ""

    # Section: Overview
    body += _section("Welcome to " + destination,
        _prose_to_html(overview_narrative) + pref_note
    )

    # Section: Intel from A2
    body += _section("Destination Intelligence",
        _prose_to_html(intel)
    )

    # Section: Cultural Tips
    cultural = _consult_persona("A2",
        f"Top 5 cultural etiquette tips for travelers visiting {destination}. "
        f"Be specific — customs, tipping, dress codes, local norms. Brief bullet format.",
        max_tokens=400
    )
    body += _section("Cultural Tips &amp; Etiquette",
        _prose_to_html(cultural)
    )

    # Section: Getting Around
    transport = _consult_persona("A10",
        f"Local transportation guide for {destination}: taxis, rideshare, public transit, "
        f"walking areas. What works best for luxury travelers? Brief and practical.",
        max_tokens=400
    )
    body += _section("Getting Around",
        _prose_to_html(transport)
    )

    return _wrap_html(
        title=f"Your Guide to {destination}",
        material_type="Destination Guide",
        subtitle=f"Curated by Dreams2Memories Travel for your {dates} journey",
        meta=f"Prepared {datetime.now().strftime('%B %Y')} &middot; Dreams2Memories Travel, LLC",
        body_html=body,
    )


def generate_pre_departure(client_name: str, booking_data: dict) -> str:
    """Generate a pre-departure packet.

    Includes packing, weather, visa/entry, emergency contacts,
    connection times (A10 Ikeda), and documents checklist.
    """
    dest = booking_data.get("destination", "your destination")
    dates = f"{booking_data.get('start_date', 'TBD')} to {booking_data.get('end_date', 'TBD')}"
    season = booking_data.get("season", "")

    logger.info(f"Generating pre-departure packet: {client_name} -> {dest}")

    body = ""

    # Section: Overview
    intro = _get_exec_narrative(
        f"Pre-departure greeting for {client_name}",
        f"Destination: {dest}, dates: {dates}. "
        f"Set the tone: excitement and confidence that everything is handled."
    )
    body += _section("Before You Go",
        _prose_to_html(intro)
    )

    # Section: Weather & Packing
    packing = _consult_persona("A2",
        f"Weather forecast summary and packing recommendations for {dest} during {dates}. "
        f"Season: {season}. Include expected temperatures, rainfall, and "
        f"specific clothing/gear suggestions for luxury travelers. Brief format.",
        max_tokens=500
    )
    body += _section("Weather &amp; Packing",
        _prose_to_html(packing)
    )

    # Section: Visa & Entry Requirements
    visa = _consult_persona("A2",
        f"Visa and entry requirements for US citizens traveling to {dest}. "
        f"Include: passport validity requirements, visa type needed, "
        f"COVID/health requirements if any, customs declarations. "
        f"Be precise with confidence levels.",
        max_tokens=500
    )
    body += _section("Visa &amp; Entry Requirements",
        _prose_to_html(visa) +
        _info_card("Important", "Always verify entry requirements with the destination's "
                   "embassy or consulate 2-4 weeks before departure. Requirements can change.", "tip")
    )

    # Section: Emergency Contacts
    d2m_phone = "(719) 291-0742"
    d2m_email = "johnloucks3@gmail.com"
    body += _section("Emergency Contacts",
        _info_card("Dreams2Memories Travel — 24/7", f"""
            <strong>John Loucks</strong><br>
            Phone: {d2m_phone}<br>
            Email: <a href="mailto:{d2m_email}">{d2m_email}</a><br>
            <em>Call or text anytime — we are your first call if something goes sideways.</em>
        """, "emergency") +
        _info_card("General Emergency Numbers",
            f"<strong>Local Emergency (most countries):</strong> 112<br>"
            f"<strong>US Embassy Abroad:</strong> +1-202-501-4444<br>"
            f"<strong>Nearest US Embassy/Consulate:</strong> Look up at "
            f"<a href='https://www.usembassy.gov/' target='_blank'>usembassy.gov</a>",
            "emergency"
        )
    )

    # Section: Connection Times & Logistics (A10 Ikeda)
    logistics = _get_logistics_intel(booking_data)
    body += _section("Travel Logistics &amp; Connections",
        _prose_to_html(logistics)
    )

    # Section: Documents Checklist
    checklist_items = [
        "Passport (valid 6+ months beyond return date)",
        "Visa (if required — see above)",
        "Travel insurance documents",
        "Flight confirmations / boarding passes",
        "Hotel / cruise confirmation",
        "Credit cards — notify bank of travel dates",
        "Copies of all documents (digital + physical)",
        "Prescription medications in original containers",
        "Emergency contact card",
        "D2M Travel contact info",
    ]
    extra_docs = booking_data.get("extra_documents", [])
    if extra_docs:
        checklist_items.extend(extra_docs)

    items_html = "".join(f"<li>{_esc(item)}</li>" for item in checklist_items)
    body += _section("Documents Checklist",
        f'<ul class="checklist">{items_html}</ul>'
    )

    return _wrap_html(
        title=f"Pre-Departure Guide",
        material_type="Pre-Departure Packet",
        subtitle=f"Prepared exclusively for {client_name}",
        meta=f"{dest} &middot; {dates} &middot; Dreams2Memories Travel, LLC",
        body_html=body,
    )


def generate_dining_guide(destination: str,
                          travel_style: str = "luxury") -> str:
    """Generate a dining guide for a destination.

    Includes restaurant recommendations, cuisine types, price range,
    ambiance, reservation tips, and local food experiences.
    """
    logger.info(f"Generating dining guide: {destination} ({travel_style})")

    # Get restaurant recommendations from A2
    recs = _consult_persona("A2",
        f"Recommend 5 restaurants in {destination} for {travel_style} travelers. "
        f"For each, provide: name, cuisine type, price range ($$-$$$$), "
        f"brief ambiance description, and one signature dish. "
        f"Mix fine dining with authentic local gems. Format as numbered list.",
        max_tokens=800
    )

    # Get food experiences from EXEC
    experiences = _get_exec_narrative(
        f"Local food experiences in {destination}",
        f"Write about food markets, cooking classes, food tours, "
        f"and unique culinary experiences. Style: {travel_style}."
    )

    # Get reservation tips
    tips = _consult_persona("A2",
        f"Reservation tips for dining in {destination}: "
        f"how far ahead to book, best apps/sites, tipping customs, "
        f"dress codes, meal times. Brief practical format.",
        max_tokens=400
    )

    body = ""

    # Section: Restaurant Recommendations
    body += _section("Restaurant Recommendations",
        _prose_to_html(recs)
    )

    # Section: Local Food Experiences
    body += _section("Food Experiences &amp; Markets",
        _prose_to_html(experiences)
    )

    # Section: Reservation Tips
    body += _section("Dining Tips &amp; Reservations",
        _prose_to_html(tips) +
        _info_card("D2M Concierge Tip",
                   "Need a hard-to-get reservation? Let us know — we have contacts "
                   "at many premier restaurants worldwide.", "tip")
    )

    return _wrap_html(
        title=f"Dining in {destination}",
        material_type="Dining Guide",
        subtitle=f"Curated culinary experiences for the discerning traveler",
        meta=f"{destination} &middot; {travel_style.title()} &middot; Dreams2Memories Travel, LLC",
        body_html=body,
    )


def generate_welcome_packet(client_name: str, booking_data: dict) -> dict:
    """Orchestrate all material types for a single booking.

    Returns dict of generated materials keyed by MaterialType value.
    Each value is the full HTML string ready for PDF rendering or email.
    """
    dest = booking_data.get("destination", "your destination")
    dates = f"{booking_data.get('start_date', 'TBD')} to {booking_data.get('end_date', 'TBD')}"
    preferences = booking_data.get("preferences", [])
    travel_style = booking_data.get("travel_style", "luxury")

    logger.info(f"Generating welcome packet: {client_name} -> {dest}")

    materials = {}

    # 1. Destination Guide
    try:
        materials[MaterialType.DESTINATION_GUIDE.value] = generate_destination_guide(
            dest, dates, preferences
        )
        logger.info("  Destination guide: OK")
    except Exception as e:
        logger.error(f"  Destination guide failed: {e}")
        materials[MaterialType.DESTINATION_GUIDE.value] = None

    # 2. Pre-Departure Packet
    try:
        materials[MaterialType.PRE_DEPARTURE.value] = generate_pre_departure(
            client_name, booking_data
        )
        logger.info("  Pre-departure packet: OK")
    except Exception as e:
        logger.error(f"  Pre-departure packet failed: {e}")
        materials[MaterialType.PRE_DEPARTURE.value] = None

    # 3. Dining Guide
    try:
        materials[MaterialType.DINING_GUIDE.value] = generate_dining_guide(
            dest, travel_style
        )
        logger.info("  Dining guide: OK")
    except Exception as e:
        logger.error(f"  Dining guide failed: {e}")
        materials[MaterialType.DINING_GUIDE.value] = None

    # Summary
    generated = sum(1 for v in materials.values() if v is not None)
    materials["_meta"] = {
        "client_name": client_name,
        "destination": dest,
        "dates": dates,
        "generated_at": datetime.now().isoformat(),
        "materials_count": generated,
        "materials_total": 3,
    }

    logger.info(f"Welcome packet complete: {generated}/3 materials generated")
    return materials


def generate_oa_supplement_email(client_name: str, oa_portal_link: str,
                                 materials: dict) -> str:
    """Generate an EXEC-voiced email to accompany the OA portal link.

    The email introduces the booking portal and the D2M supplementary
    materials — destination guide, pre-departure packet, dining guide.
    """
    meta = materials.get("_meta", {})
    dest = meta.get("destination", "your destination")
    dates = meta.get("dates", "your upcoming trip")

    # Count what we generated
    available = []
    if materials.get(MaterialType.DESTINATION_GUIDE.value):
        available.append("Destination Guide")
    if materials.get(MaterialType.PRE_DEPARTURE.value):
        available.append("Pre-Departure Packet")
    if materials.get(MaterialType.DINING_GUIDE.value):
        available.append("Dining Guide")

    materials_list = ", ".join(available) if available else "travel guides"

    # Get EXEC voice for the email
    email_body = _get_exec_narrative(
        f"Booking portal email for {client_name}",
        f"Client: {client_name}. Destination: {dest}. Dates: {dates}. "
        f"OA portal link: {oa_portal_link}. "
        f"Supplementary materials attached: {materials_list}. "
        f"Write a warm, personal email (not corporate) that: "
        f"1) Thanks them for choosing D2M, "
        f"2) Shares the booking portal link for payments/documents, "
        f"3) Introduces the attached guides as 'because travel starts before you leave home', "
        f"4) Invites them to reach out with any questions. "
        f"Sign off as John Loucks, Dreams2Memories Travel. "
        f"Keep it under 200 words."
    )

    return email_body


# ============================================================================
# PDF RENDERING (Optional — requires weasyprint)
# ============================================================================

def render_material_to_pdf(html_content: str, output_path: str) -> bool:
    """Render a material HTML string to PDF using WeasyPrint.

    Returns True on success, False on failure.
    """
    try:
        from weasyprint import HTML as WeasyprintHTML
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        WeasyprintHTML(string=html_content).write_pdf(output_path)
        logger.info(f"PDF rendered: {output_path}")
        return True
    except ImportError:
        logger.error("WeasyPrint not installed — cannot render PDF")
        return False
    except Exception as e:
        logger.error(f"PDF render failed: {e}")
        return False


def save_welcome_packet(client_name: str, materials: dict,
                        output_dir: str = None) -> dict:
    """Save all welcome packet materials as HTML and optionally PDF.

    Returns dict of saved file paths.
    """
    if output_dir is None:
        output_dir = os.path.expanduser("~/Thunderbird/output/client_materials")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    safe_name = client_name.replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    saved = {}

    for mat_type in [MaterialType.DESTINATION_GUIDE, MaterialType.PRE_DEPARTURE, MaterialType.DINING_GUIDE]:
        html = materials.get(mat_type.value)
        if not html:
            continue

        base = f"{safe_name}_{mat_type.value}_{timestamp}"
        html_path = os.path.join(output_dir, f"{base}.html")
        pdf_path = os.path.join(output_dir, f"{base}.pdf")

        # Save HTML
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Try PDF
        pdf_ok = render_material_to_pdf(html, pdf_path)

        saved[mat_type.value] = {
            "html": html_path,
            "pdf": pdf_path if pdf_ok else None,
        }

    return saved


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_client_materials_tools(mcp_server):
    """Register D2M client materials tools with the MCP server."""

    @mcp_server.tool(
        name="generate_client_materials",
        annotations={"title": "Generate D2M Client Materials", "readOnlyHint": False},
    )
    async def generate_client_materials_tool(
        client_name: str,
        destination: str,
        start_date: str,
        end_date: str,
        travel_style: str = "luxury",
        preferences: str = "",
        oa_portal_link: str = "",
        save_files: bool = True,
    ) -> str:
        """Generate supplementary D2M travel materials for a client booking.

        Creates a full welcome packet: destination guide, pre-departure packet,
        and dining guide. Optionally generates an EXEC-voiced email to accompany
        the OA portal link.

        Args:
            client_name: Client's name (e.g., 'Sarah Furlow')
            destination: Travel destination (e.g., 'Santorini, Greece')
            start_date: Trip start date (e.g., '2026-06-15')
            end_date: Trip end date (e.g., '2026-06-22')
            travel_style: Style preference: luxury, adventure, cultural, relaxation
            preferences: Comma-separated preferences (e.g., 'wine, history, beaches')
            oa_portal_link: OA My Booking Genie portal link (optional)
            save_files: Whether to save HTML/PDF files to disk
        """
        try:
            pref_list = [p.strip() for p in preferences.split(",") if p.strip()] if preferences else []

            booking_data = {
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "travel_style": travel_style,
                "preferences": pref_list,
            }

            # Generate all materials
            materials = generate_welcome_packet(client_name, booking_data)

            result = {
                "status": "success",
                "client_name": client_name,
                "destination": destination,
                "materials_generated": materials.get("_meta", {}).get("materials_count", 0),
            }

            # Save files if requested
            if save_files:
                saved = save_welcome_packet(client_name, materials)
                result["saved_files"] = saved

            # Generate supplement email if OA link provided
            if oa_portal_link:
                email = generate_oa_supplement_email(client_name, oa_portal_link, materials)
                result["supplement_email"] = email

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e), "type": "materials_error"})

    @mcp_server.tool(
        name="generate_destination_guide_tool",
        annotations={"title": "Generate Destination Guide", "readOnlyHint": False},
    )
    async def generate_destination_guide_mcp(
        destination: str,
        dates: str,
        preferences: str = "",
        save_file: bool = True,
    ) -> str:
        """Create a curated destination guide for a specific location.

        Calls A2 (Dembe) for destination intel and EXEC for narrative voice.
        Produces a branded HTML document with sections for overview, must-see,
        local dining, cultural tips, seasonal notes, and getting around.

        Args:
            destination: Destination name (e.g., 'Barcelona, Spain')
            dates: Travel dates (e.g., 'June 15-22, 2026')
            preferences: Comma-separated preferences (e.g., 'architecture, tapas, art')
            save_file: Whether to save HTML/PDF to disk
        """
        try:
            pref_list = [p.strip() for p in preferences.split(",") if p.strip()] if preferences else None

            html = generate_destination_guide(destination, dates, pref_list)

            result = {"status": "success", "destination": destination, "dates": dates}

            if save_file:
                output_dir = os.path.expanduser("~/Thunderbird/output/client_materials")
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                safe = destination.replace(" ", "_").replace(",", "").replace("/", "_")
                ts = datetime.now().strftime("%Y%m%d")
                html_path = os.path.join(output_dir, f"{safe}_destination_guide_{ts}.html")
                pdf_path = os.path.join(output_dir, f"{safe}_destination_guide_{ts}.pdf")

                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                result["html_file"] = html_path

                if render_material_to_pdf(html, pdf_path):
                    result["pdf_file"] = pdf_path

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e), "type": "guide_error"})

    logger.info("D2M Client Materials tools registered successfully")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Quick smoke test with mock data
        booking = {
            "destination": "Santorini, Greece",
            "start_date": "2026-06-15",
            "end_date": "2026-06-22",
            "travel_style": "luxury",
            "preferences": ["wine", "sunsets", "history"],
            "flights": "DEN -> ATH via FRA, Lufthansa",
            "season": "summer",
        }
        print("Generating welcome packet...")
        materials = generate_welcome_packet("Test Client", booking)
        saved = save_welcome_packet("Test_Client", materials)
        print(json.dumps(saved, indent=2, default=str))
    else:
        # Import check
        print(list(MaterialType))
        print("Materials loaded OK")
