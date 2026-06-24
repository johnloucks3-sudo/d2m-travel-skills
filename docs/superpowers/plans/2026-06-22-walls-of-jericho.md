# Walls of Jericho — Travel Data Access Plan

## ELON Mandate 1 · Dreams2Memories Travel, LLC · 2026-06-22

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- \[ \]`) syntax for tracking.

**Goal:** Achieve live data access across all 7 travel sectors — airline, hotel, cruise, ground transport, excursion, voyage feedback, industry news — using legal APIs, partner portals, session capture, and scraping adapters.

**Architecture~~:** Most adapters are already built. The primary blockers are (a) missing API keys requiring partner registration (Commander-gated), and (b) three sectors with no adapter yet: hotel, cruise feedback, and industry news. Phase 1 unlocks built adapters. Phase 2 builds the missing three. Phase 3 adds a systematic session-capture framework for portals without APIs.~~

**Tech Stack:** Python 3.11, requests, Firecrawl (active), Playwright MCP, Reddit PRAW, feedparser (RSS), existing adapters in `core/travel/`, `core/ai\_infra/`

**✅ EXECUTION IN PROGRESS — Session 2 complete. Commander review requested.**

**Assumptions removed (Commander feedback 2026-06-22):**

- ~~Amadeus~~ — not viable (no usable API, not paying)

- ~~Viator~~ — customer service unacceptable, not a viable partner

**Current Inventory (updated 2026-06-22 — session 2):**

| Sector | Adapter | Status | Blocker |
| - | - | - | - |
| **Airlines / Air+Tours** | `core/travel/thunderbird_flight_search.py` + Centrav | ✅ Active | None (session-based) |
| **Airlines (NDC)** | `core/ai_infra/thunderbird_duffel.py` | ✅ Built | `DUFFEL_API_KEY` — register at duffel.com |
| **Airlines (ITA Matrix)** | `core/travel/ita_matrix.py` | ✅ Built this session | Playwright 2-5 min compute time per search |
| **Ground transport** | Mozio adapter (`scripts/test_mozio.py`) | ⚠️ Test only | `MOZIO_API_KEY` — register at mozio.com/en-us/partners/ |
| **Cruise portals** | Regent session (manual) | ✅ Active | Manual re-auth only |
| **Hotel (B2B)** | `core/travel/roomres_search.py` | ✅ Built this session | Room-Res session JWT (~/Downloads/roomres_session.json) |
| **Cruise feedback** | `core/travel/cruise_feedback.py` | ✅ Built | None (Firecrawl + Reddit, no auth) |
| **Industry news** | `core/travel/industry_news.py` | ✅ Built | None (5 RSS feeds, no auth) |
| **Excursions (4 sources)** | `core/travel/excursion_aggregator.py` | ✅ Built this session (PE live, 3 key-gated) | GYG + SEG keys pending Commander registration |
| **Portal capture** | `core/travel/har_capture.py` | ✅ Built | None (HAR replay framework) |



## Phase 1 — Unlock What's Built (Keys Only)

These adapters are production-ready. Only blockers are API key registrations — Commander gates.

### ~~Task 1: Activate Amadeus Production (airline fare data)~~

~~**Files:~~**

- ~~Modify: `creds/amadeus\_credentials.json`~~

- ~~Test: `scratch/test\_amadeus\_api.py`~~

~~Context: Test env OAuth working since 2026-06-14. Production requires Amadeus Self-Service approval (free, instant for most accounts). Swap `base\_url` to `https://api.amadeus.com`.~~

~~**Commander action required:** Log into developers.amadeus.com → My Apps → request production key for Self-Service tier.~~

- ~~[ ] **Step 1: Confirm test env still works~~**

```
~~python3 scratch/test\_amadeus\_api.py~~
```

~~Expected: OAuth token retrieved, flight search returns results for a test query.~~

- ~~[ ] **Step 2: Wire production base\_url (once key received)~~**

```
~~\# creds/amadeus\_credentials.json  
\{  
  "client\_id": "\<PRODUCTION\_KEY\>",  
  "client\_secret": "\<PRODUCTION\_SECRET\>",  
  "base\_url": "https://api.amadeus.com"  
\}~~
```

- ~~[ ] **Step 3: Smoke test production~~**

```
~~python3 -c "  
from core.travel.amadeus\_search import flight\_offers  
results = flight\_offers('DEN', 'FCO', '2026-12-17', adults=2)  
print(f'Got \{len(results)\} offers')  
print(results\[0\])  
"~~
```

- ~~[ ] **Step 4: Add AMADEUS\_ENV to api\_registry.json** Update `config/api\_registry.json` — add Amadeus entry:~~

```
\{  
  "name": "Amadeus Self-Service (Production)",  
  "env\_var": null,  
  "tier": "free self-service",  
  "monthly\_cost\_usd": 0,  
  "monthly\_limit": "free tier: generous for search",  
  "status": "active",  
  "notes": "File-based: creds/amadeus\_credentials.json. OAuth2 client\_credentials. adapter: core/travel/amadeus\_search.py",  
  "added": "2026-06-22"  
\}
```

- [ ] **Step 5: Commit**

```
git add creds/amadeus\_credentials.json config/api\_registry.json  
git commit -m "feat(travel): Amadeus production activated — airline fare data live"
```


### ~~Task 2: Activate Viator (excursion pricing + availability)~~

~~**Files:~~**

- ~~Modify: `creds/viator\_credentials.json`~~

- ~~Existing: `core/travel/viator\_search.py` (fully built stub)~~

~~Context: Viator Partner API covers 300K+ tours/activities worldwide. D2M use: shore excursion arbitrage (35-50% cheaper than cruise-line pricing). Adapter built. Just needs key.~~

~~**Commander action required:** Apply at partnerresources.viator.com → Partner API access.~~

- ~~[ ] **Step 1: Once key received, drop into creds~~**

```
~~// creds/viator\_credentials.json  
\{"api\_key": "\<KEY\_FROM\_VIATOR\>", "note": "Viator Partner API"\}~~
```

- ~~[ ] **Step 2: Smoke test~~**

```
~~python3 -c "  
from core.travel.viator\_search import search\_experiences  
results = search\_experiences(destination\_id='d809', start\_date='2026-12-17')  
print(f'\{len(results)\} experiences found')  
"~~
```

