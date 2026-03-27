"""
Thunderbird Bulletin — Client Newsletter System
================================================
Dreams2Memories Travel, LLC

Generates and sends luxury travel newsletters to clients, personalized by
relationship tier, interests, and active bookings. Dani's voice throughout.

Workflow:
  1. generate_bulletin(theme)      — build BulletinContent, save to SQLite
  2. personalize_for_recipient()   — tier/dossier-aware personalisation
  3. render_bulletin_html()        — Jinja2 → mobile-responsive HTML
  4. draft_bulletin_emails()       — Gmail drafts, THUNDERBIRD-Client-Bulletin
  5. preview_bulletin(bulletin_id) — HTML for C2 / portal display

MCP tools: bulletin_generate · bulletin_preview · bulletin_draft_emails
           bulletin_list · bulletin_send

Register in travel_mcp_server.py:
  from thunderbird_bulletin import register_bulletin_tools
  register_bulletin_tools(mcp)

Persona: Dani Moreau — Aggregator → Artist → Advocate.
COS reviews all outbound client communications before delivery.
"""

import base64
import copy
import json
import logging
import os
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(os.path.expanduser("~/Thunderbird"))
TEMPLATES_DIR   = THUNDERBIRD_DIR / "templates"
DATA_DIR        = THUNDERBIRD_DIR / "data"
DOSSIER_DIR     = THUNDERBIRD_DIR / "dossiers"
OUTPUT_DIR      = THUNDERBIRD_DIR / "output" / "bulletins"
LOGO_PATH       = THUNDERBIRD_DIR / "Agency_Logo_email.png"
DB_PATH         = DATA_DIR / "bulletin_store.db"

BULLETIN_TEMPLATE  = "client_bulletin.html.j2"
D2M_FROM_ADDRESS   = "concierge@d2mluxury.quest"
GMAIL_ACCOUNT      = "d2mconcierge@gmail.com"
BULLETIN_LABEL     = "THUNDERBIRD-Client-Bulletin"

NAVY  = "#1a2332"
GOLD  = "#c9a84c"
CREAM = "#f7f3ea"
INK   = "#0000ff"   # Commander's pen color

COMMANDER_ADDRS = {
    "johnloucks3@gmail.com", "johnloucks75@gmail.com",
    "john@d2mluxury.quest", "d2mconcierge@gmail.com",
    "concierge@d2mluxury.quest",
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BulletinSection:
    title:     str
    body:      str           # HTML content
    image_url: str = ""
    cta_text:  str = ""      # call-to-action button text
    cta_link:  str = ""


@dataclass
class BulletinContent:
    bulletin_id:  str
    subject:      str
    greeting:     str                    # personalized per recipient
    hero_image:   str                    # top banner image URL or data URI
    sections:     List[BulletinSection] = field(default_factory=list)
    closing:      str = ""               # sign-off text (HTML allowed)
    created_date: str = ""
    status:       str = "draft"          # draft / reviewed / sent
    recipients:   List[Dict] = field(default_factory=list)
    # [{email, name, client_tier, personalization_notes}]


# ---------------------------------------------------------------------------
# BulletinStore
# ---------------------------------------------------------------------------

class BulletinStore:
    """SQLite-backed persistence for bulletins (data/bulletin_store.db)."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bulletins (
                    bulletin_id  TEXT PRIMARY KEY,
                    subject      TEXT NOT NULL,
                    status       TEXT NOT NULL DEFAULT 'draft',
                    created_date TEXT NOT NULL,
                    payload      TEXT NOT NULL
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _serialize(bulletin: BulletinContent) -> str:
        d = asdict(bulletin)
        return json.dumps(d)

    @staticmethod
    def _deserialize(payload: str) -> BulletinContent:
        d = json.loads(payload)
        d["sections"] = [BulletinSection(**s) for s in d.get("sections", [])]
        return BulletinContent(**d)

    def save_bulletin(self, bulletin: BulletinContent) -> str:
        """Insert or replace; returns bulletin_id."""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO bulletins
                   (bulletin_id, subject, status, created_date, payload)
                   VALUES (?, ?, ?, ?, ?)""",
                (bulletin.bulletin_id, bulletin.subject, bulletin.status,
                 bulletin.created_date, self._serialize(bulletin)),
            )
        logger.info("Bulletin saved: %s (%s)", bulletin.bulletin_id, bulletin.status)
        return bulletin.bulletin_id

    def get_bulletin(self, bulletin_id: str) -> Optional[BulletinContent]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM bulletins WHERE bulletin_id = ?",
                (bulletin_id,)
            ).fetchone()
        return self._deserialize(row["payload"]) if row else None

    def list_bulletins(self, status: str = None, limit: int = 10) -> List[Dict]:
        sql  = "SELECT bulletin_id, subject, status, created_date FROM bulletins"
        args: list = []
        if status:
            sql += " WHERE status = ?"
            args.append(status)
        sql += " ORDER BY created_date DESC LIMIT ?"
        args.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    def update_status(self, bulletin_id: str, status: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE bulletins SET status = ? WHERE bulletin_id = ?",
                (status, bulletin_id)
            )
            row = conn.execute(
                "SELECT payload FROM bulletins WHERE bulletin_id = ?",
                (bulletin_id,)
            ).fetchone()
            if row:
                d = json.loads(row["payload"])
                d["status"] = status
                conn.execute(
                    "UPDATE bulletins SET payload = ? WHERE bulletin_id = ?",
                    (json.dumps(d), bulletin_id)
                )
        logger.info("Bulletin %s → %s", bulletin_id, status)


