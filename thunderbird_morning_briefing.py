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
import base64
import argparse
import urllib.parse
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

THUNDERBIRD_DIR = Path(__file__).parent
SENT_CACHE = THUNDERBIRD_DIR / "briefing_sent.json"
PREVIEW_DIR = THUNDERBIRD_DIR / "output"
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo_email.png"
HEADSHOT_FILE = THUNDERBIRD_DIR / "John_Headshot.jpg"

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SA_CREDS = THUNDERBIRD_DIR / "credentials.json"
GMAIL_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"
GMAIL_OAUTH = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
USER_EMAIL = "johnloucks3@gmail.com"
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
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
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
    return f"mailto:{USER_EMAIL}?subject={subject}&body={body}"


def _mailto_snooze_link(booking_key: str, anchor_label: str) -> str:
    """Generate a mailto: link that snoozes an item for 7 days."""
    subject = urllib.parse.quote(f"[A3] SNOOZE: {booking_key} — {anchor_label}")
    body = urllib.parse.quote(
        f"Snooze 7 days:\nBooking: {booking_key}\nMilestone: {anchor_label}\n\n"
        f"(Sent from Thunderbird Briefing — Star Protocol will process)"
    )
    return f"mailto:{USER_EMAIL}?subject={subject}&body={body}"


