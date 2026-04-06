"""
Thunderbird Conversation Preference Learner
============================================

Regex-based preference detection from live conversation messages.
Feeds detected preferences into the Learning Compiler as directives.

Detection patterns:
  - "I prefer..."    → explicit preference statement
  - "I always..."    → habitual preference
  - "Never..."       → negative constraint
  - "Actually..."    → correction signal (Commander changing direction)
  - "Perfect"        → positive reinforcement of current approach
  - "Change..."      → explicit change request
  - "Don't..."       → prohibition
  - "Make sure..."   → emphasis on requirement
  - "From now on..." → standing order
  - "Stop..."        → cease behavior

Integration:
  - auto_capture_preferences() → thunderbird_learning.capture_directive()
  - detect_preferences() → returns structured signals for inspection
  - MCP tool: detect_conversation_preferences
"""

import logging
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Preference signal types
# ---------------------------------------------------------------------------

SIGNAL_TYPES = {
    "explicit_preference": "Commander states a direct preference",
    "habitual": "Commander describes habitual behavior or pattern",
    "prohibition": "Commander forbids a behavior or output",
    "correction": "Commander corrects or redirects current approach",
    "reinforcement": "Commander signals approval of current approach",
    "change_request": "Commander requests a change to behavior or output",
    "standing_order": "Commander issues a permanent directive",
    "emphasis": "Commander emphasizes a requirement",
}


@dataclass
class PreferenceSignal:
    """A detected preference signal from a conversation message."""
    signal_type: str
    raw_text: str
    extracted_preference: str
    confidence: float
    pattern_name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Detection patterns — compiled for performance
# ---------------------------------------------------------------------------

# Each pattern: (compiled_regex, signal_type, pattern_name, confidence, group_index)
# group_index: which regex group contains the preference content (0 = full match)

_PATTERNS = [
    # Explicit preferences
    (
        re.compile(r"(?i)\bi\s+prefer\s+(.+?)(?:\.|$)", re.DOTALL),
        "explicit_preference", "i_prefer", 0.9, 1,
    ),
    (
        re.compile(r"(?i)\bi\s+(?:like|want|need)\s+(?:it\s+)?(?:when\s+)?(.+?)(?:\.|$)", re.DOTALL),
        "explicit_preference", "i_like_when", 0.7, 1,
    ),

    # Habitual patterns
    (
        re.compile(r"(?i)\bi\s+always\s+(.+?)(?:\.|$)", re.DOTALL),
        "habitual", "i_always", 0.85, 1,
    ),
    (
        re.compile(r"(?i)\bi\s+usually\s+(.+?)(?:\.|$)", re.DOTALL),
        "habitual", "i_usually", 0.7, 1,
    ),

    # Prohibitions
    (
        re.compile(r"(?i)^never\s+(.+?)(?:\.|$)", re.MULTILINE | re.DOTALL),
        "prohibition", "never", 0.95, 1,
    ),
    (
        re.compile(r"(?i)\bdon'?t\s+(?:ever\s+)?(.+?)(?:\.|$)", re.DOTALL),
        "prohibition", "dont", 0.85, 1,
    ),
    (
        re.compile(r"(?i)^stop\s+(.+?)(?:\.|$)", re.MULTILINE | re.DOTALL),
        "prohibition", "stop", 0.9, 1,
    ),

    # Corrections
    (
        re.compile(r"(?i)^actually[,:]?\s+(.+?)(?:\.|$)", re.MULTILINE | re.DOTALL),
        "correction", "actually", 0.8, 1,
    ),
    (
        re.compile(r"(?i)\bno[,.]?\s+(?:I\s+(?:meant|mean)\s+)?(.+?)(?:\.|$)", re.DOTALL),
        "correction", "no_i_meant", 0.75, 1,
    ),
    (
        re.compile(r"(?i)\bthat'?s\s+(?:not\s+(?:right|correct|what\s+i))\s*[,.]?\s*(.+?)(?:\.|$)", re.DOTALL),
        "correction", "thats_not_right", 0.85, 1,
    ),

    # Reinforcement
    (
        re.compile(r"(?i)^(?:perfect|exactly|yes,?\s+(?:that'?s|exactly)|that'?s?\s+(?:it|right|perfect|exactly))(?:[.!]|$)"),
        "reinforcement", "perfect", 0.9, 0,
    ),
    (
        re.compile(r"(?i)^(?:love\s+(?:it|this|that)|this\s+is\s+(?:great|perfect|exactly\s+what))"),
        "reinforcement", "love_it", 0.85, 0,
    ),

    # Change requests
    (
        re.compile(r"(?i)^change\s+(.+?)(?:\.|$)", re.MULTILINE | re.DOTALL),
        "change_request", "change", 0.9, 1,
    ),
    (
        re.compile(r"(?i)\bswitch\s+(?:to|from)\s+(.+?)(?:\.|$)", re.DOTALL),
        "change_request", "switch_to", 0.85, 1,
    ),
    (
        re.compile(r"(?i)\binstead\s+(?:of\s+.+?,?\s*)?(?:use|do|try|go\s+with)\s+(.+?)(?:\.|$)", re.DOTALL),
        "change_request", "instead_use", 0.85, 1,
    ),

    # Standing orders
    (
        re.compile(r"(?i)from\s+now\s+on[,:]?\s+(.+?)(?:\.|$)", re.DOTALL),
        "standing_order", "from_now_on", 0.95, 1,
    ),
    (
        re.compile(r"(?i)going\s+forward[,:]?\s+(.+?)(?:\.|$)", re.DOTALL),
        "standing_order", "going_forward", 0.9, 1,
    ),
    (
        re.compile(r"(?i)^(?:new\s+)?(?:standing\s+)?(?:rule|order|policy)[:\s]+(.+?)(?:\.|$)", re.MULTILINE | re.DOTALL),
        "standing_order", "new_rule", 0.95, 1,
    ),

    # Emphasis
    (
        re.compile(r"(?i)make\s+sure\s+(?:(?:you|to)\s+)?(.+?)(?:\.|$)", re.DOTALL),
        "emphasis", "make_sure", 0.8, 1,
    ),
    (
        re.compile(r"(?i)(?:it'?s\s+)?(?:important|critical|essential)\s+(?:that\s+)?(.+?)(?:\.|$)", re.DOTALL),
        "emphasis", "important_that", 0.85, 1,
    ),
]