~~`d809` = Copenhagen (Kuklinski Viking Mars Dec 2026 first port).~~

- ~~[ ] **Step 3: Run excursion arbitrage comparison for Kuklinski group~~**

```
~~python3 scripts/cruise\_excursion\_scan.py --client kuklinski --port CPH~~
```

~~Expected: side-by-side Viking pricing vs Viator pricing, sorted by savings.~~

- ~~[ ] **Step 4: Add to api\_registry.json and commit~~**

```
~~git add creds/viator\_credentials.json config/api\_registry.json  
git commit -m "feat(travel): Viator Partner API activated — excursion arbitrage~~ live"
```


### Task 2A: Excursion Sector — 4 Sources, 4 Adapters

**Commander directive 2026-06-22:** Viator eliminated. Replace with 4-source excursion stack: Project Expedition · GetYourGuide · Shore Excursions Group · EatWith. "3-4 bullets in every gun."

**Files:**
- Existing: `scripts/discover_viator_klook.py` (Project Expedition scraper — adapt)
- Create: `core/travel/getyourguide_search.py`
- Create: `core/travel/shore_excursions_search.py`
- Create: `core/travel/eatwith_search.py`
- Create: `core/travel/excursion_aggregator.py` (unified search across all 4)
- Create: `tests/test_excursion_aggregator.py`

---

#### Source 1: Project Expedition (scraper — already partially built)

Context: Scraper exists at `scripts/discover_viator_klook.py`. Imperva rate-based protection (~6 req/IP). Throttle from request 1 — no burst. Already in `reference_projectexpedition_api_scraping.md`.

- [ ] **Step 1: Adapt existing scraper into `core/travel/` module**
```python
# core/travel/project_expedition_search.py
# Pull from scripts/discover_viator_klook.py — extract the PE-specific logic
# Throttle: 1 req/3s minimum, randomized delay
# Returns: [{name, price_usd, duration_hrs, port, url}]
```

- [ ] **Step 2: Smoke test (throttled)**
```bash
python3 -c "
from core.travel.project_expedition_search import search_excursions
results = search_excursions(port='Copenhagen', max_results=5)
print(f'{len(results)} excursions')
for r in results[:3]: print(r['name'], r['price_usd'])
"
```

---

#### Source 2: GetYourGuide (Partner API — free, register)

Context: GetYourGuide has a Distribution/Partner API covering 100K+ activities globally. Free to register as a travel agent affiliate. Better API than Viator, no bad-customer-service history. Registration: partner.getyourguide.com

**Commander action required:** Register at partner.getyourguide.com → get API key.

- [ ] **Step 1: Once key received, add to creds**
```json
// creds/getyourguide_credentials.json
{"api_key": "<KEY>", "note": "GetYourGuide Partner API"}
```

- [ ] **Step 2: Build `core/travel/getyourguide_search.py`**
```python
#!/usr/bin/env python3
"""getyourguide_search.py — Excursions via GetYourGuide Partner API."""
import json, os, requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
CREDS = ROOT / "creds/getyourguide_credentials.json"
BASE = "https://api.getyourguide.com/1"

def _key():
    k = os.environ.get("GETYOURGUIDE_API_KEY", "")
    if not k and CREDS.exists():
        k = json.loads(CREDS.read_text()).get("api_key", "")
    if not k:
        raise RuntimeError("GETYOURGUIDE_API_KEY not set")
    return k

def search_activities(query: str, date: str = None, limit: int = 20) -> list[dict]:
    r = requests.get(f"{BASE}/activities",
        headers={"X-API-Key": _key(), "Accept": "application/json"},
        params={"q": query, "date_from": date, "limit": limit},
        timeout=20)
    r.raise_for_status()
    items = r.json().get("data", {}).get("activities", [])
    return [{"name": a.get("title"), "price_usd": a.get("price", {}).get("value"),
             "duration_hrs": a.get("duration"), "url": a.get("url"),
             "source": "getyourguide"} for a in items]
```

- [ ] **Step 3: Smoke test**
```bash
python3 -c "
from core.travel.getyourguide_search import search_activities
results = search_activities('Copenhagen shore excursion')
print(f'{len(results)} activities')
"
```

---

#### Source 3: Shore Excursions Group (Firecrawl scraper)

Context: shorexcursionsgroup.com — third-party excursion specialist, strong cruise port coverage, no public API. Firecrawl handles JS-rendered content (500 credits/mo active).

- [ ] **Step 1: Write test**
```python
# tests/test_shore_excursions.py
from unittest.mock import patch
def test_search_returns_excursions():
    from core.travel.shore_excursions_search import search_excursions
    with patch("core.travel.shore_excursions_search._scrape") as m:
        m.return_value = [{"name": "City Highlights", "price_usd": 89, "port": "Copenhagen"}]
        results = search_excursions("Copenhagen")
    assert len(results) >= 1
```

- [ ] **Step 2: Build `core/travel/shore_excursions_search.py`**
```python
#!/usr/bin/env python3
"""shore_excursions_search.py — Shore Excursions Group via Firecrawl."""
import os, re, requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
FC_BASE = "https://api.firecrawl.dev/v1"

def _fc_key():
    k = os.environ.get("FIRECRAWL_API_KEY", "")
    if not k:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("FIRECRAWL_API_KEY=") and not line.startswith("#"):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    return k

def _scrape(url: str) -> list[dict]:
    r = requests.post(f"{FC_BASE}/scrape",
        headers={"Authorization": f"Bearer {_fc_key()}"},
        json={"url": url, "formats": ["markdown"]}, timeout=30)
    r.raise_for_status()
    md = r.json().get("data", {}).get("markdown", "")
    # Parse markdown for tour names and prices (adapt after first run)
    items = []
    for line in md.splitlines():
        price_match = re.search(r'\$(\d+)', line)
        if price_match and len(line) > 10:
            items.append({"name": line[:80].strip(), 
                          "price_usd": int(price_match.group(1)),
                          "source": "shore_excursions_group"})
    return items

def search_excursions(port: str) -> list[dict]:
    slug = port.lower().replace(" ", "-")
    url = f"https://www.shorexcursionsgroup.com/port/{slug}/"
    return _scrape(url)
```

