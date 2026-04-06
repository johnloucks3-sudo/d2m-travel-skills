"""
Dreams2Memories Cruise Review & Content Scraper
================================================

Wide-net scraper for cruise review, news, and community sites.
Builds a local SQLite content database for future social media,
web publishing, and Facebook content.

Working Sources:
  - CruiseIndustryNews (cruiseindustrynews.com) — industry news articles
  - CruisePassenger (cruisepassenger.com.au) — reviews + cruise news
  - CruiseHive RSS (cruisehive.com/feed) — cruise news articles
  - CruiseFever RSS (cruisefever.net/feed) — deals, news, reviews
  - Reddit (r/Cruises, r/cruise) — real traveler posts + discussions
  - Google News RSS — aggregated cruise news from all sources

Targeted cruise lines:
  Regent, Silversea, Oceania, Viking, AmaWaterways, Cunard, Seabourn, Ponant

Usage:
  python thunderbird_cruise_reviews.py --preview          # scrape + print sample
  python thunderbird_cruise_reviews.py --site reddit      # one site only
  python thunderbird_cruise_reviews.py --line regent      # one cruise line
  python thunderbird_cruise_reviews.py --full             # scrape everything
  python thunderbird_cruise_reviews.py --stats            # DB stats
  python thunderbird_cruise_reviews.py --export           # export JSON

Dependencies: playwright, playwright-stealth, requests, sqlite3 (stdlib)
"""

import asyncio
import json
import logging
import random
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from html import unescape

import requests
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

logger = logging.getLogger("cruise_reviews")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [REVIEWS] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

BASE_DIR = Path.home() / "Thunderbird"
DB_PATH = BASE_DIR / "cruise_content.db"

# Polite scraping — randomized delays
MIN_DELAY = 5
MAX_DELAY = 12

# Targeted cruise lines
CRUISE_LINES = {
    "regent": {
        "name": "Regent Seven Seas Cruises",
        "search_terms": ["regent seven seas", "RSSC", "seven seas grandeur",
                         "seven seas explorer", "seven seas splendor"],
        "reddit_terms": ["regent seven seas", "RSSC", "seven seas grandeur"],
        "google_query": "regent+seven+seas+cruise",
        "ships": ["Seven Seas Grandeur", "Seven Seas Explorer", "Seven Seas Splendor",
                  "Seven Seas Mariner", "Seven Seas Navigator"],
    },
    "silversea": {
        "name": "Silversea Cruises",
        "search_terms": ["silversea", "silver nova", "silver dawn", "silver muse"],
        "reddit_terms": ["silversea", "silver nova", "silver muse"],
        "google_query": "silversea+cruise",
        "ships": ["Silver Nova", "Silver Dawn", "Silver Muse", "Silver Moon",
                  "Silver Spirit", "Silver Ray"],
    },
    "oceania": {
        "name": "Oceania Cruises",
        "search_terms": ["oceania cruises", "oceania vista", "oceania riviera"],
        "reddit_terms": ["oceania cruises", "oceania vista"],
        "google_query": "oceania+cruises",
        "ships": ["Vista", "Riviera", "Marina", "Nautica", "Regatta", "Insignia"],
    },
    "viking": {
        "name": "Viking Ocean Cruises",
        "search_terms": ["viking cruise", "viking ocean", "viking expedition"],
        "reddit_terms": ["viking cruise", "viking ocean"],
        "google_query": "viking+ocean+cruise",
        "ships": ["Viking Star", "Viking Sea", "Viking Sky", "Viking Sun",
                  "Viking Orion", "Viking Jupiter", "Viking Neptune", "Viking Saturn"],
    },
    "amawaterways": {
        "name": "AmaWaterways",
        "search_terms": ["amawaterways", "amamagna", "ama waterways"],
        "reddit_terms": ["amawaterways", "amamagna"],
        "google_query": "amawaterways+river+cruise",
        "ships": ["AmaMagna", "AmaViola", "AmaLea", "AmaPrima", "AmaKristina"],
    },
    "cunard": {
        "name": "Cunard Line",
        "search_terms": ["cunard", "queen mary 2", "queen victoria", "queen anne"],
        "reddit_terms": ["cunard", "queen mary 2"],
        "google_query": "cunard+cruise",
        "ships": ["Queen Mary 2", "Queen Victoria", "Queen Elizabeth", "Queen Anne"],
    },
    "seabourn": {
        "name": "Seabourn Cruise Line",
        "search_terms": ["seabourn", "seabourn pursuit", "seabourn venture"],
        "reddit_terms": ["seabourn"],
        "google_query": "seabourn+cruise",
        "ships": ["Seabourn Pursuit", "Seabourn Venture", "Seabourn Ovation",
                  "Seabourn Encore", "Seabourn Quest"],
    },
    "ponant": {
        "name": "Ponant",
        "search_terms": ["ponant", "le commandant charcot", "ponant cruise"],
        "reddit_terms": ["ponant"],
        "google_query": "ponant+cruise",
        "ships": ["Le Commandant Charcot", "Le Bellot", "Le Jacques Cartier",
                  "Le Champlain", "Le Bougainville"],
    },
}