_store: Optional[BulletinStore] = None

def _get_store() -> BulletinStore:
    global _store
    if _store is None:
        _store = BulletinStore()
    return _store


# ---------------------------------------------------------------------------
# Theme library
# ---------------------------------------------------------------------------

def _derive_season(now: datetime) -> str:
    m, y = now.month, now.year
    if m in (3, 4, 5):   return f"Spring {y}"
    elif m in (6, 7, 8):  return f"Summer {y}"
    elif m in (9, 10, 11): return f"Autumn {y}"
    else:                  return f"Holiday {y}"


def _derive_theme(now: datetime) -> str:
    themes = {
        1: "New Year, New Horizons",     2: "Winter Escapes",
        3: "Mediterranean Awakening",    4: "Spring Voyages",
        5: "Rivieras & River Towns",     6: "Northern Lights & Midnight Sun",
        7: "Grand Summer Sailings",      8: "Late Summer Discoveries",
        9: "Autumn on the Water",       10: "Wine Country & Fall Foliage",
       11: "Holiday Season Preview",    12: "Year-End Luxury Escapes",
    }
    return themes.get(now.month, "Curated Discoveries")


_THEME_SECTIONS: Dict[str, List[Dict]] = {
    "Mediterranean Summer": [
        {
            "title": "The Med Is Calling",
            "body": (
                "<p>Azure coves, crumbling amphitheaters, sunsets that stay with you forever — "
                "Mediterranean summer 2026 is shaping up beautifully. We've been watching "
                "itineraries closely and a handful of sailings still have outstanding availability.</p>"
                "<p>If the Greek islands have been on your list, now is the moment.</p>"
            ),
            "cta_text": "Explore Mediterranean Sailings",
            "cta_link": "https://www.d2mluxury.quest/destinations/mediterranean",
        },
        {
            "title": "Spotlight: Storied Scandinavia — Regent SS Grandeur",
            "body": (
                "<p>Ten nights aboard Regent's newest ultra-luxury ship, tracing the luminous "
                "coastlines of the Baltic. Every excursion included, every specialty restaurant, "
                "every glass of Champagne. Stockholm to Oslo — the way it was always meant to be experienced.</p>"
            ),
            "cta_text": "Request a Quote",
            "cta_link": "https://www.d2mluxury.quest/contact",
        },
        {
            "title": "Insider Tip: Arrive in Athens Early",
            "body": (
                "<p>Don't treat Athens as a transit city. Arrive a day early, stay at the "
                "Hotel Grande Bretagne overlooking the Acropolis, and start your voyage the way "
                "it deserves — slowly, with a glass of Assyrtiko in hand.</p>"
            ),
        },
    ],
    "Alaska Cruise Season": [
        {
            "title": "Alaska: Untamed and Unforgettable",
            "body": (
                "<p>Glacier Bay's walls of ancient ice, the humpbacks of Frederick Sound, "
                "the totem poles of Ketchikan — Alaska rewards the traveler who arrives "
                "with nothing but time and wonder. The 2026 season is upon us.</p>"
            ),
            "cta_text": "See Alaska Voyages",
            "cta_link": "https://www.d2mluxury.quest/destinations/alaska",
        },
        {
            "title": "Silversea Silver Muse — Early Access",
            "body": (
                "<p>Silversea's all-suite Silver Muse returns to Alaska with our preferred "
                "group rates intact. We can hold two suites without deposit for 72 hours — "
                "worth a conversation if Alaska has been on your radar.</p>"
            ),
            "cta_text": "Check Availability",
            "cta_link": "https://www.d2mluxury.quest/contact",
        },
        {
            "title": "Packing Wisdom: Layers, Not Luggage",
            "body": (
                "<p>Alaska's weather shifts every hour. The travelers who enjoy it most pack "
                "a quality waterproof shell, thermal base layers, and leave the formal wardrobe "
                "at half the size they think they need. Casual elegance is the right register.</p>"
            ),
        },
    ],
    "Monthly Update": [
        {
            "title": "What We've Been Working On",
            "body": (
                "<p>Spring is here and our clients are heading everywhere — Scandinavia, "
                "the Greek islands, the rivers of France. We've been in the weeds on logistics "
                "so you don't have to be, and we wanted to share a few things that caught "
                "our attention this month.</p>"
            ),
        },
        {
            "title": "New Voyage Alerts",
            "body": (
                "<p>Regent Seven Seas just released their 2027 world cruise itineraries — "
                "early bookings carry an additional shipboard credit of up to $7,000 per suite. "
                "Oceania also announced three new Mediterranean port calls not available on "
                "other lines. Worth noting.</p>"
            ),
            "cta_text": "Tell Us Where You Want to Go",
            "cta_link": "https://www.d2mluxury.quest/contact",
        },
        {
            "title": "Travel Advisory Watch",
            "body": (
                "<p>We monitor State Department advisories, airline route changes, and port "
                "disruptions so you're never surprised mid-trip. If anything affecting your "
                "plans comes up, you'll hear from us first — not from a news alert.</p>"
            ),
        },
    ],
}