- [ ] **Step 3: Run tests**
```bash
python3 -m pytest tests/test_shore_excursions.py -v
```

---

#### Source 4: EatWith (local dining experiences)

Context: eatwith.com — curated local dining, cooking classes, food tours. Niche but high-value for luxury clients who want authentic food experiences in port. Has an affiliate program; API availability TBD — Firecrawl fallback.

- [ ] **Step 1: Research EatWith API availability**
```bash
python3 -c "
import requests
# Check if EatWith exposes an API endpoint
r = requests.get('https://www.eatwith.com/api/', timeout=10)
print(r.status_code, r.headers.get('content-type'))
"
```

- [ ] **Step 2: Build `core/travel/eatwith_search.py`** (Firecrawl path if no API)
```python
#!/usr/bin/env python3
"""eatwith_search.py — Local dining experiences via EatWith."""
import os, requests
from pathlib import Path

ROOT = Path(__file__).parents[2]
FC_BASE = "https://api.firecrawl.dev/v1"

def _fc_key():
    k = os.environ.get("FIRECRAWL_API_KEY", "")
    if not k:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("FIRECRAWL_API_KEY=") and not line.startswith("#"):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    return k

def search_experiences(city: str) -> list[dict]:
    """Search EatWith for dining experiences in a city."""
    url = f"https://www.eatwith.com/experiences/search?city={city.replace(' ', '+')}"
    r = requests.post(f"{FC_BASE}/scrape",
        headers={"Authorization": f"Bearer {_fc_key()}"},
        json={"url": url, "formats": ["markdown"]}, timeout=30)
    r.raise_for_status()
    md = r.json().get("data", {}).get("markdown", "")
    # Parse after first run — structure TBD from actual output
    return [{"raw": md[:500], "source": "eatwith", "city": city}]
```

---

#### Unified Aggregator

- [ ] **Step 5: Build `core/travel/excursion_aggregator.py`**
```python
#!/usr/bin/env python3
"""
excursion_aggregator.py — Unified excursion search across all 4 sources.
Runs all available sources in parallel, deduplicates, sorts by price.

Usage:
    from core.travel.excursion_aggregator import search_all
    results = search_all(port="Copenhagen", date="2026-12-17")
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.travel.project_expedition_search import search_excursions as pe_search
from core.travel.shore_excursions_search import search_excursions as seg_search
from core.travel.eatwith_search import search_experiences as ew_search

def search_all(port: str, date: str = None) -> list[dict]:
    sources = {
        "project_expedition": lambda: pe_search(port=port),
        "shore_excursions_group": lambda: seg_search(port=port),
        "eatwith": lambda: ew_search(city=port),
    }
    # GetYourGuide only if key present
    try:
        from core.travel.getyourguide_search import search_activities
        sources["getyourguide"] = lambda: search_activities(f"{port} shore excursion", date=date)
    except Exception:
        pass

    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fn): name for name, fn in sources.items()}
        for future in as_completed(futures):
            try:
                results.extend(future.result() or [])
            except Exception as e:
                results.append({"source": futures[future], "error": str(e)})

    return sorted([r for r in results if "error" not in r],
                  key=lambda x: x.get("price_usd") or 999999)

if __name__ == "__main__":
    import sys
    port = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Copenhagen"
    hits = search_all(port)
    print(f"{len(hits)} excursions found in {port}")
    for h in hits[:10]:
        print(f"  [{h.get('source')}] {h.get('name', '?')} — ${h.get('price_usd', '?')}")
```

- [ ] **Step 6: Run aggregator smoke test**
```bash
python3 core/travel/excursion_aggregator.py Copenhagen
```

- [ ] **Step 7: Commit**
```bash
git add core/travel/project_expedition_search.py core/travel/getyourguide_search.py \
        core/travel/shore_excursions_search.py core/travel/eatwith_search.py \
        core/travel/excursion_aggregator.py tests/
git commit -m "feat(travel): excursion sector — 4-source aggregator (PE + GYG + SEG + EatWith)"
```

---

### ~~Task 3: Activate Mozio (ground transport quotes via API)~~ [DECISION CHANGE 2026-06-22]

**Commander directive 2026-06-22:** Staying with Travel Agent booking portal — NOT pursuing API integration. Account at mozio.com as Travel Agent (affiliated under "Cruises and Tours Unlimited" host). Credentials in `.env` as `MOZIO_TA_EMAIL` / `MOZIO_TA_PASSWORD`. Use portal manually for ground transport quotes; no programmatic adapter needed at this time.

~~Context: Mozio aggregates 700+ ground transport suppliers worldwide. Covers private cars, transfers, rail. D2M use: airport transfers, port-to-hotel, city transit quotes for client itineraries.~~

~~**Commander action required:** Register at mozio.com/en-us/partners/ — get API key.~~

- [ ] **Step 1: Once key received, drop into creds**

```
// creds/mozio\_credentials.json  
\{"api\_key": "\<KEY\>", "note": "Mozio ground transport aggregator"\}
```

- [ ] **Step 2: Write test**

```
\# tests/test\_mozio\_search.py  
def test\_airport\_transfer\_quote():  
    from core.travel.mozio\_search import get\_transfer\_quote  
    quote = get\_transfer\_quote(  
        start\_address="Copenhagen Airport",  
        end\_address="Copenhagen Cruise Terminal",  
        pickup\_datetime="2026-12-17T10:00:00",  
        passengers=6,  
    )  
    assert quote is not None  
    assert "results" in quote or "data" in quote
```

- [ ] **Step 3: Build `core/travel/mozio\_search.py`**

```
\#!/usr/bin/env python3  
"""mozio\_search.py — Ground transport quotes via Mozio API."""  
import json, os  
import requests  
from pathlib import Path  
  
ROOT = Path(\_\_file\_\_).parents\[2\]  
CREDS = ROOT / "creds/mozio\_credentials.json"  
BASE = "https://api.mozio.com/v2"  
  
def \_key():  
    k = os.environ.get("MOZIO\_API\_KEY", "")  
    if not k and CREDS.exists():  
        k = json.loads(CREDS.read\_text()).get("api\_key", "")  
    if not k:  
        raise RuntimeError("MOZIO\_API\_KEY not set")  
    return k  
  
def get\_transfer\_quote(start\_address: str, end\_address: str,  
                       pickup\_datetime: str, passengers: int = 2) -\> dict:  
    """Search for ground transfer options."""  
    r = requests.post(f"\{BASE\}/search/", headers=\{"API-KEY": \_key()\}, json=\{  
        "start\_address": start\_address,  
        "end\_address": end\_address,  
        "mode": "one\_way",  
        "pickup\_datetime": pickup\_datetime,  
        "num\_passengers": passengers,  
        "currency": "USD",  
    \}, timeout=30)  
    r.raise\_for\_status()  
    return r.json()
```

