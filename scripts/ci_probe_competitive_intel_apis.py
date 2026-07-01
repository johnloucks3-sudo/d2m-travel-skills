#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Competitive Intelligence APIs
=================================================
MISSION-338: Perplexity + Serper for competitive monitoring.

Verifies both APIs are accessible and authenticated. These feed into Dembe
market intelligence briefs — broken APIs = blind competitive positioning.

Exit 0 = RAZOR_SHARP, 1 = degraded.
"""
import os
import sys
import subprocess
from pathlib import Path

PYBIN = Path("/home/john/Thunderbird/.venv/bin/python3")


def fail(m):
    print(f"RED competitive-intel-apis: {m}")
    sys.exit(1)


def main():
    # 1. Check Perplexity API key
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    if not perplexity_key:
        fail("PERPLEXITY_API_KEY not configured")

    # 2. Check Serper API key
    serper_key = os.environ.get("SERPER_API_KEY")
    if not serper_key:
        fail("SERPER_API_KEY not configured")

    # 3. Test Perplexity connectivity
    try:
        test_perplexity = """
import requests
try:
    r = requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers={'Authorization': f'Bearer ' + os.environ['PERPLEXITY_API_KEY']},
        json={'model': 'llama-2-7b-chat', 'messages': [{'role': 'user', 'content': 'test'}]},
        timeout=10
    )
    if r.status_code == 401:
        print('PERPLEXITY_AUTH_FAILED')
    elif r.status_code in (200, 400):
        print('PERPLEXITY_OK')
    else:
        print(f'PERPLEXITY_HTTP_{r.status_code}')
except Exception as e:
    print(f'PERPLEXITY_ERROR: {e}')
"""
        pass  # os already imported at module level
        import requests

        try:
            r = requests.post(
                'https://api.perplexity.ai/chat/completions',
                headers={'Authorization': f'Bearer {perplexity_key}'},
                json={'model': 'llama-2-7b-chat', 'messages': [{'role': 'user', 'content': 'test'}]},
                timeout=10
            )
            if r.status_code == 401:
                fail("Perplexity API authentication failed")
            elif r.status_code >= 500:
                fail(f"Perplexity API server error (HTTP {r.status_code})")
        except requests.exceptions.Timeout:
            fail("Perplexity API timeout (>10s)")
        except Exception as e:
            fail(f"Perplexity connectivity error: {e}")

    except Exception as e:
        fail(f"Perplexity test error: {e}")

    # 4. Test Serper connectivity
    try:
        import requests

        r = requests.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY': serper_key,
                'Content-Type': 'application/json'
            },
            json={'q': 'test', 'num': 1},
            timeout=10
        )
        if r.status_code == 401:
            fail("Serper API authentication failed")
        elif r.status_code >= 500:
            fail(f"Serper API server error (HTTP {r.status_code})")
    except requests.exceptions.Timeout:
        fail("Serper API timeout (>10s)")
    except Exception as e:
        fail(f"Serper connectivity error: {e}")

    print("RAZOR_SHARP competitive-intel-apis: Perplexity and Serper both authenticated and responsive")
    sys.exit(0)


if __name__ == "__main__":
    main()