def _get_theme_sections(theme: str) -> List[Dict]:
    for key in _THEME_SECTIONS:
        if theme.lower() in key.lower() or key.lower() in theme.lower():
            return _THEME_SECTIONS[key]
    return _THEME_SECTIONS["Monthly Update"]


# ---------------------------------------------------------------------------
# generate_bulletin
# ---------------------------------------------------------------------------

def generate_bulletin(
    theme: str = None,
    sections: List[Dict] = None,
) -> BulletinContent:
    """
    Build a BulletinContent and persist it to SQLite.

    If *theme* is supplied and *sections* is not, auto-generates sections
    appropriate to the theme using Dani's voice. Optionally enriches copy
    via Claude API when ANTHROPIC_API_KEY is available.
    """
    if theme is None:
        theme = "Monthly Update"

    now = datetime.utcnow()
    bulletin_id  = f"BUL-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    created_date = now.strftime("%Y-%m-%d")

    subject_map = {
        "mediterranean summer": "Your Mediterranean Summer — What We're Watching Right Now",
        "alaska":               "Alaska 2026: Ice, Whales, and Two Suites Still Available",
        "monthly update":       f"A Note from D2M — {now.strftime('%B %Y')}",
    }
    subject = next(
        (v for k, v in subject_map.items() if k in theme.lower()),
        f"{theme} — From D2M Luxury Travel",
    )

    if sections:
        built_sections = [
            BulletinSection(
                title=s.get("title", ""),
                body=s.get("body", ""),
                image_url=s.get("image_url", ""),
                cta_text=s.get("cta_text", ""),
                cta_link=s.get("cta_link", ""),
            )
            for s in sections
        ]
    else:
        raw = _get_theme_sections(theme)
        built_sections = [
            BulletinSection(
                title=s.get("title", ""),
                body=s.get("body", ""),
                image_url=s.get("image_url", ""),
                cta_text=s.get("cta_text", ""),
                cta_link=s.get("cta_link", ""),
            )
            for s in raw
        ]

    bulletin = BulletinContent(
        bulletin_id=bulletin_id,
        subject=subject,
        greeting="Dear Traveler,",
        hero_image=_get_logo_b64_uri(),
        sections=built_sections,
        closing=(
            "Travel well,<br>"
            "<strong>Dani Moreau</strong><br>"
            "Your D2M Concierge<br>"
            f"<a href='mailto:{D2M_FROM_ADDRESS}' style='color:{INK};'>{D2M_FROM_ADDRESS}</a>"
        ),
        created_date=created_date,
        status="draft",
        recipients=[],
    )

    # Optionally enrich with Claude-generated copy
    bulletin = _enrich_with_claude(bulletin)

    _get_store().save_bulletin(bulletin)
    logger.info("Generated bulletin %s — theme: %s", bulletin_id, theme)
    return bulletin