- [ ] **Step 4: Run tests and commit**

```
python3 -m pytest tests/test\_mozio\_search.py -v  
git add core/travel/mozio\_search.py tests/test\_mozio\_search.py creds/mozio\_credentials.json  
git commit -m "feat(travel): Mozio ground transport adapter activated"
```


### Task 4: Activate Duffel NDC (airline group booking)

**Files:**

- Existing: `core/ai\_infra/thunderbird\_duffel.py` (built this session)

- Modify: `.env` → add `DUFFEL\_API\_KEY`

Context: Duffel NDC aggregator covers 200+ airlines via direct NDC connections. Per-booking fee in production (Commander financial gate for first live booking). Sandbox is free. Adapter built this session.

**Commander action required:** Register at duffel.com → get test API key (no credit card for sandbox).

- [ ] **Step 1: Add sandbox key to .env**

```
echo "DUFFEL\_API\_KEY=duffel\_test\_\<KEY\>" \>\> /home/john/Thunderbird/.env
```

- [ ] **Step 2: Smoke test adapter**

```
python3 -c "  
from core.ai\_infra.thunderbird\_duffel import search\_offers  
results = search\_offers('DEN', 'FCO', '2026-12-17', passengers=2)  
print(f'\{len(results)\} offers')  
"
```

- [ ] **Step 3: Update api\_registry.json status → active, commit**

```
git add .env config/api\_registry.json  
git commit -m "feat(travel): Duffel NDC sandbox activated — airline NDC search live"
```


## Phase 2 — Build the Missing Three Sectors

### Task 5: Cruise Feedback Scraper (Cruise Critic + Reddit)

**Files:**

- Create: `core/travel/cruise\_feedback.py`

- Create: `tests/test\_cruise\_feedback.py`

Context: Cruise Critic is the authoritative source for ship reviews and passenger sentiment. Reddit r/Cruise has real-time voyage feedback. Both are public but JS-rendered or need API. Firecrawl handles Cruise Critic (already active, 500 credits/mo). Reddit PRAW API is free.

**Two sources:**

1. **Cruise Critic** — via Firecrawl (`https://www.cruisecritic.com/reviews/`)

2. **Reddit r/Cruise** — via Reddit API (PRAW, free, no key needed for read-only)

- [ ] **Step 1: Write failing tests**

```
\# tests/test\_cruise\_feedback.py  
from unittest.mock import patch  
  
def test\_reddit\_sentiment\_returns\_posts():  
    from core.travel.cruise\_feedback import reddit\_sentiment  
    with patch("core.travel.cruise\_feedback.\_reddit\_search") as m:  
        m.return\_value = \[  
            \{"title": "Just off Silver Muse — amazing!", "score": 45, "url": "..."\},  
        \]  
        results = reddit\_sentiment("Silver Muse")  
    assert len(results) \>= 1  
    assert "title" in results\[0\]  
  
def test\_cruise\_critic\_reviews\_structure():  
    from core.travel.cruise\_feedback import cruise\_critic\_reviews  
    with patch("core.travel.cruise\_feedback.\_firecrawl\_scrape") as m:  
        m.return\_value = \{"markdown": "Silver Muse review: \*\*Excellent\*\*"\}  
        results = cruise\_critic\_reviews("Silver Muse")  
    assert results is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```
python3 -m pytest tests/test\_cruise\_feedback.py -v
```

Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Build `core/travel/cruise\_feedback.py`**

```
\#!/usr/bin/env python3  
"""  
cruise\_feedback.py — Voyage sentiment from Cruise Critic + Reddit.  
  
Two sources (both free, no auth required for read-only):  
  cruise\_critic\_reviews(ship\_name) → Firecrawl scrape of CC review pages  
  reddit\_sentiment(ship\_name, subreddit="CruiseTravel") → PRAW search  
  
Usage:  
    from core.travel.cruise\_feedback import cruise\_critic\_reviews, reddit\_sentiment  
    reviews = cruise\_critic\_reviews("Silver Muse")  
    sentiment = reddit\_sentiment("Silver Muse")  
"""  
import os, json  
import requests  
from pathlib import Path  
  
ROOT = Path(\_\_file\_\_).parents\[2\]  
FIRECRAWL\_BASE = "https://api.firecrawl.dev/v1"  
  
def \_get\_firecrawl\_key() -\> str:  
    k = os.environ.get("FIRECRAWL\_API\_KEY", "")  
    if not k:  
        for line in (ROOT / ".env").read\_text().splitlines():  
            if line.startswith("FIRECRAWL\_API\_KEY=") and not line.startswith("\#"):  
                k = line.split("=", 1)\[1\].strip().strip('"').strip("'")  
    if not k:  
        raise RuntimeError("FIRECRAWL\_API\_KEY not set in .env")  
    return k  
  
def \_firecrawl\_scrape(url: str) -\> dict:  
    r = requests.post(f"\{FIRECRAWL\_BASE\}/scrape",  
        headers=\{"Authorization": f"Bearer \{\_get\_firecrawl\_key()\}",  
                 "Content-Type": "application/json"\},  
        json=\{"url": url, "formats": \["markdown"\]\},  
        timeout=30)  
    r.raise\_for\_status()  
    return r.json().get("data", \{\})  
  
def cruise\_critic\_reviews(ship\_name: str, max\_pages: int = 3) -\> list\[dict\]:  
    """Scrape Cruise Critic for ship reviews via Firecrawl."""  
    slug = ship\_name.lower().replace(" ", "-")  
    url = f"https://www.cruisecritic.com/reviews/ship.cfm?shipid=\{slug\}"  
    results = \[\]  
    try:  
        data = \_firecrawl\_scrape(url)  
        results.append(\{  
            "source": "cruise\_critic",  
            "ship": ship\_name,  
            "url": url,  
            "content": data.get("markdown", ""),  
            "metadata": data.get("metadata", \{\}),  
        \})  
    except Exception as e:  
        results.append(\{"source": "cruise\_critic", "ship": ship\_name,  
                        "error": str(e)\})  
    return results  
  
