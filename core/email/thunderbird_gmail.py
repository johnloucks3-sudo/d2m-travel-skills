"""
Dreams2Memories Gmail MCP Module
================================

Extends the travel MCP server with Gmail operations:
- Search messages by query
- Read individual messages
- Read full threads
- List drafts
- Create drafts (never auto-send for safety)

Uses OAuth 2.0 Desktop flow for D2M ops Gmail (d2mconcierge@gmail.com).
First run requires browser authorization; refresh token is saved for
all subsequent runs.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import time
import functools
import base64
import mimetypes
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
EMAIL_SENT_LOG = THUNDERBIRD_DIR / "logs" / "email_sent.log"
DRAFT_BODY_CACHE = THUNDERBIRD_DIR / "logs" / "draft_body_cache.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
USER_EMAIL = "d2mconcierge@gmail.com"
D2M_FROM_ADDRESS = "concierge@d2mluxury.quest"
COMMANDER_D2M_EMAIL = "john@d2mluxury.quest"
COMMANDER_EMAIL = "d2mconcierge@gmail.com"  # Commander directive 2026-03-19: d2mconcierge is sole D2M ops Gmail

# ── D2M Ops Gmail (d2mconcierge@gmail.com) ───────────────────────────────────
# PRIMARY D2M ops account — Commander directive 2026-03-19.
# ALL drafts, reads, sends, and label ops happen here.
WING_GMAIL_ADDRESS = "d2mconcierge@gmail.com"

# ── Commander Gmail (johnloucks3@gmail.com) ───────────────────────────────────
# Reclassified as part of the wing per Commander SO 2026-04-24.
# Hale has full read/label/manage authority — same as d2mconcierge.
# Token: ~/Thunderbird/creds/johnloucks3_token.json (gmail.modify scope, no re-auth needed).
COMMANDER_INBOX_ADDRESS = "johnloucks3@gmail.com"

def _get_wing_gmail_service():
    """Return Gmail service authenticated as the Wing persona account (d2mconcierge)."""
    try:
        from thunderbird_google_auth import get_persona_gmail
        return get_persona_gmail()
    except Exception as e:
        raise RuntimeError(f"Wing Gmail not available: {e}. Run --authorize-persona.")


def _get_commander_gmail_service():
    """Return Gmail service authenticated as Commander's inbox (johnloucks3@gmail.com).

    Granted wing-level access per Commander SO 2026-04-24. Hale may read, search,
    label, move, and flag — but never draft or send from this account.
    """
    try:
        from thunderbird_google_auth import get_commander_gmail
        return get_commander_gmail()
    except Exception as e:
        raise RuntimeError(f"Commander Gmail not available: {e}. Check creds/johnloucks3_token.json.")

# All Commander-owned addresses — sends here are auto-authorized, no draft staging needed.
# Commander directive 2026-03-18: "SENDING TO ME FROM D2M CONCIERGE OR D2M STAFF IS AUTHORIZED"
COMMANDER_ADDRS = {
    "johnloucks3@gmail.com",
    "johnloucks75@gmail.com",
    "concierge@d2mluxury.quest",
    "john@d2mluxury.quest",
}

# Persona display names for Send As support
PERSONA_DISPLAY_NAMES = {
    "COS": "Victoria Hale, D2M Travel",
    "EXEC": "Naia Solberg-Vega, D2M Travel",
    "A2": "Marcus Dembe, D2M Travel",
    "A3": "Dani Moreau, D2M Travel",
    "A5": "Ryan Castillo, D2M Travel",
    "A6": "Luna Voss, D2M Travel",
    "A9": "Vic Harlan, D2M Travel",
    "A10": "Tomoko Ikeda, D2M Travel",
    "CH": "James Washington, D2M Travel",
    "A12": "ELON, D2M Travel",
    "D2M": "Dreams2Memories Travel",
    "CONCIERGE": "D2M Concierge",
    "COMMANDER": "John Loucks, Dreams2Memories Travel",
}

# Commander's email ink color — bright blue, his pen of choice.
# Restored to #0000ff per Commander directive 2026-03-16.
D2M_INK_COLOR = "#0000ff"

# Commander directive 2026-03-21: ALL outbound correspondence — Dani or not — must include
# Commander's signature and logo.  Logo is in the banner; this block is the signature footer,
# appended inside the paper card below the body text.
COMMANDER_SIGNATURE_HTML = (
    '<hr style="border: none; border-top: 1px solid rgba(201,168,76,0.45); margin: 28px 0 18px 0;" />'
    '<div style="color: #0000ff; font-family: Georgia, \'Times New Roman\', serif; '
    'font-size: 9.5pt; line-height: 1.7;">'
    '<strong>John Loucks</strong><br>'
    'Owner &amp; Founder, Dreams2Memories Travel, LLC<br>'
    '<a href="mailto:concierge@d2mluxury.quest" '
    'style="color: #0000ff; text-decoration: none;">concierge@d2mluxury.quest</a>'
    '&nbsp;&middot;&nbsp;'
    '<a href="https://d2mluxury.quest" '
    'style="color: #0000ff; text-decoration: none;">d2mluxury.quest</a>'
    '</div>'
)

# ── STAFF PERSONA VISUAL IDENTITY ────────────────────────────────────────────
# Per-persona config for all Wing→Commander internal email templates.
# Drives: accent color, full name/rank/title, and email address for sig blocks.
_STAFF_PERSONA_CONFIGS: dict = {
    "COS": {
        "name": 'Col Victoria &ldquo;Iron Vic&rdquo; Hale',
        "suffix": ", USAF (Ret.)",
        "title": "Chief of Staff &nbsp;&middot;&nbsp; Thunderbird Wing",
        "accent": "#D4AF37",
        "email": "d2mconcierge@gmail.com",
    },
    "EXEC": {
        "name": "Naia Solberg-Vega",
        "suffix": "",
        "title": "Executive Director &nbsp;&middot;&nbsp; Voice, Visual &amp; Commander's Intent",
        "accent": "#C0C0C0",
        "email": "d2mconcierge@gmail.com",
    },
    "A1": {
        "name": 'Dr. Sofia &ldquo;Iris&rdquo; Navarro',
        "suffix": "",
        "title": "A1 &nbsp;&middot;&nbsp; Intake &amp; Client Profile Architect",
        "accent": "#4ECDC4",
        "email": "d2mconcierge@gmail.com",
    },
    "A2": {
        "name": 'Lt Col Marcus &ldquo;Wraith&rdquo; Dembe',
        "suffix": ", USAF (Ret.)",
        "title": "A2 &nbsp;&middot;&nbsp; Research &amp; Market Intelligence",
        "accent": "#4A90D9",
        "email": "d2mconcierge@gmail.com",
    },
    "A3": {
        "name": 'Danielle &ldquo;Dani&rdquo; Moreau',
        "suffix": "",
        "title": "A3 &nbsp;&middot;&nbsp; D2M Luxury Travel Concierge",
        "accent": "#C9956C",
        "email": "d2mconcierge@gmail.com",
    },
    "A5": {
        "name": 'Lt Col Ryan &ldquo;Viper&rdquo; Castillo',
        "suffix": ", USAF (Ret.)",
        "title": "A5 &nbsp;&middot;&nbsp; Strategy &amp; Business Growth",
        "accent": "#DC143C",
        "email": "d2mconcierge@gmail.com",
    },
    "A6": {
        "name": "Luna Voss",
        "suffix": "",
        "title": "A6 &nbsp;&middot;&nbsp; Creative Director &amp; Brand Dreamer",
        "accent": "#9B59B6",
        "email": "d2mconcierge@gmail.com",
    },
    "A7": {
        "name": 'Brig Gen (Ret.) Thomas &ldquo;Gauge&rdquo; Sterling',
        "suffix": "",
        "title": "A7 &nbsp;&middot;&nbsp; Process, Technology &amp; Metrics",
        "accent": "#CD7F32",
        "email": "d2mconcierge@gmail.com",
    },
    "A8": {
        "name": 'Marco &ldquo;Atlas&rdquo; Reyes',
        "suffix": "",
        "title": "A8 &nbsp;&middot;&nbsp; Experience Architect",
        "accent": "#F39C12",
        "email": "d2mconcierge@gmail.com",
    },
    "A9": {
        "name": 'Victor &ldquo;Vic&rdquo; Harlan',
        "suffix": "",
        "title": "A9 &nbsp;&middot;&nbsp; Finance &amp; Process Improvement",
        "accent": "#27AE60",
        "email": "d2mconcierge@gmail.com",
    },
    "CH": {
        "name": 'Col James &ldquo;Padre&rdquo; Washington',
        "suffix": ", USAF (Ret.)",
        "title": "CH &nbsp;&middot;&nbsp; Wisdom, Ethics &amp; Morale",
        "accent": "#8B0000",
        "email": "d2mconcierge@gmail.com",
    },
    "A12": {
        "name": "ELON",
        "suffix": "",
        "title": "A12 &nbsp;&middot;&nbsp; Innovation &amp; Disruption",
        "accent": "#00CED1",
        "email": "d2mconcierge@gmail.com",
    },
}


def _get_staff_icon_html(persona_id: str, accent: str) -> str:
    """Return a CSS div badge for each Wing persona — renders in all email clients.

    SVG is stripped by Gmail. This div/span approach (border-radius circles with
    callsign initials) works universally: Gmail web, Outlook, Apple Mail.
    COS Hale gets a double-ring treatment to mark command authority.
    """
    bg = "#0d1117"
    # Two-letter callsign badge labels — unique per persona
    labels = {
        "COS":  ("IVH", "10pt"),   # Iron Vic Hale — 3 letters, COS distinction
        "EXEC": ("NSV", "10pt"),   # Naia Solberg-Vega
        "A1":   ("IR",  "13pt"),   # Iris Navarro
        "A2":   ("WR",  "13pt"),   # Wraith Dembe
        "A3":   ("DN",  "13pt"),   # Dani Moreau
        "A5":   ("VP",  "13pt"),   # Viper Castillo
        "A6":   ("LV",  "13pt"),   # Luna Voss
        "A7":   ("GS",  "13pt"),   # Gauge Sterling
        "A8":   ("AR",  "13pt"),   # Atlas Reyes
        "A9":   ("VH",  "13pt"),   # Vic Harlan
        "CH":   ("PW",  "13pt"),   # Padre Washington
        "A12":  ("EL",  "13pt"),   # ELON
    }
    label, font_size = labels.get(persona_id, (persona_id[:2], "13pt"))

    if persona_id == "COS":
        # Eagle emoji in double gold ring — the IVH seal. Emoji renders in Gmail + all clients.
        return (
            f'<div style="display:inline-block;width:54px;height:54px;'
            f'border-radius:50%;background:{accent};text-align:center;'
            f'vertical-align:middle;">'
            f'<div style="width:44px;height:44px;margin:5px;border-radius:50%;'
            f'background:{bg};border:1.5px solid {accent};text-align:center;'
            f'line-height:44px;font-size:22pt;">'
            f'&#x1F985;'
            f'</div>'
            f'</div>'
        )

    # All other staff: solid accent disc, dark initials
    return (
        f'<div style="display:inline-block;width:54px;height:54px;border-radius:50%;'
        f'background:{accent};text-align:center;line-height:54px;vertical-align:middle;'
        f'font-family:Arial Black,Arial,sans-serif;font-size:{font_size};'
        f'font-weight:900;color:{bg};letter-spacing:0.5px;">'
        f'{label}'
        f'</div>'
    )


# Keep SVG function as dead code reference — not used (Gmail strips SVG)
def _get_staff_icon_svg(persona_id: str, accent: str) -> str:  # noqa: ARG001
    return _get_staff_icon_html(persona_id, accent)


def _wrap_staff_html(body: str, persona_id: str = "COS") -> str:
    """Universal Wing→Commander email template with per-persona visual identity.

    Dark-ops base: charcoal wrapper, per-persona accent color and icon SVG.
    All styles inline — Gmail strips style blocks. No Commander sig block.
    """
    import html as html_mod
    import re as _re

    cfg = _STAFF_PERSONA_CONFIGS.get(persona_id.upper(), _STAFF_PERSONA_CONFIGS["COS"])
    accent = cfg["accent"]

    if _re.search(r'<[a-zA-Z][^>]*>', body):
        html_body = body
    else:
        escaped = html_mod.escape(body)
        html_body = escaped.replace('\n', '<br>\n')

    icon_svg = _get_staff_icon_html(persona_id.upper(), accent)

    sig = (
        f'<hr style="border:none;border-top:2px solid {accent};margin:28px 0 18px 0;" />'
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:9.5pt;'
        f'line-height:1.7;color:#c9d1d9;">'
        f'<strong style="color:{accent};letter-spacing:1px;">{cfg["name"]}</strong>'
        f'{cfg["suffix"]}<br>'
        f'{cfg["title"]}<br>'
        f'Dreams2Memories Travel, LLC<br>'
        f'<a href="mailto:{cfg["email"]}" style="color:#8b949e;text-decoration:none;">'
        f'{cfg["email"]}</a>'
        f'</div>'
    )

    return (
        '<div style="background:#0d1117;padding:0;margin:0;'
        'font-family:Arial,Helvetica,sans-serif;">'

        f'<div style="background:#161b22;padding:18px 28px;'
        f'border-bottom:2px solid {accent};text-align:center;">'
        f'<div style="display:inline-block;vertical-align:middle;margin-right:14px;">'
        f'{icon_svg}</div>'
        '<div style="display:inline-block;vertical-align:middle;">'
        f'<div style="color:{accent};font-size:12pt;font-weight:700;letter-spacing:3px;'
        f'text-transform:uppercase;font-family:Arial,Helvetica,sans-serif;">'
        'THUNDERBIRD WING</div>'
        '<div style="color:#8b949e;font-size:8pt;letter-spacing:2px;margin-top:3px;">'
        'DREAMS2MEMORIES TRAVEL, LLC &nbsp;&middot;&nbsp; COMMAND CHANNEL</div>'
        '</div>'
        '</div>'

        '<div style="background:#0d1117;padding:28px 36px 24px 36px;">'
        '<div style="color:#e6edf3;font-size:10.5pt;line-height:1.75;'
        'font-family:Arial,Helvetica,sans-serif;">'
        f'{html_body}'
        '</div>'
        f'{sig}'
        '</div>'

        '<div style="background:#161b22;border-top:1px solid #30363d;'
        'padding:8px 32px;text-align:center;">'
        '<span style="color:#484f58;font-size:7.5pt;letter-spacing:1.5px;'
        'font-family:Arial,Helvetica,sans-serif;">'
        'INTERNAL &nbsp;&bull;&nbsp; THUNDERBIRD WING &nbsp;&bull;&nbsp; EYES ONLY'
        '</span>'
        '</div>'

        '</div>'
    )


# Backward-compat alias — delegates to universal staff wrapper
HALE_SIGNATURE_HTML = ""  # Unused externally; sig now generated dynamically in _wrap_staff_html


def _wrap_hale_html(plain_text: str) -> str:
    return _wrap_staff_html(plain_text, "COS")


logger = logging.getLogger(__name__)

# Cached service instance
_gmail_service = None


def _get_gmail_service():
    """Authenticate and return a cached Gmail API service instance.

    Uses OAuth 2.0 Desktop flow:
    - If gmail_token.json exists, loads and auto-refreshes the token
    - If no token exists, raises a clear error pointing to --authorize
    """
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service

    creds = None

    # Load existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            TOKEN_FILE.write_text(creds.to_json())
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            creds = None

    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail not authorized. Run:  python3 thunderbird_gmail.py --authorize\n"
            f"OAuth credentials file needed: {OAUTH_CREDENTIALS_FILE}"
        )

    _gmail_service = build("gmail", "v1", credentials=creds)
    return _gmail_service


def authorize_gmail():
    """Run the one-time OAuth 2.0 authorization flow.

    Opens a browser for user consent, saves the refresh token to gmail_token.json.
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: OAuth credentials file not found: {OAUTH_CREDENTIALS_FILE}")
        print()
        print("To create it:")
        print("  1. Go to console.cloud.google.com > project d2m-python-pipeline")
        print("  2. APIs & Services > Credentials > Create Credentials > OAuth client ID")
        print("  3. Application type: Desktop app")
        print("  4. Download JSON and save as:")
        print(f"     {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"Authorization successful! Token saved to {TOKEN_FILE}")
    print(f"Email: {USER_EMAIL}")
    return True


def _retry_on_error(func):
    """Retry wrapper for transient Google API errors (429, 500, 503)."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        retries = 3
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status in (429, 500, 503) and attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Gmail API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _strip_html(html: str) -> str:
    """Convert HTML to readable plain text using stdlib."""
    import html as html_mod
    import re
    # Replace common block elements with newlines
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)  # strip remaining tags
    text = html_mod.unescape(text)
    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _decode_body(payload):
    """Extract body from a Gmail message payload.

    Prefers text/plain. Falls back to text/html (stripped to plain text)
    so HTML-only emails (confirmations, cruise lines, etc.) aren't lost.
    """
    plain = _find_mime_part(payload, "text/plain")
    if plain:
        return plain
    html = _find_mime_part(payload, "text/html")
    if html:
        logger.debug("No text/plain part found — falling back to HTML→text conversion")
        return _strip_html(html)
    logger.debug("No text/plain or text/html body found in message payload")
    return ""


def _find_mime_part(payload, mime_type: str) -> str | None:
    """Recursively search a Gmail payload for a specific MIME type and decode it."""
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == mime_type and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # Nested multipart
        if part.get("parts"):
            result = _find_mime_part(part, mime_type)
            if result:
                return result
    return None


def _get_logo_data_uri() -> str:
    """Load the D2M email logo as a base64 data URI. Cached after first call.

    Looks for Agency_Logo_email.png in media/ (email-optimised, ~54KB).
    Falls back to Agency_Logo.png (full cinematic, ~623KB) if email version absent.
    """
    if not hasattr(_get_logo_data_uri, '_cached'):
        import base64 as b64
        # Canonical location: ~/Thunderbird/media/
        base = Path(__file__).resolve().parent.parent.parent  # ~/Thunderbird/
        for candidate in ("media/Agency_Logo_email.png", "media/Agency_Logo.png"):
            logo_path = base / candidate
            if logo_path.exists():
                with open(logo_path, 'rb') as f:
                    _get_logo_data_uri._cached = f"data:image/png;base64,{b64.b64encode(f.read()).decode()}"
                break
        else:
            _get_logo_data_uri._cached = ""
            logger.warning("Agency_Logo_email.png not found in media/ — email banner will be omitted")
    return _get_logo_data_uri._cached


def _get_dani_avatar_data_uri() -> str:
    """Load Dani Moreau avatar as base64 data URI. Cached after first call."""
    if not hasattr(_get_dani_avatar_data_uri, '_cached'):
        avatar_path = Path(__file__).parent / "output" / "images" / "dani_moreau_avatar.png"
        if avatar_path.exists():
            import base64 as b64
            with open(avatar_path, 'rb') as f:
                _get_dani_avatar_data_uri._cached = f"data:image/png;base64,{b64.b64encode(f.read()).decode()}"
        else:
            _get_dani_avatar_data_uri._cached = ""
            logger.warning("dani_moreau_avatar.png not found — Dani sig will render without avatar")
    return _get_dani_avatar_data_uri._cached


def _get_dani_sig_html() -> str:
    """Return HTML for Dani Moreau's persona sig block — circular avatar balanced with name/role/contact."""
    avatar_uri = _get_dani_avatar_data_uri()
    avatar_cell = (
        f'<td style="padding-right:14px;vertical-align:middle;">'
        f'<img src="{avatar_uri}" alt="Dani Moreau" '
        f'style="width:64px;height:64px;border-radius:50%;display:block;'
        f'border:2px solid rgba(201,168,76,0.55);" /></td>'
    ) if avatar_uri else '<td style="display:none;"></td>'

    return (
        '<div style="margin:22px 0 0 0;">'
        '<table style="border-collapse:collapse;">'
        '<tr>'
        f'{avatar_cell}'
        '<td style="vertical-align:middle;font-family:Georgia,\'Times New Roman\',serif;'
        'font-size:9.5pt;color:#0000ff;line-height:1.7;">'
        '<strong>Dani Moreau</strong><br>'
        '<em>D2M Luxury Travel Concierge</em><br>'
        '<a href="mailto:concierge@d2mluxury.quest" style="color:#0000ff;text-decoration:none;">'
        'concierge@d2mluxury.quest</a>'
        '&nbsp;&middot;&nbsp;719-291-0742'
        '</td>'
        '</tr>'
        '</table>'
        '</div>'
    )


def _wrap_body_html(plain_text: str, persona_id: Optional[str] = None) -> str:
    """Wrap plain text body in styled HTML — D2M AFA stationery for Gmail.

    Design intent: Air Force Academy blue (#003087) hero with cinematic D2M logo,
    clean white content area, silver (#A9B0B7) accents. All styles inline for Gmail.

    Layout:
      - Full-width hero: D2M cinematic logo image over AFA blue gradient overlay
      - Silver divider stripe (3px gradient)
      - White content card (640px), dark body text (#2c2c2c), Georgia serif
      - AFA blue headings (#003087), silver accent borders
      - Logo thumbnail beside sig block
      - Navy gradient footer with D2M branding
    """
    # If caller already passed a full HTML document, inline CSS so Gmail renders it correctly.
    # Gmail strips <style> blocks — premailer converts them to inline styles.
    stripped = plain_text.strip()
    if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
        try:
            import premailer
            return premailer.transform(plain_text, remove_classes=False, strip_important=False)
        except Exception:
            pass  # Fall through and return as-is if premailer unavailable
        return plain_text

    import html as html_mod
    import re as _re
    # If body already contains HTML tags (partial HTML), don't escape — use directly.
    # Only escape if it's truly plain text with no markup.
    if _re.search(r'<[a-zA-Z][^>]*>', plain_text):
        html_body = plain_text
    else:
        escaped = html_mod.escape(plain_text)
        html_body = escaped.replace('\n', '<br>\n')

    logo_uri = _get_logo_data_uri()

    # ── HERO HEADER ──────────────────────────────────────────────────────────
    if logo_uri:
        hero = (
            f'<div style="position:relative;width:100%;max-height:200px;overflow:hidden;'
            f'background:linear-gradient(135deg,#003087 0%,#000d3a 100%);">'
            f'<img src="{logo_uri}" alt="Dreams2Memories Travel" '
            f'style="width:100%;max-height:200px;object-fit:cover;object-position:center 35%;display:block;" />'
            f'<div style="position:absolute;top:0;left:0;right:0;bottom:0;'
            f'background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,'
            f'rgba(0,48,135,0.35) 55%,rgba(0,13,58,0.82) 100%);"></div>'
            f'<div style="position:absolute;bottom:0;left:0;right:0;padding:14px 28px;text-align:center;">'
            f'<div style="color:#ffffff;font-family:Georgia,serif;font-size:18px;font-weight:bold;'
            f'letter-spacing:3px;text-transform:uppercase;text-shadow:0 2px 8px rgba(0,0,0,0.6);">'
            f'Dreams2Memories Travel</div>'
            f'<div style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;'
            f'letter-spacing:2px;text-transform:uppercase;margin-top:3px;font-style:italic;">'
            f'Curating the voyage of your lifetime</div>'
            f'</div>'
            f'</div>'
        )
    else:
        hero = (
            f'<div style="background:linear-gradient(135deg,#003087 0%,#001a5c 100%);'
            f'padding:36px 28px;text-align:center;">'
            f'<div style="color:#ffffff;font-family:Georgia,serif;font-size:20px;font-weight:bold;'
            f'letter-spacing:4px;text-transform:uppercase;">Dreams2Memories Travel</div>'
            f'<div style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;'
            f'letter-spacing:2px;text-transform:uppercase;margin-top:6px;font-style:italic;">'
            f'Curating the voyage of your lifetime</div>'
            f'</div>'
        )

    # ── SILVER DIVIDER ────────────────────────────────────────────────────────
    divider = (
        '<div style="height:3px;background:linear-gradient('
        '90deg,#003087,#A9B0B7,#ffffff,#A9B0B7,#003087);"></div>'
    )

    # ── LOGO SIG THUMBNAIL ────────────────────────────────────────────────────
    logo_sig = (
        f'<table cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;'
        f'padding-top:18px;border-top:2px solid #A9B0B7;width:100%;">'
        f'<tr><td style="width:90px;vertical-align:top;padding-right:14px;">'
        f'<img src="{logo_uri}" alt="D2M" style="width:80px;height:80px;'
        f'object-fit:cover;object-position:center;border-radius:6px;'
        f'border:2px solid #A9B0B7;display:block;" /></td>'
        f'<td style="vertical-align:middle;">'
        f'<div style="font-family:Georgia,serif;font-size:13px;font-weight:bold;'
        f'color:#003087;letter-spacing:2px;text-transform:uppercase;">D2M</div>'
        f'<div style="font-family:Georgia,serif;font-size:10px;color:#A9B0B7;'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-top:2px;">'
        f'Dreams2Memories Travel, LLC</div>'
        f'</td></tr></table>'
    ) if logo_uri else ''

    # ── FOOTER ────────────────────────────────────────────────────────────────
    footer = (
        '<div style="height:3px;background:linear-gradient('
        '90deg,#003087,#A9B0B7,#ffffff,#A9B0B7,#003087);"></div>'
        '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="background:linear-gradient(135deg,#001a5c 0%,#003087 100%);">'
        '<tr>'
        '<td style="padding:14px 28px;vertical-align:middle;">'
        '<span style="color:#ffffff;font-family:Georgia,serif;font-size:18px;'
        'font-weight:bold;letter-spacing:4px;">D<span style="color:#A9B0B7;">2</span>M</span>'
        '<br><span style="color:#A9B0B7;font-family:Georgia,serif;font-size:9px;'
        'letter-spacing:2px;text-transform:uppercase;">Dreams2Memories Travel, LLC</span>'
        '</td>'
        '<td style="padding:14px 28px;vertical-align:middle;text-align:right;">'
        '<a href="mailto:concierge@d2mluxury.quest" style="color:#ffffff;font-family:Georgia,serif;'
        'font-size:11px;text-decoration:none;letter-spacing:1px;">concierge@d2mluxury.quest</a>'
        '<br><span style="color:#A9B0B7;font-family:Georgia,serif;font-size:10px;">d2mluxury.quest</span>'
        '</td>'
        '</tr>'
        '</table>'
        '<div style="background:#000d3a;text-align:center;padding:6px;">'
        '<span style="color:rgba(169,176,183,0.6);font-family:Georgia,serif;font-size:9px;">'
        '&copy; 2026 Dreams2Memories Travel, LLC &nbsp;&middot;&nbsp; Colorado Springs, CO'
        '</span></div>'
        '<div style="height:3px;background:linear-gradient('
        '90deg,#A9B0B7,#ffffff,#A9B0B7,#ffffff,#A9B0B7);"></div>'
    )

    return (
        f'<div style="background-color:#1a1a2e;padding:0;margin:0;">'
        f'<div style="max-width:640px;margin:0 auto;">'
        f'{hero}'
        f'{divider}'
        f'<div style="background-color:#ffffff;border-left:2px solid #A9B0B7;'
        f'border-right:2px solid #A9B0B7;padding:32px 40px;">'
        f'<div style="color:#2c2c2c;font-family:Georgia,\'Times New Roman\',serif;'
        f'font-size:10.5pt;line-height:1.75;">'
        f'{html_body}'
        f'</div>'
        f'{_get_dani_sig_html() if persona_id == "A3" else ""}'
        f'{COMMANDER_SIGNATURE_HTML}'
        f'{logo_sig}'
        f'</div>'
        f'{footer}'
        f'</div>'
        f'</div>'
    )


def _extract_headers(headers, keys=None):
    """Extract specific headers from a Gmail message header list."""
    if keys is None:
        keys = {"From", "To", "Subject", "Date", "Cc", "Bcc"}
    return {h["name"]: h["value"] for h in headers if h["name"] in keys}


def register_gmail_tools(mcp):
    """Register all Gmail tools with the MCP server."""
    from mcp.server.fastmcp import FastMCP  # deferred — not needed by standalone importers

    @mcp.tool(
        name="gmail_search_messages",
        annotations={"title": "Search Gmail Messages", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_search_messages(
        query: str = Field(..., description="Gmail search query (same syntax as Gmail search bar, e.g. 'from:silversea subject:confirmation')"),
        max_results: int = Field(10, description="Max messages to return (1-50)"),
    ) -> str:
        """Search Gmail messages using standard Gmail query syntax."""
        try:
            service = _get_gmail_service()
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=min(max_results, 50))
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return json.dumps({"status": "success", "query": query, "count": 0, "messages": []}, indent=2)

            # Fetch summary metadata for each message
            summaries = []
            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"])
                    .execute()
                )
                headers = _extract_headers(msg.get("payload", {}).get("headers", []))
                summaries.append({
                    "id": msg["id"],
                    "threadId": msg["threadId"],
                    "snippet": msg.get("snippet", ""),
                    "labels": msg.get("labelIds", []),
                    **headers,
                })

            return json.dumps({"status": "success", "query": query, "count": len(summaries), "messages": summaries}, indent=2)

        except HttpError as e:
            logger.error(f"Gmail search error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except RuntimeError as e:
            return json.dumps({"error": str(e), "type": "auth_error"})
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_read_message",
        annotations={"title": "Read Gmail Message", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_read_message(
        message_id: str = Field(..., description="Gmail message ID (from search results)"),
    ) -> str:
        """Read the full content of a specific Gmail message."""
        try:
            service = _get_gmail_service()
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = _extract_headers(payload.get("headers", []))
            body = _decode_body(payload)

            # Truncate very long emails
            if len(body) > 30000:
                body = body[:30000] + "\n\n... [TRUNCATED — email exceeds 30K chars]"

            # Extract attachment info (don't download, just list)
            attachments = []
            for part in payload.get("parts", []):
                if part.get("filename"):
                    attachments.append({
                        "filename": part["filename"],
                        "mimeType": part.get("mimeType", "unknown"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": part.get("body", {}).get("attachmentId", ""),
                    })

            return json.dumps({
                "status": "success",
                "id": msg["id"],
                "threadId": msg["threadId"],
                "labels": msg.get("labelIds", []),
                **headers,
                "body": body,
                "attachments": attachments,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail read error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail read error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_read_thread",
        annotations={"title": "Read Gmail Thread", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_read_thread(
        thread_id: str = Field(..., description="Gmail thread ID"),
    ) -> str:
        """Read all messages in a Gmail thread."""
        try:
            service = _get_gmail_service()
            thread = (
                service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )

            messages = []
            for msg in thread.get("messages", []):
                payload = msg.get("payload", {})
                headers = _extract_headers(payload.get("headers", []))
                body = _decode_body(payload)
                if len(body) > 15000:
                    body = body[:15000] + "\n\n... [TRUNCATED]"
                messages.append({
                    "id": msg["id"],
                    **headers,
                    "snippet": msg.get("snippet", ""),
                    "body": body,
                })

            return json.dumps({
                "status": "success",
                "threadId": thread_id,
                "message_count": len(messages),
                "messages": messages,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail thread error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail thread error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_list_drafts",
        annotations={"title": "List Gmail Drafts", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_list_drafts(
        max_results: int = Field(10, description="Max drafts to return (1-25)"),
    ) -> str:
        """List existing Gmail drafts."""
        try:
            service = _get_gmail_service()
            results = (
                service.users()
                .drafts()
                .list(userId="me", maxResults=min(max_results, 25))
                .execute()
            )

            drafts = results.get("drafts", [])
            if not drafts:
                return json.dumps({"status": "success", "count": 0, "drafts": []}, indent=2)

            draft_summaries = []
            for draft_ref in drafts:
                draft = (
                    service.users()
                    .drafts()
                    .get(userId="me", id=draft_ref["id"], format="metadata")
                    .execute()
                )
                msg = draft.get("message", {})
                headers = _extract_headers(msg.get("payload", {}).get("headers", []))
                draft_summaries.append({
                    "draft_id": draft["id"],
                    "message_id": msg.get("id", ""),
                    "snippet": msg.get("snippet", ""),
                    **headers,
                })

            return json.dumps({"status": "success", "count": len(draft_summaries), "drafts": draft_summaries}, indent=2)

        except HttpError as e:
            logger.error(f"Gmail drafts error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail drafts error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_create_draft",
        annotations={"title": "Create Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_create_draft(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
        bcc: Optional[str] = Field(None, description="BCC recipients (comma-separated)"),
        reply_to_message_id: Optional[str] = Field(None, description="Message ID to reply to (creates reply draft)"),
        attachment_paths: Optional[List[str]] = Field(None, description="List of absolute file paths to attach (e.g. PDFs, images)"),
        from_persona: Optional[str] = Field(None, description="Persona ID (e.g. 'A3', 'CONCIERGE') — sets From to persona display name via concierge@d2mluxury.quest"),
    ) -> str:
        """Create a Gmail draft with optional file attachments. Does NOT send — saves as draft for review.

        This is intentionally draft-only for safety. John reviews and sends manually.
        Supports multiple attachments — pass a list of absolute file paths.
        When from_persona is set, uses the D2M persona display name with concierge@d2mluxury.quest as the From address.
        """
        try:
            service = _get_gmail_service()

            # Build body part: plain text + HTML with Commander's blue ink
            # _wrap_body_html inlines CSS via premailer when given a full HTML doc
            html_part = _wrap_body_html(body, persona_id=from_persona)
            # Plain text: strip HTML tags if body is an HTML document; otherwise use as-is
            stripped = body.strip()
            if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
                plain_part = _strip_html(stripped)
            else:
                plain_part = body
            body_part = MIMEMultipart("alternative")
            body_part.attach(MIMEText(plain_part, "plain"))
            body_part.attach(MIMEText(html_part, "html"))

            # If attachments, wrap in mixed; otherwise alternative is the root
            attached_files = []
            if attachment_paths:
                message = MIMEMultipart("mixed")
                message.attach(body_part)
                for file_path_str in attachment_paths:
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        return json.dumps({"error": f"Attachment not found: {file_path}", "type": "file_error"})
                    if not file_path.is_file():
                        return json.dumps({"error": f"Not a file: {file_path}", "type": "file_error"})

                    content_type, _ = mimetypes.guess_type(str(file_path))
                    if content_type is None:
                        content_type = "application/octet-stream"
                    main_type, sub_type = content_type.split("/", 1)

                    with open(file_path, "rb") as f:
                        att = MIMEBase(main_type, sub_type)
                        att.set_payload(f.read())
                    encoders.encode_base64(att)
                    att.add_header("Content-Disposition", "attachment", filename=file_path.name)
                    message.attach(att)
                    attached_files.append(file_path.name)
            else:
                message = body_part

            message["to"] = to

            # Set From based on persona
            if from_persona and from_persona.upper() in PERSONA_DISPLAY_NAMES:
                pid = from_persona.upper()
                display_name = PERSONA_DISPLAY_NAMES[pid]
                from_addr = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS
                message["from"] = f'"{display_name}" <{from_addr}>'
                message["reply-to"] = COMMANDER_EMAIL
            else:
                message["from"] = USER_EMAIL

            message["subject"] = subject
            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            draft_body = {"message": {"raw": raw}}

            if reply_to_message_id:
                # Get the thread ID from the original message
                orig = (
                    service.users()
                    .messages()
                    .get(userId="me", id=reply_to_message_id, format="minimal")
                    .execute()
                )
                draft_body["message"]["threadId"] = orig.get("threadId", "")

            draft = (
                service.users()
                .drafts()
                .create(userId="me", body=draft_body)
                .execute()
            )

            result = {
                "status": "success",
                "action": "draft_created",
                "draft_id": draft["id"],
                "to": to,
                "subject": subject,
                "note": "Draft saved — NOT sent. Review in Gmail before sending.",
            }
            if attached_files:
                result["attachments"] = attached_files
                result["attachment_count"] = len(attached_files)

            return json.dumps(result, indent=2)

        except HttpError as e:
            logger.error(f"Gmail draft create error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail draft create error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_get_profile",
        annotations={"title": "Get Gmail Profile", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_get_profile() -> str:
        """Get Gmail profile info. Useful as a connectivity test."""
        try:
            service = _get_gmail_service()
            profile = service.users().getProfile(userId="me").execute()
            return json.dumps({
                "status": "success",
                "email": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal"),
                "threads_total": profile.get("threadsTotal"),
                "history_id": profile.get("historyId"),
            }, indent=2)
        except HttpError as e:
            logger.error(f"Gmail profile error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except RuntimeError as e:
            return json.dumps({"error": str(e), "type": "auth_error"})
        except Exception as e:
            logger.error(f"Gmail profile error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    # ------------------------------------------------------------------
    # DRAFT APPROVAL — promote draft to sent, or update draft content
    # ------------------------------------------------------------------

    @mcp.tool(
        name="gmail_send_draft",
        annotations={"title": "Send Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_send_draft(
        draft_id: str = Field(..., description="Gmail draft ID (from gmail_list_drafts or draft creation)"),
    ) -> str:
        """Send an existing Gmail draft. Promotes a draft to a sent message.

        Used by the Commander approval flow: Dani creates draft → Commander approves → COS sends.
        WARNING: This SENDS the email. Use only after Commander approval.
        """
        try:
            service = _get_gmail_service()

            # Fetch the draft body before sending for diff capture
            sent_body = None
            try:
                draft_data = service.users().drafts().get(
                    userId="me", id=draft_id, format="full"
                ).execute()
                sent_body = _decode_body(draft_data.get("message", {}).get("payload", {}))
            except Exception:
                pass  # Non-critical — diff capture is best-effort

            sent = (
                service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            # Log the send action
            msg_id = sent.get("id", "unknown")
            _log_email_action(
                to="(from draft)", subject="(from draft)",
                persona_id="APPROVED", auto_send=True, ref_id=msg_id,
            )

            # After successful send, capture diff for learning compiler
            try:
                from thunderbird_learning import capture_email_diff
                original_body = _pop_cached_draft_body(draft_id)
                if original_body and sent_body and original_body != sent_body:
                    capture_email_diff(
                        original_body, sent_body,
                        context="Commander edited draft before sending",
                        source="gmail_send",
                    )
            except Exception:
                pass  # Learning capture is non-critical — never block sends

            return json.dumps({
                "status": "success",
                "action": "draft_sent",
                "message_id": msg_id,
                "draft_id": draft_id,
                "labels": sent.get("labelIds", []),
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail send draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail send draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    # ------------------------------------------------------------------
    # DIRECT SEND — compose and send in one step (bypasses draft stage)
    # ------------------------------------------------------------------

    @mcp.tool(
        name="gmail_send_email",
        annotations={"title": "Send Email via Gmail", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_send_email(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
        bcc: Optional[str] = Field(None, description="BCC recipients (comma-separated)"),
        from_persona: Optional[str] = Field(
            None,
            description="Persona ID (e.g. 'A3', 'CONCIERGE', 'COMMANDER') — sets From display name. "
                        "Defaults to concierge@d2mluxury.quest; COMMANDER uses john@d2mluxury.quest",
        ),
        html_body: Optional[str] = Field(
            None,
            description="Optional HTML email body. If provided, sends as HTML with plain text fallback.",
        ),
        reply_to_message_id: Optional[str] = Field(
            None,
            description="Message ID to reply to (threads the conversation)",
        ),
        commander_approved: bool = Field(
            False,
            description="WF17 APPROVAL GATE: Set True ONLY when the Commander has explicitly "
                        "approved this send via Telegram /drafts flow or direct order. "
                        "When False (default), email is saved as a draft for Commander review.",
        ),
    ) -> str:
        """Send an email via Gmail — subject to WF17 approval gate.

        DEFAULT BEHAVIOR: Creates a draft, applies THUNDERBIRD-Commander-Review label,
        and returns draft_id for Commander review via Telegram. Does NOT send.

        ONLY when commander_approved=True does this send immediately. That flag
        should be set exclusively when:
          - Commander explicitly orders "send this now" via Telegram or CLI
          - Commander approves a draft via the /drafts Telegram approval flow
          - An internal-only email (staff, not client-facing)

        Uses D2M persona display names and concierge@d2mluxury.quest as From address.
        Reply-To is always set to johnloucks3@gmail.com so client replies reach the Commander.
        """
        try:
            service = _get_gmail_service()

            # Build MIME message — always include HTML for blue ink color
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html_body if html_body else _wrap_body_html(body), "html"))

            message["to"] = to
            message["subject"] = subject

            # Set From based on persona
            if from_persona and from_persona.upper() in PERSONA_DISPLAY_NAMES:
                pid = from_persona.upper()
                display_name = PERSONA_DISPLAY_NAMES[pid]
                from_addr = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS
                message["from"] = f'"{display_name}" <{from_addr}>'
            else:
                # Default: Dani as concierge
                message["from"] = f'"{PERSONA_DISPLAY_NAMES["CONCIERGE"]}" <{D2M_FROM_ADDRESS}>'

            message["reply-to"] = COMMANDER_EMAIL

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            # Thread support — reply to existing conversation
            thread_id_for_msg = ""
            if reply_to_message_id:
                try:
                    orig = (
                        service.users()
                        .messages()
                        .get(userId="me", id=reply_to_message_id, format="metadata",
                             metadataHeaders=["Message-ID", "Subject"])
                        .execute()
                    )
                    orig_headers = {h["name"]: h["value"] for h in orig.get("payload", {}).get("headers", [])}
                    if orig_headers.get("Message-ID"):
                        message["In-Reply-To"] = orig_headers["Message-ID"]
                        message["References"] = orig_headers["Message-ID"]
                    thread_id_for_msg = orig.get("threadId", "")
                except Exception as thread_err:
                    logger.warning(f"Could not thread reply: {thread_err}")

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # ── WF17 APPROVAL GATE ──────────────────────────────────────
            # DEFAULT: stage as draft → label → notify Commander
            # OVERRIDE: commander_approved=True → send immediately
            if not commander_approved:
                logger.info(f"WF17 GATE: staging draft for Commander review — to={to} subj={subject[:60]}")
                draft_body = {"message": {"raw": raw}}
                if thread_id_for_msg:
                    draft_body["message"]["threadId"] = thread_id_for_msg

                draft = (
                    service.users()
                    .drafts()
                    .create(userId="me", body=draft_body)
                    .execute()
                )
                draft_id = draft.get("id", "unknown")

                # Tag with THUNDERBIRD-Commander-Review label
                try:
                    draft_msg_id = draft.get("message", {}).get("id")
                    if draft_msg_id:
                        _tag_commander_review(service, draft_msg_id)
                except Exception as e:
                    logger.warning(f"Failed to tag draft with review label: {e}")

                # Cache original AI-generated body for learning diff at send time
                _cache_draft_body(draft_id, body)

                pid_used = (from_persona or "CONCIERGE").upper()
                _log_email_action(
                    to=to, subject=subject,
                    persona_id=pid_used, auto_send=False, ref_id=draft_id,
                )

                return json.dumps({
                    "status": "success",
                    "action": "draft_created",
                    "draft_id": draft_id,
                    "from_persona": pid_used,
                    "from_display": PERSONA_DISPLAY_NAMES.get(pid_used, "D2M Concierge"),
                    "to": to,
                    "subject": subject,
                    "note": "WF17: Draft staged for Commander review. NOT sent. "
                            "Commander must approve via Telegram /drafts flow.",
                }, indent=2)

            # ── COMMANDER APPROVED — internal addresses only ─────────────
            # Extract bare email from "Display Name <email>" format if needed
            _to_bare = to.strip().lower()
            _m = __import__("re").search(r"<([^>]+)>", _to_bare)
            if _m:
                _to_bare = _m.group(1).strip()
            if _to_bare not in {a.lower() for a in COMMANDER_ADDRS}:
                # External send permanently blocked — stage as draft instead
                logger.warning("EXT SEND GUARD: blocking send to %s — staging as draft", to)
                draft_body = {"message": {"raw": raw}}
                if thread_id_for_msg:
                    draft_body["message"]["threadId"] = thread_id_for_msg
                draft = (
                    service.users().drafts().create(userId="me", body=draft_body).execute()
                )
                draft_id = draft.get("id", "unknown")
                return json.dumps({
                    "status": "blocked",
                    "action": "draft_created",
                    "draft_id": draft_id,
                    "to": to,
                    "subject": subject,
                    "note": "External send permanently prohibited. Only Commander addresses "
                            "(johnloucks3/johnloucks75/d2mluxury.quest) may receive direct sends. "
                            "Draft staged in d2mconcierge for review.",
                }, indent=2)

            # All clear — send immediately ───────────────────────────────
            send_body = {"raw": raw}
            if thread_id_for_msg:
                send_body["threadId"] = thread_id_for_msg

            sent = (
                service.users()
                .messages()
                .send(userId="me", body=send_body)
                .execute()
            )

            msg_id = sent.get("id", "unknown")
            pid_used = (from_persona or "CONCIERGE").upper()
            _log_email_action(
                to=to, subject=subject,
                persona_id=pid_used, auto_send=True, ref_id=msg_id,
            )

            return json.dumps({
                "status": "success",
                "action": "sent",
                "message_id": msg_id,
                "thread_id": sent.get("threadId", ""),
                "from_persona": pid_used,
                "from_display": PERSONA_DISPLAY_NAMES.get(pid_used, "D2M Concierge"),
                "to": to,
                "subject": subject,
                "labels": sent.get("labelIds", []),
                "note": "Commander-approved send.",
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail send email error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail send email error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_update_draft",
        annotations={"title": "Update Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_update_draft(
        draft_id: str = Field(..., description="Gmail draft ID to update"),
        body: Optional[str] = Field(None, description="New email body text (replaces existing body)"),
        subject: Optional[str] = Field(None, description="New subject line (replaces existing)"),
    ) -> str:
        """Update an existing Gmail draft's body or subject.

        Used when Commander edits a Dani draft before approving.
        Preserves all other fields (to, from, cc, attachments).
        """
        try:
            service = _get_gmail_service()

            # Fetch the existing draft to preserve fields
            existing = (
                service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
                .execute()
            )
            msg = existing.get("message", {})
            payload = msg.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            # Build updated message preserving original fields
            updated = MIMEMultipart()
            updated["to"] = headers.get("To", "")
            updated["from"] = headers.get("From", USER_EMAIL)
            if headers.get("Cc"):
                updated["cc"] = headers["Cc"]
            if headers.get("Bcc"):
                updated["bcc"] = headers["Bcc"]
            if headers.get("Reply-To"):
                updated["reply-to"] = headers["Reply-To"]
            if headers.get("In-Reply-To"):
                updated["In-Reply-To"] = headers["In-Reply-To"]
            if headers.get("References"):
                updated["References"] = headers["References"]

            updated["subject"] = subject if subject else headers.get("Subject", "")

            # Use new body if provided, otherwise keep existing
            # Always attach both plain + HTML (stationery) for consistency
            if body:
                alt = MIMEMultipart("alternative")
                alt.attach(MIMEText(body, "plain"))
                alt.attach(MIMEText(_wrap_body_html(body), "html"))
                updated.attach(alt)
            else:
                existing_body = _decode_body(payload)
                alt = MIMEMultipart("alternative")
                alt.attach(MIMEText(existing_body, "plain"))
                alt.attach(MIMEText(_wrap_body_html(existing_body), "html"))
                updated.attach(alt)

            raw = base64.urlsafe_b64encode(updated.as_bytes()).decode("utf-8")
            draft_body = {"message": {"raw": raw}}

            # Preserve thread ID if it was a reply
            thread_id = msg.get("threadId")
            if thread_id:
                draft_body["message"]["threadId"] = thread_id

            result = (
                service.users()
                .drafts()
                .update(userId="me", id=draft_id, body=draft_body)
                .execute()
            )

            return json.dumps({
                "status": "success",
                "action": "draft_updated",
                "draft_id": result.get("id", draft_id),
                "subject": updated["subject"],
                "to": updated["to"],
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail update draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail update draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_delete_draft",
        annotations={"title": "Delete Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_delete_draft(
        draft_id: str = Field(..., description="Gmail draft ID to delete"),
    ) -> str:
        """Delete a Gmail draft. Used for draft hygiene — removing superseded or stale drafts."""
        try:
            service = _get_gmail_service()
            service.users().drafts().delete(userId="me", id=draft_id).execute()
            return json.dumps({
                "status": "success",
                "action": "draft_deleted",
                "draft_id": draft_id,
            }, indent=2)
        except HttpError as e:
            logger.error(f"Gmail delete draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail delete draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    # ------------------------------------------------------------------
    # SEND AS PERSONA — sends email directly via Gmail API
    # ------------------------------------------------------------------

    @mcp.tool(
        name="send_client_email",
        annotations={"title": "Send Email as D2M Persona", "readOnlyHint": False},
    )
    @_retry_on_error
    async def send_client_email(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        persona_id: str = Field("CONCIERGE", description="Persona ID: COS, EXEC, A2, A3, A5, A6, A9, A10, CH, A12, D2M, CONCIERGE"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
    ) -> str:
        """WF17 APPROVAL GATE — stages email for Commander approval. Never sends directly.

        Creates a Gmail draft, tags it THUNDERBIRD-Commander-Review, and immediately
        pushes a Telegram notification to Commander with Preview / Approve & Send / Reject buttons.
        The only path to actual sending is Commander pressing ✅ Approve in Telegram or /drafts.

        Use this for ALL client-facing emails. There is no bypass.
        """
        return await _send_or_draft_as_persona(
            service=_get_gmail_service(),
            to=to, subject=subject, body=body,
            persona_id=persona_id, cc=cc,
            auto_send=False,   # WF17 hard gate — no model call can override this
        )

    @mcp.tool(
        name="draft_client_email",
        annotations={"title": "Draft Email as D2M Persona", "readOnlyHint": False},
    )
    @_retry_on_error
    async def draft_client_email(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        persona_id: str = Field("CONCIERGE", description="Persona ID: COS, EXEC, A2, A3, A5, A6, A9, A10, CH, A12, D2M, CONCIERGE"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
    ) -> str:
        """Create a draft email as a D2M persona for Commander review before sending.

        Uses Gmail Send As with the persona display name via concierge@d2mluxury.quest.
        Reply-To is set to johnloucks3@gmail.com. Draft is NOT sent — Commander reviews in Gmail.
        """
        return await _send_or_draft_as_persona(
            service=_get_gmail_service(),
            to=to, subject=subject, body=body,
            persona_id=persona_id, cc=cc,
            auto_send=False,
        )

    # ── Email Management Tools (label/thread operations) ──

    @mcp.tool(
        name="gmail_create_label",
        annotations={"title": "Create Gmail Label", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_create_label(
        name: str = Field(..., description="Label name (use '/' for nesting, e.g. 'D2M/Clients')"),
    ) -> str:
        """Create a new Gmail label. Supports nested labels with '/' separator."""
        try:
            service = _get_gmail_service()
            # Check if already exists
            results = service.users().labels().list(userId="me").execute()
            for label in results.get("labels", []):
                if label["name"] == name:
                    return json.dumps({"status": "exists", "label_id": label["id"], "name": name})
            body = {
                "name": name,
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
            }
            created = service.users().labels().create(userId="me", body=body).execute()
            return json.dumps({"status": "created", "label_id": created["id"], "name": name})
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(
        name="gmail_delete_label",
        annotations={"title": "Delete Gmail Label", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_delete_label(
        label_id: str = Field(..., description="Label ID to delete (from gmail_list_labels)"),
    ) -> str:
        """Delete a Gmail label. Does NOT delete messages — just removes the label."""
        try:
            service = _get_gmail_service()
            service.users().labels().delete(userId="me", id=label_id).execute()
            return json.dumps({"status": "deleted", "label_id": label_id})
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(
        name="gmail_modify_message",
        annotations={"title": "Modify Gmail Message Labels", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_modify_message(
        message_id: str = Field(..., description="Gmail message ID"),
        add_labels: Optional[str] = Field(None, description="Comma-separated label IDs to add"),
        remove_labels: Optional[str] = Field(None, description="Comma-separated label IDs to remove (use 'INBOX' to archive)"),
    ) -> str:
        """Add or remove labels on a Gmail message. Remove 'INBOX' to archive."""
        try:
            service = _get_gmail_service()
            body = {}
            if add_labels:
                _add = add_labels if isinstance(add_labels, list) else [lid.strip() for lid in str(add_labels).split(",")]
                body["addLabelIds"] = _add
            if remove_labels:
                _rem = remove_labels if isinstance(remove_labels, list) else [lid.strip() for lid in str(remove_labels).split(",")]
                body["removeLabelIds"] = _rem
            result = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
            return json.dumps({"status": "success", "message_id": message_id, "labels": result.get("labelIds", [])})
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(
        name="gmail_modify_thread",
        annotations={"title": "Modify Gmail Thread Labels", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_modify_thread(
        thread_id: str = Field(..., description="Gmail thread ID"),
        add_labels: Optional[str] = Field(None, description="Comma-separated label IDs to add"),
        remove_labels: Optional[str] = Field(None, description="Comma-separated label IDs to remove (use 'INBOX' to archive)"),
    ) -> str:
        """Add or remove labels on an entire Gmail thread. Remove 'INBOX' to archive."""
        try:
            service = _get_gmail_service()
            body = {}
            if add_labels:
                body["addLabelIds"] = [lid.strip() for lid in add_labels.split(",")]
            if remove_labels:
                body["removeLabelIds"] = [lid.strip() for lid in remove_labels.split(",")]
            result = service.users().threads().modify(userId="me", id=thread_id, body=body).execute()
            return json.dumps({"status": "success", "thread_id": thread_id, "thread_id_out": result.get("id", "")})
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(
        name="gmail_trash_message",
        annotations={"title": "Trash Gmail Message", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_trash_message(
        message_id: str = Field(..., description="Gmail message ID to trash"),
    ) -> str:
        """Move a Gmail message to trash. Recoverable for 30 days."""
        try:
            service = _get_gmail_service()
            service.users().messages().trash(userId="me", id=message_id).execute()
            return json.dumps({"status": "trashed", "message_id": message_id})
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    @mcp.tool(
        name="gmail_list_labels",
        annotations={"title": "List Gmail Labels", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_list_labels() -> str:
        """List all Gmail labels (system and user-created) with their IDs."""
        try:
            service = _get_gmail_service()
            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            user_labels = [
                {"id": l["id"], "name": l["name"], "type": l.get("type", "")}
                for l in labels
            ]
            return json.dumps({"status": "success", "count": len(user_labels), "labels": user_labels}, indent=2)
        except HttpError as e:
            return json.dumps({"status": "error", "error": str(e)})

    logger.info("Gmail tools registered successfully (including Send As persona tools + email management)")


async def _send_or_draft_as_persona(
    service, to: str, subject: str, body: str,
    persona_id: str = "CONCIERGE", cc: Optional[str] = None,
    auto_send: bool = False,
) -> str:
    """Internal helper: build a persona email and either send or save as draft.

    Args:
        service: Gmail API service instance
        to: Recipient email
        subject: Subject line
        body: Plain text body
        persona_id: Key into PERSONA_DISPLAY_NAMES
        cc: Optional CC addresses
        auto_send: True = send immediately, False = create draft for review
    """
    try:
        pid = persona_id.upper()
        display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
        from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

        message = MIMEMultipart("alternative")
        message["to"] = to
        message["from"] = f'"{display_name}" <{from_address}>'
        message["reply-to"] = COMMANDER_EMAIL
        message["subject"] = subject
        if cc:
            message["cc"] = cc

        # Plain text fallback + HTML with Commander's blue ink color
        message.attach(MIMEText(body, "plain"))
        message.attach(MIMEText(_wrap_body_html(body), "html"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        if auto_send:
            sent = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            action = "sent"
            ref_id = sent.get("id", "unknown")
        else:
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            action = "draft_created"
            ref_id = draft.get("id", "unknown")

            # Tag draft with THUNDERBIRD-Commander-Review for /drafts approval flow
            try:
                draft_msg_id = draft.get("message", {}).get("id")
                if draft_msg_id:
                    _tag_commander_review(service, draft_msg_id)
            except Exception as e:
                logger.warning(f"Failed to tag draft with review label: {e}")

            # Cache original AI-generated body for learning diff at send time
            _cache_draft_body(ref_id, body)

            # WF17 — push Telegram notification so Commander doesn't need to poll /drafts
            try:
                _push_telegram_draft_alert(
                    draft_id=ref_id,
                    message_id=draft.get("message", {}).get("id", ""),
                    to=to,
                    subject=subject,
                    body_full=body,
                    persona_display=display_name,
                )
            except Exception as e:
                logger.warning(f"WF17 Telegram push failed: {e}")

        # Log the action
        _log_email_action(
            to=to, subject=subject, persona_id=pid,
            auto_send=auto_send, ref_id=ref_id,
        )

        result = {
            "status": "success",
            "action": action,
            "id": ref_id,
            "from_persona": pid,
            "from_display": display_name,
            "from_address": from_address,
            "reply_to": COMMANDER_EMAIL,
            "to": to,
            "subject": subject,
        }
        if not auto_send:
            result["note"] = "Draft saved — NOT sent. Review in Gmail before sending."

        return json.dumps(result, indent=2)

    except HttpError as e:
        logger.error(f"Gmail persona email error: {e}")
        return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
    except Exception as e:
        logger.error(f"Gmail persona email error: {e}")
        return json.dumps({"error": str(e), "type": "gmail_error"})


COMMANDER_REVIEW_LABEL = "THUNDERBIRD-Commander-Review"
_review_label_id_cache: str = ""


def _tag_commander_review(service, message_id: str):
    """Add the THUNDERBIRD-Commander-Review label to a draft message."""
    global _review_label_id_cache
    if not _review_label_id_cache:
        results = service.users().labels().list(userId="me").execute()
        for lbl in results.get("labels", []):
            if lbl["name"] == COMMANDER_REVIEW_LABEL:
                _review_label_id_cache = lbl["id"]
                break
        if not _review_label_id_cache:
            body = {
                "name": COMMANDER_REVIEW_LABEL,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=body).execute()
            _review_label_id_cache = created["id"]
            logger.info(f"Created Gmail label: {COMMANDER_REVIEW_LABEL}")

    service.users().messages().modify(
        userId="me", id=message_id,
        body={"addLabelIds": [_review_label_id_cache]},
    ).execute()


def _push_telegram_draft_alert(
    draft_id: str, message_id: str,
    to: str, subject: str, body_full: str,
    persona_display: str,
) -> None:
    """Push the complete draft to Commander via Telegram when staged for approval.

    Sends the full email body — no truncation.
    Splits into multiple messages if body exceeds Telegram's 4096-char limit.
    Buttons (Preview / Approve & Send / Reject) always appear on the last message.
    Failure is silent — draft is already saved in Gmail.
    """
    import urllib.request
    import json as _json
    import re as _re

    poe_env = THUNDERBIRD_DIR / "config" / "poe.env"
    bot_token = ""
    chat_id   = ""
    if poe_env.exists():
        for line in poe_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                bot_token = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_COMMANDER_ID="):
                chat_id = line.split("=", 1)[1].strip()

    if not bot_token or not chat_id:
        logger.warning("WF17 Telegram push skipped — no bot token/chat_id in poe.env")
        return

    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def _send(text: str, keyboard: dict | None = None) -> None:
        body: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if keyboard:
            body["reply_markup"] = keyboard
        payload = _json.dumps(body).encode()
        req = urllib.request.Request(tg_url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=8)

    # Strip HTML tags from email body for clean Telegram display
    clean_body = _re.sub(r"<[^>]+>", "", body_full).strip()

    # Gmail compose deep-link
    gmail_link = ""
    if message_id:
        gmail_link = f"\n<a href=\"https://mail.google.com/mail/b/{USER_EMAIL}/#drafts/{message_id}\">Open in Gmail ↗</a>"

    header = (
        f"📧 <b>Draft Staged for Approval</b> — WF17\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>From:</b> {persona_display}\n"
        f"<b>To:</b> {to}\n"
        f"<b>Subject:</b> {subject}"
        f"{gmail_link}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    keyboard: dict = {
        "inline_keyboard": [
            [
                {"text": "👁 Preview",         "callback_data": f"draft_preview:{draft_id}"},
                {"text": "✅ Approve & Send",   "callback_data": f"draft_approve:{draft_id}"},
            ],
            [
                {"text": "❌ Reject & Delete",  "callback_data": f"draft_reject:{draft_id}"},
                {"text": "💬 Comment",          "callback_data": f"draft_comment:{draft_id}"},
            ],
        ]
    }
    if message_id:
        keyboard["inline_keyboard"].append([
            {"text": "📝 Edit in Gmail", "url": f"https://mail.google.com/mail/b/{USER_EMAIL}/#drafts/{message_id}"},
        ])

    TG_LIMIT = 4096

    try:
        # Fit header + as much body as possible in the first message
        first_chunk_capacity = TG_LIMIT - len(header) - 10
        if len(clean_body) <= first_chunk_capacity:
            # Entire email fits in one message — send with buttons
            _send(header + clean_body, keyboard)
        else:
            # Split: first message = header + partial body, continuation(s) follow
            _send(header + clean_body[:first_chunk_capacity])
            remaining = clean_body[first_chunk_capacity:]
            while remaining:
                chunk = remaining[:TG_LIMIT]
                remaining = remaining[TG_LIMIT:]
                # Attach buttons to the final chunk only
                _send(chunk, keyboard if not remaining else None)

        logger.info("WF17 Telegram draft alert sent for draft_id=%s (%d chars)", draft_id, len(clean_body))
    except Exception as e:
        logger.warning("WF17 Telegram push failed (draft still saved): %s", e)


def _log_email_action(to: str, subject: str, persona_id: str, auto_send: bool, ref_id: str):
    """Append a line to ~/Thunderbird/logs/email_sent.log."""
    try:
        EMAIL_SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        mode = "SENT" if auto_send else "DRAFT"
        line = f"[{ts}] {mode} | persona={persona_id} | to={to} | subject={subject} | id={ref_id}\n"
        with open(EMAIL_SENT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Failed to write email log: {e}")


def _cache_draft_body(draft_id: str, body: str) -> None:
    """Store the AI-generated original body for a draft, keyed by draft_id.

    Used by the learning compiler: when Commander edits a draft before sending,
    we diff the original AI body vs the sent body to extract voice principles.
    """
    try:
        DRAFT_BODY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        cache: dict = {}
        if DRAFT_BODY_CACHE.exists():
            cache = json.loads(DRAFT_BODY_CACHE.read_text(encoding="utf-8"))
        cache[draft_id] = body
        # Keep cache bounded — prune entries older than 200
        if len(cache) > 200:
            keys = list(cache.keys())
            for k in keys[:-200]:
                del cache[k]
        DRAFT_BODY_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Draft body cache write failed (non-critical): {e}")


def _pop_cached_draft_body(draft_id: str) -> Optional[str]:
    """Retrieve and remove the original AI-generated body for a draft."""
    try:
        if not DRAFT_BODY_CACHE.exists():
            return None
        cache = json.loads(DRAFT_BODY_CACHE.read_text(encoding="utf-8"))
        body = cache.pop(draft_id, None)
        if body is not None:
            DRAFT_BODY_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        return body
    except Exception:
        return None


# ============================================================================
# Standalone convenience functions (importable without MCP)
# ============================================================================

def gmail_send_from_wing(
    to: str, subject: str, body: str,
    persona_id: str = "COS", cc: Optional[str] = None,
) -> dict:
    """Send staff→Commander email FROM d2mconcierge@gmail.com (Wing inbox).

    PRIMARY channel for all persona→Commander internal communications.
    COS→Commander stays on Telegram — use this for A2, A3, EXEC, A5, A9 etc.
    Client emails: use gmail_send_as_persona() via concierge@ instead.
    """
    service = _get_wing_gmail_service()
    pid = persona_id.upper()
    display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES.get("D2M", "D2M Wing"))

    html_body = _wrap_staff_html(body, pid)
    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["from"] = f'"{display_name}" <{WING_GMAIL_ADDRESS}>'
    msg["reply-to"] = WING_GMAIL_ADDRESS
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    _log_email_action(to=to, subject=subject, persona_id=pid, auto_send=True, ref_id=result.get("id", ""))
    return {
        "status": "success",
        "action": "sent",
        "message_id": result.get("id"),
        "from": f"{display_name} <{WING_GMAIL_ADDRESS}>",
        "to": to,
        "subject": subject,
    }


def gmail_send_as_persona(to: str, subject: str, body: str, persona_id: str = "CONCIERGE", cc: Optional[str] = None) -> dict:
    """Synchronous wrapper: send an email as a D2M persona.

    Builds the email with the persona display name as From,
    uses concierge@d2mluxury.quest (or john@d2mluxury.quest for COMMANDER),
    sets Reply-To to johnloucks3@gmail.com,
    and SENDS via Gmail API. Returns dict with message ID and confirmation.
    """
    if SEND_LOCKOUT:
        return {
            "status": "blocked",
            "error": "SEND LOCKOUT active (Commander directive 2026-03-18). "
                     "All AI send privileges revoked. Commander must send manually.",
            "to": to, "subject": subject,
        }

    service = _get_gmail_service()
    pid = persona_id.upper()
    display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
    from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

    message = MIMEMultipart()
    message["to"] = to
    message["from"] = f'"{display_name}" <{from_address}>'
    message["reply-to"] = COMMANDER_EMAIL
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    message.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    _log_email_action(to=to, subject=subject, persona_id=pid, auto_send=True, ref_id=sent.get("id", "unknown"))

    return {
        "status": "success",
        "action": "sent",
        "message_id": sent.get("id"),
        "from_persona": pid,
        "from_display": display_name,
        "from_address": from_address,
        "reply_to": COMMANDER_EMAIL,
        "to": to,
        "subject": subject,
    }


def gmail_send_with_approval(
    to: str, subject: str, body: str,
    persona_id: str = "CONCIERGE", auto_send: bool = False,
    cc: Optional[str] = None,
) -> dict:
    """Safety gate: send or draft based on recipient and auto_send flag.

    Routing logic (Commander directive 2026-03-18):
    - TO Commander address: always send directly — no draft staging
    - TO client/vendor:     auto_send=True sends, False (default) creates draft for review
    - Always logs to ~/Thunderbird/logs/email_sent.log
    """
    to_lower = to.lower()
    if any(addr in to_lower for addr in COMMANDER_ADDRS):
        auto_send = True  # Commander addresses always send directly

    if SEND_LOCKOUT and auto_send:
        return {
            "status": "blocked",
            "error": "SEND LOCKOUT active (Commander directive 2026-03-18). "
                     "All AI send privileges revoked. auto_send=True is blocked. "
                     "Draft creation still permitted.",
            "to": to, "subject": subject,
        }

    service = _get_gmail_service()
    pid = persona_id.upper()
    display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
    from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

    message = MIMEMultipart()
    message["to"] = to
    message["from"] = f'"{display_name}" <{from_address}>'
    message["reply-to"] = COMMANDER_EMAIL
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    message.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    if auto_send:
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        action = "sent"
        ref_id = result.get("id", "unknown")
    else:
        result = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        action = "draft_created"
        ref_id = result.get("id", "unknown")
        # Cache original AI-generated body for learning diff at send time
        _cache_draft_body(ref_id, body)

    _log_email_action(to=to, subject=subject, persona_id=pid, auto_send=auto_send, ref_id=ref_id)

    return {
        "status": "success",
        "action": action,
        "id": ref_id,
        "from_persona": pid,
        "from_display": display_name,
        "from_address": from_address,
        "reply_to": COMMANDER_EMAIL,
        "to": to,
        "subject": subject,
        "auto_send": auto_send,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SEND LOCKOUT — lifted 2026-03-18 per Commander directive (test workflow)
# WF17 hook (pre_tool_guard.py) remains the primary approval gate.
# Set True to re-engage full lockout; False = normal operation.
# ══════════════════════════════════════════════════════════════════════════════
SEND_LOCKOUT = False


def gmail_send_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: send (promote) an existing Gmail draft.

    Used by the Telegram approval flow: Commander approves → COS calls this → draft sent.
    Returns dict with message ID and confirmation.
    Includes diff capture for learning compiler (Staff Skill #1-3).
    """
    if SEND_LOCKOUT:
        return {
            "status": "blocked",
            "error": "SEND LOCKOUT active (Commander directive 2026-03-18). "
                     "All AI send privileges revoked. Commander must send manually.",
            "draft_id": draft_id,
        }

    service = _get_gmail_service()

    # Fetch the draft body + headers before sending — captures the Commander-approved version
    # (may have been edited from the AI-generated original)
    sent_body = None
    sent_to = "(unknown)"
    sent_subject = "(unknown)"
    try:
        draft_data = service.users().drafts().get(userId="me", id=draft_id, format="full").execute()
        msg_payload = draft_data.get("message", {}).get("payload", {})
        sent_body = _decode_body(msg_payload)
        hdr = _extract_headers(msg_payload.get("headers", []))
        sent_to = hdr.get("To", "(unknown)")
        sent_subject = hdr.get("Subject", "(unknown)")
    except Exception:
        pass  # Non-critical — diff capture is best-effort

    sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()

    msg_id = sent.get("id", "unknown")
    _log_email_action(
        to=sent_to, subject=sent_subject,
        persona_id="APPROVED", auto_send=True, ref_id=msg_id,
    )

    # After successful send, capture diff for learning compiler
    try:
        from thunderbird_learning import capture_email_diff
        original_body = _pop_cached_draft_body(draft_id)
        if original_body and sent_body and original_body != sent_body:
            capture_email_diff(
                original_body, sent_body,
                context="Commander edited draft before sending",
                source="gmail_send",
            )
    except Exception:
        pass  # Learning capture is non-critical — never block sends

    return {
        "status": "success",
        "action": "draft_sent",
        "message_id": msg_id,
        "draft_id": draft_id,
        "sent_to": sent_to,
        "sent_subject": sent_subject,
    }


def gmail_get_message_sync(message_id: str) -> dict:
    """Synchronous wrapper: fetch a sent/received message's full content by ID.

    Returns dict with id, threadId, labels, headers, body, and attachment list.
    Used by Goose for email content comparison after sends.
    """
    service = _get_gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = _extract_headers(payload.get("headers", []))
    body = _decode_body(payload)

    if len(body) > 30000:
        body = body[:30000] + "\n\n... [TRUNCATED — exceeds 30K chars]"

    attachments = []
    for part in payload.get("parts", []):
        if part.get("filename"):
            attachments.append({
                "filename": part["filename"],
                "mimeType": part.get("mimeType", "unknown"),
                "size": part.get("body", {}).get("size", 0),
            })

    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labels": msg.get("labelIds", []),
        **headers,
        "body": body,
        "attachments": attachments,
    }


def gmail_get_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: fetch a draft's metadata and full body.

    Returns dict with to, subject, body_preview (500 chars), body_full, from fields.
    """
    service = _get_gmail_service()
    draft = service.users().drafts().get(userId="me", id=draft_id, format="full").execute()
    msg = draft.get("message", {})
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
    body = _decode_body(payload)

    return {
        "draft_id": draft_id,
        "message_id": msg.get("id", ""),
        "to": headers.get("To", ""),
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "body_preview": body[:500],
        "body_full": body,
    }


def gmail_delete_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: delete a draft."""
    service = _get_gmail_service()
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    return {"status": "success", "action": "draft_deleted", "draft_id": draft_id}


def gmail_list_drafts_sync(max_results: int = 10) -> list[dict]:
    """Synchronous wrapper: list drafts with metadata. Returns list of draft summaries."""
    service = _get_gmail_service()
    results = service.users().drafts().list(userId="me", maxResults=min(max_results, 50)).execute()
    drafts = results.get("drafts", [])
    if not drafts:
        return []

    summaries = []
    for draft_ref in drafts:
        draft = service.users().drafts().get(userId="me", id=draft_ref["id"], format="metadata").execute()
        msg = draft.get("message", {})
        headers = _extract_headers(msg.get("payload", {}).get("headers", []))
        summaries.append({
            "draft_id": draft["id"],
            "message_id": msg.get("id", ""),
            "snippet": msg.get("snippet", ""),
            **headers,
        })
    return summaries


def gmail_check_wing_inbox(max_results: int = 10, mark_read: bool = True) -> list[dict]:
    """Check d2mconcierge@gmail.com inbox for unread Commander replies.

    Polls the Wing Gmail account for messages FROM any Commander address.
    Used by the Wing reply loop to close the conversational loop:
      Staff → Wing Gmail → Commander → reply → Wing Gmail inbox → here → Telegram

    Args:
        max_results: Max messages to return (cap at 20).
        mark_read:   Mark fetched messages as read (default True).

    Returns:
        List of dicts: message_id, thread_id, from, subject, date, snippet, body.
        Empty list if Wing Gmail unavailable or no unread Commander messages.
    """
    try:
        # FILTER: Prevent inbox clutter from automated wing noise
        NOISY_SUBJECTS = [
            "Delivery Status Notification",
            "Task",
            "Timer System Update",
            "PREFLIGHT CHECK",
            "HALE DAILY BRIEF"
        ]
        if subject and any(noisy in subject for noisy in NOISY_SUBJECTS):
            logger.info(f"BLOCKED NOISY EMAIL: {subject} (Route: /logs/system_noise.log)")
            with open("/home/john/Thunderbird/logs/system_noise.log", "a") as f:
                f.write(f"[{datetime.now()}] BLOCKED: {subject}\n{body}\n---\n")
            return {"status": "success", "message_id": "blocked_noise"}

        service = _get_wing_gmail_service()
    except Exception as e:
        logger.warning(f"Wing Gmail not available for inbox check: {e}")
        return []


    # Build query: unread messages from any Commander address
    addrs = " OR ".join(f"from:{addr}" for addr in COMMANDER_ADDRS)
    query = f"is:unread ({addrs})"

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=min(max_results, 20)
        ).execute()
    except Exception as e:
        logger.error(f"Wing inbox list failed: {e}")
        return []

    stubs = results.get("messages", [])
    if not stubs:
        return []

    fetched = []
    for stub in stubs:
        msg_id = stub["id"]
        try:
            full = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            headers = {
                h["name"]: h["value"]
                for h in full.get("payload", {}).get("headers", [])
            }
            body = _decode_body(full.get("payload", {}))

            if mark_read:
                service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()

            fetched.append({
                "message_id": msg_id,
                "thread_id": full.get("threadId", ""),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": full.get("snippet", ""),
                "body": body,
            })
        except Exception as e:
            logger.error(f"Wing inbox: failed to fetch message {msg_id}: {e}")

    return fetched


def gmail_create_draft_sync(
    to: str,
    subject: str,
    body: str,
    from_address: str = "concierge@d2mluxury.quest",
    label_review: bool = True,
) -> dict:
    """Synchronous wrapper: create a Gmail draft with D2M stationery.

    Used by n8n workflows to stage Intel / Tech drafts for Commander review.
    Applies THUNDERBIRD-Commander-Review label by default.
    Returns dict with draft_id, message_id, subject, and status.
    """
    import base64 as _b64

    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["from"] = from_address
    msg["subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(_wrap_body_html(body), "html"))

    raw = _b64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    draft_id = draft["id"]
    message_id = draft.get("message", {}).get("id", "")

    if label_review and message_id:
        try:
            _tag_commander_review(service, message_id)
        except Exception as e:
            logger.warning(f"gmail_create_draft_sync: label tagging failed: {e}")

    logger.info(f"Draft created — id={draft_id} subject='{subject}'")
    return {
        "status": "success",
        "draft_id": draft_id,
        "message_id": message_id,
        "subject": subject,
        "to": to,
        "label_applied": label_review,
    }


if __name__ == "__main__":
    import sys
    if "--authorize" in sys.argv:
        authorize_gmail()
    else:
        print("Usage: python3 thunderbird_gmail.py --authorize")
        print("  Runs the one-time OAuth 2.0 browser authorization flow.")
        print(f"  Saves token to: {TOKEN_FILE}")
