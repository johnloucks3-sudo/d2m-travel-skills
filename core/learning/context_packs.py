"""
D2M Context Engineering — Document Context Packs
==================================================
Context Engineering principle: don't write prompts — build context packs.
Every model call for a client document loads a structured bundle of everything
the model needs to write correctly on the FIRST pass.

Four canonical doc types:
  - ProposalContext       → luxury travel proposal (extends d2m_proposal_schema)
  - ItineraryContext      → day-by-day trip narrative
  - TripValidationContext → pre-departure checklist / status document
  - EmailContext          → client communication (any tier)

Usage pattern (all types):
  1. Load dossier → extract client + booking facts
  2. Pull voice examples from config/voice_examples.json (tier-filtered)
  3. Pull learning principles from learning compiler (context-matched)
  4. Populate context pack dataclass
  5. Pass to generate_* function → model call with rich context

All currency pre-formatted via fmt_usd() before entering any pack.
Photos as base64 data URIs.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Shared Building Blocks ────────────────────────────────────────────────────

@dataclass
class ClientProfile:
    """Who is this client — everything the model needs about the relationship."""
    name: str                          # e.g., "Nancy & Ken Lyons"
    relationship_tier: str             # "friend" | "vip" | "standard" | "prospect"
    relationship_depth: str = ""       # e.g., "close friend — 15+ year relationship via Susie"
    pronouns: str = ""                 # e.g., "she/her" — for Nancy as primary contact
    communication_style: str = ""      # e.g., "warm, prefers detail, asks follow-up questions"
    special_notes: list[str] = field(default_factory=list)  # Health, preferences, sensitivities
    prior_trips: list[str] = field(default_factory=list)    # Past D2M bookings


@dataclass
class VoiceExample:
    """A real Commander email — injected to teach the model tone."""
    tier: str                          # "personal" | "client" | "vendor" | "internal"
    subject: str
    body: str
    score: int = 0                     # 1-10 authenticity score from voice harvest


@dataclass
class LearningPrinciple:
    """An extracted edit principle from the learning compiler."""
    context: str                       # e.g., "friend tier, proposal narrative"
    principle: str                     # e.g., "Use first name only; avoid formal salutations"
    direction: str                     # "soften" | "personalize" | "remove" | "tighten"
    example_before: str = ""
    example_after: str = ""


@dataclass
class BookingFact:
    """A single confirmed booking element."""
    type: str                          # "cruise" | "hotel" | "flight" | "transfer" | "excursion"
    supplier: str                      # e.g., "Regent Seven Seas", "Finnair"
    description: str                   # e.g., "Regent Grandeur — Scandinavia Aug 29–Sep 8"
    confirmation: str = ""             # Booking/PNR code
    dates: str = ""                    # Human-readable date range
    amount: str = ""                   # Pre-formatted: "$15,486"
    payment_status: str = ""           # "deposit_paid" | "final_paid" | "final_due_DATE"
    notes: str = ""                    # Seat assignments, cabin number, etc.


# ── Doc Type 1: Proposal ──────────────────────────────────────────────────────

@dataclass
class ProposalContextPack:
    """
    Everything the model needs to write a D2M luxury travel proposal.

    Wire to: templates/dani_proposal.html.j2 via templates/d2m_proposal_schema.py
    Workflow: generate .md draft → save to Drive → Telegram Commander link
              → Commander edits in Google Doc → format to PDF for client
    """
    # Who
    client: ClientProfile

    # Trip vitals
    destination: str                   # e.g., "Athens, Greece"
    travel_dates: str                  # e.g., "August 8–12, 2026"
    nights: int = 0
    guests: int = 0
    budget_per_person: str = ""        # Pre-formatted: "$4,000–$5,000"

    # Options (raw data — model writes the narrative)
    hotel_options: list[dict] = field(default_factory=list)  # name, rate, highlights, link
    excursion_options: list[dict] = field(default_factory=list)
    flight_context: str = ""           # e.g., "COS → ATH, Aug 8, ~12h with connection"

    # Pricing
    net_rates: dict = field(default_factory=dict)     # {"hotel_a": "$3,200/nt net", ...}
    target_markup: float = 0.25        # Default 25%

    # Context layers — what makes this first-pass accurate
    voice_examples: list[VoiceExample] = field(default_factory=list)   # 3-5 tier-matched
    learning_principles: list[LearningPrinciple] = field(default_factory=list)
    dossier_excerpt: str = ""          # Key facts from client dossier
    prior_proposal_notes: str = ""     # e.g., "Lyons liked the Grande Bretagne — lead with it"

    # Brand controls
    tone_directive: str = "warm, unhurried, evocative — Dani voice, not corporate"
    narrative_length: str = "medium"   # "brief" | "medium" | "full"
    draft_format: str = "md"           # "md" → Drive → Google Doc → PDF pipeline


# ── Doc Type 2: Itinerary ─────────────────────────────────────────────────────

@dataclass
class DayPlan:
    """One day in a confirmed itinerary."""
    day_number: int
    date: str                          # e.g., "Saturday, August 29"
    location: str                      # e.g., "Oslo, Norway"
    title: str                         # e.g., "Embarkation Day"
    morning: str = ""
    afternoon: str = ""
    evening: str = ""
    logistics: list[str] = field(default_factory=list)  # Transfers, pickups, times
    dining: list[str] = field(default_factory=list)     # Confirmed reservations
    notes: str = ""                    # Port info, tender status, dress code


@dataclass
class ItineraryContextPack:
    """
    Everything the model needs to write a D2M day-by-day trip narrative.

    Workflow: generate .md → Drive → Google Doc → Commander review → PDF for client
    """
    # Who
    client: ClientProfile

    # Trip structure
    trip_name: str                     # e.g., "Regent Grandeur — Scandinavia"
    total_days: int = 0
    days: list[DayPlan] = field(default_factory=list)

    # Confirmed bookings
    bookings: list[BookingFact] = field(default_factory=list)

    # Logistics block
    outbound_flight: str = ""          # PNR, airline, times
    return_flight: str = ""
    hotel_pre: str = ""                # Pre-cruise hotel if applicable
    hotel_post: str = ""
    transfers: list[str] = field(default_factory=list)
    emergency_contacts: dict = field(default_factory=dict)  # {"ship": "...", "D2M": "..."}

    # Client docs
    passport_expiry: str = ""          # e.g., "John: Dec 2029 / Nancy: Aug 2027"
    visa_status: str = ""
    insurance_policy: str = ""

    # Context layers
    voice_examples: list[VoiceExample] = field(default_factory=list)
    learning_principles: list[LearningPrinciple] = field(default_factory=list)
    narrative_style: str = "warm and anticipatory — build excitement, don't just list facts"
    draft_format: str = "md"


# ── Doc Type 3: Trip Validation ───────────────────────────────────────────────

@dataclass
class ValidationItem:
    """One item on the pre-departure checklist."""
    category: str                      # "booking" | "document" | "payment" | "logistics"
    item: str                          # e.g., "Finnair seat assignments — outbound"
    status: str                        # "confirmed" | "pending" | "action_required" | "n/a"
    details: str = ""
    deadline: str = ""                 # If action required: "by April 1"
    owner: str = "client"             # "client" | "D2M" | "supplier"


@dataclass
class TripValidationContextPack:
    """
    Everything needed for a pre-departure trip validation document.
    Surfaces gaps, confirms status, lists action items.

    Workflow: generate .md → Drive → Google Doc → client-ready PDF
    """
    # Who
    client: ClientProfile
    trip_name: str
    departure_date: str                # e.g., "August 29, 2026"
    days_until_departure: int = 0

    # All checklist items
    items: list[ValidationItem] = field(default_factory=list)

    # Booking summary
    bookings: list[BookingFact] = field(default_factory=list)

    # Financial summary
    total_invoiced: str = ""           # Pre-formatted: "$32,400"
    total_paid: str = ""
    balance_due: str = ""
    balance_due_date: str = ""

    # Action items surfaced (pre-populated by scanner)
    action_items: list[str] = field(default_factory=list)
    gaps_detected: list[str] = field(default_factory=list)

    # Context layers
    tone_directive: str = (
        "reassuring and organized — client should feel looked after, not alarmed"
    )
    draft_format: str = "md"


# ── Doc Type 4: Email ─────────────────────────────────────────────────────────

@dataclass
class EmailContextPack:
    """
    Everything the model needs to write a client email in Commander's voice.

    The most context-sensitive doc type. Voice examples are critical.
    Workflow: generate draft → Gmail draft via d2mconcierge → Telegram preview
              → Commander approves → send from concierge@d2mluxury.quest
    """
    # Who
    client: ClientProfile
    to_address: str                    # Recipient email
    from_alias: str = "concierge@d2mluxury.quest"

    # Email purpose
    occasion: str = ""                 # e.g., "final payment reminder", "seat assignment follow-up"
    subject_line: str = ""             # Draft subject — Commander may adjust
    key_facts: list[str] = field(default_factory=list)  # The facts the email must convey
    call_to_action: str = ""           # What you want the client to DO

    # Prior thread (for reply context)
    prior_thread_summary: str = ""     # 2-3 sentence summary of prior exchange
    last_contact_date: str = ""        # e.g., "March 18"

    # Context layers — MOST IMPORTANT for emails
    voice_examples: list[VoiceExample] = field(default_factory=list)  # 5+ tier-matched
    learning_principles: list[LearningPrinciple] = field(default_factory=list)
    dossier_excerpt: str = ""          # Key client context
    tone_modifiers: list[str] = field(default_factory=list)  # ["brief", "warm", "urgent but not alarming"]

    # Brand controls
    stationery: str = "d2m_standard"   # Auto-applies cream/blue/navy — never override
    sign_off: str = "Thanks"           # NEVER "Best" — Commander's standing order
    sender_name: str = "John"          # Or "Dani" for Dani-sent emails


# ── Context Pack Loader ───────────────────────────────────────────────────────

def load_voice_examples(
    tier: str,
    count: int = 5,
    voice_file: str = "/home/john/Thunderbird/config/voice_examples.json",
) -> list[VoiceExample]:
    """
    Load top-scored voice examples for a given relationship tier.
    Tiers: "personal" | "client" | "vendor" | "internal" | "family"
    """
    import json
    from pathlib import Path

    path = Path(voice_file)
    if not path.exists():
        return []

    data = json.loads(path.read_text())
    examples = [
        VoiceExample(
            tier=e["tier"],
            subject=e["subject"],
            body=e["body"],
            score=e.get("score", 0),
        )
        for e in data.get("examples", [])
        if e.get("tier") == tier
    ]
    # Sort by score descending, take top N
    examples.sort(key=lambda x: x.score, reverse=True)
    return examples[:count]


def load_learning_principles(
    context_keywords: list[str],
    principles_file: str = "/home/john/Thunderbird/config/learning_principles.json",
) -> list[LearningPrinciple]:
    """
    Load learning principles that match the given context keywords.
    Falls back to empty list if file not yet populated.
    """
    import json
    from pathlib import Path

    path = Path(principles_file)
    if not path.exists():
        return []

    data = json.loads(path.read_text())
    principles = []
    keywords_lower = [k.lower() for k in context_keywords]

    for p in data.get("principles", []):
        context_lower = p.get("context", "").lower()
        if any(kw in context_lower for kw in keywords_lower):
            principles.append(LearningPrinciple(
                context=p["context"],
                principle=p["principle"],
                direction=p.get("direction", ""),
                example_before=p.get("example_before", ""),
                example_after=p.get("example_after", ""),
            ))

    return principles


def build_system_prompt(pack) -> str:
    """
    Convert any context pack into a rich system prompt for the model.
    This is the Context Engineering → model call bridge.
    """
    lines = [
        "You are writing on behalf of Dreams2Memories Travel, LLC.",
        "The owner is John Loucks ('Yoda'), Colorado Springs, CO.",
        "",
        "== CLIENT ==",
        f"Name: {pack.client.name}",
        f"Tier: {pack.client.relationship_tier}",
    ]

    if pack.client.relationship_depth:
        lines.append(f"Relationship: {pack.client.relationship_depth}")
    if pack.client.communication_style:
        lines.append(f"Style: {pack.client.communication_style}")
    if pack.client.special_notes:
        lines.append("Notes: " + "; ".join(pack.client.special_notes))

    # Voice examples
    if hasattr(pack, "voice_examples") and pack.voice_examples:
        lines += ["", "== COMMANDER'S ACTUAL VOICE (use these as your style model) =="]
        for i, ex in enumerate(pack.voice_examples[:5], 1):
            lines += [
                f"[Example {i} — {ex.tier} tier, score {ex.score}]",
                f"Subject: {ex.subject}",
                ex.body[:400] + ("..." if len(ex.body) > 400 else ""),
                "",
            ]

    # Learning principles
    if hasattr(pack, "learning_principles") and pack.learning_principles:
        lines += ["", "== EDIT PRINCIPLES (apply before you write) =="]
        for p in pack.learning_principles:
            lines.append(f"• [{p.context}] {p.principle}")

    # Tone directive
    if hasattr(pack, "tone_directive") and pack.tone_directive:
        lines += ["", f"== TONE == {pack.tone_directive}"]

    # Brand rules
    lines += [
        "",
        "== BRAND RULES ==",
        "- Company name: Dreams2Memories Travel, LLC. NEVER 'Love Group Travel.'",
        "- Sign-off: 'Thanks' or 'Thank you'. NEVER 'Best.'",
        "- Stationery: cream paper (#f7f3ea), bright blue ink (#0000ff), Georgia serif.",
        "- Voice: warm, unhurried, confident. Never corporate. Never salesy.",
    ]

    return "\n".join(lines)
