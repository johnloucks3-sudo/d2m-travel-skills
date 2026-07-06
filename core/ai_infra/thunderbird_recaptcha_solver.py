#!/usr/bin/env python3
"""
thunderbird_recaptcha_solver.py — reCAPTCHA solving integration via 2Captcha.

Provides async/sync wrappers for automated reCAPTCHA v2/v3 solving on Regent portal.
Used in conjunction with Playwright for full portal automation (replaces manual Chrome CDP).

Usage:
    from core.ai_infra.thunderbird_recaptcha_solver import solve_recaptcha_v2
    token = await solve_recaptcha_v2("https://www.rssc.com/agent/login", api_key="...")
    await page.evaluate(f"document.querySelector('[name=\"g-recaptcha-response\"]').innerHTML = '{token}'")

2Captcha API: https://2captcha.com/2captcha-api
Cost: ~$0.0003–0.001 per solve
Accuracy: 99%
Speed: 5–15 seconds
"""

from __future__ import annotations
import asyncio
import aiohttp
import json
import time
from typing import Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse

TWOCAPTCHA_API = "http://2captcha.com"
TWOCAPTCHA_SOLVE_URL = f"{TWOCAPTCHA_API}/api/upload"
TWOCAPTCHA_STATUS_URL = f"{TWOCAPTCHA_API}/api/res"
SOLVE_TIMEOUT = 60  # seconds to wait for solve


async def solve_recaptcha_v2(
    page_url: str,
    sitekey: str,
    api_key: str,
    timeout: int = SOLVE_TIMEOUT,
    verbose: bool = False,
) -> str:
    """
    Solve reCAPTCHA v2 (checkbox or invisible) via 2Captcha API.

    Args:
        page_url: URL where reCAPTCHA is embedded (used for context)
        sitekey: reCAPTCHA site key (data-sitekey attribute)
        api_key: 2Captcha API key
        timeout: Max seconds to wait for solution
        verbose: Print polling status

    Returns:
        reCAPTCHA response token (g-recaptcha-response value)

    Raises:
        asyncio.TimeoutError: If solve exceeds timeout
        ValueError: If 2Captcha returns an error
    """
    if verbose:
        print(f"📨 Submitting reCAPTCHA v2 to 2Captcha API...")
        print(f"   Page: {page_url}")
        print(f"   Sitekey: {sitekey[:20]}...")

    async with aiohttp.ClientSession() as session:
        # Upload reCAPTCHA to 2Captcha
        payload = {
            "method": "userrecaptcha",
            "googlekey": sitekey,
            "pageurl": page_url,
            "apikey": api_key,
            "json": 1,
        }

        try:
            async with session.post(TWOCAPTCHA_SOLVE_URL, data=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise ValueError(f"2Captcha upload failed: HTTP {resp.status}")
                result = await resp.json()

                if result.get("is_correct") == False or "error_text" in result:
                    raise ValueError(f"2Captcha error: {result.get('error_text', 'Unknown error')}")

                captcha_id = result.get("captcha_id")
                if not captcha_id:
                    raise ValueError(f"2Captcha did not return captcha_id: {result}")

                if verbose:
                    print(f"✅ Captcha uploaded. ID: {captcha_id}")

        except asyncio.TimeoutError:
            raise ValueError("2Captcha upload timeout")

        # Poll for solution
        deadline = time.time() + timeout
        poll_interval = 3  # seconds between polls

        while time.time() < deadline:
            await asyncio.sleep(poll_interval)

            status_payload = {
                "apikey": api_key,
                "action": "get",
                "captcha_id": captcha_id,
                "json": 1,
            }

            try:
                async with session.get(TWOCAPTCHA_STATUS_URL, params=status_payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        if verbose:
                            print(f"⏳ Status check failed (HTTP {resp.status}), retrying...")
                        continue

                    result = await resp.json()

                    if result.get("is_correct") == False or "error_text" in result:
                        raise ValueError(f"2Captcha error: {result.get('error_text', 'Unknown error')}")

                    if result.get("status") == 0:
                        # Not ready yet
                        if verbose:
                            print(f"⏳ Solving... ({int(time.time() - (deadline - timeout))}s elapsed)")
                        continue

                    # Solution ready
                    token = result.get("request")
                    if not token:
                        raise ValueError(f"2Captcha returned empty token: {result}")

                    elapsed = time.time() - (deadline - timeout)
                    if verbose:
                        print(f"✅ Solved in {elapsed:.1f}s")

                    return token

            except asyncio.TimeoutError:
                if verbose:
                    print(f"⏳ Status check timeout, retrying...")
                continue

        raise asyncio.TimeoutError(f"reCAPTCHA solve timeout after {timeout}s")


def solve_recaptcha_v2_sync(
    page_url: str,
    sitekey: str,
    api_key: str,
    timeout: int = SOLVE_TIMEOUT,
) -> str:
    """Blocking wrapper around solve_recaptcha_v2."""
    return asyncio.run(solve_recaptcha_v2(page_url, sitekey, api_key, timeout, verbose=True))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python3 thunderbird_recaptcha_solver.py <page_url> <sitekey> <api_key>")
        print("Example: python3 thunderbird_recaptcha_solver.py https://www.example.com/login abc123 key456")
        sys.exit(1)

    page_url, sitekey, api_key = sys.argv[1:4]
    try:
        token = solve_recaptcha_v2_sync(page_url, sitekey, api_key)
        print(f"Token: {token}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
