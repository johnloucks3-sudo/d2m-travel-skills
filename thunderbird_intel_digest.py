#!/usr/bin/env python3
"""
Thunderbird Intel Digest — Colossal Twice-Daily Briefing
Dreams2Memories Travel, LLC

Scrapes X/Twitter OSINT feeds, combines with ship intel, world intel,
fare watches, anchor dates — analyzes via Claude Opus, emails to Commander.

Runs at 0600 and 1800 MT via cron.

Usage:
  python3 thunderbird_intel_digest.py              # Send digest email
  python3 thunderbird_intel_digest.py --preview     # Save HTML locally
  python3 thunderbird_intel_digest.py --scrape-only  # Just scrape X, print results
"""

import json
import asyncio
import logging
import sys
import base64
import argparse
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(__file__).parent
FOLLOW_LIST = THUNDERBIRD_DIR / "x_osint_follow_list.txt"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo_email.png"
HEADSHOT_FILE = THUNDERBIRD_DIR / "John_Headshot.jpg"
DEDUP_CACHE = THUNDERBIRD_DIR / "intel_digest_sent.json"


GMAIL_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"
GMAIL_OAUTH = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
USER_EMAIL = "johnloucks3@gmail.com"
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.modify"]

PROFILE_NAME = "x_twitter"
PROFILES_DIR = THUNDERBIRD_DIR / "browser_profiles"

logger = logging.getLogger("intel_digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INTEL] %(message)s",
    stream=sys.stderr,
)


# ---------------------------------------------------------------------------
# GMAIL SERVICE
# ---------------------------------------------------------------------------

def _get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN), SCOPES_GMAIL)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# X/TWITTER SCRAPER (Playwright direct)
# ---------------------------------------------------------------------------

