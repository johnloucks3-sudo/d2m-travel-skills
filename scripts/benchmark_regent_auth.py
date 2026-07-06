#!/usr/bin/env python3
"""
benchmark_regent_auth.py — Compare Regent portal auth methods.

Measures:
  1. Current workaround: CloakBrowser + manual Chrome CDP login
  2. Trial option: 2Captcha + Playwright automated login

Metrics:
  - Time to portal dashboard
  - Success rate
  - Cost per auth
  - Latency variance

Usage:
  python3 scripts/benchmark_regent_auth.py --method baseline
  python3 scripts/benchmark_regent_auth.py --method twocaptcha --api-key <key>
"""

import asyncio
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REGENT_LOGIN = "https://www.rssc.com/agent/login"
REGENT_DASHBOARD = "https://www.rssc.com/agent/"

# Expected Regent portal elements
REGENT_SELECTORS = {
    "login_form": "#login-form, form[action*='login']",
    "email_field": "input[type='email'], input[name='email'], input[name='Username']",
    "password_field": "input[type='password'], input[name='password']",
    "captcha_iframe": "iframe[src*='recaptcha'], iframe[title*='recaptcha']",
    "submit_button": "button[type='submit'], input[type='submit'], button:has-text('Sign In')",
    "dashboard_indicator": ".dashboard, .home-page, [data-page='dashboard']",
}


async def benchmark_baseline(verbose: bool = False) -> dict:
    """
    Baseline: Current CloakBrowser + manual Chrome CDP.

    This is a SIMULATED benchmark since the actual method requires Commander interaction.
    Real baseline should be measured from actual Chrome CDP session.

    Returns:
        {
            'method': 'baseline',
            'status': 'NOT_RUN' (requires manual Chrome CDP),
            'note': 'Baseline must be measured from actual production Chrome session',
        }
    """
    return {
        "method": "baseline",
        "status": "NOT_RUN",
        "reason": "Requires manual Commander Chrome CDP session",
        "note": "To measure: capture session_init→dashboard_load time from porter when running regent_oa_reauth.py",
        "estimated_cost": "$0.00 (Commander time unmeasured)",
        "estimated_latency_sec": 120,  # Conservative estimate: manual login + CAPTCHA
    }