REDDIT_SUBS = ["Cruises", "cruise"]
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    """Create the content database if it doesn't exist."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            content_type TEXT NOT NULL,
            cruise_line TEXT,
            ship_name TEXT,
            title TEXT,
            body TEXT NOT NULL,
            author TEXT,
            rating REAL,
            url TEXT NOT NULL,
            published_date TEXT,
            scraped_at TEXT NOT NULL,
            tags TEXT,
            UNIQUE(url, source)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            cruise_line TEXT,
            status TEXT NOT NULL,
            items_found INTEGER DEFAULT 0,
            error_msg TEXT,
            scraped_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_source ON content(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_line ON content(cruise_line)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_date ON content(scraped_at)")
    conn.commit()
    return conn


def store_content(conn: sqlite3.Connection, items: List[Dict[str, Any]]):
    """Store scraped content, skipping duplicates."""
    stored = 0
    for item in items:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO content
                (source, content_type, cruise_line, ship_name, title, body, author,
                 rating, url, published_date, scraped_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("source", ""),
                item.get("content_type", "review"),
                item.get("cruise_line", ""),
                item.get("ship_name", ""),
                item.get("title", ""),
                item.get("body", ""),
                item.get("author", ""),
                item.get("rating"),
                item.get("url", ""),
                item.get("published_date", ""),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(item.get("tags", [])),
            ))
            stored += 1
        except Exception as e:
            logger.warning(f"  Store error: {e}")
    conn.commit()
    return stored


def log_scrape(conn: sqlite3.Connection, source: str, cruise_line: str,
               status: str, items_found: int = 0, error_msg: str = ""):
    """Log a scrape attempt."""
    conn.execute("""
        INSERT INTO scrape_log (source, cruise_line, status, items_found, error_msg, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (source, cruise_line, status, items_found, error_msg,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()


# ---------------------------------------------------------------------------
# Helper: tag cruise line from text
# ---------------------------------------------------------------------------

def _tag_cruise_line(text: str) -> str:
    """Detect which cruise line a text snippet refers to."""
    text_lower = text.lower()
    for key, config in CRUISE_LINES.items():
        for term in config.get("search_terms", []):
            if term.lower() in text_lower:
                return key
    return "general"


def _tag_ship(text: str, cruise_line_key: str) -> str:
    """Detect which ship a text snippet refers to."""
    text_lower = text.lower()
    config = CRUISE_LINES.get(cruise_line_key, {})
    for ship in config.get("ships", []):
        if ship.lower() in text_lower:
            return ship
    return ""


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    return text.strip()


def _polite_delay_sync():
    """Synchronous polite delay."""
    import time
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    logger.info(f"  Polite delay: {delay:.1f}s")
    time.sleep(delay)


async def _polite_delay():
    """Async polite delay."""
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    logger.info(f"  Polite delay: {delay:.1f}s")
    await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# 1. CruiseIndustryNews (Playwright)
# ---------------------------------------------------------------------------

async def scrape_cruise_industry_news(page, cruise_line_key: str = None) -> List[Dict]:
    """Scrape CruiseIndustryNews — homepage + search by cruise line."""
    items = []

    if cruise_line_key:
        line_config = CRUISE_LINES.get(cruise_line_key, {})
        search_term = line_config.get("name", cruise_line_key).replace(" ", "+")
        url = f"https://www.cruiseindustrynews.com/?s={search_term}"
        logger.info(f"  CruiseIndustryNews search: {line_config.get('name', cruise_line_key)}")
    else:
        url = "https://www.cruiseindustrynews.com/"
        logger.info("  CruiseIndustryNews: homepage")

    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if not resp or resp.status >= 400:
            return items
        await asyncio.sleep(3)

        articles = await page.query_selector_all("article")
        logger.info(f"    Found {len(articles)} articles")

        for article in articles[:20]:
            try:
                # Try title selectors in order — h3 a is CIN's actual structure
                title_el = None
                for sel in ["h2 a", "h3 a", ".entry-title a", "h1 a"]:
                    title_el = await article.query_selector(sel)
                    if title_el:
                        break
                if not title_el:
                    continue

                title = (await title_el.inner_text()).strip()
                href = await title_el.get_attribute("href") or ""

                # Get excerpt
                excerpt_el = await article.query_selector("p, .entry-summary, .excerpt")
                excerpt = ""
                if excerpt_el:
                    excerpt = (await excerpt_el.inner_text()).strip()

                if not title or len(title) < 10:
                    continue

                # Auto-tag cruise line
                cl = cruise_line_key or _tag_cruise_line(title + " " + excerpt)

                items.append({
                    "source": "cruiseindustrynews",
                    "content_type": "news",
                    "cruise_line": cl,
                    "ship_name": _tag_ship(title + " " + excerpt, cl),
                    "title": title,
                    "body": excerpt[:2000] if excerpt else title,
                    "author": "Cruise Industry News",
                    "url": href if href.startswith("http") else f"https://cruiseindustrynews.com{href}",
                    "tags": ["cruise_news", "industry"],
                })
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"  CruiseIndustryNews error: {e}")

    return items


# ---------------------------------------------------------------------------
# 2. CruisePassenger (Playwright)
# ---------------------------------------------------------------------------

async def scrape_cruise_passenger(page, cruise_line_key: str = None) -> List[Dict]:
    """Scrape CruisePassenger.com.au — reviews and news."""
    items = []

    if cruise_line_key:
        line_config = CRUISE_LINES.get(cruise_line_key, {})
        search_term = line_config.get("name", cruise_line_key).replace(" ", "+")
        url = f"https://www.cruisepassenger.com.au/?s={search_term}"
        logger.info(f"  CruisePassenger search: {line_config.get('name', cruise_line_key)}")
    else:
        url = "https://www.cruisepassenger.com.au/"
        logger.info("  CruisePassenger: homepage")

    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if not resp or resp.status >= 400:
            return items
        await asyncio.sleep(3)

        headlines = await page.query_selector_all("h2 a, h3 a")
        logger.info(f"    Found {len(headlines)} headlines")

        for h in headlines[:20]:
            try:
                title = (await h.inner_text()).strip()
                href = await h.get_attribute("href") or ""

                if not title or len(title) < 10:
                    continue
                if not href:
                    continue

                # Determine content type from URL
                ctype = "review" if "/review" in href.lower() else "news"
                cl = cruise_line_key or _tag_cruise_line(title)

                items.append({
                    "source": "cruisepassenger",
                    "content_type": ctype,
                    "cruise_line": cl,
                    "ship_name": _tag_ship(title, cl),
                    "title": title,
                    "body": title,  # Will get full article body on follow-up scrapes
                    "author": "Cruise Passenger",
                    "url": href if href.startswith("http") else f"https://www.cruisepassenger.com.au{href}",
                    "tags": ["cruise_news", ctype],
                })
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"  CruisePassenger error: {e}")

    return items


