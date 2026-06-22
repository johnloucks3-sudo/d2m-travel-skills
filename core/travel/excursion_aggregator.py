#!/usr/bin/env python3
"""
excursion_aggregator.py — Multi-source shore excursion + activity search.

Sources (in priority order — all run in parallel):
  1. Project Expedition — cruise-focused, net pricing, no key required
  2. GetYourGuide       — global, 100k+ tours (key required → creds/getyourguide_credentials.json)
  3. Shore Excursions Group — cruise-specialist (key + agent_id → creds/shore_excursions_credentials.json)
  4. EatWith            — social dining/experiences (Playwright needed — TODO stub)

Common output schema per excursion:
  {source, name, location, duration_hours, price_per_person, currency,
   url, rating, review_count, accessible, cruise_friendly, private, includes_food, error}

Usage:
    from core.travel.excursion_aggregator import search
    results = search("Venice", date="2026-12-17", adults=2)
    results = search("Santorini", adults=4, min_rating=4.0)

CLI:
    python3 core/travel/excursion_aggregator.py "Venice" 2026-12-17 2
    python3 core/travel/excursion_aggregator.py "Santorini" --cruise-friendly
"""
import base64
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).parents[2]

# ─── Common schema ───────────────────────────────────────────────────────────

def _exc(source: str, name: str, price: float, url: str = "",
         location: str = "", duration_hours: float = None,
         rating: float = None, review_count: int = None,
         accessible: bool = None, cruise_friendly: bool = None,
         private: bool = False, includes_food: bool = False,
         currency: str = "USD", **extra) -> dict:
    return {
        "source": source,
        "name": name,
        "location": location,
        "duration_hours": duration_hours,
        "price_per_person": price,
        "currency": currency,
        "url": url,
        "rating": rating,
        "review_count": review_count,
        "accessible": accessible,
        "cruise_friendly": cruise_friendly,
        "private": private,
        "includes_food": includes_food,
        "error": None,
    }


def _err(source: str, msg: str) -> dict:
    return {"source": source, "name": None, "error": msg}


# ─── Source 1: Project Expedition ────────────────────────────────────────────

PE_BASE = "https://www.projectexpedition.com"
PE_RATE_LIMIT_S = 3  # Imperva blocks at ~6 req/IP; minimum 3s between calls
_pe_last_call = 0.0

# Known city → location_id (scraped from /location pages; Imperva-blocked re-scrape)
# Extend with _pe_get_location_id() for unknown cities
PE_KNOWN_IDS: dict[str, str] = {
    # Mediterranean — Italy
    "venice": "771",
    "veneto": "771",
    "rome": "734",
    "civitavecchia": "734",
    "lazio": "734",
    "florence": "717",
    "livorno": "717",
    "tuscany": "717",
    "naples": "732",
    "campania": "732",
    "sicily": "728",
    # Mediterranean — Greece
    "athens": "450",
    "piraeus": "450",
    "santorini": "1655",
    "paros": "1652",
    "mykonos": "1654",
    "crete": "1649",
    "corfu": "1648",
    "rhodes": "1653",
    # Mediterranean — Croatia / Montenegro
    "dubrovnik": "374",
    "split": "1543",
    "kotor": "820",
    "zadar": "378",
    # Mediterranean — Turkey / Spain / France / Morocco
    "istanbul": "60",
    "ephesus": "61",
    "kusadasi": "61",
    "barcelona": "934",
    "marseille": "831",
    "monaco": "838",
    "casablanca": "1190",
    # Mediterranean — smaller ports / islands
    "patmos": "1929",
    # Caribbean / Bermuda
    "bermuda": "1110",
    # Norway
    "bergen": "995",
    "flam": "992",
    "stavanger": "1001",
    # Skip list — redirect-loop slugs on PE (needs browser)
    "split_redirect": None,  # handled above via region ID
}


