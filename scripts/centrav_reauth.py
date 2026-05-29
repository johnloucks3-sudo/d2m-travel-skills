#!/usr/bin/env python3
"""
Centrav B2B — Stealth Re-Auth Script (M-074)
=============================================
Re-authenticates to Centrav using invisible_playwright (stealth Firefox 150,
score 963/1005) which bypasses Centrav's reCAPTCHA gate (confirmed M-061).

Flow:
  1. invisible_playwright → navigate to Centrav /login
  2. Fill credentials (centrav_credentials.json)
  3. Submit — reCAPTCHA bypassed by stealth fingerprint
  4. Centrav sends 6-digit OTP to email on record (johnloucks3@gmail.com)
  5. Poll Gmail API for OTP (up to 2 min)
  6. Enter OTP in browser → authenticated
  7. Export browser cookies → centrav_session.json + centrav_credentials.json

Run when:
  - centrav_connector reports "session_expired"
  - M-076 Regent monitor flags Centrav cookie staleness (laravel_session expired)
  - Manually before an intel sweep

Usage:
  source .venv/bin/activate
  python3 scripts/centrav_reauth.py

  # Skip Gmail auto-fetch (enter OTP manually):
  python3 scripts/centrav_reauth.py --manual-otp

  # Test cookie validity only (no login attempt):
  python3 scripts/centrav_reauth.py --check-only

Dreams2Memories Travel, LLC — Hale COS / A12 ELON — M-074 2026-05-29
"""

import argparse
import json
import re
import sys
import time
from base64 import urlsafe_b64decode
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────

THUNDERBIRD = Path(__file__).resolve().parent.parent
VENV_SITE = THUNDERBIRD / ".venv" / "lib" / "python3.13" / "site-packages"
if str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
SESSION_FILE = THUNDERBIRD / "core" / "travel" / "data" / "centrav_session.json"
GMAIL_TOKEN_PATH = THUNDERBIRD / "gmail_token_commander.json"

CENTRAV_LOGIN_URL = "https://www.centrav.com/login"
CENTRAV_HOME_URL = "https://www.centrav.com/"

OTP_POLL_INTERVAL_S = 8
OTP_MAX_WAIT_S = 120  # 2 minutes


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Cookie validation ─────────────────────────────────────────────────────────

def _check_cookie_validity() -> tuple[bool, list[str]]:
    """Returns (all_valid, list_of_expired_names)."""
    if not SESSION_FILE.exists():
        return False, ["no session file"]

    try:
        cookies = json.loads(SESSION_FILE.read_text())
        if not isinstance(cookies, list):
            return False, ["invalid session file format"]
    except Exception as e:
        return False, [f"parse error: {e}"]

    now_ts = datetime.now(timezone.utc).timestamp()
    expired = []
    for c in cookies:
        exp = c.get("expires", -1)
        if exp and exp > 0 and exp < now_ts:
            expired.append(c.get("name", "?"))

    auth_names = {"laravel_session", "XSRF-TOKEN"}
    expired_auth = [n for n in expired if n in auth_names]
    return len(expired_auth) == 0, expired


# ── Gmail OTP polling ─────────────────────────────────────────────────────────

def _get_gmail_service():
    """Build Gmail API client using commander token."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        log("WARN: google-auth not installed — Gmail OTP polling unavailable")
        return None

    if not GMAIL_TOKEN_PATH.exists():
        log(f"WARN: Gmail token not found at {GMAIL_TOKEN_PATH}")
        return None

    try:
        token_data = json.loads(GMAIL_TOKEN_PATH.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            # Save refreshed token
            token_data["token"] = creds.token
            GMAIL_TOKEN_PATH.write_text(json.dumps(token_data, indent=2))

        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        log(f"WARN: Gmail service build failed: {e}")
        return None


def _extract_otp_from_body(body: str) -> str | None:
    """Extract 6-digit OTP code from email body text."""
    # Centrav sends codes in formats like: "Your code is: 123456" or just a standalone 6-digit number
    patterns = [
        r"(?:code|verification|otp)[:\s]+(\d{6})",
        r"\b(\d{6})\b",
    ]
    for pat in patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _decode_gmail_body(payload: dict) -> str:
    """Recursively extract plain text or HTML body from Gmail payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if body_data:
        return urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    # Recurse into parts
    for part in payload.get("parts", []):
        text = _decode_gmail_body(part)
        if text:
            return text
    return ""


