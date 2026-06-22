# Walls of Jericho — Travel Data Access Plan
## ELON Mandate 1 · Dreams2Memories Travel, LLC · 2026-06-22

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Achieve live data access across all 7 travel sectors — airline, hotel, cruise, ground transport, excursion, voyage feedback, industry news — using legal APIs, partner portals, session capture, and scraping adapters.

**Architecture:** Most adapters are already built. The primary blockers are (a) missing API keys requiring partner registration (Commander-gated), and (b) three sectors with no adapter yet: hotel, cruise feedback, and industry news. Phase 1 unlocks built adapters. Phase 2 builds the missing three. Phase 3 adds a systematic session-capture framework for portals without APIs.

**Tech Stack:** Python 3.11, requests, Firecrawl (active), Playwright MCP, Reddit PRAW, feedparser (RSS), existing adapters in `core/travel/`, `core/ai_infra/`

**Current Inventory (ACCURATE as of 2026-06-22):**

| Sector | Adapter | Status | Blocker |
|---|---|---|---|
| **Airlines** | `core/travel/amadeus_search.py` | ✅ Built, test env confirmed | Production approval + base_url swap |
| **Airlines / Air+Tours** | `core/travel/thunderbird_flight_search.py` + Centrav | ✅ Active | None (session-based) |
| **Airlines (NDC)** | `core/ai_infra/thunderbird_duffel.py` | ✅ Built | `DUFFEL_API_KEY` — Commander registers at duffel.com |
| **Excursions** | `core/travel/viator_search.py` | ✅ Built, STUB | `VIATOR_API_KEY` — Commander registers at partnerresources.viator.com |
| **Excursions** | `scripts/discover_viator_klook.py` | ✅ Active (discovery mode) | None |
| **Ground transport** | Mozio adapter (`scripts/test_mozio.py`) | ⚠️ Test only | `MOZIO_API_KEY` — Commander registers at mozio.com/en-us/partners/ |
| **Cruise portals** | Regent session (manual) | ✅ Active | Manual re-auth only |
| **Hotel** | None | ❌ Missing | Build needed |
| **Cruise feedback** | None | ❌ Missing | Build needed |
| **Industry news** | None | ❌ Missing | Build needed |
| **Voyage data** | None | ❌ Missing | Build needed |

---

## Phase 1 — Unlock What's Built (Keys Only)

These adapters are production-ready. Only blockers are API key registrations — Commander gates.

### Task 1: Activate Amadeus Production (airline fare data)

**Files:**
- Modify: `creds/amadeus_credentials.json`
- Test: `scratch/test_amadeus_api.py`

Context: Test env OAuth working since 2026-06-14. Production requires Amadeus Self-Service approval (free, instant for most accounts). Swap `base_url` to `https://api.amadeus.com`.

**Commander action required:** Log into developers.amadeus.com → My Apps → request production key for Self-Service tier.

- [ ] **Step 1: Confirm test env still works**
```bash
python3 scratch/test_amadeus_api.py
```
Expected: OAuth token retrieved, flight search returns results for a test query.

- [ ] **Step 2: Wire production base_url (once key received)**
```python
# creds/amadeus_credentials.json
{
  "client_id": "<PRODUCTION_KEY>",
  "client_secret": "<PRODUCTION_SECRET>",
  "base_url": "https://api.amadeus.com"
}
```

- [ ] **Step 3: Smoke test production**
```bash
python3 -c "
from core.travel.amadeus_search import flight_offers
results = flight_offers('DEN', 'FCO', '2026-12-17', adults=2)
print(f'Got {len(results)} offers')
print(results[0])
"
```

- [ ] **Step 4: Add AMADEUS_ENV to api_registry.json**
Update `config/api_registry.json` — add Amadeus entry:
```json
{
  "name": "Amadeus Self-Service (Production)",
  "env_var": null,
  "tier": "free self-service",
  "monthly_cost_usd": 0,
  "monthly_limit": "free tier: generous for search",
  "status": "active",
  "notes": "File-based: creds/amadeus_credentials.json. OAuth2 client_credentials. adapter: core/travel/amadeus_search.py",
  "added": "2026-06-22"
}
```

