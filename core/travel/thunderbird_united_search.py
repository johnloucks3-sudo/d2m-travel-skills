"""
Dreams2Memories United Airlines Flight Search Module
=====================================================

Direct-source United.com flight search via CloakBrowser (stealth Chromium,
`tools/cloak/cloak_fetch.mjs`) — NOT a RapidAPI/aggregator wrapper. Built
2026-07-09/10 after exhausting the API-first path (see research below).

WHY THIS PATH, NOT AN API WRAPPER:
1. RapidAPI has NO genuine United-specific or United-inclusive flight-search
   API. Live searches on rapidapi.com for "united flight" (1 result) and
   "united airlines" (3 results) returned only name-collisions (a British
   Airways API matched on "United Kingdom") and two junk employee-portal
   scrapers ("Flying Together UAL" — an internal UAL staff login page, not
   flight search). Confirmed via Playwright against the live marketplace,
   logged in as d2mtravel2026/d2mconcierge@gmail.com (same account as the
   Kiwi.com build). No subscribe screen to even evaluate — there is nothing
   to subscribe to.
2. United's own developer program (united.business/NDC) is a REAL, human-only
   gate for a shop D2M's size: "Custom API" (direct NDC connect) requires
   significant IT resources and a business relationship (contact
   UCDhelp@united.com); the GDS/aggregator route is the realistic option for
   a travel agency — and that is exactly what Amadeus (`search_flights` in
   `thunderbird_flight_search.py`) already gives us. Confirmed via WebSearch
   against united.business/NDC-travel-agencies and united.business/NDC-corporate.
3. GROUNDING CHECK (do this before ever building a 4th United source): run
   `search_flights(origin, destination, date)` (Amadeus, already wired into
   the MCP server) first. It already returns full United GDS inventory —
   confirmed live 2026-07-09, DEN->ORD 2026-08-15 returned 15 UA offers with
   real booking classes (G/K/S/V/W), seat counts, aircraft types, and fares
   from $119.44 net. This is AGENT-BOOKABLE GDS data (fare basis + booking
   class) that a united.com scrape can never produce — Amadeus should stay
   the default/primary United source. This module exists ONLY for a
   consumer-web cross-check (e.g. spot-checking a client-reported published
   fare, or a route Amadeus returns thin/no results for).

WHAT WORKS (verified live 2026-07-09/10, CloakBrowser stealth Chromium via
tools/cloak/cloak_fetch.mjs, no CAPTCHA hit):
- ONE-WAY deep-link searches (`fsr/choose-flights?f=...&t=...&d=...&tt=1...`)
  load real results reliably. Verified TWICE against DEN->ORD 2026-08-15:
  run 1 = 101 price mentions / 15 flight cards parsed, run 2 = 39 price
  mentions — both real live fares (e.g. UA1377 DEN->ORD $93 Economy),
  matching Amadeus's ballpark for the same route/date.

WHAT DOES NOT WORK (verified live, same session, honest limitation):
- ROUND-TRIP deep links (`&r=<return_date>...`) hit exactly the silent
  "Loading results..." stall described in the original bot-check finding —
  reproduced 2x (60s and 90s timeout budgets, both stall). A "Sign in for
  the best experience" modal appears in the DOM at the same time, suggesting
  the round-trip results fetch may be gated behind an interaction/soft
  nudge the deep-link approach never satisfies. NOT investigated further
  (out of scope for this session) — round-trip on united.com is UNSOLVED.
  Workaround: call this module twice (outbound one-way + return one-way)
  and combine client-side, OR use Amadeus's `search_flights` with
  `return_date` set (Amadeus round-trip search already works).
- No internal fare-search JSON/XHR endpoint was found via network capture
  (`tools/cloak/united_network_probe.mjs`, 58 requests captured over a 15s
  window on a successful one-way load) — only auth/telemetry/airport-lookup
  calls. This means the fare data is very likely server-side-rendered
  into the initial HTML (Next.js/React SSR), not fetched via a separate
  client XHR — so a network-capture shortcut isn't available; the DOM/text
  scrape (what this module does) IS the robust path here, not a workaround.

PARSER: united.com's rendered text has a consistent per-flight-card
structure for NONSTOP itineraries (time / origin / duration / destination /
"UA #### (aircraft)" / fare tiers). This module regex-parses that reliably
(verified: 13-15 real nonstop cards parsed cleanly per run, zero garbage).
Itineraries with 1+ stops use a different card shape (connection leg info,
often no single flight-number line) and are NOT reliably parsed — they are
preserved in `raw_text` for manual reading but omitted from the structured
`offers` list. This is a known, documented gap, not a silent failure.

USAGE DISCIPLINE (same standard as Kiwi, Commander directive 2026-07-09):
call this synchronously/on-demand only — e.g. a one-off cross-check during
a client conversation. NEVER wire into a background sweep, headless probe,
or automated loop. This is a browser-automation scrape of united.com, not
a stable API — it is inherently more brittle than Amadeus/Centrav/Kiwi and
should be treated as a fallback verification tool, not a primary source.

Dependencies: `tools/cloak/cloak_fetch.mjs` (Node, CloakBrowser) must be
reachable; this module shells out to it via subprocess. Node + the
tools/cloak/node_modules install must already exist (they do, as of the
Kiwi/Regent/Silversea CloakBrowser builds this session).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

_ROOT = Path(__file__).resolve().parents[2]  # Thunderbird/
_CLOAK_DIR = _ROOT / "tools" / "cloak"
_CLOAK_FETCH = _CLOAK_DIR / "cloak_fetch.mjs"

_BASE_URL = "https://www.united.com/en/us/fsr/choose-flights"

# Per-flight-card regex for NONSTOP itineraries. See module docstring for
# why connecting (1+ stop) itineraries are not parsed by this pattern.
_CARD_SPLIT = re.compile(r"\n(NONSTOP|\d+ STOPS?)\n")
_DEP_TIME = re.compile(r"(\d{1,2}:\d{2} [AP]M)\nDeparting at")
_ARR_TIME = re.compile(r"(\d{1,2}:\d{2} [AP]M)\nArriving at")
_ORIGIN = re.compile(r"([A-Z]{3})\nOrigin [^\n(]+\(([A-Z]{3})\)")
_DEST = re.compile(r"([A-Z]{3})\nDestination [^\n(]+\(([A-Z]{3})\)")
_FLIGHT = re.compile(r"UA ?(\d+) \(([^)]+)\)")
_FARE = re.compile(r"From\n\$(\d+)\n([A-Za-z0-9 ®+]+?)\ncabin select")


def _run_cloak_fetch(url: str, timeout_ms: int = 60000, proc_timeout_s: int = 90, retries: int = 2) -> str:
    """Shell out to tools/cloak/cloak_fetch.mjs and return page text.
    Retries on transient failure — verified live 2026-07-10 that CloakBrowser
    occasionally returns empty content on united.com (SPA client-side nav
    race) even when the URL/params are correct; a same-URL retry recovers.
    Raises RuntimeError with the LAST attempt's stderr if all retries fail."""
    if not _CLOAK_FETCH.exists():
        raise RuntimeError(f"cloak_fetch.mjs not found at {_CLOAK_FETCH}")
    last_err = None
    for attempt in range(retries + 1):
        proc = subprocess.run(
            ["node", str(_CLOAK_FETCH), url, "--output", "text", "--timeout", str(timeout_ms)],
            cwd=str(_CLOAK_DIR),
            capture_output=True,
            text=True,
            timeout=proc_timeout_s,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        last_err = f"cloak_fetch.mjs failed (exit {proc.returncode}): {proc.stderr.strip()}"
    raise RuntimeError(last_err)


def _parse_nonstop_flights(text: str) -> list[dict]:
    """Parse NONSTOP flight cards out of united.com search-results page text.
    Connecting (1+ stop) itineraries are intentionally NOT parsed here — see
    module docstring "PARSER" section. Returns [] if nothing matched (e.g.
    round-trip stall, or page format changed — caller should fall back to
    raw_text)."""
    splits = _CARD_SPLIT.split(text)
    results = []
    for i in range(1, len(splits) - 1, 2):
        stops_label, body = splits[i], splits[i + 1]
        if stops_label != "NONSTOP":
            continue  # connecting itinerary — not reliably parsed, skip
        dep_m = _DEP_TIME.search(body)
        arr_m = _ARR_TIME.search(body)
        origin_m = _ORIGIN.search(body)
        dest_m = _DEST.search(body)
        flight_m = _FLIGHT.search(body)
        if not (dep_m and origin_m and dest_m):
            continue
        # NOTE: united.com's DOM text repeats the literal label "United Economy"
        # for BOTH the Economy and Economy Plus tiers (verified live 2026-07-10 —
        # the accessible fare-tier name is not distinguishable from page text
        # alone). Cabin names below are inferred by POSITION (1st=Economy,
        # 2nd=Economy Plus, 3rd=First) matching the fixed 3-tier tab order
        # shown elsewhere on the page, NOT re-derived from the per-price text.
        _POSITIONAL_CABINS = ["Economy", "Economy Plus", "First"]
        raw_fares = _FARE.findall(body)
        fares = [
            {"price_usd": int(p), "cabin": _POSITIONAL_CABINS[idx] if idx < 3 else c.strip()}
            for idx, (p, c) in enumerate(raw_fares)
        ]
        results.append({
            "stops": 0,
            "departure_time": dep_m.group(1),
            "arrival_time": arr_m.group(1) if arr_m else None,
            "origin": origin_m.group(2),
            "destination": dest_m.group(2),
            "flight_number": f"UA{flight_m.group(1)}" if flight_m else None,
            "aircraft": flight_m.group(2) if flight_m else None,
            "fares": fares,
            "cheapest_usd": min((f["price_usd"] for f in fares), default=None),
        })
    return results


def search_united_oneway(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
) -> dict:
    """One-way United.com search via CloakBrowser deep-link + text scrape.
    origin/destination: 3-letter IATA airport codes.
    departure_date: YYYY-MM-DD.
    Returns dict with 'offers' (parsed nonstop flights), 'raw_text' (full
    page text, for connecting itineraries or manual review), and 'note'.
    ROUND-TRIP IS NOT SUPPORTED — see module docstring. Call twice (outbound
    + return, both one-way) and combine, or use Amadeus search_flights with
    return_date instead."""
    url = (
        f"{_BASE_URL}?f={origin}&t={destination}&d={departure_date}"
        f"&tt=1&sc=7&px={adults}&taxng=1&idx=1"
    )
    text = _run_cloak_fetch(url)
    lower = text.lower()
    # Two distinct failure modes seen live 2026-07-10 — do NOT collapse them
    # into a bare "no offers" success (that would be exactly the false-success
    # the Wing's independent-verification doctrine forbids: a system saying
    # "done" when it errored, not when it genuinely found zero flights).
    if "loading results" in lower:
        return {
            "success": False,
            "status": "stalled",
            "offers": [],
            "raw_text": text,
            "note": "Silent-block: page stuck on 'Loading results...'. Known "
                    "issue reproduced for round-trip deep links; retry, or "
                    "fall back to Amadeus search_flights.",
        }
    if "unable to complete your request" in lower or ("sorry" in lower and "flight search results" in lower):
        return {
            "success": False,
            "status": "site_error",
            "offers": [],
            "raw_text": text,
            "note": "united.com returned an explicit error page ('unable to "
                    "complete your request') — not a silent stall, a real "
                    "request failure (seen live on malformed/round-trip "
                    "param combos). Do not treat as 'zero flights found'.",
        }
    offers = _parse_nonstop_flights(text)
    return {
        "success": True,
        "status": "ok" if offers else "ok_no_nonstop_parsed",
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "offers": offers,
        "nonstop_count": len(offers),
        "cheapest_usd": min((o["cheapest_usd"] for o in offers if o["cheapest_usd"]), default=None),
        "raw_text": text,
        "note": "Connecting (1+ stop) itineraries are present in raw_text but "
                "NOT parsed into offers — see module docstring PARSER section. "
                "'ok_no_nonstop_parsed' means the page loaded fine but no "
                "NONSTOP cards matched (route may be connections-only) — "
                "check raw_text before assuming zero availability.",
    }


def register_united_search_tools(mcp: FastMCP):
    """Register United.com flight search tools with the MCP server.

    NOT wired into core/mcp/travel_mcp_server.py by this build (per explicit
    instruction). To wire in, add to travel_mcp_server.py matching the
    existing thunderbird_kiwi_search.py pattern:

        try:
            from thunderbird_united_search import register_united_search_tools
        except ImportError:
            def register_united_search_tools(mcp): pass  # cloak_fetch.mjs unavailable

    ...and add `register_united_search_tools` to the `_TRAVEL_LOADERS` list
    (~line 610 of travel_mcp_server.py, same list Kiwi's loader is in).
    """

    @mcp.tool(
        name="search_united_flights",
        annotations={"title": "Search Flights (United.com direct, one-way only)", "readOnlyHint": True},
    )
    async def search_united_flights(
        origin: str = Field(..., description="Origin airport IATA code, e.g. 'DEN'"),
        destination: str = Field(..., description="Destination airport IATA code, e.g. 'ORD'"),
        departure_date: str = Field(..., description="Departure date YYYY-MM-DD"),
        adults: int = Field(1, description="Number of adult passengers"),
    ) -> str:
        """Direct united.com flight search via CloakBrowser stealth scrape —
        NOT an API. ONE-WAY ONLY (round-trip deep links silently stall on
        united.com, unresolved — see module docstring). Cross-check/fallback
        tool only: Amadeus (search_flights) already returns full United GDS
        inventory with booking classes and should stay the default United
        source. Use this only to spot-check a published consumer fare or a
        route Amadeus returns thin.

        USAGE DISCIPLINE: synchronous/on-demand only. Never call from a
        background sweep, headless probe, or automated loop — this is a
        browser-automation scrape of a live airline website, more brittle
        than an API and slower (~15-60s per call).

        Returns nonstop flight offers with flight numbers, times, and fares.
        Connecting itineraries are present in raw text but not structured.
        """
        try:
            result = search_united_oneway(origin, destination, departure_date, adults)
            # Trim raw_text for the MCP response — full text is verbose;
            # offers carry the structured data callers actually need.
            out = {k: v for k, v in result.items() if k != "raw_text"}
            out["raw_text_available"] = bool(result.get("raw_text"))
            return json.dumps(out, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Smoke test — mirrors the live verification run 2026-07-09/10.
    result = search_united_oneway("DEN", "ORD", "2026-08-15")
    print(f"success={result['success']} nonstop_count={result.get('nonstop_count')} "
          f"cheapest=${result.get('cheapest_usd')}")
    for o in result.get("offers", [])[:5]:
        print(f"  {o['flight_number']} {o['origin']}->{o['destination']} "
              f"{o['departure_time']}-{o['arrival_time']} from ${o['cheapest_usd']}")
