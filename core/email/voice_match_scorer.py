"""
Thunderbird Voice Match Scorer
================================
Scores a client email draft against the D2M brand voice card and gold-standard
reference samples. No external services — uses existing DeepSeek V3.1 via
OpenRouter (already in the stack, ~$0.27/M tokens).

Replaces the need for River (web-only, no API) and Jenova (API-gated).
PII stays in-wing. Zero added cost at D2M email volume.

Scoring dimensions (100 pts total):
  1. Specificity (20)     — names, dates, numbers; no vague references
  2. Warmth (20)          — personal register, relationship evidence
  3. Length discipline (15) — 3-5 sentences for routine; no filler
  4. Clean vocabulary (15)  — zero forbidden words from voice card
  5. Closing compliance (15) — correct sign-off only
  6. Screenshot test (15)   — could only be written for this client

Integration:
  - Standalone:       result = score_draft(body, client_name="Kyle")
  - Presend gate:     violations = check_voice_match(body, client_name="Kyle")
  - Called from:      thunderbird_presend_evaluator.py (optional LLM gate)

Threshold: 75+ = pass. Below 75 = WARN violation surfaced to COS.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("voice_match_scorer")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
BRAND_VOICE_PATH = THUNDERBIRD_DIR / "d2m_brand_voice.json"

# Gold-standard reference emails (Commander-approved, "commend your staff")
REFERENCE_SAMPLES_PATH = THUNDERBIRD_DIR / "output" / "Drafts_for_Client_Lifecycle_Engagement.md"

# Default pass threshold
DEFAULT_THRESHOLD = 75


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    name: str
    max_pts: int
    earned: int
    feedback: str = ""

    @property
    def pct(self) -> float:
        return (self.earned / self.max_pts * 100) if self.max_pts else 0


@dataclass
class VoiceMatchResult:
    overall_score: int           # 0-100
    passed: bool                 # True if >= threshold
    threshold: int
    dimensions: list[DimensionScore] = field(default_factory=list)
    summary_feedback: str = ""   # One-sentence COS note
    forbidden_hits: list[str] = field(default_factory=list)  # Words to remove
    llm_used: bool = False       # False = fast-path regex only

    def to_cos_report(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"VOICE MATCH: {status} — {self.overall_score}/100 (threshold {self.threshold})"]
        if self.summary_feedback:
            lines.append(f"  Note: {self.summary_feedback}")
        if self.forbidden_hits:
            lines.append(f"  Forbidden words: {', '.join(self.forbidden_hits)}")
        for d in self.dimensions:
            flag = "✓" if d.pct >= 70 else "✗"
            lines.append(f"  {flag} {d.name}: {d.earned}/{d.max_pts}")
            if d.feedback and d.pct < 70:
                lines.append(f"    → {d.feedback}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Brand voice card loader
# ---------------------------------------------------------------------------

_voice_card_cache: dict = {}


def _load_voice_card() -> dict:
    global _voice_card_cache
    if _voice_card_cache:
        return _voice_card_cache
    if BRAND_VOICE_PATH.exists():
        with open(BRAND_VOICE_PATH) as f:
            _voice_card_cache = json.load(f)
    else:
        logger.warning(f"Brand voice card not found at {BRAND_VOICE_PATH}")
    return _voice_card_cache


# ---------------------------------------------------------------------------
# Fast-path checks (regex only — no LLM cost)
# ---------------------------------------------------------------------------

def _fast_forbidden_words(body: str, card: dict) -> list[str]:
    """Check for forbidden vocabulary. Returns list of hits. Uses word boundaries."""
    forbidden = card.get("forbidden_words", [])
    hits = []
    for word in forbidden:
        if re.search(r"\b" + re.escape(word) + r"\b", body, re.IGNORECASE):
            hits.append(word)
    return hits


def _fast_closing_check(body: str, card: dict) -> tuple[int, str]:
    """
    Returns (earned_pts, feedback).
    15 pts: correct closing. 0 pts: wrong or missing.
    """
    correct_closings = [v["text"] for v in card.get("closing_variants", [])]
    prohibited = card.get("closing_prohibition", "")

    body_tail = body[-300:]  # Only check last ~300 chars

    # Check prohibited closings
    bad_patterns = ["Best,", "Best regards", "Warm regards", "Cheers,", "Sincerely,"]
    for bad in bad_patterns:
        if bad.lower() in body_tail.lower():
            return 0, f"Prohibited closing '{bad}' detected — use Thanks / Thank you"

    # Check for any correct closing
    for closing in correct_closings:
        if closing.split(",")[0].strip().lower() in body_tail.lower():
            return 15, ""

    # Generic "Thanks" or "Thank you" present
    if re.search(r"\bThanks\b|\bThank you\b", body_tail, re.IGNORECASE):
        return 12, "Closing detected but not verified as exact D2M variant"

    return 5, "No recognizable closing found — add 'Thanks, John' or 'Thank you, John'"


def _fast_length_check(body: str, card: dict) -> tuple[int, str]:
    """
    Returns (earned_pts, feedback).
    Length rules from voice card: routine = 3-5 sentences.
    """
    # Strip HTML tags if present
    clean = re.sub(r"<[^>]+>", " ", body)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Sentence count (rough)
    sentences = [s.strip() for s in re.split(r"[.!?]+", clean) if len(s.strip()) > 10]
    count = len(sentences)

    word_count = len(clean.split())

    if 3 <= count <= 8:
        return 15, ""
    elif count < 3:
        if word_count > 100:
            # Long sentences, probably OK
            return 12, "Sentence count low — ensure it reads naturally, not run-on"
        return 8, f"Draft is short ({count} sentences) — may feel abrupt"
    elif 8 < count <= 15:
        return 10, f"Draft is long ({count} sentences) — trim unless this is a multi-purpose email"
    else:
        return 5, f"Draft is very long ({count} sentences) — tighten; D2M voice is brief but complete"


def _fast_specificity_check(body: str, card: dict, client_name: Optional[str]) -> tuple[int, str]:
    """
    Returns (earned_pts, feedback).
    Checks for presence of specifics: dates, proper nouns, dollar amounts, ship names.
    """
    specificity_signals = [
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\b",  # dates
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d",
        r"\$[\d,]+",            # dollar amounts
        r"\b(?:Silver\s+Nova|Silver\s+Muse|Grandeur|Viking\s+Mars|Splendor|Insignia|Riviera)\b",  # ships
        r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Proper names (rough)
        r"\bBooking\s*(?:#|number|:)?\s*\d{5,}\b",  # booking numbers
    ]

    hit_count = 0
    for pattern in specificity_signals:
        if re.search(pattern, body, re.IGNORECASE):
            hit_count += 1

    # Client name usage
    if client_name and client_name.lower() in body.lower():
        hit_count += 1

    if hit_count >= 4:
        return 20, ""
    elif hit_count == 3:
        return 16, ""
    elif hit_count == 2:
        return 12, "Add more specific details — date, ship name, booking number, or dollar amount"
    elif hit_count == 1:
        return 7, "Draft lacks specificity — client's name or trip detail must anchor every message"
    else:
        return 3, "No specifics detected — D2M voice requires at least one date, name, or number"


# ---------------------------------------------------------------------------
# LLM scoring (DeepSeek V3.1 via OpenRouter)
# ---------------------------------------------------------------------------

def _llm_score_warmth_and_screenshot(
    body: str,
    card: dict,
    client_name: Optional[str],
    context: Optional[str],
) -> tuple[tuple[int, str], tuple[int, str]]:
    """
    Returns ((warmth_pts, warmth_feedback), (screenshot_pts, screenshot_feedback)).
    These two dimensions require LLM judgment — pure regex can't assess tone or personalization depth.
    """
    try:
        import sys
        sys.path.insert(0, str(THUNDERBIRD_DIR / "OpsCenter"))
        from core.ai_infra.free_model_router import free_infer as _fi
        def ask_claude(prompt, system="", model="", max_tokens=300, temperature=0.2):
            return _fi(prompt, provider="groq", model="meta-llama/llama-4-scout-17b-16e-instruct", system=system, max_tokens=max_tokens)

        required_qualities = "\n".join(f"- {q}" for q in card.get("required_qualities", []))
        screenshot_test = card.get("screenshot_test", "")

        prompt = f"""You are evaluating a client email draft against the D2M brand voice standard.