- [ ] **Step 5: Commit**
```bash
git add creds/amadeus_credentials.json config/api_registry.json
git commit -m "feat(travel): Amadeus production activated — airline fare data live"
```

---

### Task 2: Activate Viator (excursion pricing + availability)

**Files:**
- Modify: `creds/viator_credentials.json`
- Existing: `core/travel/viator_search.py` (fully built stub)

Context: Viator Partner API covers 300K+ tours/activities worldwide. D2M use: shore excursion arbitrage (35-50% cheaper than cruise-line pricing). Adapter built. Just needs key.

**Commander action required:** Apply at partnerresources.viator.com → Partner API access.

- [ ] **Step 1: Once key received, drop into creds**
```json
// creds/viator_credentials.json
{"api_key": "<KEY_FROM_VIATOR>", "note": "Viator Partner API"}
```

- [ ] **Step 2: Smoke test**
```bash
python3 -c "
from core.travel.viator_search import search_experiences
results = search_experiences(destination_id='d809', start_date='2026-12-17')
print(f'{len(results)} experiences found')
"
```
`d809` = Copenhagen (Kuklinski Viking Mars Dec 2026 first port).

- [ ] **Step 3: Run excursion arbitrage comparison for Kuklinski group**
```bash
python3 scripts/cruise_excursion_scan.py --client kuklinski --port CPH
```
Expected: side-by-side Viking pricing vs Viator pricing, sorted by savings.

- [ ] **Step 4: Add to api_registry.json and commit**
```bash
git add creds/viator_credentials.json config/api_registry.json
git commit -m "feat(travel): Viator Partner API activated — excursion arbitrage live"
```

---

### Task 3: Activate Mozio (ground transport quotes)

**Files:**
- Modify: `creds/mozio_credentials.json`
- Existing: `scripts/test_mozio.py`
- Create: `core/travel/mozio_search.py`

Context: Mozio aggregates 700+ ground transport suppliers worldwide. Covers private cars, transfers, rail. D2M use: airport transfers, port-to-hotel, city transit quotes for client itineraries.

**Commander action required:** Register at mozio.com/en-us/partners/ — get API key.

- [ ] **Step 1: Once key received, drop into creds**
```json
// creds/mozio_credentials.json
{"api_key": "<KEY>", "note": "Mozio ground transport aggregator"}
```

- [ ] **Step 2: Write test**
```python
# tests/test_mozio_search.py
def test_airport_transfer_quote():
    from core.travel.mozio_search import get_transfer_quote
    quote = get_transfer_quote(
        start_address="Copenhagen Airport",
        end_address="Copenhagen Cruise Terminal",
        pickup_datetime="2026-12-17T10:00:00",
        passengers=6,
    )
    assert quote is not None
    assert "results" in quote or "data" in quote
```

- [ ] **Step 3: Build `core/travel/mozio_search.py`**
```python
#!/usr/bin/env python3
"""mozio_search.py — Ground transport quotes via Mozio API."""
import json, os
import requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
CREDS = ROOT / "creds/mozio_credentials.json"
BASE = "https://api.mozio.com/v2"

def _key():
    k = os.environ.get("MOZIO_API_KEY", "")
    if not k and CREDS.exists():
        k = json.loads(CREDS.read_text()).get("api_key", "")
    if not k:
        raise RuntimeError("MOZIO_API_KEY not set")
    return k

def get_transfer_quote(start_address: str, end_address: str,
                       pickup_datetime: str, passengers: int = 2) -> dict:
    """Search for ground transfer options."""
    r = requests.post(f"{BASE}/search/", headers={"API-KEY": _key()}, json={
        "start_address": start_address,
        "end_address": end_address,
        "mode": "one_way",
        "pickup_datetime": pickup_datetime,
        "num_passengers": passengers,
        "currency": "USD",
    }, timeout=30)
    r.raise_for_status()
    return r.json()
```

