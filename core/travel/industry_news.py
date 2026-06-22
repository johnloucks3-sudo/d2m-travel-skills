#!/usr/bin/env python3
"""
industry_news.py — Travel industry news aggregator via RSS.

No API keys required. 5 feeds cover 90% of cruise industry news.

Usage:
    from core.travel.industry_news import daily_brief
    print(daily_brief(keywords=["Silversea", "Regent", "Viking"]))
"""
import hashlib
from datetime import datetime, timezone

import requests

FEEDS = {
    "cruiseindustrynews": "https://www.cruiseindustrynews.com/feed/",
    "seatrade":           "https://www.seatrade-cruise.com/rss.xml",
    "travelweekly":       "https://www.travelweekly.com/RSS/CruiseFeed",
    "travelpulse":        "https://www.travelpulse.com/rss/cruises",
    "cruisehive":         "https://www.cruisehive.com/feed",
}

HEADERS = {"User-Agent": "Thunderbird-D2M/1.0 travel-intel"}


def _fetch_feed(name: str, url: str, max_items: int = 10) -> list[dict]:
    items = []
    try:
        try:
            import feedparser
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:max_items]:
                items.append({
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", "")[:300],
                    "source": name,
                })
        except ImportError:
            import xml.etree.ElementTree as ET
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for item in (root.findall(".//item") or
                         root.findall(".//atom:entry", ns))[:max_items]:
                title = (item.findtext("title") or
                         item.findtext("atom:title", namespaces=ns) or "")
                link = (item.findtext("link") or
                        item.findtext("atom:link", namespaces=ns) or "")
                items.append({"title": title.strip(), "link": link.strip(),
                               "published": "", "summary": "", "source": name})
    except Exception as e:
        items.append({"title": f"[FEED ERROR: {name}]", "link": url,
                      "published": "", "summary": str(e), "source": name})
    return items


def fetch_all_feeds(max_per_feed: int = 10) -> list[dict]:
    all_items = []
    for name, url in FEEDS.items():
        all_items.extend(_fetch_feed(name, url, max_per_feed))
    return all_items


def dedup_by_title(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        key = hashlib.md5(item.get("title", "").lower().strip().encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def filter_by_keywords(items: list[dict], keywords: list[str]) -> list[dict]:
    kw_lower = [k.lower() for k in keywords]
    return [i for i in items
            if any(k in (i.get("title", "") + i.get("summary", "")).lower()
                   for k in kw_lower)]


def daily_brief(keywords: list[str] = None, max_per_feed: int = 8) -> str:
    items = dedup_by_title(fetch_all_feeds(max_per_feed))
    if keywords:
        filtered = filter_by_keywords(items, keywords)
        if not filtered:
            filtered = items[:10]
    else:
        filtered = items[:15]
    lines = [f"=== TRAVEL INDUSTRY BRIEF — {datetime.now(timezone.utc).strftime('%Y-%m-%d')} ==="]
    for item in filtered[:20]:
        lines.append(f"[{item.get('source','?')}] {item.get('title','')} — {item.get('link','')}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    kw = sys.argv[1:] if len(sys.argv) > 1 else ["Silversea", "Regent", "Viking", "luxury"]
    print(daily_brief(keywords=kw))
