#!/usr/bin/env python3
"""
VTG Cookie Refresh Helper.

Opens vacationstogo.com in Firefox (visible), waits for Commander to log in,
then captures CFID/CFTOKEN/VTG/VTG_COOKIE cookies and saves them.

Run: python3 scripts/vtg_cookie_refresh.py
"""
import json, time
from pathlib import Path

ROOT   = Path("/home/john/Thunderbird")
CREDS  = ROOT / "creds" / "vtg_cookies.json"

def main():
    from playwright.sync_api import sync_playwright

    print("Opening VTG in Chromium (visible)…")
    print("Log in to vacationstogo.com when the browser opens.")
    print("Press Enter here when you've logged in and can see the deal page.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.vacationstogo.com/", wait_until="domcontentloaded")

        input("\n[Press Enter after logging in to save cookies] ")

        # Capture target cookies
        all_cookies = context.cookies()
        vtg_cookies = {
            c["name"]: c["value"]
            for c in all_cookies
            if c.get("domain", "").endswith("vacationstogo.com")
            and c["name"] in {"CFID", "CFTOKEN", "TS01859d73", "VTG", "VTG_COOKIE"}
        }

        browser.close()

    if not vtg_cookies:
        print("No VTG cookies captured — were you logged in?")
        return

    CREDS.write_text(json.dumps(vtg_cookies, indent=2))
    print(f"Saved {len(vtg_cookies)} cookies to {CREDS}")
    print("Now run: python3 scripts/fetch_vtg_ticker.py")

if __name__ == "__main__":
    main()