def _poll_gmail_for_otp(service, timeout_s: int = OTP_MAX_WAIT_S) -> str | None:
    """Poll Gmail for Centrav OTP email. Returns 6-digit code or None."""
    log(f"Polling Gmail for Centrav OTP (up to {timeout_s}s)...")
    start = time.monotonic()
    seen_ids: set[str] = set()

    while time.monotonic() - start < timeout_s:
        try:
            # Search for recent Centrav emails (last 5 minutes)
            result = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q="from:centrav newer_than:5m subject:code OR subject:verification OR subject:login",
                    maxResults=5,
                )
                .execute()
            )
            msgs = result.get("messages", [])
            for msg_ref in msgs:
                mid = msg_ref["id"]
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)

                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=mid, format="full")
                    .execute()
                )
                body = _decode_gmail_body(msg.get("payload", {}))
                snippet = msg.get("snippet", "")
                combined = f"{snippet} {body}"
                otp = _extract_otp_from_body(combined)
                if otp:
                    log(f"  OTP found: {otp} (message id: {mid})")
                    return otp

            # Also try a broader search if narrow search misses it
            if not msgs:
                broad = (
                    service.users()
                    .messages()
                    .list(userId="me", q="from:centrav newer_than:5m", maxResults=3)
                    .execute()
                )
                for msg_ref in broad.get("messages", []):
                    mid = msg_ref["id"]
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=mid, format="full")
                        .execute()
                    )
                    body = _decode_gmail_body(msg.get("payload", {}))
                    otp = _extract_otp_from_body(f"{msg.get('snippet','')} {body}")
                    if otp:
                        log(f"  OTP found (broad search): {otp}")
                        return otp

        except Exception as e:
            log(f"  Gmail poll error: {e}")

        elapsed = round(time.monotonic() - start)
        log(f"  No OTP yet ({elapsed}s elapsed) — waiting {OTP_POLL_INTERVAL_S}s...")
        time.sleep(OTP_POLL_INTERVAL_S)

    log("  OTP poll timed out.")
    return None


# ── Browser re-auth ───────────────────────────────────────────────────────────

def _save_cookies(cookies: list[dict]) -> None:
    """Save Playwright cookies to centrav_session.json and centrav_credentials.json."""
    # Save to session file (primary — read by centrav_connector)
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    log(f"  Saved {len(cookies)} cookies → {SESSION_FILE}")

    # Update credentials file cookies dict
    if CREDS_PATH.exists():
        try:
            creds = json.loads(CREDS_PATH.read_text())
            creds["cookies"] = {c["name"]: c["value"] for c in cookies}
            creds["_last_exported"] = datetime.now(timezone.utc).isoformat()
            CREDS_PATH.write_text(json.dumps(creds, indent=2))
            log(f"  Updated cookies in {CREDS_PATH}")
        except Exception as e:
            log(f"  WARN: could not update {CREDS_PATH}: {e}")


