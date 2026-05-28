"""
VTG (Vacations To Go) promo email → intel_index connector.
Scrapes d2mconcierge Gmail inbox for VTG promo emails.
TTL: 24h (on-receive sweep)
"""
import json
import logging
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

VTG_SENDER_PATTERNS = [
    "vacationstogo.com",
    "vtg.com",
    "vacations-to-go",
]

# Gmail token path for d2mconcierge
GMAIL_TOKEN_PATH = Path(__file__).resolve().parents[3] / "gmail_token.json"


def _parse_price_from_text(text: str) -> float:
    """Extract first dollar amount from text."""
    m = re.search(r"\$[\d,]+(?:\.\d{1,2})?", text)
    if m:
        return float(m.group().replace("$", "").replace(",", ""))
    return 0.0


def _extract_vtg_deals(html_body: str, subject: str) -> list[dict]:
    """Parse VTG promo email HTML for cruise deals."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html_body, "html.parser")
    deals = []

    # VTG emails typically have deal blocks with ship, price, date
    # Look for table rows or div blocks containing cruise info
    blocks = (
        soup.select("td[class*='deal']")
        or soup.select("div[class*='deal']")
        or soup.select("tr")
    )

    # Fallback: extract all text blocks that mention prices
    if not blocks:
        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Look for clusters with price + ship name + date
        for i, line in enumerate(lines):
            if "$" in line and any(c.isdigit() for c in line):
                context = " ".join(lines[max(0, i-2):i+3])
                price = _parse_price_from_text(line)
                if price > 100:
                    deals.append({
                        "ship": "",
                        "price_from": price,
                        "context": context[:200],
                        "source_subject": subject,
                    })
        return deals[:20]  # cap at 20 raw hits per email

    for block in blocks[:50]:
        text = block.get_text(separator=" ", strip=True)
        price = _parse_price_from_text(text)
        if price < 100:
            continue

        # Try to extract ship name — VTG often bolds ship name
        ship_el = block.select_one("strong") or block.select_one("b")
        ship = ship_el.get_text(strip=True) if ship_el else ""

        # Extract date patterns
        date_m = re.search(
            r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s+\d{4})",
            text
        )
        dep_date = date_m.group(1) if date_m else ""

        # Nights
        nights_m = re.search(r"(\d+)\s*-?\s*night", text, re.I)
        nights = nights_m.group(1) if nights_m else ""

        deals.append({
            "ship": ship,
            "price_from": price,
            "departure_date": dep_date,
            "nights": nights,
            "context": text[:200],
            "source_subject": subject,
        })

    return deals


def _decode_gmail_body(payload: dict) -> str:
    """Extract plain/HTML body from Gmail message payload."""
    import base64

    def _get_part(p):
        mime = p.get("mimeType", "")
        if mime in ("text/html", "text/plain"):
            data = p.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        for sub in p.get("parts", []):
            result = _get_part(sub)
            if result:
                return result
        return ""

    return _get_part(payload)


def ingest_vtg(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    try:
        from core.email.thunderbird_gmail import _get_gmail_service
    except ImportError as e:
        logger.error("vtg: could not import Gmail service: %s", e)
        log_run(con, "vtg", "import_error", error=str(e))
        return

    t0 = time.monotonic()
    all_rows = []

    try:
        service = _get_gmail_service()

        # Search for VTG promo emails in d2mconcierge
        query_parts = [f"from:{pat}" for pat in VTG_SENDER_PATTERNS]
        query = "(" + " OR ".join(query_parts) + ") newer_than:30d"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.info("vtg: no VTG emails found in last 30 days")
            elapsed = time.monotonic() - t0
            log_run(con, "vtg", "no_emails", rows_in=0, rows_out=0, elapsed=elapsed)
            return

        seen_ids: set = set()
        for msg_ref in messages:
            msg_id = msg_ref.get("id", "")
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

            try:
                full_msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                headers = {
                    h["name"].lower(): h["value"]
                    for h in full_msg.get("payload", {}).get("headers", [])
                }
                subject = headers.get("subject", "")
                date_str = headers.get("date", "")
                body_html = _decode_gmail_body(full_msg.get("payload", {}))

                deals = _extract_vtg_deals(body_html or full_msg.get("snippet", ""), subject)
                for i, deal in enumerate(deals):
                    row = {
                        "id": f"vtg_{msg_id}_{i}",
                        "email_id": msg_id,
                        "email_date": date_str,
                        "email_subject": subject,
                        "ship": deal.get("ship", ""),
                        "price_from": deal.get("price_from", 0),
                        "departure_date": deal.get("departure_date", ""),
                        "nights": deal.get("nights", ""),
                        "context": deal.get("context", ""),
                        "source": "vtg_email",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_rows.append(row)

            except Exception as e:
                logger.warning("vtg: failed to process message %s: %s", msg_id, e)
                continue

    except Exception as e:
        elapsed = time.monotonic() - t0
        log_run(con, "vtg", "gmail_error", error=str(e), elapsed=elapsed)
        logger.error("vtg Gmail ingest failed: %s", e)
        return

    elapsed = time.monotonic() - t0
    if all_rows:
        n = upsert_rows(
            con, "vtg", "promo_email", all_rows, ttl,
            provenance="d2mconcierge Gmail / VTG promo emails",
        )
        log_run(con, "vtg", "email_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("vtg/promo_email: %d rows in %.1fs", n, elapsed)
    else:
        log_run(con, "vtg", "email_empty", rows_in=0, rows_out=0, elapsed=elapsed,
                error="No deals extracted from VTG emails")
        logger.info("vtg: 0 deals extracted in %.1fs", elapsed)
