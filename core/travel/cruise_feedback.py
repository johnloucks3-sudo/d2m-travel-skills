#!/usr/bin/env python3
"""
cruise_feedback.py — Voyage sentiment from Cruise Critic + Reddit.

Two sources (both free, no auth required for read-only):
  cruise_critic_reviews(ship_name) → Firecrawl scrape of CC review pages
  reddit_sentiment(ship_name) → Reddit public search API

Usage:
    from core.travel.cruise_feedback import feedback_brief
    print(feedback_brief("Silver Muse"))
"""
import os
import requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
FC_BASE = "https://api.firecrawl.dev/v1"
REDDIT_HEADERS = {"User-Agent": "Thunderbird-D2M/1.0 travel-research"}


def _fc_key() -> str:
    k = os.environ.get("FIRECRAWL_API_KEY", "")
    if not k:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("FIRECRAWL_API_KEY=") and not line.startswith("#"):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        raise RuntimeError("FIRECRAWL_API_KEY not set in .env")
    return k


def _firecrawl_scrape(url: str) -> dict:
    r = requests.post(f"{FC_BASE}/scrape",
        headers={"Authorization": f"Bearer {_fc_key()}", "Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"]}, timeout=30)
    r.raise_for_status()
    return r.json().get("data", {})


def cruise_critic_reviews(ship_name: str) -> list[dict]:
    """Scrape Cruise Critic for ship reviews via Firecrawl."""
    slug = ship_name.lower().replace(" ", "-")
    url = f"https://www.cruisecritic.com/reviews/ship.cfm?shipid={slug}"
    try:
        data = _firecrawl_scrape(url)
        return [{"source": "cruise_critic", "ship": ship_name, "url": url,
                 "content": data.get("markdown", ""), "metadata": data.get("metadata", {})}]
    except Exception as e:
        return [{"source": "cruise_critic", "ship": ship_name, "error": str(e)}]


def _reddit_search(query: str, subreddit: str = "CruiseTravel", limit: int = 25) -> list[dict]:
    r = requests.get(
        f"https://www.reddit.com/r/{subreddit}/search.json",
        params={"q": query, "sort": "relevance", "limit": limit, "t": "year"},
        headers=REDDIT_HEADERS, timeout=20)
    r.raise_for_status()
    posts = r.json().get("data", {}).get("children", [])
    return [{"title": p["data"]["title"], "score": p["data"]["score"],
             "url": f"https://reddit.com{p['data']['permalink']}",
             "selftext": p["data"].get("selftext", "")[:500]}
            for p in posts]


def reddit_sentiment(ship_name: str, subreddits: list[str] = None) -> list[dict]:
    """Pull recent Reddit posts about a ship from travel subreddits."""
    if subreddits is None:
        subreddits = ["CruiseTravel", "Cruise", "travel"]
    results = []
    for sub in subreddits:
        try:
            results.extend(_reddit_search(ship_name, subreddit=sub))
        except Exception as e:
            results.append({"subreddit": sub, "error": str(e)})
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


def feedback_brief(ship_name: str) -> str:
    """One-call summary: CC reviews + Reddit sentiment for a ship."""
    cc = cruise_critic_reviews(ship_name)
    reddit = reddit_sentiment(ship_name)
    cc_summary = cc[0].get("content", "")[:800] if cc else "No CC data"
    top_str = "\n".join(
        f"  [{r.get('score',0)}] {r.get('title','')}" for r in reddit[:5]
    )
    return (f"=== CRUISE FEEDBACK: {ship_name} ===\n"
            f"Cruise Critic (excerpt):\n{cc_summary}\n\n"
            f"Reddit top posts:\n{top_str}")


if __name__ == "__main__":
    import sys
    ship = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Silver Muse"
    print(feedback_brief(ship))
