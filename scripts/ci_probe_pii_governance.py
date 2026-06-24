#!/usr/bin/env python3
"""
CI EFFICACY PROBE — PII Governance & Data Hygiene
================================================
MISSION-387: Automated PII detection before non-Claude dispatch.

Verifies that the PII scanner is installed, executable, and can actually DETECT
PII in test data (not just present/importable). Client PII protection is
client-affecting: broken = PII leakage to external APIs (OpenRouter/Groq).

Exit 0 = RAZOR_SHARP, 1 = degraded.
"""
import json
import subprocess
import sys
from pathlib import Path

SCANNER = Path("/home/john/Thunderbird/core/ai_infra/pii_scanner.py")
PYBIN = Path("/home/john/Thunderbird/.venv/bin/python3")


def fail(m):
    print(f"RED pii-governance: {m}")
    sys.exit(1)


def main():
    # 1. Scanner exists and is executable
    if not SCANNER.exists():
        fail(f"PII scanner not found at {SCANNER}")
    
    # 2. Test detection on sample data
    test_cases = [
        ("Plain text with no PII", {"has_pii": False}),
        ("Contact Amy Darrow at amy.darrow@me.com about booking", {"has_pii": True}),
        ("Payment reference: 4532-1111-2222-3333", {"has_pii": True}),
        ("Order #78901234 shipped", {"has_pii": False}),
    ]
    
    detected = 0
    for text, expected in test_cases:
        try:
            r = subprocess.run(
                [str(PYBIN), str(SCANNER), "--detect", "--json"],
                input=text,
                capture_output=True,
                text=True,
                timeout=10
            )
            if r.returncode != 0:
                fail(f"scanner failed on test: {r.stderr[:200]}")
            
            result = json.loads(r.stdout)
            has_pii = result.get("detected", False)
            
            if has_pii == expected.get("has_pii"):
                detected += 1
        except json.JSONDecodeError:
            fail(f"scanner output not JSON: {r.stdout[:200]}")
        except subprocess.TimeoutExpired:
            fail("scanner timeout (>10s)")
        except Exception as e:
            fail(f"scanner error: {e}")
    
    if detected < len(test_cases):
        fail(f"PII detection accuracy {detected}/{len(test_cases)} (expected 100%)")
    
    print(f"RAZOR_SHARP pii-governance: scanner operational, {len(test_cases)}/{len(test_cases)} detection tests pass")
    sys.exit(0)


if __name__ == "__main__":
    main()