def \_reddit\_search(query: str, subreddit: str = "CruiseTravel",  
                   limit: int = 25) -\> list\[dict\]:  
    """Search Reddit without auth using pushshift-compatible endpoint."""  
    headers = \{"User-Agent": "Thunderbird-D2M/1.0 travel-research"\}  
    r = requests.get(  
        f"https://www.reddit.com/r/\{subreddit\}/search.json",  
        params=\{"q": query, "sort": "relevance", "limit": limit, "t": "year"\},  
        headers=headers, timeout=20)  
    r.raise\_for\_status()  
    posts = r.json().get("data", \{\}).get("children", \[\])  
    return \[\{"title": p\["data"\]\["title"\], "score": p\["data"\]\["score"\],  
             "url": f"https://reddit.com\{p\['data'\]\['permalink'\]\}",  
             "selftext": p\["data"\].get("selftext", "")\[:500\]\}  
            for p in posts\]  
  
def reddit\_sentiment(ship\_name: str,  
                     subreddits: list\[str\] = None) -\> list\[dict\]:  
    """Pull recent Reddit posts about a ship from travel subreddits."""  
    if subreddits is None:  
        subreddits = \["CruiseTravel", "Cruise", "travel"\]  
    results = \[\]  
    for sub in subreddits:  
        try:  
            posts = \_reddit\_search(ship\_name, subreddit=sub)  
            results.extend(posts)  
        except Exception as e:  
            results.append(\{"subreddit": sub, "error": str(e)\})  
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)  
  
def feedback\_brief(ship\_name: str) -\> str:  
    """One-call summary: CC reviews + Reddit sentiment for a ship."""  
    cc = cruise\_critic\_reviews(ship\_name)  
    reddit = reddit\_sentiment(ship\_name)  
    cc\_summary = cc\[0\].get("content", "")\[:800\] if cc else "No CC data"  
    reddit\_top = reddit\[:5\] if reddit else \[\]  
    top\_str = "\\n".join(f"  \[\{r.get('score',0)\}\] \{r.get('title','')\}" for r in reddit\_top)  
    return (f"=== CRUISE FEEDBACK: \{ship\_name\} ===\\n"  
            f"Cruise Critic (excerpt):\\n\{cc\_summary\}\\n\\n"  
            f"Reddit top posts:\\n\{top\_str\}")  
  
if \_\_name\_\_ == "\_\_main\_\_":  
    import sys  
    ship = " ".join(sys.argv\[1:\]) if len(sys.argv) \> 1 else "Silver Muse"  
    print(feedback\_brief(ship))
```

- [ ] **Step 4: Run tests**

```
python3 -m pytest tests/test\_cruise\_feedback.py -v
```

Expected: 2/2 PASS.

- [ ] **Step 5: Live smoke test**

```
python3 core/travel/cruise\_feedback.py "Silver Muse"  
python3 core/travel/cruise\_feedback.py "Viking Mars"
```

- [ ] **Step 6: Commit**

```
git add core/travel/cruise\_feedback.py tests/test\_cruise\_feedback.py  
git commit -m "feat(travel): cruise feedback adapter — Cruise Critic + Reddit sentiment"
```


### Task 6: Industry News Aggregator (RSS + Firecrawl)

**Files:**

- Create: `core/travel/industry\_news.py`

- Create: `tests/test\_industry\_news.py`

Context: 5 key free RSS feeds cover 90% of cruise industry news. No auth, no API keys. Firecrawl handles paywalled stories (Travel Weekly, Seatrade) when RSS teaser links behind paywall.

**Feeds:**

- `https://www.cruiseindustrynews.com/feed/` — ship deployments, fleet news

- `https://www.seatrade-cruise.com/rss.xml` — industry, port, deployment

- `https://www.travelweekly.com/RSS/CruiseFeed` — trade news

- `https://www.travelpulse.com/rss/cruises` — agent-focused

- `https://www.cruisehive.com/feed` — consumer-facing, ship reviews

- [ ] 

- **Step 1: Write failing test**

```
\# tests/test\_industry\_news.py  
from unittest.mock import patch  
  
def test\_fetch\_feeds\_returns\_items():  
    from core.travel.industry\_news import fetch\_all\_feeds  
    with patch("core.travel.industry\_news.\_fetch\_feed") as m:  
        m.return\_value = \[\{"title": "Viking Adds 2027 Route", "link": "...",  
                           "published": "Mon, 22 Jun 2026 10:00:00 +0000",  
                           "source": "cruiseindustrynews"\}\]  
        items = fetch\_all\_feeds(max\_per\_feed=5)  
    assert len(items) \>= 1  
    assert "title" in items\[0\]  
  
def test\_dedup\_removes\_duplicates():  
    from core.travel.industry\_news import dedup\_by\_title  
    items = \[\{"title": "Same Story", "link": "a"\}, \{"title": "Same Story", "link": "b"\}\]  
    result = dedup\_by\_title(items)  
    assert len(result) == 1
```

- [ ] **Step 2: Run failing tests**

```
python3 -m pytest tests/test\_industry\_news.py -v
```

- [ ] **Step 3: Build `core/travel/industry\_news.py`**

