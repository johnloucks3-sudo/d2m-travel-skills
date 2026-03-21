"""
Thunderbird Information Delta Tracker — Layer 2 Passive Observation
===================================================================
Analyzes edit diffs at the SEMANTIC level. Tracks not just WHAT text changed
but WHAT TYPE of information was added/removed.

Categories:
  PERSONAL_TOUCH  — names, pet names, personal references, relationship signals
  PRICING         — dollar amounts, percentages, rates, costs
  LOGISTICS       — dates, times, flights, transfers, hotels, reservations
  TONE_SHIFT      — softening, hardening, formality changes
  JARGON_REMOVAL  — industry terms replaced with plain language
  DETAIL_ADDITION — new factual content added
  DETAIL_REMOVAL  — factual content stripped
  STRUCTURE_CHANGE— paragraph breaks, reordering, formatting

Integration:
  - Called from thunderbird_dani_email.py after COS review captures a diff
  - Feeds enriched context into thunderbird_learning.py capture_email_diff
  - Exposed as MCP tool: analyze_info_delta
"""

import difflib
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enum & Dataclass
# ---------------------------------------------------------------------------

class DeltaCategory(str, Enum):
    """Semantic category of a text change."""
    PERSONAL_TOUCH = "PERSONAL_TOUCH"
    PRICING = "PRICING"
    LOGISTICS = "LOGISTICS"
    TONE_SHIFT = "TONE_SHIFT"
    JARGON_REMOVAL = "JARGON_REMOVAL"
    DETAIL_ADDITION = "DETAIL_ADDITION"
    DETAIL_REMOVAL = "DETAIL_REMOVAL"
    STRUCTURE_CHANGE = "STRUCTURE_CHANGE"


@dataclass
class InformationDelta:
    """A single semantic change detected between original and edited text."""
    category: DeltaCategory
    original_fragment: str
    edited_fragment: str
    confidence: float  # 0.0–1.0
    explanation: str
    line_range: Optional[Tuple[int, int]] = None  # approx location

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


# ---------------------------------------------------------------------------
# Pattern definitions for classification
# ---------------------------------------------------------------------------

# Dollar amounts: $1,234.56  or  USD 1234  or  €123
_RE_MONEY = re.compile(
    r'[\$€£¥]\s*[\d,]+(?:\.\d{2})?'
    r'|(?:USD|EUR|GBP)\s*[\d,]+(?:\.\d{2})?'
    r'|\d+(?:,\d{3})+(?:\.\d{2})?\s*(?:dollars|euros|per\s+person|pp|pn|per\s+night)',
    re.IGNORECASE,
)

# Percentage patterns: 25%, 16-20%
_RE_PERCENT = re.compile(r'\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%')

# Date patterns: Mar 15, 2026 / 2026-03-15 / March 15 / 15 Mar / 3/15/26
_RE_DATE = re.compile(
    r'\b(?:\d{4}-\d{2}-\d{2})'
    r'|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?)'
    r'|(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?:\s*\d{4})?)'
    r'|(?:\d{1,2}/\d{1,2}/\d{2,4})',
    re.IGNORECASE,
)

# Time patterns: 2:30 PM, 14:30, 0800
_RE_TIME = re.compile(
    r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?'
    r'|\b\d{4}\s*(?:hrs?|hours?|HRS)',
    re.IGNORECASE,
)

# Flight patterns: AA 1234, UA123, DL 456, Finnair PNR BB4X94
_RE_FLIGHT = re.compile(
    r'\b(?:AA|UA|DL|WN|AS|B6|NK|F9|HA|SY|QR|EK|BA|LH|AF|AY|IB|SK)\s*\d{1,5}\b'
    r'|(?:PNR|confirmation|conf)\s*[#:]?\s*[A-Z0-9]{5,8}',
    re.IGNORECASE,
)

# Hotel / transfer / logistics keywords
_RE_LOGISTICS_KW = re.compile(
    r'\b(?:hotel|resort|villa|suite|cabin|stateroom|transfer|pickup|shuttle'
    r'|flight|airline|airport|terminal|gate|check-?in|check-?out'
    r'|excursion|tour|reservation|itinerary|embark|disembark|port)\b',
    re.IGNORECASE,
)

