#!/usr/bin/env python3
"""
hale_phrase_filter.py — Banned Phrase Runtime Filter for Hale COS
Dreams2Memories Travel, LLC | Thunderbird Wing

SO 29 APR 2026: Passive/permission-seeking language erodes autonomy posture.
This module enforces the banned phrase table at runtime — any text passing through
Hale's output pipeline is checked and corrected before delivery.

Banned phrase table (from hale_cos.md Layer 2 — Autonomy Posture):

  BANNED                               REQUIRED REPLACEMENT
  "Should I...?"                    →  "Doing [X]. Reason: [phrase]."
  "Would you like me to...?"        →  "Dispatching [X]. ETA: [time]."
  "Shall I...?"                     →  "Proceeding with [X]."
  "Standing by for orders."         →  "Delivered. Queued [next 3 moves]. Briefing at [time]."
  "Awaiting confirmation before..."  →  "Proceeding. Holding only at WF-17 / financial gate."
  "MCP failed — should I try Python?"→  "MCP failed. Pivoted to Python. [Result]."

Usage:
    from core.ops.hale_phrase_filter import filter_response, check_response, audit_log_violations

    cleaned, replacements = filter_response(text)
    violations = check_response(text)
    had_violations = audit_log_violations(text, source="hale_dispatcher")
"""

import re
import sys
from pathlib import Path

# Allow running directly from any directory
_BASE = Path(__file__).resolve().parent.parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))


# ---------------------------------------------------------------------------
# 1. BANNED_PATTERNS — compiled regex, case-insensitive, partial match
# ---------------------------------------------------------------------------
# Each entry: (pattern_key, compiled_regex, replacement_template)
# Pattern is intentionally broad — catches natural variations of each phrase.

_RAW_PATTERNS = [
    (
        "should_i",
        r"\bshould\s+i\b[^?]*\?",
        "Doing [X]. Reason: [phrase].",
    ),
    (
        "would_you_like_me",
        r"\bwould\s+you\s+like\s+me\s+to\b[^?]*\?",
        "Dispatching [X]. ETA: [time].",
    ),
    (
        "shall_i",
        r"\bshall\s+i\b[^?]*\?",
        "Proceeding with [X].",
    ),
    (
        "standing_by_for_orders",
        r"\bstanding\s+by\s+for\s+(orders|instructions|direction)\b[.!]?",
        "Delivered. Queued [next 3 moves]. Briefing at [time].",
    ),
    (
        "awaiting_confirmation",
        r"\bawaiting\s+(your\s+)?confirmation\s+before\s+(proceeding|continuing|moving\s+forward)\b[.!]?",
        "Proceeding. Holding only at WF-17 / financial gate.",
    ),
    (
        "mcp_should_python",
        r"\bMCP\s+(failed|error)[^.!?]*[—\-–]\s*should\s+i\s+try\s+(python|alternate)\b[^?]*\?",
        "MCP failed. Pivoted to Python. [Result].",
    ),
]

# Compile once at import time
BANNED_PATTERNS = [
    (key, re.compile(pattern, re.IGNORECASE | re.DOTALL), replacement)
    for key, pattern, replacement in _RAW_PATTERNS
]

# Convenience dict: pattern_key -> replacement template
REPLACEMENT_TEMPLATES = {key: replacement for key, _, replacement in BANNED_PATTERNS}


# ---------------------------------------------------------------------------
# 2. filter_response — scan + replace, returns (cleaned_text, replacements_made)
# ---------------------------------------------------------------------------

def filter_response(text: str) -> tuple[str, list[str]]:
    """
    Scan text for banned phrases and replace them with the canonical template.

    Args:
        text: The response text to scan.

    Returns:
        (cleaned_text, list_of_replacements_made)
        If no violations, returns (original_text, []) — original is NOT copied.
    """
    replacements_made: list[str] = []
    cleaned = text

    for key, pattern, replacement in BANNED_PATTERNS:
        matches = list(pattern.finditer(cleaned))
        if matches:
            for m in matches:
                replacements_made.append(
                    f"[{key}] Replaced: \"{m.group(0).strip()}\" → \"{replacement}\""
                )
            cleaned = pattern.sub(replacement, cleaned)

    return cleaned, replacements_made


# ---------------------------------------------------------------------------
# 3. check_response — violations only, no modification
# ---------------------------------------------------------------------------

