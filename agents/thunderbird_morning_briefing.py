"""
Thunderbird Morning Briefing — "Wake Up Impressed"
Dreams2Memories Travel, LLC

Pulls ALL intelligence from Google Sheets, anchor dates, fare watches,
and client data into a single beautifully formatted HTML email sent
daily at 0630 MT.

Deduplication: tracks sent item hashes in briefing_sent.json to avoid
repeating the same headline across consecutive days.

Usage:
  python3 thunderbird_morning_briefing.py                # Send daily briefing
  python3 thunderbird_morning_briefing.py --preview      # Save HTML locally, don't send
  python3 thunderbird_morning_briefing.py --weekly       # Weekly digest mode
"""

import json
import hashlib
import logging
import sys
import os
import base64
import argparse
import urllib.parse
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import feedparser
from bs4 import BeautifulSoup
import gspread
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(__file__).parent.parent
SENT_CACHE = THUNDERBIRD_DIR / "briefing_sent.json"
PREVIEW_DIR = THUNDERBIRD_DIR / "output"
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo_email.png"
HEADSHOT_FILE = THUNDERBIRD_DIR / "John_Headshot.jpg"

# Send-lock prevents duplicate sends on the same day
# Lock file: OpsCenter/morning_brief_sent_YYYYMMDD.lock (MT date)
_LOCK_DIR = THUNDERBIRD_DIR / "OpsCenter"


def _morning_brief_lock_path() -> Path:
    try:
        import zoneinfo
        mt_date = datetime.now(tz=zoneinfo.ZoneInfo("America/Denver")).strftime("%Y%m%d")
    except Exception:
        mt_date = date.today().strftime("%Y%m%d")
    return _LOCK_DIR / f"morning_brief_sent_{mt_date}.lock"


def _morning_brief_lock_exists() -> bool:
    return _morning_brief_lock_path().exists()


def _write_morning_brief_lock():
    p = _morning_brief_lock_path()
    p.write_text(json.dumps({"sent_at": datetime.utcnow().isoformat()}))
    logger.info(f"Morning brief send-lock written: {p}")

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SA_CREDS = THUNDERBIRD_DIR / "credentials.json"
GMAIL_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"
GMAIL_OAUTH = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
# D2M ops account — authenticated sender for all briefing emails (gmail_token.json)
OPS_EMAIL = "d2mconcierge@gmail.com"
# Commander's personal inbox — all briefings delivered here
COMMANDER_EMAIL = "johnloucks3@gmail.com"
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.modify"]

# Dedup window: items older than this many days get purged from cache
DEDUP_WINDOW_DAYS = 5

logger = logging.getLogger("thunderbird_briefing")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


# ---------------------------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------------------------