# Personal name patterns (capitalized words that look like names, 2+ letters)
_RE_NAME = re.compile(
    r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Col\.?|Capt\.?)?\s*'
    r'[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,2}\b'
)

# Personal / relationship signals
_RE_PERSONAL = re.compile(
    r'\b(?:birthday|anniversary|congrat|excited\s+for\s+you|happy\s+for\s+you'
    r'|looking\s+forward|can\'t\s+wait|wonderful|special\s+occasion'
    r'|family|kids|wife|husband|daughter|son|mom|dad|grandkid'
    r'|friend|love|miss\s+you|thinking\s+of\s+you)\b',
    re.IGNORECASE,
)

# Tone markers: softening words, hedges, intensifiers
_SOFTENERS = {
    'perhaps', 'maybe', 'might', 'could', 'would suggest', 'you may want',
    'just a thought', 'no pressure', 'whenever you get a chance',
    'feel free', 'let me know', 'happy to', 'glad to', 'of course',
    'absolutely', 'certainly', 'I\'d love to', 'we\'d love to',
}
_HARDENERS = {
    'must', 'need to', 'required', 'deadline', 'immediately',
    'urgent', 'asap', 'critical', 'mandatory', 'final',
    'non-refundable', 'penalty', 'last chance', 'expires',
}

# Jargon patterns
_JARGON_TERMS = {
    'net rate', 'rack rate', 'markup', 'commission', 'GDS', 'OTA',
    'ADR', 'RevPAR', 'CLIA', 'ASTA', 'IATA', 'consortia',
    'preferred vendor', 'override', 'FAM trip', 'ship inspect',
    'amenity fee', 'port charges', 'NCF', 'OBC', 'SBC',
    'category upgrade', 'waitlist', 'guarantee', 'GTY',
    'embarkation', 'debarkation', 'tender', 'muster',
}


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _extract_diff_blocks(original: str, edited: str) -> List[Dict[str, Any]]:
    """Use difflib to extract added, removed, and changed blocks."""
    orig_lines = original.splitlines(keepends=True)
    edit_lines = edited.splitlines(keepends=True)

    sm = difflib.SequenceMatcher(None, orig_lines, edit_lines)
    blocks = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        blocks.append({
            "tag": tag,  # replace, insert, delete
            "orig": "".join(orig_lines[i1:i2]),
            "edit": "".join(edit_lines[j1:j2]),
            "orig_range": (i1, i2),
            "edit_range": (j1, j2),
        })

    return blocks


def _classify_text(text: str) -> Dict[str, float]:
    """Score a text fragment across all delta categories. Returns {category: score}."""
    scores: Dict[str, float] = {}
    text_lower = text.lower()

    # PRICING
    money_hits = len(_RE_MONEY.findall(text))
    pct_hits = len(_RE_PERCENT.findall(text))
    if money_hits or pct_hits:
        scores[DeltaCategory.PRICING.value] = min(1.0, (money_hits + pct_hits) * 0.4)

    # LOGISTICS
    date_hits = len(_RE_DATE.findall(text))
    time_hits = len(_RE_TIME.findall(text))
    flight_hits = len(_RE_FLIGHT.findall(text))
    logistics_kw = len(_RE_LOGISTICS_KW.findall(text))
    logistics_score = (date_hits * 0.25 + time_hits * 0.25 +
                       flight_hits * 0.4 + logistics_kw * 0.15)
    if logistics_score > 0:
        scores[DeltaCategory.LOGISTICS.value] = min(1.0, logistics_score)

    # PERSONAL_TOUCH
    name_hits = len(_RE_NAME.findall(text))
    personal_hits = len(_RE_PERSONAL.findall(text))
    if name_hits or personal_hits:
        scores[DeltaCategory.PERSONAL_TOUCH.value] = min(1.0, name_hits * 0.2 + personal_hits * 0.35)

    # TONE (check for softeners/hardeners)
    soft_count = sum(1 for s in _SOFTENERS if s in text_lower)
    hard_count = sum(1 for h in _HARDENERS if h in text_lower)
    if soft_count or hard_count:
        scores[DeltaCategory.TONE_SHIFT.value] = min(1.0, (soft_count + hard_count) * 0.25)

    # JARGON
    jargon_count = sum(1 for j in _JARGON_TERMS if j.lower() in text_lower)
    if jargon_count:
        scores[DeltaCategory.JARGON_REMOVAL.value] = min(1.0, jargon_count * 0.3)

    return scores