# ---------------------------------------------------------------------------
# render_bulletin_html
# ---------------------------------------------------------------------------

def render_bulletin_html(
    bulletin: BulletinContent,
    recipient: Dict = None,
) -> str:
    """
    Render BulletinContent → complete mobile-responsive HTML.

    Uses templates/client_bulletin.html.j2 when available; falls back to
    the inline template otherwise.
    """
    greeting = bulletin.greeting
    if recipient:
        name  = recipient.get("name", "")
        first = name.split()[0] if name else ""
        tier  = (recipient.get("client_tier", "") or "").lower()
        if first:
            greeting = f"Hey {first}," if tier == "friend" else f"Dear {first},"

    context = {
        "bulletin":  bulletin,
        "recipient": recipient or {},
        "greeting":  greeting,
        "navy":      NAVY,
        "gold":      GOLD,
        "cream":     CREAM,
        "ink":       INK,
        "year":      datetime.utcnow().year,
    }

    if _JINJA2_AVAILABLE:
        template_path = TEMPLATES_DIR / BULLETIN_TEMPLATE
        if template_path.exists():
            import urllib.parse
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "j2"]),
            )
            env.filters["urlencode"] = urllib.parse.quote
            return env.get_template(BULLETIN_TEMPLATE).render(**context)
        logger.warning("Bulletin template not found at %s — using inline fallback", template_path)

    return _inline_html(bulletin, greeting)