# ---------------------------------------------------------------------------
# 3. CruiseHive RSS (requests)
# ---------------------------------------------------------------------------

def scrape_cruisehive_rss() -> List[Dict]:
    """Scrape CruiseHive via RSS feed."""
    items = []
    logger.info("  CruiseHive RSS")

    try:
        r = requests.get("https://www.cruisehive.com/feed",
                         headers=HTTP_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"  CruiseHive RSS: HTTP {r.status_code}")
            return items

        rss_items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        logger.info(f"    Found {len(rss_items)} RSS items")

        for item_xml in rss_items:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item_xml)
            if not title_m:
                title_m = re.search(r'<title>(.*?)</title>', item_xml)
            link_m = re.search(r'<link>(https?://[^<]+)</link>', item_xml)
            desc_m = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item_xml, re.DOTALL)
            if not desc_m:
                desc_m = re.search(r'<description>(.*?)</description>', item_xml, re.DOTALL)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
            author_m = re.search(r'<dc:creator><!\[CDATA\[(.*?)\]\]></dc:creator>', item_xml)
            cats = re.findall(r'<category><!\[CDATA\[(.*?)\]\]></category>', item_xml)

            title = _clean_html(title_m.group(1)) if title_m else ""
            link = link_m.group(1) if link_m else ""
            desc = _clean_html(desc_m.group(1))[:2000] if desc_m else ""
            pub_date = date_m.group(1) if date_m else ""
            author = author_m.group(1) if author_m else "CruiseHive"

            if not title:
                continue

            cl = _tag_cruise_line(title + " " + desc)

            items.append({
                "source": "cruisehive",
                "content_type": "news",
                "cruise_line": cl,
                "ship_name": _tag_ship(title + " " + desc, cl),
                "title": title,
                "body": desc or title,
                "author": author,
                "url": link,
                "published_date": pub_date,
                "tags": ["cruise_news"] + [c.lower().replace(" ", "_") for c in cats[:5]],
            })

    except Exception as e:
        logger.warning(f"  CruiseHive RSS error: {e}")

    return items


