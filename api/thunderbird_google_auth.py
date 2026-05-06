"""
Thunderbird Unified Google Auth
================================
Dreams2Memories Travel, LLC

Single OAuth token (gmail_token.json) covering all Google APIs.
One re-auth grants access to every Google service Thunderbird uses.

Service builders:
    from thunderbird_google_auth import get_gmail, get_drive, get_calendar
    from thunderbird_google_auth import get_sheets, get_docs, get_tasks, get_people

Re-authorize (if scopes expanded or token missing):
    python3 thunderbird_google_auth.py --authorize

Check current token scopes:
    python3 thunderbird_google_auth.py --status
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"

# ---------------------------------------------------------------------------
# Master scope list — ALL Google APIs Thunderbird uses
# ---------------------------------------------------------------------------

SCOPES = [
    # Gmail — read, write, send, label, trash (superset of compose)
    "https://www.googleapis.com/auth/gmail.modify",
    # Drive — full CRUD on files and folders
    "https://www.googleapis.com/auth/drive",
    # Calendar — create, update, delete events on any accessible calendar
    "https://www.googleapis.com/auth/calendar",
    # Sheets — read and write all spreadsheets
    "https://www.googleapis.com/auth/spreadsheets",
    # Docs — create and edit documents
    "https://www.googleapis.com/auth/documents",
    # Forms — create and manage forms
    "https://www.googleapis.com/auth/forms.body",
    # Tasks — create, update, complete tasks
    "https://www.googleapis.com/auth/tasks",
    # People / Contacts — read and write contact records
    "https://www.googleapis.com/auth/contacts",
]

# ---------------------------------------------------------------------------
# Persona Gmail — separate account for D2M Wing internal communications
# ---------------------------------------------------------------------------
# Account: concierge.d2mluxury@gmail.com (or similar — create in browser first)
# Purpose: Personas send FROM this account TO Commander. Commander replies
#          land in this inbox — closing the conversational loop. Eliminates
#          draft clutter in Commander's personal inbox (johnloucks3 = personal only, not D2M ops).
#
# Setup (one-time, Commander must do):
#   1. Create Google account: concierge.d2mluxury@gmail.com
#   2. python3 thunderbird_google_auth.py --authorize-persona
# ---------------------------------------------------------------------------

PERSONA_GMAIL_TOKEN = THUNDERBIRD_DIR / "config" / "persona_gmail_token.json"
PERSONA_GMAIL_ADDRESS = "d2mconcierge@gmail.com"
PERSONA_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

_cached_persona_creds: Credentials | None = None


def get_persona_credentials(force_refresh: bool = False) -> Credentials:
    """Return credentials for the persona Gmail account."""
    global _cached_persona_creds
    if _cached_persona_creds and _cached_persona_creds.valid and not force_refresh:
        return _cached_persona_creds
    if not PERSONA_GMAIL_TOKEN.exists():
        raise FileNotFoundError(
            f"No persona Gmail token at {PERSONA_GMAIL_TOKEN}.\n"
            "Run: python3 thunderbird_google_auth.py --authorize-persona"
        )
    creds = Credentials.from_authorized_user_file(str(PERSONA_GMAIL_TOKEN), PERSONA_GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        PERSONA_GMAIL_TOKEN.write_text(creds.to_json())
    _cached_persona_creds = creds
    return creds


def get_persona_gmail():
    """Return authenticated Gmail service for the D2M Wing persona account."""
    return build("gmail", "v1", credentials=get_persona_credentials())


# ---------------------------------------------------------------------------
# Commander Gmail — johnloucks3@gmail.com (part of the Wing, SO 2026-04-24)
# ---------------------------------------------------------------------------
# Authority expansion granted 2026-04-24: Commander reclassified johnloucks3 as
# part of the wing. Hale has full read/label/manage access — same authority as
# d2mconcierge. No re-auth needed; token at creds/johnloucks3_token.json.
# ---------------------------------------------------------------------------

COMMANDER_GMAIL_TOKEN = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
COMMANDER_GMAIL_ADDRESS = "johnloucks3@gmail.com"
COMMANDER_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

_cached_commander_creds: Credentials | None = None


def get_commander_credentials(force_refresh: bool = False) -> Credentials:
    """Return credentials for the Commander's Gmail account (johnloucks3@gmail.com)."""
    global _cached_commander_creds
    if _cached_commander_creds and _cached_commander_creds.valid and not force_refresh:
        return _cached_commander_creds
    if not COMMANDER_GMAIL_TOKEN.exists():
        raise FileNotFoundError(
            f"No Commander Gmail token at {COMMANDER_GMAIL_TOKEN}.\n"
            "Commander must re-authenticate via OAuth flow."
        )
    creds = Credentials.from_authorized_user_file(str(COMMANDER_GMAIL_TOKEN), COMMANDER_GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        COMMANDER_GMAIL_TOKEN.write_text(creds.to_json())
    _cached_commander_creds = creds
    return creds


def get_commander_gmail():
    """Return authenticated Gmail service for Commander's inbox (johnloucks3@gmail.com)."""
    return build("gmail", "v1", credentials=get_commander_credentials())


def commander_gmail_available() -> bool:
    """True if the Commander Gmail token exists and is valid."""
    try:
        get_commander_credentials()
        return True
    except Exception:
        return False


def persona_gmail_available() -> bool:
    """True if the persona Gmail token exists and is valid."""
    try:
        get_persona_credentials()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Core credential loader (shared by all service builders)
# ---------------------------------------------------------------------------

_cached_creds: Credentials | None = None


def get_credentials(force_refresh: bool = False) -> Credentials:
    """Return valid OAuth2 credentials, refreshing if expired.

    Raises FileNotFoundError if no token exists — run --authorize first.
    Raises ValueError if current token is missing required scopes.
    """
    global _cached_creds

    if _cached_creds and not force_refresh:
        if _cached_creds.valid:
            return _cached_creds
        if _cached_creds.expired and _cached_creds.refresh_token:
            _cached_creds.refresh(Request())
            _save_token(_cached_creds)
            return _cached_creds

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"No token found at {TOKEN_FILE}. "
            "Run: python3 thunderbird_google_auth.py --authorize"
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)

    _cached_creds = creds
    return creds


