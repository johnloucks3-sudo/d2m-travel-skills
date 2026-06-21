#!/usr/bin/env python3
"""
google_contacts_auth.py — Add contacts scope to gmail_token.json via Chrome CDP.

Drives the existing Chrome session (port 9222) through the Google OAuth consent
flow. No new browser window needed — uses the browser that's already open and
already logged in as johnloucks3@gmail.com.

After this runs successfully, api/thunderbird_contacts_mcp.py is live.

Usage:
  python3 scripts/google_contacts_auth.py
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
CDP_URL = "http://localhost:9222"
CALLBACK_PORT = 8777  # fixed port for OAuth redirect


async def drive_oauth_in_chrome(auth_url: str):
    """Navigate Chrome to the OAuth consent URL and wait for the redirect."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        sys.exit(1)

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome at {CDP_URL}: {e}")
            return

        print(f"✅ Connected to Chrome")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        print(f"Navigating to Google OAuth consent page...")
        await page.goto(auth_url, timeout=30000)

        print("\nOAuth consent page loaded.")
        print(f"If you see a consent screen — click Allow.")
        print(f"Waiting for completion (up to 3 minutes)...\n")

        try:
            # Wait for redirect back to our local callback server
            await page.wait_for_url(
                f"**localhost:{CALLBACK_PORT}**",
                timeout=180000,
            )
            print(f"✅ Auth code received!")
        except Exception:
            # Also accept the Google success page
            try:
                await page.wait_for_selector("text=The authentication flow", timeout=10000)
                print("✅ Auth flow completed.")
            except Exception:
                print("Auth may have completed — continuing...")

        try:
            await page.close()
        except Exception:
            pass


def run_auth():
    """Run the full OAuth flow, driving Chrome for the consent step."""
    sys.path.insert(0, str(ROOT))

    from google_auth_oauthlib.flow import InstalledAppFlow
    from api.thunderbird_google_auth import OAUTH_CREDENTIALS_FILE, SCOPES, TOKEN_FILE

    print("=== Google Contacts Auth — full scope re-auth ===")
    print(f"Scopes: {len(SCOPES)} (gmail, drive, calendar, contacts, sheets, docs, photos...)")
    print()

    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: {OAUTH_CREDENTIALS_FILE} not found.")
        sys.exit(1)

    # Build the flow and set a fixed redirect URI so we know the port
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CREDENTIALS_FILE), SCOPES)
    flow.redirect_uri = f"http://localhost:{CALLBACK_PORT}/"

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # force new refresh_token with all scopes
    )

    print(f"OAuth callback will be on port {CALLBACK_PORT}")
    print(f"Auth URL ready — driving Chrome...")
    print()

    # Start the OAuth callback server in a background thread
    creds_container = []
    error_container = []

    def flow_thread():
        try:
            # run_local_server with fixed port, no browser auto-open
            creds = flow.run_local_server(
                port=CALLBACK_PORT,
                open_browser=False,
                authorization_prompt_message="",
            )
            creds_container.append(creds)
        except Exception as e:
            error_container.append(e)

    t = threading.Thread(target=flow_thread, daemon=True)
    t.start()

    # Give the server a moment to start
    time.sleep(1.5)

    # Drive Chrome to the consent page
    asyncio.run(drive_oauth_in_chrome(auth_url))

    # Wait for the flow thread to complete (token exchange)
    print("Waiting for token exchange to complete...")
    t.join(timeout=30)

    if error_container:
        print(f"\nERROR: {error_container[0]}")
        sys.exit(1)

    if not creds_container:
        print("\nAuth did not complete. No credentials received.")
        print("Try manually: python3 api/thunderbird_google_auth.py --authorize")
        sys.exit(1)

    creds = creds_container[0]
    TOKEN_FILE.write_text(creds.to_json())
    print(f"\n✅ Token saved → {TOKEN_FILE}")
    scopes = sorted(creds.scopes or SCOPES)
    print(f"   Scopes: {len(scopes)}")
    for s in scopes:
        print(f"   • {s.split('/')[-1]}")

    # Verify contacts API
    print("\nVerifying Contacts API...")
    try:
        from googleapiclient.discovery import build
        svc = build("people", "v1", credentials=creds)
        result = svc.people().connections().list(
            resourceName="people/me", pageSize=5,
            personFields="names,emailAddresses"
        ).execute()
        conns = result.get("connections", [])
        print(f"✅ Contacts API LIVE — {len(conns)} contacts returned")
        for c in conns[:3]:
            name = c.get("names", [{}])[0].get("displayName", "?")
            email = c.get("emailAddresses", [{}])[0].get("value", "?")
            print(f"   {name} | {email}")
    except Exception as e:
        print(f"Contacts test: {e}")
        print("Token saved — contacts_search should work now.")


if __name__ == "__main__":
    run_auth()