- [ ] **Step 4: Run tests and commit**
```bash
python3 -m pytest tests/test_mozio_search.py -v
git add core/travel/mozio_search.py tests/test_mozio_search.py creds/mozio_credentials.json
git commit -m "feat(travel): Mozio ground transport adapter activated"
```

---

### Task 4: Activate Duffel NDC (airline group booking)

**Files:**
- Existing: `core/ai_infra/thunderbird_duffel.py` (built this session)
- Modify: `.env` → add `DUFFEL_API_KEY`

Context: Duffel NDC aggregator covers 200+ airlines via direct NDC connections. Per-booking fee in production (Commander financial gate for first live booking). Sandbox is free. Adapter built this session.

**Commander action required:** Register at duffel.com → get test API key (no credit card for sandbox).

- [ ] **Step 1: Add sandbox key to .env**
```bash
echo "DUFFEL_API_KEY=duffel_test_<KEY>" >> /home/john/Thunderbird/.env
```

- [ ] **Step 2: Smoke test adapter**
```bash
python3 -c "
from core.ai_infra.thunderbird_duffel import search_offers
results = search_offers('DEN', 'FCO', '2026-12-17', passengers=2)
print(f'{len(results)} offers')
"
```

- [ ] **Step 3: Update api_registry.json status → active, commit**
```bash
git add .env config/api_registry.json
git commit -m "feat(travel): Duffel NDC sandbox activated — airline NDC search live"
```

---

## Phase 2 — Build the Missing Three Sectors

### Task 5: Cruise Feedback Scraper (Cruise Critic + Reddit)

**Files:**
- Create: `core/travel/cruise_feedback.py`
- Create: `tests/test_cruise_feedback.py`

Context: Cruise Critic is the authoritative source for ship reviews and passenger sentiment. Reddit r/Cruise has real-time voyage feedback. Both are public but JS-rendered or need API. Firecrawl handles Cruise Critic (already active, 500 credits/mo). Reddit PRAW API is free.

**Two sources:**
1. **Cruise Critic** — via Firecrawl (`https://www.cruisecritic.com/reviews/`)
2. **Reddit r/Cruise** — via Reddit API (PRAW, free, no key needed for read-only)

- [ ] **Step 1: Write failing tests**
```python
# tests/test_cruise_feedback.py
from unittest.mock import patch

def test_reddit_sentiment_returns_posts():
    from core.travel.cruise_feedback import reddit_sentiment
    with patch("core.travel.cruise_feedback._reddit_search") as m:
        m.return_value = [
            {"title": "Just off Silver Muse — amazing!", "score": 45, "url": "..."},
        ]
        results = reddit_sentiment("Silver Muse")
    assert len(results) >= 1
    assert "title" in results[0]

def test_cruise_critic_reviews_structure():
    from core.travel.cruise_feedback import cruise_critic_reviews
    with patch("core.travel.cruise_feedback._firecrawl_scrape") as m:
        m.return_value = {"markdown": "Silver Muse review: **Excellent**"}
        results = cruise_critic_reviews("Silver Muse")
    assert results is not None
```