def _detect_structure_change(orig: str, edit: str) -> bool:
    """Check if the change is primarily structural (reordering, line breaks, formatting)."""
    # Normalize whitespace and compare — if content is same, it's structural
    orig_normalized = " ".join(orig.split())
    edit_normalized = " ".join(edit.split())

    if orig_normalized == edit_normalized and orig != edit:
        return True

    # Check for paragraph count changes
    orig_paras = len([p for p in orig.split("\n\n") if p.strip()])
    edit_paras = len([p for p in edit.split("\n\n") if p.strip()])
    if abs(orig_paras - edit_paras) >= 2:
        return True

    return False


def _detect_tone_direction(orig: str, edit: str) -> Optional[str]:
    """Determine if tone shifted softer or harder."""
    orig_lower, edit_lower = orig.lower(), edit.lower()
    orig_soft = sum(1 for s in _SOFTENERS if s in orig_lower)
    edit_soft = sum(1 for s in _SOFTENERS if s in edit_lower)
    orig_hard = sum(1 for h in _HARDENERS if h in orig_lower)
    edit_hard = sum(1 for h in _HARDENERS if h in edit_lower)

    softened = (edit_soft - orig_soft) - (edit_hard - orig_hard)
    if softened > 0:
        return "softened"
    elif softened < 0:
        return "hardened"
    return None


def _detect_jargon_removal(orig: str, edit: str) -> List[str]:
    """Return jargon terms that were in original but removed in edit."""
    orig_lower, edit_lower = orig.lower(), edit.lower()
    removed = []
    for term in _JARGON_TERMS:
        t = term.lower()
        if t in orig_lower and t not in edit_lower:
            removed.append(term)
    return removed


def analyze_edit_delta(original: str, edited: str) -> List[InformationDelta]:
    """Analyze the semantic differences between original and edited text.

    Uses difflib to find changed blocks, then classifies each block by category.
    Returns a list of InformationDelta objects.
    """
    if original.strip() == edited.strip():
        return []

    blocks = _extract_diff_blocks(original, edited)
    deltas: List[InformationDelta] = []

    for block in blocks:
        tag = block["tag"]
        orig_text = block["orig"]
        edit_text = block["edit"]
        line_range = block["orig_range"]

        # --- Structure change check ---
        if tag == "replace" and _detect_structure_change(orig_text, edit_text):
            deltas.append(InformationDelta(
                category=DeltaCategory.STRUCTURE_CHANGE,
                original_fragment=orig_text[:300],
                edited_fragment=edit_text[:300],
                confidence=0.85,
                explanation="Structural reorganization (paragraph breaks, reordering, formatting)",
                line_range=line_range,
            ))
            continue

        # --- Classify the changed content ---
        # For replacements, classify both sides
        if tag == "replace":
            orig_scores = _classify_text(orig_text)
            edit_scores = _classify_text(edit_text)
            combined_cats = set(orig_scores.keys()) | set(edit_scores.keys())

            # Check for jargon removal specifically
            removed_jargon = _detect_jargon_removal(orig_text, edit_text)
            if removed_jargon:
                deltas.append(InformationDelta(
                    category=DeltaCategory.JARGON_REMOVAL,
                    original_fragment=orig_text[:300],
                    edited_fragment=edit_text[:300],
                    confidence=0.9,
                    explanation=f"Jargon removed: {', '.join(removed_jargon)}",
                    line_range=line_range,
                ))

            # Check for tone shift
            tone_dir = _detect_tone_direction(orig_text, edit_text)
            if tone_dir:
                deltas.append(InformationDelta(
                    category=DeltaCategory.TONE_SHIFT,
                    original_fragment=orig_text[:300],
                    edited_fragment=edit_text[:300],
                    confidence=0.75,
                    explanation=f"Tone {tone_dir} in edit",
                    line_range=line_range,
                ))

            # Classify by dominant signal
            for cat in combined_cats:
                if cat in (DeltaCategory.TONE_SHIFT.value, DeltaCategory.JARGON_REMOVAL.value):
                    continue  # already handled above
                score = max(orig_scores.get(cat, 0), edit_scores.get(cat, 0))
                if score >= 0.2:
                    deltas.append(InformationDelta(
                        category=DeltaCategory(cat),
                        original_fragment=orig_text[:300],
                        edited_fragment=edit_text[:300],
                        confidence=score,
                        explanation=f"{cat} content modified",
                        line_range=line_range,
                    ))

            # If nothing matched, it's a generic detail change
            if not combined_cats and not removed_jargon and not tone_dir:
                deltas.append(InformationDelta(
                    category=DeltaCategory.DETAIL_ADDITION if len(edit_text) > len(orig_text)
                    else DeltaCategory.DETAIL_REMOVAL,
                    original_fragment=orig_text[:300],
                    edited_fragment=edit_text[:300],
                    confidence=0.6,
                    explanation="Text replaced without strong category signal",
                    line_range=line_range,
                ))

        elif tag == "insert":
            # New content added
            scores = _classify_text(edit_text)
            if scores:
                top_cat = max(scores, key=scores.get)
                deltas.append(InformationDelta(
                    category=DeltaCategory(top_cat),
                    original_fragment="",
                    edited_fragment=edit_text[:300],
                    confidence=scores[top_cat],
                    explanation=f"{top_cat} content added",
                    line_range=line_range,
                ))
            else:
                deltas.append(InformationDelta(
                    category=DeltaCategory.DETAIL_ADDITION,
                    original_fragment="",
                    edited_fragment=edit_text[:300],
                    confidence=0.6,
                    explanation="New content added",
                    line_range=line_range,
                ))

        elif tag == "delete":
            # Content removed
            scores = _classify_text(orig_text)
            if scores:
                top_cat = max(scores, key=scores.get)
                deltas.append(InformationDelta(
                    category=DeltaCategory(top_cat),
                    original_fragment=orig_text[:300],
                    edited_fragment="",
                    confidence=scores[top_cat],
                    explanation=f"{top_cat} content removed",
                    line_range=line_range,
                ))
            else:
                deltas.append(InformationDelta(
                    category=DeltaCategory.DETAIL_REMOVAL,
                    original_fragment=orig_text[:300],
                    edited_fragment="",
                    confidence=0.6,
                    explanation="Content removed",
                    line_range=line_range,
                ))

    return deltas


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------