def _save_token(creds: Credentials) -> None:
    TOKEN_FILE.write_text(creds.to_json())


def authorize() -> Credentials:
    """Run browser OAuth flow and save the token.

    Requests ALL scopes in one flow — no need to re-auth per API.
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}\n"
            "Download from Google Cloud Console → APIs & Services → Credentials."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    print(f"✓ Token saved to {TOKEN_FILE}")
    print(f"  Scopes granted: {len(creds.scopes or SCOPES)}")
    return creds


# ---------------------------------------------------------------------------
# Service builders
# ---------------------------------------------------------------------------

def get_gmail():
    """Return authenticated Gmail API v1 service."""
    return build("gmail", "v1", credentials=get_credentials())


def get_drive():
    """Return authenticated Drive API v3 service."""
    return build("drive", "v3", credentials=get_credentials())


def get_calendar():
    """Return authenticated Calendar API v3 service."""
    return build("calendar", "v3", credentials=get_credentials())


def get_sheets():
    """Return authenticated Sheets API v4 service."""
    return build("sheets", "v4", credentials=get_credentials())


def get_docs():
    """Return authenticated Docs API v1 service."""
    return build("docs", "v1", credentials=get_credentials())


def get_forms():
    """Return authenticated Forms API v1 service."""
    return build("forms", "v1", credentials=get_credentials())


def get_tasks():
    """Return authenticated Tasks API v1 service."""
    return build("tasks", "v1", credentials=get_credentials())


def get_people():
    """Return authenticated People API v1 service."""
    return build("people", "v1", credentials=get_credentials())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HEADLESS_PORT = 8085  # SSH-forwardable port for headless OAuth


def authorize_headless() -> Credentials:
    """Headless OAuth flow for Yoga (no local browser).

    Starts a local callback server on port 8085, then you SSH-forward that
    port to your Chromebook and complete the flow in any browser.

    Step-by-step:
      1. Keep this terminal open (it's waiting for the callback)
      2. In a NEW terminal on your Chromebook:
             ssh -L 8085:localhost:8085 john@192.168.1.198
      3. Open http://localhost:8085 in your Chromebook browser
      4. Sign in to Google and grant all permissions
      5. Browser shows "The authentication flow has completed" — done
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}\n"
            "Download from Google Cloud Console → APIs & Services → Credentials."
        )
    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), SCOPES
    )
    print("\n" + "=" * 60)
    print("HEADLESS OAUTH — Two-terminal method")
    print("=" * 60)
    print(f"\nStep 1: Keep this terminal open (waiting on port {HEADLESS_PORT})")
    print("\nStep 2: Open a NEW terminal on your Chromebook and run:")
    print(f"          ssh -L {HEADLESS_PORT}:localhost:{HEADLESS_PORT} john@192.168.1.198")
    print(f"\nStep 3: Open in Chromebook browser: http://localhost:{HEADLESS_PORT}")
    print("\nStep 4: Sign in to Google, grant all permissions")
    print("         (browser will show 'authentication flow completed')")
    print("\nWaiting for browser callback...\n")

    creds = flow.run_local_server(
        port=HEADLESS_PORT,
        open_browser=False,
        prompt="consent",
        access_type="offline",
    )
    _save_token(creds)
    print(f"\n✓ Token saved to {TOKEN_FILE}")
    print(f"  Scopes granted: {len(creds.scopes or SCOPES)}")
    return creds