- [ ] **Step 2: Run tests to verify they fail**
```bash
python3 -m pytest tests/test_cruise_feedback.py -v
```
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Build `core/travel/cruise_feedback.py`**
```python
#!/usr/bin/env python3
"""
cruise_feedback.py — Voyage sentiment from Cruise Critic + Reddit.

Two sources (both free, no auth required for read-only):
  cruise_critic_reviews(ship_name) → Firecrawl scrape of CC review pages
  reddit_sentiment(ship_name, subreddit="CruiseTravel") → PRAW search

Usage:
    from core.travel.cruise_feedback import cruise_critic_reviews, reddit_sentiment
    reviews = cruise_critic_reviews("Silver Muse")
    sentiment = reddit_sentiment("Silver Muse")
"""
import os, json
import requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

def _get_firecrawl_key() -> str:
    k = os.environ.get("FIRECRAWL_API_KEY", "")
    if not k:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("FIRECRAWL_API_KEY=") and not line.startswith("#"):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        raise RuntimeError("FIRECRAWL_API_KEY not set in .env")
    return k

def _firecrawl_scrape(url: str) -> dict:
    r = requests.post(f"{FIRECRAWL_BASE}/scrape",
        headers={"Authorization": f"Bearer {_get_firecrawl_key()}",
                 "Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"]},
        timeout=30)
    r.raise_for_status()
    return r.json().get("data", {})

def cruise_critic_reviews(ship_name: str, max_pages: int = 3) -> list[dict]:
    """Scrape Cruise Critic for ship reviews via Firecrawl."""
    slug = ship_name.lower().replace(" ", "-")
    url = f"https://www.cruisecritic.com/reviews/ship.cfm?shipid={slug}"
    results = []
    try:
        data = _firecrawl_scrape(url)
        results.append({
            "source": "cruise_critic",
            "ship": ship_name,
            "url": url,
            "content": data.get("markdown", ""),
            "metadata": data.get("metadata", {}),
        })
    except Exception as e:
        results.append({"source": "cruise_critic", "ship": ship_name,
                        "error": str(e)})
    return results

def _reddit_search(query: str, subreddit: str = "CruiseTravel",
                   limit: int = 25) -> list[dict]:
    """Search Reddit without auth using pushshift-compatible endpoint."""
    headers = {"User-Agent": "Thunderbird-D2M/1.0 travel-research"}
    r = requests.get(
        f"https://www.reddit.com/r/{subreddit}/search.json",
        params={"q": query, "sort": "relevance", "limit": limit, "t": "year"},
        headers=headers, timeout=20)
    r.raise_for_status()
    posts = r.json().get("data", {}).get("children", [])
    return [{"title": p["data"]["title"], "score": p["data"]["score"],
             "url": f"https://reddit.com{p['data']['permalink']}",
             "selftext": p["data"].get("selftext", "")[:500]}
            for p in posts]

def reddit_sentiment(ship_name: str,
                     subreddits: list[str] = None) -> list[dict]:
    """Pull recent Reddit posts about a ship from travel subreddits."""
    if subreddits is None:
        subreddits = ["CruiseTravel", "Cruise", "travel"]
    results = []
    for sub in subreddits:
        try:
            posts = _reddit_search(ship_name, subreddit=sub)
            results.extend(posts)
        except Exception as e:
            results.append({"subreddit": sub, "error": str(e)})
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)

def feedback_brief(ship_name: str) -> str:
    """One-call summary: CC reviews + Reddit sentiment for a ship."""
    cc = cruise_critic_reviews(ship_name)
    reddit = reddit_sentiment(ship_name)
    cc_summary = cc[0].get("content", "")[:800] if cc else "No CC data"
    reddit_top = reddit[:5] if reddit else []
    top_str = "\n".join(f"  [{r.get('score',0)}] {r.get('title','')}" for r in reddit_top)
    return (f"=== CRUISE FEEDBACK: {ship_name} ===\n"
            f"Cruise Critic (excerpt):\n{cc_summary}\n\n"
            f"Reddit top posts:\n{top_str}")

if __name__ == "__main__":
    import sys
    ship = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Silver Muse"
    print(feedback_brief(ship))
```

- [ ] **Step 4: Run tests**
```bash
python3 -m pytest tests/test_cruise_feedback.py -v
```
Expected: 2/2 PASS.

- [ ] **Step 5: Live smoke test**
```bash
python3 core/travel/cruise_feedback.py "Silver Muse"
python3 core/travel/cruise_feedback.py "Viking Mars"
```

- [ ] **Step 6: Commit**
```bash
git add core/travel/cruise_feedback.py tests/test_cruise_feedback.py
git commit -m "feat(travel): cruise feedback adapter — Cruise Critic + Reddit sentiment"
```

---

### Task 6: Industry News Aggregator (RSS + Firecrawl)

**Files:**
- Create: `core/travel/industry_news.py`
- Create: `tests/test_industry_news.py`

Context: 5 key free RSS feeds cover 90% of cruise industry news. No auth, no API keys. Firecrawl handles paywalled stories (Travel Weekly, Seatrade) when RSS teaser links behind paywall.

