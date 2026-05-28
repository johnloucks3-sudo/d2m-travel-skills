"""
CruiseBound.com → intel_index connector.
Public HTML scraper — no auth required.
TTL: 8h
"""
import logging
import sqlite3
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CRUISEBOUND_BASE = "https://www.cruisebound.com"

# CruiseBound uses /lp/book-{name}-cruises pattern
SEARCH_LINES = [
    ("book-silversea-cruises",       "Silversea"),
    ("book-regent-seven-seas-cruises", "Regent Seven Seas"),
    ("book-cunard-cruises",          "Cunard"),
    ("book-oceania-cruises",         "Oceania"),
    ("book-seabourn-cruises",        "Seabourn"),
    ("book-viking-ocean-cruises",    "Viking Ocean"),
    ("book-ponant-cruises",          "Ponant"),
]


def _parse_price(text: str) -> float:
    if not text:
        return 0.0
    cleaned = "".join(c for c in text if c.isdigit() or c == ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def ingest_cruisebound(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        logger.error("cruisebound: missing dependency: %s", e)
        log_run(con, "cruisebound", "import_error", error=str(e))
        return

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    all_rows = []
    t0 = time.monotonic()

    for line_slug, line_name in SEARCH_LINES:
        url = f"{CRUISEBOUND_BASE}/lp/{line_slug}"
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.warning("cruisebound/%s: HTTP %d", line_name, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # CruiseBound result cards — try multiple selectors
            cards = (
                soup.select("div.cruise-card")
                or soup.select("div[class*='result-card']")
                or soup.select("article[class*='cruise']")
                or soup.select("div[class*='listing']")
            )

            # Also try JSON-LD structured data
            if not cards:
                import json as _json
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = _json.loads(script.string or "")
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get("@type") in ("Product", "Trip", "Offer", "ItemList"):
                                price_val = 0.0
                                if "offers" in item:
                                    price_val = _parse_price(
                                        str(item["offers"].get("price", 0))
                                    )
                                row = {
                                    "id": f"cruisebound_{line_name}_{len(all_rows)}",
                                    "line": line_name,
                                    "ship": item.get("name", ""),
                                    "price_from": price_val,
                                    "url": item.get("url", url),
                                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                                }
                                all_rows.append(row)
                    except Exception:
                        pass
                time.sleep(1)
                continue

            for card in cards:
                ship_el = (
                    card.select_one("[class*='ship']")
                    or card.select_one("h3")
                    or card.select_one("h2")
                )
                price_el = (
                    card.select_one("[class*='price']")
                    or card.select_one(".price")
                )
                date_el = card.select_one("[class*='date']") or card.select_one(".date")
                nights_el = card.select_one("[class*='night']") or card.select_one(".nights")
                dest_el = card.select_one("[class*='destination']") or card.select_one(".destination")
                link_el = card.select_one("a[href]")

                ship = ship_el.get_text(strip=True) if ship_el else ""
                price = _parse_price(price_el.get_text(strip=True) if price_el else "")
                dep_date = date_el.get_text(strip=True) if date_el else ""
                nights = nights_el.get_text(strip=True) if nights_el else ""
                dest = dest_el.get_text(strip=True) if dest_el else ""
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = CRUISEBOUND_BASE + link

                row = {
                    "id": f"cruisebound_{line_name}_{len(all_rows)}",
                    "line": line_name,
                    "ship": ship,
                    "price_from": price,
                    "departure_date": dep_date,
                    "nights": nights,
                    "destination": dest,
                    "url": link,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                all_rows.append(row)

            logger.debug("cruisebound/%s: %d cards", line_slug, len(cards))
            time.sleep(1)

        except Exception as e:
            logger.warning("cruisebound/%s failed: %s", line_slug, e)
            continue

    elapsed = time.monotonic() - t0
    if all_rows:
        n = upsert_rows(
            con, "cruisebound", "cruise_pricing", all_rows, ttl,
            provenance=f"{CRUISEBOUND_BASE}/search",
        )
        log_run(con, "cruisebound", "pricing_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("cruisebound/cruise_pricing: %d rows in %.1fs", n, elapsed)
    else:
        log_run(con, "cruisebound", "pricing_empty", rows_in=0, rows_out=0, elapsed=elapsed,
                error="No rows scraped — page structure may have changed")
        logger.warning("cruisebound: 0 rows scraped in %.1fs", elapsed)