def authorize_persona() -> Credentials:
    """OAuth flow for the D2M Wing persona Gmail account.

    Copy-paste method — no local server, no port forwarding.
    Works on any machine: browser fails to load the redirect, you copy the URL, paste it here.
    """
    # oauthlib rejects http:// redirect URIs unless this is set.
    # localhost redirects over HTTP are safe and standard for installed apps.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    if not OAUTH_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), PERSONA_GMAIL_SCOPES
    )
    flow.redirect_uri = "http://localhost:8085/"

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    print("\n" + "=" * 60)
    print("PERSONA GMAIL OAUTH — copy-paste method")
    print("=" * 60)
    print(f"\nAccount to authorize: {PERSONA_GMAIL_ADDRESS}")
    print("Make sure you are signed into THAT account in the browser.\n")
    print("STEP 1 — Open this URL in any browser:")
    print(f"\n  {auth_url}\n")
    print("STEP 2 — Click Allow / Continue on the Google consent screen.")
    print()
    print("STEP 3 — The browser will try to redirect to localhost:8085")
    print("         and show 'site cannot be reached' — that is expected.")
    print()
    print("STEP 4 — Copy the FULL URL from the browser address bar")
    print("         (it starts with http://localhost:8085/?state=...&code=...)")
    print()

    redirect_response = input("Paste the full redirect URL here: ").strip()

    flow.fetch_token(authorization_response=redirect_response)
    creds = flow.credentials
    PERSONA_GMAIL_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    PERSONA_GMAIL_TOKEN.write_text(creds.to_json())
    print(f"\n✓ Persona token saved to {PERSONA_GMAIL_TOKEN}")
    print(f"  Persona Gmail ready: {PERSONA_GMAIL_ADDRESS}")
    return creds


if __name__ == "__main__":
    if "--authorize-persona" in sys.argv:
        print("Authorizing D2M Wing persona Gmail account...")
        creds = authorize_persona()
        print("\nPersona Gmail ready. Personas can now send and receive independently.")

    elif "--authorize-headless" in sys.argv:
        print("Headless Google OAuth authorization (no browser needed on this machine).")
        print("Requesting all Thunderbird scopes in one flow.\n")
        creds = authorize_headless()
        print("\nAuthorization complete. All Google APIs are now accessible.")

    elif "--authorize" in sys.argv:
        print("Opening browser for Google OAuth authorization...")
        print("Requesting all Thunderbird scopes in one flow.")
        creds = authorize()
        print("\nAuthorization complete. All Google APIs are now accessible.")

    elif "--status" in sys.argv:
        if not TOKEN_FILE.exists():
            print(f"No token found at {TOKEN_FILE}")
            print("Run: python3 thunderbird_google_auth.py --authorize")
            sys.exit(1)
        token_data = json.loads(TOKEN_FILE.read_text())
        granted = token_data.get("scopes", [])
        print(f"Token: {TOKEN_FILE}")
        print(f"Granted scopes ({len(granted)}):")
        for s in granted:
            status = "✓" if s in SCOPES else "?"
            print(f"  {status} {s}")
        missing = [s for s in SCOPES if s not in granted]
        if missing:
            print(f"\nMissing scopes ({len(missing)}) — run --authorize to add:")
            for s in missing:
                print(f"  ✗ {s}")
        else:
            print("\nAll required scopes are present.")

    else:
        print("Usage:")
        print("  python3 thunderbird_google_auth.py --authorize-headless  # Headless auth — main D2M account (Yoga)")
        print("  python3 thunderbird_google_auth.py --authorize           # Desktop auth — main D2M account (opens browser)")
        print("  python3 thunderbird_google_auth.py --authorize-persona   # Authorize persona Gmail (concierge.d2mluxury@gmail.com)")
        print("  python3 thunderbird_google_auth.py --status              # Show current token scopes")
