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


def dembe_intel_report(keywords: list[str] = None, max_per_feed: int = 8) -> str:
    """Format industry news as a Dembe A2 Intel Report."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items = dedup_by_title(fetch_all_feeds(max_per_feed))
    if keywords:
        filtered = filter_by_keywords(items, keywords)
        if not filtered:
            filtered = items[:10]
    else:
        filtered = items[:15]

    lines = [
        "# A2 DEMBE — INTEL REPORT",
        f"## Travel Industry — Daily News Sweep",
        f"**Date:** {today} | **Sources:** {len(FEEDS)} RSS feeds | "
        f"**Items:** {len(filtered)} (deduped from {len(items)} raw)",
        f"**Classification:** Industry intelligence — internal use",
        "",
        "---",
        "",
        "## BLUF",
        "",
        f"Daily sweep of {len(FEEDS)} cruise/travel industry feeds. "
        f"{len(filtered)} relevant items after dedup and keyword filter.",
        "",
        "---",
        "",
    ]
    for i, item in enumerate(filtered[:20], 1):
        src = item.get("source", "?")
        title = item.get("title", "")
        link = item.get("link", "")
        summary = item.get("summary", "")
        lines.append(f"## FINDING {i} — {title}")
        lines.append(f"**Source:** [{src}]({link})")
        if summary:
            lines.append(f"\n{summary}")
        lines.append("")
    return "\n".join(lines)


def send_to_inbox(report: str, subject: str = None) -> bool:
    """Send intel report to johnloucks3 inbox via Python gmail send."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if subject is None:
        subject = f"A2 DEMBE — Travel Industry Intel — {today}"
    try:
        import subprocess, sys
        script = f"""
import sys
sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_send_from_wing
result = gmail_send_from_wing(
    to='johnloucks3@gmail.com',
    subject={repr(subject)},
    body={repr(report)},
    token_path='/home/john/Thunderbird/api/thunderbird_google_auth_johnloucks3_token.json',
)
print('SENT' if result else 'FAILED')
"""
        r = subprocess.run([sys.executable, "-c", script],
                           capture_output=True, text=True, timeout=30)
        return "SENT" in r.stdout
    except Exception as e:
        print(f"[send_to_inbox failed: {e}]")
        return False


if __name__ == "__main__":
    import sys
    kw = sys.argv[1:] if len(sys.argv) > 1 else ["Silversea", "Regent", "Viking", "luxury"]
    report = dembe_intel_report(keywords=kw)
    print(report)
    if "--send" in sys.argv:
        ok = send_to_inbox(report)
        print(f"\n{'✅ Sent to johnloucks3' if ok else '❌ Send failed'}")
