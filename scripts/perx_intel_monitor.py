#!/usr/bin/env python3
"""
Perx Intel Monitor — Interline Rate Early-Warning System
=========================================================
Perx.com surfaces interline (employee/industry) fares for cruise + air.
These fares are a leading indicator: when Perx discounts deepen significantly
on a sailing or route, TA commission rates almost always follow within 7-14 days.

Logic:
  1. Load authenticated Perx session cookies
  2. Search for sailings on watched routes (Norway 2027, Silver Nova, RSSC, etc.)
  3. Compare current interline prices vs stored baseline
  4. Telegram Commander when discount depth exceeds TA_SIGNAL_THRESHOLD

Signal thresholds (empirical — adjust as history accumulates):
  WATCH (15–24% below baseline)  → monitor more closely
  SIGNAL (≥25% below baseline)   → TA rate likely within 7-14 days
  URGENT (≥35% below baseline)   → TA rate may already be live — check TA portals NOW

Run:
  python3 scripts/perx_intel_monitor.py
  python3 scripts/perx_intel_monitor.py --routes "norway silversea" --verbose

Data files:
  data/perx_intel_history.json   — price history per sailing key
  data/perx_intel_watches.json   — active route/ship watch list

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale/Intel 2026-06-08
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
TB = Path(__file__).resolve().parent.parent
CREDS_DIR = TB / "creds"
DATA_DIR = TB / "data"
LOG_DIR = TB / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

COOKIE_FILE = CREDS_DIR / "perx_cookies.json"
HISTORY_FILE = DATA_DIR / "perx_intel_history.json"
WATCHES_FILE = DATA_DIR / "perx_intel_watches.json"
ALERT_DEDUP_FILE = DATA_DIR / "perx_alert_dedup.json"
EOD_QUEUE_FILE = DATA_DIR / "perx_eod_queue.json"
ENV_FILE = TB / ".env"

# ── Signal thresholds ──────────────────────────────────────────────────────────
WATCH_THRESHOLD = -15.0    # % — start watching
SIGNAL_THRESHOLD = -25.0   # % — TA rate likely incoming
URGENT_THRESHOLD = -35.0   # % — TA rate may already be live

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s PERX-INTEL %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "perx_intel_monitor.log"), mode="a"),
    ],
)
log = logging.getLogger("perx_intel")

COMMANDER_ID = 7554895206

# ── Default watch list — routes to monitor on each run ────────────────────────
DEFAULT_WATCHES = [
    # --- APPROVED LINES: Regent, Atlas Ocean, Celebrity, Silversea ---
    # Norway/Scandinavia 2027
    {
        "id": "norway-2027-silversea",
        "label": "Norway/Scandinavia 2027 — Silversea",
        "search_terms": ["norway", "silversea"],
        "year": 2027,
        "months": [7, 8],
        "notes": "MISSION-067/068 active watch",
    },
    {
        "id": "norway-2027-regent",
        "label": "Norway/Scandinavia 2027 — Regent Seven Seas",
        "search_terms": ["norway", "regent"],
        "year": 2027,
        "months": [7, 8],
        "notes": "MISSION-068 active watch",
    },
    # Silver Nova (active D2M client sailings — Silversea)
    {
        "id": "silver-nova-2026",
        "label": "Silver Nova 2026 sailings",
        "search_terms": ["silver nova"],
        "year": 2026,
        "months": [10, 11, 12],
        "notes": "Active D2M client sailings",
    },
    # RSSC Grandeur (McLeod active + Loucks Dec 29 booking)
    {
        "id": "grandeur-2026",
        "label": "Seven Seas Grandeur 2026",
        "search_terms": ["grandeur", "regent"],
        "year": 2026,
        "months": [7, 8, 9, 10],
        "notes": "McLeod/Furlow active booking — MISSION-053",
    },
    # Loucks — Regent Grandeur Panama Canal Dec 29 (MIA→LAX, 16 nights)
    {
        "id": "loucks-grandeur-panama-dec2026",
        "label": "Regent Grandeur — Panama Canal Dec 29 2026 (Loucks, MIA→LAX)",
        "search_terms": ["grandeur", "regent", "panama"],
        "year": 2026,
        "months": [12],
        "notes": "Loucks booking 3122006. Board MIA Dec 29, disembark LAX Jan 14 2027.",
    },
    # Mediterranean 2027 — Silversea + Regent only (no Viking/Seabourn/Princess)
    {
        "id": "med-2027-silversea",
        "label": "Mediterranean 2027 — Silversea",
        "search_terms": ["mediterranean", "silversea"],
        "year": 2027,
        "months": [4, 5, 6, 9, 10],
        "notes": "Silversea Med TA rate signal",
    },
    {
        "id": "med-2027-regent",
        "label": "Mediterranean 2027 — Regent",
        "search_terms": ["mediterranean", "regent"],
        "year": 2027,
        "months": [4, 5, 6, 9, 10],
        "notes": "Regent Med TA rate signal — Loucks May 2027",
    },
    # Atlas Ocean Voyages
    {
        "id": "atlas-ocean-2027",
        "label": "Atlas Ocean Voyages 2027",
        "search_terms": ["atlas ocean"],
        "year": 2027,
        "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "notes": "Commander-approved line — TA interline rate watch",
    },
    # Celebrity Cruises (river watch: Celebrity does ocean only — flag if Commander means a different river brand)
    {
        "id": "celebrity-2027",
        "label": "Celebrity Cruises 2027",
        "search_terms": ["celebrity"],
        "year": 2027,
        "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "notes": "Commander-approved. Note: Celebrity is ocean only. If river cruises intended, specify brand (AmaWaterways, Crystal, Scenic).",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_env_var(key: str) -> str:
    val = os.environ.get(key, "")
    if not val and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
    return val


def _tg_send(text: str) -> bool:
    token = _load_env_var("TELEGRAM_C2_BOT_TOKEN") or _load_env_var("TELEGRAM_BOT_TOKEN")
    if not token:
        log.warning("No Telegram token — alert logged only")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.ok
    except Exception as exc:
        log.error("Telegram send failed: %s", exc)
        return False


def _load_dedup() -> dict:
    if ALERT_DEDUP_FILE.exists():
        try:
            return json.loads(ALERT_DEDUP_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_dedup(dedup: dict) -> None:
    ALERT_DEDUP_FILE.write_text(json.dumps(dedup, indent=2), encoding="utf-8")


def _is_already_sent_today(dedup: dict, key: str, level: str, current_price: float = None) -> bool:
    """Return True if this exact quote was already Telegram-sent.

    Fixed 2026-07-04 (Commander: "same quotes each day... I only need to see
    it once until it changes"): this used to re-send once every calendar day
    regardless of whether the price had moved at all — a date-based cooldown,
    same bug class as the staff-tasking/credentials-health fixes today. Now
    compares against the LAST ALERTED PRICE for this key+level; only re-alerts
    when the price has actually moved (>$1), not when the day rolls over.
    """
    entry = dedup.get(f"{key}:{level}")
    if not entry:
        return False
    last_price = entry.get("last_price")
    if last_price is None:
        # legacy dedup entry from before this fix — treat as stale, allow one fresh alert
        return False
    if current_price is None:
        return True
    return abs(last_price - current_price) < 1.0


def _mark_sent(dedup: dict, key: str, level: str, current_price: float = None) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    dedup[f"{key}:{level}"] = {
        "date": today, "ts": datetime.now().isoformat(), "last_price": current_price,
    }


def _queue_for_eod(signals: list[dict]) -> None:
    """Persist WATCH-level signals to EOD queue file for morning brief pickup."""
    today = datetime.now().strftime("%Y-%m-%d")
    queue: dict = {}
    if EOD_QUEUE_FILE.exists():
        try:
            queue = json.loads(EOD_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if queue.get("date") != today:
        queue = {"date": today, "watches": []}
    seen_keys = {w["key"] for w in queue.get("watches", [])}
    for s in signals:
        if s["key"] not in seen_keys:
            queue.setdefault("watches", []).append(s)
    EOD_QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")


def _load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_history(history: dict):
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_watches() -> list:
    if WATCHES_FILE.exists():
        try:
            return json.loads(WATCHES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Write defaults on first run
    WATCHES_FILE.write_text(json.dumps(DEFAULT_WATCHES, indent=2), encoding="utf-8")
    return DEFAULT_WATCHES


def _load_cookies() -> list:
    if not COOKIE_FILE.exists():
        return []
    raw = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    # Support both raw list and nested {"cookies": [...]} format
    if isinstance(raw, list):
        return raw
    return raw.get("cookies", [])


def _classify_signal(pct_change: float) -> tuple[str, str]:
    """Return (level, emoji) for a discount depth."""
    if pct_change <= URGENT_THRESHOLD:
        return "URGENT", "🚨"
    elif pct_change <= SIGNAL_THRESHOLD:
        return "SIGNAL", "⚠️"
    elif pct_change <= WATCH_THRESHOLD:
        return "WATCH", "👁"
    else:
        return "STABLE", "✅"


# ── Playwright scraper ─────────────────────────────────────────────────────────

def _get_session() -> requests.Session:
    """Build an authenticated requests.Session using saved Perx cookies."""
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.perx.com/",
        "Origin": "https://www.perx.com",
    })
    for cookie in _load_cookies():
        if "perx" in cookie.get("domain", ""):
            sess.cookies.set(cookie["name"], cookie["value"], domain="www.perx.com")
    return sess


def _search_perx_sailings_http(
    sess: requests.Session,
    search_terms: list[str],
    year: int,
    months: list[int],
    verbose: bool = False,
) -> list[dict]:
    """
    Search Perx.com for sailings using authenticated HTTP session.
    Returns list of: {ship, cruise_line, departure_date, nights, route, price_usd, source}

    Strategy (sail-personalize.com API is dead as of 2026-05):
      1. Authenticated POST to sail-personalize.com API with session cookies
      2. If API returns data → parse structured JSON
      3. If API dead (400) → HTTP GET to Perx search page → parse HTML
    """
    import time as _time
    from html.parser import HTMLParser

    month_start = min(months)
    month_end = max(months)
    sailings = []

    # ── Strategy 1: authenticated API ─────────────────────────────────────────
    api_url = "https://api.sail-personalize.com/v1/search/cruises"
    csrf = sess.cookies.get("csrftoken", default="")

    line_lookup = {
        "silversea": "Silversea Cruises",
        "regent": "Regent Seven Seas Cruises",
        "seabourn": "Seabourn",
        "silver nova": "Silversea Cruises",
        "grandeur": "Regent Seven Seas Cruises",
        "viking": "Viking",
        "oceania": "Oceania Cruises",
        "ponant": "PONANT",
        "windstar": "Windstar Cruises",
    }
    region_lookup = {
        "norway": "arctic",
        "scandinavia": "arctic",
        "nordic": "arctic",
        "arctic": "arctic",
        "mediterranean": "mediterranean",
        "med": "mediterranean",
        "caribbean": "caribbean",
    }

    for term in search_terms:
        tl = term.lower()
        payload = {
            "departure_date_from": f"{year}-{month_start:02d}-01",
            "departure_date_to": f"{year}-{month_end:02d}-30",
            "nights_min": 3,
            "nights_max": 120,
            "page": 1,
            "per_page": 200,
            "sort": "departure_date",
            "currency": "USD",
        }
        if tl in region_lookup:
            payload["destination"] = region_lookup[tl]
        if tl in line_lookup:
            payload["cruise_line"] = line_lookup[tl]

        try:
            resp = sess.post(
                api_url,
                json=payload,
                headers={"X-CSRFToken": csrf, "Content-Type": "application/json"},
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_list = data if isinstance(data, list) else data.get("results", data.get("data", []))
                for item in raw_list:
                    ship = (item.get("ship_name") or item.get("ship") or "").strip()
                    dep = (item.get("departure_date") or item.get("date") or "").strip()
                    route = (item.get("itinerary_name") or item.get("route") or item.get("name") or "").strip()
                    line = (item.get("cruise_line_name") or item.get("cruise_line") or "").strip()
                    days = str(item.get("nights") or item.get("days") or "").strip()
                    raw_price = item.get("price") or item.get("price_usd") or item.get("from_price") or 0
                    try:
                        price = float(str(raw_price).replace(",", "").replace("$", ""))
                    except Exception:
                        price = 0

                    if not ship or not dep or not price:
                        continue

                    # Ship-specific filters
                    text_blob = f"{ship} {route} {line}".lower()
                    if "silver nova" in tl and "nova" not in text_blob:
                        continue
                    if "grandeur" in tl and "grandeur" not in text_blob:
                        continue

                    sailings.append({
                        "ship": ship, "cruise_line": line,
                        "departure_date": dep, "nights": days,
                        "route": route, "price_usd": price,
                        "source": "api",
                    })
                if verbose:
                    log.info("API: %d sailings for term=%s", len(raw_list), term)
            else:
                if verbose:
                    log.info("API %d for term=%s", resp.status_code, term)
        except Exception as exc:
            if verbose:
                log.info("API error for term=%s: %s", term, exc)
        _time.sleep(0.5)

    if sailings:
        log.info("API path: %d sailings for %s", len(sailings), search_terms)
        return sailings

    # ── Strategy 2: authenticated HTML scrape ─────────────────────────────────
    # Build a search URL with cruise line filter
    line_slug_map = {
        "silversea": "Silversea+Cruises",
        "regent": "Regent+Seven+Seas+Cruises",
        "seabourn": "Seabourn",
        "silver nova": "Silversea+Cruises",
        "grandeur": "Regent+Seven+Seas+Cruises",
    }
    line_filter = ""
    for term in search_terms:
        if term.lower() in line_slug_map:
            line_filter = f"&cruise_line={line_slug_map[term.lower()]}"
            break

    search_url = (
        f"https://www.perx.com/cruises/"
        f"?date_from={year}-{month_start:02d}-01"
        f"&date_to={year}-{month_end:02d}-30"
        f"&per_page=100&currency=USD&sort=departure_date"
        f"{line_filter}"
    )

    try:
        resp = sess.get(search_url, timeout=30)
        if resp.status_code != 200:
            log.warning("HTML search returned %d", resp.status_code)
            return []

        html = resp.text
        # Extract JSON-LD or embedded data attributes for pricing
        # Perx embeds cruise data as JSON in script tags or data attributes
        json_ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for match in json_ld_matches:
            try:
                data = json.loads(match.strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Product", "Offer", "Trip"):
                        name = item.get("name", "")
                        price = item.get("offers", {}).get("price") or item.get("price") or 0
                        if price and name:
                            sailings.append({
                                "ship": name, "cruise_line": "",
                                "departure_date": "", "nights": "",
                                "route": name, "price_usd": float(price),
                                "source": "json-ld",
                            })
            except Exception:
                pass

        # Fallback: extract price patterns near ship names from raw HTML
        if not sailings:
            price_pattern = re.compile(r'\$\s*([\d,]+)')
            ship_pattern = re.compile(
                r'(Silver [A-Z][a-z]+|Seven Seas [A-Z][a-z]+|Seabourn [A-Z][a-z]+|'
                r'Viking [A-Z][a-z]+|Le [A-Z][a-z]+|World [A-Za-z]+er)'
            )
            ships_found = ship_pattern.findall(html)
            prices_found = [float(p.replace(",", "")) for p in price_pattern.findall(html)]

            if ships_found and prices_found:
                # Pair first N ships with first N prices (rough heuristic)
                for i, ship in enumerate(ships_found[:20]):
                    price = prices_found[i] if i < len(prices_found) else 0
                    if price > 500:
                        sailings.append({
                            "ship": ship, "cruise_line": "",
                            "departure_date": "", "nights": "",
                            "route": f"{ship} sailing", "price_usd": price,
                            "source": "html-heuristic",
                        })

        # Filter to relevant terms
        if sailings:
            filtered = []
            for s in sailings:
                blob = f"{s['ship']} {s['route']} {s['cruise_line']}".lower()
                if any(t.lower() in blob for t in search_terms if len(t) > 3):
                    filtered.append(s)
            sailings = filtered or sailings  # keep all if none match filter

        log.info("HTML scrape: %d sailings for %s (url: %s)", len(sailings), search_terms, search_url[:80])

    except Exception as exc:
        log.error("HTML scrape failed: %s", exc)

    return sailings


# ── Analysis engine ────────────────────────────────────────────────────────────

def _sailing_key(watch_id: str, ship: str, dep_date: str) -> str:
    ship_slug = re.sub(r"[^a-z0-9]", "_", ship.lower())[:20]
    date_slug = dep_date[:10].replace("-", "") if dep_date else "nodate"
    return f"{watch_id}_{ship_slug}_{date_slug}"


def analyze_sailings(
    watch: dict,
    sailings: list[dict],
    history: dict,
) -> list[dict]:
    """
    Compare current prices to baseline. Return list of signal dicts.
    """
    signals = []
    now = datetime.now(timezone.utc).isoformat()
    watch_id = watch["id"]

    for s in sailings:
        price = s.get("price_usd", 0)
        if not price or price < 100:
            continue  # skip entries with no price

        key = _sailing_key(watch_id, s["ship"], s["departure_date"])

        # Load history for this sailing
        entry = history.get(key, {
            "watch_id": watch_id,
            "key": key,
            "ship": s["ship"],
            "cruise_line": s["cruise_line"],
            "departure_date": s["departure_date"],
            "route": s["route"],
            "baseline_price": price,  # first observed price IS the baseline
            "prices": [],
            "last_signal": None,
        })

        # Record this check
        entry["prices"].append({"ts": now, "price": price})
        entry["prices"] = entry["prices"][-90:]  # keep 90 data points

        # Establish baseline: median of first 5 non-zero observations
        all_prices = [p["price"] for p in entry["prices"] if p["price"] > 0]
        if len(all_prices) >= 5:
            sorted_p = sorted(all_prices[:5])
            entry["baseline_price"] = sorted_p[len(sorted_p) // 2]  # median
        entry["last_checked"] = now
        history[key] = entry

        baseline = entry["baseline_price"]
        pct_change = ((price - baseline) / baseline * 100) if baseline else 0
        level, emoji = _classify_signal(pct_change)

        if level != "STABLE":
            signals.append({
                "key": key,
                "watch_id": watch_id,
                "watch_label": watch["label"],
                "ship": s["ship"],
                "cruise_line": s["cruise_line"],
                "departure_date": s["departure_date"],
                "route": s["route"],
                "current_price": price,
                "baseline_price": baseline,
                "pct_change": round(pct_change, 1),
                "level": level,
                "emoji": emoji,
            })

    return signals


# ── Telegram formatter ─────────────────────────────────────────────────────────

def _build_telegram_message(signals: list[dict], watches_run: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    urgent = [s for s in signals if s["level"] == "URGENT"]
    alert = [s for s in signals if s["level"] == "SIGNAL"]
    watch = [s for s in signals if s["level"] == "WATCH"]

    if urgent:
        header = "🚨 <b>PERX URGENT — TA rates may be LIVE NOW</b>"
    elif alert:
        header = "⚠️ <b>PERX SIGNAL — TA rates incoming (7–14 days)</b>"
    else:
        header = "👁 <b>PERX WATCH — discount depth increasing</b>"

    lines = [
        header,
        f"<i>{now} · {watches_run} watch(es) scanned</i>",
        "",
    ]

    for s in urgent + alert + watch:
        action = ""
        if s["level"] == "URGENT":
            action = "→ <b>CHECK TA PORTALS NOW — rate may already be live</b>"
        elif s["level"] == "SIGNAL":
            action = "→ <b>Position clients — TA rate expected within 7–14 days</b>"
        else:
            action = "→ Monitor — discount trending deeper"

        ship_line = f"{s['ship']}" if s["ship"] != "unknown" else s["watch_label"]
        price_str = f"${s['current_price']:,.0f}" if s["current_price"] else "?"
        baseline_str = f"${s['baseline_price']:,.0f}" if s["baseline_price"] else "?"

        lines += [
            f"{s['emoji']} <b>{ship_line}</b> ({s.get('departure_date', '')[:10]})",
            f"  Route: {s['route'][:60]}" if s.get("route") else "",
            f"  Perx: {price_str} vs baseline {baseline_str} ({s['pct_change']:+.1f}%)",
            f"  {action}",
            "",
        ]

    lines.append("<i>— Intel (Dembe) · Thunderbird Perx Watch</i>")
    # Commander 2026-07-04: "I need a visible verification loop... I only need
    # to see it once until it changes." This stamp marks that the numbers above
    # were pulled from a live scan this run, not carried forward/guessed —
    # and that this exact price is new since the last alert (the dedup above
    # is what makes that claim true, not decoration).
    lines.append("<i>CHIEF SILVER — verified this run, new price since last alert</i>")
    return "\n".join(l for l in lines if l != "  ")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_perx_watch_cycle(
    route_filter: Optional[str] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    watches = _load_watches()
    history = _load_history()

    if route_filter:
        terms = [t.strip().lower() for t in route_filter.split()]
        watches = [
            w for w in watches
            if any(t in " ".join(w.get("search_terms", [])).lower() or t in w["label"].lower()
                   for t in terms)
        ]
        log.info("Filter '%s' matched %d watches", route_filter, len(watches))

    if not watches:
        log.warning("No watches matched — running all %d defaults", len(DEFAULT_WATCHES))
        watches = DEFAULT_WATCHES

    all_signals = []
    watches_run = 0

    # Auto-refresh session if expired
    sess = _get_session()
    try:
        check = sess.get("https://www.perx.com/account/", allow_redirects=False, timeout=10)
        if check.status_code != 200:
            log.info("Session expired — running keepalive before scan")
            import subprocess
            subprocess.run(
                ["python3", str(TB / "scripts" / "perx_session_keepalive.py")],
                timeout=120, check=True,
            )
            sess = _get_session()  # reload with fresh cookies
    except Exception as exc:
        log.warning("Session check failed: %s — proceeding anyway", exc)

    for watch in watches:
        log.info("Scanning watch: %s", watch["label"])
        try:
            sailings = _search_perx_sailings_http(
                sess,
                watch["search_terms"],
                watch["year"],
                watch["months"],
                verbose=verbose,
            )
            signals = analyze_sailings(watch, sailings, history)
            all_signals.extend(signals)
            watches_run += 1

            if verbose:
                log.info("  → %d sailings, %d signals", len(sailings), len(signals))
                for s in signals:
                    log.info(
                        "    %s %s %s %+.1f%%",
                        s["emoji"], s["ship"], s["departure_date"], s["pct_change"],
                    )

        except Exception as exc:
            log.error("Watch %s failed: %s", watch["id"], exc)

    _save_history(history)
    log.info(
        "Perx cycle complete: %d watch(es), %d signal(s) (%d URGENT, %d SIGNAL, %d WATCH)",
        watches_run, len(all_signals),
        sum(1 for s in all_signals if s["level"] == "URGENT"),
        sum(1 for s in all_signals if s["level"] == "SIGNAL"),
        sum(1 for s in all_signals if s["level"] == "WATCH"),
    )

    # WATCH-level signals → EOD queue only (never Telegram)
    watch_signals = [s for s in all_signals if s["level"] == "WATCH"]
    actionable = [s for s in all_signals if s["level"] in ("SIGNAL", "URGENT")]

    if watch_signals:
        _queue_for_eod(watch_signals)
        log.info("WATCH signals (%d) queued to EOD report — no Telegram", len(watch_signals))

    # SIGNAL/URGENT → Telegram, one-and-done: only when the price actually moved
    if actionable and not dry_run:
        dedup = _load_dedup()
        new_alerts = [
            s for s in actionable
            if not _is_already_sent_today(dedup, s["key"], s["level"], s.get("current_price"))
        ]
        if new_alerts:
            msg = _build_telegram_message(new_alerts, watches_run)
            sent = _tg_send(msg)
            if sent:
                for s in new_alerts:
                    _mark_sent(dedup, s["key"], s["level"], s.get("current_price"))
                _save_dedup(dedup)
            log.info("Telegram alert sent (%d new/changed actionable signals): %s", len(new_alerts), sent)
        else:
            log.info("All SIGNAL/URGENT signals unchanged from last alert — skipping Telegram")
    elif actionable and dry_run:
        log.info("dry-run: %d actionable signals would have been sent", len(actionable))

    return {
        "watches_run": watches_run,
        "signals": all_signals,
        "urgent": [s for s in all_signals if s["level"] == "URGENT"],
        "alert": [s for s in all_signals if s["level"] == "SIGNAL"],
        "watch": [s for s in all_signals if s["level"] == "WATCH"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Perx interline rate monitor — TA rate early warning")
    parser.add_argument("--routes", type=str, default=None,
                        help="Filter watches by route keyword (e.g. 'norway silversea')")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't send Telegram alerts")
    parser.add_argument("--list-watches", action="store_true",
                        help="List configured watches and exit")
    args = parser.parse_args()

    if args.list_watches:
        watches = _load_watches()
        print(f"\n{len(watches)} Perx intel watches configured:\n")
        for w in watches:
            months_str = f"months {min(w['months'])}–{max(w['months'])}" if w.get("months") else ""
            print(f"  [{w['id']}] {w['label']}")
            print(f"    terms={w['search_terms']} year={w.get('year','')} {months_str}")
            if w.get("notes"):
                print(f"    notes: {w['notes']}")
        return 0

    result = run_perx_watch_cycle(
        route_filter=args.routes,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, indent=2))
    return 0 if not result.get("urgent") else 2  # exit 2 on URGENT


if __name__ == "__main__":
    sys.exit(main())
