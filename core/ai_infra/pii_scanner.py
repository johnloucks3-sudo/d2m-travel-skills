#!/usr/bin/env python3
"""
pii_scanner.py — PII Detection Before Non-Claude Dispatch
Detects email addresses, credit card numbers, and SSNs in text.
Used as a guard before sending content to external AI APIs (OpenRouter, Groq, Deepseek).

Usage:
  echo "text to scan" | python3 core/ai_infra/pii_scanner.py --detect --json
  python3 core/ai_infra/pii_scanner.py --detect --json  # reads from stdin

Exit codes:
  0 = scan complete (check JSON for detected: true/false)
  1 = error
"""
from __future__ import annotations
import json
import re
import sys


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

# Credit card: 4 groups of 4 digits, separated by space or dash
# Pattern match is sufficient — Luhn check adds false negatives (test data rarely passes)
_CC_RE = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b")

# SSN: XXX-XX-XXXX
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def scan(text: str) -> dict:
    """
    Scan text for PII. Returns dict with:
      detected (bool), types (list[str]), matches_count (int)
    """
    types = []
    matches_count = 0

    emails = _EMAIL_RE.findall(text)
    if emails:
        types.append("email")
        matches_count += len(emails)

    ccs = _CC_RE.findall(text)
    if ccs:
        types.append("credit_card")
        matches_count += len(ccs)

    ssns = _SSN_RE.findall(text)
    if ssns:
        types.append("ssn")
        matches_count += len(ssns)

    return {
        "detected": len(types) > 0,
        "types": types,
        "matches_count": matches_count,
        "scanned_chars": len(text),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PII scanner for Thunderbird Wing")
    parser.add_argument("--detect", action="store_true", help="Scan stdin for PII")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--text", help="Text to scan (alternative to stdin)")
    args = parser.parse_args()

    if not args.detect:
        parser.print_help()
        sys.exit(1)

    if args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    result = scan(text)

    if args.json:
        print(json.dumps(result))
    else:
        status = "PII DETECTED" if result["detected"] else "CLEAN"
        print(f"{status}: types={result['types']} count={result['matches_count']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