def _inline_html(bulletin: BulletinContent, greeting: str) -> str:
    """Inline fallback HTML — no external dependencies."""
    sections_html = ""
    for sec in bulletin.sections:
        img_html = (
            f'<img src="{sec.image_url}" alt="{sec.title}" '
            f'style="max-width:100%;height:auto;display:block;margin-bottom:14px;"/>'
            if sec.image_url else ""
        )
        cta_html = ""
        if sec.cta_text and sec.cta_link:
            cta_html = (
                f'<p style="margin-top:18px;">'
                f'<a href="{sec.cta_link}" '
                f'style="display:inline-block;background:{NAVY};color:{GOLD};'
                f'padding:10px 22px;text-decoration:none;border-radius:3px;'
                f'font-size:13px;letter-spacing:0.5px;">'
                f'{sec.cta_text}</a></p>'
            )
        sections_html += f"""
        <tr><td style="padding:28px 36px 0;">
            {img_html}
            <h2 style="font-family:Georgia,serif;font-size:18px;color:{NAVY};
                        font-weight:600;margin:0 0 10px;">{sec.title}</h2>
            <div style="font-size:15px;line-height:1.75;color:#2d3748;">{sec.body}</div>
            {cta_html}
        </td></tr>
        <tr><td style="padding:0 36px;">
            <hr style="border:none;border-top:1px solid #e0d8c8;margin:24px 0 0;"/>
        </td></tr>"""

    logo_html = ""
    if bulletin.hero_image:
        logo_html = (
            f'<img src="{bulletin.hero_image}" alt="Dreams2Memories Travel" '
            f'style="max-width:180px;height:auto;display:block;margin:0 auto 10px;"/>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
<title>{bulletin.subject}</title>
</head>
<body style="margin:0;padding:0;background:#eee8db;font-family:Georgia,'Times New Roman',serif;
             -webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center" style="padding:28px 12px;">
  <table width="620" cellpadding="0" cellspacing="0" border="0"
         style="background:{CREAM};max-width:620px;width:100%;
                border:1px solid #d6ccb8;border-radius:4px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- HEADER -->
    <tr><td style="background:{NAVY};padding:30px 36px;text-align:center;border-radius:4px 4px 0 0;">
      {logo_html}
      <p style="font-family:Georgia,serif;font-size:13px;letter-spacing:3px;
                color:{GOLD};margin:0;text-transform:uppercase;">
        Dreams2Memories Travel, LLC
      </p>
    </td></tr>

    <!-- DATE + SUBJECT -->
    <tr><td style="padding:28px 36px 0;">
      <p style="font-size:12px;color:#999;letter-spacing:0.5px;margin:0 0 14px;">
        {bulletin.created_date}
      </p>
      <p style="font-size:17px;color:{NAVY};margin:0;">{greeting}</p>
    </td></tr>

    <!-- SECTIONS -->
    {sections_html}

    <!-- CLOSING -->
    <tr><td style="padding:28px 36px;">
      <p style="font-size:15px;color:{NAVY};line-height:1.75;margin:0;">
        {bulletin.closing}
      </p>
    </td></tr>

    <!-- FOOTER -->
    <tr><td style="background:{NAVY};padding:18px 36px;text-align:center;
                   border-radius:0 0 4px 4px;">
      <p style="font-family:Georgia,serif;font-size:11px;color:{GOLD};
                letter-spacing:1px;margin:0;">
        Dreams2Memories Travel, LLC &nbsp;·&nbsp; {D2M_FROM_ADDRESS}
      </p>
      <p style="font-size:10px;color:#7a8a9a;margin:6px 0 0;">
        You are receiving this because you are a valued D2M traveler. &nbsp;
        <a href="mailto:{D2M_FROM_ADDRESS}?subject=Unsubscribe"
           style="color:#7a8a9a;">Unsubscribe</a>
      </p>
    </td></tr>

  </table>
</td></tr>
</table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# personalize_for_recipient
# ---------------------------------------------------------------------------

def personalize_for_recipient(
    bulletin: BulletinContent,
    recipient: Dict,
) -> BulletinContent:
    """
    Return a deep copy of the bulletin personalized for one recipient.

    - Greeting: first name, tone adjusted for tier (friend=casual, prospect=aspirational)
    - Closing: softened for friends
    - Dossier interest signals logged for future section weighting
    """
    personalized = copy.deepcopy(bulletin)

    name  = recipient.get("name", "")
    first = name.split()[0] if name else ""
    tier  = (recipient.get("client_tier", "paying") or "paying").lower()

    if first:
        if tier == "friend":
            personalized.greeting = f"Hey {first},"
            personalized.closing  = personalized.closing.replace("Travel well,", "Talk soon,")
        elif tier == "prospect":
            personalized.greeting = f"Dear {first},"
            personalized.closing  = personalized.closing.replace(
                "Travel well,",
                "We'd love to help you plan something extraordinary."
            )
        else:
            personalized.greeting = f"Dear {first},"

    notes = recipient.get("personalization_notes", "")
    if notes:
        logger.debug("Personalization notes for %s: %s", name, notes)

    # Light dossier scan for interest signals
    if name:
        last = name.split()[-1] if len(name.split()) > 1 else name
        candidates = list(DOSSIER_DIR.glob(f"*{last}*.md")) if DOSSIER_DIR.exists() else []
        if candidates:
            try:
                excerpt = candidates[0].read_text(errors="ignore")[:800]
                interests = [
                    kw for kw in (
                        "Alaska", "Mediterranean", "river", "expedition",
                        "family", "cruise", "Viking", "Silversea", "Regent",
                    )
                    if kw.lower() in excerpt.lower()
                ]
                if interests:
                    logger.debug("Dossier interests for %s: %s", name, interests)
            except Exception as exc:
                logger.warning("Dossier read error for %s: %s", name, exc)

    return personalized


# ---------------------------------------------------------------------------
# draft_bulletin_emails
# ---------------------------------------------------------------------------

def draft_bulletin_emails(
    bulletin_id: str,
    recipients: List[Dict] = None,
) -> List[str]:
    """
    Create Gmail drafts for each recipient via thunderbird_gmail.

    From: concierge@d2mluxury.quest (send-as on d2mconcierge@gmail.com)
    Label: THUNDERBIRD-Client-Bulletin
    Returns list of draft IDs created.
    """
    store    = _get_store()
    bulletin = store.get_bulletin(bulletin_id)
    if bulletin is None:
        raise ValueError(f"Bulletin not found: {bulletin_id}")

    target_recipients = recipients or bulletin.recipients
    if not target_recipients:
        logger.warning("No recipients for bulletin %s", bulletin_id)
        return []

    try:
        from thunderbird_gmail import _get_gmail_service
    except ImportError:
        logger.error("thunderbird_gmail unavailable — cannot create drafts")
        return []

    try:
        service = _get_gmail_service()
    except Exception as exc:
        logger.error("Gmail service unavailable: %s", exc)
        return []

    # Ensure label exists
    _ensure_gmail_label(service, BULLETIN_LABEL)

    draft_ids: List[str] = []
    for rec in target_recipients:
        email = rec.get("email", "")
        if not email or email.lower() in COMMANDER_ADDRS:
            continue
        try:
            personal = personalize_for_recipient(bulletin, rec)
            html_body = render_bulletin_html(personal, rec)
            plain_body = _html_to_plain(html_body)
            draft_id = _create_mime_draft(
                service=service,
                to_addr=email,
                subject=personal.subject,
                html_body=html_body,
                plain_body=plain_body,
                label_name=BULLETIN_LABEL,
            )
            draft_ids.append(draft_id)
            logger.info("Bulletin draft created: %s → %s", email, draft_id)
        except Exception as exc:
            logger.error("Draft failed for %s: %s", email, exc)
            draft_ids.append(f"ERROR:{email}:{exc}")

    successes = [d for d in draft_ids if not d.startswith("ERROR:")]
    if successes:
        store.update_status(bulletin_id, "reviewed")
        logger.info(
            "Bulletin %s: %d drafts created, %d errors",
            bulletin_id, len(successes), len(draft_ids) - len(successes),
        )

    return draft_ids


# ---------------------------------------------------------------------------
# preview_bulletin
# ---------------------------------------------------------------------------

def preview_bulletin(bulletin_id: str) -> str:
    """Return full HTML preview string for Telegram C2 or portal display."""
    store    = _get_store()
    bulletin = store.get_bulletin(bulletin_id)
    if bulletin is None:
        return f"<p><strong>Bulletin {bulletin_id} not found.</strong></p>"
    return render_bulletin_html(bulletin)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_logo_b64_uri() -> str:
    if LOGO_PATH.exists():
        try:
            with open(LOGO_PATH, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext  = LOGO_PATH.suffix.lstrip(".").lower()
            mime = "image/png" if ext == "png" else f"image/{ext}"
            return f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.warning("Logo load failed: %s", exc)
    return ""


def _html_to_plain(html: str) -> str:
    """Very lightweight HTML → plain text for MIME fallback."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ensure_gmail_label(service, label_name: str) -> Optional[str]:
    """Create Gmail label if it doesn't exist; return label ID."""
    try:
        result = service.users().labels().list(userId="me").execute()
        for lbl in result.get("labels", []):
            if lbl.get("name") == label_name:
                return lbl["id"]
        created = service.users().labels().create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
        ).execute()
        logger.info("Created Gmail label: %s (%s)", label_name, created.get("id"))
        return created.get("id")
    except Exception as exc:
        logger.warning("Could not ensure label %s: %s", label_name, exc)
        return None


def _create_mime_draft(
    service,
    to_addr: str,
    subject: str,
    html_body: str,
    plain_body: str,
    label_name: str,
) -> str:
    """Create a Gmail draft and apply label; returns draft ID."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    DANI_DISPLAY = "Dani Moreau, Dreams2Memories Travel"

    msg = MIMEMultipart("alternative")
    msg["to"]       = to_addr
    msg["from"]     = f'"{DANI_DISPLAY}" <{D2M_FROM_ADDRESS}>'
    msg["subject"]  = subject
    msg["reply-to"] = GMAIL_ACCOUNT

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    draft_id  = result.get("id", "")
    thread_id = result.get("message", {}).get("threadId", "")

    # Apply label to the underlying message
    label_id = _ensure_gmail_label(service, label_name)
    if label_id and thread_id:
        try:
            msg_id = result.get("message", {}).get("id", "")
            service.users().messages().modify(
                userId="me", id=msg_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as exc:
            logger.warning("Label apply failed for draft %s: %s", draft_id, exc)

    return draft_id


# ---------------------------------------------------------------------------
# Claude copy enrichment (graceful degradation)
# ---------------------------------------------------------------------------

def _enrich_with_claude(bulletin: BulletinContent) -> BulletinContent:
    """
    Call Claude via Anthropic SDK to rewrite section bodies in Dani's voice.
    Silently skips if SDK / API key unavailable.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()

        sections_desc = "\n".join(
            f"SECTION_{i}: {s.title}"
            for i, s in enumerate(bulletin.sections)
        )

        prompt = (
            f"You are Dani Moreau, luxury travel concierge at Dreams2Memories Travel.\n"
            f"Rewrite each bulletin section body in Dani's voice.\n\n"
            f"Voice: warm, literate, never corporate. Short sentences. Confident.\n"
            f"No exclamation points. Blue-ink pen on cream stationery — elegant, personal.\n\n"
            f"Theme: {bulletin.subject}\n\n"
            f"Sections:\n{sections_desc}\n\n"
            f"For each section, write 2–4 sentences of compelling body copy. "
            f"Return JSON: {{\"sections\": [{{\"body\": \"...html...\"}}, ...]}}\n"
            f"Use <p> tags. Keep the order."
        )

        resp = client.messages.create(
            model="claude-sonnet-4-5-20251001",  # Sonnet (SO 2026-03-27: Opus retired)
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text if resp.content else ""

        # Extract JSON block
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            for i, sec_data in enumerate(data.get("sections", [])):
                if i < len(bulletin.sections) and sec_data.get("body"):
                    bulletin.sections[i].body = sec_data["body"]
            logger.info("Claude enrichment applied to bulletin %s", bulletin.bulletin_id)

    except Exception as exc:
        logger.debug("Claude enrichment skipped: %s", exc)

    return bulletin


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_bulletin_tools(server) -> None:
    """Register all bulletin MCP tools with the FastMCP server instance."""

    @server.tool()
    async def bulletin_generate(theme: str = "Monthly Update") -> str:
        """
        Generate a new client bulletin for the given theme.

        Themes: 'Mediterranean Summer', 'Alaska Cruise Season',
        'Monthly Update', or any custom string.
        Returns bulletin_id, subject, and section count.
        """
        try:
            bulletin = generate_bulletin(theme=theme)
            return json.dumps({
                "status":      "ok",
                "bulletin_id": bulletin.bulletin_id,
                "subject":     bulletin.subject,
                "sections":    len(bulletin.sections),
                "created":     bulletin.created_date,
                "next_step":   "Use bulletin_preview to inspect HTML, then bulletin_draft_emails to stage.",
            }, indent=2)
        except Exception as exc:
            logger.exception("bulletin_generate failed")
            return json.dumps({"status": "error", "message": str(exc)})

    @server.tool()
    async def bulletin_preview(bulletin_id: str) -> str:
        """
        Return the full HTML preview of a bulletin.

        Truncated to 4,000 chars for Telegram; render full HTML in portal/browser.
        """
        try:
            html = preview_bulletin(bulletin_id)
            if len(html) > 4000:
                return html[:4000] + "\n<!-- truncated — view full HTML in portal -->"
            return html
        except Exception as exc:
            logger.exception("bulletin_preview failed")
            return f"ERROR: {exc}"

    @server.tool()
    async def bulletin_draft_emails(bulletin_id: str) -> str:
        """
        Create Gmail drafts for all recipients in the bulletin.

        Drafts are labeled THUNDERBIRD-Client-Bulletin, sent from
        concierge@d2mluxury.quest via d2mconcierge@gmail.com.
        COS reviews before Commander approves and sends (WF17).
        """
        try:
            store    = _get_store()
            bulletin = store.get_bulletin(bulletin_id)
            if bulletin is None:
                return json.dumps({"status": "error", "message": f"Bulletin {bulletin_id} not found"})
            draft_ids = draft_bulletin_emails(bulletin_id)
            successes = [d for d in draft_ids if not d.startswith("ERROR:")]
            errors    = [d for d in draft_ids if d.startswith("ERROR:")]
            return json.dumps({
                "status":          "ok",
                "bulletin_id":     bulletin_id,
                "drafts_created":  len(successes),
                "errors":          len(errors),
                "draft_ids":       successes,
                "error_details":   errors[:5],
                "note":            "Drafts in d2mconcierge@gmail.com — COS review before send.",
            }, indent=2)
        except Exception as exc:
            logger.exception("bulletin_draft_emails failed")
            return json.dumps({"status": "error", "message": str(exc)})

    @server.tool()
    async def bulletin_list(status: str = None) -> str:
        """
        List bulletins, optionally filtered by status: draft / reviewed / sent.
        Returns up to 10 most recent.
        """
        try:
            rows = _get_store().list_bulletins(status=status or None, limit=10)
            return json.dumps({"status": "ok", "count": len(rows), "bulletins": rows}, indent=2)
        except Exception as exc:
            logger.exception("bulletin_list failed")
            return json.dumps({"status": "error", "message": str(exc)})

    @server.tool()
    async def bulletin_send(bulletin_id: str) -> str:
        """
        Mark a bulletin as sent after Gmail drafts have been approved and dispatched.

        NOTE: This records status only — it does NOT auto-send email.
        Actual delivery happens via WF17 draft approval flow in Gmail.
        """
        try:
            store    = _get_store()
            bulletin = store.get_bulletin(bulletin_id)
            if bulletin is None:
                return json.dumps({"status": "error", "message": f"Bulletin {bulletin_id} not found"})
            store.update_status(bulletin_id, "sent")
            return json.dumps({
                "status":      "ok",
                "bulletin_id": bulletin_id,
                "new_status":  "sent",
                "note":        "Status recorded. Actual send via Gmail WF17 draft approval.",
            }, indent=2)
        except Exception as exc:
            logger.exception("bulletin_send failed")
            return json.dumps({"status": "error", "message": str(exc)})

    logger.info(
        "Bulletin MCP tools registered: "
        "bulletin_generate, bulletin_preview, bulletin_draft_emails, "
        "bulletin_list, bulletin_send"
    )


# ---------------------------------------------------------------------------
# CLI — standalone testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="D2M Client Bulletin System")
    sub    = parser.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("generate", help="Generate a bulletin")
    p_gen.add_argument("--theme",  default="Monthly Update")
    p_gen.add_argument("--sections-json", default="", help="JSON array of section dicts")

    p_list = sub.add_parser("list", help="List bulletins")
    p_list.add_argument("--status", default="", help="draft|reviewed|sent")

    p_prev = sub.add_parser("preview", help="Preview bulletin HTML")
    p_prev.add_argument("bulletin_id")
    p_prev.add_argument("--save", action="store_true", help="Save to output/bulletins/")

    p_draft = sub.add_parser("draft", help="Create Gmail drafts")
    p_draft.add_argument("bulletin_id")

    args = parser.parse_args()

    if args.cmd == "generate":
        secs = json.loads(args.sections_json) if args.sections_json else None
        b = generate_bulletin(theme=args.theme, sections=secs)
        print(f"\nGenerated: {b.bulletin_id}")
        print(f"  Subject: {b.subject}")
        print(f"  Sections: {len(b.sections)}")
        print(f"  Status: {b.status}")

    elif args.cmd == "list":
        rows = _get_store().list_bulletins(status=args.status or None)
        print(f"\n{len(rows)} bulletin(s):")
        for r in rows:
            print(f"  [{r['status']:10}] {r['bulletin_id']}  {r['subject'][:60]}")

    elif args.cmd == "preview":
        html = preview_bulletin(args.bulletin_id)
        if args.save:
            safe = re.sub(r"[^\w\-]", "_", args.bulletin_id)
            out  = OUTPUT_DIR / f"preview_{safe}.html"
            out.write_text(html, encoding="utf-8")
            print(f"Saved: {out}")
        else:
            print(html[:2000], "... (truncated)")

    elif args.cmd == "draft":
        ids = draft_bulletin_emails(args.bulletin_id)
        ok  = [d for d in ids if not d.startswith("ERROR:")]
        err = [d for d in ids if d.startswith("ERROR:")]
        print(f"\nDrafts created: {len(ok)}  Errors: {len(err)}")
        for d in ok:
            print(f"  OK: {d}")
        for e in err:
            print(f"  ERR: {e}")

    else:
        parser.print_help()