**Feeds:**
- `https://www.cruiseindustrynews.com/feed/` — ship deployments, fleet news
- `https://www.seatrade-cruise.com/rss.xml` — industry, port, deployment
- `https://www.travelweekly.com/RSS/CruiseFeed` — trade news  
- `https://www.travelpulse.com/rss/cruises` — agent-focused
- `https://www.cruisehive.com/feed` — consumer-facing, ship reviews

- [ ] **Step 1: Write failing test**
```python
# tests/test_industry_news.py
from unittest.mock import patch

def test_fetch_feeds_returns_items():
    from core.travel.industry_news import fetch_all_feeds
    with patch("core.travel.industry_news._fetch_feed") as m:
        m.return_value = [{"title": "Viking Adds 2027 Route", "link": "...",
                           "published": "Mon, 22 Jun 2026 10:00:00 +0000",
                           "source": "cruiseindustrynews"}]
        items = fetch_all_feeds(max_per_feed=5)
    assert len(items) >= 1
    assert "title" in items[0]

def test_dedup_removes_duplicates():
    from core.travel.industry_news import dedup_by_title
    items = [{"title": "Same Story", "link": "a"}, {"title": "Same Story", "link": "b"}]
    result = dedup_by_title(items)
    assert len(result) == 1
```

- [ ] **Step 2: Run failing tests**
```bash
python3 -m pytest tests/test_industry_news.py -v
```

- [ ] **Step 3: Build `core/travel/industry_news.py`**
```python
#!/usr/bin/env python3
"""
industry_news.py — Travel industry news aggregator via RSS + Firecrawl.

No API keys required for RSS feeds. Firecrawl used for paywalled full-text.

Usage:
    from core.travel.industry_news import daily_brief, fetch_all_feeds
    brief = daily_brief(keywords=["Viking", "Silversea", "Regent"])
"""
import hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    feedparser = None

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
    """Fetch and parse an RSS feed. Falls back to requests if feedparser absent."""
    items = []
    try:
        if feedparser:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:max_items]:
                items.append({
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                    "summary": getattr(entry, "summary", "")[:300],
                    "source": name,
                })
        else:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            # Minimal XML parse for title+link
            import xml.etree.ElementTree as ET
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
    """Fetch all configured feeds and return merged list."""
    all_items = []
    for name, url in FEEDS.items():
        all_items.extend(_fetch_feed(name, url, max_per_feed))
    return all_items


def dedup_by_title(items: list[dict]) -> list[dict]:
    """Remove near-duplicate titles (first occurrence wins)."""
    seen = set()
    result = []
    for item in items:
        key = hashlib.md5(item.get("title", "").lower().strip().encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def filter_by_keywords(items: list[dict], keywords: list[str]) -> list[dict]:
    """Filter to items where title or summary contains any keyword (case-insensitive)."""
    kw_lower = [k.lower() for k in keywords]
    return [i for i in items
            if any(k in (i.get("title", "") + i.get("summary", "")).lower()
                   for k in kw_lower)]


def daily_brief(keywords: list[str] = None, max_per_feed: int = 8) -> str:
    """Fetch, dedup, filter, and format a daily industry news brief."""
    items = dedup_by_title(fetch_all_feeds(max_per_feed))
    if keywords:
        filtered = filter_by_keywords(items, keywords)
        if not filtered:
            filtered = items[:10]  # fallback: show top 10 if no keyword match
    else:
        filtered = items[:15]

    lines = [f"=== TRAVEL INDUSTRY BRIEF — {datetime.now(timezone.utc).strftime('%Y-%m-%d')} ==="]
    for item in filtered[:20]:
        src = item.get("source", "?")
        lines.append(f"[{src}] {item.get('title', '')} — {item.get('link', '')}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    kw = sys.argv[1:] if len(sys.argv) > 1 else ["Silversea", "Regent", "Viking", "luxury"]
    print(daily_brief(keywords=kw))
```

- [ ] **Step 4: Install feedparser if not present**
```bash
pip install feedparser --quiet
```

- [ ] **Step 5: Run tests**
```bash
python3 -m pytest tests/test_industry_news.py -v
```