def fetch_anchor_dates_upcoming() -> dict:
    """Get upcoming anchor dates from KNOWN_BOOKINGS."""
    try:
        from thunderbird_anchor_dates import KNOWN_BOOKINGS, compute_anchors, scan_all_bookings_due
        all_anchors = {}
        for key, bk in KNOWN_BOOKINGS.items():
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk.get("hard_dates"), key,
            )
            all_anchors[key] = anchors
        return scan_all_bookings_due(all_anchors)
    except Exception as e:
        logger.error(f"Anchor dates fetch failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# DIRECT RSS FEED FETCHER
# ---------------------------------------------------------------------------

# Domain category mapping for RSS sources
_SOURCE_CATEGORIES = {
    "Cruise Critic": "Cruise", "Seatrade Cruise News": "Cruise",
    "Travel Weekly": "Cruise", "Cruise Industry News": "Cruise",
    "Cruise Hive": "Cruise", "Cruise Mapper": "Cruise",
    "ISW": "War/Geopolitics", "RealClearDefense": "War/Geopolitics",
    "RealClearWorld": "War/Geopolitics", "Defense One": "War/Geopolitics",
    "War on the Rocks": "War/Geopolitics",
    "RealClearPolitics": "Politics", "RealClearPolicy": "Politics",
    "The Hill": "Politics",
    "Simple Flying": "Airline", "Routes Online": "Airline",
    "The Points Guy Airlines": "Airline", "Cranky Flier": "Airline",
    "The Maritime Executive": "Maritime", "gCaptain": "Maritime",
    "TradeWinds": "Maritime",
    "RealClearMarkets": "Markets", "RealClearEnergy": "Markets",
    "Skift": "Travel", "Travel Pulse": "Travel",
}


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

def build_executive_summary(
    commander_log, intel_log, pricing, tech_news, fare_log, anchor_report, today,
    rss_direct=None,
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

    # Determine alert level
    if overdue > 0 or due_today > 0:
        alert_level = "RED"
        alert_icon = "&#9888;"  # warning triangle
        alert_text = f"{overdue + due_today} ACTION ITEMS NEED ATTENTION"
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
        "alert_level": alert_level,
        "alert_icon": alert_icon,
        "alert_text": alert_text,
    }


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
) -> str:
    """Render the full briefing as branded HTML email."""

    logo_uri = _img_base64(LOGO_FILE)
    headshot_uri = _img_base64(HEADSHOT_FILE)
    today = datetime.now()

    # Alert color mapping
    alert_colors = {
        "RED": ("#ff4444", "#2a0a0a", "#ff6666"),
        "GOLD": ("#c9a84c", "#1a1400", "#e8c97a"),
        "GREEN": ("#44aa44", "#0a1a0a", "#66cc66"),
    }
    ac = alert_colors.get(summary["alert_level"], alert_colors["GREEN"])

    briefing_type = "WEEKLY INTELLIGENCE DIGEST" if is_weekly else "MORNING BRIEFING"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #080d14;
    color: #e0e6ed;
    line-height: 1.6;
  }}

  .container {{
    max-width: 700px;
    margin: 0 auto;
    background: #0d1b2e;
  }}

  /* HEADER */
  .header {{
    background: linear-gradient(135deg, #0d1b2e 0%, #152540 50%, #1e3358 100%);
    padding: 32px 28px 20px;
    border-bottom: 3px solid #c9a84c;
    position: relative;
    overflow: hidden;
  }}

  .header::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%);
    border-radius: 50%;
  }}

  .header-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }}

  .logo-block {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .logo-block img {{
    height: 50px;
    border-radius: 6px;
  }}

  .brand-text {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: #c9a84c;
    font-weight: 600;
  }}

  .briefing-title {{
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin: 8px 0 4px;
  }}

  .briefing-date {{
    font-size: 14px;
    color: #8a9ab5;
    font-weight: 400;
  }}

  .briefing-tag {{
    display: inline-block;
    background: rgba(201,168,76,0.15);
    color: #e8c97a;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid rgba(201,168,76,0.3);
    margin-top: 4px;
  }}

  /* ALERT BANNER */
  .alert-banner {{
    background: {ac[1]};
    border-left: 4px solid {ac[0]};
    padding: 16px 24px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .alert-icon {{
    font-size: 24px;
    color: {ac[0]};
  }}

  .alert-text {{
    font-size: 14px;
    font-weight: 600;
    color: {ac[2]};
    text-transform: uppercase;
    letter-spacing: 1px;
  }}

  /* STATS BAR */
  .stats-bar {{
    display: flex;
    background: #152540;
    border-bottom: 1px solid rgba(201,168,76,0.2);
  }}

  .stat-item {{
    flex: 1;
    text-align: center;
    padding: 14px 8px;
    border-right: 1px solid rgba(201,168,76,0.1);
  }}

  .stat-item:last-child {{ border-right: none; }}

  .stat-number {{
    font-size: 22px;
    font-weight: 700;
    color: #e8c97a;
    display: block;
  }}

  .stat-label {{
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #6b7c99;
    margin-top: 2px;
  }}

  /* SECTIONS */
  .section {{
    padding: 24px 28px;
    border-bottom: 1px solid rgba(201,168,76,0.12);
  }}

  .section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }}

  .section-icon {{
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }}

  .section-title {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #c9a84c;
  }}

  .section-count {{
    font-size: 11px;
    color: #6b7c99;
    margin-left: auto;
  }}

  /* ANCHOR DATE CARDS */
  .anchor-card {{
    background: #152540;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 3px solid #c9a84c;
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .anchor-card.overdue {{
    border-left-color: #ff4444;
    background: #1a0f0f;
  }}

  .anchor-card.today {{
    border-left-color: #ff8800;
    background: #1a1508;
  }}

  .anchor-date {{
    font-size: 12px;
    font-weight: 600;
    color: #e8c97a;
    white-space: nowrap;
    min-width: 80px;
  }}

  .anchor-label {{
    font-size: 13px;
    color: #c8d0dc;
  }}

  .anchor-booking {{
    font-size: 11px;
    color: #6b7c99;
    display: block;
  }}

  .anchor-category {{
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: auto;
    white-space: nowrap;
  }}

  .cat-payment {{ background: rgba(255,68,68,0.2); color: #ff6666; }}
  .cat-milestone {{ background: rgba(201,168,76,0.2); color: #e8c97a; }}
  .cat-documents {{ background: rgba(68,170,255,0.2); color: #66aaff; }}
  .cat-insurance {{ background: rgba(170,68,255,0.2); color: #aa88ff; }}
  .cat-client_care {{ background: rgba(68,255,170,0.2); color: #66ffaa; }}
  .cat-deliverable {{ background: rgba(255,170,68,0.2); color: #ffaa66; }}
  .cat-operations {{ background: rgba(255,255,68,0.2); color: #dddd66; }}
  .cat-business {{ background: rgba(68,200,200,0.2); color: #66cccc; }}
  .cat-supplier {{ background: rgba(200,100,100,0.2); color: #dd8888; }}

  /* INTEL SOURCE BLOCKS */
  .source-block {{
    margin-bottom: 16px;
  }}

  .source-name {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #8a9ab5;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(138,154,181,0.2);
    margin-bottom: 8px;
  }}

  .intel-item {{
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }}

  .intel-item:last-child {{ border-bottom: none; }}

  .intel-item a {{
    color: #c8d0dc;
    text-decoration: none;
    font-size: 13px;
    line-height: 1.5;
    transition: color 0.2s;
  }}

  .intel-item a:hover {{ color: #e8c97a; }}

  .intel-meta {{
    font-size: 10px;
    color: #4a5a75;
    margin-top: 2px;
  }}

  /* PRICING TABLE */
  .price-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
  }}

  .price-table th {{
    text-align: left;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #6b7c99;
    padding: 8px 10px;
    border-bottom: 1px solid rgba(201,168,76,0.2);
  }}

  .price-table td {{
    font-size: 13px;
    padding: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: #c8d0dc;
  }}

  .price-amount {{
    color: #e8c97a;
    font-weight: 600;
  }}

  .price-change-up {{ color: #ff6666; }}
  .price-change-down {{ color: #66ff66; }}

  /* TECH NEWS */
  .tech-item {{
    display: flex;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    align-items: baseline;
  }}

  .tech-badge {{
    font-size: 8px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 10px;
    background: rgba(100,100,255,0.15);
    color: #8888ff;
    white-space: nowrap;
  }}

  .tech-title {{
    font-size: 13px;
    color: #c8d0dc;
  }}

  .tech-source {{
    font-size: 10px;
    color: #4a5a75;
  }}

  /* FOOTER */
  .footer {{
    background: #080d14;
    padding: 24px 28px;
    text-align: center;
  }}

  .footer-brand {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: #4a5a75;
    margin-bottom: 8px;
  }}

  .footer-line {{
    font-size: 11px;
    color: #3a4a65;
    font-style: italic;
  }}

  .divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(201,168,76,0.3), transparent);
    margin: 0 28px;
  }}

  .new-badge {{
    display: inline-block;
    font-size: 8px;
    font-weight: 700;
    background: rgba(68,255,68,0.2);
    color: #66ff66;
    padding: 1px 6px;
    border-radius: 8px;
    margin-left: 6px;
    text-transform: uppercase;
    letter-spacing: 1px;
    vertical-align: middle;
  }}
</style>
</head>
<body>
<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="header-top">
      <div class="logo-block">
        {"<img src='" + logo_uri + "' alt='D2M'>" if logo_uri else ""}
        <div>
          <div class="brand-text">Dreams2Memories Travel</div>
          <div class="briefing-title">THUNDERBIRD {briefing_type}</div>
          <div class="briefing-date">{summary['date_display']}</div>
        </div>
      </div>
    </div>
    <div class="briefing-tag">CLASSIFIED // COMMANDER EYES ONLY</div>
  </div>

  <!-- ALERT BANNER -->
  <div class="alert-banner">
    <span class="alert-icon">{summary['alert_icon']}</span>
    <span class="alert-text">{summary['alert_text']}</span>
  </div>

  <!-- STATS BAR -->
  <div class="stats-bar">
    <div class="stat-item">
      <span class="stat-number">{summary['overdue'] + summary['due_today']}</span>
      <div class="stat-label">Action Items</div>
    </div>
    <div class="stat-item">
      <span class="stat-number">{summary['due_week']}</span>
      <div class="stat-label">This Week</div>
    </div>
    <div class="stat-item">
      <span class="stat-number">{summary['total_commander']}</span>
      <div class="stat-label">World Intel</div>
    </div>
    <div class="stat-item">
      <span class="stat-number">{summary['total_intel']}</span>
      <div class="stat-label">RSS Items</div>
    </div>
    <div class="stat-item">
      <span class="stat-number">{summary.get('total_rss_direct', 0)}</span>
      <div class="stat-label">Live Feeds</div>
    </div>
    <div class="stat-item">
      <span class="stat-number">{summary['total_pricing']}</span>
      <div class="stat-label">Fares Tracked</div>
    </div>
  </div>
"""

    # ── SECTION 1: ANCHOR DATES ──
    if completed_actions is None:
        completed_actions = set()
    done_count = 0
    anchor_items = []
    for bucket, css_class in [("overdue", "overdue"), ("due_today", "today"), ("due_this_week", ""), ("due_next_week", "")]:
        for item in anchor_report.get(bucket, []):
            bkey = item.get("booking", "").strip()
            label = item.get("label", "").strip()
            if (bkey, label) in completed_actions:
                done_count += 1
                continue
            anchor_items.append((item, css_class, bucket))

    if anchor_items or done_count > 0:
        done_badge = f' <span style="font-size:10px;color:#66ff66;margin-left:8px;">({done_count} completed)</span>' if done_count > 0 else ""
        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(255,136,0,0.15);">&#128197;</div>
      <div class="section-title">Anchor Date Pipeline""" + done_badge + """</div>
      <div class="section-count">""" + str(len(anchor_items)) + """ active</div>
    </div>
"""
        for item, css_class, bucket in anchor_items:
            cat = item.get("category", "")
            cat_css = f"cat-{cat}" if cat else ""
            booking_key = item.get("booking", "").strip()
            anchor_label = item.get("label", "").strip()
            booking_short = booking_key.replace("_", " ").split("|")[0].strip()
            done_link = _mailto_done_link(booking_key, anchor_label)
            snooze_link = _mailto_snooze_link(booking_key, anchor_label)
            html += f"""
    <div class="anchor-card {css_class}">
      <div class="anchor-date">{item.get('date', '')}</div>
      <div style="flex:1;">
        <div class="anchor-label">{anchor_label}</div>
        <span class="anchor-booking">{booking_short}</span>
      </div>
      <span class="anchor-category {cat_css}">{cat}</span>
      <a href="{done_link}" style="display:inline-block;background:rgba(68,255,68,0.15);color:#66ff66;font-size:10px;font-weight:700;padding:4px 10px;border-radius:12px;text-decoration:none;margin-left:6px;border:1px solid rgba(68,255,68,0.3);" title="Mark Done">&#10004; DONE</a>
      <a href="{snooze_link}" style="display:inline-block;background:rgba(255,170,68,0.15);color:#ffaa66;font-size:10px;font-weight:700;padding:4px 10px;border-radius:12px;text-decoration:none;margin-left:4px;border:1px solid rgba(255,170,68,0.3);" title="Snooze 7 days">&#128164; SNOOZE</a>
    </div>
"""
        html += "  </div>\n  <div class='divider'></div>\n"

    # ── SECTION 2: WORLD INTELLIGENCE (Commander_Log) ──
    if commander_log:
        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(68,170,255,0.15);">&#127758;</div>
      <div class="section-title">World Intelligence</div>
      <div class="section-count">""" + str(len(commander_log)) + """ dispatches</div>
    </div>
"""
        # Show only new items (deduped), newest first
        for entry in reversed(commander_log):
            content = entry.get("content", "")
            sources = _parse_commander_content(content)
            ts = entry.get("timestamp", "")

            for src in sources:
                if not src["items"]:
                    continue
                html += f'    <div class="source-block">\n'
                html += f'      <div class="source-name">{src["source"]} <span style="font-weight:400;color:#3a4a65">// {ts[:10]}</span></div>\n'
                for item in src["items"][:5]:  # Top 5 per source
                    title = item["title"]
                    url = item["url"]
                    if url:
                        html += f'      <div class="intel-item"><a href="{url}">{title}</a></div>\n'
                    else:
                        html += f'      <div class="intel-item"><span style="color:#c8d0dc">{title}</span></div>\n'
                html += '    </div>\n'

        html += "  </div>\n  <div class='divider'></div>\n"

    # ── SECTION 3: CRUISE PRICING TRACKER ──
    if pricing:
        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(201,168,76,0.15);">&#128176;</div>
      <div class="section-title">Cruise Pricing Tracker</div>
      <div class="section-count">""" + str(len(pricing)) + """ voyages</div>
    </div>
    <table class="price-table">
      <tr>
        <th>Cruise Line</th>
        <th>Voyage</th>
        <th>Price</th>
        <th>Change</th>
      </tr>
"""
        for p in pricing:
            line = p.get("Cruise Line", "")
            voyage = p.get("Voyage ID", p.get("Ship", ""))
            price = p.get("New Price", p.get("Price", ""))
            change = p.get("Change %", "")
            change_css = ""
            if change:
                try:
                    val = float(change.replace("%", "").replace("+", ""))
                    change_css = "price-change-up" if val > 0 else "price-change-down"
                except ValueError:
                    pass

            html += f"""      <tr>
        <td>{line}</td>
        <td>{voyage[:50]}</td>
        <td class="price-amount">{price}</td>
        <td class="{change_css}">{change or '—'}</td>
      </tr>
"""
        html += "    </table>\n  </div>\n  <div class='divider'></div>\n"

    # ── SECTION 4: TECH NEWS ──
    if tech_news:
        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(100,100,255,0.15);">&#128187;</div>
      <div class="section-title">Tech Monitor</div>
      <div class="section-count">""" + str(len(tech_news)) + """ articles</div>
    </div>
"""
        seen_titles = set()
        for t in tech_news:
            title = t.get("Title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            source = t.get("Source", "")
            category = t.get("Category", "")
            html += f"""    <div class="tech-item">
      <span class="tech-badge">{category}</span>
      <div>
        <div class="tech-title">{title}</div>
        <div class="tech-source">{source}</div>
      </div>
    </div>
"""
        html += "  </div>\n  <div class='divider'></div>\n"

    # ── SECTION 5: FARE LOG ──
    if fare_log:
        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(68,255,170,0.15);">&#128200;</div>
      <div class="section-title">Fare Watch Log</div>
      <div class="section-count">""" + str(len(fare_log)) + """ entries</div>
    </div>
    <table class="price-table">
      <tr>
"""
        if fare_log:
            for key in list(fare_log[0].keys())[:5]:
                html += f"        <th>{key}</th>\n"
            html += "      </tr>\n"
            for f in fare_log[-10:]:  # Last 10
                html += "      <tr>\n"
                for key in list(fare_log[0].keys())[:5]:
                    html += f"        <td>{f.get(key, '')}</td>\n"
                html += "      </tr>\n"
        html += "    </table>\n  </div>\n"

    # ── SECTION 5b: LIVE INTELLIGENCE FEEDS (direct RSS) ──
    if rss_direct:
        # Group articles by category
        by_cat: dict[str, list] = {}
        for art in rss_direct:
            cat = art.get("category", "Other")
            by_cat.setdefault(cat, []).append(art)

        # Desired display order
        cat_order = ["Cruise", "War/Geopolitics", "Politics", "Airline",
                      "Maritime", "Markets", "Travel", "Other"]
        sorted_cats = [c for c in cat_order if c in by_cat]
        # Append any categories not in the order list
        for c in by_cat:
            if c not in sorted_cats:
                sorted_cats.append(c)

        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(68,200,200,0.15);">&#128752;</div>
      <div class="section-title">Live Intelligence Feeds</div>
      <div class="section-count">""" + str(len(rss_direct)) + """ articles (direct RSS)</div>
    </div>
"""
        for cat in sorted_cats:
            items = by_cat[cat]
            html += f'    <div class="source-block">\n'
            html += f'      <div class="source-name">{cat} <span style="font-weight:400;color:#3a4a65">// {len(items)} articles</span></div>\n'
            for art in items:
                title = art.get("title", "")
                url = art.get("url", "")
                src = art.get("source", "")
                pub = art.get("published", "")
                summary_snip = art.get("summary", "")[:500]
                rel = art.get("relevance_score", 1)
                border_style = "border-left:3px solid #c9a84c;padding-left:10px;" if rel >= 3 else ""
                if url:
                    html += f'      <div class="intel-item" style="{border_style}"><a href="{url}">{title}</a>'
                else:
                    html += f'      <div class="intel-item" style="{border_style}"><span style="color:#c8d0dc">{title}</span>'
                html += f'<div class="intel-meta">{src} // {pub}</div>\n'
                if summary_snip:
                    html += f'        <div style="font-size:12px;color:#8a9ab5;margin-top:4px;line-height:1.5;">{summary_snip}</div>\n'
                html += '      </div>\n'
            html += '    </div>\n'

        html += "  </div>\n  <div class='divider'></div>\n"

    # ── SECTION 6: RSS INTEL (sampled) ──
    if intel_log:
        # Group by source, show latest unique items
        by_source = {}
        for item in reversed(intel_log):
            src = item.get("source", "Unknown")
            if src not in by_source:
                by_source[src] = []
            if len(by_source[src]) < 5:
                headline = item.get("headline", item.get("line", ""))
                if headline and headline not in [x["headline"] for x in by_source[src]]:
                    by_source[src].append(item)

        html += """
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(255,170,68,0.15);">&#128225;</div>
      <div class="section-title">RSS Intelligence Feed</div>
      <div class="section-count">""" + str(len(intel_log)) + """ items (top per source)</div>
    </div>
"""
        for src, items in by_source.items():
            html += f'    <div class="source-block">\n'
            html += f'      <div class="source-name">{src}</div>\n'
            for item in items:
                headline = item.get("headline", item.get("line", ""))
                url = item.get("url", "")
                ts = item.get("timestamp", "")
                if url:
                    html += f'      <div class="intel-item"><a href="{url}">{headline}</a><div class="intel-meta">{ts}</div></div>\n'
                else:
                    html += f'      <div class="intel-item"><span style="color:#c8d0dc">{headline}</span><div class="intel-meta">{ts}</div></div>\n'
            html += '    </div>\n'

        html += "  </div>\n"

    # ── FOOTER ──
    html += f"""
  <div class="footer">
    <div class="footer-brand">Thunderbird OS // Dreams2Memories Travel, LLC</div>
    <div class="footer-line">Generated {today.strftime('%Y-%m-%d %H:%M:%S')} MT</div>
    <div class="footer-line" style="margin-top:4px;font-size:10px;color:#2a3a55;">
      Curating the experience of a lifetime
    </div>
  </div>

</div>
</body>
</html>"""

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


def send_briefing_email(html_content: str, subject: str):
    """Send the briefing as an HTML email to Commander."""
    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["To"] = USER_EMAIL
    msg["From"] = USER_EMAIL
    msg["Subject"] = subject

    # Plain text fallback
    plain = f"Thunderbird Briefing — {datetime.now().strftime('%B %d, %Y')}\nView in HTML-capable email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    logger.info(f"Briefing SENT to {USER_EMAIL}: {subject}")


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_briefing(preview: bool = False, weekly: bool = False):
    """Execute the full briefing pipeline."""
    today = date.today()
    now = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"THUNDERBIRD {'WEEKLY' if weekly else 'MORNING'} BRIEFING — {today}")
    logger.info(f"{'='*60}")

    # Load dedup cache
    cache = _load_sent_cache()

    # Fetch all data sources
    logger.info("Connecting to Google Sheets...")
    gc = _get_sheets_client()

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

    logger.info("Fetching direct RSS feeds...")
    rss_direct = fetch_direct_rss_feeds()
    logger.info(f"  {len(rss_direct)} articles from live feeds")

    # Build executive summary
    summary = build_executive_summary(
        commander_log, intel_log, pricing, tech_news, fare_log, anchor_report, today,
        rss_direct=rss_direct,
    )

    # Render HTML
    logger.info("Rendering briefing HTML...")
    html = render_briefing_html(
        summary, commander_log, intel_log, pricing,
        tech_news, fare_log, anchor_report, is_weekly=weekly,
        completed_actions=completed_actions,
        rss_direct=rss_direct,
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
        # Send email
        if weekly:
            subject = f"THUNDERBIRD WEEKLY DIGEST // {today.strftime('%B %d, %Y')}"
        else:
            emoji = {"RED": "🔴", "GOLD": "🟡", "GREEN": "🟢"}.get(summary["alert_level"], "")
            subject = f"{emoji} THUNDERBIRD BRIEFING // {today.strftime('%b %d')} — {summary['alert_text']}"
        send_briefing_email(html, subject)
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
    args = parser.parse_args()

    try:
        result = run_briefing(preview=args.preview, weekly=args.weekly)
        print(f"Done: {result}", file=sys.stderr)
    except Exception as e:
        logger.error(f"Briefing FAILED: {e}", exc_info=True)
        sys.exit(1)