def _pe_get_location_id(city: str) -> str | None:
    """Scrape Project Expedition city page for location ID. May fail due to Imperva."""
    slug = city.lower().replace(" ", "-")
    url = f"{PE_BASE}/location/europe/{slug}/"  # most cruise ports are Europe; fallback below
    for base in [f"{PE_BASE}/location/europe/{slug}/",
                 f"{PE_BASE}/location/caribbean/{slug}/",
                 f"{PE_BASE}/location/{slug}/"]:
        try:
            r = requests.get(base, timeout=10,
                             headers={"User-Agent": "Mozilla/5.0 Chrome/131.0.0.0"})
            if r.status_code == 200:
                m = re.search(r"setup_location_page',\s*\{\s*l_sId:\s*'([0-9]+)'", r.text)
                if m:
                    return m.group(1)
        except Exception:
            pass
    return None


def _pe_parse_price(raw: str, private: bool, adults: int) -> float | None:
    """Extract per-person USD from PE productPrice string."""
    m = re.search(r"US\$\s*::\s*([0-9.]+)", raw or "")
    if not m:
        return None
    price = float(m.group(1))
    # If per-party, divide by pax
    if private and adults > 1 and "Per Person" not in raw:
        price = price / adults
    return price


def _pe_parse_duration(raw: str) -> float | None:
    m = re.search(r"::([0-9.]+)::", raw or "")
    return float(m.group(1)) if m else None


def _pe_parse_accessible(tag: str | None) -> bool | None:
    if not tag:
        return None
    t = tag.lower()
    if "wheelchair accessible" in t or "limited mobility" in t:
        return True
    if "not wheelchair" in t:
        return False
    return None


def search_project_expedition(city: str, adults: int = 2,
                               max_results: int = 20) -> list[dict]:
    global _pe_last_call

    # Rate-limit enforcement
    elapsed = time.time() - _pe_last_call
    if elapsed < PE_RATE_LIMIT_S:
        time.sleep(PE_RATE_LIMIT_S - elapsed)

    location_id = PE_KNOWN_IDS.get(city.lower())
    if location_id is None and city.lower() not in PE_KNOWN_IDS:
        location_id = _pe_get_location_id(city)
    if not location_id:
        return [_err("project_expedition", f"Location ID not found for '{city}' — add to PE_KNOWN_IDS or scrape")]

    args = {
        "function": "getLocationProducts",
        "param_1": location_id,
        "param_2": "true",
        "param_3": "region",
        "param_4": "3500",
        "search": "",
        "key": f"PAGE_LOCATION_PRODUCTS_2{location_id}_regionUSD",
        "order": "",
        "pe": {},
    }
    b64 = base64.b64encode(json.dumps(args).encode()).decode()
    body = f"p_sAction=get_all_products&p_sArgs={b64}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{PE_BASE}/",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0.0.0",
    }

    try:
        _pe_last_call = time.time()
        r = requests.post(f"{PE_BASE}/rq/", headers=headers, data=body, timeout=20)
        if r.status_code == 403:
            return [_err("project_expedition", "Imperva rate-limit (403) — wait and retry")]
    except Exception as e:
        return [_err("project_expedition", str(e))]

    m = re.search(r"cleanTours\((\[.*?\])\)", r.text, re.DOTALL)
    if not m:
        return [_err("project_expedition", "No tour data in response — unexpected format")]
    try:
        raw_tours = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return [_err("project_expedition", f"JSON parse error: {e}")]

    results = []
    for t in raw_tours[:max_results]:
        private = bool(t.get("private_tour"))
        price = _pe_parse_price(t.get("productPrice", ""), private, adults)
        cruise_friendly = (
            "Cruise Friendly" in (t.get("shoreex_refund_policy") or "")
        )
        includes_food = bool(
            t.get("fb_included") or t.get("food_description") or t.get("beverage_description")
        )
        slug = t.get("productSlug", "")
        url = f"{PE_BASE}/tour/{slug}/" if slug else PE_BASE
        results.append(_exc(
            source="project_expedition",
            name=t.get("tourName", "?"),
            price=price or 0,
            url=url,
            location=city,
            duration_hours=_pe_parse_duration(t.get("duration", "")),
            rating=t.get("reviewAvgRating") or t.get("peRating"),
            review_count=t.get("reviewCount"),
            accessible=_pe_parse_accessible(t.get("accessible_tag")),
            cruise_friendly=cruise_friendly,
            private=private,
            includes_food=includes_food,
        ))
    return results