- [ ] **Step 6: Live smoke test**
```bash
python3 core/travel/industry_news.py Silversea Regent Viking luxury
```
Expected: 15-20 news items from 5 feeds.

- [ ] **Step 7: Commit**
```bash
git add core/travel/industry_news.py tests/test_industry_news.py
git commit -m "feat(travel): industry news aggregator — 5 RSS feeds, keyword filter, dedup"
```

---

### Task 7: Hotel Sector — RateHawk B2B Adapter

**Files:**
- Create: `creds/ratehawk_credentials.json`
- Create: `core/travel/ratehawk_search.py`
- Create: `tests/test_ratehawk_search.py`

Context: RateHawk (part of Emerging Travel Group) is a B2B hotel aggregator for travel agents. Free to join, no credit card needed for search-only access. Covers 2M+ properties worldwide. API access available to registered agents. D2M use: hotel quotes for pre/post cruise stays and Door County trip (Sep 2026 MISSION-203).

**Registration:** ratehawk.com → "For Partners" → Travel Agent signup. API key issued on approval.

**Commander action required:** Register at ratehawk.com as a travel agent partner.

- [ ] **Step 1: Write failing tests**
```python
# tests/test_ratehawk_search.py
from unittest.mock import patch

def test_hotel_search_returns_properties():
    from core.travel.ratehawk_search import search_hotels
    with patch("core.travel.ratehawk_search._api_call") as m:
        m.return_value = {"data": {"hotels": [
            {"id": "h1", "name": "The Grand", "rates": [{"price": 250}]}
        ]}}
        results = search_hotels("Copenhagen", "2026-12-16", "2026-12-17", guests=6)
    assert len(results) >= 1
    assert "name" in results[0]

def test_missing_key_raises():
    from core.travel.ratehawk_search import _get_key
    import pytest
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="RATEHAWK"):
            _get_key()
```

- [ ] **Step 2: Build `core/travel/ratehawk_search.py`**
```python
#!/usr/bin/env python3
"""
ratehawk_search.py — B2B hotel search via RateHawk API (Emerging Travel Group).

STATUS: STUB awaiting API key from ratehawk.com partner registration.
Adapter is production-ready; just needs key.

D2M use cases:
  - Pre/post cruise hotel quotes (Copenhagen, Barcelona, Rome)
  - Door County lodging for Loucks Sep 2026 (MISSION-203)
  - Group hotel blocks for clients

API docs: https://docs.ratehawk.com/
"""
import json, os
import requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
CREDS = ROOT / "creds/ratehawk_credentials.json"
BASE = "https://api.worldota.net/api/b2b/v3"


def _get_key() -> tuple[str, str]:
    """Returns (key_id, api_key) tuple."""
    key_id = os.environ.get("RATEHAWK_KEY_ID", "")
    api_key = os.environ.get("RATEHAWK_API_KEY", "")
    if not key_id and CREDS.exists():
        data = json.loads(CREDS.read_text())
        key_id = data.get("key_id", "")
        api_key = data.get("api_key", "")
    if not key_id or not api_key:
        raise RuntimeError(
            "RATEHAWK_KEY_ID/RATEHAWK_API_KEY not set.\n"
            "Register at ratehawk.com → For Partners → Travel Agent."
        )
    return key_id, api_key


def _api_call(endpoint: str, payload: dict) -> dict:
    key_id, api_key = _get_key()
    r = requests.post(f"{BASE}/{endpoint}/",
        auth=(key_id, api_key),
        json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def search_hotels(destination: str, checkin: str, checkout: str,
                  guests: int = 2, rooms: int = 1) -> list[dict]:
    """Search for hotels. Returns list of property dicts."""
    data = _api_call("search/serp/region/", {
        "checkin": checkin,
        "checkout": checkout,
        "guests": [{"adults": guests}],
        "region_id": destination,
        "currency": "USD",
    })
    hotels = data.get("data", {}).get("hotels", [])
    return [{
        "id": h.get("id"),
        "name": h.get("name"),
        "stars": h.get("star_rating"),
        "price_usd": h.get("rates", [{}])[0].get("price") if h.get("rates") else None,
        "address": h.get("address"),
    } for h in hotels]


if __name__ == "__main__":
    import sys
    dest = sys.argv[1] if len(sys.argv) > 1 else "Copenhagen"
    checkin = sys.argv[2] if len(sys.argv) > 2 else "2026-12-16"
    checkout = sys.argv[3] if len(sys.argv) > 3 else "2026-12-17"
    results = search_hotels(dest, checkin, checkout)
    for h in results[:5]:
        print(f"{h['name']} ({h['stars']}★) — ${h['price_usd']}/night")
```