def _load_sent_cache() -> dict:
    if SENT_CACHE.exists():
        try:
            return json.loads(SENT_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_sent_cache(cache: dict):
    # Prune entries older than DEDUP_WINDOW_DAYS
    cutoff = (date.today() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    pruned = {k: v for k, v in cache.items() if v >= cutoff}
    SENT_CACHE.write_text(json.dumps(pruned, indent=2), encoding="utf-8")


def _item_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()


def _is_new(text: str, cache: dict) -> bool:
    return _item_hash(text) not in cache


def _mark_sent(text: str, cache: dict):
    cache[_item_hash(text)] = date.today().isoformat()


# ---------------------------------------------------------------------------
# DATA SOURCES
# ---------------------------------------------------------------------------

def _get_sheets_client():
    creds = service_account.Credentials.from_service_account_file(
        str(SA_CREDS),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def fetch_commander_log(gc) -> list[dict]:
    """Commander_Log: curated daily world event summaries."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Commander_Log")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return []
        entries = []
        for row in rows[1:]:
            if len(row) >= 3:
                entries.append({
                    "timestamp": row[0],
                    "category": row[1],
                    "content": row[2],
                })
        return entries
    except Exception as e:
        logger.error(f"Commander_Log fetch failed: {e}")
        return []


def fetch_intel_log(gc, limit=100) -> list[dict]:
    """Intel_Log: raw RSS feed items."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Intel_Log")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return []
        # Get latest entries (they're appended, so last rows are newest)
        entries = []
        for row in rows[-limit:]:
            if len(row) >= 6:
                entries.append({
                    "timestamp": row[0],
                    "source": row[1],
                    "line": row[2],
                    "ship": row[3] if len(row) > 3 else "",
                    "headline": row[4] if len(row) > 4 else "",
                    "category": row[5] if len(row) > 5 else "",
                    "priority": row[6] if len(row) > 6 else "",
                    "url": row[7] if len(row) > 7 else "",
                })
        return entries
    except Exception as e:
        logger.error(f"Intel_Log fetch failed: {e}")
        return []


def fetch_pricing_tracker(gc) -> list[dict]:
    """Pricing Tracker: cruise price snapshots."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Pricing Tracker")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as e:
        logger.error(f"Pricing Tracker fetch failed: {e}")
        return []


def fetch_tech_news(gc) -> list[dict]:
    """Tech News Monitor."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Tech News Monitor")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as e:
        logger.error(f"Tech News fetch failed: {e}")
        return []


def fetch_fare_log(gc) -> list[dict]:
    """Fare Log: historical fare tracking."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Fare Log")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as e:
        logger.error(f"Fare Log fetch failed: {e}")
        return []


def fetch_completed_actions(gc) -> set:
    """Read Action_Tracker for items marked DONE. Returns set of (booking_key, anchor_label)."""
    try:
        ws = gc.open_by_key(SHEET_ID).worksheet("Action_Tracker")
        rows = ws.get_all_values()
        completed = set()
        for row in rows[1:]:
            if len(row) >= 5 and row[4].strip().upper() == "DONE":
                completed.add((row[0].strip(), row[1].strip()))
        return completed
    except Exception as e:
        logger.error(f"Action_Tracker fetch failed: {e}")
        return set()


def _mailto_done_link(booking_key: str, anchor_label: str) -> str:
    """Generate a mailto: link that sends a DONE command via self-email for Star Protocol."""
    subject = urllib.parse.quote(f"[A3] DONE: {booking_key} — {anchor_label}")
    body = urllib.parse.quote(
        f"Mark complete:\nBooking: {booking_key}\nMilestone: {anchor_label}\n\n"
        f"(Sent from Thunderbird Briefing — Star Protocol will process)"
    )
    return f"mailto:{COMMANDER_EMAIL}?subject={subject}&body={body}"


def _mailto_snooze_link(booking_key: str, anchor_label: str) -> str:
    """Generate a mailto: link that snoozes an item for 7 days."""
    subject = urllib.parse.quote(f"[A3] SNOOZE: {booking_key} — {anchor_label}")
    body = urllib.parse.quote(
        f"Snooze 7 days:\nBooking: {booking_key}\nMilestone: {anchor_label}\n\n"
        f"(Sent from Thunderbird Briefing — Star Protocol will process)"
    )
    return f"mailto:{COMMANDER_EMAIL}?subject={subject}&body={body}"


def fetch_anchor_dates_upcoming() -> dict:
    """Get upcoming anchor dates from KNOWN_BOOKINGS."""
    try:
        from core.booking.thunderbird_tp_scheduler import scan_all_actionable
        from thunderbird_anchor_dates import KNOWN_BOOKINGS, compute_anchors, scan_all_bookings_due
        all_anchors = {}
        for key, bk in KNOWN_BOOKINGS.items():
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk.get("hard_dates"), key,
                fpd_status=bk.get("fpd_status"),
            )
            all_anchors[key] = anchors
        return scan_all_bookings_due(all_anchors)
    except Exception as e:
        logger.error(f"Anchor dates fetch failed: {e}")
        return {}


def fetch_heartbeat_findings() -> dict:
    """Read the latest hale_heartbeat_scan.py results — overdue suspenses,
    aging P0/P1 missions, stale CI tools. This is the validated, low-noise
    process layer built 2026-07-04; it is the PRIMARY signal for 'what needs
    the Commander's attention' going forward, ahead of the legacy anchor-date
    system (which has its own, separately-tracked data-staleness issues —
    see MISSION-1540)."""
    p = THUNDERBIRD_DIR / "OpsCenter" / "state" / "heartbeat_scan_latest.json"
    if not p.exists():
        return {"findings": [], "scanned_at": None}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Heartbeat findings fetch failed: {e}")
        return {"findings": [], "scanned_at": None}


# ---------------------------------------------------------------------------
# DIRECT RSS FEED FETCHER
# ---------------------------------------------------------------------------

# Domain category mapping for RSS sources — kept in sync with WorldIntelConfig.FEED_CATEGORIES.
# When adding a new feed to WorldIntelConfig.NEWS_FEEDS, add it here too.
def _build_source_categories() -> dict:
    """Build _SOURCE_CATEGORIES from WorldIntelConfig.FEED_CATEGORIES with a local fallback."""
    try:
        from thunderbird_world_intel import WorldIntelConfig
        return dict(WorldIntelConfig.FEED_CATEGORIES)
    except Exception:
        pass
    # Fallback hardcoded copy (kept in sync manually)
    return {
        "Cruise Critic": "Cruise", "Seatrade Cruise News": "Cruise",
        "Travel Weekly": "Cruise", "Cruise Industry News": "Cruise",
        "Cruise Hive": "Cruise", "Cruise Mapper": "Cruise",
        "ISW": "War/Geopolitics", "RealClearDefense": "War/Geopolitics",
        "RealClearWorld": "War/Geopolitics", "Defense One": "War/Geopolitics",
        "War on the Rocks": "War/Geopolitics", "Foreign Affairs": "War/Geopolitics",
        "RealClearPolitics": "Politics", "RealClearPolicy": "Politics",
        "The Hill": "Politics",
        "Simple Flying": "Airline", "Aviation Week": "Airline",
        "Routes Online": "Airline", "The Points Guy Airlines": "Airline",
        "Cranky Flier": "Airline",
        "The Maritime Executive": "Maritime", "gCaptain": "Maritime",
        "TradeWinds": "Maritime",
        "RealClearMarkets": "Markets", "RealClearEnergy": "Markets",
        "Skift": "Travel", "Travel Pulse": "Travel", "The Points Guy": "Travel",
    }


_SOURCE_CATEGORIES = _build_source_categories()


def fetch_direct_rss_feeds() -> list[dict]:
    """Fetch RSS feeds directly using feedparser, scored by relevance.

    Returns list of dicts: source, title, url, published, summary,
    relevance_score, category.  Groups by domain category.
    Max 10 articles per source, 250 total.
    """
    from thunderbird_world_intel import WorldIntelConfig

    articles: list[dict] = []

    for source_name, feed_url in WorldIntelConfig.NEWS_FEEDS.items():
        try:
            logger.info(f"  RSS: {source_name}...")
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries:
                if count >= 10:
                    break

                title = entry.get("title", "").strip()
                if not title:
                    continue

                url = entry.get("link", "")
                published = entry.get("published", "")
                raw_summary = entry.get("summary", entry.get("description", ""))

                # Strip HTML tags from summary
                summary_text = BeautifulSoup(raw_summary, "html.parser").get_text()
                summary_text = summary_text[:2000]  # full summary, no 300-char truncation

                # Score relevance using alert keywords
                relevance = 1
                search_blob = (title + " " + summary_text).lower()
                for kw in WorldIntelConfig.ALERT_KEYWORDS:
                    if kw.lower() in search_blob:
                        relevance += 1
                relevance = min(relevance, 5)

                category = _SOURCE_CATEGORIES.get(source_name, "Other")

                articles.append({
                    "source": source_name,
                    "title": title,
                    "url": url,
                    "published": published,
                    "summary": summary_text,
                    "relevance_score": relevance,
                    "category": category,
                })
                count += 1

        except Exception as e:
            logger.error(f"  RSS FAIL ({source_name}): {e}")
            continue

    # Sort by relevance descending, then cap at 250
    articles.sort(key=lambda a: a["relevance_score"], reverse=True)
    articles = articles[:250]

    logger.info(f"Direct RSS: {len(articles)} articles fetched across {len(WorldIntelConfig.NEWS_FEEDS)} feeds")
    return articles


# ---------------------------------------------------------------------------
# EXECUTIVE SUMMARY BUILDER
# ---------------------------------------------------------------------------

def fetch_overnight_outputs() -> list[dict]:
    """Scan for overnight routine outputs from the last 24h."""
    results = []
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    intel_dir = THUNDERBIRD_DIR / "intel"
    output_dir = THUNDERBIRD_DIR / "output"

    # Scan intel/ for files modified in last 24h
    if intel_dir.exists():
        for f in sorted(intel_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            size_kb = f.stat().st_size / 1024
            # Grab first meaningful line as description
            try:
                first_line = f.read_text(encoding="utf-8", errors="replace")[:200].strip()
            except Exception:
                first_line = ""
            results.append({
                "source": "intel",
                "file": f.name,
                "path": str(f.relative_to(THUNDERBIRD_DIR)),
                "size_kb": round(size_kb, 1),
                "mtime": mtime.strftime("%H:%M"),
                "preview": first_line[:150] if first_line else "",
            })

    # Scan output/ for files modified in last 24h
    if output_dir.exists():
        for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            # Only catch routine outputs (ask_*, wind_staff_*, etc.)
            if not any(f.name.startswith(p) for p in ["ask_", "wind_staff_", "two_brain_", "briefing_"]):
                continue
            size_kb = f.stat().st_size / 1024
            try:
                first_line = f.read_text(encoding="utf-8", errors="replace")[:200].strip()
            except Exception:
                first_line = ""
            results.append({
                "source": "output",
                "file": f.name,
                "path": str(f.relative_to(THUNDERBIRD_DIR)),
                "size_kb": round(size_kb, 1),
                "mtime": mtime.strftime("%H:%M"),
                "preview": first_line[:150] if first_line else "",
            })
    return results


def fetch_system_status() -> dict:
    """Gather system health summary."""
    status = {}

    # Preflight log tail
    preflight_log = THUNDERBIRD_DIR / "logs" / "preflight.log"
    if preflight_log.exists():
        try:
            lines = preflight_log.read_text(encoding="utf-8").strip().split("\n")
            tail = [l for l in lines if "RED" in l or "YELLOW" in l or "GREEN" in l or "Overall" in l]
            status["preflight"] = tail[-5:] if tail else ["No alerts in preflight log"]
        except Exception:
            status["preflight"] = ["Could not read preflight log"]
    else:
        status["preflight"] = ["No preflight log found"]

    # Metronome latest tick
    metronome_ticks = THUNDERBIRD_DIR / "OpsCenter" / "metronome_ticks.jsonl"
    if metronome_ticks.exists():
        try:
            lines = metronome_ticks.read_text(encoding="utf-8").strip().split("\n")
            if lines:
                last = json.loads(lines[-1])
                status["metronome"] = {
                    "state": last.get("state", "UNKNOWN"),
                    "last_tick": last.get("ts", "")[:19],
                }
        except Exception:
            status["metronome"] = {"state": "UNKNOWN", "last_tick": "?"}
    else:
        status["metronome"] = {"state": "OFF", "last_tick": "N/A"}

    # Mission board counts
    mission_board = THUNDERBIRD_DIR / "OpsCenter" / "mission_board.json"
    if mission_board.exists():
        try:
            board = json.loads(mission_board.read_text(encoding="utf-8"))
            missions = board.get("missions", [])
            active = [m for m in missions if m.get("status") not in ("complete", "completed")]
            status["missions"] = {"active": len(active), "total": len(missions)}
        except Exception:
            status["missions"] = {"active": "?", "total": "?"}
    else:
        status["missions"] = {"active": 0, "total": 0}

    return status


def build_executive_summary(
    commander_log, intel_log, pricing, tech_news, fare_log, anchor_report, today,
    rss_direct=None,
    recon_line: str = "",
    product_digest: str = "",
    heartbeat: dict = None,
) -> dict:
    """Build counts and highlights for the exec summary banner."""
    # Count new items (after dedup)
    total_intel = len(intel_log)
    total_commander = len(commander_log)
    total_pricing = len(pricing)
    total_tech = len(tech_news)
    total_fares = len(fare_log)
    total_rss_direct = len(rss_direct) if rss_direct else 0

    # Anchor date counts
    overdue = len(anchor_report.get("overdue", []))
    due_today = len(anchor_report.get("due_today", []))
    due_week = len(anchor_report.get("due_this_week", []))

    # Heartbeat scan counts — the validated process layer (2026-07-04). Overdue
    # suspenses are the primary trigger the Commander asked to see on every
    # login; they lead the banner ahead of the legacy anchor system.
    heartbeat = heartbeat or {}
    hb_findings = heartbeat.get("findings", [])
    overdue_suspenses = [f for f in hb_findings if f.get("category") == "overdue_suspense"]
    aging_missions = [f for f in hb_findings if f.get("category") == "aging_mission"]
    stale_ci = [f for f in hb_findings if f.get("category") == "stale_ci_tool"]

    # Determine alert level — overdue suspenses take priority (they're the
    # validated, deliberately-deferred items the Commander asked to review),
    # then anchor-date overdue/due-today, then aging missions as a lower tier.
    if overdue_suspenses:
        alert_level = "RED"
        alert_icon = "&#9888;"
        alert_text = f"{len(overdue_suspenses)} OVERDUE SUSPENSE{'S' if len(overdue_suspenses) != 1 else ''} TO REVIEW"
    elif overdue > 0 or due_today > 0:
        alert_level = "RED"
        alert_icon = "&#9888;"  # warning triangle
        alert_text = f"{overdue + due_today} ACTION ITEMS NEED ATTENTION"
    elif aging_missions:
        alert_level = "GOLD"
        alert_icon = "&#9733;"
        alert_text = f"{len(aging_missions)} P0/P1 mission(s) aging"
    elif due_week > 0:
        alert_level = "GOLD"
        alert_icon = "&#9733;"  # star
        alert_text = f"{due_week} milestones this week"
    else:
        alert_level = "GREEN"
        alert_icon = "&#10004;"  # checkmark
        alert_text = "All clear — no urgent items"

    return {
        "date_display": today.strftime("%A, %B %d, %Y"),
        "total_intel": total_intel,
        "total_commander": total_commander,
        "total_pricing": total_pricing,
        "total_tech": total_tech,
        "total_fares": total_fares,
        "total_rss_direct": total_rss_direct,
        "overdue": overdue,
        "due_today": due_today,
        "due_week": due_week,
        "overdue_suspenses": overdue_suspenses,
        "aging_missions": aging_missions,
        "stale_ci": stale_ci,
        "heartbeat_scanned_at": heartbeat.get("scanned_at"),
        "alert_level": alert_level,
        "alert_icon": alert_icon,
        "alert_text": alert_text,
        "recon_line": recon_line,
        "product_digest": product_digest,
    }


# ---------------------------------------------------------------------------
# TELEGRAM DIGEST SENDER
# ---------------------------------------------------------------------------

def send_telegram_digest(rss_direct: list, anchor_report: dict, summary: dict):
    """Send a condensed digest to Telegram C2 (@D2MC2C_bot)."""
    import urllib.request as _urlreq

    BOT_TOKEN = os.environ.get("D2M_TELEGRAM_TOKEN", "***REMOVED-SECRET***")
    CHAT_ID   = os.environ.get("D2M_TELEGRAM_CHAT_ID", "@D2MC2C_bot")
    MAX_CHUNK = 3800

    def _tg_send(text: str):
        url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # Try with Markdown first; fall back to plain text on 400 (unescaped chars)
        for parse_mode in ("Markdown", None):
            payload = {"chat_id": CHAT_ID, "text": text,
                       "disable_web_page_preview": True}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            data = json.dumps(payload).encode()
            req  = _urlreq.Request(url, data=data,
                                    headers={"Content-Type": "application/json"})
            try:
                _urlreq.urlopen(req, timeout=15)
                break  # success — stop retrying
            except Exception as e:
                if parse_mode and "400" in str(e):
                    logger.debug("Markdown parse failed, retrying plain text")
                    continue
                logger.warning(f"Telegram send failed: {e}")
                break

    def _chunk_send(text: str):
        lines, buf = text.split("\n"), ""
        for line in lines:
            if len(buf) + len(line) + 1 > MAX_CHUNK:
                if buf.strip():
                    _tg_send(buf)
                buf = line + "\n"
            else:
                buf += line + "\n"
        if buf.strip():
            _tg_send(buf)

    today = datetime.now().strftime("%a %b %d")
    alert_emoji = {"RED": "🔴", "GOLD": "🟡", "GREEN": "🟢"}.get(summary["alert_level"], "")
    header = (
        f"*THUNDERBIRD BRIEF — {today}*\n"
        f"{alert_emoji} {summary['alert_text']}\n"
        f"_{summary['total_rss_direct']} live intel items across 18 sources_\n"
        f"{'─' * 30}"
    )
    _tg_send(header)

    # Action items
    urgent = anchor_report.get("overdue", []) + anchor_report.get("due_today", [])
    if urgent:
        lines = ["*⚠️ ACTION ITEMS*"]
        for item in urgent[:5]:
            lines.append(f"• {item.get('label','')} — _{item.get('booking','')}_")
        _chunk_send("\n".join(lines))

    # Top headlines by category
    cat_order = ["War/Geopolitics", "Politics", "Cruise", "Airline", "Maritime", "Markets", "Travel"]
    by_cat: dict[str, list] = {}
    for art in (rss_direct or []):
        by_cat.setdefault(art.get("category", "Other"), []).append(art)

    cat_icons = {
        "War/Geopolitics": "🌍", "Politics": "🏛", "Cruise": "🚢",
        "Airline": "✈️", "Maritime": "⚓", "Markets": "📈", "Travel": "🧳",
    }
    for cat in cat_order:
        items = by_cat.get(cat, [])
        if not items:
            continue
        icon = cat_icons.get(cat, "•")
        lines = [f"*{icon} {cat.upper()}*"]
        for art in items[:4]:
            title = art.get("title", "")[:90]
            url   = art.get("url", "")
            src   = art.get("source", "")
            if url:
                lines.append(f"• [{title}]({url}) _{src}_")
            else:
                lines.append(f"• {title} _{src}_")
        _chunk_send("\n".join(lines))

    _tg_send("_End of brief — full detail in inbox_")
    logger.info(f"Telegram digest sent to {CHAT_ID}")


# ---------------------------------------------------------------------------
# HTML TEMPLATE
# ---------------------------------------------------------------------------

def _img_base64(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _parse_commander_content(content: str) -> list[dict]:
    """Parse commander log content into structured source/items."""
    sources = []
    current_source = None
    current_items = []

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("**") and line.endswith("**"):
            if current_source:
                sources.append({"source": current_source, "items": current_items})
            current_source = line.strip("*").strip()
            current_items = []
        elif line.startswith("- "):
            # Extract title and URL
            text = line[2:].strip()
            url = ""
            if "(" in text and text.endswith(")"):
                parts = text.rsplit("(", 1)
                title = parts[0].strip()
                url = parts[1].rstrip(")")
            else:
                title = text
            current_items.append({"title": title, "url": url})

    if current_source:
        sources.append({"source": current_source, "items": current_items})

    return sources


def _render_card_section(icon: str, title: str, card_id: str,
                          bullets: list[str], expanded_html: str,
                          accent: str = "#c9a84c") -> str:
    """Render a single collapsible intel card."""
    bullets_html = "".join(
        f'<li style="margin:3px 0;font-size:12px;color:#a0aec0;">{b}</li>'
        for b in bullets[:4]
    )
    return f"""
<div style="margin:0 0 10px 0;border-radius:10px;overflow:hidden;
            border:1px solid rgba(201,168,76,0.18);background:#111c2e;">
  <!-- Card header — always visible -->
  <div onclick="toggle('{card_id}')"
       style="display:flex;align-items:center;gap:12px;padding:14px 18px;
              cursor:pointer;background:#152540;border-left:4px solid {accent};
              user-select:none;">
    <span style="font-size:20px;">{icon}</span>
    <span style="font-size:13px;font-weight:700;text-transform:uppercase;
                 letter-spacing:1.5px;color:#c9a84c;flex:1;">{title}</span>
    <span id="arr-{card_id}"
          style="font-size:18px;color:#c9a84c;transition:transform .25s;">▸</span>
  </div>
  <!-- Collapsed bullet summary -->
  <div id="sum-{card_id}" style="padding:8px 18px 10px 54px;background:#0f1a2e;">
    <ul style="margin:0;padding:0;list-style:disc;">{bullets_html}</ul>
  </div>
  <!-- Expanded full content (hidden by default) -->
  <div id="exp-{card_id}"
       style="display:none;padding:16px 18px;background:#0d1525;
              border-top:1px solid rgba(201,168,76,0.12);">
    {expanded_html}
  </div>
</div>
"""


def render_briefing_html(
    summary: dict,
    commander_log: list,
    intel_log: list,
    pricing: list,
    tech_news: list,
    fare_log: list,
    anchor_report: dict,
    is_weekly: bool = False,
    completed_actions: set = None,
    rss_direct: list = None,
    intel_crew_report: dict = None,
    temporal_intel: str = "",
    overnight_outputs: list[dict] = None,
    system_status: dict = None,
) -> str:
    """Render the full briefing as branded expandable-card HTML email."""

    logo_uri = _img_base64(LOGO_FILE)
    today = datetime.now()
    alert_emoji = {"RED": "🔴", "GOLD": "🟡", "GREEN": "🟢"}.get(summary["alert_level"], "")
    briefing_type = "WEEKLY INTELLIGENCE DIGEST" if is_weekly else "MORNING BRIEFING"

    # ── Group RSS by category ──
    by_cat: dict[str, list] = {}
    for art in (rss_direct or []):
        by_cat.setdefault(art.get("category", "Other"), []).append(art)

    cat_order = ["War/Geopolitics", "Politics", "Cruise", "Airline",
                 "Maritime", "Markets", "Travel", "Other"]
    cat_icons = {
        "War/Geopolitics": "🌍", "Politics": "🏛️", "Cruise": "🚢",
        "Airline": "✈️", "Maritime": "⚓", "Markets": "📈",
        "Travel": "🧳", "Other": "📰",
    }

    # ── Build expanded HTML per card ──
    def _get_dossier_link(bkey: str) -> str:
        """Find dossier file for a booking key and return file:// URL."""
        import glob
        dossier_dir = THUNDERBIRD_DIR / "dossiers"
        if not bkey or not dossier_dir.exists():
            return ""
        # Look for dossier files matching the booking key
        pattern = str(dossier_dir / f"*{bkey}*.md")
        files = glob.glob(pattern)
        if files:
            return f"file://{files[0]}"
        # Try matching by client name (first part of bkey, e.g., "McLeod" from "McLeod_Silversea_298475")
        client_name = bkey.split("_")[0]
        pattern = str(dossier_dir / f"{client_name}*.md")
        files = glob.glob(pattern)
        if files:
            return f"file://{files[0]}"
        return ""

    def _story_list(items: list, max_items: int = 15) -> str:
        out = []
        for art in items[:max_items]:
            title = art.get("title", "")
            url   = art.get("url", "")
            src   = art.get("source", "")
            pub   = art.get("published", "")[:16]
            summ  = art.get("summary", "")[:300]
            rel   = art.get("relevance_score", 1)
            border = "border-left:3px solid #c9a84c;padding-left:10px;" if rel >= 3 else ""
            # Commander directive 2026-06-25: links required in briefing articles (supersedes 2026-06-11 no-links rule)
            link  = (f'<a href="{url}" style="color:#7eb8ff;text-decoration:none;">{title}</a>'
                     if url else f'<span style="color:#c8d0dc;">{title}</span>')
            summ_html = (f'<div style="font-size:12px;color:#8a9ab5;margin-top:3px;line-height:1.5;">{summ}</div>'
                         if summ else "")
            out.append(
                f'<div style="padding:6px 0 6px 0;{border}border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'{link}'
                f'<div style="font-size:11px;color:#4a5a75;margin-top:2px;">{src} // {pub}</div>'
                f'{summ_html}'
                f'</div>'
            )
        return "\n".join(out)

    def _anchor_expanded() -> str:
        if completed_actions is None:
            ca = set()
        else:
            ca = completed_actions
        items_html = []
        for bucket in ["overdue", "due_today", "due_this_week"]:
            for item in anchor_report.get(bucket, []):
                bkey  = item.get("booking", "").strip()
                label = item.get("label", "").strip()
                if (bkey, label) in ca:
                    continue
                cat   = item.get("category", "")
                dt    = item.get("date", "")
                color = "#ff4444" if bucket == "overdue" else ("#ff8800" if bucket == "due_today" else "#c9a84c")

                # Generate dossier link
                dossier_link = _get_dossier_link(bkey)
                bkey_html = f'<a href="{dossier_link}" style="color:#7eb8ff;text-decoration:none;">{bkey}</a>' if dossier_link else bkey

                items_html.append(
                    f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                    f'<span style="color:{color};font-weight:700;">{dt}</span> — '
                    f'<span style="color:#c8d0dc;">{label}</span> '
                    f'<span style="color:#6b7c99;font-size:11px;">({bkey_html}) [{cat}]</span>'
                    f'</div>'
                )
        return "\n".join(items_html) if items_html else '<p style="color:#6b7c99;">No active items.</p>'

    # ── Anchor bullets ──
    anchor_bullets = []
    for bucket in ["overdue", "due_today", "due_this_week"]:
        for item in anchor_report.get(bucket, [])[:2]:
            prefix = "🔴" if bucket == "overdue" else ("🟠" if bucket == "due_today" else "🟡")
            bkey = item.get("booking","")
            dossier_link = _get_dossier_link(bkey)
            bkey_text = f'<a href="{dossier_link}" style="color:#7eb8ff;text-decoration:underline;">{bkey}</a>' if dossier_link else bkey
            anchor_bullets.append(f'{prefix} {item.get("label","")} — {bkey_text}')

    # ── Heartbeat / Validation card (2026-07-04) ──
    # Overdue suspenses, aging P0/P1, stale CI tools — from hale_heartbeat_scan.py.
    # This is the validated, deliberately-built process layer; leads the brief
    # ahead of the legacy anchor-date system per Commander directive.
    overdue_susp = summary.get("overdue_suspenses", [])
    aging_miss = summary.get("aging_missions", [])
    stale_ci_items = summary.get("stale_ci", [])

    def _file_link(f: dict) -> str:
        """Every line links to its actual file on disk — Commander is
        usually on yoga where file:// paths resolve directly (2026-07-04)."""
        path = f.get("file")
        if not path:
            return ""
        return f' <a href="file://{path}" style="color:#7eb8ff;text-decoration:none;font-size:10px;">[open]</a>'

    def _heartbeat_expanded() -> str:
        sections = []
        if overdue_susp:
            rows = "".join(
                f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                f'<span style="color:#ff4444;font-weight:700;">{f["what"]}</span>{_file_link(f)}<br>'
                f'<span style="color:#6b7c99;font-size:11px;">{f["action"]}</span></div>'
                for f in overdue_susp
            )
            sections.append(f'<div style="margin-bottom:14px;"><div style="color:#e8c97a;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Overdue Suspenses — review these</div>{rows}</div>')
        if aging_miss:
            rows = "".join(
                f'<div style="padding:6px 0;color:#c8d0dc;font-size:12px;">{f["what"]}{_file_link(f)}</div>'
                for f in aging_miss
            )
            sections.append(f'<div style="margin-bottom:14px;"><div style="color:#e8c97a;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Aging P0/P1 Missions</div>{rows}</div>')
        if stale_ci_items:
            rows = "".join(
                f'<div style="padding:4px 0;color:#8a9ab5;font-size:11px;">{f["what"]}{_file_link(f)}</div>'
                for f in stale_ci_items
            )
            sections.append(f'<div><div style="color:#e8c97a;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Stale CI Tools</div>{rows}</div>')
        scanned = summary.get("heartbeat_scanned_at")
        footer = f'<div style="margin-top:10px;color:#4a5568;font-size:10px;">Last scan: {scanned or "never run"}</div>'
        return ("\n".join(sections) if sections else '<p style="color:#6b7c99;">Nothing crossed threshold — genuinely clear.</p>') + footer

    heartbeat_bullets = [f'🔴 {f["what"]}{_file_link(f)}' for f in overdue_susp[:2]]
    heartbeat_bullets += [f'🟡 {f["what"]}{_file_link(f)}' for f in aging_miss[:2]]
    if not heartbeat_bullets:
        heartbeat_bullets = ["Nothing crossed threshold — genuinely clear"]

    # ── Intel Crew summary ──
    crew_expanded = ""
    if intel_crew_report:
        cos = intel_crew_report.get("cos_review", "")
        if cos:
            crew_expanded = f'<div style="font-size:13px;color:#c8d0dc;line-height:1.7;">{cos.replace(chr(10),"<br>")}</div>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;
          background:#080d14; color:#e0e6ed; line-height:1.6; }}
  .wrap {{ max-width:700px; margin:0 auto; background:#0d1b2e; }}
  .hdr  {{ background:#0d1b2e; padding:28px 24px 18px;
           border-bottom:3px solid #c9a84c; }}
  .stat-bar {{ display:flex; background:#152540;
               border-bottom:1px solid rgba(201,168,76,0.2); }}
  .stat {{ flex:1; text-align:center; padding:12px 6px;
           border-right:1px solid rgba(201,168,76,0.1); }}
  .stat:last-child {{ border-right:none; }}
  .sn   {{ font-size:20px; font-weight:700; color:#e8c97a; display:block; }}
  .sl   {{ font-size:9px; text-transform:uppercase; letter-spacing:1.5px; color:#6b7c99; }}
  .cards {{ padding:16px; }}
  a     {{ color:#7eb8ff; }}
</style>
<script>
function toggle(id) {{
  var s = document.getElementById('sum-'+id);
  var e = document.getElementById('exp-'+id);
  var a = document.getElementById('arr-'+id);
  if (e.style.display === 'none') {{
    e.style.display = 'block';
    s.style.display = 'none';
    a.style.transform = 'rotate(90deg)';
  }} else {{
    e.style.display = 'none';
    s.style.display = 'block';
    a.style.transform = 'rotate(0deg)';
  }}
}}
</script>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    {"<img src='" + logo_uri + "' style='height:48px;margin-bottom:10px;display:block;'>" if logo_uri else ""}
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:3px;color:#c9a84c;">Dreams2Memories Travel</div>
    <div style="font-size:26px;font-weight:700;color:#fff;margin:4px 0 2px;">THUNDERBIRD {briefing_type}</div>
    <div style="font-size:13px;color:#8a9ab5;">{summary["date_display"]}</div>
    <div style="margin-top:8px;display:inline-block;background:rgba(201,168,76,0.15);
                color:#e8c97a;font-size:10px;font-weight:700;letter-spacing:2px;
                padding:4px 12px;border-radius:20px;border:1px solid rgba(201,168,76,0.3);">
      {alert_emoji} {summary["alert_text"]}
    </div>
  </div>

  <div class="stat-bar">
    <div class="stat"><span class="sn">{len(summary.get("overdue_suspenses", []))}</span><div class="sl">Suspenses</div></div>
    <div class="stat"><span class="sn">{summary["overdue"] + summary["due_today"]}</span><div class="sl">Actions</div></div>
    <div class="stat"><span class="sn">{summary["due_week"]}</span><div class="sl">This Week</div></div>
    <div class="stat"><span class="sn">{len(rss_direct) if rss_direct else 0}</span><div class="sl">Live Intel</div></div>
    <div class="stat"><span class="sn">{summary["total_pricing"]}</span><div class="sl">Fares</div></div>
  </div>

  <div class="cards">
"""

    # ── Heartbeat / Validation Card (leads — this is what Commander asked
    #    to see on every login: overdue suspenses first) ──
    html += _render_card_section(
        "⚡", "Overdue Suspenses & Process Validation", "heartbeat",
        heartbeat_bullets,
        _heartbeat_expanded(),
        accent="#ff4444" if overdue_susp else "#44c8c8"
    )

    # ── Anchor Dates Card ──
    html += _render_card_section(
        "📅", "Action Items & Deadlines", "anchors",
        anchor_bullets or ["All clear — no urgent items"],
        _anchor_expanded(),
        accent="#ff8800"
    )

    # ── Intel Crew card (if available) ──
    if intel_crew_report and crew_expanded:
        crew_bullets = ["COS Hale synthesis available", "A2 Dembe analysis complete"]
        html += _render_card_section("🎯", "Intel Crew Analysis", "crew",
                                      crew_bullets, crew_expanded, accent="#44c8c8")

    # ── Overnight File Outputs card ──
    if overnight_outputs:
        overnight_bullets = []
        overnight_expanded_parts = []
        for out in overnight_outputs[:15]:
            icon = "📁" if out["source"] == "intel" else "📄"
            overnight_bullets.append(f'{icon} {out["file"]} ({out["size_kb"]}KB, {out["mtime"]})')
            preview = out.get("preview", "")
            preview_html = f'<div style="font-size:11px;color:#6b7c99;margin-top:3px;">{preview}</div>' if preview else ""
            overnight_expanded_parts.append(
                f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'<span style="color:#e8c97a;font-weight:600;">{out["file"]}</span>'
                f'<span style="color:#6b7c99;font-size:11px;margin-left:8px;">[{out["size_kb"]}KB @ {out["mtime"]}]</span>'
                f'{preview_html}'
                f'</div>'
            )
        overnight_expanded = "\n".join(overnight_expanded_parts)

        # System status sub-section inline
        if system_status:
            sys_parts = []
            preflight_lines = system_status.get("preflight", [])
            if preflight_lines:
                for pl in preflight_lines:
                    color = "#ff4444" if "RED" in pl else ("#ff8800" if "YELLOW" in pl else "#44c8c8")
                    sys_parts.append(f'<div style="color:{color};font-size:12px;padding:2px 0;">{pl[:120]}</div>')
            met = system_status.get("metronome", {})
            met_state = met.get("state", "?")
            met_color = {"GREEN": "#44c8c8", "YELLOW": "#ff8800", "RED": "#ff4444", "OFFLINE": "#6b7c99"}.get(met_state, "#c8d0dc")
            mis = system_status.get("missions", {})
            sys_parts.append(
                f'<div style="font-size:12px;color:#6b7c99;padding:4px 0;">'
                f'Metronome: <span style="color:{met_color};">{met_state}</span>'
                f' &middot; Last tick: {met.get("last_tick","?")}'
                f' &middot; Missions: {mis.get("active","?")} active / {mis.get("total","?")} total'
                f'</div>'
            )
            overnight_expanded += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.08);">' + "\n".join(sys_parts) + '</div>'

        html += _render_card_section("🌙", "Overnight Routine Outputs", "overnight",
                                      overnight_bullets[:5], overnight_expanded, accent="#7eb8ff")

    # ── RSS category cards ──
    for cat in cat_order:
        items = by_cat.get(cat, [])
        if not items:
            continue
        icon    = cat_icons.get(cat, "📰")
        bullets = [f'{a.get("source","")}: {a.get("title","")[:70]}' for a in items[:4]]
        html   += _render_card_section(icon, cat, f"cat-{cat.replace('/','-').replace(' ','-').lower()}",
                                        bullets, _story_list(items), accent="#c9a84c")

    # ── Close cards div + footer ──
    html += f"""
  </div>
  <div style="background:#080d14;padding:20px;text-align:center;">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:3px;color:#4a5a75;">
      Thunderbird OS // Dreams2Memories Travel, LLC
    </div>
    <div style="font-size:11px;color:#3a4a65;font-style:italic;margin-top:4px;">
      Generated {today.strftime('%Y-%m-%d %H:%M')} MT
    </div>
  </div>
</div>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Revenue Pipeline — FPD countdowns + pipeline value (per Harlan rec)
# ---------------------------------------------------------------------------

def _build_revenue_pipeline_section() -> str:
    """Build revenue pipeline digest from dossiers and anchor dates.

    Returns HTML section showing:
    - FPDs within 30 days with countdown
    - Total pipeline value (all active bookings)
    - Bookings by status
    """
    from datetime import datetime, timedelta
    from pathlib import Path
    import re

    import os as _os
    dossier_dir = Path(_os.path.expanduser("~/Thunderbird/dossiers"))
    today = datetime.now().date()
    fpd_alerts = []
    total_value = 0.0
    booking_count = 0
    skip_files = {"CLAUDE.md", "DANI_TESTER_BRIEFINGS.md", "DOSSIER_Regent_Tips_Guide.md"}

    if not dossier_dir.exists():
        return ""

    for fpath in sorted(dossier_dir.glob("*.md")):
        if fpath.name in skip_files:
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Extract client name from filename
        stem = fpath.stem
        client_name = stem.replace("_", " ").replace("DOSSIER ", "")

        # Find Final Payment Date
        fpd_match = re.search(
            r'(?:Final\s+Payment|FPD)[:\s]+(\w+\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})',
            content, re.IGNORECASE
        )
        if fpd_match:
            date_str = fpd_match.group(1).strip().rstrip(",")
            fpd_date = None
            for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y-%m-%d",
                        "%B %d,%Y", "%b %d,%Y"]:
                try:
                    fpd_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if fpd_date:
                days_until = (fpd_date - today).days
                if 0 <= days_until <= 30:
                    urgency = "CRITICAL" if days_until <= 7 else "WARNING" if days_until <= 14 else "INFO"
                    fpd_alerts.append({
                        "client": client_name,
                        "fpd_date": fpd_date.strftime("%b %d"),
                        "days": days_until,
                        "urgency": urgency,
                    })
                elif days_until < 0 and days_until >= -7:
                    fpd_alerts.append({
                        "client": client_name,
                        "fpd_date": fpd_date.strftime("%b %d"),
                        "days": days_until,
                        "urgency": "OVERDUE",
                    })

        # Extract booking value (look for total/price/amount patterns)
        value_match = re.search(
            r'(?:Total|Price|Amount|Cost|Value)[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            content, re.IGNORECASE
        )
        if value_match:
            try:
                val = float(value_match.group(1).replace(",", ""))
                if 100 < val < 500000:  # sanity check
                    total_value += val
                    booking_count += 1
            except ValueError:
                pass

    # Build HTML
    if not fpd_alerts and booking_count == 0:
        return ""

    # Sort FPD alerts by urgency then days
    urgency_order = {"OVERDUE": 0, "CRITICAL": 1, "WARNING": 2, "INFO": 3}
    fpd_alerts.sort(key=lambda x: (urgency_order.get(x["urgency"], 9), x["days"]))

    html = """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(126,184,255,0.15);">&#128176;</div>
      <div class="section-title">Revenue Pipeline</div>
    </div>
    <div style="padding:12px 16px;font-size:13px;line-height:1.7;color:#e0e6ed;">
"""

    if booking_count > 0:
        html += (
            f'      <div style="color:#c9a84c;font-weight:600;margin-bottom:8px;">'
            f'Pipeline: ${total_value:,.0f} across {booking_count} active booking(s)</div>\n'
        )

    if fpd_alerts:
        html += '      <div style="color:#7eb8ff;font-weight:600;margin-bottom:4px;">Final Payment Deadlines</div>\n'
        for alert in fpd_alerts:
            color_map = {"OVERDUE": "#ff4444", "CRITICAL": "#ff6666", "WARNING": "#e8c97a", "INFO": "#7eb8ff"}
            color = color_map.get(alert["urgency"], "#e0e6ed")
            if alert["days"] < 0:
                countdown = f'{abs(alert["days"])}d OVERDUE'
            elif alert["days"] == 0:
                countdown = "TODAY"
            else:
                countdown = f'{alert["days"]}d'
            html += (
                f'      <div style="padding:2px 0 2px 12px;">'
                f'<span style="color:{color};font-weight:600;">[{alert["urgency"]}]</span> '
                f'{alert["client"]} — {alert["fpd_date"]} '
                f'<span style="color:{color};">({countdown})</span>'
                f'</div>\n'
            )

    html += "    </div>\n  </div>\n"
    return html


# ---------------------------------------------------------------------------
# EMAIL SEND (not draft!)
# ---------------------------------------------------------------------------

def _get_gmail_service():
    """Get Gmail API service using OAuth token."""
    creds = None
    if GMAIL_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN), SCOPES_GMAIL)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError("Gmail not authorized. Run: python3 thunderbird_gmail.py --authorize")
    return build("gmail", "v1", credentials=creds)


def _wrap_briefing_in_stationery(html_content: str) -> str:
    """Wrap the briefing's dark-navy HTML body in D2M stationery outer shell.

    The briefing has its own internal styling (dark navy, gold accents).
    This adds the D2M brand layer on top:
      - Full-width navy banner with D2M logo (180px)
      - Warm linen surround (#eee8db) — the desk beneath the card
      - The briefing's own HTML sits inside as a self-contained block

    We inject the banner above the briefing body content so the logo
    appears at the top of the email, then the briefing's internal
    header follows naturally.
    """
    logo_uri = _img_base64(LOGO_FILE)
    if logo_uri:
        banner_html = (
            f'<div style="background-color:#0d1b2e;padding:28px 0;text-align:center;margin:0;">'
            f'<img src="{logo_uri}" alt="Dreams2Memories Travel" '
            f'style="height:180px;width:auto;display:inline-block;" />'
            f'</div>'
        )
    else:
        banner_html = ''

    # Inject banner + linen surround. The briefing HTML is self-contained
    # (has its own <!DOCTYPE>, <html>, <body>). We extract the <body>
    # content and re-wrap it inside the stationery shell so email clients
    # render a single clean document.
    import re
    body_match = re.search(r'<body[^>]*>([\s\S]*)</body>', html_content, re.IGNORECASE)
    if body_match:
        body_inner = body_match.group(1)
        # Preserve the original <head> (styles, fonts)
        head_match = re.search(r'<head[^>]*>([\s\S]*?)</head>', html_content, re.IGNORECASE)
        head_block = head_match.group(0) if head_match else ''
        wrapped = (
            f'<!DOCTYPE html><html>'
            f'{head_block}'
            f'<body style="margin:0;padding:0;background-color:#eee8db;">'
            f'{banner_html}'
            f'<div style="background-color:#eee8db;padding:12px 0 32px 0;">'
            f'{body_inner}'
            f'</div>'
            f'</body></html>'
        )
        return wrapped
    else:
        # Fallback: prepend banner above the raw HTML
        return f'<div style="background-color:#eee8db;margin:0;padding:0;">{banner_html}{html_content}</div>'


def send_briefing_json(intel_log: list, pricing: dict, tech_news: list, subject: str):
    """Send briefing as JSON with clickable links. Format: D2M Relevance → Source Links."""
    import subprocess
    import json as json_module

    brief_json = {
        "timestamp": datetime.now().isoformat(),
        "subject": subject,
        "sections": []
    }

    # ── Hale Everywhere — yesterday's dispatch telemetry (Phase 2 hook) ──
    # Renders at the top of the briefing JSON.  Defensive: brief still ships
    # if the telemetry module or rollup is unavailable.
    try:
        from agents.morning_brief_telemetry import telemetry_section
        brief_json["sections"].insert(0, {
            "id": "dispatch-telemetry",
            "title": "YESTERDAY'S DISPATCH",
            "text": telemetry_section(),
        })
    except Exception as _e:
        logger.debug(f"Dispatch telemetry section skipped: {_e}")

    # D2M RELEVANCE SUMMARY
    if intel_log:
        relevance_section = {
            "id": "d2m-relevance",
            "title": "D2M RELEVANCE SUMMARY",
            "items": []
        }
        for item in intel_log[:5]:  # Top 5
            relevance_section["items"].append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "link": item.get("link", ""),
                "relevance": item.get("relevance", "MEDIUM"),
                "rationale": item.get("rationale", "")
            })
        brief_json["sections"].append(relevance_section)

    # PRICING INTELLIGENCE
    if pricing:
        price_section = {
            "id": "pricing",
            "title": "PRICING INTELLIGENCE",
            "items": []
        }
        for key, val in list(pricing.items())[:5]:
            price_section["items"].append({
                "route": key,
                "price_usd": val.get("price_usd", ""),
                "trend": val.get("trend", ""),
                "link": val.get("link", "")
            })
        brief_json["sections"].append(price_section)

    # TECH NEWS
    if tech_news:
        tech_section = {
            "id": "tech-news",
            "title": "TECHNOLOGY & INNOVATION",
            "items": []
        }
        for item in tech_news[:5]:
            tech_section["items"].append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "link": item.get("link", ""),
                "category": item.get("category", "")
            })
        brief_json["sections"].append(tech_section)

    # Write to file instead of email
    json_path = f"/home/john/Thunderbird/output/briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w') as f:
        json_module.dump(brief_json, f, indent=2)

    logger.info(f"Briefing JSON saved: {json_path}")

    # Send to Commander via Telegram
    try:
        cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh",
            "telegram_send",
            json_module.dumps({"chat_id": "COMMANDER", "text": f"📊 Briefing JSON ready: {json_path}"})
        ]
        subprocess.run(cmd, capture_output=True)
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


def send_briefing_email(html_content: str, subject: str):
    """Send the briefing as an HTML email to Commander."""
    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["To"] = COMMANDER_EMAIL
    msg["From"] = OPS_EMAIL
    msg["Subject"] = subject

    # Plain text fallback
    plain = f"Thunderbird Briefing — {datetime.now().strftime('%B %d, %Y')}\nView in HTML-capable email client."
    msg.attach(MIMEText(plain, "plain"))
    # Wrap in D2M stationery (navy banner + linen surround) before sending
    msg.attach(MIMEText(_wrap_briefing_in_stationery(html_content), "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    logger.info(f"Briefing SENT to {COMMANDER_EMAIL}: {subject}")


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_briefing(preview: bool = False, weekly: bool = False, force: bool = False):
    """Execute the full briefing pipeline."""
    import fcntl
    
    if not preview and not force:
        p = _morning_brief_lock_path()
        os.makedirs(p.parent, exist_ok=True)
        # Open in append mode so we can flock without truncating
        lock_fd = open(p, 'a')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, IOError):
            logger.info("Morning brief send-lock exists (flock) — already sent (or sending) today. Exiting.")
            return "Already sent (locked)"
            
        if p.stat().st_size > 0:
            logger.info("Morning brief send-lock exists (size > 0) — already sent today. Exiting.")
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            return "Already sent"
            
        # Write the lock BEFORE the send
        lock_fd.write(json.dumps({"sent_at": datetime.utcnow().isoformat()}) + "\n")
        lock_fd.flush()
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    today = date.today()
    now = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"THUNDERBIRD {'WEEKLY' if weekly else 'MORNING'} BRIEFING — {today}")
    logger.info(f"{'='*60}")

    # Load dedup cache
    cache = _load_sent_cache()

    # Fetch all data sources
    logger.info("Connecting to Google Sheets...")
    try:
        gc = _get_sheets_client()
    except Exception as e:
        logger.warning(f"Google Sheets unavailable (credentials issue): {e} — continuing without Sheets data")
        gc = None

    logger.info("Fetching Commander_Log...")
    commander_log_raw = fetch_commander_log(gc)
    # Dedup: only include items not sent before
    commander_log = []
    for entry in commander_log_raw:
        content = entry.get("content", "")
        if _is_new(content, cache):
            commander_log.append(entry)
            _mark_sent(content, cache)
    logger.info(f"  {len(commander_log)} new / {len(commander_log_raw)} total")

    logger.info("Fetching Intel_Log...")
    intel_log_raw = fetch_intel_log(gc, limit=200 if weekly else 100)
    intel_log = []
    for entry in intel_log_raw:
        key = entry.get("headline", "") or entry.get("line", "")
        if _is_new(key, cache):
            intel_log.append(entry)
            _mark_sent(key, cache)
    logger.info(f"  {len(intel_log)} new / {len(intel_log_raw)} total")

    logger.info("Fetching Pricing Tracker...")
    pricing = fetch_pricing_tracker(gc)
    logger.info(f"  {len(pricing)} voyages")

    logger.info("Fetching Tech News...")
    tech_news = fetch_tech_news(gc)
    logger.info(f"  {len(tech_news)} articles")

    logger.info("Fetching Fare Log...")
    fare_log = fetch_fare_log(gc)
    logger.info(f"  {len(fare_log)} entries")

    logger.info("Computing Anchor Dates...")
    anchor_report = fetch_anchor_dates_upcoming()
    due = len(anchor_report.get("due_today", [])) + len(anchor_report.get("overdue", []))
    logger.info(f"  {due} action items, {len(anchor_report.get('due_this_week', []))} this week")

    logger.info("Fetching Action Tracker (completed items)...")
    completed_actions = fetch_completed_actions(gc)
    logger.info(f"  {len(completed_actions)} items marked DONE")

    # ── Booking Reconciliation ─────────────────────────────────────────────
    recon_line = ""
    try:
        from thunderbird_reconciliation import reconciliation_briefing_line
        recon_line = reconciliation_briefing_line()
        logger.info(f"  {recon_line}")
    except Exception as e:
        logger.warning(f"Reconciliation skipped: {e}")

    # ── Product Intake Digest ──────────────────────────────────────────────
    product_digest = ""
    try:
        from thunderbird_product_intake import generate_product_digest
        product_digest = generate_product_digest(days=7)
        if product_digest:
            logger.info(f"  Product digest: {len(product_digest)} chars")
    except Exception as e:
        logger.debug(f"Product digest skipped: {e}")

    logger.info("Fetching direct RSS feeds...")
    rss_direct = fetch_direct_rss_feeds()
    logger.info(f"  {len(rss_direct)} articles from live feeds")

    # ── INTEL CREW: A2 Dembe → A1 Radar → COS Hale ──
    # Run the persona-chain pipeline for analyzed, COS-approved intelligence.
    # Falls back gracefully to raw RSS if the crew fails.
    intel_crew_report = None
    logger.info("Running Intel Crew pipeline (A2 → A1 → COS)...")
    try:
        from thunderbird_intel_crew import IntelCrew
        intel_crew_report = IntelCrew().run()
        crew_status = intel_crew_report.get("status", "UNKNOWN")
        logger.info(f"  Intel Crew complete — status: {crew_status}")
    except Exception as e:
        logger.warning(f"Intel Crew failed, falling back to raw RSS only: {e}")

    # ── Temporal Intelligence: preference shifts + upcoming milestones ─────
    temporal_intel = ""
    try:
        from thunderbird_temporal_memory import get_backend
        from thunderbird_anchor_dates import KNOWN_BOOKINGS

        backend = get_backend()
        t_lines = []

        # Gather active client keys from bookings
        active_clients = set()
        for bk_key, bk in KNOWN_BOOKINGS.items():
            name = bk_key.split("_")[0].lower()
            active_clients.add(name)

        # Detect preference shifts across all active clients (90-day window)
        for client_key in sorted(active_clients):
            shifts = backend.detect_preference_shifts(entity=client_key, window_days=90)
            for s in shifts:
                t_lines.append(
                    f"<li><strong>{client_key.title()}</strong> — "
                    f"{s['attribute']}: {s.get('old_value', '?')} &rarr; "
                    f"{s.get('new_value', '?')} ({s.get('changed_at', '?')[:10]})</li>"
                )

        # Upcoming milestones: birthdays/anniversaries within 30 days
        milestone_attrs = ("birthday", "anniversary")
        for client_key in sorted(active_clients):
            for attr in milestone_attrs:
                facts = backend.get_fact_history(entity=client_key, limit=5)
                for f in facts:
                    if f.get("attribute") != attr or f.get("valid_to") is not None:
                        continue
                    val = f.get("value", "")
                    # Try to detect month-day proximity
                    try:
                        date_str = val.split(":")[-1].strip() if ":" in val else val
                        md = datetime.strptime(date_str, "%Y-%m-%d")
                        this_year = md.replace(year=today.year)
                        delta = (this_year - datetime.combine(today, datetime.min.time())).days
                        if 0 <= delta <= 30:
                            t_lines.append(
                                f"<li><strong>{client_key.title()}</strong> — "
                                f"{attr}: {val} (in {delta} days)</li>"
                            )
                    except Exception:
                        pass

        if t_lines:
            temporal_intel = "<ul>" + "\n".join(t_lines) + "</ul>"
            logger.info(f"  Temporal intelligence: {len(t_lines)} items")

    except Exception as e:
        logger.debug(f"Temporal intelligence skipped: {e}")

    # Fetch heartbeat scan findings — overdue suspenses, aging P0/P1, stale CI
    # (the validated process layer built 2026-07-04; primary login signal)
    logger.info("Fetching heartbeat scan findings...")
    heartbeat = fetch_heartbeat_findings()
    logger.info(f"  {len(heartbeat.get('findings', []))} findings, scanned {heartbeat.get('scanned_at', 'never')}")

    # Build executive summary
    summary = build_executive_summary(
        commander_log, intel_log, pricing, tech_news, fare_log, anchor_report, today,
        rss_direct=rss_direct,
        recon_line=recon_line,
        product_digest=product_digest,
        heartbeat=heartbeat,
    )

    # Scan overnight routine outputs
    logger.info("Scanning overnight file outputs...")
    overnight_outputs = fetch_overnight_outputs()
    system_status = fetch_system_status()
    logger.info(f"  {len(overnight_outputs)} files, {len(system_status.get('preflight',[]))} system checks")

    # Render HTML
    logger.info("Rendering briefing HTML...")
    html = render_briefing_html(
        summary, commander_log, intel_log, pricing,
        tech_news, fare_log, anchor_report, is_weekly=weekly,
        completed_actions=completed_actions,
        rss_direct=rss_direct,
        intel_crew_report=intel_crew_report,
        temporal_intel=temporal_intel,
        overnight_outputs=overnight_outputs,
        system_status=system_status,
    )

    # Save dedup cache
    _save_sent_cache(cache)

    if preview:
        # Save locally
        out_path = PREVIEW_DIR / f"briefing_{'weekly' if weekly else 'daily'}_{now.strftime('%Y%m%d_%H%M')}.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"Preview saved: {out_path}")
        return str(out_path)
    else:
        # Send JSON briefing with links
        if weekly:
            subject = f"THUNDERBIRD WEEKLY DIGEST // {today.strftime('%B %d, %Y')}"
        else:
            emoji = {"RED": "🔴", "GOLD": "🟡", "GREEN": "🟢"}.get(summary["alert_level"], "")
            subject = f"{emoji} THUNDERBIRD BRIEFING // {today.strftime('%b %d')} — {summary['alert_text']}"

        # Send HTML email to Commander with full briefing
        try:
            send_briefing_email(html, subject)
            logger.info(f"Briefing email sent: {subject}")
        except Exception as e:
            logger.warning(f"Briefing email failed (non-fatal): {e}")

        # Also send JSON summary
        send_briefing_json(intel_log, pricing, tech_news, subject)

        # Telegram C2 digest SUPPRESSED — brief goes to email (johnloucks3 direct send).
        # D2MC2C is P0 action alerts only. Morning brief = email channel per doctrine 2026-06-19.
        return subject


# ---------------------------------------------------------------------------
# MCP TOOL REGISTRATION
# ---------------------------------------------------------------------------

def register_briefing_tools(mcp):
    """Register morning briefing tools with MCP server."""

    @mcp.tool()
    async def send_morning_briefing(
        preview: bool = False,
        weekly: bool = False,
    ) -> str:
        """Send or preview the Thunderbird Morning Briefing email.

        Pulls ALL intelligence (world events, cruise pricing, tech news, fare watches,
        anchor dates) into a branded HTML email and sends to Commander.

        Args:
            preview: If True, save HTML locally instead of sending
            weekly: If True, send weekly digest format
        """
        result = run_briefing(preview=preview, weekly=weekly)
        return json.dumps({"status": "success", "result": result})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Morning Briefing")
    parser.add_argument("--preview", action="store_true", help="Save HTML locally, don't send")
    parser.add_argument("--weekly", action="store_true", help="Weekly digest mode")
    parser.add_argument("--force", action="store_true", help="Ignore send-lock (testing only)")
    args = parser.parse_args()

    # Send-lock guard is now inside run_briefing()
    try:
        result = run_briefing(preview=args.preview, weekly=args.weekly, force=args.force)
        print(f"Done: {result}", file=sys.stderr)
    except Exception as e:
        logger.error(f"Briefing FAILED: {e}", exc_info=True)
        sys.exit(1)

