#!/usr/bin/env python3
"""
Thunderbird Claude Code Intelligence Digest
============================================
Scrapes Claude Code news from multiple sources, deduplicates,
and generates a branded HTML digest page.

Sources:
  - Anthropic News (web scrape)
  - GitHub claude-code releases (Atom feed)
  - Hacker News search
  - Reddit r/ClaudeAI search

Usage: python3 thunderbird_claude_code_digest.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_HTML = BASE_DIR / "output" / "claude_code_articles.html"
SEEN_FILE = BASE_DIR / "claude_code_digest_seen.json"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": "Thunderbird-OS/2.0 (Dreams2Memories Travel Claude Code Digest)"
}

# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------

def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
            return set(data)
        except (json.JSONDecodeError, TypeError):
            return set()
    return set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Source scrapers — each returns list of dicts:
#   {"title", "url", "date", "snippet", "source"}
# ---------------------------------------------------------------------------

def fetch_anthropic_news() -> list[dict]:
    """Scrape anthropic.com/news for Claude Code related articles."""
    articles = []
    try:
        resp = requests.get("https://www.anthropic.com/news", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a_tag in soup.select("a[href*='/news/']"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 5:
                continue
            if not href.startswith("http"):
                href = "https://www.anthropic.com" + href
            # Filter for Claude Code relevance
            text_lower = title.lower()
            if any(kw in text_lower for kw in ("claude code", "claude-code", "cli", "coding", "developer", "claude 4", "claude opus", "claude sonnet", "agent")):
                articles.append({
                    "title": title,
                    "url": href,
                    "date": "",
                    "snippet": f"From Anthropic News: {title}",
                    "source": "Anthropic News",
                })
        # Also grab anything that just mentions Claude broadly (limit 10)
        if not articles:
            for a_tag in soup.select("a[href*='/news/']")[:10]:
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                if not title or len(title) < 10:
                    continue
                if not href.startswith("http"):
                    href = "https://www.anthropic.com" + href
                if "claude" in title.lower():
                    articles.append({
                        "title": title,
                        "url": href,
                        "date": "",
                        "snippet": f"From Anthropic News: {title}",
                        "source": "Anthropic News",
                    })
    except Exception as e:
        print(f"[WARN] Anthropic News scrape failed: {e}")
    return articles


def fetch_github_releases() -> list[dict]:
    """Parse GitHub claude-code releases Atom feed."""
    articles = []
    try:
        resp = requests.get(
            "https://github.com/anthropics/claude-code/releases.atom",
            headers=HEADERS, timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:15]:
            snippet = entry.get("summary", entry.get("content", [{}])[0].get("value", "")) if hasattr(entry, "summary") else ""
            # Strip HTML from snippet
            if snippet:
                snippet = BeautifulSoup(snippet, "html.parser").get_text()[:300]
            pub_date = entry.get("updated", entry.get("published", ""))
            articles.append({
                "title": entry.get("title", "Untitled Release"),
                "url": entry.get("link", ""),
                "date": pub_date[:10] if pub_date else "",
                "snippet": snippet or "New Claude Code release.",
                "source": "GitHub Releases",
            })
    except Exception as e:
        print(f"[WARN] GitHub releases fetch failed: {e}")
    return articles


def fetch_hackernews() -> list[dict]:
    """Search Hacker News Algolia API for Claude Code stories."""
    articles = []
    try:
        params = {"query": "Claude Code", "tags": "story", "hitsPerPage": 15}
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            created = hit.get("created_at", "")[:10]
            points = hit.get("points", 0)
            num_comments = hit.get("num_comments", 0)
            articles.append({
                "title": title,
                "url": url,
                "date": created,
                "snippet": f"{points} points, {num_comments} comments on Hacker News",
                "source": "Hacker News",
            })
    except Exception as e:
        print(f"[WARN] Hacker News search failed: {e}")
    return articles


def fetch_reddit() -> list[dict]:
    """Search Reddit r/ClaudeAI for Claude Code posts."""
    articles = []
    try:
        params = {"q": "Claude Code", "restrict_sr": "on", "sort": "new", "limit": 15}
        resp = requests.get(
            "https://www.reddit.com/r/ClaudeAI/search.json",
            params=params,
            headers={**HEADERS, "User-Agent": "Thunderbird-OS/2.0"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            permalink = post.get("permalink", "")
            url = f"https://www.reddit.com{permalink}" if permalink else ""
            created_utc = post.get("created_utc", 0)
            date_str = datetime.fromtimestamp(created_utc, tz=timezone.utc).strftime("%Y-%m-%d") if created_utc else ""
            selftext = (post.get("selftext", "") or "")[:250]
            score = post.get("score", 0)
            articles.append({
                "title": title,
                "url": url,
                "date": date_str,
                "snippet": selftext if selftext else f"Score: {score} on r/ClaudeAI",
                "source": "Reddit r/ClaudeAI",
            })
    except Exception as e:
        print(f"[WARN] Reddit search failed: {e}")
    return articles

# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def render_html(grouped: dict[str, list[dict]], seen: set, now_str: str) -> str:
    """Render the branded HTML digest."""
    source_blocks = []
    for source_name, items in grouped.items():
        if not items:
            continue
        rows = []
        for art in items:
            is_new = art["url"] not in seen
            badge = '<span class="badge new">NEW</span>' if is_new else '<span class="badge seen">SEEN</span>'
            date_html = f'<span class="date">{art["date"]}</span>' if art["date"] else ""
            snippet = art["snippet"][:300] if art["snippet"] else ""
            rows.append(f"""
            <div class="article {"article-new" if is_new else ""}">
              <div class="article-header">
                {badge} {date_html}
                <a href="{art["url"]}" target="_blank" class="article-title">{art["title"]}</a>
              </div>
              <p class="snippet">{snippet}</p>
            </div>""")
        source_blocks.append(f"""
        <div class="source-group">
          <h2 class="source-heading">{source_name} <span class="count">({len(items)})</span></h2>
          {"".join(rows)}
        </div>""")

    total = sum(len(v) for v in grouped.values())
    new_count = sum(1 for items in grouped.values() for a in items if a["url"] not in seen)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Code Intelligence Digest</title>
<style>
  :root {{
    --navy:       #0d1b2e;
    --navy2:      #152540;
    --navy3:      #1e3358;
    --gold:       #c9a84c;
    --gold-light: #e8c97a;
    --gold-pale:  #f5e9c8;
    --muted:      #8a9ab5;
    --white:      #f0f0f0;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--navy);
    color: var(--white);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    padding: 0;
  }}
  .header {{
    background: var(--navy2);
    border-bottom: 3px solid var(--gold);
    padding: 2rem 2rem 1.5rem;
    text-align: center;
  }}
  .header h1 {{
    color: var(--gold-light);
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }}
  .header .meta {{
    color: var(--muted);
    font-size: 0.9rem;
    margin-top: 0.3rem;
  }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 1.5rem 2rem 3rem; }}
  .source-group {{ margin-bottom: 2rem; }}
  .source-heading {{
    color: var(--gold);
    font-size: 1.2rem;
    border-bottom: 1px solid var(--navy3);
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
  }}
  .source-heading .count {{ color: var(--muted); font-weight: 400; font-size: 0.9rem; }}
  .article {{
    background: var(--navy2);
    border-left: 3px solid var(--navy3);
    border-radius: 4px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
  }}
  .article-new {{ border-left-color: var(--gold); }}
  .article-header {{ display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }}
  .article-title {{
    color: var(--white);
    text-decoration: none;
    font-weight: 600;
  }}
  .article-title:hover {{ color: var(--gold-light); text-decoration: underline; }}
  .badge {{
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.15rem 0.45rem;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .badge.new {{ background: var(--gold); color: var(--navy); }}
  .badge.seen {{ background: var(--navy3); color: var(--muted); }}
  .date {{ color: var(--muted); font-size: 0.8rem; }}
  .snippet {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.3rem; }}
  .footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.8rem;
    padding: 2rem 1rem;
    border-top: 1px solid var(--navy3);
    margin-top: 1rem;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>Claude Code Intelligence Digest</h1>
  <div class="meta">{now_str} &mdash; {total} articles ({new_count} new)</div>
</div>
<div class="container">
  {"".join(source_blocks) if source_blocks else '<p style="color:var(--muted);text-align:center;padding:3rem;">No articles found. Sources may be temporarily unavailable.</p>'}
</div>
<div class="footer">
  Thunderbird OS // Dreams2Memories Travel, LLC
</div>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Thunderbird Claude Code Intelligence Digest")
    print("=" * 50)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    seen = load_seen()
    print(f"Loaded {len(seen)} previously seen URLs.")

    # Fetch from all sources
    sources = {
        "GitHub Releases": fetch_github_releases,
        "Anthropic News": fetch_anthropic_news,
        "Hacker News": fetch_hackernews,
        "Reddit r/ClaudeAI": fetch_reddit,
    }

    grouped: dict[str, list[dict]] = {}
    all_urls: set[str] = set()

    for name, fetcher in sources.items():
        print(f"  Fetching {name}...", end=" ", flush=True)
        items = fetcher()
        # Deduplicate within source
        deduped = []
        for item in items:
            if item["url"] and item["url"] not in all_urls:
                all_urls.add(item["url"])
                deduped.append(item)
        grouped[name] = deduped
        print(f"{len(deduped)} articles")

    total = sum(len(v) for v in grouped.values())
    new_count = sum(1 for items in grouped.values() for a in items if a["url"] not in seen)
    print(f"\nTotal: {total} articles, {new_count} new")

    # Render HTML
    html = render_html(grouped, seen, now_str)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML written to {OUTPUT_HTML}")

    # Update seen list
    for items in grouped.values():
        for art in items:
            if art["url"]:
                seen.add(art["url"])
    save_seen(seen)
    print(f"Seen list updated: {len(seen)} total URLs tracked.")
    print("Done.")


if __name__ == "__main__":
    main()