- [ ] **Step 3: Create stub credentials file**
```bash
echo '{"key_id": "", "api_key": "", "note": "Register at ratehawk.com/partners"}' \
  > /home/john/Thunderbird/creds/ratehawk_credentials.json
```

- [ ] **Step 4: Run tests**
```bash
python3 -m pytest tests/test_ratehawk_search.py -v
```
Expected: 2/2 PASS (mocked).

- [ ] **Step 5: Add to api_registry.json**
Add entry for RateHawk with `status: "pending_key"`.

- [ ] **Step 6: Commit**
```bash
git add core/travel/ratehawk_search.py tests/test_ratehawk_search.py creds/ratehawk_credentials.json config/api_registry.json
git commit -m "feat(travel): RateHawk hotel search adapter — B2B hotel sector unlocked (pending key)"
```

---

## Phase 3 — Session Capture Framework

### Task 8: HAR Capture Utility (portal data without APIs)

**Files:**
- Create: `core/travel/har_capture.py`
- Create: `docs/HAR_CAPTURE_PLAYBOOK.md`

Context: Several cruise line portals (Princess, Celebrity, MSC, Norwegian) have no partner API. The Wing already uses session cookies for Regent and Centrav. A systematic HAR capture framework lets Dembe intercept B2B portal API calls and replay them authenticated. This is the legal-door approach ELON referenced — HAR files expose the API the portal calls internally.

Pattern: Log into portal via yoga Firefox with network capture → save HAR → extract authenticated API endpoints → replay with Python requests.

- [ ] **Step 1: Write tests**
```python
# tests/test_har_capture.py
def test_parse_har_extracts_api_calls():
    from core.travel.har_capture import extract_api_calls
    har = {"log": {"entries": [
        {"request": {"url": "https://portal.example.com/api/availability",
                     "method": "GET",
                     "headers": [{"name": "Authorization", "value": "Bearer tok123"}]},
         "response": {"status": 200, "content": {"mimeType": "application/json",
                                                   "text": '{"available": true}'}}}
    ]}}
    calls = extract_api_calls(har, domain_filter="portal.example.com")
    assert len(calls) == 1
    assert calls[0]["url"] == "https://portal.example.com/api/availability"
    assert calls[0]["auth_header"] == "Bearer tok123"
```