def load_follow_list():
    accounts = []
    with open(FOLLOW_LIST, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                accounts.append(line)
    return accounts


async def scrape_x_account(context, handle, max_length=5000):
    """Scrape a single X account, return dict with content + links."""
    url = f"https://x.com/{handle}"
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        title = await page.title()

        # Check if session is dead early
        quick_text = await page.evaluate("document.body.innerText.substring(0, 200)")
        if "Log in" in (title or "") or "Sign in" in quick_text:
            return {
                "handle": handle,
                "status": "error",
                "error": "Session expired",
                "content": "",
                "posts": [],
                "links": [],
            }

        # Extract the 3 most recent ACTUAL POSTS from article elements
        posts = await page.evaluate("""
            () => {
                var articles = document.querySelectorAll('article[data-testid="tweet"]');
                var results = [];
                for (var i = 0; i < Math.min(articles.length, 3); i++) {
                    var art = articles[i];

                    // Get post text
                    var textEl = art.querySelector('[data-testid="tweetText"]');
                    var text = textEl ? textEl.innerText.trim() : '';

                    // Get author
                    var userEl = art.querySelector('[data-testid="User-Name"]');
                    var user = userEl ? userEl.innerText.trim() : '';

                    // Get timestamp
                    var timeEl = art.querySelector('time');
                    var timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
                    var timeDisplay = timeEl ? timeEl.innerText.trim() : '';

                    // Get tweet permalink
                    var linkEl = timeEl ? timeEl.closest('a') : null;
                    var permalink = linkEl ? linkEl.href : '';

                    // Get any embedded links (articles, external URLs)
                    var embeddedLinks = [];
                    var cardLinks = art.querySelectorAll('a[href]');
                    for (var j = 0; j < cardLinks.length; j++) {
                        var href = cardLinks[j].href;
                        var linkText = cardLinks[j].innerText.trim().substring(0, 120);
                        if (href.startsWith('http') &&
                            !href.includes('/status/') &&
                            !href.includes('x.com/search') &&
                            !href.includes('x.com/hashtag') &&
                            !href.includes('/photo/') &&
                            linkText.length > 2) {
                            embeddedLinks.push({text: linkText, url: href});
                        }
                    }

                    // Get engagement metrics
                    var metrics = '';
                    var metricEls = art.querySelectorAll('[data-testid="reply"], [data-testid="retweet"], [data-testid="like"]');

                    if (text) {
                        results.push({
                            text: text.substring(0, 1000),
                            author: user.split('\\n')[0],
                            time: timeDisplay,
                            timestamp: timestamp,
                            permalink: permalink,
                            links: embeddedLinks.slice(0, 5)
                        });
                    }
                }
                return results;
            }
        """)

        # Flatten all links from posts for the links array
        all_links = []
        for post in posts:
            if post.get("permalink"):
                all_links.append({"text": "[tweet]", "url": post["permalink"]})
            for link in post.get("links", []):
                all_links.append(link)

        # Build clean content from posts
        content_lines = []
        for idx, post in enumerate(posts):
            content_lines.append(f"[{post.get('time', '?')}] {post.get('text', '')}")
            for link in post.get("links", []):
                content_lines.append(f"  -> {link['text'][:60]}: {link['url']}")

        return {
            "handle": handle,
            "status": "ok",
            "content": "\n\n".join(content_lines),
            "posts": posts,
            "links": all_links,
            "url": url,
        }

    except Exception as e:
        return {
            "handle": handle,
            "status": "error",
            "error": str(e),
            "content": "",
            "links": [],
        }
    finally:
        await page.close()


async def scrape_all_x_feeds():
    """Scrape all X accounts from follow list."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    accounts = load_follow_list()
    logger.info(f"Scraping {len(accounts)} X accounts...")

    results = []
    async with Stealth().use_async(async_playwright()) as p:
        profile_dir = PROFILES_DIR / PROFILE_NAME
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        for handle in accounts:
            logger.info(f"  Scraping @{handle}...")
            result = await scrape_x_account(context, handle)
            results.append(result)
            # Be polite — 2 sec between requests
            await asyncio.sleep(2)

        await context.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    logger.info(f"Done: {ok}/{len(results)} accounts scraped successfully")
    return results


# ---------------------------------------------------------------------------
# OPUS ANALYZER (via Claude CLI subprocess)
# ---------------------------------------------------------------------------

async def summarize_feeds(raw_feeds):
    """Send raw feeds to Claude Opus for AI full analysis."""
    import subprocess
    import os

    # Build raw text — NO truncation, feed the full content
    raw_text = ""
    for feed in raw_feeds:
        if feed["status"] == "ok":
            raw_text += f"\n\n=== @{feed['handle']} ===\n{feed['content']}"

    if not raw_text.strip():
        return "No feeds available for analysis."

    prompt = f"""You are a senior intelligence analyst. Produce a FULL ANALYSIS from these social media feeds.

RULES:
- Focus on OPERATIONAL FACTS: military movements, strikes, casualties, shipping disruptions, energy prices, travel impacts, space/defense developments, weather threats
- DO NOT editorialize on domestic politics, partisan debates, or culture war topics
- DO NOT include opinion commentary, election takes, or political scandals unless they directly affect defense, travel, or markets
- If a post is purely political opinion with no operational fact, SKIP IT

FORMAT:
1. SITUATION REPORT (3-5 key developments — what happened, where, confirmed facts only)
2. THREAT MATRIX (risks to travel routes, shipping lanes, energy supply, regional stability)
3. MARKET & LOGISTICS (oil prices, shipping suspensions, airport closures, currency moves)
4. WATCH LIST (emerging situations that could escalate in 24-72 hours)
5. SPACE & TECH (any defense tech, space, or cyber developments)

For each item:
- One-line fact summary
- Source: @handle
- Significance: HIGH / MEDIUM / LOW

RAW FEEDS:
{raw_text}"""

    # Strip ANTHROPIC_API_KEY so CLI uses Max plan OAuth ($0)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    cmd = [
        os.path.expanduser("~/.local/bin/claude"),
        "--print",
        "--model", "opus",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=clean_env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            stderr = result.stderr.strip()[:200] if result.stderr else "No stderr"
            logger.error(f"Opus CLI error (exit {result.returncode}): {stderr}")
            return f"[Opus analysis failed: exit {result.returncode}]"
    except subprocess.TimeoutExpired:
        logger.error("Opus CLI timed out after 300s")
        return "[Opus analysis timed out after 300s]"
    except Exception as e:
        logger.error(f"Opus CLI exception: {e}")
        return f"[Opus analysis failed: {e}]"


# ---------------------------------------------------------------------------
# EXISTING THUNDERBIRD DATA SOURCES
# ---------------------------------------------------------------------------

def fetch_sheets_data():
    """Pull data from Google Sheets (same sources as morning briefing)."""
    try:
        import gspread
        from google.oauth2 import service_account

        SA_CREDS = THUNDERBIRD_DIR / "credentials.json"
        SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

        creds = service_account.Credentials.from_service_account_file(
            str(SA_CREDS),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        gc = gspread.authorize(creds)
        wb = gc.open_by_key(SHEET_ID)

        data = {}

        # Intel Log
        try:
            intel_ws = wb.worksheet("Intel_Log")
            rows = intel_ws.get_all_records()
            data["intel_log"] = rows[-50:] if len(rows) > 50 else rows
        except Exception:
            data["intel_log"] = []

        # Pricing Tracker
        try:
            pricing_ws = wb.worksheet("Pricing_Tracker")
            data["pricing"] = pricing_ws.get_all_records()
        except Exception:
            data["pricing"] = []

        # Fare Log
        try:
            fare_ws = wb.worksheet("Fare_Log")
            rows = fare_ws.get_all_records()
            data["fare_log"] = rows[-20:] if len(rows) > 20 else rows
        except Exception:
            data["fare_log"] = []

        # Commander Log
        try:
            cmd_ws = wb.worksheet("Commander_Log")
            rows = cmd_ws.get_all_records()
            data["commander_log"] = rows[-20:] if len(rows) > 20 else rows
        except Exception:
            data["commander_log"] = []

        logger.info(f"Sheets data: {len(data.get('intel_log',[]))} intel, "
                     f"{len(data.get('pricing',[]))} pricing, "
                     f"{len(data.get('fare_log',[]))} fares")
        return data

    except Exception as e:
        logger.error(f"Sheets fetch error: {e}")
        return {"intel_log": [], "pricing": [], "fare_log": [], "commander_log": []}


def fetch_anchor_dates():
    """Pull upcoming anchor dates."""
    try:
        from thunderbird_anchor_dates import scan_all_bookings_due, compute_all_known_anchors
        all_anchors = compute_all_known_anchors()
        return scan_all_bookings_due(all_anchors)
    except Exception as e:
        logger.error(f"Anchor dates error: {e}")
        return {"overdue": [], "due_today": [], "due_this_week": [], "upcoming": []}


# ---------------------------------------------------------------------------
# HTML RENDERER
# ---------------------------------------------------------------------------

def _img_base64(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _clean_feed_text(text):
    """Strip X navigation noise from feed text, keep post content."""
    # Remove common X UI elements
    noise = [
        "To view keyboard shortcuts, press question mark",
        "View keyboard shortcuts",
        "Creator Studio", "Premium", "50% off",
        "Who to follow", "Show more", "Terms of Service",
        "Privacy Policy", "Cookie Policy", "Accessibility",
        "Ads info", "© 2026 X Corp.",
    ]
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        skip = False
        for n in noise:
            if n in line:
                skip = True
                break
        if not skip and len(line) > 3:
            cleaned.append(line)
    return "\n".join(cleaned)


def render_digest_html(ai_summary, x_feeds, sheets_data, anchor_data):
    """Render the colossal intel digest as branded HTML email."""

    logo_uri = _img_base64(LOGO_FILE)
    now = datetime.now()
    period = "0600" if now.hour < 12 else "1800"

    # Count stats
    total_feeds = len([f for f in x_feeds if f["status"] == "ok"])
    total_intel = len(sheets_data.get("intel_log", []))
    total_fares = len(sheets_data.get("fare_log", []))
    overdue = len(anchor_data.get("overdue", []))
    due_today = len(anchor_data.get("due_today", []))

    if overdue > 0 or due_today > 0:
        alert_color = "#ff4444"
        alert_text = f"{overdue + due_today} ACTION ITEMS NEED ATTENTION"
    else:
        alert_color = "#44aa44"
        alert_text = "All clear — no urgent items"

    # --- BUILD HTML ---
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #080d14; color: #e0e6ed; line-height: 1.6; }}
  .container {{ max-width: 750px; margin: 0 auto; background: #0d1b2e; }}
  .header {{ background: linear-gradient(135deg, #0d1b2e 0%, #1e3358 100%); padding: 24px; text-align: center; border-bottom: 3px solid #c9a84c; }}
  .header img {{ height: 50px; margin-bottom: 8px; }}
  .header h1 {{ color: #c9a84c; font-size: 22px; letter-spacing: 2px; margin: 4px 0; }}
  .header .meta {{ color: #8a9ab5; font-size: 13px; }}
  .alert {{ padding: 12px 24px; background: {alert_color}22; border-left: 4px solid {alert_color}; margin: 16px 24px; color: {alert_color}; font-weight: 600; }}
  .section {{ padding: 20px 24px; border-bottom: 1px solid #1e3358; }}
  .section-title {{ color: #c9a84c; font-size: 16px; font-weight: 700; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #c9a84c33; }}
  .summary-box {{ background: #152540; padding: 16px; border-radius: 6px; border: 1px solid #c9a84c44; white-space: pre-wrap; font-size: 14px; line-height: 1.7; }}
  .feed-block {{ background: #0a1520; margin: 12px 0; padding: 14px; border-radius: 4px; border-left: 3px solid #c9a84c; }}
  .feed-handle {{ color: #c9a84c; font-weight: 700; font-size: 14px; margin-bottom: 6px; }}
  .feed-handle a {{ color: #c9a84c; text-decoration: none; }}
  .feed-content {{ font-size: 13px; color: #c8d0dc; white-space: pre-wrap; word-wrap: break-word; max-height: 400px; overflow-y: auto; }}
  .feed-links {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #1e3358; }}
  .feed-links a {{ color: #e8c97a; font-size: 12px; text-decoration: none; display: block; margin: 2px 0; }}
  .feed-links a:hover {{ text-decoration: underline; }}
  .feed-error {{ color: #ff6666; font-style: italic; }}
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 8px 0; }}
  .data-table th {{ background: #1e3358; color: #c9a84c; padding: 6px 10px; text-align: left; }}
  .data-table td {{ padding: 6px 10px; border-bottom: 1px solid #152540; }}
  .data-table tr:nth-child(even) td {{ background: #0a1520; }}
  .anchor-overdue {{ color: #ff4444; font-weight: 600; }}
  .anchor-today {{ color: #c9a84c; font-weight: 600; }}
  .stat-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
  .stat-box {{ background: #152540; padding: 10px 16px; border-radius: 4px; text-align: center; flex: 1; min-width: 100px; }}
  .stat-num {{ color: #e8c97a; font-size: 22px; font-weight: 700; }}
  .stat-label {{ color: #8a9ab5; font-size: 11px; text-transform: uppercase; }}
  .footer {{ padding: 16px 24px; text-align: center; color: #8a9ab5; font-size: 11px; border-top: 1px solid #1e3358; }}
  .pub-hook {{ display: none; }} /* Hidden hooks for future daily/weekly feed publishing */
</style>
</head>
<body>
<div class="container">

<!-- HEADER -->
<div class="header">
  {"<img src='" + logo_uri + "' alt='D2M'>" if logo_uri else ""}
  <h1>THUNDERBIRD INTEL DIGEST</h1>
  <div class="meta">{now.strftime('%A, %B %d, %Y')} &mdash; {period} MT</div>
</div>

<!-- ALERT BAR -->
<div class="alert">{alert_text}</div>

<!-- STATS -->
<div class="section">
  <div class="stat-grid">
    <div class="stat-box"><div class="stat-num">{total_feeds}</div><div class="stat-label">X Feeds</div></div>
    <div class="stat-box"><div class="stat-num">{total_intel}</div><div class="stat-label">Intel Items</div></div>
    <div class="stat-box"><div class="stat-num">{total_fares}</div><div class="stat-label">Fare Watches</div></div>
    <div class="stat-box"><div class="stat-num">{overdue + due_today}</div><div class="stat-label">Action Items</div></div>
  </div>
</div>
"""

    # --- COLLECT ALL POSTS, SORT BY TIME ---
    all_posts = []
    error_feeds = []
    no_posts_feeds = []

    for feed in x_feeds:
        handle = feed["handle"]
        profile_url = f"https://x.com/{handle}"

        if feed["status"] == "ok" and feed.get("posts"):
            for post in feed["posts"]:
                post["_handle"] = handle
                post["_profile_url"] = profile_url
                all_posts.append(post)
            # Publishing hook data
            all_posts[-1]["_pub_hook"] = {
                "handle": handle,
                "scraped": datetime.now().isoformat(),
                "url": profile_url,
                "count": len(feed["posts"]),
            }
        elif feed["status"] == "ok":
            no_posts_feeds.append({"handle": handle, "url": profile_url,
                                    "content": _clean_feed_text(feed.get("content", ""))[:300]})
        else:
            error_feeds.append({"handle": handle, "url": profile_url,
                                "error": feed.get("error", "Unknown error")})

    # Sort by ISO timestamp (newest first), fall back to original order
    def _sort_key(p):
        ts = p.get("timestamp", "")
        if ts:
            return ts
        # Parse relative times: "2h", "5m", "Mar 7", etc — put unknowns at end
        return "0000"

    all_posts.sort(key=_sort_key, reverse=True)

    # --- X/OSINT RAW FEEDS (sorted by time) ---
    html += f"""
<div class="section">
  <div class="section-title">&#128225; X / OSINT FEEDS — {len(all_posts)} posts, sorted newest first</div>
"""
    for post in all_posts:
        handle = post["_handle"]
        profile_url = post["_profile_url"]
        text = post.get("text", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        time_str = post.get("time", "")
        permalink = post.get("permalink", "")

        time_link = f'<a href="{permalink}" target="_blank" style="color:#8a9ab5;text-decoration:none;">{time_str}</a>' if permalink else time_str
        handle_link = f'<a href="{profile_url}" target="_blank" style="color:#c9a84c;text-decoration:none;font-weight:600;">@{handle}</a>'

        html += f'<div style="margin:10px 24px;padding:10px;background:#0a1520;border-radius:4px;border-left:3px solid #c9a84c;">'
        html += f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:12px;">{handle_link}</span><span style="font-size:11px;color:#8a9ab5;">{time_link}</span></div>'
        html += f'<div style="font-size:13px;color:#e0e6ed;white-space:pre-wrap;">{text}</div>'

        if post.get("links"):
            html += '<div style="margin-top:6px;">'
            seen = set()
            for link in post["links"]:
                if link["url"] not in seen:
                    lt = link["text"][:80].replace("&", "&amp;").replace("<", "&lt;")
                    html += f'<a href="{link["url"]}" target="_blank" style="color:#e8c97a;font-size:12px;text-decoration:none;display:block;margin:2px 0;">&#128279; {lt}</a>'
                    seen.add(link["url"])
            html += '</div>'

        html += '</div>'

        # Publishing hook
        if post.get("_pub_hook"):
            ph = post["_pub_hook"]
            html += f'<div class="pub-hook" data-handle="{ph["handle"]}" data-scraped="{ph["scraped"]}" data-url="{ph["url"]}" data-post-count="{ph["count"]}"></div>'

    # Show feeds that had no extractable posts
    for nf in no_posts_feeds:
        cleaned_html = nf["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html += f'<div style="margin:6px 24px;padding:8px;background:#0a1520;border-radius:4px;border-left:3px solid #8a9ab5;">'
        html += f'<span style="color:#8a9ab5;font-size:12px;">@{nf["handle"]} — no structured posts extracted</span></div>'

    # Show error feeds
    for ef in error_feeds:
        html += f'<div style="margin:6px 24px;padding:8px;background:#0a1520;border-radius:4px;border-left:3px solid #ff4444;">'
        html += f'<span style="color:#ff6666;font-size:12px;">@{ef["handle"]} — {ef["error"]}</span></div>'

    html += "</div>"

    # --- AI SUMMARY (before world intel) ---
    # Moved here so it sits between X feeds and Thunderbird data
    html += f"""
<div class="section">
  <div class="section-title">&#9733; AI EXECUTIVE SUMMARY</div>
  <div class="summary-box">{ai_summary}</div>
</div>
"""

    # --- WORLD INTEL LOG ---
    intel = sheets_data.get("intel_log", [])
    if intel:
        html += """
<div class="section">
  <div class="section-title">&#127758; WORLD INTEL LOG</div>
  <table class="data-table">
    <tr><th>Date</th><th>Headline</th><th>Source</th></tr>
"""
        for row in intel[-25:]:
            dt = row.get("Date", row.get("date", ""))
            headline = row.get("Headline", row.get("headline", row.get("line", "")))
            source = row.get("Source", row.get("source", ""))
            url = row.get("URL", row.get("url", ""))
            if url:
                headline = f'<a href="{url}" target="_blank" style="color:#e8c97a">{headline}</a>'
            html += f"    <tr><td>{dt}</td><td>{headline}</td><td>{source}</td></tr>\n"
        html += "  </table>\n</div>"

    # --- SHIP INTEL / PRICING ---
    pricing = sheets_data.get("pricing", [])
    if pricing:
        html += """
<div class="section">
  <div class="section-title">&#128674; SHIP INTEL &amp; PRICING</div>
  <table class="data-table">
    <tr><th>Voyage</th><th>Line</th><th>Price</th><th>Change</th><th>Date Checked</th></tr>
"""
        for row in pricing[-20:]:
            voyage = row.get("Voyage", row.get("voyage", ""))
            line = row.get("Line", row.get("line", ""))
            price = row.get("Price", row.get("price", ""))
            change = row.get("Change", row.get("change", ""))
            checked = row.get("Date", row.get("date", ""))
            html += f"    <tr><td>{voyage}</td><td>{line}</td><td>{price}</td><td>{change}</td><td>{checked}</td></tr>\n"
        html += "  </table>\n</div>"

    # --- FARE WATCHES ---
    fares = sheets_data.get("fare_log", [])
    if fares:
        html += """
<div class="section">
  <div class="section-title">&#128200; FARE WATCH LOG</div>
  <table class="data-table">
    <tr><th>Route</th><th>Price</th><th>Date</th><th>Notes</th></tr>
"""
        for row in fares[-15:]:
            route = row.get("Route", row.get("route", ""))
            price = row.get("Price", row.get("price", ""))
            dt = row.get("Date", row.get("date", ""))
            notes = row.get("Notes", row.get("notes", ""))
            html += f"    <tr><td>{route}</td><td>{price}</td><td>{dt}</td><td>{notes}</td></tr>\n"
        html += "  </table>\n</div>"

    # --- ANCHOR DATES & DEADLINES ---
    overdue_items = anchor_data.get("overdue", [])
    today_items = anchor_data.get("due_today", [])
    week_items = anchor_data.get("due_this_week", [])
    upcoming_items = anchor_data.get("upcoming", [])

    html += """
<div class="section">
  <div class="section-title">&#128197; ANCHOR DATES &amp; DEADLINES</div>
"""
    if overdue_items or today_items or week_items or upcoming_items:
        for item in overdue_items:
            label = item.get("label", item.get("description", ""))
            due = item.get("date", item.get("due_date", ""))
            html += f'  <div class="anchor-overdue">&#9888; OVERDUE: {label} — was due {due}</div>\n'
        for item in today_items:
            label = item.get("label", item.get("description", ""))
            html += f'  <div class="anchor-today">&#9733; DUE TODAY: {label}</div>\n'
        for item in week_items:
            label = item.get("label", item.get("description", ""))
            due = item.get("date", item.get("due_date", ""))
            html += f'  <div style="color:#8a9ab5;margin:4px 0;">&#8226; This week: {label} — {due}</div>\n'
        for item in upcoming_items[:10]:
            label = item.get("label", item.get("description", ""))
            due = item.get("date", item.get("due_date", ""))
            html += f'  <div style="color:#556680;margin:4px 0;">&#8226; Upcoming: {label} — {due}</div>\n'
    else:
        html += '  <div style="color:#8a9ab5;">No anchor dates loaded. Use: update_anchor_dates tool or edit ~/Thunderbird/anchor_dates.json</div>\n'

    html += """
  <div style="margin-top:12px;padding:8px;background:#152540;border-radius:4px;font-size:12px;color:#8a9ab5;">
    To update deadlines: <code style="color:#e8c97a;">python3 thunderbird_anchor_dates.py --refresh</code>
    or reply to this email with new dates and TITAN will process them.
  </div>
</div>
"""

    # --- FOOTER ---
    html += f"""
<div class="footer">
  THUNDERBIRD INTEL DIGEST &mdash; Dreams2Memories Travel, LLC<br>
  Generated {now.strftime('%Y-%m-%d %H:%M')} MT &mdash; {total_feeds} feeds scraped
</div>

<!-- Publishing hooks for future daily/weekly feed -->
<div class="pub-hook" data-digest-id="{now.strftime('%Y%m%d_%H%M')}" data-period="{period}" data-feed-count="{total_feeds}"></div>

</div>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# EMAIL SENDER
# ---------------------------------------------------------------------------

def send_digest_email(html_content, subject):
    """Send the digest as an HTML email to Commander."""
    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["To"] = USER_EMAIL
    msg["From"] = USER_EMAIL
    msg["Subject"] = subject

    plain = f"Thunderbird Intel Digest — {datetime.now().strftime('%B %d, %Y')}\nView in HTML-capable email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Digest SENT to {USER_EMAIL}: {subject}")


# ---------------------------------------------------------------------------
# SMS PING (short alert to phone)
# ---------------------------------------------------------------------------

def send_sms_ping():
    """Send a short SMS that the digest has been emailed."""
    try:
        service = _get_gmail_service()
        sms_msg = MIMEText("Intel Digest delivered. Check email.")
        sms_msg["to"] = "7192910742@tmomail.net"
        sms_msg["from"] = USER_EMAIL
        sms_msg["subject"] = "THUNDERBIRD"
        raw = base64.urlsafe_b64encode(sms_msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("SMS ping sent")
    except Exception as e:
        logger.error(f"SMS ping failed: {e}")


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

async def run_digest(preview=False, scrape_only=False):
    """Execute the full intel digest pipeline."""
    now = datetime.now()
    period = "0600" if now.hour < 12 else "1800"
    logger.info(f"{'='*60}")
    logger.info(f"THUNDERBIRD INTEL DIGEST — {now.strftime('%Y-%m-%d')} {period}")
    logger.info(f"{'='*60}")

    # 1. Scrape X feeds
    logger.info("Phase 1: Scraping X/Twitter feeds...")
    x_feeds = await scrape_all_x_feeds()

    if scrape_only:
        for feed in x_feeds:
            print(f"\n=== @{feed['handle']} ({feed['status']}) ===")
            if feed["status"] == "ok":
                print(_clean_feed_text(feed["content"][:2000]))
                if feed.get("links"):
                    print("\nLinks:")
                    for link in feed["links"][:10]:
                        print(f"  {link['text'][:60]} -> {link['url']}")
            else:
                print(f"  ERROR: {feed.get('error')}")
        return

    # 2. AI Summary
    logger.info("Phase 2: Opus AI analysis...")
    ai_summary = await summarize_feeds(x_feeds)

    # 2b. Intel Crew pipeline (Dembe → Radar → COS review chain)
    logger.info("Phase 2b: Intel Crew persona chain analysis...")
    try:
        from thunderbird_intel_crew import IntelCrew
        crew = IntelCrew()
        crew_result = crew.run()
        if crew_result and crew_result.get("cos_review"):
            crew_text = "\n\n--- CREW ANALYSIS ---\n\n"
            crew_text += f"## A2 Dembe Analysis\n{crew_result.get('analysis', '')}\n\n"
            crew_text += f"## A1 Radar Audit\n{crew_result.get('audit_report', '')}\n\n"
            crew_text += f"## COS Review ({crew_result.get('status', 'N/A')})\n{crew_result.get('cos_review', '')}"
            ai_summary = ai_summary + crew_text
            logger.info("Intel Crew pipeline completed — crew analysis appended.")
        else:
            logger.warning("Intel Crew pipeline returned empty result.")
    except Exception as e:
        logger.warning(f"Intel Crew pipeline failed (non-fatal): {e}")

    # 3. Pull Thunderbird data (sheets, anchors)
    logger.info("Phase 3: Fetching Thunderbird data sources...")
    sheets_data = fetch_sheets_data()
    anchor_data = fetch_anchor_dates()

    # 4. Render HTML
    logger.info("Phase 4: Rendering HTML digest...")
    html = render_digest_html(ai_summary, x_feeds, sheets_data, anchor_data)

    # 5. Save or send
    if preview:
        outpath = OUTPUT_DIR / f"intel_digest_{now.strftime('%Y%m%d_%H%M')}.html"
        outpath.write_text(html, encoding="utf-8")
        logger.info(f"Preview saved: {outpath}")
        print(f"Preview: {outpath}")
    else:
        ok_count = sum(1 for f in x_feeds if f["status"] == "ok")
        subject = f"THUNDERBIRD INTEL DIGEST // {now.strftime('%b %d')} {period} — {ok_count} feeds"
        send_digest_email(html, subject)
        send_sms_ping()
        logger.info("Digest complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Intel Digest")
    parser.add_argument("--preview", action="store_true", help="Save HTML locally, don't send")
    parser.add_argument("--scrape-only", action="store_true", help="Just scrape X, print results")
    args = parser.parse_args()

    asyncio.run(run_digest(preview=args.preview, scrape_only=args.scrape_only))
