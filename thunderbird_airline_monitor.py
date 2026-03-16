#!/usr/bin/env python3
"""
Thunderbird Airline Monitor — Route Change Detection + Client Alerting
======================================================================

Dedicated airline route change monitor for Dreams2Memories Travel.
Scrapes airline news sources for route announcements, cross-references
against client dossier airports, and sends immediate Telegram alerts.

The SWA/Dulles failure prevention system.

Usage:
  python3 thunderbird_airline_monitor.py              # Run full scan
  python3 thunderbird_airline_monitor.py --check-only  # Check without alerting
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import feedparser

logger = logging.getLogger("thunderbird_airline_monitor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AIRLINE] %(message)s",
    stream=sys.stderr,
)

THUNDERBIRD_DIR = Path(__file__).parent

# ============================================================================
# AIRLINE NEWS SOURCES
# ============================================================================

AIRLINE_FEEDS = {
    "Simple Flying": "https://simpleflying.com/feed/",
    "Routes Online": "https://www.routesonline.com/rss/news/",
    "The Points Guy Airlines": "https://thepointsguy.com/airlines/feed/",
    "Cranky Flier": "https://crankyflier.com/feed/",
}

# Keywords that indicate route changes
ROUTE_CHANGE_KEYWORDS = [
    "route cancel", "route cut", "drops route", "ends service",
    "new route", "adds service", "launches route", "suspends",
    "discontinue", "pulls out", "exits market", "reduces service",
    "frequency cut", "seasonal end", "permanent cut",
]

# Airlines D2M clients fly
TRACKED_AIRLINES = [
    "southwest", "swa", "united", "delta", "american",
    "alaska", "jetblue", "frontier", "spirit",
]


# ============================================================================
# CLIENT AIRPORT EXTRACTION
# ============================================================================

def get_client_airports() -> Dict[str, List[str]]:
    """Extract airports from active client dossiers.

    Returns dict: {client_name: [airport_codes]}
    Reads from dossiers and KNOWN_BOOKINGS.
    """
    client_airports = {}

    # Known client airports from dossiers
    try:
        dossier_dir = THUNDERBIRD_DIR / "dossiers"
        if dossier_dir.exists():
            for f in dossier_dir.glob("DOSSIER_*.md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    codes = re.findall(r'\b([A-Z]{3})\b', content)
                    valid_codes = [c for c in codes if _is_likely_airport(c)]
                    if valid_codes:
                        name = f.stem.replace("DOSSIER_", "").replace("_", " ")
                        client_airports[name] = list(set(valid_codes))
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Dossier airport extraction failed: {e}")

    # Hardcoded known airports from active bookings (safety net)
    known = {
        "Justin Loucks": ["DCA", "IAD", "COS", "DEN"],
        "Ryan Loucks": ["OMA", "COS", "DEN"],
        "Westbrook": ["HNL", "COS", "DEN", "SEA"],
    }
    for client, airports in known.items():
        if client in client_airports:
            client_airports[client] = list(set(client_airports[client] + airports))
        else:
            client_airports[client] = airports

    return client_airports


def _is_likely_airport(code: str) -> bool:
    """Check if a 3-letter code is likely an airport code."""
    known_airports = {
        "DCA", "IAD", "DEN", "COS", "SEA", "OMA", "HNL",
        "ORD", "LAX", "JFK", "SFO", "MIA", "ATL", "DFW",
        "BWI", "PHX", "LAS", "MCO", "BOS", "EWR", "IAH",
        "MSP", "DTW", "FLL", "SAN", "TPA", "STL", "AUS",
        "RDU", "CMH", "IND", "MCI", "SAT", "PIT", "CVG",
        "BCN", "FCO", "ATH", "VCE", "LIS", "CDG", "LHR",
        "AMS", "CPH", "OSL", "KEF", "SIN", "SYD",
    }
    return code in known_airports


# ============================================================================
# FEED SCRAPING
# ============================================================================

def scrape_airline_feeds() -> List[Dict[str, Any]]:
    """Scrape airline RSS feeds for route-related news."""
    articles = []

    for source_name, feed_url in AIRLINE_FEEDS.items():
        try:
            logger.info(f"Fetching {source_name}...")
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                url = entry.get("link", "")
                published = entry.get("published", "")

                # Clean HTML
                from bs4 import BeautifulSoup
                summary_text = BeautifulSoup(summary, "html.parser").get_text()

                articles.append({
                    "title": title,
                    "summary": summary_text[:3000],
                    "url": url,
                    "source": source_name,
                    "published": published,
                })

        except Exception as e:
            logger.error(f"Failed to fetch {source_name}: {e}")

    logger.info(f"Scraped {len(articles)} airline articles")
    return articles


def scrape_airline_route_changes() -> List[Dict[str, Any]]:
    """Filter airline articles to only route-change-related items."""
    all_articles = scrape_airline_feeds()
    route_articles = []

    for article in all_articles:
        text = (article["title"] + " " + article["summary"]).lower()

        matched_keywords = [kw for kw in ROUTE_CHANGE_KEYWORDS if kw in text]
        matched_airlines = [al for al in TRACKED_AIRLINES if al in text]

        if matched_keywords or matched_airlines:
            article["matched_keywords"] = matched_keywords
            article["matched_airlines"] = matched_airlines
            article["relevance"] = len(matched_keywords) + len(matched_airlines)
            route_articles.append(article)

    route_articles.sort(key=lambda x: x["relevance"], reverse=True)
    logger.info(f"Found {len(route_articles)} route-change articles")
    return route_articles


# ============================================================================
# CLIENT IMPACT ASSESSMENT
# ============================================================================

def check_client_airport_impact(articles: List[Dict] = None) -> List[Dict[str, Any]]:
    """Cross-reference route change articles against client airports.

    Returns list of impact alerts with severity:
    - CRITICAL: airline + airport match (the SWA/Dulles test)
    - HIGH: airport match only
    - MEDIUM: airline match for a client's region
    """
    if articles is None:
        articles = scrape_airline_route_changes()

    client_airports = get_client_airports()
    impacts = []

    for article in articles:
        text = (article["title"] + " " + article["summary"]).lower()

        for client, airports in client_airports.items():
            for airport in airports:
                if airport.lower() in text:
                    airline_match = any(al in text for al in TRACKED_AIRLINES)
                    severity = "CRITICAL" if airline_match else "HIGH"

                    impacts.append({
                        "severity": severity,
                        "client": client,
                        "airport": airport,
                        "airline_match": article.get("matched_airlines", []),
                        "title": article["title"],
                        "summary": article["summary"][:500],
                        "url": article["url"],
                        "source": article["source"],
                        "published": article["published"],
                    })

    impacts.sort(key=lambda x: 0 if x["severity"] == "CRITICAL" else 1)

    if impacts:
        logger.warning(f"CLIENT IMPACTS DETECTED: {len(impacts)} "
                       f"({sum(1 for i in impacts if i['severity'] == 'CRITICAL')} CRITICAL)")

    return impacts


# ============================================================================
# TELEGRAM ALERTING
# ============================================================================

def send_telegram_alert(impacts: List[Dict]) -> bool:
    """Send immediate Telegram alert to Commander for client-impacting route changes."""
    if not impacts:
        return False

    try:
        from thunderbird_telegram import send_commander_message

        msg_parts = ["*AIRLINE ALERT — CLIENT IMPACT DETECTED*\n"]

        for impact in impacts[:5]:
            severity_emoji = "\U0001f534" if impact["severity"] == "CRITICAL" else "\U0001f7e1"
            msg_parts.append(
                f"{severity_emoji} *{impact['severity']}*: {impact['client']}\n"
                f"  Airport: {impact['airport']}\n"
                f"  {impact['title']}\n"
                f"  Source: {impact['source']}\n"
                f"  {impact['url']}\n"
            )

        msg = "\n".join(msg_parts)
        send_commander_message(msg)
        logger.info(f"Telegram alert sent: {len(impacts)} impacts")
        return True

    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        alert_file = THUNDERBIRD_DIR / "output" / "airline_alerts.json"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        alert_file.write_text(json.dumps(impacts, indent=2), encoding="utf-8")
        return False


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_airline_monitor_tools(mcp_server):
    """Register airline monitor tools with MCP server."""
    from pydantic import Field

    @mcp_server.tool(
        name="scan_airline_route_changes",
        annotations={"title": "Scan Airline Route Changes", "readOnlyHint": True},
    )
    async def tool_scan_route_changes() -> str:
        """Scan airline news feeds for route changes and cancellations."""
        articles = scrape_airline_route_changes()
        return json.dumps(articles[:20], indent=2)

    @mcp_server.tool(
        name="check_client_airline_impact",
        annotations={"title": "Check Client Airline Impact", "readOnlyHint": True},
    )
    async def tool_check_impact() -> str:
        """Check if any airline route changes affect D2M clients.
        Cross-references route change news against client airport profiles."""
        impacts = check_client_airport_impact()
        return json.dumps(impacts, indent=2)

    @mcp_server.tool(
        name="get_client_airports",
        annotations={"title": "Get Client Airport Profiles", "readOnlyHint": True},
    )
    async def tool_get_airports() -> str:
        """Get airport profiles for all active D2M clients from dossiers."""
        airports = get_client_airports()
        return json.dumps(airports, indent=2)

    logger.info("Airline monitor tools registered with MCP server")


# ============================================================================
# FULL SCAN
# ============================================================================

async def run_airline_scan(alert: bool = True) -> Dict[str, Any]:
    """Run full airline monitor scan.

    Args:
        alert: If True, send Telegram alerts for client impacts

    Returns:
        Scan results with articles and impacts
    """
    logger.info("=" * 60)
    logger.info("AIRLINE MONITOR — Route Change Scan")
    logger.info("=" * 60)

    articles = scrape_airline_route_changes()
    impacts = check_client_airport_impact(articles)

    if alert and impacts:
        send_telegram_alert(impacts)

    result = {
        "timestamp": datetime.now().isoformat(),
        "articles_scanned": len(articles),
        "route_change_articles": len(articles),
        "client_impacts": len(impacts),
        "critical_impacts": sum(1 for i in impacts if i["severity"] == "CRITICAL"),
        "impacts": impacts,
    }

    output_path = THUNDERBIRD_DIR / "output" / f"airline_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Thunderbird Airline Monitor")
    parser.add_argument("--check-only", action="store_true", help="Check without alerting")
    args = parser.parse_args()

    result = asyncio.run(run_airline_scan(alert=not args.check_only))
    print(json.dumps(result, indent=2))
