"""XVFB + Headful Firefox — RSSC Agent Portal Auto-Login.
Uses exact selectors from DOM dump, evaluate() instead of content()."""
import asyncio, json, os, subprocess, time
from pathlib import Path
from playwright._impl._errors import TimeoutError as PwTimeout

ROOT = Path("/home/john/Thunderbird")
CREDS_FILE = ROOT / "config" / "portal_creds.json"
COOKIES_FILE = ROOT / "creds" / "regent_cookies.json"
PROD_PROFILE = ROOT / "state" / "firefox_rssc_prod"
PROD_PROFILE.mkdir(parents=True, exist_ok=True)

LOGIN_URL = ("https://www.rssc.com/agent/default.aspx"
             "?ReturnUrl=%2fagent%2fdashboard%2f")
FURLOW_BOOKING = ("https://www.rssc.com/agent/myaccount/bookedcruise.aspx"
                  "?eecDnW0xAFxbgFqHZBS8Eko5Uc3K5UTVHzz%2b5iUsOMeF38Ba0f"
                  "%2bR5xYgM6Gv3nm1CyaweMg7GG8DwKCVXbjhAg%3d%3d")

DISPLAY_NUM = 99


def load_credentials():
    creds = json.loads(CREDS_FILE.read_text())
    acct = creds.get("regent", {}).get("account_direct", {})
    return acct.get("email", ""), acct.get("password", "")