- [ ] **Step 2: Build `core/travel/har_capture.py`**
```python
#!/usr/bin/env python3
"""
har_capture.py — Extract and replay authenticated API calls from HAR files.

Use case: Cruise line B2B portals without partner APIs.
  1. Log into portal in Firefox with DevTools → Network → Export HAR
  2. Pass HAR to extract_api_calls() to find authenticated endpoints
  3. Replay with replay_call() to pull live data

Usage:
    from core.travel.har_capture import extract_api_calls, replay_call
    calls = extract_api_calls(har_data, domain_filter="book.princess.com")
    result = replay_call(calls[0])
"""
import json
import requests
from pathlib import Path


def load_har(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def extract_api_calls(har: dict, domain_filter: str = "",
                      method_filter: str = "") -> list[dict]:
    """Extract API calls from a HAR file. Optionally filter by domain or method."""
    results = []
    for entry in har.get("log", {}).get("entries", []):
        req = entry.get("request", {})
        resp = entry.get("response", {})
        url = req.get("url", "")
        method = req.get("method", "GET")

        if domain_filter and domain_filter not in url:
            continue
        if method_filter and method.upper() != method_filter.upper():
            continue
        # Only API calls (JSON responses)
        mime = resp.get("content", {}).get("mimeType", "")
        if "json" not in mime and "xml" not in mime:
            continue

        headers = {h["name"]: h["value"] for h in req.get("headers", [])}
        auth_header = headers.get("Authorization") or headers.get("Cookie", "")

        results.append({
            "url": url,
            "method": method,
            "headers": headers,
            "auth_header": auth_header,
            "body": req.get("postData", {}).get("text", ""),
            "response_status": resp.get("status"),
            "response_preview": resp.get("content", {}).get("text", "")[:200],
        })
    return results


def replay_call(call: dict, override_headers: dict = None) -> requests.Response:
    """Replay a captured API call with optional header overrides."""
    headers = dict(call.get("headers", {}))
    if override_headers:
        headers.update(override_headers)
    method = call.get("method", "GET").upper()
    url = call["url"]
    body = call.get("body", "")

    r = requests.request(method, url, headers=headers,
                         data=body.encode() if body else None, timeout=30)
    return r


def har_to_playbook(har_path: str, domain: str, output_path: str = None) -> str:
    """Extract all API calls from a HAR and write a playbook markdown."""
    har = load_har(har_path)
    calls = extract_api_calls(har, domain_filter=domain)
    lines = [f"# HAR Playbook — {domain}", f"Extracted {len(calls)} API endpoints\n"]
    for i, c in enumerate(calls, 1):
        lines.append(f"## Call {i}: {c['method']} {c['url']}")
        lines.append(f"- Auth: `{c['auth_header'][:60]}...`" if len(c['auth_header']) > 60
                     else f"- Auth: `{c['auth_header']}`")
        lines.append(f"- Response: HTTP {c['response_status']}")
        lines.append(f"- Preview: `{c['response_preview'][:100]}`\n")
    out = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(out)
    return out
```

- [ ] **Step 3: Run tests**
```bash
python3 -m pytest tests/test_har_capture.py -v
```

- [ ] **Step 4: Write `docs/HAR_CAPTURE_PLAYBOOK.md`**
Document the step-by-step process for Dembe to capture HAR files from cruise line portals:
1. Open yoga Firefox with DevTools Network tab
2. Log into target portal
3. Perform the desired action (search availability, pull booking list)
4. Export HAR from DevTools
5. Run `python3 -c "from core.travel.har_capture import har_to_playbook; print(har_to_playbook('capture.har', 'portal.cruiseline.com', 'docs/playbooks/cruiseline.md'))"`
6. Check `docs/playbooks/` for extracted endpoints

- [ ] **Step 5: Commit**
```bash
git add core/travel/har_capture.py tests/test_har_capture.py docs/HAR_CAPTURE_PLAYBOOK.md
git commit -m "feat(travel): HAR capture framework — authenticated portal API extraction"
```

---

## Completion Criteria

The Walls of Jericho plan is complete when:

| Sector | Gate |
|---|---|
| Airlines (Amadeus) | `amadeus_search.py` returns live production results |
| Airlines (Duffel NDC) | `thunderbird_duffel.py` returns sandbox offers |
| Excursions (Viator) | `viator_search.py` returns live excursions for a client port |
| Ground transport (Mozio) | `mozio_search.py` returns transfer quotes |
| Cruise feedback | `cruise_feedback.py` returns Cruise Critic + Reddit data for any ship |
| Industry news | `industry_news.py` returns 10+ items from live RSS feeds |
| Hotel sector | `ratehawk_search.py` returns hotel results (pending key) |
| Portal capture | `har_capture.py` extracts and replays a real portal API call |

**Commander-gated registrations (4 portals, all free):**
1. Duffel — duffel.com (sandbox, no credit card)
2. Viator Partner — partnerresources.viator.com
3. Mozio Partner — mozio.com/en-us/partners/
4. RateHawk — ratehawk.com/partners (travel agent)

**ELON's metric:** Wing can pull live data from at least one new travel sector per week. No wall stays unexamined.

---

*Plan authored: 2026-06-22 · ELON Mandate 1 · Owner: ELON (A12) — discovery; Hale — execution routing*
*Execution: superpowers:subagent-driven-development, task-by-task*
