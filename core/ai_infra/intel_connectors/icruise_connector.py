"""
iCruise.com → intel_index connector.
Public HTML scraper — no auth required.
TTL: 8h
"""
import logging
import sqlite3
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ICRUISE_BASE = "https://www.icruise.com"

# Correct iCruise URL pattern: /cruise-lines/{name}-cruises.html
SEARCH_LINES = [
    ("silversea-cruises", "Silversea"),
    ("regent-seven-seas-cruises", "Regent Seven Seas"),
    ("cunard-line", "Cunard"),
    ("oceania-cruises", "Oceania"),
    ("seabourn-cruise-line", "Seabourn"),
    ("viking-ocean-cruises", "Viking Ocean"),
    ("amawaterways", "AmaWaterways"),
    ("ponant", "Ponant"),
]


def _parse_price(text: str) -> float:
    """Extract numeric price from strings like '$4,299' or '4299'."""
    if not text:
        return 0.0
    cleaned = text.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def ingest_icruise(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        logger.error("icruise: missing dependency: %s", e)
        log_run(con, "icruise", "import_error", error=str(e))
        return

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    all_rows = []
    t0 = time.monotonic()

    for line_slug, line_name in SEARCH_LINES:
        url = f"{ICRUISE_BASE}/cruise-lines/{line_slug}.html"
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.warning("icruise/%s: HTTP %d", line_slug, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # iCruise listing cards — class patterns vary by version
            cards = (
                soup.select("div.cruise-result")
                or soup.select("div.search-result-item")
                or soup.select("article.cruise-card")
                or soup.select("div[class*='cruise-result']")
            )

            if not cards:
                # Fallback: grab any price + ship name from structured data
                import json as _json
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = _json.loads(script.string or "")
                        if isinstance(data, list):
                            items = data
                        else:
                            items = data.get("itemListElement", [data])
                        for item in items:
                            if item.get("@type") in ("Trip", "Product", "Offer"):
                                row = {
                                    "id": f"icruise_{line_slug}_{len(all_rows)}",
                                    "line": line_name,
                                    "ship": item.get("name", ""),
                                    "price_from": _parse_price(
                                        str(item.get("offers", {}).get("price", 0))
                                    ),
                                    "url": item.get("url", url),
                                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                                }
                                all_rows.append(row)
                    except Exception:
                        pass
                continue

            for card in cards:
                ship_el = (
                    card.select_one(".ship-name")
                    or card.select_one("h3")
                    or card.select_one("h2")
                    or card.select_one("[class*='ship']")
                )
                price_el = (
                    card.select_one(".price")
                    or card.select_one("[class*='price']")
                    or card.select_one("span.from-price")
                )
                date_el = (
                    card.select_one(".departure-date")
                    or card.select_one("[class*='date']")
                )
                nights_el = (
                    card.select_one(".nights")
                    or card.select_one("[class*='night']")
                )
                link_el = card.select_one("a[href]")

                ship = ship_el.get_text(strip=True) if ship_el else ""
                price = _parse_price(price_el.get_text(strip=True) if price_el else "")
                dep_date = date_el.get_text(strip=True) if date_el else ""
                nights = nights_el.get_text(strip=True) if nights_el else ""
                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = ICRUISE_BASE + link

                row = {
                    "id": f"icruise_{line_slug}_{len(all_rows)}",
                    "line": line_name,
                    "ship": ship,
                    "price_from": price,
                    "departure_date": dep_date,
                    "nights": nights,
                    "url": link,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                all_rows.append(row)

            logger.debug("icruise/%s: %d cards", line_slug, len(cards))
            time.sleep(1)  # polite crawl delay

        except Exception as e:
            logger.warning("icruise/%s failed: %s", line_slug, e)
            continue

    elapsed = time.monotonic() - t0
    if all_rows:
        n = upsert_rows(
            con, "icruise", "cruise_pricing", all_rows, ttl,
            provenance=f"{ICRUISE_BASE}/cruise-line/",
        )
        log_run(con, "icruise", "pricing_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("icruise/cruise_pricing: %d rows in %.1fs", n, elapsed)
    else:
        log_run(con, "icruise", "pricing_empty", rows_in=0, rows_out=0, elapsed=elapsed,
                error="No rows scraped — page structure may have changed")
        logger.warning("icruise: 0 rows scraped in %.1fs", elapsed)