def check_response(text: str) -> list[str]:
    """
    Return list of violations found in text without modifying it.
    Used for audit/logging.

    Returns:
        List of violation strings. Empty list = clean.
    """
    violations: list[str] = []
    for key, pattern, _ in BANNED_PATTERNS:
        for m in pattern.finditer(text):
            violations.append(f"[{key}] \"{m.group(0).strip()}\"")
    return violations


# ---------------------------------------------------------------------------
# 4. audit_log_violations — log to hale_activity_logger, return True if found
# ---------------------------------------------------------------------------

def audit_log_violations(text: str, source: str = "") -> bool:
    """
    Check text for banned phrases and log any violations via hale_activity_logger.

    Args:
        text: The response text to audit.
        source: Caller identifier for the log entry.

    Returns:
        True if violations were found and logged, False if clean.
    """
    violations = check_response(text)
    if not violations:
        return False

    try:
        from core.ops.hale_activity_logger import log_event
        log_event(
            "ERROR",
            "Banned phrase violation detected",
            detail=f"{len(violations)} violation(s): " + " | ".join(violations),
            source=source or "hale_phrase_filter",
            level="ERROR",
        )
    except Exception:
        pass  # Never let logging crash the caller

    return True


# ---------------------------------------------------------------------------
# 5. TEST BLOCK — 8 test cases
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import textwrap

    PASS = "\033[92mPASS\033[0m"
    FAIL = "\033[91mFAIL\033[0m"

    test_cases = [
        # (description, input_text, expect_violations: bool)
        (
            "TC-1: 'Should I..?' — basic",
            "I've reviewed the dossier. Should I send the draft to Dani now?",
            True,
        ),
        (
            "TC-2: 'Would you like me to..?' — full phrase",
            "Would you like me to pull the booking confirmation from TESS?",
            True,
        ),
        (
            "TC-3: 'Shall I..?' — with context",
            "The fare watch shows a $200 drop. Shall I trigger the alert workflow?",
            True,
        ),
        (
            "TC-4: 'Standing by for orders.' — period variant",
            "All products are staged and ready. Standing by for orders.",
            True,
        ),
        (
            "TC-5: 'Awaiting confirmation before proceeding.' — exact",
            "Draft is in Commander-Review. Awaiting confirmation before proceeding.",
            True,
        ),
        (
            "TC-6: 'MCP failed — should I try Python?' — exact",
            "Attempted to call gmail_create_draft. MCP failed — should I try Python?",
            True,
        ),
        (
            "TC-7: CLEAN — declarative autonomy posture",
            "Fare watch fired. Pivoting to Sonnet for synthesis. Brief queued for 07:00 MT.",
            False,
        ),
        (
            "TC-8: CLEAN — contains 'should' but not banned form",
            "The proposal should land well. I've staged it in Commander-Review.",
            False,
        ),
    ]

    print("=" * 70)
    print("HALE PHRASE FILTER — Test Suite (8 cases)")
    print("SO 29 APR 2026 — Banned Phrase Runtime Enforcement")
    print("=" * 70)

    passed = 0
    failed = 0

    for desc, text, expect_violations in test_cases:
        cleaned, replacements = filter_response(text)
        violations = check_response(text)
        got_violations = len(violations) > 0

        result = PASS if (got_violations == expect_violations) else FAIL
        if got_violations == expect_violations:
            passed += 1
        else:
            failed += 1

        print(f"\n{result}  {desc}")
        print(f"  INPUT:   {text}")
        if replacements:
            print(f"  CLEANED: {cleaned}")
            for r in replacements:
                print(f"  LOG:     {r}")
        else:
            print(f"  STATUS:  No violations — text unchanged.")

    print()
    print("=" * 70)
    status = PASS if failed == 0 else FAIL
    print(f"RESULT: {passed}/8 passed  {status}")
    print("=" * 70)

    # Also test audit_log_violations (dry run — logger may not be wired in test env)
    had = audit_log_violations(
        "Should I escalate this to A9 Harlan?", source="hale_phrase_filter_test"
    )
    clean_had = audit_log_violations(
        "Escalating to A9 Harlan. ETA: next cycle.", source="hale_phrase_filter_test"
    )
    print(f"\naudit_log_violations(banned text) → {had}  (expected True)")
    print(f"audit_log_violations(clean text)  → {clean_had}  (expected False)")