```
\#!/usr/bin/env python3  
"""  
industry\_news.py — Travel industry news aggregator via RSS + Firecrawl.  
  
No API keys required for RSS feeds. Firecrawl used for paywalled full-text.  
  
Usage:  
    from core.travel.industry\_news import daily\_brief, fetch\_all\_feeds  
    brief = daily\_brief(keywords=\["Viking", "Silversea", "Regent"\])  
"""  
import hashlib  
from datetime import datetime, timezone  
from pathlib import Path  
  
try:  
    import feedparser  
except ImportError:  
    feedparser = None  
  
import requests  
  
FEEDS = \{  
    "cruiseindustrynews": "https://www.cruiseindustrynews.com/feed/",  
    "seatrade":           "https://www.seatrade-cruise.com/rss.xml",  
    "travelweekly":       "https://www.travelweekly.com/RSS/CruiseFeed",  
    "travelpulse":        "https://www.travelpulse.com/rss/cruises",  
    "cruisehive":         "https://www.cruisehive.com/feed",  
\}  
  
HEADERS = \{"User-Agent": "Thunderbird-D2M/1.0 travel-intel"\}  
  
  
def \_fetch\_feed(name: str, url: str, max\_items: int = 10) -\> list\[dict\]:  
    """Fetch and parse an RSS feed. Falls back to requests if feedparser absent."""  
    items = \[\]  
    try:  
        if feedparser:  
            parsed = feedparser.parse(url)  
            for entry in parsed.entries\[:max\_items\]:  
                items.append(\{  
                    "title": getattr(entry, "title", ""),  
                    "link": getattr(entry, "link", ""),  
                    "published": getattr(entry, "published", ""),  
                    "summary": getattr(entry, "summary", "")\[:300\],  
                    "source": name,  
                \})  
        else:  
            r = requests.get(url, headers=HEADERS, timeout=15)  
            r.raise\_for\_status()  
            \# Minimal XML parse for title+link  
            import xml.etree.ElementTree as ET  
            root = ET.fromstring(r.text)  
            ns = \{"atom": "http://www.w3.org/2005/Atom"\}  
            for item in (root.findall(".//item") or  
                         root.findall(".//atom:entry", ns))\[:max\_items\]:  
                title = (item.findtext("title") or  
                         item.findtext("atom:title", namespaces=ns) or "")  
                link = (item.findtext("link") or  
                        item.findtext("atom:link", namespaces=ns) or "")  
                items.append(\{"title": title.strip(), "link": link.strip(),  
                               "published": "", "summary": "", "source": name\})  
    except Exception as e:  
        items.append(\{"title": f"\[FEED ERROR: \{name\}\]", "link": url,  
                      "published": "", "summary": str(e), "source": name\})  
    return items  
  
  
def fetch\_all\_feeds(max\_per\_feed: int = 10) -\> list\[dict\]:  
    """Fetch all configured feeds and return merged list."""  
    all\_items = \[\]  
    for name, url in FEEDS.items():  
        all\_items.extend(\_fetch\_feed(name, url, max\_per\_feed))  
    return all\_items  
  
  
def dedup\_by\_title(items: list\[dict\]) -\> list\[dict\]:  
    """Remove near-duplicate titles (first occurrence wins)."""  
    seen = set()  
    result = \[\]  
    for item in items:  
        key = hashlib.md5(item.get("title", "").lower().strip().encode()).hexdigest()  
        if key not in seen:  
            seen.add(key)  
            result.append(item)  
    return result  
  
  
def filter\_by\_keywords(items: list\[dict\], keywords: list\[str\]) -\> list\[dict\]:  
    """Filter to items where title or summary contains any keyword (case-insensitive)."""  
    kw\_lower = \[k.lower() for k in keywords\]  
    return \[i for i in items  
            if any(k in (i.get("title", "") + i.get("summary", "")).lower()  
                   for k in kw\_lower)\]  
  
  
def daily\_brief(keywords: list\[str\] = None, max\_per\_feed: int = 8) -\> str:  
    """Fetch, dedup, filter, and format a daily industry news brief."""  
    items = dedup\_by\_title(fetch\_all\_feeds(max\_per\_feed))  
    if keywords:  
        filtered = filter\_by\_keywords(items, keywords)  
        if not filtered:  
            filtered = items\[:10\]  \# fallback: show top 10 if no keyword match  
    else:  
        filtered = items\[:15\]  
  
    lines = \[f"=== TRAVEL INDUSTRY BRIEF — \{datetime.now(timezone.utc).strftime('%Y-%m-%d')\} ==="\]  
    for item in filtered\[:20\]:  
        src = item.get("source", "?")  
        lines.append(f"\[\{src\}\] \{item.get('title', '')\} — \{item.get('link', '')\}")  
    return "\\n".join(lines)  
  
  
if \_\_name\_\_ == "\_\_main\_\_":  
    import sys  
    kw = sys.argv\[1:\] if len(sys.argv) \> 1 else \["Silversea", "Regent", "Viking", "luxury"\]  
    print(daily\_brief(keywords=kw))
```

- [ ] **Step 4: Install feedparser if not present**

```
pip install feedparser --quiet
```

- [ ] **Step 5: Run tests**

```
python3 -m pytest tests/test\_industry\_news.py -v
```

- [ ] **Step 6: Live smoke test**

```
python3 core/travel/industry\_news.py Silversea Regent Viking luxury
```

Expected: 15-20 news items from 5 feeds.

- [ ] **Step 7: Commit**

```
git add core/travel/industry\_news.py tests/test\_industry\_news.py  
git commit -m "feat(travel): industry news aggregator — 5 RSS feeds, keyword filter, dedup"
```


### Task 7: Hotel Sector — RateHawk B2B Adapter

**Files:**

- Create: `creds/ratehawk\_credentials.json`

- Create: `core/travel/ratehawk\_search.py`

- Create: `tests/test\_ratehawk\_search.py`

Context: RateHawk (part of Emerging Travel Group) is a B2B hotel aggregator for travel agents. Free to join, no credit card needed for search-only access. Covers 2M+ properties worldwide. API access available to registered agents. D2M use: hotel quotes for pre/post cruise stays and Door County trip (Sep 2026 MISSION-203).

**Registration:** ratehawk.com → "For Partners" → Travel Agent signup. API key issued on approval.

**Commander action required:** Register at ratehawk.com as a travel agent partner.

- [ ] **Step 1: Write failing tests**

```
\# tests/test\_ratehawk\_search.py  
from unittest.mock import patch  
  
def test\_hotel\_search\_returns\_properties():  
    from core.travel.ratehawk\_search import search\_hotels  
    with patch("core.travel.ratehawk\_search.\_api\_call") as m:  
        m.return\_value = \{"data": \{"hotels": \[  
            \{"id": "h1", "name": "The Grand", "rates": \[\{"price": 250\}\]\}  
        \]\}\}  
        results = search\_hotels("Copenhagen", "2026-12-16", "2026-12-17", guests=6)  
    assert len(results) \>= 1  
    assert "name" in results\[0\]  
  
def test\_missing\_key\_raises():  
    from core.travel.ratehawk\_search import \_get\_key  
    import pytest  
    with patch.dict("os.environ", \{\}, clear=True):  
        with pytest.raises(RuntimeError, match="RATEHAWK"):  
            \_get\_key()
```