def summarize_deltas(deltas: List[InformationDelta]) -> str:
    """Format a list of InformationDelta objects for the learning compiler.

    Returns a structured text block suitable for context enrichment.
    """
    if not deltas:
        return "No semantic deltas detected."

    # Group by category
    by_cat: Dict[str, List[InformationDelta]] = {}
    for d in deltas:
        by_cat.setdefault(d.category.value, []).append(d)

    lines = [f"SEMANTIC DELTA ANALYSIS — {len(deltas)} change(s) detected"]
    lines.append("=" * 55)

    for cat, items in sorted(by_cat.items()):
        avg_conf = sum(i.confidence for i in items) / len(items)
        lines.append(f"\n[{cat}] — {len(items)} instance(s), avg confidence {avg_conf:.0%}")
        for i, item in enumerate(items, 1):
            lines.append(f"  {i}. {item.explanation}")
            if item.original_fragment:
                frag = item.original_fragment.replace("\n", " ")[:120]
                lines.append(f"     ORIG: \"{frag}...\"")
            if item.edited_fragment:
                frag = item.edited_fragment.replace("\n", " ")[:120]
                lines.append(f"     EDIT: \"{frag}...\"")

    # Dominant category summary
    top_cat = max(by_cat, key=lambda c: len(by_cat[c]))
    lines.append(f"\nDOMINANT CHANGE TYPE: {top_cat} ({len(by_cat[top_cat])} instance(s))")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Feed into learning compiler
# ---------------------------------------------------------------------------

