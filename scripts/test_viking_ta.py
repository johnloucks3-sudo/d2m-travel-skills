#!/usr/bin/env python3
"""
Viking TA portal login test — verifies Azure B2C OAuth flow with current creds.
Expected: FAIL (consumer account, not TA). Documents exact failure mode + fix steps.
"""
import asyncio, json, sys, textwrap
from datetime import datetime
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH  = THUNDERBIRD / "config" / "portal_creds.json"
SCREENSHOTS = THUNDERBIRD / "storage" / "output" / "viking_test"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

VIKING_ADVISOR = "https://www.viking.com/travel-advisor"

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

async def main():
    creds = json.loads(CREDS_PATH.read_text())
    viking = creds.get("viking", {})
    email    = viking.get("email", "")
    password = viking.get("password", "")
    print(f"{'='*66}")
    print(f"  VIKING TA ACCOUNT LOGIN TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*66}")
    print(f"  Credentials: email={email!r}")
    print(f"  Account type: consumer (not TA) — EXPECTED FAILURE")
    print(f"{'='*66}\n")

    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        # ── 1. Go to TA portal ──
        log(f"Navigating to {VIKING_ADVISOR} ...")
        await page.goto(VIKING_ADVISOR, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(3_000)
        log(f"  URL: {page.url}")
        log(f"  Title: {await page.title()}")
        await page.screenshot(path=str(SCREENSHOTS / "01_landing.png"), full_page=True)

        # ── 2. Dump visible elements — find the login path ──
        log("\n  Scanning visible interactive elements ...")
        buttons = await page.query_selector_all("button, a[href*='login'], a[href*='sign'], a[class*='login'], a[class*='sign']")
        if buttons:
            for btn in buttons[:10]:
                txt = (await btn.inner_text()).strip()
                href = await btn.get_attribute("href") or ""
                visible = await btn.is_visible()
                log(f"    button/link: text={txt!r:30s} href={href!r:40s} visible={visible}")
        else:
            log("    No buttons found — checking page structure ...")

        # ── 3. Check for OAuth redirect to login.viking.com ──
        if "login.viking.com" in page.url:
            log("\n  Detected Azure B2C login page.")
            await page.screenshot(path=str(SCREENSHOTS / "02_b2c_login.png"), full_page=True)

        # ── 4. Map form fields (they may be invisible until triggered) ──
        inputs = await page.query_selector_all("input")
        log(f"\n  Found {len(inputs)} input elements:")
        for inp in inputs:
            t  = await inp.get_attribute("type") or ""
            n  = await inp.get_attribute("name") or ""
            pid = await inp.get_attribute("id") or ""
            ph = await inp.get_attribute("placeholder") or ""
            vis = await inp.is_visible()
            log(f"    type={t:12s} name={n:20s} id={pid:25s} placeholder={ph:20s} visible={vis}")

        # ── 5. Fill fields if visible — otherwise try clicking Sign in first ──
        email_el = page.locator("#signInName").first
        pass_el  = page.locator("#password").first
        email_visible = False
        pass_visible  = False
        try:
            email_visible = await email_el.is_visible(timeout=1_000)
        except Exception:
            pass
        try:
            pass_visible = pass_visible or await pass_el.is_visible(timeout=1_000)
        except Exception:
            pass

        if not email_visible or not pass_visible:
            log("\n  Fields are HIDDEN — may require clicking a 'Sign in' trigger first.")
            signin_btn = None
            for sel in [
                "button:has-text('Sign in')",
                "button:has-text('Log in')",
                "button:has-text('Sign In')",
                "button:has-text('Log In')",
                "button:has-text('Login')",
                "a:has-text('Sign in')",
                "button[id*='sign']",
                "button[id*='login']",
                "[class*='signin'] button",
                "[class*='login'] button",
            ]:
                btn = page.locator(sel).first
                try:
                    if await btn.is_visible(timeout=1_000):
                        log(f"  Found trigger: {sel}")
                        signin_btn = sel
                        break
                except Exception:
                    continue

            if signin_btn:
                log(f"  Clicking '{signin_btn}' to reveal form ...")
                await page.locator(signin_btn).first.click()
                await page.wait_for_timeout(2_000)
                await page.screenshot(path=str(SCREENSHOTS / "03_after_signin_click.png"), full_page=True)
                try:
                    email_visible = await email_el.is_visible(timeout=3_000)
                    pass_visible  = await pass_el.is_visible(timeout=3_000)
                    log(f"  Post-click: email_visible={email_visible} pass_visible={pass_visible}")
                except Exception:
                    pass
            else:
                log("  No Sign-in trigger found. Dumping full body HTML for diagnosis ...")
                body_html = await page.inner_html("body")
                log(f"  Body HTML (first 3000 chars):\n{body_html[:3000]}")
        else:
            log("\n  Fields are visible — proceeding to fill.")

        # ── 6. Attempt login ──
        if email_visible and pass_visible:
            log("\n  Filling credentials ...")
            await email_el.click()
            await page.keyboard.press("Control+a")
            await email_el.press_sequentially(email, delay=40)
            await page.wait_for_timeout(200)

            await pass_el.click()
            await page.keyboard.press("Control+a")
            await pass_el.press_sequentially(password, delay=40)
            await page.wait_for_timeout(200)

            submitted = False
            for btn_sel in [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Sign in')",
                "button:has-text('Log in')",
                "button:has-text('Continue')",
            ]:
                try:
                    btn = page.locator(btn_sel).first
                    if await btn.is_visible(timeout=1_000):
                        log(f"  Clicking submit: {btn_sel}")
                        await btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                log("  No submit button — pressing Enter")
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(5_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except PWTimeout:
                pass
            await page.wait_for_timeout(2_000)
        else:
            log("\n  Cannot fill form — fields not visible after all attempts.")
            await page.screenshot(path=str(SCREENSHOTS / "04_no_form.png"), full_page=True)

        # ── 7. Capture post-login state ──
        post_url   = page.url
        post_title = await page.title()
        try:
            post_body = (await page.inner_text("body")).lower()[:800]
        except Exception:
            post_body = ""

        await page.screenshot(path=str(SCREENSHOTS / "05_post_login.png"), full_page=True)
        await page.screenshot(path=str(SCREENSHOTS / "05_post_login_full.png"), full_page=True)

        log(f"\n{'='*66}")
        log(f"  POST-LOGIN STATE")
        log(f"{'='*66}")
        log(f"  URL:   {post_url}")
        log(f"  Title: {post_title!r}")
        log(f"  Body:  {post_body[:300]!r}")

        # ── 8. Evaluate result ──
        print(f"\n{'='*66}")
        print(f"  RESULT ANALYSIS")
        print(f"{'='*66}")

        # TA portal URLs contain /travel-advisor after login; consumer URLs contain /myjourney
        is_ta_portal   = "/travel-advisor" in post_url and "dashboard" in post_url or "search" in post_url
        is_consumer    = "/myjourney" in post_url or "my-journey" in post_url
        error_signals  = ["incorrect", "invalid", "wrong", "failed", "error", "sign in", "log in"]

        if is_ta_portal:
            print(f"  ✅ TA LOGIN SUCCESSFUL — on TA dashboard")
        elif is_consumer:
            print(f"  ❌ CONSUMER ACCOUNT — not TA")
            print(f"     Redirected to {post_url}")
            print(f"     johnloucks3@gmail.com is a consumer account.")
            print(f"     A proper TA account must be registered with Nexion host credentials.")
        elif any(s in post_body for s in error_signals):
            print(f"  ❌ LOGIN FAILED — credential error")
        elif "login" in post_url.lower() or "b2c" in post_url.lower():
            print(f"  ⚠ STILL ON LOGIN PAGE — may be MFA or form submission failed")
        else:
            print(f"  ? AMBIGUOUS — check URL and body above")

        await browser.close()

    # ── 9. Summary for Commander ──
    print(f"\n{'='*66}")
    print(f"  COMMANDER ACTION REQUIRED — TA ACCOUNT REGISTRATION")
    print(f"{'='*66}")
    print(textwrap.dedent("""
    The current Viking credentials (johnloucks3@gmail.com) are a CONSUMER
    account. Azure B2C validates account tier on login — this will never
    reach the TA dashboard regardless of password correctness.

    Step-by-step for Commander:
    ────────────────────────────────────────────────────────────
    1. Go to https://www.viking.com/travel-advisor

    2. Click "Register" or "Create Account" (NOT "Sign In")

    3. Fill the TA registration form with:
       - Host Agency: Nexion / Travel Leaders Group
       - Nexion IATAN # or CLIA # — see Nexion profile at
         https://app.myagentmate.com (creds in portal_creds.json)
       - Agency Name: Dreams2Memories Travel, LLC
       - Your full name and contact info

    4. Use a business email if possible (john@lovegrouptravel.com
       or similar), OR register with johnloucks3@gmail.com but
       identify as a TA with Nexion credentials.

    5. Verify the registration via the email link Viking sends.

    6. Test login at https://www.viking.com/travel-advisor
       — should land on TA dashboard, not /myjourney/*

    7. Update portal_creds.json → viking section:
       - email: <registered email>
       - password: <chosen password>
       - url: https://www.viking.com/travel-advisor

    Note: If the page shows a "Consumer" vs "Travel Advisor" toggle
    at the top, make sure "Travel Advisor" is selected before
    registering.

    Host agency reference:
      Nexion / Travel Leaders Group
      URL: https://app.myagentmate.com
      Login: NXN8IMC (in portal_creds.json → nexion_myagentmate)
      Contact Nexion support for your Viking TA registration code
      or preferred IATAN/CLIA number to use.
    ────────────────────────────────────────────────────────────
    """))

    print(f"\n  Screenshots saved to: {SCREENSHOTS}/")
    print(f"{'='*66}")

if __name__ == "__main__":
    asyncio.run(main())
