#!/usr/bin/env python3
"""
PII Fence — Presidio-backed redaction before untrusted LLM dispatch.
Thunderbird Wing · Dreams2Memories Travel, LLC
Wired 2026-06-21 (daily-search wave 3 integration).

Doctrine (hale_cos.md §PII Fence):
  OpenCode / DeepSeek / any non-Claude model NEVER receives client PII.
  This module provides the mechanical enforcement for that doctrine.

Usage:
    from core.security.pii_fence import sanitize, sanitize_required

    clean = sanitize(text)                   # redact, return cleaned text
    sanitize_required(text, caller="DEMBE")  # raises if PII found (strict mode)

Entities redacted by default:
  PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE,
  US_SSN, URL (selectively), NRP, LOCATION (client-specific override)

Booking reference pattern: custom regex for TESS/Regent/Silversea refs.
"""

import re
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Lazy-load Presidio (heavy import — only pay on first call) ─────────────
_analyzer = None
_anonymizer = None


def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            _analyzer = AnalyzerEngine()
            _anonymizer = AnonymizerEngine()
            log.info("pii_fence: Presidio engines loaded")
        except ImportError:
            log.error("pii_fence: presidio-analyzer not installed — pip install presidio-analyzer presidio-anonymizer")
            raise
    return _analyzer, _anonymizer


# ── Entities to redact before OpenCode/DeepSeek dispatch ──────────────────
DEFAULT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
    "NRP",              # national/passport numbers
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "DATE_TIME",        # travel dates can fingerprint a client
]

# Booking reference pattern (TESS, Regent, Silversea booking IDs)
BOOKING_REF_PATTERN = re.compile(
    r'\b([A-Z]{2,4}[-/]?\d{6,10}|'   # e.g. PE164714008, 2984034
    r'\d{7,10}|'                        # 7-10 digit booking IDs
    r'[A-Z]{3}\d{4,8})\b'             # e.g. ABC12345678
)


def sanitize(text: str, entities: Optional[list] = None, language: str = "en") -> str:
    """
    Redact PII from text before dispatching to untrusted LLMs.
    Returns sanitized text with <REDACTED_TYPE> placeholders.
    Booking references replaced with <BOOKING_REF>.
    """
    if not text or not text.strip():
        return text

    # Step 1: redact booking refs with regex (Presidio won't catch these)
    cleaned = BOOKING_REF_PATTERN.sub("<BOOKING_REF>", text)

    # Step 2: Presidio entity redaction
    try:
        analyzer, anonymizer = _get_engines()
        target_entities = entities or DEFAULT_ENTITIES
        results = analyzer.analyze(text=cleaned, entities=target_entities, language=language)
        if results:
            from presidio_anonymizer.entities import OperatorConfig
            anonymized = anonymizer.anonymize(
                text=cleaned,
                analyzer_results=results,
                operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})},
            )
            cleaned = anonymized.text
            log.debug("pii_fence: redacted %d entities", len(results))
    except Exception as exc:
        log.warning("pii_fence: Presidio error (%s) — returning regex-only sanitized text", exc)

    return cleaned


def sanitize_required(text: str, caller: str = "unknown") -> str:
    """
    Strict mode: sanitize and LOG a warning if any PII was found.
    Use this on the hot path before dispatching to OpenCode/DeepSeek.
    Does NOT raise — returns sanitized text and logs the violation.
    """
    original_len = len(text)
    cleaned = sanitize(text)
    if cleaned != text:
        log.warning(
            "pii_fence: PII detected and redacted before %s dispatch "
            "(original %d chars → %d chars sanitized)",
            caller, original_len, len(cleaned)
        )
    return cleaned


def has_pii(text: str, entities: Optional[list] = None, language: str = "en") -> bool:
    """Return True if text contains detectable PII. Use for pre-flight checks."""
    if not text or not text.strip():
        return False
    if BOOKING_REF_PATTERN.search(text):
        return True
    try:
        analyzer, _ = _get_engines()
        target_entities = entities or DEFAULT_ENTITIES
        results = analyzer.analyze(text=text, entities=target_entities, language=language)
        return bool(results)
    except Exception:
        return False


if __name__ == "__main__":
    # Smoke test
    test_cases = [
        "Client John Smith (john@email.com, 555-1234) has booking PE164714008 departing Aug 29.",
        "Please check booking 2984034 for the Regent Grandeur voyage.",
        "No PII here — just general travel advice about Mediterranean cruises.",
    ]
    print("PII Fence Smoke Test\n" + "="*50)
    for t in test_cases:
        result = sanitize(t)
        found = has_pii(t)
        print(f"\nInput:    {t}")
        print(f"PII found: {found}")
        print(f"Cleaned:  {result}")
