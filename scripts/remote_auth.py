from playwright.sync_api import sync_playwright
import json
import time

def setup_remote_login(url, cookie_file):
    with sync_playwright() as p:
        # Launch with remote debugging. Basic stealth args added 2026-07-10
        # for the Icelandair test (Cloudflare Bot Management target) —
        # --disable-blink-features=AutomationControlled hides the one
        # trivially-detected navigator.webdriver flag vanilla Playwright
        # Chromium sets; channel="chrome" uses the real installed Chrome
        # binary instead of Playwright's bundled Chromium, which carries a
        # different (more automation-associated) build fingerprint.
        browser = p.chromium.launch(
            headless=True,  # MUST be true for headless environments
            channel="chrome",
            args=[
                "--remote-debugging-port=9222",
                "--remote-debugging-address=0.0.0.0",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        print(f"Remote debugging launched on port 9222.")
        print(f"Connect your browser via: ssh -L 9222:localhost:9222 john@yoga")
        print(f"Navigate to: {url}")
        
        # Fixed 2026-07-10: browser.contexts[0] assumes a pre-existing
        # context, which a fresh launch() doesn't have — IndexError on
        # first real run (caught during the Icelandair proof-of-concept).
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        
        print("Waiting for you to login... (Press Ctrl+C when done)")
        try:
            while True:
                time.sleep(5)
                # Check for successful navigation (assuming it goes to a dashboard)
                if "dashboard" in page.url or "home" in page.url:
                    print(f"Detected login! URL: {page.url}")
                    cookies = context.cookies()
                    with open(cookie_file, 'w') as f:
                        json.dump(cookies, f)
                    print(f"Cookies saved to {cookie_file}")
                    break
        except KeyboardInterrupt:
            print("Capturing manual cookies now...")
            cookies = context.cookies()
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
            print(f"Cookies saved to {cookie_file}")
        finally:
            browser.close()

if __name__ == "__main__":
    # We will run this for Hotelbeds first, then TESS
    import sys
    target = sys.argv[1]
    if target == "hotelbeds":
        setup_remote_login("https://app.bedsonline.com/auth/login", "/home/john/Thunderbird/creds/hotelbeds_cookies.json")
    elif target == "tess":
        # Adjust URL as needed for TESS portal
        setup_remote_login("https://portal.tess.com/login", "/home/john/Thunderbird/creds/tess_cookies.json")
    elif target == "icelandair":
        # 2026-07-10 proof-of-concept — cf_bm/cf_clearance are IP+UA-bound,
        # so the login MUST happen through this same server's egress IP
        # (never grab cookies from the Commander's local Chrome instead —
        # see docs/superpowers/specs/2026-07-09-self-healing-architecture-
        # reverse-engineered.md-adjacent airfare CI audit, Icelandair section).
        setup_remote_login("https://www.icelandair.com/en-us/", "/home/john/Thunderbird/creds/icelandair_cookies.json")