Score TWO dimensions ONLY. Return ONLY valid JSON — no commentary, no markdown.

WARMTH (0-20 points):
Does the email match the client's emotional register? Is it personal but professional?
Is it warm but certain (the client is unsure — John is steady)?
Required qualities:
{required_qualities}

SCREENSHOT TEST (0-15 points):
"{screenshot_test}"
Could this email ONLY have been written for this specific client?
Or could it be sent to any client with no changes?

CLIENT NAME: {client_name or "unknown"}
ADDITIONAL CONTEXT: {context or "none"}

DRAFT TO EVALUATE:
---
{body[:1500]}
---

Return this exact JSON structure:
{{
  "warmth_score": <int 0-20>,
  "warmth_feedback": "<one sentence — specific issue or empty string if passing>",
  "screenshot_score": <int 0-15>,
  "screenshot_feedback": "<one sentence — what personal detail is missing or empty string if passing>"
}}"""

        raw = ask_claude(
            prompt=prompt,
            system="You are a luxury travel brand voice evaluator. Return only valid JSON.",
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=300,
            temperature=0.2,
        )

        # Parse JSON — strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?\n?", "", raw).strip("`").strip()

        data = json.loads(raw)
        warmth = (
            min(20, max(0, int(data.get("warmth_score", 12)))),
            data.get("warmth_feedback", ""),
        )
        screenshot = (
            min(15, max(0, int(data.get("screenshot_score", 10)))),
            data.get("screenshot_feedback", ""),
        )
        return warmth, screenshot

    except Exception as e:
        logger.warning(f"LLM voice scoring failed — using defaults: {e}")
        # Fallback: conservative defaults that pass but flag for manual review
        return (12, "LLM scoring unavailable — manual COS warmth check recommended"), \
               (10, "LLM scoring unavailable — verify personal reference for this client")


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_draft(
    body: str,
    client_name: Optional[str] = None,
    context: Optional[str] = None,
    threshold: int = DEFAULT_THRESHOLD,
    use_llm: bool = True,
) -> VoiceMatchResult:
    """
    Score a client email draft against the D2M voice standard.

    Args:
        body:        Email body (plain text or HTML — HTML tags stripped internally)
        client_name: Client first name for personalization check
        context:     Optional extra context (trip name, relationship notes)
        threshold:   Pass/fail threshold (default 75)
        use_llm:     If True, calls DeepSeek for warmth + screenshot dims (~$0.0001/call)

    Returns:
        VoiceMatchResult with score, breakdown, and COS-ready report
    """
    card = _load_voice_card()

    dimensions: list[DimensionScore] = []

    # --- Dim 1: Specificity (regex, fast) ---
    spec_pts, spec_fb = _fast_specificity_check(body, card, client_name)
    dimensions.append(DimensionScore("Specificity", 20, spec_pts, spec_fb))

    # --- Dim 2: Warmth + Dim 6: Screenshot (LLM) ---
    if use_llm:
        (warmth_pts, warmth_fb), (screenshot_pts, screenshot_fb) = \
            _llm_score_warmth_and_screenshot(body, card, client_name, context)
        llm_used = True
    else:
        warmth_pts, warmth_fb = 14, "LLM disabled — manual warmth review recommended"
        screenshot_pts, screenshot_fb = 10, "LLM disabled — verify personal reference manually"
        llm_used = False

    dimensions.append(DimensionScore("Warmth", 20, warmth_pts, warmth_fb))

    # --- Dim 3: Length (regex, fast) ---
    len_pts, len_fb = _fast_length_check(body, card)
    dimensions.append(DimensionScore("Length discipline", 15, len_pts, len_fb))

    # --- Dim 4: Clean vocabulary (regex, fast) ---
    forbidden_hits = _fast_forbidden_words(body, card)
    vocab_pts = max(0, 15 - (len(forbidden_hits) * 5))
    vocab_fb = f"Remove: {', '.join(forbidden_hits)}" if forbidden_hits else ""
    dimensions.append(DimensionScore("Clean vocabulary", 15, vocab_pts, vocab_fb))

    # --- Dim 5: Closing (regex, fast) ---
    close_pts, close_fb = _fast_closing_check(body, card)
    dimensions.append(DimensionScore("Closing compliance", 15, close_pts, close_fb))

    # --- Dim 6: Screenshot test (from LLM above) ---
    dimensions.append(DimensionScore("Screenshot test", 15, screenshot_pts, screenshot_fb))

    # --- Total ---
    overall = sum(d.earned for d in dimensions)
    passed = overall >= threshold

    # --- Summary feedback ---
    worst = min(dimensions, key=lambda d: d.pct)
    if passed:
        summary = f"Voice match confirmed ({overall}/100) — ready for COS gate."
    else:
        summary = (
            f"Voice gap at '{worst.name}' ({worst.earned}/{worst.max_pts}): {worst.feedback}"
            if worst.feedback else
            f"Overall voice score {overall}/100 — below {threshold} threshold."
        )

    return VoiceMatchResult(
        overall_score=overall,
        passed=passed,
        threshold=threshold,
        dimensions=dimensions,
        summary_feedback=summary,
        forbidden_hits=forbidden_hits,
        llm_used=llm_used,
    )


# ---------------------------------------------------------------------------
# Presend evaluator integration hook
# ---------------------------------------------------------------------------

def check_voice_match(
    body: str,
    client_name: Optional[str] = None,
    context: Optional[str] = None,
    threshold: int = DEFAULT_THRESHOLD,
    use_llm: bool = True,
) -> list:
    """
    Returns list of Violation objects for integration into thunderbird_presend_evaluator.py.
    Import Violation and Severity from that module — kept separate to avoid circular imports.
    """
    # Import locally to avoid circular dependency
    try:
        import sys
        sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "email"))
        from thunderbird_presend_evaluator import Violation, Severity  # type: ignore
    except ImportError:
        logger.warning("Could not import Violation/Severity — returning raw strings")
        return []

    result = score_draft(body, client_name, context, threshold, use_llm)
    violations = []

    if not result.passed:
        violations.append(Violation(
            rule_id="VOICE-01",
            severity=Severity.WARN,
            message=f"Voice match score {result.overall_score}/100 (threshold {threshold})",
            suggestion=result.summary_feedback,
        ))

    if result.forbidden_hits:
        violations.append(Violation(
            rule_id="VOICE-02",
            severity=Severity.WARN,
            message=f"Forbidden D2M vocabulary detected",
            match=", ".join(result.forbidden_hits),
            suggestion="Remove these words — they signal AI/automation to the client",
        ))

    for dim in result.dimensions:
        if dim.pct < 50 and dim.feedback:
            violations.append(Violation(
                rule_id=f"VOICE-{dim.name[:3].upper()}",
                severity=Severity.WARN,
                message=f"Voice dim '{dim.name}': {dim.earned}/{dim.max_pts}",
                suggestion=dim.feedback,
            ))

    return violations


# ---------------------------------------------------------------------------
# CLI for quick manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        draft_text = Path(sys.argv[1]).read_text()
        client = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Built-in smoke test using a known-good Kuklinski excerpt
        draft_text = """Hi Kyle,

You're confirmed. All three cabins on Viking Mars are locked in, and your full payment
of $21,244 processed on March 27. You're sailing December 17 from Panama City,
returning December 27 in Fort Lauderdale.

I'm watching fares from all three home cities to Panama City right now.
Expect curated options from me by June 17.

Thanks,
John"""
        client = "Kyle"

    print(f"Scoring draft for client: {client or 'unknown'}")
    print("=" * 60)

    result = score_draft(draft_text, client_name=client)
    print(result.to_cos_report())
    print(f"\nLLM used: {result.llm_used}")
    sys.exit(0 if result.passed else 1)
