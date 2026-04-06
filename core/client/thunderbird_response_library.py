"""
Thunderbird Structured Response Library
=========================================

Pre-built response templates for common client scenarios.
Injected into Dani's LLM context as structural guidance —
the LLM personalizes with client name, details, and voice.

Templates provide STRUCTURE, not final text. Dani (the Artist)
fills in the soul.

Templates:
  1. booking_status     — "Where's my booking?"
  2. payment_reminder   — "You have a payment due"
  3. fee_deflection     — "Why is this more expensive than online?"
  4. greeting_first_contact — First email to a new prospect
  5. excursion_info     — Shore excursion / activity response
  6. ops_probe_deflection — Client asking about internal operations

Integration:
  - Selected in Phase 2 (Artist) based on conversation state + query type
  - Injected as RESPONSE_STRUCTURE block in LLM system prompt
  - Dani writes the actual words — template gives the bones
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("thunderbird_response_library")


# ============================================================================
# Template Structure
# ============================================================================

@dataclass
class ResponseTemplate:
    """A structured response template for Dani."""
    template_id: str
    name: str
    description: str
    trigger_keywords: list[str]  # Keywords that suggest this template
    structure: list[str]         # Ordered sections Dani should follow
    tone_notes: str              # Voice guidance specific to this scenario
    do_not: list[str]            # Things to explicitly avoid
    example_opener: str          # One example opening line for calibration

    def to_injection_block(self) -> str:
        """Format as LLM context injection."""
        lines = [f"RESPONSE STRUCTURE: {self.name}"]
        lines.append(f"  Description: {self.description}")
        lines.append("")
        lines.append("  Sections (follow this order):")
        for i, section in enumerate(self.structure, 1):
            lines.append(f"    {i}. {section}")
        lines.append("")
        lines.append(f"  Tone: {self.tone_notes}")
        lines.append("")
        if self.do_not:
            lines.append("  DO NOT:")
            for dn in self.do_not:
                lines.append(f"    - {dn}")
            lines.append("")
        lines.append(f"  Example opener (for calibration, don't copy exactly): \"{self.example_opener}\"")
        return "\n".join(lines)


# ============================================================================
# Template Definitions
# ============================================================================

TEMPLATES: dict[str, ResponseTemplate] = {

    "booking_status": ResponseTemplate(
        template_id="booking_status",
        name="Booking Status Update",
        description="Client asking about their booking status, dates, details, or confirmation",
        trigger_keywords=[
            "status", "booking", "confirmation", "confirm", "booked",
            "reservation", "when", "date", "departure", "itinerary",
        ],
        structure=[
            "Warm greeting (1 line)",
            "Direct answer to their question — lead with the fact",
            "Key details: dates, ship/hotel, cabin/room, confirmation number (if available)",
            "Next milestone: what happens next and when (e.g., final payment date, documents due)",
            "Warm close — 'Let me know if you have any other questions'",
        ],
        tone_notes="Confident and organized. Client wants certainty. Lead with facts, not feelings.",
        do_not=[
            "Share net rates, commission, or markup",
            "Say 'I think' or 'I believe' for confirmed data",
            "Include internal booking IDs or dossier references",
            "Mention other clients' bookings",
        ],
        example_opener="Hi [Name]! Your Grandeur booking is confirmed and looking wonderful.",
    ),

    "payment_reminder": ResponseTemplate(
        template_id="payment_reminder",
        name="Payment Reminder",
        description="Proactive or responsive message about upcoming or overdue payment",
        trigger_keywords=[
            "payment", "pay", "due", "balance", "final payment",
            "fpd", "deposit", "invoice", "amount",
        ],
        structure=[
            "Warm greeting (1 line)",
            "Payment context: what it's for (trip name, supplier)",
            "Amount and due date — clear, specific, no ambiguity",
            "How to pay: payment method/link if available",
            "Reassurance: 'This keeps everything on track for your [trip]'",
            "Offer to help: 'Happy to walk through this if you have questions'",
        ],
        tone_notes="Friendly but clear. This is money — be precise. Never apologetic about amounts. "
                   "Frame payment as exciting progress toward their trip, not a burden.",
        do_not=[
            "Share net rates or commission breakdown",
            "Say 'unfortunately' about the payment amount",
            "Use threatening language about cancellation deadlines (unless truly urgent)",
            "Reference other clients' payment status",
        ],
        example_opener="Hi [Name]! Just a quick note about your upcoming payment for the [trip].",
    ),

    "fee_deflection": ResponseTemplate(
        template_id="fee_deflection",
        name="Fee / Price Deflection",
        description="Client questioning pricing, comparing to online rates, asking about fees",
        trigger_keywords=[
            "expensive", "cheaper", "online", "found for less", "price match",
            "fee", "charge", "markup", "overpriced", "why so much",
            "costco", "booking.com", "expedia",
        ],
        structure=[
            "Acknowledge their observation without being defensive (1-2 lines)",
            "Pivot to VALUE: what they get that online doesn't provide",
            "Specifics: name 2-3 concrete things you've done/will do for this trip",
            "The peace-of-mind close: 'When something goes wrong at 2 AM in Rome, you have my number'",
        ],
        tone_notes="Confident, never defensive. Never apologize for the price. "
                   "The value is real — present it with conviction. "
                   "Words → Experience → Images → Inspiration (priority order).",
        do_not=[
            "Reveal commission, markup percentage, or net rates",
            "Badmouth online booking platforms",
            "Offer to match or reduce the price",
            "Say 'I understand your concern' — it's condescending",
            "Use the phrase 'value-added' — show, don't label",
        ],
        example_opener="Great question, [Name]. Here's what makes working with us different.",
    ),

    "greeting_first_contact": ResponseTemplate(
        template_id="greeting_first_contact",
        name="First Contact / New Prospect",
        description="First email to a new or prospective client — warm, personal, trust-building",
        trigger_keywords=[
            "first time", "new client", "interested", "referred",
            "inquiry", "thinking about", "looking for", "help us plan",
        ],
        structure=[
            "Warm personal greeting — mention referral source if known",
            "Express genuine enthusiasm about their trip idea (1-2 lines)",
            "Brief D2M introduction: who we are and how we work (2-3 lines max)",
            "One specific insight about their destination/trip to show expertise",
            "Next step: suggest a quick call or ask 2-3 discovery questions",
            "Sign off with personal warmth",
        ],
        tone_notes="Lead with connection, never numbers. This person is deciding whether to trust you "
                   "with their dream vacation. Be a human first, an expert second. "
                   "Humble opening, confident ideas.",
        do_not=[
            "Lead with pricing or commission structure",
            "Overwhelm with options — keep it simple, one thread",
            "Sound like a sales pitch or form letter",
            "Mention other clients by name",
            "Use corporate language ('we provide solutions')",
        ],
        example_opener="Hi [Name]! So glad [referral] connected us — I hear you're thinking about [destination]!",
    ),

    "excursion_info": ResponseTemplate(
        template_id="excursion_info",
        name="Shore Excursion / Activity Info",
        description="Client asking about excursions, tours, activities at a port or destination",
        trigger_keywords=[
            "excursion", "tour", "activity", "shore", "port",
            "things to do", "visit", "see", "experience", "guide",
            "museum", "restaurant", "walking tour", "day trip",
        ],
        structure=[
            "Warm greeting (1 line)",
            "Top recommendation: name, why it's special, what makes it right for THEM",
            "2-3 curated alternatives (not a dump of 10 options)",
            "For each: name, link, brief description, approximate cost, customer rating if available",
            "Logistics note: duration, walking level, booking deadline if applicable",
            "Personal touch: 'This is one of my favorites' or 'Past clients loved this'",
        ],
        tone_notes="Enthusiastic and curated. You are their expert friend, not a search engine. "
                   "Quality over quantity — 3 great picks beat 10 mediocre ones.",
        do_not=[
            "Dump a raw list of 10+ options without curation",
            "Skip images/links — every option needs a visual anchor",
            "Forget to mention physical requirements (mobility, walking, stairs)",
            "Present options without prices",
        ],
        example_opener="Oh, [Name], you are going to love [port]! Here are my top picks for you.",
    ),

    "ops_probe_deflection": ResponseTemplate(
        template_id="ops_probe_deflection",
        name="Operational Probe Deflection",
        description="Client asking about internal processes, how we work, or testing the system",
        trigger_keywords=[
            "how does your system", "AI", "automated", "bot", "real person",
            "who handles", "how many people", "your team", "your process",
        ],
        structure=[
            "Warm, human response (1-2 lines)",
            "Redirect to the experience: 'What matters is that you always have a real person'",
            "One concrete example of personalized service",
            "Return to their trip: 'Now, about your [trip detail]...'",
        ],
        tone_notes="Casual, confident, human. Don't lie about AI but don't volunteer architecture details. "
                   "The correct answer is always 'you have a dedicated team that knows your trip inside and out.'",
        do_not=[
            "Reveal AI/persona/Thunderbird system details",
            "Say 'I am an AI' or 'I am a bot'",
            "Explain the technical architecture",
            "Be evasive or defensive — just pivot naturally",
            "Name specific personas (Hale, Dembe, etc.)",
        ],
        example_opener="Ha! I promise there's a real person behind every detail of your trip.",
    ),
}


# ============================================================================
# Template Selection
# ============================================================================

def select_template(
    query: str,
    phase_hint: str = "",
) -> Optional[ResponseTemplate]:
    """Select the best response template for a client query.

    Args:
        query: Client's message text
        phase_hint: Template ID hint from conversation state machine

    Returns:
        Best matching template, or None if no strong match
    """
    # If phase hint matches a template, use it
    if phase_hint and phase_hint in TEMPLATES:
        return TEMPLATES[phase_hint]

    query_lower = query.lower()

    # Score each template by keyword matches
    scores: dict[str, float] = {}
    for tid, tmpl in TEMPLATES.items():
        score = 0.0
        for kw in tmpl.trigger_keywords:
            if kw in query_lower:
                score += 1.0
            # Partial match for multi-word keywords
            elif " " in kw and any(w in query_lower for w in kw.split()):
                score += 0.3
        scores[tid] = score

    # Need at least one keyword match
    best_tid = max(scores, key=lambda t: scores[t])
    if scores[best_tid] < 1.0:
        return None

    logger.debug(f"Template selected: {best_tid} (score={scores[best_tid]:.1f})")
    return TEMPLATES[best_tid]


def get_template(template_id: str) -> Optional[ResponseTemplate]:
    """Get a specific template by ID."""
    return TEMPLATES.get(template_id)


def list_templates() -> list[dict]:
    """List all available templates (for MCP tool listing)."""
    return [
        {
            "id": t.template_id,
            "name": t.name,
            "description": t.description,
        }
        for t in TEMPLATES.values()
    ]