- [ ] **Step 2: Build `core/travel/ratehawk\_search.py`**

```
\#!/usr/bin/env python3  
"""  
ratehawk\_search.py — B2B hotel search via RateHawk API (Emerging Travel Group).  
  
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
  
ROOT = Path(\_\_file\_\_).parents\[2\]  
CREDS = ROOT / "creds/ratehawk\_credentials.json"  
BASE = "https://api.worldota.net/api/b2b/v3"  
  
  
def \_get\_key() -\> tuple\[str, str\]:  
    """Returns (key\_id, api\_key) tuple."""  
    key\_id = os.environ.get("RATEHAWK\_KEY\_ID", "")  
    api\_key = os.environ.get("RATEHAWK\_API\_KEY", "")  
    if not key\_id and CREDS.exists():  
        data = json.loads(CREDS.read\_text())  
        key\_id = data.get("key\_id", "")  
        api\_key = data.get("api\_key", "")  
    if not key\_id or not api\_key:  
        raise RuntimeError(  
            "RATEHAWK\_KEY\_ID/RATEHAWK\_API\_KEY not set.\\n"  
            "Register at ratehawk.com → For Partners → Travel Agent."  
        )  
    return key\_id, api\_key  
  
  
def \_api\_call(endpoint: str, payload: dict) -\> dict:  
    key\_id, api\_key = \_get\_key()  
    r = requests.post(f"\{BASE\}/\{endpoint\}/",  
        auth=(key\_id, api\_key),  
        json=payload, timeout=30)  
    r.raise\_for\_status()  
    return r.json()  
  
  
def search\_hotels(destination: str, checkin: str, checkout: str,  
                  guests: int = 2, rooms: int = 1) -\> list\[dict\]:  
    """Search for hotels. Returns list of property dicts."""  
    data = \_api\_call("search/serp/region/", \{  
        "checkin": checkin,  
        "checkout": checkout,  
        "guests": \[\{"adults": guests\}\],  
        "region\_id": destination,  
        "currency": "USD",  
    \})  
    hotels = data.get("data", \{\}).get("hotels", \[\])  
    return \[\{  
        "id": h.get("id"),  
        "name": h.get("name"),  
        "stars": h.get("star\_rating"),  
        "price\_usd": h.get("rates", \[\{\}\])\[0\].get("price") if h.get("rates") else None,  
        "address": h.get("address"),  
    \} for h in hotels\]  
  
  
if \_\_name\_\_ == "\_\_main\_\_":  
    import sys  
    dest = sys.argv\[1\] if len(sys.argv) \> 1 else "Copenhagen"  
    checkin = sys.argv\[2\] if len(sys.argv) \> 2 else "2026-12-16"  
    checkout = sys.argv\[3\] if len(sys.argv) \> 3 else "2026-12-17"  
    results = search\_hotels(dest, checkin, checkout)  
    for h in results\[:5\]:  
        print(f"\{h\['name'\]\} (\{h\['stars'\]\}★) — $\{h\['price\_usd'\]\}/night")
```

- [ ] **Step 3: Create stub credentials file**

```
echo '\{"key\_id": "", "api\_key": "", "note": "Register at ratehawk.com/partners"\}' \\  
  \> /home/john/Thunderbird/creds/ratehawk\_credentials.json
```

- [ ] **Step 4: Run tests**

```
python3 -m pytest tests/test\_ratehawk\_search.py -v
```

Expected: 2/2 PASS (mocked).

- [ ] 

- **Step 5: Add to api\_registry.json** Add entry for RateHawk with `status: "pending\_key"`.

- [ ] 

- **Step 6: Commit**

```
git add core/travel/ratehawk\_search.py tests/test\_ratehawk\_search.py creds/ratehawk\_credentials.json config/api\_registry.json  
git commit -m "feat(travel): RateHawk hotel search adapter — B2B hotel sector unlocked (pending key)"
```


## Phase 3 — Session Capture Framework

### Task 8: HAR Capture Utility (portal data without APIs)

**Files:**

- Create: `core/travel/har\_capture.py`

- Create: `docs/HAR\_CAPTURE\_PLAYBOOK.md`

Context: Several cruise line portals (Princess, Celebrity, MSC, Norwegian) have no partner API. The Wing already uses session cookies for Regent and Centrav. A systematic HAR capture framework lets Dembe intercept B2B portal API calls and replay them authenticated. This is the legal-door approach ELON referenced — HAR files expose the API the portal calls internally.

Pattern: Log into portal via yoga Firefox with network capture → save HAR → extract authenticated API endpoints → replay with Python requests.

- [ ] **Step 1: Write tests**

```
\# tests/test\_har\_capture.py  
def test\_parse\_har\_extracts\_api\_calls():  
    from core.travel.har\_capture import extract\_api\_calls  
    har = \{"log": \{"entries": \[  
        \{"request": \{"url": "https://portal.example.com/api/availability",  
                     "method": "GET",  
                     "headers": \[\{"name": "Authorization", "value": "Bearer tok123"\}\]\},  
         "response": \{"status": 200, "content": \{"mimeType": "application/json",  
                                                   "text": '\{"available": true\}'\}\}\}  
    \]\}\}  
    calls = extract\_api\_calls(har, domain\_filter="portal.example.com")  
    assert len(calls) == 1  
    assert calls\[0\]\["url"\] == "https://portal.example.com/api/availability"  
    assert calls\[0\]\["auth\_header"\] == "Bearer tok123"
```

- [ ] **Step 2: Build `core/travel/har\_capture.py`**

