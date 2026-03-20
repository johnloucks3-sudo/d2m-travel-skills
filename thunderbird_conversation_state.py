"""
Thunderbird Conversation State Machine
========================================

Detects the phase of a client conversation so Dani can respond
with the right tone, depth, and action. No LLM calls — keyword
and pattern-based detection.

Phases:
  GREETING       — First contact, warmth, rapport-building
  DISCOVERY      — Client exploring options, asking broad questions
  INFORMATION    — Specific detail requests (dates, prices, logistics)
  ACKNOWLEDGMENT — Client confirming receipt, saying thanks, pausing
  CLOSING        — Wrapping up, goodbye, "talk soon"
  ESCALATION     — Client frustrated, urgent, needs Commander attention
  FOLLOWUP       — Checking back on prior thread, "any update on..."

Integration:
  - Called in Dani Engine Phase 2 (Artist) before LLM prompt construction
  - Phase determines: response length, warmth level, action bias, template hints
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("thunderbird_conversation_state")


# ============================================================================
# Conversation Phases
# ============================================================================

class Phase(str, Enum):
    GREETING = "GREETING"
    DISCOVERY = "DISCOVERY"
    INFORMATION = "INFORMATION"
    ACKNOWLEDGMENT = "ACKNOWLEDGMENT"
    CLOSING = "CLOSING"
    ESCALATION = "ESCALATION"
    FOLLOWUP = "FOLLOWUP"


@dataclass
class PhaseGuidance:
    """Behavioral guidance for Dani based on detected phase."""
    phase: Phase
    tone: str              # Tone directive for LLM
    max_length: str        # short / medium / long
    action_bias: str       # describe / recommend / confirm / escalate
    template_hint: str     # Suggested response library template (if any)
    warmth: int            # 1-5 warmth scale

    def to_injection_block(self) -> str:
        """Format as LLM context injection."""
        return (
            f"CONVERSATION PHASE: {self.phase.value}\n"
            f"  Tone: {self.tone}\n"
            f"  Response length: {self.max_length}\n"
            f"  Action bias: {self.action_bias}\n"
            f"  Warmth level: {self.warmth}/5\n"
            f"  Template hint: {self.template_hint}"
        )


# ============================================================================
# Phase Definitions
# ============================================================================

PHASE_GUIDANCE = {
    Phase.GREETING: PhaseGuidance(
        phase=Phase.GREETING,
        tone="Warm, personal, relationship-first. Lead with connection, not business.",
        max_length="medium",
        action_bias="describe",
        template_hint="greeting_first_contact",
        warmth=5,
    ),
    Phase.DISCOVERY: PhaseGuidance(
        phase=Phase.DISCOVERY,
        tone="Enthusiastic, knowledgeable. Paint the picture. Inspire without overwhelming.",
        max_length="long",
        action_bias="recommend",
        template_hint="",
        warmth=4,
    ),
    Phase.INFORMATION: PhaseGuidance(
        phase=Phase.INFORMATION,
        tone="Crisp, organized, precise. Answer the question first, then elaborate if helpful.",
        max_length="medium",
        action_bias="confirm",
        template_hint="booking_status",
        warmth=3,
    ),
    Phase.ACKNOWLEDGMENT: PhaseGuidance(
        phase=Phase.ACKNOWLEDGMENT,
        tone="Brief, warm. Confirm receipt, set next expectation if applicable.",
        max_length="short",
        action_bias="confirm",
        template_hint="",
        warmth=4,
    ),
    Phase.CLOSING: PhaseGuidance(
        phase=Phase.CLOSING,
        tone="Warm farewell, leave the door open. 'We're here whenever you need us.'",
        max_length="short",
        action_bias="describe",
        template_hint="",
        warmth=5,
    ),
    Phase.ESCALATION: PhaseGuidance(
        phase=Phase.ESCALATION,
        tone="Empathetic, calm, action-oriented. Acknowledge the frustration FIRST, then solve.",
        max_length="medium",
        action_bias="escalate",
        template_hint="",
        warmth=4,
    ),
    Phase.FOLLOWUP: PhaseGuidance(
        phase=Phase.FOLLOWUP,
        tone="Proactive, organized. Provide the update, then next steps.",
        max_length="medium",
        action_bias="confirm",
        template_hint="",
        warmth=3,
    ),
}


# ============================================================================
# Detection Patterns
# ============================================================================

# Each list: (regex_pattern, weight)
# Highest total weight wins.

PHASE_PATTERNS: dict[Phase, list[tuple[str, float]]] = {
    Phase.GREETING: [
        (r"\b(?:hi|hello|hey|good\s+(?:morning|afternoon|evening))\b", 3.0),
        (r"\b(?:how\s+are\s+you|nice\s+to\s+(?:meet|hear|connect))\b", 2.0),
        (r"\b(?:reaching\s+out|first\s+time|new\s+client|referred\s+by)\b", 2.5),
        (r"\b(?:introduction|introduce\s+(?:myself|us))\b", 2.0),
        (r"\b(?:we'?re?\s+(?:interested|looking|thinking\s+about))\b", 1.5),
    ],
    Phase.DISCOVERY: [
        (r"\b(?:options?|choices?|alternatives?|suggestions?)\b", 2.0),
        (r"\b(?:what\s+(?:do\s+you|would\s+you)\s+recommend)\b", 3.0),
        (r"\b(?:tell\s+(?:me|us)\s+(?:about|more))\b", 2.0),
        (r"\b(?:compare|comparison|versus|vs\.?|or)\b", 1.5),
        (r"\b(?:what'?s?\s+(?:available|possible|the\s+best))\b", 2.0),
        (r"\b(?:thinking\s+about|considering|exploring)\b", 1.5),
        (r"\b(?:which\s+(?:cruise|ship|cabin|hotel|flight))\b", 2.5),
        (r"\b(?:where\s+should\s+we)\b", 2.0),
    ],
    Phase.INFORMATION: [
        (r"\b(?:what\s+(?:time|date|day|is\s+the))\b", 2.0),
        (r"\b(?:how\s+much|price|cost|total|balance)\b", 2.5),
        (r"\b(?:when\s+(?:is|does|do|will))\b", 2.0),
        (r"\b(?:confirm|confirmation|verify|status)\b", 2.0),
        (r"\b(?:itinerary|schedule|departure|arrival)\b", 1.5),
        (r"\b(?:details?|specifics?|exact(?:ly)?)\b", 1.5),
        (r"\b(?:what'?s?\s+(?:the|my|our)\s+(?:flight|hotel|cabin|booking))\b", 3.0),
        (r"\b(?:do\s+(?:we|I)\s+(?:have|need))\b", 1.5),
    ],
    Phase.ACKNOWLEDGMENT: [
        (r"\b(?:thanks?|thank\s+you|thx|ty)\b", 3.0),
        (r"\b(?:got\s+it|received|understood|perfect|great)\b", 2.0),
        (r"\b(?:sounds?\s+(?:good|great|perfect|wonderful))\b", 2.5),
        (r"\b(?:appreciate\s+(?:it|that|your))\b", 2.0),
        (r"\b(?:will\s+(?:review|look|check))\b", 1.5),
        (r"\b(?:noted|acknowledged?)\b", 1.5),
    ],
    Phase.CLOSING: [
        (r"\b(?:goodbye|bye|farewell|take\s+care)\b", 3.0),
        (r"\b(?:talk\s+(?:soon|later)|catch\s+up\s+(?:soon|later))\b", 2.5),
        (r"\b(?:that'?s?\s+(?:all|everything)\s+(?:for\s+now|I\s+need))\b", 2.0),
        (r"\b(?:have\s+a\s+(?:good|great|wonderful))\b", 2.0),
        (r"\b(?:until\s+(?:next\s+time|then))\b", 2.0),
    ],
    Phase.ESCALATION: [
        (r"\b(?:urgent|asap|emergency|immediately|right\s+now)\b", 3.0),
        (r"\b(?:frustrated|upset|disappointed|unhappy|concerned)\b", 2.5),
        (r"\b(?:problem|issue|wrong|mistake|error)\b", 2.0),
        (r"\b(?:need\s+to\s+(?:speak|talk)\s+(?:to|with)\s+(?:john|someone|a\s+manager))\b", 3.0),
        (r"\b(?:unacceptable|ridiculous|terrible)\b", 2.5),
        (r"\b(?:been\s+waiting|no\s+(?:response|reply|update))\b", 2.0),
        (r"!{2,}", 1.0),  # Multiple exclamation marks
    ],
    Phase.FOLLOWUP: [
        (r"\b(?:any\s+update|following\s+up|checking\s+(?:in|back))\b", 3.0),
        (r"\b(?:(?:last|previous)\s+(?:email|message|conversation))\b", 2.0),
        (r"\b(?:you\s+(?:mentioned|said|told))\b", 2.0),
        (r"\b(?:still\s+(?:waiting|pending|available))\b", 2.0),
        (r"\b(?:where\s+(?:are\s+we|do\s+(?:we|things))\s+stand)\b", 2.5),
        (r"\b(?:wanted\s+to\s+(?:check|follow|circle))\b", 2.5),
        (r"\b(?:regarding|re:|about\s+(?:the|our|my)\s+(?:booking|trip|flight))\b", 1.5),
    ],
}


# ============================================================================
# Detection Engine
# ============================================================================

def detect_phase(
    message: str,
    is_first_message: bool = False,
    prior_phase: Optional[Phase] = None,
) -> Phase:
    """Detect the conversation phase from a client message.

    Args:
        message: The client's message text
        is_first_message: True if this is the first message in conversation
        prior_phase: Previous phase (for transition logic)

    Returns:
        Detected Phase
    """
    if not message or not message.strip():
        return Phase.ACKNOWLEDGMENT

    msg_lower = message.lower().strip()

    # Score each phase
    scores: dict[Phase, float] = {phase: 0.0 for phase in Phase}

    for phase, patterns in PHASE_PATTERNS.items():
        for pattern, weight in patterns:
            matches = re.findall(pattern, msg_lower, re.IGNORECASE)
            scores[phase] += weight * len(matches)

    # First-message bonus for GREETING
    if is_first_message:
        scores[Phase.GREETING] += 2.0

    # Transition bonuses — some phases naturally follow others
    if prior_phase == Phase.GREETING:
        scores[Phase.DISCOVERY] += 1.0
    elif prior_phase == Phase.DISCOVERY:
        scores[Phase.INFORMATION] += 1.0
    elif prior_phase == Phase.INFORMATION:
        scores[Phase.ACKNOWLEDGMENT] += 0.5

    # ESCALATION always wins if scored — it's urgent
    if scores[Phase.ESCALATION] > 3.0:
        return Phase.ESCALATION

    # Find highest score
    best_phase = max(scores, key=lambda p: scores[p])

    # If no strong signal, default based on context
    if scores[best_phase] < 1.0:
        if is_first_message:
            return Phase.GREETING
        if prior_phase:
            # Continue in same phase if no clear signal
            return prior_phase
        return Phase.INFORMATION  # Safe default

    logger.debug(
        f"Phase detection: {best_phase.value} (score={scores[best_phase]:.1f}) "
        f"| scores: {', '.join(f'{p.value}={s:.1f}' for p, s in scores.items() if s > 0)}"
    )

    return best_phase


def get_guidance(phase: Phase) -> PhaseGuidance:
    """Get behavioral guidance for a detected phase."""
    return PHASE_GUIDANCE[phase]


def detect_and_guide(
    message: str,
    is_first_message: bool = False,
    prior_phase: Optional[Phase] = None,
) -> PhaseGuidance:
    """Detect phase and return guidance in one call. Main entry point."""
    phase = detect_phase(message, is_first_message, prior_phase)
    return get_guidance(phase)


# ============================================================================
# Message Length Estimator
# ============================================================================

def suggested_word_count(phase: Phase) -> tuple[int, int]:
    """Return (min_words, max_words) for response based on phase."""
    length_map = {
        "short": (20, 60),
        "medium": (50, 150),
        "long": (100, 300),
    }
    guidance = PHASE_GUIDANCE[phase]
    return length_map.get(guidance.max_length, (50, 150))