def feed_deltas_to_learning(
    deltas: List[InformationDelta],
    recipient: str,
    topic: str,
    original: str,
    edited: str,
) -> int:
    """Capture the diff in the learning compiler with enriched semantic context.

    Calls capture_email_diff from thunderbird_learning.py with the delta
    summary appended to the context field.

    Args:
        deltas: List of InformationDelta from analyze_edit_delta
        recipient: Who the email was for (client name)
        topic: Email subject / topic
        original: Full original text
        edited: Full edited text

    Returns:
        correction_id from the learning compiler (-1 if no diff)
    """
    from thunderbird_learning import capture_email_diff

    summary = summarize_deltas(deltas)

    # Build enriched context
    cat_tags = sorted(set(d.category.value for d in deltas))
    enriched_context = (
        f"COS review of reply to {recipient} re: {topic}\n"
        f"Delta categories: {', '.join(cat_tags)}\n"
        f"---\n"
        f"{summary}"
    )

    cid = capture_email_diff(
        original, edited,
        context=enriched_context,
        source="cos_review_enriched",
    )

    if cid > 0:
        logger.info(
            f"Info delta fed to learning compiler: correction #{cid}, "
            f"categories={cat_tags}, recipient={recipient}"
        )

    return cid


# ---------------------------------------------------------------------------
# Convenience: analyze + feed in one call
# ---------------------------------------------------------------------------

def analyze_and_feed(
    original: str,
    edited: str,
    recipient: str,
    topic: str,
) -> Dict[str, Any]:
    """One-shot: analyze deltas and feed to learning compiler.

    Returns dict with deltas, summary, and correction_id.
    """
    deltas = analyze_edit_delta(original, edited)
    summary = summarize_deltas(deltas)
    cid = feed_deltas_to_learning(deltas, recipient, topic, original, edited)

    return {
        "deltas": [d.to_dict() for d in deltas],
        "summary": summary,
        "correction_id": cid,
        "delta_count": len(deltas),
        "categories": sorted(set(d.category.value for d in deltas)),
    }


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_info_delta_tools(mcp_server):
    """Register information delta tools with the MCP server."""

    @mcp_server.tool(
        name="analyze_info_delta",
        annotations={"title": "Analyze Information Delta", "readOnlyHint": True},
    )
    async def analyze_info_delta_tool(
        original_text: str,
        edited_text: str,
        recipient: str = "",
        topic: str = "",
        feed_to_learning: bool = False,
    ) -> str:
        """Analyze semantic differences between original and edited text.

        Classifies changes into categories: PERSONAL_TOUCH, PRICING, LOGISTICS,
        TONE_SHIFT, JARGON_REMOVAL, DETAIL_ADDITION, DETAIL_REMOVAL, STRUCTURE_CHANGE.

        Set feed_to_learning=True to also capture the enriched diff in the learning compiler.
        """
        deltas = analyze_edit_delta(original_text, edited_text)
        summary = summarize_deltas(deltas)

        result = {
            "status": "analyzed",
            "delta_count": len(deltas),
            "categories": sorted(set(d.category.value for d in deltas)),
            "deltas": [d.to_dict() for d in deltas],
            "summary": summary,
        }

        if feed_to_learning and deltas:
            cid = feed_deltas_to_learning(
                deltas,
                recipient=recipient or "unknown",
                topic=topic or "unknown",
                original=original_text,
                edited=edited_text,
            )
            result["correction_id"] = cid
            result["fed_to_learning"] = True

        return json.dumps(result, indent=2)

    logger.info("Information delta tools registered (1 tool)")


# ---------------------------------------------------------------------------
# CLI test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    original = """\
Hi Nancy,

Thank you for reaching out! I'd love to help you with your upcoming cruise.

The net rate for the Regent Seven Seas Splendor sailing is $4,200 per person.
Your embarkation is scheduled for August 10, 2026 from Piraeus port.

I've checked the GTY category and there's availability in a Veranda Suite.
The OBC for this booking would be $500 per stateroom.

Let me know if you need anything else.

Best,
Dani"""

    edited = """\
Hi Nancy!

So excited to help with your Mediterranean adventure — this is going to be wonderful!

The Regent Seven Seas Splendor sailing is $5,250 per person, all-inclusive.
You'll board on August 10, 2026 at the Piraeus cruise terminal in Athens —
Ken mentioned you're planning dinner at the Grand Bretagne that evening, which
is a perfect way to start the trip!

I've confirmed a beautiful Veranda Suite is available for you both.
You'll also enjoy a $500 onboard credit to use however you like.

Can't wait to hear your thoughts! Let me know if you have any questions.

Thanks,
Dani"""

    deltas = analyze_edit_delta(original, edited)
    print(summarize_deltas(deltas))
    print()
    for d in deltas:
        print(f"  [{d.category.value}] conf={d.confidence:.0%} — {d.explanation}")