```
\#!/usr/bin/env python3  
"""  
har\_capture.py — Extract and replay authenticated API calls from HAR files.  
  
Use case: Cruise line B2B portals without partner APIs.  
  1. Log into portal in Firefox with DevTools → Network → Export HAR  
  2. Pass HAR to extract\_api\_calls() to find authenticated endpoints  
  3. Replay with replay\_call() to pull live data  
  
Usage:  
    from core.travel.har\_capture import extract\_api\_calls, replay\_call  
    calls = extract\_api\_calls(har\_data, domain\_filter="book.princess.com")  
    result = replay\_call(calls\[0\])  
"""  
import json  
import requests  
from pathlib import Path  
  
  
def load\_har(path: str | Path) -\> dict:  
    return json.loads(Path(path).read\_text())  
  
  
def extract\_api\_calls(har: dict, domain\_filter: str = "",  
                      method\_filter: str = "") -\> list\[dict\]:  
    """Extract API calls from a HAR file. Optionally filter by domain or method."""  
    results = \[\]  
    for entry in har.get("log", \{\}).get("entries", \[\]):  
        req = entry.get("request", \{\})  
        resp = entry.get("response", \{\})  
        url = req.get("url", "")  
        method = req.get("method", "GET")  
  
        if domain\_filter and domain\_filter not in url:  
            continue  
        if method\_filter and method.upper() != method\_filter.upper():  
            continue  
        \# Only API calls (JSON responses)  
        mime = resp.get("content", \{\}).get("mimeType", "")  
        if "json" not in mime and "xml" not in mime:  
            continue  
  
        headers = \{h\["name"\]: h\["value"\] for h in req.get("headers", \[\])\}  
        auth\_header = headers.get("Authorization") or headers.get("Cookie", "")  
  
        results.append(\{  
            "url": url,  
            "method": method,  
            "headers": headers,  
            "auth\_header": auth\_header,  
            "body": req.get("postData", \{\}).get("text", ""),  
            "response\_status": resp.get("status"),  
            "response\_preview": resp.get("content", \{\}).get("text", "")\[:200\],  
        \})  
    return results  
  
  
def replay\_call(call: dict, override\_headers: dict = None) -\> requests.Response:  
    """Replay a captured API call with optional header overrides."""  
    headers = dict(call.get("headers", \{\}))  
    if override\_headers:  
        headers.update(override\_headers)  
    method = call.get("method", "GET").upper()  
    url = call\["url"\]  
    body = call.get("body", "")  
  
    r = requests.request(method, url, headers=headers,  
                         data=body.encode() if body else None, timeout=30)  
    return r  
  
  
def har\_to\_playbook(har\_path: str, domain: str, output\_path: str = None) -\> str:  
    """Extract all API calls from a HAR and write a playbook markdown."""  
    har = load\_har(har\_path)  
    calls = extract\_api\_calls(har, domain\_filter=domain)  
    lines = \[f"\# HAR Playbook — \{domain\}", f"Extracted \{len(calls)\} API endpoints\\n"\]  
    for i, c in enumerate(calls, 1):  
        lines.append(f"\#\# Call \{i\}: \{c\['method'\]\} \{c\['url'\]\}")  
        lines.append(f"- Auth: \`\{c\['auth\_header'\]\[:60\]\}...\`" if len(c\['auth\_header'\]) \> 60  
                     else f"- Auth: \`\{c\['auth\_header'\]\}\`")  
        lines.append(f"- Response: HTTP \{c\['response\_status'\]\}")  
        lines.append(f"- Preview: \`\{c\['response\_preview'\]\[:100\]\}\`\\n")  
    out = "\\n".join(lines)  
    if output\_path:  
        Path(output\_path).write\_text(out)  
    return out
```

- [ ] **Step 3: Run tests**

```
python3 -m pytest tests/test\_har\_capture.py -v
```

- [ ] **Step 4: Write `docs/HAR\_CAPTURE\_PLAYBOOK.md`** Document the step-by-step process for Dembe to capture HAR files from cruise line portals:

1. Open yoga Firefox with DevTools Network tab

2. Log into target portal

3. Perform the desired action (search availability, pull booking list)

4. Export HAR from DevTools

5. Run `python3 -c "from core.travel.har\_capture import har\_to\_playbook; print(har\_to\_playbook('capture.har', 'portal.cruiseline.com', 'docs/playbooks/cruiseline.md'))"`

6. Check `docs/playbooks/` for extracted endpoints

- [ ] **Step 5: Commit**

```
git add core/travel/har\_capture.py tests/test\_har\_capture.py docs/HAR\_CAPTURE\_PLAYBOOK.md  
git commit -m "feat(travel): HAR capture framework — authenticated portal API extraction"
```


## Completion Criteria (updated 2026-06-22)

The Walls of Jericho plan is complete when:

| Sector | Gate | Status |
| - | - | - |
| ~~Airlines (Amadeus)~~ | ~~eliminated~~ | ~~STRUCK~~ |
| Airlines (ITA Matrix) | `ita_matrix.py` returns fare URL + scraped min fare | ✅ BUILT |
| Airlines (Duffel NDC) | `thunderbird_duffel.py` returns sandbox offers | ⏳ pending key |
| ~~Excursions (Viator)~~ | ~~eliminated~~ | ~~STRUCK~~ |
| Excursions (4-source) | `excursion_aggregator.py` returns PE results; GYG/SEG fire on key | ✅ PE LIVE |
| Ground transport (Mozio) | TA portal account active — manual quotes via mozio.com | ✅ TA ACCOUNT LIVE |
| Cruise feedback | `cruise_feedback.py` returns CC + Reddit data for any ship | ✅ BUILT |
| Industry news | `industry_news.py` returns 10+ items from live RSS feeds | ✅ BUILT |
| Hotel (Room-Res B2B) | `roomres_search.py` returns live net rates for any city | ✅ BUILT |
| Portal capture | `har_capture.py` extracts and replays a real portal API call | ✅ BUILT |


**Commander-gated registrations still needed (all free):**

1. ~~Duffel~~ — ✅ test key wired 2026-06-22 (`DUFFEL_API_KEY` in `.env`)
2. GetYourGuide Partner — partner.getyourguide.com (excursion source 2)
3. Shore Excursions Group — shoreexcursionsgroup.com/travel-agents-signup (excursion source 3)
4. ~~Mozio Partner API~~ — ✅ staying with TA portal account (Commander directive 2026-06-22)

**ELON's metric:** Wing can pull live data from at least one new travel sector per week. No wall stays unexamined.


*Plan authored: 2026-06-22 · ELON Mandate 1 · Owner: ELON (A12) — discovery; Hale — execution routing* *Execution: superpowers:subagent-driven-development, task-by-task*