# ---------------------------------------------------------------------------
# Core detection functions
# ---------------------------------------------------------------------------

def detect_preferences(message: str) -> List[PreferenceSignal]:
    """Scan a message for preference signals.

    Returns a list of PreferenceSignal objects, sorted by confidence descending.
    Deduplicates overlapping matches by keeping the higher-confidence one.
    """
    if not message or len(message.strip()) < 4:
        return []

    signals: List[PreferenceSignal] = []
    seen_spans: List[tuple] = []

    for pattern, signal_type, pattern_name, confidence, group_idx in _PATTERNS:
        for match in pattern.finditer(message):
            span = match.span()

            # Skip if this span overlaps significantly with an existing match
            overlaps = False
            for existing_span in seen_spans:
                overlap_start = max(span[0], existing_span[0])
                overlap_end = min(span[1], existing_span[1])
                if overlap_end > overlap_start:
                    overlap_len = overlap_end - overlap_start
                    match_len = span[1] - span[0]
                    if overlap_len / match_len > 0.5:
                        overlaps = True
                        break

            if overlaps:
                continue

            raw = match.group(0).strip()
            extracted = match.group(group_idx).strip() if group_idx > 0 else raw

            # Skip very short or noisy extractions
            if len(extracted) < 3:
                continue

            signals.append(PreferenceSignal(
                signal_type=signal_type,
                raw_text=raw,
                extracted_preference=extracted,
                confidence=confidence,
                pattern_name=pattern_name,
            ))
            seen_spans.append(span)

    # Sort by confidence descending
    signals.sort(key=lambda s: s.confidence, reverse=True)
    return signals


def auto_capture_preferences(
    message: str,
    min_confidence: float = 0.8,
    context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Detect preferences and feed high-confidence ones into the learning compiler.

    Only captures signals at or above min_confidence.
    Returns list of captured signals with their correction_ids.
    """
    from thunderbird_learning import capture_directive

    signals = detect_preferences(message)
    captured = []

    for sig in signals:
        if sig.confidence < min_confidence:
            continue

        # Build context string
        ctx_parts = [f"signal_type={sig.signal_type}", f"pattern={sig.pattern_name}"]
        if context:
            ctx_parts.append(f"conversation_context={context}")

        cid = capture_directive(
            commander_text=sig.extracted_preference,
            context=" | ".join(ctx_parts),
        )

        result = sig.to_dict()
        result["correction_id"] = cid
        captured.append(result)
        logger.info(
            f"Auto-captured preference: [{sig.signal_type}] "
            f"{sig.extracted_preference[:80]}... (cid={cid})"
        )

    return captured


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_conversation_learner_tools(mcp_server):
    """Register conversation preference detection tools with the MCP server."""
    import json

    @mcp_server.tool(
        name="detect_conversation_preferences",
        annotations={"title": "Detect Conversation Preferences", "readOnlyHint": True},
    )
    async def detect_conversation_preferences_tool(
        message: str,
        auto_capture: bool = False,
        min_confidence: float = 0.8,
        context: str = "",
    ) -> str:
        """Scan a message for Commander preference signals.

        Set auto_capture=True to automatically feed high-confidence signals
        into the learning compiler as directives.
        """
        if auto_capture:
            captured = auto_capture_preferences(
                message, min_confidence=min_confidence,
                context=context or None,
            )
            return json.dumps({
                "status": "captured",
                "count": len(captured),
                "signals": captured,
            }, indent=2)
        else:
            signals = detect_preferences(message)
            return json.dumps({
                "status": "detected",
                "count": len(signals),
                "signals": [s.to_dict() for s in signals],
            }, indent=2)

    logger.info("Conversation learner tools registered (1 tool)")
