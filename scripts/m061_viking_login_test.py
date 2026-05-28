#!/usr/bin/env python3
"""
M-061 — Viking login test
Azure B2C OAuth flow — probe login with current creds, map the form fields,
attempt auth, report post-login state.
"""
import asyncio
import json
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH  = THUNDERBIRD / "config" / "portal_creds.json"

VIKING_ADVISOR = "https://www.viking.com/travel-advisor"


async def main():
    from playwright.async_api import async_playwright

    creds = json.loads(CREDS_PATH.read_text())
    viking = creds.get("viking", {})
    email    = viking.get("email", "")
    password = viking.get("password", "")
    print(f"Testing with email={email!r}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()

        print(f"Navigating to {VIKING_ADVISOR} ...")
        await page.goto(VIKING_ADVISOR, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2_500)

        print(f"  Final URL: {page.url}")
        print(f"  Title:     {await page.title()}")

        # Map login form fields
        email_sel = None
        for sel in [
            "input[type='email']", "input[name='email']",
            "input[id*='email']", "input[type='text']",
            "input[id*='logon']", "input[name='logonIdentifier']",
        ]:
            el = page.locator(sel).first
            try:
                if await el.is_visible(timeout=1_500):
                    email_sel = sel
                    print(f"  Email field: {sel}")
                    break
            except Exception:
                continue

        pass_sel = None
        for sel in ["input[type='password']", "input[name='password']", "input[id*='password']"]:
            el = page.locator(sel).first
            try:
                if await el.is_visible(timeout=1_500):
                    pass_sel = sel
                    print(f"  Password field: {sel}")
                    break
            except Exception:
                continue

        if not email_sel or not pass_sel:
            print("  ⚠ Could not find both form fields — dumping visible inputs:")
            inputs = await page.query_selector_all("input")
            for inp in inputs[:10]:
                t = await inp.get_attribute("type") or ""
                n = await inp.get_attribute("name") or ""
                pid = await inp.get_attribute("id") or ""
                ph = await inp.get_attribute("placeholder") or ""
                vis = await inp.is_visible()
                print(f"    type={t!r} name={n!r} id={pid!r} placeholder={ph!r} visible={vis}")
            await browser.close()
            return

        # Fill and submit
        print(f"\nFilling credentials ...")
        email_loc = page.locator(email_sel).first
        pass_loc  = page.locator(pass_sel).first

        await email_loc.click()
        await page.keyboard.press("Control+a")
        await email_loc.press_sequentially(email, delay=50)
        await page.wait_for_timeout(300)

        await pass_loc.click()
        await page.keyboard.press("Control+a")
        await pass_loc.press_sequentially(password, delay=50)
        await page.wait_for_timeout(300)

        # Find submit button
        submitted = False
        for btn_sel in [
            "button[type='submit']", "input[type='submit']",
            "button:has-text('Sign in')", "button:has-text('Log in')",
            "button:has-text('Continue')", "button:has-text('Next')",
        ]:
            try:
                btn = page.locator(btn_sel).first
                if await btn.is_visible(timeout=1_500):
                    print(f"  Clicking: {btn_sel}")
                    await btn.click()
                    submitted = True
                    break
            except Exception:
                continue

        if not submitted:
            print("  No submit button found — pressing Enter")
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(5_000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            pass

        post_url   = page.url
        post_title = await page.title()
        post_text  = (await page.inner_text("body")).lower()[:600]

        print(f"\nPost-login:")
        print(f"  URL:   {post_url}")
        print(f"  Title: {post_title!r}")
        print(f"  Body:  {post_text[:200]!r}")

        # Evaluate success
        error_signals  = ["incorrect", "invalid", "wrong", "failed", "error", "not found", "mismatch"]
        success_signals = ["dashboard", "search", "my bookings", "welcome", "agent", "advisor portal", "find a cruise"]

        if any(s in post_text for s in success_signals) and "login" not in post_url.lower():
            print("\n✅ LOGIN SUCCESSFUL")
        elif any(s in post_text for s in error_signals):
            print(f"\n❌ LOGIN FAILED — credential error")
        elif "login" in post_url.lower() or post_url == page.url:
            print(f"\n⚠ Still on login/auth page — may be MFA, wrong creds, or slow redirect")
        else:
            print(f"\n? Ambiguous — check URL and body above")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