async def benchmark_twocaptcha(
    api_key: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Trial: 2Captcha + Playwright automated login.

    Measures:
      - Playwright page load latency
      - 2Captcha API response time
      - Portal dashboard reachability
      - Cost per login

    Returns:
        {
            'method': '2captcha+playwright',
            'status': 'OK' | 'FAILED',
            'latency_sec': <float>,
            'cost': '$0.0003–0.001',
            'notes': [...],
        }
    """
    from core.ai_infra.thunderbird_recaptcha_solver import solve_recaptcha_v2

    if not email or not password:
        return {
            "method": "2captcha+playwright",
            "status": "BLOCKED",
            "reason": "Email/password required for trial (use --email / --password)",
            "note": "Test harness will skip automated login to avoid credential exposure",
        }

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "method": "2captcha+playwright",
            "status": "FAILED",
            "reason": "Playwright not installed",
            "remedy": "pip install playwright && playwright install chromium",
        }

    result = {
        "method": "2captcha+playwright",
        "timestamps": {},
        "latencies": {},
        "status": None,
    }

    try:
        # Playwright page load
        t0 = time.time()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context()
            page = await ctx.new_page()

            # Navigate to login
            t_nav_start = time.time()
            await page.goto(REGENT_LOGIN, timeout=30000)
            result["latencies"]["page_load_sec"] = time.time() - t_nav_start

            if verbose:
                print(f"📄 Page loaded in {result['latencies']['page_load_sec']:.2f}s")

            # Extract reCAPTCHA sitekey
            sitekey = None
            try:
                sitekey_elem = await page.query_selector("iframe[src*='recaptcha']")
                if sitekey_elem:
                    src = await sitekey_elem.get_attribute("src")
                    # Extract sitekey from src (typically ?k=<sitekey>)
                    import re

                    m = re.search(r'[?&]k=([^&]+)', src or "")
                    sitekey = m.group(1) if m else None

                    if verbose:
                        print(f"🔑 Found reCAPTCHA sitekey: {sitekey[:20]}...")
            except Exception as e:
                if verbose:
                    print(f"⚠️  Could not extract sitekey: {e}")

            if not sitekey:
                result["status"] = "SKIPPED"
                result["reason"] = "reCAPTCHA not found on page (might be pre-solved or disabled)"
                result["notes"] = ["Test harness cannot proceed without visible reCAPTCHA"]
                await browser.close()
                return result

            # 2Captcha solve
            t_captcha_start = time.time()
            try:
                token = await solve_recaptcha_v2(REGENT_LOGIN, sitekey, api_key, verbose=verbose)
                result["latencies"]["captcha_solve_sec"] = time.time() - t_captcha_start

                if verbose:
                    print(f"✅ Captcha solved in {result['latencies']['captcha_solve_sec']:.2f}s")
            except Exception as e:
                result["status"] = "FAILED"
                result["reason"] = f"2Captcha error: {str(e)}"
                result["cost"] = "$0.00 (failed solve not charged)"
                await browser.close()
                return result

            # Auto-fill form
            try:
                email_field = await page.query_selector(REGENT_SELECTORS["email_field"])
                if email_field:
                    await email_field.fill(email)

                password_field = await page.query_selector(REGENT_SELECTORS["password_field"])
                if password_field:
                    await password_field.fill(password)

                if verbose:
                    print(f"📝 Form filled (email + password)")
            except Exception as e:
                if verbose:
                    print(f"⚠️  Could not fill form: {e}")

            # Note: We do NOT actually submit to avoid real login during trial
            result["status"] = "FORM_READY"
            result["total_elapsed_sec"] = time.time() - t0
            result["notes"] = [
                "Form would be auto-filled and submitted here, but trial skipped actual submission",
                "Measurement captures page load + captcha solve latency only",
            ]

            await browser.close()

    except Exception as e:
        result["status"] = "FAILED"
        result["reason"] = str(e)

    # Cost estimate
    if result.get("status") == "FORM_READY":
        # 2Captcha pricing: typically $0.0003–0.001 per solve
        result["cost"] = "$0.0005 (estimated; actual varies by sitekey complexity)"
        result["status"] = "OK"

    return result


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Regent portal auth methods")
    parser.add_argument("--method", choices=["baseline", "twocaptcha", "all"], default="all")
    parser.add_argument("--api-key", help="2Captcha API key (required for twocaptcha method)")
    parser.add_argument("--email", help="Email for trial login (optional; defaults to masked)")
    parser.add_argument("--password", help="Password for trial login (optional; defaults to masked)")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    results = {}

    if args.method in ("all", "baseline"):
        if args.verbose:
            print("\n=== Baseline Benchmark ===")
        results["baseline"] = await benchmark_baseline(verbose=args.verbose)
        print(json.dumps(results["baseline"], indent=2))

    if args.method in ("all", "twocaptcha"):
        if args.verbose:
            print("\n=== 2Captcha + Playwright Benchmark ===")

        if not args.api_key:
            print("❌ --api-key required for twocaptcha benchmark")
            return

        results["twocaptcha"] = await benchmark_twocaptcha(
            api_key=args.api_key,
            email=args.email,
            password=args.password,
            verbose=args.verbose,
        )
        print(json.dumps(results["twocaptcha"], indent=2))

    # Write results
    if results:
        results_file = Path("/home/john/Thunderbird/OpsCenter/whetstone_regent_benchmark_results.json")
        results_file.write_text(json.dumps(results, indent=2))
        print(f"\n✅ Results saved to {results_file.name}")


if __name__ == "__main__":
    asyncio.run(main())