# ---------------------------------------------------------------------------
# 4. CruiseFever RSS (requests)
# ---------------------------------------------------------------------------

def scrape_cruisefever_rss() -> List[Dict]:
    """Scrape Cruise Fever via RSS feed."""
    items = []
    logger.info("  CruiseFever RSS")

    try:
        r = requests.get("https://cruisefever.net/feed/",
                         headers=HTTP_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"  CruiseFever RSS: HTTP {r.status_code}")
            return items

        rss_items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        logger.info(f"    Found {len(rss_items)} RSS items")

        for item_xml in rss_items:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item_xml)
            if not title_m:
                title_m = re.search(r'<title>(.*?)</title>', item_xml)
            link_m = re.search(r'<link>(https?://[^<]+)</link>', item_xml)
            desc_m = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item_xml, re.DOTALL)
            if not desc_m:
                desc_m = re.search(r'<description>(.*?)</description>', item_xml, re.DOTALL)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
            cats = re.findall(r'<category><!\[CDATA\[(.*?)\]\]></category>', item_xml)

            title = _clean_html(title_m.group(1)) if title_m else ""
            link = link_m.group(1) if link_m else ""
            desc = _clean_html(desc_m.group(1))[:2000] if desc_m else ""
            pub_date = date_m.group(1) if date_m else ""

            if not title:
                continue

            cl = _tag_cruise_line(title + " " + desc)

            items.append({
                "source": "cruisefever",
                "content_type": "news",
                "cruise_line": cl,
                "ship_name": _tag_ship(title + " " + desc, cl),
                "title": title,
                "body": desc or title,
                "author": "Cruise Fever",
                "url": link,
                "published_date": pub_date,
                "tags": ["cruise_news", "deals"] + [c.lower().replace(" ", "_") for c in cats[:5]],
            })

    except Exception as e:
        logger.warning(f"  CruiseFever RSS error: {e}")

    return items