async def run():
    xvfb = None
    try:
        xvfb = subprocess.Popen(
            ["/usr/bin/Xvfb", f":{DISPLAY_NUM}", "-screen", "0", "1440x900x24"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        os.environ["DISPLAY"] = f":{DISPLAY_NUM}"
        time.sleep(1)

        from playwright.async_api import async_playwright

        email, password = load_credentials()
        print(f"Credentials: {email[:4]}...{'*' * 6}")

        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=False)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})

            print("\n1. Loading RSSC agent dashboard...")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            try:
                await page.evaluate("""() =>
                    document.querySelectorAll('meta[http-equiv="refresh"]')
                        .forEach(e => e.remove())
                """)
            except Exception as e:
                print(f"   Meta-refresh kill failed (non-fatal): {e}")

            try:
                await page.wait_for_selector("input", state="attached", timeout=20000)
                print("   Input fields detected — page stabilized")
            except PwTimeout:
                print("   ⚠️  Timed out waiting for inputs")

            await page.wait_for_timeout(2000)

            url = page.url
            title = await page.evaluate("document.title")
            print(f"   URL: {url[:100]}")
            print(f"   Title: {title!r}")

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PwTimeout:
                print("   Network idle timed out (continuing)")

            sso = await page.evaluate("""() => {
                const h = window.location.hostname;
                const body = document.body.innerHTML.toLowerCase();
                return {
                    current_host: h,
                    is_azure: h.includes('login.microsoftonline.com') ||
                              !!document.querySelector('#i0116'),
                    is_okta: h.includes('okta') ||
                             !!document.querySelector('[data-se="o-form"]'),
                    is_saml: !!document.querySelector('input[name="SAMLResponse"]'),
                    captcha_recaptcha: !!document.querySelector('.g-recaptcha, #recaptcha'),
                    captcha_hcaptcha: !!document.querySelector('.h-captcha'),
                    captcha_generic: body.includes('captcha'),
                    akamai_blocked: body.includes('access denied') ||
                                    body.includes('_abck')
                };
            }""")
            print(f"   SSO/CAPTCHA state: {json.dumps(sso, indent=6)}")

            is_login_page = "default.aspx" in url or (
                "login" in url.lower()
            ) or sso["is_azure"] or sso["is_okta"]

            if sso.get("akamai_blocked"):
                print("\n   ❌ Akamai still blocking via JS check")
                text = await page.evaluate("document.body.innerText")
                print(f"   Page text: {text[:300]}")
                await browser.close()
                return

            if sso.get("captcha_recaptcha") or sso.get("captcha_hcaptcha"):
                print("\n   ⛔ CAPTCHA detected — auto-login not possible")
                await browser.close()
                return

            if is_login_page:
                print("\n2. Login page confirmed — dumping input fields")

                inputs = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('input')).map(i => ({
                        id: i.id, name: i.name, type: i.type,
                        placeholder: i.placeholder, className: i.className,
                        form: i.form ? i.form.id : null,
                        visible: i.offsetParent !== null
                    }))
                """)
                buttons = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('button, input[type=submit]'))
                        .map(b => ({
                            id: b.id, type: b.type || b.getAttribute('type'),
                            text: (b.innerText || b.value || '').trim(),
                            visible: b.offsetParent !== null
                        }))
                """)
                print(f"   Inputs ({len(inputs)}):")
                for inp in inputs:
                    print(f"     id={inp['id']!r} name={inp['name']!r} "
                          f"type={inp['type']!r} placeholder={inp['placeholder']!r} "
                          f"visible={inp['visible']}")
                print(f"   Buttons ({len(buttons)}):")
                for btn in buttons:
                    print(f"     id={btn['id']!r} type={btn['type']!r} "
                          f"text={btn['text']!r} visible={btn['visible']}")

                print("\n3. Dismissing OneTrust cookie banner...")
                try:
                    accept_btn = await page.wait_for_selector(
                        "#onetrust-accept-btn-handler", timeout=3000
                    )
                    if accept_btn:
                        await accept_btn.click()
                        await page.wait_for_timeout(1000)
                        print("   OneTrust ACCEPT clicked")
                except PwTimeout:
                    print("   No OneTrust banner found")

                print("\n4. Filling login form (targeting exact selectors)...")
                login_email_id = "uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox"
                login_pass_id = "uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox"

                email_el = await page.wait_for_selector(
                    f"#{login_email_id}", timeout=5000
                )
                pass_el = await page.wait_for_selector(
                    f"#{login_pass_id}", timeout=5000
                )

                if email_el and pass_el:
                    await email_el.click()
                    await email_el.fill(email)
                    await page.wait_for_timeout(300)
                    await pass_el.click()
                    await pass_el.fill(password)
                    await page.wait_for_timeout(300)

                    print("   Fields filled. Submitting via Enter...")
                    await page.keyboard.press("Enter")

                    await page.wait_for_timeout(10000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except PwTimeout:
                        pass

                    await page.wait_for_timeout(3000)

                    post_url = page.url
                    post_title = await page.evaluate("document.title")
                    post_text = await page.evaluate("document.body.innerText")
                    post_html_lower = await page.evaluate(
                        "() => document.documentElement.outerHTML.toLowerCase()"
                    )

                    logged_in = (
                        "myaccount" in post_url
                        or "dashboard" in post_url
                        or "bookedcruise" in post_url
                    )
                    still_login = (
                        "default.aspx" in post_url
                        or "sign in" in post_html_lower and not logged_in
                    )
                    error_msg = "incorrect" in post_text.lower() or "invalid" in post_text.lower()

                    print(f"\n5. Post-login URL: {post_url[:100]}")
                    print(f"   Post-login title: {post_title!r}")
                    print(f"   Logged in (by URL): {logged_in}")
                    print(f"   Still on login page: {still_login}")
                    print(f"   Error message: {error_msg}")

                    if logged_in:
                        cookies = await page.context.cookies()
                        rssc_cookies = [
                            c for c in cookies
                            if "rssc.com" in c.get("domain", "")
                        ]

                        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
                        print(f"\n   ✅ Login SUCCESS — {len(rssc_cookies)} cookies saved")

                        print("\n6. Injecting into persistent production profile...")
                        from playwright.async_api import async_playwright as pw_native
                        async with pw_native() as pw:
                            ctx = await pw.firefox.launch_persistent_context(
                                user_data_dir=str(PROD_PROFILE), headless=True
                            )
                            await ctx.add_cookies(rssc_cookies)
                            fp = await ctx.new_page()
                            await fp.goto(
                                FURLOW_BOOKING,
                                wait_until="commit", timeout=30000
                            )
                            await fp.wait_for_timeout(5000)

                            fhtml = await fp.evaluate(
                                "document.documentElement.outerHTML"
                            )
                            fauth = "sign out" in fhtml.lower() or "mybookings" in fhtml.lower()
                            print(f"   Furlow booking page authenticated: {fauth}")

                            if fauth:
                                print(f"\n{'='*55}")
                                print("   🎉 TOTAL AUTOMATION ACHIEVED 🎉")
                                print(f"{'='*55}")
                                print(f"   Profile: {PROD_PROFILE}")
                            else:
                                print("\n   ⚠️  Cookies saved but profile test failed")
                                ftext = await fp.evaluate("document.body.innerText")
                                print(f"   Furlow text: {ftext[:300]}")

                            await ctx.close()
                    else:
                        print(f"\n   ❌ Login failed")
                        if error_msg:
                            print("   → Wrong credentials")
                            print(f"   Error text: {post_text[:300]}")
                        else:
                            print(f"   Post-login text (first 500):")
                            print(f"   {post_text[:500]}")
                else:
                    print("\n   ❌ Could not find login form fields")
                    inputs = await page.evaluate("""() =>
                        Array.from(document.querySelectorAll('input')).map(i => ({
                            id: i.id, name: i.name, type: i.type
                        }))
                    """)
                    print(f"   Available inputs: {inputs}")
            else:
                print("\n   ❌ Unexpected page state")
                text = await page.evaluate("document.body.innerText")
                print(f"   Page text (first 300): {text[:300]}")

            await browser.close()

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        if xvfb:
            xvfb.terminate()
            xvfb.wait()
            print("\nXvfb stopped")


if __name__ == "__main__":
    asyncio.run(run())