# ─── Source 2: GetYourGuide ──────────────────────────────────────────────────

def search_getyourguide(city: str, date: str = None,
                         adults: int = 2, max_results: int = 20) -> list[dict]:
    try:
        from core.travel.gyg_search import search_tours, location_lookup
        locs = location_lookup(city)
        if not locs:
            return [_err("getyourguide", f"Location '{city}' not found in GYG")]
        loc_id = locs[0].get("id") or locs[0].get("location_id")
        raw = search_tours(loc_id, start_date=date, adults=adults, limit=max_results)
        results = []
        for t in raw:
            results.append(_exc(
                source="getyourguide",
                name=t.get("title", "?"),
                price=t.get("price", {}).get("values", {}).get("amount", 0),
                currency=t.get("price", {}).get("currencyCode", "USD"),
                url=t.get("url", ""),
                location=city,
                duration_hours=(t.get("durationRange", {}) or {}).get("duration"),
                rating=t.get("ratingInfo", {}).get("combinedAverageRating"),
                review_count=t.get("ratingInfo", {}).get("totalCount"),
            ))
        return results
    except RuntimeError as e:
        return [_err("getyourguide", str(e))]
    except Exception as e:
        return [_err("getyourguide", f"Search failed: {e}")]


# ─── Source 3: Shore Excursions Group ────────────────────────────────────────

def search_shore_excursions_group(city: str, ship_date: str = None,
                                   adults: int = 2, max_results: int = 20) -> list[dict]:
    try:
        creds_path = ROOT / "creds" / "shore_excursions_credentials.json"
        if not creds_path.exists():
            return [_err("shore_excursions_group",
                         "Credentials not set — register at shoreexcursionsgroup.com/travel-agents-signup")]
        creds = json.loads(creds_path.read_text())
        api_key = creds.get("api_key", "")
        agent_id = creds.get("agent_id", "")
        if not api_key:
            return [_err("shore_excursions_group", "api_key missing from shore_excursions_credentials.json")]

        seg_base = creds.get("api_base", "https://www.shoreexcursionsgroup.com/api")
        r = requests.get(f"{seg_base}/tours",
                         params={"port": city, "date": ship_date or "",
                                 "agent_id": agent_id, "limit": max_results},
                         headers={"X-API-Key": api_key}, timeout=20)
        r.raise_for_status()
        tours = r.json().get("tours", r.json() if isinstance(r.json(), list) else [])
        results = []
        for t in tours:
            results.append(_exc(
                source="shore_excursions_group",
                name=t.get("name", "?"),
                price=t.get("price_per_person", 0),
                url=t.get("url", ""),
                location=city,
                duration_hours=t.get("duration_hours"),
                rating=t.get("rating"),
                review_count=t.get("review_count"),
                cruise_friendly=True,  # SEG is cruise-specialist, all tours are ship-safe
            ))
        return results
    except RuntimeError as e:
        return [_err("shore_excursions_group", str(e))]
    except Exception as e:
        return [_err("shore_excursions_group", f"Search failed: {e}")]


# ─── Source 4: EatWith ───────────────────────────────────────────────────────

def search_eatwith(city: str, date: str = None,
                    adults: int = 2, max_results: int = 10) -> list[dict]:
    """
    EatWith social dining + local experiences.
    STATUS: STUB — site is Next.js/React, requires Playwright for JS rendering.
    TODO: Implement via Playwright browser navigation (Chrome debug port 9222 available).
    """
    return [_err("eatwith",
                 "EatWith requires Playwright (Next.js app, no scrapeable API found). "
                 "TODO: drive Chrome debug port 9222")]


# ─── Aggregator ──────────────────────────────────────────────────────────────

SOURCES = {
    "project_expedition": search_project_expedition,
    "getyourguide": search_getyourguide,
    "shore_excursions_group": search_shore_excursions_group,
    "eatwith": search_eatwith,
}