# ---------------------------------------------------------------------------
# 5. Reddit (JSON API)
# ---------------------------------------------------------------------------

def scrape_reddit(cruise_line_key: str = None) -> List[Dict]:
    """Scrape Reddit cruise subreddits for relevant posts."""
    items = []

    # Build search terms
    if cruise_line_key:
        line_config = CRUISE_LINES.get(cruise_line_key, {})
        search_terms = line_config.get("reddit_terms", [line_config.get("name", "")])
        logger.info(f"  Reddit search: {line_config.get('name', cruise_line_key)}")
    else:
        search_terms = None
        logger.info("  Reddit: general cruise subs")

    for sub in REDDIT_SUBS:
        try:
            if search_terms:
                # Search within subreddit
                for term in search_terms[:2]:
                    url = f"https://www.reddit.com/r/{sub}/search.json?q={term.replace(' ', '+')}&restrict_sr=1&sort=new&limit=10"
                    r = requests.get(url, headers={"User-Agent": "D2M-Cruise-Bot/1.0"}, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        posts = data.get("data", {}).get("children", [])
                        for post in posts:
                            d = post.get("data", {})
                            title = d.get("title", "")
                            selftext = d.get("selftext", "")
                            if not title:
                                continue

                            cl = cruise_line_key or _tag_cruise_line(title + " " + selftext)

                            items.append({
                                "source": "reddit",
                                "content_type": "discussion",
                                "cruise_line": cl,
                                "ship_name": _tag_ship(title + " " + selftext, cl),
                                "title": title,
                                "body": (selftext[:2000] if selftext else title),
                                "author": d.get("author", ""),
                                "rating": None,
                                "url": f"https://www.reddit.com{d.get('permalink', '')}",
                                "published_date": datetime.fromtimestamp(
                                    d.get("created_utc", 0), tz=timezone.utc
                                ).isoformat() if d.get("created_utc") else "",
                                "tags": ["reddit", f"r/{sub}", "traveler_post",
                                         f"score:{d.get('score', 0)}",
                                         f"comments:{d.get('num_comments', 0)}"],
                            })

                    _polite_delay_sync()

            else:
                # Just get recent posts
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
                r = requests.get(url, headers={"User-Agent": "D2M-Cruise-Bot/1.0"}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    posts = data.get("data", {}).get("children", [])
                    logger.info(f"    r/{sub}: {len(posts)} posts")
                    for post in posts:
                        d = post.get("data", {})
                        title = d.get("title", "")
                        selftext = d.get("selftext", "")
                        if not title or d.get("stickied"):
                            continue

                        cl = _tag_cruise_line(title + " " + selftext)

                        items.append({
                            "source": "reddit",
                            "content_type": "discussion",
                            "cruise_line": cl,
                            "ship_name": _tag_ship(title + " " + selftext, cl),
                            "title": title,
                            "body": (selftext[:2000] if selftext else title),
                            "author": d.get("author", ""),
                            "url": f"https://www.reddit.com{d.get('permalink', '')}",
                            "published_date": datetime.fromtimestamp(
                                d.get("created_utc", 0), tz=timezone.utc
                            ).isoformat() if d.get("created_utc") else "",
                            "tags": ["reddit", f"r/{sub}", "traveler_post",
                                     f"score:{d.get('score', 0)}",
                                     f"comments:{d.get('num_comments', 0)}"],
                        })

                _polite_delay_sync()

        except Exception as e:
            logger.warning(f"  Reddit r/{sub} error: {e}")

    return items


# ---------------------------------------------------------------------------
# 6. Google News RSS (requests)
# ---------------------------------------------------------------------------

def scrape_google_news(cruise_line_key: str = None) -> List[Dict]:
    """Scrape Google News RSS for cruise content."""
    items = []

    if cruise_line_key:
        line_config = CRUISE_LINES.get(cruise_line_key, {})
        queries = [line_config.get("google_query", "")]
        logger.info(f"  Google News: {line_config.get('name', cruise_line_key)}")
    else:
        queries = ["luxury+cruise+news", "cruise+industry+news"]
        logger.info("  Google News: general cruise news")

    for query in queries:
        if not query:
            continue
        try:
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            r = requests.get(url, headers=HTTP_HEADERS, timeout=15)

            if r.status_code != 200:
                continue

            rss_items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
            logger.info(f"    Found {len(rss_items)} Google News items for '{query}'")

            for item_xml in rss_items[:25]:  # Cap at 25 per query
                title_m = re.search(r'<title>(.*?)</title>', item_xml)
                link_m = re.search(r'<link/>\s*(.*?)\s*<guid', item_xml, re.DOTALL)
                if not link_m:
                    link_m = re.search(r'<link>(.*?)</link>', item_xml)
                date_m = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
                source_m = re.search(r'<source[^>]*>(.*?)</source>', item_xml)

                title = _clean_html(title_m.group(1)) if title_m else ""
                link = link_m.group(1).strip() if link_m else ""
                pub_date = date_m.group(1) if date_m else ""
                news_source = _clean_html(source_m.group(1)) if source_m else "Google News"

                if not title:
                    continue

                cl = cruise_line_key or _tag_cruise_line(title)

                items.append({
                    "source": "google_news",
                    "content_type": "news",
                    "cruise_line": cl,
                    "ship_name": _tag_ship(title, cl),
                    "title": title,
                    "body": title,  # Google News only gives titles in RSS
                    "author": news_source,
                    "url": link,
                    "published_date": pub_date,
                    "tags": ["google_news", "aggregated", news_source.lower().replace(" ", "_")],
                })

        except Exception as e:
            logger.warning(f"  Google News error: {e}")

    return items


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

SITE_SCRAPERS_SYNC = {
    "cruisehive": ("CruiseHive RSS", scrape_cruisehive_rss, False),
    "cruisefever": ("CruiseFever RSS", scrape_cruisefever_rss, False),
    "reddit": ("Reddit", scrape_reddit, True),  # True = accepts cruise_line_key
    "google_news": ("Google News", scrape_google_news, True),
}

SITE_SCRAPERS_ASYNC = {
    "cruiseindustrynews": ("Cruise Industry News", scrape_cruise_industry_news, True),
    "cruisepassenger": ("Cruise Passenger", scrape_cruise_passenger, True),
}


async def run_scrape(
    sites: Optional[List[str]] = None,
    lines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run the full scrape pipeline."""
    conn = init_db()

    all_sites = list(SITE_SCRAPERS_SYNC.keys()) + list(SITE_SCRAPERS_ASYNC.keys())
    target_sites = sites or all_sites
    target_lines = lines or list(CRUISE_LINES.keys())

    total_items = 0
    total_stored = 0
    errors = []

    logger.info("=" * 60)
    logger.info("CRUISE CONTENT SCRAPER — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("Sites: %s", ", ".join(target_sites))
    logger.info("Lines: %s", ", ".join(target_lines))
    logger.info("=" * 60)

    # --- Sync scrapers (RSS + API) ---
    for site_key in target_sites:
        if site_key not in SITE_SCRAPERS_SYNC:
            continue

        name, scraper_fn, accepts_line = SITE_SCRAPERS_SYNC[site_key]
        logger.info(f"\n--- {name} ---")

        try:
            if accepts_line:
                for line_key in target_lines:
                    all_items = scraper_fn(line_key)
                    total_items += len(all_items)
                    if all_items:
                        stored = store_content(conn, all_items)
                        total_stored += stored
                        logger.info(f"  → {len(all_items)} found, {stored} new stored")
                    log_scrape(conn, site_key, line_key, "success", len(all_items))
            else:
                all_items = scraper_fn()
                total_items += len(all_items)
                if all_items:
                    stored = store_content(conn, all_items)
                    total_stored += stored
                    logger.info(f"  → {len(all_items)} found, {stored} new stored")
                log_scrape(conn, site_key, "all", "success", len(all_items))

        except Exception as e:
            err_msg = str(e)[:200]
            logger.error(f"  ERROR: {err_msg}")
            errors.append(f"{site_key}: {err_msg}")
            log_scrape(conn, site_key, "all", "error", 0, err_msg)

    # --- Async scrapers (Playwright) ---
    async_sites = [s for s in target_sites if s in SITE_SCRAPERS_ASYNC]
    if async_sites:
        try:
            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                for site_key in async_sites:
                    name, scraper_fn, accepts_line = SITE_SCRAPERS_ASYNC[site_key]
                    logger.info(f"\n--- {name} ---")

                    try:
                        if accepts_line:
                            for line_key in target_lines:
                                all_items = await scraper_fn(page, line_key)
                                total_items += len(all_items)
                                if all_items:
                                    stored = store_content(conn, all_items)
                                    total_stored += stored
                                    logger.info(f"  → {len(all_items)} found, {stored} new stored")
                                log_scrape(conn, site_key, line_key, "success", len(all_items))
                                await _polite_delay()
                        else:
                            all_items = await scraper_fn(page)
                            total_items += len(all_items)
                            if all_items:
                                stored = store_content(conn, all_items)
                                total_stored += stored
                                logger.info(f"  → {len(all_items)} found, {stored} new stored")
                            log_scrape(conn, site_key, "all", "success", len(all_items))

                    except Exception as e:
                        err_msg = str(e)[:200]
                        logger.error(f"  ERROR: {err_msg}")
                        errors.append(f"{site_key}: {err_msg}")
                        log_scrape(conn, site_key, "all", "error", 0, err_msg)

                await context.close()
                await browser.close()

        except Exception as e:
            logger.error(f"Browser launch error: {e}")
            errors.append(f"browser: {str(e)[:200]}")

    conn.close()

    summary = {
        "total_found": total_items,
        "total_stored": total_stored,
        "sites_scraped": len(target_sites),
        "lines_scraped": len(target_lines),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("\n" + "=" * 60)
    logger.info(f"DONE — {total_items} items found, {total_stored} new stored, {len(errors)} errors")
    logger.info("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# Stats & Export
# ---------------------------------------------------------------------------

def print_stats():
    """Print database statistics."""
    if not DB_PATH.exists():
        print("No database yet. Run a scrape first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
    print(f"\n{'='*50}")
    print(f"CRUISE CONTENT DATABASE — {total} items")
    print(f"{'='*50}")

    print("\nBy Source:")
    for row in conn.execute("SELECT source, COUNT(*) FROM content GROUP BY source ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]:25s} {row[1]:5d}")

    print("\nBy Cruise Line:")
    for row in conn.execute("SELECT cruise_line, COUNT(*) FROM content GROUP BY cruise_line ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]:25s} {row[1]:5d}")

    print("\nBy Content Type:")
    for row in conn.execute("SELECT content_type, COUNT(*) FROM content GROUP BY content_type ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]:25s} {row[1]:5d}")

    print("\nMost Recent 15:")
    for row in conn.execute(
        "SELECT source, cruise_line, title, scraped_at FROM content ORDER BY scraped_at DESC LIMIT 15"
    ):
        print(f"  [{row[0]:15s}] {row[1]:12s} — {row[2][:55]}  ({row[3][:10]})")

    conn.close()


def export_json(output_path: str = None):
    """Export database to JSON for content publishing."""
    if not DB_PATH.exists():
        print("No database yet.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM content ORDER BY scraped_at DESC").fetchall()
    data = [dict(row) for row in rows]

    if not output_path:
        output_path = str(BASE_DIR / "output" / f"cruise_content_export_{datetime.now().strftime('%Y%m%d')}.json")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(data)} items to {output_path}")
    conn.close()


def preview_content(limit: int = 25):
    """Print a preview of recently scraped content."""
    if not DB_PATH.exists():
        print("No database yet. Run a scrape first.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT source, content_type, cruise_line, ship_name, title, body, rating, url "
        "FROM content ORDER BY scraped_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

    if not rows:
        print("Database is empty.")
        return

    print(f"\n{'='*70}")
    print(f"CRUISE CONTENT PREVIEW — {len(rows)} items")
    print(f"{'='*70}")

    for i, row in enumerate(rows, 1):
        source, ctype, line, ship, title, body, rating, url = row
        rating_str = f" ★{rating}" if rating else ""
        ship_str = f" [{ship}]" if ship else ""
        print(f"\n--- {i}. [{source}] {ctype}{rating_str} ---")
        print(f"  Line: {line}{ship_str}")
        print(f"  Title: {title[:80]}")
        print(f"  URL: {url[:80]}")
        if body and body != title:
            body_preview = body[:200].replace('\n', ' ')
            print(f"  {body_preview}...")

    conn.close()


# ---------------------------------------------------------------------------
# MCP Registration
# ---------------------------------------------------------------------------

def register_cruise_review_tools(mcp):
    """Register cruise review scraper tools with the MCP server."""

    @mcp.tool(
        name="scrape_cruise_reviews",
        annotations={"title": "Scrape Cruise Review Sites", "readOnlyHint": False},
    )
    async def scrape_cruise_reviews(
        sites: Optional[str] = None,
        cruise_lines: Optional[str] = None,
    ) -> str:
        """Scrape cruise review and news sites to build the content database.

        Args:
            sites: Comma-separated site keys (cruisehive,cruisefever,reddit,google_news,cruiseindustrynews,cruisepassenger). Default: all.
            cruise_lines: Comma-separated cruise line keys (regent,silversea,oceania,viking,amawaterways,cunard,seabourn,ponant). Default: all.
        """
        site_list = [s.strip() for s in sites.split(",")] if sites else None
        line_list = [l.strip() for l in cruise_lines.split(",")] if cruise_lines else None
        result = await run_scrape(sites=site_list, lines=line_list)
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="cruise_content_stats",
        annotations={"title": "Cruise Content Database Stats", "readOnlyHint": True},
    )
    async def cruise_content_stats() -> str:
        """Get statistics on the cruise content database."""
        if not DB_PATH.exists():
            return "No database yet. Run scrape_cruise_reviews first."

        conn = sqlite3.connect(str(DB_PATH))
        total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        by_source = conn.execute("SELECT source, COUNT(*) FROM content GROUP BY source").fetchall()
        by_line = conn.execute("SELECT cruise_line, COUNT(*) FROM content GROUP BY cruise_line").fetchall()
        conn.close()

        return json.dumps({
            "total": total,
            "by_source": dict(by_source),
            "by_cruise_line": dict(by_line),
        }, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="D2M Cruise Content Scraper")
    parser.add_argument("--full", action="store_true", help="Full scrape — all sites, all lines")
    parser.add_argument("--site", type=str, help="Scrape one site (cruisehive, cruisefever, reddit, google_news, cruiseindustrynews, cruisepassenger)")
    parser.add_argument("--line", type=str, help="Scrape one cruise line (regent, silversea, etc.)")
    parser.add_argument("--preview", action="store_true", help="Scrape + preview results")
    parser.add_argument("--stats", action="store_true", help="Print database stats")
    parser.add_argument("--export", action="store_true", help="Export database to JSON")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    if args.export:
        export_json()
        return

    sites = [args.site] if args.site else None
    lines = [args.line] if args.line else None

    if not args.full and not args.site and not args.line and not args.preview:
        parser.print_help()
        return

    result = asyncio.run(run_scrape(sites=sites, lines=lines))
    print(json.dumps(result, indent=2))

    if args.preview:
        preview_content()


if __name__ == "__main__":
    main()