def do_reauth(manual_otp: bool = False) -> bool:
    """Perform stealth re-auth. Returns True on success."""
    try:
        from invisible_playwright import InvisiblePlaywright
    except ImportError as e:
        log(f"FATAL: cannot import invisible_playwright: {e}")
        log(f"Run: source {THUNDERBIRD}/.venv/bin/activate && pip install invisible-playwright")
        return False

    # Load credentials
    if not CREDS_PATH.exists():
        log(f"FATAL: credentials not found at {CREDS_PATH}")
        return False
    try:
        creds = json.loads(CREDS_PATH.read_text())
        email = creds["email"]
        password = creds["password"]
    except Exception as e:
        log(f"FATAL: could not load credentials: {e}")
        return False

    # Prepare Gmail service for OTP polling
    gmail_service = None
    if not manual_otp:
        gmail_service = _get_gmail_service()
        if not gmail_service:
            log("Gmail service unavailable — will prompt for manual OTP entry")
            manual_otp = True

    log(f"Launching InvisiblePlaywright (headless=True, stealth Firefox 150)...")
    launch_t0 = time.monotonic()
    success = False

    try:
        with InvisiblePlaywright(
            headless=True,
            humanize=True,
            prep_recaptcha=True,
            locale="en-US",
            timezone="America/Denver",
        ) as browser:
            log(f"Browser ready ({round(time.monotonic()-launch_t0,1)}s)")

            ctx = browser.new_context()
            page = ctx.new_page()

            # Step 1: Navigate to login
            log(f"Navigating to {CENTRAV_LOGIN_URL}")
            page.goto(CENTRAV_LOGIN_URL, timeout=45_000, wait_until="domcontentloaded")
            time.sleep(2.0)

            url = page.url
            log(f"  Landed on: {url}")

            # Check for immediate bot-block
            body_text = ""
            try:
                body_text = page.inner_text("body")[:2000].lower()
            except Exception:
                pass
            if any(s in body_text for s in ["access denied", "cloudflare", "ray id", "checking your browser"]):
                log("FAIL: Bot-block detected before login")
                page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_blocked.png"))
                return False

            # Step 2: Fill credentials
            try:
                page.fill("#FormEmail", email, timeout=10_000)
                page.fill("#FormPassword", password, timeout=5_000)
                log(f"  Credentials filled ({email})")
            except Exception as e:
                log(f"FAIL: Could not fill credential fields: {e}")
                page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_fill_fail.png"))
                return False

            # Step 3: Submit (reCAPTCHA bypassed by stealth fingerprint)
            try:
                page.click("#FormSubmitButton, [type='submit']", timeout=8_000)
                log("  Form submitted — waiting for redirect...")
                time.sleep(3.5)
            except Exception as e:
                log(f"WARN: submit click issue: {e}")
                page.keyboard.press("Enter")
                time.sleep(3.5)

            # Step 4: Detect post-submit state
            url_after = page.url
            body_after = ""
            try:
                body_after = page.inner_text("body")[:4000].lower()
            except Exception:
                pass

            log(f"  Post-submit URL: {url_after}")

            # Check for email MFA screen
            otp_signals = [
                "check your email", "verification code", "enter the code",
                "email code", "6-digit", "one-time", "sent to your email",
            ]
            on_otp_screen = any(s in body_after for s in otp_signals)

            # Check if already authenticated (skipped MFA)
            auth_signals = ["logout", "my account", "dashboard", "search flights", "flying from"]
            already_auth = any(s in body_after for s in auth_signals)
            if "login" not in url_after.lower() and not on_otp_screen:
                already_auth = True

            if already_auth and not on_otp_screen:
                log("  ✅ Authenticated directly (no MFA required this session)")
                cookies = ctx.cookies()
                _save_cookies(cookies)
                success = True

            elif on_otp_screen:
                log("  Email MFA screen detected — fetching OTP...")
                page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_mfa_screen.png"))

                otp = None
                if manual_otp:
                    otp = input("  Enter the 6-digit OTP from your email: ").strip()
                else:
                    otp = _poll_gmail_for_otp(gmail_service)
                    if not otp:
                        log("  Gmail poll failed — falling back to manual entry")
                        otp = input("  Enter the 6-digit OTP from your email (johnloucks3@gmail.com): ").strip()

                if not otp or not re.match(r"^\d{6}$", otp):
                    log(f"FAIL: Invalid OTP '{otp}'")
                    return False

                # Step 5: Enter OTP
                log(f"  Entering OTP: {otp}")
                try:
                    # Try common OTP input selectors
                    otp_selectors = [
                        "input[name='code']", "input[name='otp']", "input[name='token']",
                        "input[type='number']", "input[placeholder*='code']",
                        "input[placeholder*='Code']", "input[maxlength='6']",
                    ]
                    filled_otp = False
                    for sel in otp_selectors:
                        try:
                            el = page.query_selector(sel)
                            if el and el.is_visible():
                                el.fill(otp)
                                filled_otp = True
                                log(f"  OTP filled via selector: {sel}")
                                break
                        except Exception:
                            continue

                    if not filled_otp:
                        # Fallback: type OTP into focused element
                        page.keyboard.type(otp, delay=80)
                        filled_otp = True
                        log("  OTP typed via keyboard (fallback)")

                    time.sleep(0.5)

                    # Submit OTP form
                    submit_selectors = ["[type='submit']", "button[name='verify']", "button"]
                    for sel in submit_selectors:
                        try:
                            btn = page.query_selector(sel)
                            if btn and btn.is_visible():
                                btn.click()
                                break
                        except Exception:
                            continue
                    else:
                        page.keyboard.press("Enter")

                    time.sleep(3.5)

                except Exception as e:
                    log(f"FAIL: OTP entry failed: {e}")
                    page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_otp_fail.png"))
                    return False

                # Step 6: Verify authentication
                url_final = page.url
                body_final = ""
                try:
                    body_final = page.inner_text("body")[:3000].lower()
                except Exception:
                    pass

                log(f"  Post-OTP URL: {url_final}")

                if "login" not in url_final.lower() and any(s in body_final for s in auth_signals + ["logout"]):
                    log("  ✅ Authenticated after OTP")
                    cookies = ctx.cookies()
                    _save_cookies(cookies)
                    success = True
                elif "login" not in url_final.lower():
                    log("  ✅ Likely authenticated (redirected off login)")
                    cookies = ctx.cookies()
                    _save_cookies(cookies)
                    success = True
                else:
                    log(f"FAIL: Still on login page after OTP. URL={url_final}")
                    page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_otp_rejected.png"))

            else:
                log(f"FAIL: Unknown post-submit state. URL={url_after}")
                page.screenshot(path=str(THUNDERBIRD / "output" / "centrav_reauth_unknown.png"))

            page.close()

    except Exception as e:
        import traceback
        log(f"FATAL: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    return success


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Centrav B2B stealth re-auth (M-074)")
    parser.add_argument("--check-only", action="store_true",
                        help="Check cookie validity only — do not re-auth")
    parser.add_argument("--manual-otp", action="store_true",
                        help="Prompt for OTP manually instead of Gmail polling")
    args = parser.parse_args()

    log("=" * 60)
    log("Centrav Re-Auth — M-074 — Thunderbird OS")
    log("=" * 60)

    # Always check current state
    valid, expired = _check_cookie_validity()
    if valid:
        log("✅ Session cookies are VALID — no re-auth needed")
        if not args.check_only:
            log("   (use --check-only to stop here)")
    else:
        log(f"🔴 Session EXPIRED — expired cookies: {', '.join(expired)}")

    if args.check_only:
        sys.exit(0 if valid else 1)

    if valid:
        log("Skipping re-auth (session still valid). Run with --force to override.")
        sys.exit(0)

    # Perform re-auth
    log("")
    log("Starting stealth re-auth via invisible_playwright...")
    ok = do_reauth(manual_otp=args.manual_otp)

    log("")
    if ok:
        log("=" * 60)
        log("✅ RE-AUTH COMPLETE")
        log(f"   Session file: {SESSION_FILE}")
        log(f"   Centrav connector will use fresh cookies on next run.")
        log("=" * 60)
        sys.exit(0)
    else:
        log("=" * 60)
        log("❌ RE-AUTH FAILED")
        log("   Check output/centrav_reauth_*.png for screenshots")
        log("   Fallback: open Firefox, login manually, export cookies via:")
        log("   python3 scripts/export_regent_cookies.py  (adapt for Centrav)")
        log("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