def search(city: str, date: str = None, adults: int = 2,
           sources: list[str] = None,
           min_rating: float = None,
           cruise_friendly_only: bool = False,
           max_per_source: int = 20,
           workers: int = 4) -> list[dict]:
    """
    Parallel multi-source excursion search. Returns merged, sorted results.

    Args:
        city: Cruise port or destination ("Venice", "Santorini", "Kotor")
        date: Ship date YYYY-MM-DD (used by SEG for availability)
        adults: Party size (affects per-person pricing on private tours)
        sources: Subset of sources to query (default: all)
        min_rating: Filter by minimum rating (0–5)
        cruise_friendly_only: Only return Cruise Friendly tours (back-to-ship guarantee)
        max_per_source: Max results per source
        workers: Thread pool size

    Returns:
        List of normalized excursion dicts, sorted by rating desc (None last).
        Error-only dicts have source and error fields but name=None.
    """
    active_sources = {k: v for k, v in SOURCES.items()
                      if sources is None or k in sources}

    def _call(source_name, fn):
        try:
            if source_name in ("getyourguide",):
                return fn(city, date=date, adults=adults, max_results=max_per_source)
            elif source_name in ("shore_excursions_group",):
                return fn(city, ship_date=date, adults=adults, max_results=max_per_source)
            elif source_name in ("eatwith",):
                return fn(city, date=date, adults=adults, max_results=max_per_source)
            else:
                return fn(city, adults=adults, max_results=max_per_source)
        except Exception as e:
            return [_err(source_name, str(e))]

    all_results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_call, name, fn): name
                   for name, fn in active_sources.items()}
        for future in as_completed(futures):
            all_results.extend(future.result() or [])

    # Filter
    real = [r for r in all_results if r.get("name")]
    errors = [r for r in all_results if not r.get("name")]

    if min_rating is not None:
        real = [r for r in real if r.get("rating") and r["rating"] >= min_rating]
    if cruise_friendly_only:
        real = [r for r in real if r.get("cruise_friendly")]

    # Sort by rating desc (unrated last)
    real.sort(key=lambda r: (r.get("rating") or 0), reverse=True)
    return real + errors


def brief(city: str, date: str = None, adults: int = 2,
          top_n: int = 10, cruise_friendly_only: bool = False) -> str:
    """One-call summary suitable for a Dembe Intel Report section."""
    results = search(city, date=date, adults=adults,
                     cruise_friendly_only=cruise_friendly_only)
    real = [r for r in results if r.get("name")]
    errors = [r for r in results if not r.get("name")]

    lines = [f"## EXCURSIONS — {city.upper()} ({len(real)} results)"]
    for r in real[:top_n]:
        price = f"${r['price_per_person']:.0f}/pp" if r.get("price_per_person") else "price TBD"
        dur = f"{r['duration_hours']:.0f}h" if r.get("duration_hours") else ""
        rating = f"★{float(r['rating']):.1f}" if r.get("rating") else ""
        cf = " 🚢CF" if r.get("cruise_friendly") else ""
        food = " 🍽" if r.get("includes_food") else ""
        lines.append(f"- [{r['source']}] {r['name']} — {price} {dur} {rating}{cf}{food}")
    for e in errors:
        lines.append(f"  ⚠ {e['source']}: {e['error'][:60]}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys, argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("adults", nargs="?", type=int, default=2)
    ap.add_argument("--cruise-friendly", action="store_true")
    ap.add_argument("--min-rating", type=float, default=None)
    ap.add_argument("--source", action="append", dest="sources")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    print(brief(args.city, date=args.date, adults=args.adults,
                cruise_friendly_only=args.cruise_friendly, top_n=args.top))
    if args.min_rating or args.sources:
        print("\n[Filtered view]")
        results = search(args.city, date=args.date, adults=args.adults,
                         sources=args.sources, min_rating=args.min_rating,
                         cruise_friendly_only=args.cruise_friendly)
        real = [r for r in results if r.get("name")]
        for r in real[:args.top]:
            price = f"${r['price_per_person']:.0f}" if r.get("price_per_person") else "?"
            print(f"  {r['name']} [{r['source']}] {price}")
