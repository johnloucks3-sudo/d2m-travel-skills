"""
Thunderbird Email Classifier
=============================
Implements Solberg-Vega's 12-class email architecture (SO-6).

Every outbound D2M email maps to exactly one class (C1-C12).
Each class has a 4-segment structure (INTRO, CONTEXT, BODY, CLOSE),
voice parameters, and fact source requirements.

Predictability scoring gates auto-send: structure (25%), voice (35%), facts (40%).

Usage:
    from thunderbird_email_classifier import classify_email, get_class_template, score_predictability

    cls = classify_email(subject, body, sender, trigger_type)
    template = get_class_template(cls.class_id)
    score = score_predictability(draft_text, cls, verified_facts)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Payment Portal — CANONICAL CONSTANT (2026-03-21)
# D2M uses the OA/TESS Client Portal for ALL credit card collection.
# portal.d2mluxury.quest is a DIFFERENT product (post-booking materials/magic link).
# NEVER direct clients to portal.d2mluxury.quest for CC submission.
# ---------------------------------------------------------------------------
OA_PAYMENT_PORTAL_INSTRUCTIONS = (
    "To submit your credit card securely, please watch for a separate email "
    "from our booking system with the subject 'Client Portal Activation.' "
    "Click the *ACTIVATE NOW* button, register your account (Passkey or "
    "one-time email code), then add your card under the secure Payments section. "
    "Your card data is encrypted — I never see the full number in plain text. "
    "Please do NOT email card numbers — the portal is the only safe method."
)

OA_PORTAL_CC_SHORT = (
    "Watch for a 'Client Portal Activation' email → click ACTIVATE NOW → "
    "add your card securely. Do NOT email card numbers."
)


# ---------------------------------------------------------------------------
# Email Classes (C1-C12)
# ---------------------------------------------------------------------------

class EmailClass(Enum):
    C1_PROSPECT_FIRST_CONTACT = "C1"
    C2_BOOKING_CONFIRMATION = "C2"
    C3_PAYMENT_REMINDER = "C3"
    C4_TRIP_UPDATE = "C4"
    C5_EXCURSION_DINING_REC = "C5"
    C6_FARE_ALERT = "C6"
    C7_POST_TRIP_FOLLOWUP = "C7"
    C8_VENDOR_COMMUNICATION = "C8"
    C9_CLIENT_BULLETIN = "C9"
    C10_RESPONSE_TO_QUESTION = "C10"
    C11_PROACTIVE_OUTREACH = "C11"
    C12_INTERNAL_STAFF = "C12"


# ---------------------------------------------------------------------------
# Segment Structure
# ---------------------------------------------------------------------------

class Segment(Enum):
    INTRO = "S1"
    CONTEXT = "S2"
    BODY = "S3"
    CLOSE = "S4"


@dataclass
class SegmentSpec:
    """Specification for one segment within a class."""
    segment: Segment
    content_guide: str
    sentence_target: str
    tone: str


@dataclass
class VoiceParams:
    """Voice parameters per class."""
    formality: int          # 1 (casual) to 5 (formal)
    personal_ref_required: bool
    personal_ref_note: str
    signoff_variant: str
    emoji_policy: str
    length_target: str
    length_words: Tuple[int, int]  # (min, max) word count
    auto_send_eligible: bool


@dataclass
class ClassTemplate:
    """Complete template specification for an email class."""
    class_id: EmailClass
    name: str
    description: str
    sender: str             # "john", "dani", "john_or_dani"
    segments: List[SegmentSpec]
    voice: VoiceParams
    fact_sources: List[str]
    template_lineage: str
    never_auto_send: bool


@dataclass
class Classification:
    """Result of classifying an email."""
    class_id: EmailClass
    confidence: float
    signals: List[str]
    sender_recommendation: str
    template: Optional[ClassTemplate] = None


# ---------------------------------------------------------------------------
# Class Templates — Full 12-class registry
# ---------------------------------------------------------------------------

_CLASS_TEMPLATES: Dict[EmailClass, ClassTemplate] = {}


def _build_templates():
    """Build the full template registry. Called once at module load."""
    global _CLASS_TEMPLATES

    _CLASS_TEMPLATES[EmailClass.C1_PROSPECT_FIRST_CONTACT] = ClassTemplate(
        class_id=EmailClass.C1_PROSPECT_FIRST_CONTACT,
        name="Prospect First Contact",
        description="The handshake. First impression — never Dani.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Personal greeting. Reference how we connected.", "1-2 sentences", "Warm, unhurried, confident"),
            SegmentSpec(Segment.CONTEXT, "Brief personal story or observation. Why D2M exists.", "2-3 sentences", "Visionary but grounded"),
            SegmentSpec(Segment.BODY, "What we can do specifically. One concrete example. Introduce Dani if appropriate.", "3-5 sentences + attachment", "Confident, never pushy"),
            SegmentSpec(Segment.CLOSE, "Soft CTA. No pitch, no obligation. Offer conversation.", "2-3 sentences", "Open door, no pressure"),
        ],
        voice=VoiceParams(3, True, "Reference how connected", "Looking forward to this one", "Never", "long", (400, 600), False),
        fact_sources=["MANUAL", "GMAIL"],
        template_lineage="T5 (Capability Showcase)",
        never_auto_send=True,
    )

    _CLASS_TEMPLATES[EmailClass.C2_BOOKING_CONFIRMATION] = ClassTemplate(
        class_id=EmailClass.C2_BOOKING_CONFIRMATION,
        name="Booking Confirmation",
        description="Confirms commitment, sets expectations, opens relationship.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Congratulations or acknowledgment. Match trip excitement.", "1 sentence", "Warm, celebratory"),
            SegmentSpec(Segment.CONTEXT, "Highlight box: booking ref, dates, ship/hotel, cabin. Hard facts only.", "structured block", "Precise, scannable"),
            SegmentSpec(Segment.BODY, "What happens next: guest profile, documents, payment schedule, portal.", "3-5 sentences + action box", "Clear, organized"),
            SegmentSpec(Segment.CLOSE, "Personal availability. 'I'm here if anything comes up.'", "1-2 sentences", "Reassuring"),
        ],
        voice=VoiceParams(3, True, "Trip excitement", "Thank you", "Never", "medium", (200, 400), False),
        fact_sources=["BOOKING", "TESS", "DOSSIER", "ANCHOR"],
        template_lineage="Tier 1 correspondence with highlight-box",
        never_auto_send=True,
    )

    _CLASS_TEMPLATES[EmailClass.C3_PAYMENT_REMINDER] = ClassTemplate(
        class_id=EmailClass.C3_PAYMENT_REMINDER,
        name="Payment Reminder",
        description="Money conversation. Personal, not automated.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Warm greeting. Personal reference. Never open with 'your payment is due.'", "1-2 sentences", "Personal first"),
            SegmentSpec(Segment.CONTEXT, "Trip context: where, when, what to look forward to. Dream before invoice.", "2-3 sentences", "Anticipatory"),
            SegmentSpec(Segment.BODY, "Payment details: amount, due date, method. CC collection: OA/TESS Client Portal ONLY (use OA_PAYMENT_PORTAL_INSTRUCTIONS constant) — NEVER portal.d2mluxury.quest. Action box.", "structured block + 2-3 sentences", "Matter-of-fact, helpful"),
            SegmentSpec(Segment.CLOSE, "'Let me know if you have any questions.' Personal sign-off.", "1-2 sentences", "Steady, available"),
        ],
        voice=VoiceParams(2, True, "Family, trip anticipation", "Thanks", "Never", "medium-long", (300, 500), False),
        fact_sources=["BOOKING", "ANCHOR", "DOSSIER", "TESS"],
        template_lineage="Tier 1 correspondence with action-box",
        never_auto_send=True,
    )

    _CLASS_TEMPLATES[EmailClass.C4_TRIP_UPDATE] = ClassTemplate(
        class_id=EmailClass.C4_TRIP_UPDATE,
        name="Trip Update / Logistics",
        description="Operational heartbeat. Itinerary changes, confirmations.",
        sender="john_or_dani",
        segments=[
            SegmentSpec(Segment.INTRO, "Quick greeting. Acknowledge thread or context.", "1 sentence", "Efficient, warm"),
            SegmentSpec(Segment.CONTEXT, "What changed and why. One sentence.", "1-2 sentences", "Direct"),
            SegmentSpec(Segment.BODY, "Updated details. Structured if multiple items. Show before/after for changes.", "2-5 sentences or structured block", "Clear, scannable"),
            SegmentSpec(Segment.CLOSE, "Confirm what's handled vs. needs their input. Sign-off.", "1-2 sentences", "Decisive"),
        ],
        voice=VoiceParams(2, False, "Optional", "Thanks", "Never", "short-medium", (100, 300), True),
        fact_sources=["BOOKING", "DOSSIER", "TESS", "GMAIL"],
        template_lineage="T3 (Operational), Tier 1",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C5_EXCURSION_DINING_REC] = ClassTemplate(
        class_id=EmailClass.C5_EXCURSION_DINING_REC,
        name="Excursion / Dining / Experience Recommendation",
        description="The reason people hire us. Curated, personal, anticipatory.",
        sender="dani",
        segments=[
            SegmentSpec(Segment.INTRO, "Personal greeting. Reference port, destination, or interest.", "1-2 sentences", "Anticipatory, warm"),
            SegmentSpec(Segment.CONTEXT, "Why this matters to them. Tie to dossier: preferences, dietary, family.", "2-3 sentences", "Knowledgeable, personal"),
            SegmentSpec(Segment.BODY, "Structured recommendation blocks. Primary + 1-2 alternatives. Name, link, logistics, pricing, why it fits.", "structured blocks", "Expert, curated"),
            SegmentSpec(Segment.CLOSE, "'For your awareness — no action needed.' Low-pressure CTA.", "2-3 sentences", "No pressure"),
        ],
        voice=VoiceParams(2, True, "Preferences, past trips", "Looking forward to connecting", "Structured markers only", "medium-long", (300, 600), True),
        fact_sources=["DOSSIER", "TEMPORAL", "ENRICH", "MANUAL"],
        template_lineage="T9 (Proactive Resource), Dani engine",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C6_FARE_ALERT] = ClassTemplate(
        class_id=EmailClass.C6_FARE_ALERT,
        name="Fare Alert / Price Change",
        description="Time-sensitive intelligence. Price drop, cabin opened, promotion.",
        sender="dani",
        segments=[
            SegmentSpec(Segment.INTRO, "Quick greeting. Signal: 'I found something worth your attention.'", "1 sentence", "Alert but not alarming"),
            SegmentSpec(Segment.CONTEXT, "What they're currently booked/interested in. Baseline.", "1-2 sentences", "Factual"),
            SegmentSpec(Segment.BODY, "The change: new price, availability, promotion. Clear was/now comparison.", "2-4 sentences or structured block", "Precise, time-aware"),
            SegmentSpec(Segment.CLOSE, "'Want me to lock this in?' Clear decision point.", "1-2 sentences", "Action-ready"),
        ],
        voice=VoiceParams(2, False, "Optional", "Thanks", "Never", "short", (100, 200), True),
        fact_sources=["BOOKING", "MANUAL", "ENRICH"],
        template_lineage="T8 (Forwarded Intel) + pricing block",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C7_POST_TRIP_FOLLOWUP] = ClassTemplate(
        class_id=EmailClass.C7_POST_TRIP_FOLLOWUP,
        name="Post-Trip Follow-up",
        description="Close of the loop. Thank you, how was it, what's next.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Welcome home. Reference a specific trip moment.", "1-2 sentences", "Warm, genuine"),
            SegmentSpec(Segment.CONTEXT, "Light reflection. Not a survey — a human check-in.", "1-2 sentences", "Conversational"),
            SegmentSpec(Segment.BODY, "'If anything stood out — good or bad.' Plant seed for next trip without selling.", "2-3 sentences", "Unhurried"),
            SegmentSpec(Segment.CLOSE, "'Looking forward to the next one.' Personal sign-off.", "1 sentence", "Forward-looking"),
        ],
        voice=VoiceParams(1, True, "Specific trip moments", "Looking forward to the next one", "Never", "short-medium", (150, 300), False),
        fact_sources=["DOSSIER", "BOOKING", "TEMPORAL", "GMAIL"],
        template_lineage="T4 (Personal) or T7 (Quick Reply)",
        never_auto_send=True,
    )

    _CLASS_TEMPLATES[EmailClass.C8_VENDOR_COMMUNICATION] = ClassTemplate(
        class_id=EmailClass.C8_VENDOR_COMMUNICATION,
        name="Vendor Communication",
        description="Supplier, tour operator, cruise line, hotel. Transactional.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Professional greeting. Context: booking ref, client name.", "1 sentence", "Professional"),
            SegmentSpec(Segment.CONTEXT, "The situation. What we need and why.", "1-3 sentences", "Direct, factual"),
            SegmentSpec(Segment.BODY, "The request or information. Specific, actionable. Bullets if multiple items.", "2-5 sentences or bullets", "Transactional, clear"),
            SegmentSpec(Segment.CLOSE, "'Thanks for sending' or 'Please confirm.' Timeline if applicable.", "1 sentence", "Efficient"),
        ],
        voice=VoiceParams(3, False, "No", "Thanks", "Never", "short", (50, 200), True),
        fact_sources=["BOOKING", "TESS", "GMAIL"],
        template_lineage="T3 (Operational)",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C9_CLIENT_BULLETIN] = ClassTemplate(
        class_id=EmailClass.C9_CLIENT_BULLETIN,
        name="Client Bulletin",
        description="One-to-many. Newsletter-adjacent but personal.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "Branded header. Personal greeting from John. Hook.", "2-3 sentences", "Inviting, not salesy"),
            SegmentSpec(Segment.CONTEXT, "Why now. Seasonal tie-in, new capability, industry development.", "2-3 sentences", "Informed, relevant"),
            SegmentSpec(Segment.BODY, "The content. Destinations, partner spotlight, capability showcase. Visual-heavy.", "variable — medium to long", "Inspiring, visual"),
            SegmentSpec(Segment.CLOSE, "Soft CTA. 'If any of this sparks an idea, let's talk.' Full signature.", "1-2 sentences", "Open door"),
        ],
        voice=VoiceParams(3, False, "No (one-to-many)", "Thanks", "Branded markers in body OK", "long", (500, 800), False),
        fact_sources=["MANUAL"],
        template_lineage="client_bulletin.html.j2",
        never_auto_send=True,
    )

    _CLASS_TEMPLATES[EmailClass.C10_RESPONSE_TO_QUESTION] = ClassTemplate(
        class_id=EmailClass.C10_RESPONSE_TO_QUESTION,
        name="Response to Client Question",
        description="Reactive. Client asked something specific. Answer it.",
        sender="dani",
        segments=[
            SegmentSpec(Segment.INTRO, "Mirror their energy. Quick question = quick greeting.", "1 sentence", "Matched"),
            SegmentSpec(Segment.CONTEXT, "Restate or acknowledge what they asked. Proves you read it.", "1 sentence (often implicit)", "Confirming"),
            SegmentSpec(Segment.BODY, "The answer. Direct. If multiple parts, number them. If uncertain, say when you'll know.", "1-5 sentences", "Direct, certain"),
            SegmentSpec(Segment.CLOSE, "'Let me know if that covers it' or 'I'll follow up with [X] by [when].'", "1 sentence", "Decisive"),
        ],
        voice=VoiceParams(2, False, "Match their energy", "Thanks", "Never", "short", (50, 200), True),
        fact_sources=["DOSSIER", "BOOKING", "GMAIL", "TEMPORAL", "ENRICH"],
        template_lineage="T7 (Quick Reply), T3, Dani freestyle",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C11_PROACTIVE_OUTREACH] = ClassTemplate(
        class_id=EmailClass.C11_PROACTIVE_OUTREACH,
        name="Proactive Outreach (Milestone / Seasonal)",
        description="Birthday. Anniversary. 'I saw this and thought of you.'",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "The occasion. 'Happy birthday,' 'I was thinking about...'", "1-2 sentences", "Genuine, personal"),
            SegmentSpec(Segment.CONTEXT, "Personal connection. What makes this relevant to them.", "1-2 sentences", "Intimate (appropriately)"),
            SegmentSpec(Segment.BODY, "Optional: gift, early access, suggestion. Or just the human touch — no ask.", "0-3 sentences", "Generous"),
            SegmentSpec(Segment.CLOSE, "Light. No CTA required. 'Hope you have a wonderful day.'", "1 sentence", "Warm"),
        ],
        voice=VoiceParams(1, True, "Always", "Varies by occasion", "Never for prospects, light for friends", "short", (50, 200), True),
        fact_sources=["DOSSIER", "TEMPORAL", "ANCHOR"],
        template_lineage="T4 (Personal), T9 (Proactive Resource)",
        never_auto_send=False,
    )

    _CLASS_TEMPLATES[EmailClass.C12_INTERNAL_STAFF] = ClassTemplate(
        class_id=EmailClass.C12_INTERNAL_STAFF,
        name="Internal Staff Communication",
        description="Commander to staff, staff to Commander. Never client-facing.",
        sender="john",
        segments=[
            SegmentSpec(Segment.INTRO, "ISSUE: One sentence.", "1 sentence", "Direct"),
            SegmentSpec(Segment.CONTEXT, "DISCUSSION: Context, analysis, cross-references.", "variable", "Substantive"),
            SegmentSpec(Segment.BODY, "OPTIONS: Numbered alternatives when applicable.", "numbered list", "Clear"),
            SegmentSpec(Segment.CLOSE, "ACTIONS: Numbered recommendations.", "numbered list", "Decisive"),
        ],
        voice=VoiceParams(4, False, "N/A", "Staff Paper signature", "N/A", "variable", (50, 2000), False),
        fact_sources=["MANUAL", "GMAIL", "BOOKING", "DOSSIER"],
        template_lineage="Staff Paper (ISSUE/DISCUSSION/OPTIONS/ACTIONS)",
        never_auto_send=False,
    )


_build_templates()


# ---------------------------------------------------------------------------
# Classification Engine
# ---------------------------------------------------------------------------

_CLASS_SIGNALS: Dict[EmailClass, List[Tuple[str, float]]] = {
    EmailClass.C1_PROSPECT_FIRST_CONTACT: [
        (r"(?:new\s+)?(?:inquiry|prospect|lead|interested|first\s+contact)", 0.7),
        (r"(?:heard\s+about|referred|recommendation|found\s+(?:you|us))", 0.6),
    ],
    EmailClass.C2_BOOKING_CONFIRMATION: [
        (r"(?:booking|reservation)\s+(?:confirm|created|placed|secured)", 0.8),
        (r"(?:welcome\s+aboard|congratulations.*book|booked)", 0.7),
        (r"(?:confirmation\s+number|booking\s+ref)", 0.6),
    ],
    EmailClass.C3_PAYMENT_REMINDER: [
        (r"(?:final\s+)?payment\s+(?:due|remind|deadline|approaching|overdue)", 0.9),
        (r"(?:balance\s+due|deposit\s+due|FPD)", 0.8),
        (r"(?:amount\s+(?:due|owing|remaining))", 0.7),
    ],
    EmailClass.C4_TRIP_UPDATE: [
        (r"(?:itinerary|schedule|transfer|flight)\s+(?:update|change|confirm)", 0.8),
        (r"(?:update\s+on|change\s+to|revised|modified)\s+(?:your|the)\s+(?:trip|booking|itinerary)", 0.7),
        (r"(?:logistics|document\s+request|passport|visa)", 0.6),
    ],
    EmailClass.C5_EXCURSION_DINING_REC: [
        (r"(?:excursion|dining|restaurant|experience|port\s+(?:of\s+call|day))", 0.7),
        (r"(?:recommend|suggestion|curated|option)\s+(?:for|at|in)", 0.6),
        (r"(?:shore\s+excursion|wine\s+tasting|private\s+tour|cooking\s+class)", 0.7),
    ],
    EmailClass.C6_FARE_ALERT: [
        (r"(?:fare|price|rate)\s+(?:drop|change|alert|decrease|increase)", 0.9),
        (r"(?:promotion|sale|offer|discount|special)\s+(?:on|for|available)", 0.7),
        (r"(?:cabin\s+opened|upgrade\s+available|new\s+availability)", 0.7),
    ],
    EmailClass.C7_POST_TRIP_FOLLOWUP: [
        (r"(?:welcome\s+(?:home|back)|how\s+was|after\s+(?:your|the)\s+trip)", 0.8),
        (r"(?:post.?trip|follow.?up|debrie)", 0.7),
    ],
    EmailClass.C8_VENDOR_COMMUNICATION: [
        (r"(?:supplier|vendor|cruise\s+line|hotel|tour\s+operator)", 0.6),
        (r"(?:please\s+confirm|invoice|contract|commission|net\s+rate)", 0.7),
    ],
    EmailClass.C9_CLIENT_BULLETIN: [
        (r"(?:bulletin|newsletter|update\s+from|new\s+at\s+D2M)", 0.9),
        (r"(?:seasonal|quarterly|monthly)\s+(?:update|roundup|digest)", 0.7),
    ],
    EmailClass.C10_RESPONSE_TO_QUESTION: [
        (r"(?:re:|RE:|\bresponse\b|\breply\b|\banswer\b)", 0.4),
        (r"(?:you\s+asked|regarding\s+your\s+question|to\s+answer)", 0.7),
    ],
    EmailClass.C11_PROACTIVE_OUTREACH: [
        (r"(?:happy\s+birthday|anniversary|congratulations|thinking\s+of\s+you)", 0.9),
        (r"(?:milestone|celebration|special\s+occasion)", 0.7),
    ],
    EmailClass.C12_INTERNAL_STAFF: [
        (r"(?:ISSUE:|DISCUSSION:|OPTIONS:|ACTIONS:)", 0.9),
        (r"(?:staff\s+paper|internal|commander|COS|briefing)", 0.6),
    ],
}

_TRIGGER_MAP = {
    "booking_created": EmailClass.C2_BOOKING_CONFIRMATION,
    "booking_confirmed": EmailClass.C2_BOOKING_CONFIRMATION,
    "payment_due": EmailClass.C3_PAYMENT_REMINDER,
    "payment_reminder": EmailClass.C3_PAYMENT_REMINDER,
    "fare_change": EmailClass.C6_FARE_ALERT,
    "fare_drop": EmailClass.C6_FARE_ALERT,
    "post_trip": EmailClass.C7_POST_TRIP_FOLLOWUP,
    "bulletin": EmailClass.C9_CLIENT_BULLETIN,
    "client_question": EmailClass.C10_RESPONSE_TO_QUESTION,
    "client_reply": EmailClass.C10_RESPONSE_TO_QUESTION,
    "birthday": EmailClass.C11_PROACTIVE_OUTREACH,
    "anniversary": EmailClass.C11_PROACTIVE_OUTREACH,
    "milestone": EmailClass.C11_PROACTIVE_OUTREACH,
    "internal": EmailClass.C12_INTERNAL_STAFF,
    "staff_paper": EmailClass.C12_INTERNAL_STAFF,
    "prospect": EmailClass.C1_PROSPECT_FIRST_CONTACT,
    "new_lead": EmailClass.C1_PROSPECT_FIRST_CONTACT,
    "excursion": EmailClass.C5_EXCURSION_DINING_REC,
    "dining": EmailClass.C5_EXCURSION_DINING_REC,
    "trip_update": EmailClass.C4_TRIP_UPDATE,
    "itinerary_change": EmailClass.C4_TRIP_UPDATE,
    "vendor": EmailClass.C8_VENDOR_COMMUNICATION,
}

_VENDOR_DOMAINS = {
    "rssc.com", "silversea.com", "cunard.com", "vikingcruises.com",
    "seabourn.com", "oceaniacruises.com", "ponant.com",
    "amawaterways.com", "blacklane.com", "viator.com",
}


def classify_email(
    subject: str = "",
    body: str = "",
    sender: str = "",
    trigger_type: str = "",
    recipient: str = "",
) -> Classification:
    """Classify an email into one of 12 classes.

    Args:
        subject: Email subject line
        body: Email body text (first ~500 chars is sufficient)
        sender: Who's sending (john, dani, system)
        trigger_type: What triggered this email
        recipient: Email recipient (helps distinguish vendor vs client)

    Returns:
        Classification with class_id, confidence, signals, and template.
    """
    combined = f"{subject} {body[:500]} {trigger_type}".lower()
    scores: Dict[EmailClass, float] = {}
    signal_log: Dict[EmailClass, List[str]] = {}

    for cls, patterns in _CLASS_SIGNALS.items():
        total = 0.0
        sigs = []
        for pattern, weight in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                total += weight
                sigs.append(f"matched: {pattern[:40]}")
        if total > 0:
            scores[cls] = total
            signal_log[cls] = sigs

    # Trigger type overrides
    if trigger_type.lower() in _TRIGGER_MAP:
        override = _TRIGGER_MAP[trigger_type.lower()]
        scores[override] = scores.get(override, 0) + 2.0
        signal_log.setdefault(override, []).append(f"trigger={trigger_type}")

    # Vendor detection by recipient domain
    if recipient and "@" in recipient:
        r_domain = recipient.split("@")[-1].lower()
        if any(vd in r_domain for vd in _VENDOR_DOMAINS):
            scores[EmailClass.C8_VENDOR_COMMUNICATION] = scores.get(EmailClass.C8_VENDOR_COMMUNICATION, 0) + 1.5
            signal_log.setdefault(EmailClass.C8_VENDOR_COMMUNICATION, []).append(f"vendor_domain={r_domain}")

    if not scores:
        best = EmailClass.C10_RESPONSE_TO_QUESTION
        confidence = 0.3
        signals = ["no_signals — default C10"]
    else:
        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3.0, 1.0)
        signals = signal_log.get(best, [])

    template = _CLASS_TEMPLATES.get(best)
    return Classification(
        class_id=best,
        confidence=confidence,
        signals=signals,
        sender_recommendation=template.sender if template else "john",
        template=template,
    )


def get_class_template(class_id: EmailClass) -> Optional[ClassTemplate]:
    """Get the full template for a class."""
    return _CLASS_TEMPLATES.get(class_id)


def get_all_templates() -> Dict[str, ClassTemplate]:
    """Return all templates keyed by class code (C1-C12)."""
    return {cls.value: tmpl for cls, tmpl in _CLASS_TEMPLATES.items()}


# ---------------------------------------------------------------------------
# Predictability Scoring
# ---------------------------------------------------------------------------

@dataclass
class PredictabilityScore:
    """Result of scoring a draft for predictability."""
    structure_score: float   # 0-100
    voice_score: float       # 0-100
    fact_score: float        # 0-100
    composite: float         # structure(25%) + voice(35%) + facts(40%)
    auto_send_eligible: bool
    violations: List[str]
    segment_coverage: Dict[str, bool]


_FORBIDDEN_WORDS = [
    "automated", "system", "alert", "update", "platform", "portal",
    "algorithm", "AI", "bot", "notification", "generate", "process",
    "template", "workflow", "pipeline", "optimize", "leverage",
    "utilize", "facilitate", "stakeholder", "scalable", "synergy",
]

_FORBIDDEN_CLOSINGS = ["best", "best regards", "warm regards", "cheers", "sincerely"]


def score_predictability(
    draft_text: str,
    classification: Classification,
    verified_facts: Optional[List[str]] = None,
    unverified_facts: Optional[List[str]] = None,
) -> PredictabilityScore:
    """Score a draft for predictability across three dimensions.

    Thresholds for auto-send:
      - Structure >= 80
      - Voice >= 85
      - Facts >= 95
      - Composite >= 85
      - Class not in never_auto_send list
    """
    template = classification.template
    violations = []
    verified_facts = verified_facts or []
    unverified_facts = unverified_facts or []

    # --- Structure (25%) ---
    structure_score = 100.0
    segment_coverage = {"S1": False, "S2": False, "S3": False, "S4": False}

    if template:
        word_count = len(draft_text.split())
        min_w, max_w = template.voice.length_words
        if word_count < min_w * 0.7:
            structure_score -= 20
            violations.append(f"Too short: {word_count}w (target {min_w}-{max_w})")
        elif word_count > max_w * 1.5:
            structure_score -= 15
            violations.append(f"Too long: {word_count}w (target {min_w}-{max_w})")

        lines = [l.strip() for l in draft_text.strip().split("\n") if l.strip()]
        if len(lines) >= 4:
            for k in segment_coverage:
                segment_coverage[k] = True
        elif len(lines) >= 2:
            segment_coverage["S1"] = True
            segment_coverage["S3"] = True
            structure_score -= 20
            violations.append("Missing segments — too few paragraphs")
        else:
            structure_score -= 40
            violations.append("Single block — no segment structure")

    # --- Voice (35%) ---
    voice_score = 100.0
    draft_lower = draft_text.lower()

    for fw in _FORBIDDEN_WORDS:
        if re.search(rf'\b{re.escape(fw)}\b', draft_lower):
            voice_score -= 5
            violations.append(f"Forbidden word: '{fw}'")

    for fc in _FORBIDDEN_CLOSINGS:
        if fc in draft_lower:
            voice_score -= 15
            violations.append(f"Forbidden closing: '{fc}'")

    if template and template.voice.personal_ref_required:
        sentences = re.split(r'[.!?]\s+', draft_text)
        has_personal = any(
            any(w[0].isupper() and len(w) > 2 and w not in ("D2M", "Dreams2Memories", "LLC", "Travel")
                for w in s.split()[1:])
            for s in sentences if len(s.split()) > 1
        )
        if not has_personal:
            voice_score -= 10
            violations.append("No personal reference (required for this class)")

    first_line = draft_text.strip().split("\n")[0] if draft_text.strip() else ""
    if first_line.startswith(("Dear ", "Hello there", "To Whom")):
        voice_score -= 20
        violations.append(f"Wrong opening: '{first_line[:30]}'")

    excl_count = draft_text.count("!")
    if excl_count > 2:
        voice_score -= 5 * (excl_count - 2)
        violations.append(f"Too many exclamation marks: {excl_count}")

    # --- Facts (40%) ---
    fact_score = 100.0
    total_facts = len(verified_facts) + len(unverified_facts)
    if total_facts > 0:
        fact_score = (len(verified_facts) / total_facts) * 100.0
        if unverified_facts:
            violations.append(f"Unverified facts ({len(unverified_facts)}): {', '.join(unverified_facts[:3])}")

    verify_tags = len(re.findall(r'\[VERIFY\]', draft_text))
    if verify_tags:
        fact_score = max(fact_score - 20 * verify_tags, 0)
        violations.append(f"{verify_tags} [VERIFY] tags — facts unconfirmed")

    # Floor at 0
    structure_score = max(structure_score, 0.0)
    voice_score = max(voice_score, 0.0)
    fact_score = max(fact_score, 0.0)

    composite = (structure_score * 0.25) + (voice_score * 0.35) + (fact_score * 0.40)

    auto_send_eligible = (
        composite >= 85.0
        and structure_score >= 80.0
        and voice_score >= 85.0
        and fact_score >= 95.0
        and not (template and template.never_auto_send)
        and verify_tags == 0
    )

    return PredictabilityScore(
        structure_score=round(structure_score, 1),
        voice_score=round(voice_score, 1),
        fact_score=round(fact_score, 1),
        composite=round(composite, 1),
        auto_send_eligible=auto_send_eligible,
        violations=violations,
        segment_coverage=segment_coverage,
    )


# ---------------------------------------------------------------------------
# Injection Block — for prompt injection into Dani/email pipeline
# ---------------------------------------------------------------------------

def format_classification_block(classification: Classification) -> str:
    """Format classification as prompt injection block."""
    tmpl = classification.template
    if not tmpl:
        return f"[EMAIL CLASS: {classification.class_id.value} — {classification.confidence:.0%}]"

    lines = [
        f"[EMAIL CLASS: {tmpl.class_id.value} — {tmpl.name}]",
        f"Confidence: {classification.confidence:.0%}",
        f"Sender: {tmpl.sender}",
        f"Formality: {tmpl.voice.formality}/5",
        f"Length: {tmpl.voice.length_target} ({tmpl.voice.length_words[0]}-{tmpl.voice.length_words[1]} words)",
        f"Sign-off: {tmpl.voice.signoff_variant}",
        "",
        "SEGMENT STRUCTURE:",
    ]
    for seg in tmpl.segments:
        lines.append(f"  {seg.segment.value} ({seg.segment.name}): {seg.content_guide}")
        lines.append(f"     Length: {seg.sentence_target} | Tone: {seg.tone}")

    if tmpl.voice.personal_ref_required:
        lines.append(f"\nPersonal reference REQUIRED: {tmpl.voice.personal_ref_note}")
    if tmpl.never_auto_send:
        lines.append("\nThis class NEVER auto-sends — Commander review required.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_email_classifier_tools(mcp):
    """Register email classifier MCP tools."""

    @mcp.tool()
    async def email_classify(
        subject: str = "",
        body: str = "",
        sender: str = "",
        trigger_type: str = "",
        recipient: str = "",
    ) -> str:
        """Classify an outbound email into one of 12 D2M classes (C1-C12).

        Returns class, confidence, sender recommendation, and segment structure.
        """
        cls = classify_email(subject, body, sender, trigger_type, recipient)
        block = format_classification_block(cls)
        return f"{block}\n\nSignals: {', '.join(cls.signals)}"

    @mcp.tool()
    async def email_score_draft(
        draft_text: str,
        class_id: str = "",
        trigger_type: str = "",
        verified_facts: str = "",
        unverified_facts: str = "",
    ) -> str:
        """Score an email draft for predictability (structure/voice/facts).

        Returns composite score and auto-send eligibility.
        """
        if class_id:
            for ec in EmailClass:
                if ec.value == class_id.upper():
                    cls = Classification(
                        class_id=ec, confidence=1.0, signals=["manual"],
                        sender_recommendation=_CLASS_TEMPLATES[ec].sender,
                        template=_CLASS_TEMPLATES.get(ec),
                    )
                    break
            else:
                cls = classify_email(body=draft_text, trigger_type=trigger_type)
        else:
            cls = classify_email(body=draft_text, trigger_type=trigger_type)

        v = [f.strip() for f in verified_facts.split(",") if f.strip()] if verified_facts else []
        u = [f.strip() for f in unverified_facts.split(",") if f.strip()] if unverified_facts else []
        score = score_predictability(draft_text, cls, v, u)

        lines = [
            f"CLASS: {cls.class_id.value} ({cls.template.name if cls.template else '?'})",
            f"STRUCTURE: {score.structure_score}/100",
            f"VOICE: {score.voice_score}/100",
            f"FACTS: {score.fact_score}/100",
            f"COMPOSITE: {score.composite}/100",
            f"AUTO-SEND: {'YES' if score.auto_send_eligible else 'NO'}",
        ]
        if score.violations:
            lines.append(f"VIOLATIONS ({len(score.violations)}):")
            for v in score.violations:
                lines.append(f"  - {v}")
        return "\n".join(lines)

    @mcp.tool()
    async def email_list_classes() -> str:
        """List all 12 D2M email classes with auto-send status."""
        lines = ["D2M EMAIL CLASSES (Solberg-Vega Architecture v1.0)", ""]
        for cls in EmailClass:
            tmpl = _CLASS_TEMPLATES[cls]
            auto = "NEVER" if tmpl.never_auto_send else "Eligible"
            lines.append(f"{cls.value}: {tmpl.name} | Sender: {tmpl.sender} | Auto-send: {auto}")
        return "\n".join(lines)

    logger.info("Email classifier tools registered: email_classify, email_score_draft, email_list_classes")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = classify_email(body=text)
        print(format_classification_block(result))
    else:
        for cls in EmailClass:
            tmpl = _CLASS_TEMPLATES[cls]
            auto = "NEVER" if tmpl.never_auto_send else "YES"
            print(f"{cls.value}: {tmpl.name} (sender={tmpl.sender}, auto={auto})")
