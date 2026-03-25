"""
Thunderbird Product Intake Pipeline
=====================================
Dreams2Memories Travel, LLC

Scans vendor/cruise-line emails sent to d2mconcierge@gmail.com, extracts
structured product data (cruises, hotels, tours, flights, excursions),
catalogs them in SQLite, and matches them to active clients via dossier scan.

Storage:  ~/Thunderbird/data/product_catalog.db
Dossiers: ~/Thunderbird/dossiers/

MCP tools registered via register_product_intake_tools():
  product_scan_vendors · product_search · product_match_clients
  product_list_recent  · product_digest
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DB_PATH = THUNDERBIRD_DIR / "data" / "product_catalog.db"
DOSSIERS_DIR = THUNDERBIRD_DIR / "dossiers"

# Commission defaults (CLAUDE.md §4)
STANDARD_MARKUP = 0.25        # 25 % — hotels / cruises
PREMIUM_SLH_MARKUP = 0.22     # 22 % — premium / SLH
PONANT_COMMISSION = 0.18      # 18 % midpoint (16–20 %)
EUR_USD = 1.09                # default exchange rate

TARGETED_CRUISE_LINES = {
    "silversea", "regent", "cunard", "oceania",
    "seabourn", "viking", "amawaterways", "ponant",
}

VENDOR_DOMAINS = {
    "silversea.com", "rssc.com", "cunard.com", "oceania.com",
    "seabourn.com", "vikingcruises.com", "amawaterways.com",
    "ponant.com", "slh.com", "fourseasons.com", "ritz-carlton.com",
}

PRODUCT_KEYWORDS = {
    "itinerary", "promotion", "offer", "pricing", "new voyage",
    "limited time", "early bird", "special rate", "package",
    "sailing", "incentive", "override", "commission", "fam trip",
}

VALID_PRODUCT_TYPES = {"cruise", "hotel", "tour", "flight", "excursion", "other"}
VALID_STATUSES = {"new", "cataloged", "matched", "archived"}

DOSSIER_SKIP = {"CLAUDE.md", "DANI_TESTER_BRIEFINGS.md", "DOSSIER_Regent_Tips_Guide.md"}


# ---------------------------------------------------------------------------
# Commission / Pricing Helpers
# ---------------------------------------------------------------------------

def fmt_usd(amount: float) -> str:
    """Format a float as a USD string: 12345.6 → '$12,345.60'."""
    return f"${amount:,.2f}"


def _apply_markup(
    net_usd: float,
    supplier: str = "",
    markup: Optional[float] = None,
) -> Dict[str, Any]:
    """Apply D2M markup to a net price and return pricing dict.

    Markup precedence:
      1. Explicit ``markup`` argument
      2. Ponant supplier  → 18 % (midpoint 16-20 %)
      3. 'premium' / SLH  → 22 %
      4. Default          → 25 %
    """
    if markup is None:
        supplier_lc = supplier.lower()
        if "ponant" in supplier_lc:
            markup = PONANT_COMMISSION
        elif any(x in supplier_lc for x in ("slh", "premium", "four seasons")):
            markup = PREMIUM_SLH_MARKUP
        else:
            markup = STANDARD_MARKUP

    client_price = net_usd * (1 + markup)
    return {
        "net_usd": fmt_usd(net_usd),
        "markup_pct": f"{markup * 100:.0f}%",
        "client_price_usd": fmt_usd(client_price),
        "commission_usd": fmt_usd(client_price - net_usd),
    }


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class Product:
    product_id: str
    product_type: str                    # cruise | hotel | tour | flight | excursion | other
    supplier: str                        # Silversea, Regent, Ponant, etc.
    name: str
    description: str
    destinations: List[str]
    dates: Dict[str, str]               # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    pricing: Dict[str, Any]             # net_usd + markup via _apply_markup()
    images: List[str]                   # URLs or base64 refs
    source_email_id: str
    intake_date: str                    # ISO date string
    matched_clients: List[str]
    tags: List[str]
    status: str                         # new | cataloged | matched | archived


def _make_product_id() -> str:
    return "PRD-" + uuid.uuid4().hex[:8].upper()


def _serialize(p: Product) -> Dict[str, Any]:
    d = asdict(p)
    for list_key in ("destinations", "images", "matched_clients", "tags"):
        d[list_key] = json.dumps(d[list_key])
    d["dates"] = json.dumps(d["dates"])
    d["pricing"] = json.dumps(d["pricing"])
    return d


def _deserialize(row: Dict[str, Any]) -> Product:
    for list_key in ("destinations", "images", "matched_clients", "tags"):
        if isinstance(row.get(list_key), str):
            row[list_key] = json.loads(row[list_key])
    for dict_key in ("dates", "pricing"):
        if isinstance(row.get(dict_key), str):
            row[dict_key] = json.loads(row[dict_key])
    return Product(**{k: row[k] for k in Product.__dataclass_fields__ if k in row})  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ProductCatalog — SQLite Backend
# ---------------------------------------------------------------------------

class ProductCatalog:
    """SQLite-backed catalog for D2M travel products."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Schema ──────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id      TEXT PRIMARY KEY,
                    product_type    TEXT NOT NULL,
                    supplier        TEXT,
                    name            TEXT,
                    description     TEXT,
                    destinations    TEXT,   -- JSON list
                    dates           TEXT,   -- JSON dict
                    pricing         TEXT,   -- JSON dict
                    images          TEXT,   -- JSON list
                    source_email_id TEXT,
                    intake_date     TEXT,
                    matched_clients TEXT,   -- JSON list
                    tags            TEXT,   -- JSON list
                    status          TEXT    DEFAULT 'new'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_status ON products(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_type ON products(product_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_intake ON products(intake_date)"
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── CRUD ────────────────────────────────────────────────────────────────

    def add_product(self, product: Product) -> str:
        """Persist a Product. Returns product_id.

        Skips insert if source_email_id already exists (idempotent).
        """
        if product.source_email_id:
            with self._conn() as conn:
                existing = conn.execute(
                    "SELECT product_id FROM products WHERE source_email_id = ?",
                    (product.source_email_id,),
                ).fetchone()
                if existing:
                    logger.info(
                        "Email %s already cataloged as %s — skipping",
                        product.source_email_id, existing["product_id"],
                    )
                    return existing["product_id"]

        row = _serialize(product)
        cols = ", ".join(row.keys())
        placeholders = ", ".join("?" * len(row))
        with self._conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO products ({cols}) VALUES ({placeholders})",
                list(row.values()),
            )
        logger.info("Cataloged %s — %s (%s)", product.product_id, product.name, product.supplier)
        return product.product_id

    def get_product(self, product_id: str) -> Optional[Product]:
        """Retrieve a single Product by ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE product_id = ?", (product_id,)
            ).fetchone()
        return _deserialize(dict(row)) if row else None

    def search_products(
        self,
        query: str,
        product_type: Optional[str] = None,
        supplier: Optional[str] = None,
    ) -> List[Product]:
        """Full-text search across name, description, destinations, tags.

        Optional filters: product_type and/or supplier (case-insensitive).
        """
        sql = "SELECT * FROM products WHERE status != 'archived'"
        params: List[Any] = []
        if query:
            like = f"%{query}%"
            sql += (
                " AND (name LIKE ? OR description LIKE ?"
                " OR destinations LIKE ? OR tags LIKE ? OR supplier LIKE ?)"
            )
            params.extend([like, like, like, like, like])
        if product_type:
            sql += " AND product_type = ?"
            params.append(product_type.lower())
        if supplier:
            sql += " AND supplier LIKE ?"
            params.append(f"%{supplier}%")
        sql += " ORDER BY intake_date DESC"

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_deserialize(dict(r)) for r in rows]

    def list_recent(
        self,
        days: int = 7,
        product_type: Optional[str] = None,
    ) -> List[Product]:
        """Products ingested within the last *days* days, newest first."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = "SELECT * FROM products WHERE intake_date >= ? AND status != 'archived'"
        params: List[Any] = [cutoff]
        if product_type:
            sql += " AND product_type = ?"
            params.append(product_type.lower())
        sql += " ORDER BY intake_date DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_deserialize(dict(r)) for r in rows]

    def archive_product(self, product_id: str) -> bool:
        """Set product status to 'archived'. Returns True if found."""
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE products SET status = 'archived' WHERE product_id = ?",
                (product_id,),
            )
        found = cursor.rowcount > 0
        if found:
            logger.info("Archived %s", product_id)
        else:
            logger.warning("archive_product: %s not found", product_id)
        return found

    def _update_matched_clients(self, product_id: str, clients: List[str]):
        status = "matched" if clients else "cataloged"
        with self._conn() as conn:
            conn.execute(
                "UPDATE products SET matched_clients = ?, status = ? WHERE product_id = ?",
                (json.dumps(clients), status, product_id),
            )

    def match_to_clients(self, product_id: str) -> List[Dict[str, Any]]:
        """Scan dossiers and return match records for this product.

        Each record: {client, match_reason, match_score}
        Also persists matched_clients list back to the DB.
        """
        product = self.get_product(product_id)
        if not product:
            logger.warning("match_to_clients: product %s not found", product_id)
            return []

        clients = _load_dossier_clients()
        results: List[Dict[str, Any]] = []
        prod_dests = {d.lower() for d in product.destinations}
        prod_tags = set(product.tags)
        supplier_lc = product.supplier.lower()

        for client in clients:
            score = 0
            reasons: List[str] = []

            # Destination overlap
            client_dests = {d.lower() for d in client.get("destinations", [])}
            overlap = prod_dests & client_dests
            if overlap:
                score += len(overlap) * 3
                reasons.append(f"destination: {', '.join(list(overlap)[:3])}")

            # Tag overlap
            tag_overlap = prod_tags & set(client.get("tags", []))
            if tag_overlap:
                score += len(tag_overlap) * 2
                reasons.append(f"interests: {', '.join(tag_overlap)}")

            # Supplier match
            if any(supplier_lc in s.lower() or s.lower() in supplier_lc
                   for s in client.get("suppliers", [])):
                score += 4
                reasons.append(f"past supplier: {product.supplier}")

            # Free-text dossier scan
            text_lc = client.get("text_excerpt", "").lower()
            for dest in product.destinations[:5]:
                if dest.lower() in text_lc:
                    score += 2
                    reasons.append(f"dossier mentions {dest}")

            if score >= 3:
                results.append({
                    "product": product_id,
                    "client": client["name"],
                    "match_reason": "; ".join(reasons),
                    "match_score": score,
                })
                logger.debug("  Match %s (score=%d): %s", client["name"], score, "; ".join(reasons))

        matched_names = [r["client"] for r in results]
        self._update_matched_clients(product_id, matched_names)
        logger.info("%s matched %d clients: %s", product_id, len(matched_names), matched_names)
        return results


# ---------------------------------------------------------------------------
# Dossier Client Loader (shared utility)
# ---------------------------------------------------------------------------

def _load_dossier_clients() -> List[Dict[str, Any]]:
    """Parse all dossier .md files into lightweight client dicts for matching."""
    clients: List[Dict[str, Any]] = []
    if not DOSSIERS_DIR.is_dir():
        logger.warning("Dossiers directory not found: %s", DOSSIERS_DIR)
        return clients

    for fp in DOSSIERS_DIR.glob("*.md"):
        if fp.name in DOSSIER_SKIP:
            continue
        try:
            text = fp.read_text(encoding="utf-8")
            name_m = re.search(r"^#[^#].*?—\s*(.+?)$", text, re.MULTILINE)
            client_name = name_m.group(1).strip() if name_m else fp.stem

            destinations: List[str] = []
            for pat in (
                r"Destinations?[:\s]+([^\n]+)",
                r"Port[s]?[:\s]+([^\n]+)",
                r"(?:going to|travel to|visiting)\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)",
            ):
                for m in re.finditer(pat, text, re.IGNORECASE):
                    destinations.extend(
                        d.strip() for d in re.split(r"[,;|]", m.group(1)) if d.strip()
                    )

            suppliers = [
                s for s in (
                    "Regent", "Viking", "Silversea", "Ponant", "Oceania",
                    "Seabourn", "Cunard", "AmaWaterways",
                    "Four Seasons", "SLH", "Marriott", "Hyatt",
                )
                if s.lower() in text.lower()
            ]

            tag_map = {
                "luxury":    ["luxury", "suite", "butler", "five star", "5-star"],
                "family":    ["family", "kids", "children", "grandchildren"],
                "adventure": ["adventure", "hiking", "expedition", "active"],
                "river":     ["river cruise", "ama", "amawaterways", "viking river"],
                "ocean":     ["ocean cruise", "silversea", "regent", "seabourn", "cunard"],
                "europe":    ["europe", "mediterranean", "scandinavia", "baltic", "greek"],
                "caribbean": ["caribbean", "antilles", "bahamas"],
                "alaska":    ["alaska"],
                "hawaii":    ["hawaii", "honolulu"],
                "asia":      ["asia", "japan", "tokyo", "hong kong"],
            }
            tags = [
                tag for tag, kws in tag_map.items()
                if any(kw.lower() in text.lower() for kw in kws)
            ]

            clients.append({
                "name": client_name,
                "filename": fp.name,
                "destinations": list(dict.fromkeys(destinations))[:20],
                "suppliers": suppliers,
                "tags": tags,
                "text_excerpt": text[:3000],
            })
        except Exception as exc:
            logger.error("Failed to parse dossier %s: %s", fp.name, exc)

    logger.info("Loaded %d dossier clients for matching", len(clients))
    return clients


# ---------------------------------------------------------------------------
# Email Parsing Helpers
# ---------------------------------------------------------------------------

_CRUISE_LINE_RE = re.compile(
    r"\b(Silversea|Regent(?:\s+Seven\s+Seas)?|Cunard|Oceania|Seabourn|"
    r"Viking(?:\s+Cruises)?|AmaWaterways|Ponant)\b",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")
_DATE_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:,?\s+20\d{2})?",
    re.IGNORECASE,
)
_DEST_RE = re.compile(
    r"\b(Mediterranean|Caribbean|Scandinavia|Baltic|Alaska|Hawaii|"
    r"Greek Isles?|Norwegian Fjords?|Adriatic|Red Sea|"
    r"Japan|Asia|South America|Amazon|Antarctica)\b",
    re.IGNORECASE,
)
_CABIN_RE = re.compile(r"\b(veranda|suite|penthouse|balcony|interior|oceanview|expedition)\b", re.IGNORECASE)


def extract_product_from_email(email_data: Dict[str, Any]) -> Optional[Product]:
    """Parse a raw email dict into a Product record.

    Keys expected in email_data: id, subject, sender, body (plain text).
    Returns None if the email is not recognizable as a product offer.
    """
    msg_id = email_data.get("id", "")
    subject = email_data.get("subject", "")
    sender = email_data.get("sender", "")
    body = email_data.get("body", "")
    body_trunc = body[:12000]
    full_text = f"{subject}\n{body_trunc}"

    # ── Supplier detection ──────────────────────────────────────────────────
    supplier = ""
    cruise_hits = _CRUISE_LINE_RE.findall(full_text)
    if cruise_hits:
        # Most-frequent cruise line name wins
        supplier = max(set(cruise_hits), key=cruise_hits.count).title()
    if not supplier:
        domain_m = re.search(r"@([\w.-]+)", sender)
        if domain_m:
            supplier = _domain_to_brand(domain_m.group(1).lower())

    # ── Product type ────────────────────────────────────────────────────────
    body_lc = full_text.lower()
    if any(x in body_lc for x in ("cruise", "sailing", "voyage", "ship", "cabin")):
        product_type = "cruise"
    elif any(x in body_lc for x in ("hotel", "resort", "property", "room rate")):
        product_type = "hotel"
    elif any(x in body_lc for x in ("tour", "day trip", "excursion", "shore")):
        product_type = "tour" if "tour" in body_lc else "excursion"
    elif any(x in body_lc for x in ("flight", "fare", "airfare", "airline")):
        product_type = "flight"
    else:
        product_type = "other"

    # ── Destinations ────────────────────────────────────────────────────────
    destinations = list(dict.fromkeys(m.group(0) for m in _DEST_RE.finditer(full_text)))

    # ── Dates ───────────────────────────────────────────────────────────────
    date_hits = [m.group(0) for m in _DATE_RE.finditer(full_text)]
    dates: Dict[str, str] = {}
    if date_hits:
        dates["start"] = date_hits[0]
        if len(date_hits) > 1:
            dates["end"] = date_hits[-1]

    # ── Pricing ─────────────────────────────────────────────────────────────
    price_hits = [float(p.replace(",", "")) for p in _PRICE_RE.findall(full_text)]
    pricing: Dict[str, Any] = {}
    if price_hits:
        net_usd = min(price_hits)          # lowest listed price → net estimate
        pricing = _apply_markup(net_usd, supplier=supplier)
        pricing["from_raw"] = fmt_usd(min(price_hits))
        pricing["to_raw"] = fmt_usd(max(price_hits)) if len(price_hits) > 1 else ""

    # ── Tags ────────────────────────────────────────────────────────────────
    tags: List[str] = []
    tag_signals = {
        "luxury":    ["luxury", "ultra-luxury", "suite", "butler"],
        "family":    ["family", "kids", "children"],
        "adventure": ["expedition", "adventure", "active"],
        "ocean":     ["ocean", "cruise", "ship"],
        "river":     ["river", "barge"],
        "europe":    ["mediterranean", "scandinavia", "baltic", "adriatic", "european"],
        "caribbean": ["caribbean"],
        "alaska":    ["alaska"],
        "hawaii":    ["hawaii"],
        "asia":      ["japan", "asia", "hong kong"],
    }
    for tag, signals in tag_signals.items():
        if any(s in body_lc for s in signals):
            tags.append(tag)

    # ── Cabin categories as tags ────────────────────────────────────────────
    cabin_hits = list(dict.fromkeys(m.group(0).lower() for m in _CABIN_RE.finditer(full_text)))
    tags.extend(cabin_hits)

    # Reject clearly empty extractions from unknown senders
    if not supplier and not destinations and not price_hits:
        logger.debug("extract_product_from_email: insufficient signal in email %s", msg_id)
        return None

    # ── Name: derive from subject or supplier + destinations ─────────────────
    name = subject[:80] if subject else f"{supplier or 'Vendor'} Offer"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return Product(
        product_id=_make_product_id(),
        product_type=product_type,
        supplier=supplier or "Unknown",
        name=name,
        description=body_trunc[:400].strip(),
        destinations=destinations[:15],
        dates=dates,
        pricing=pricing,
        images=[],
        source_email_id=msg_id,
        intake_date=today,
        matched_clients=[],
        tags=tags,
        status="new",
    )


def _domain_to_brand(domain: str) -> str:
    mapping = {
        "silversea.com":      "Silversea",
        "rssc.com":           "Regent Seven Seas",
        "cunard.com":         "Cunard",
        "oceania.com":        "Oceania",
        "seabourn.com":       "Seabourn",
        "vikingcruises.com":  "Viking",
        "amawaterways.com":   "AmaWaterways",
        "ponant.com":         "Ponant",
        "slh.com":            "SLH",
        "fourseasons.com":    "Four Seasons",
    }
    for k, v in mapping.items():
        if k in domain:
            return v
    parts = domain.split(".")
    return parts[-2].title() if len(parts) >= 2 else domain


# ---------------------------------------------------------------------------
# scan_vendor_emails
# ---------------------------------------------------------------------------

def scan_vendor_emails(days: int = 3) -> List[Product]:
    """Scan d2mconcierge@gmail.com for vendor/product emails in the last *days* days.

    Uses thunderbird_gmail helpers to search, parse, extract, and catalog products.
    Returns list of newly ingested Products (deduplicated against existing DB).
    """
    from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers  # type: ignore

    logger.info("Scanning vendor emails (last %d days)…", days)
    catalog = ProductCatalog()

    try:
        service = _get_gmail_service()
    except Exception as exc:
        logger.error("Gmail auth failed: %s", exc)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    after_epoch = int(cutoff.timestamp())

    domain_q = " OR ".join(f"from:@{d}" for d in VENDOR_DOMAINS)
    kw_q = " OR ".join(f'subject:"{kw}"' for kw in list(PRODUCT_KEYWORDS)[:10])
    query = f"({domain_q} OR {kw_q}) after:{after_epoch}"

    try:
        resp = (
            service.users().messages()
            .list(userId="me", q=query, maxResults=50)
            .execute()
        )
        messages = resp.get("messages", [])
    except Exception as exc:
        logger.error("Gmail search failed: %s", exc)
        return []

    logger.info("Found %d candidate vendor emails", len(messages))

    # Pre-load cataloged email IDs to skip duplicates without hitting Claude
    with catalog._conn() as conn:
        existing_ids = {
            r[0] for r in conn.execute(
                "SELECT source_email_id FROM products WHERE source_email_id IS NOT NULL"
            ).fetchall()
        }

    new_products: List[Product] = []

    for stub in messages:
        msg_id = stub["id"]
        if msg_id in existing_ids:
            logger.debug("  Skipping already-cataloged email %s", msg_id)
            continue

        try:
            msg = (
                service.users().messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            headers = _extract_headers(
                payload.get("headers", []),
                {"From", "Subject", "Date"},
            )
            body = _decode_body(payload)

            if len(body.strip()) < 80:
                logger.debug("  Skipping thin email %s (%d chars)", msg_id, len(body))
                continue

            email_data = {
                "id": msg_id,
                "subject": headers.get("Subject", ""),
                "sender": headers.get("From", ""),
                "body": body,
            }
            product = extract_product_from_email(email_data)
            if product is None:
                logger.debug("  No product signal in email %s", msg_id)
                continue

            # Run client matching before persisting
            clients = _load_dossier_clients()
            product.matched_clients = _match_product_to_clients_list(product, clients)

            if product.matched_clients:
                product.status = "matched"
            else:
                product.status = "cataloged"

            catalog.add_product(product)
            new_products.append(product)
            logger.info(
                "  + %s: %s (%s, %d client matches)",
                product.product_id, product.name,
                product.supplier, len(product.matched_clients),
            )

        except Exception as exc:
            logger.error("  Failed to process email %s: %s", msg_id, exc)

    logger.info("Scan complete: %d new products ingested", len(new_products))
    return new_products


# ---------------------------------------------------------------------------
# match_products_to_clients
# ---------------------------------------------------------------------------

def _match_product_to_clients_list(
    product: Product,
    clients: List[Dict[str, Any]],
) -> List[str]:
    """Internal: return matched client names for a single product."""
    prod_dests = {d.lower() for d in product.destinations}
    prod_tags = set(product.tags)
    supplier_lc = product.supplier.lower()
    matched: List[str] = []

    for client in clients:
        score = 0
        client_dests = {d.lower() for d in client.get("destinations", [])}
        overlap = prod_dests & client_dests
        if overlap:
            score += len(overlap) * 3
        tag_overlap = prod_tags & set(client.get("tags", []))
        if tag_overlap:
            score += len(tag_overlap) * 2
        if any(supplier_lc in s.lower() or s.lower() in supplier_lc
               for s in client.get("suppliers", [])):
            score += 4
        text_lc = client.get("text_excerpt", "").lower()
        for dest in product.destinations[:5]:
            if dest.lower() in text_lc:
                score += 2
        if score >= 3:
            matched.append(client["name"])

    return matched


def match_products_to_clients() -> List[Dict[str, Any]]:
    """Scan all new/cataloged products and match them to active clients.

    Returns list of {product, client, match_reason, match_score} dicts.
    Also persists updated matched_clients back to the DB.
    """
    catalog = ProductCatalog()
    clients = _load_dossier_clients()

    # Fetch all non-archived, unmatched products
    with catalog._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE status IN ('new', 'cataloged')"
        ).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        product = _deserialize(dict(row))
        prod_dests = {d.lower() for d in product.destinations}
        prod_tags = set(product.tags)
        supplier_lc = product.supplier.lower()

        product_matches: List[str] = []

        for client in clients:
            score = 0
            reasons: List[str] = []

            client_dests = {d.lower() for d in client.get("destinations", [])}
            overlap = prod_dests & client_dests
            if overlap:
                score += len(overlap) * 3
                reasons.append(f"destination: {', '.join(list(overlap)[:3])}")

            tag_overlap = prod_tags & set(client.get("tags", []))
            if tag_overlap:
                score += len(tag_overlap) * 2
                reasons.append(f"interests: {', '.join(tag_overlap)}")

            if any(supplier_lc in s.lower() or s.lower() in supplier_lc
                   for s in client.get("suppliers", [])):
                score += 4
                reasons.append(f"past supplier: {product.supplier}")

            text_lc = client.get("text_excerpt", "").lower()
            for dest in product.destinations[:5]:
                if dest.lower() in text_lc:
                    score += 2
                    reasons.append(f"dossier mentions {dest}")

            if score >= 3:
                product_matches.append(client["name"])
                results.append({
                    "product": product.product_id,
                    "client": client["name"],
                    "match_reason": "; ".join(reasons),
                    "match_score": score,
                })

        if product_matches:
            catalog._update_matched_clients(product.product_id, product_matches)

    logger.info("match_products_to_clients: %d match records across %d products", len(results), len(rows))
    return results


# ---------------------------------------------------------------------------
# generate_product_digest
# ---------------------------------------------------------------------------

def generate_product_digest(days: int = 7) -> str:
    """Generate a markdown morning-briefing digest of recent products.

    Groups by product_type, highlights client matches, ready for COS brief.
    """
    catalog = ProductCatalog()
    products = catalog.list_recent(days=days)

    if not products:
        return f"## D2M Product Digest — No new products in the last {days} days.\n"

    by_type: Dict[str, List[Product]] = {}
    for p in products:
        by_type.setdefault(p.product_type, []).append(p)

    lines: List[str] = [
        f"## D2M Product Digest — Last {days} Days",
        f"*{datetime.now(timezone.utc).strftime('%Y-%m-%d')} · {len(products)} products across {len(by_type)} categories*",
        "",
    ]

    type_order = ["cruise", "hotel", "tour", "excursion", "flight", "other"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for ptype in sorted_types:
        group = by_type[ptype]
        lines.append(f"### {ptype.upper()} ({len(group)})")
        for p in group:
            status_flag = "🔴 NEW" if p.status == "new" else ("✅ MATCHED" if p.status == "matched" else "")
            lines.append(f"**{p.name}** — {p.supplier}  {status_flag}")
            if p.destinations:
                lines.append(f"  Destinations: {', '.join(p.destinations[:5])}")
            if p.pricing:
                client_price = p.pricing.get("client_price_usd", "")
                if client_price:
                    lines.append(f"  Client price from: {client_price}  (markup {p.pricing.get('markup_pct', '')})")
            if p.matched_clients:
                lines.append(f"  **Client matches: {', '.join(p.matched_clients)}**")
            lines.append(f"  ID: `{p.product_id}` · Intake: {p.intake_date}")
            lines.append("")

    # Summary block
    total_matched = sum(1 for p in products if p.matched_clients)
    all_clients: Dict[str, int] = {}
    for p in products:
        for c in p.matched_clients:
            all_clients[c] = all_clients.get(c, 0) + 1

    lines.append("---")
    lines.append(f"**{total_matched}/{len(products)} products have client matches.**")
    if all_clients:
        top = sorted(all_clients.items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append("Top matched clients: " + ", ".join(f"{c} ({n})" for c, n in top))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_product_intake_tools(server):
    """Register product intake tools with the MCP server instance."""

    @server.tool()
    async def product_scan_vendors(days: int = 3) -> str:
        """Scan d2mconcierge Gmail for vendor/product emails in the last N days.

        Identifies emails from known cruise/hotel suppliers and subject-line keywords.
        Extracts product data, matches to clients, and catalogs in SQLite.
        """
        try:
            products = scan_vendor_emails(days=days)
            return json.dumps({
                "status": "ok",
                "days_scanned": days,
                "new_products": len(products),
                "products": [
                    {
                        "product_id": p.product_id,
                        "name": p.name,
                        "supplier": p.supplier,
                        "product_type": p.product_type,
                        "destinations": p.destinations,
                        "matched_clients": p.matched_clients,
                        "pricing": p.pricing,
                    }
                    for p in products
                ],
            }, indent=2)
        except Exception as exc:
            logger.error("product_scan_vendors error: %s", exc)
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def product_search(query: str, product_type: str = None) -> str:
        """Search the D2M product catalog.

        query:        Free-text search (name, description, destinations, tags).
        product_type: Optional filter — cruise | hotel | tour | flight | excursion | other.
        """
        try:
            catalog = ProductCatalog()
            products = catalog.search_products(query, product_type=product_type or None)
            return json.dumps({
                "status": "ok",
                "count": len(products),
                "products": [
                    {
                        "product_id": p.product_id,
                        "name": p.name,
                        "supplier": p.supplier,
                        "product_type": p.product_type,
                        "destinations": p.destinations,
                        "pricing": p.pricing,
                        "matched_clients": p.matched_clients,
                        "status": p.status,
                        "intake_date": p.intake_date,
                        "tags": p.tags,
                    }
                    for p in products
                ],
            }, indent=2)
        except Exception as exc:
            logger.error("product_search error: %s", exc)
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def product_match_clients() -> str:
        """Re-run client matching across all new/cataloged products.

        Reads all dossiers in ~/Thunderbird/dossiers/ and scores products
        against client destinations, interests, and supplier history.
        Returns all match records (product, client, reason, score).
        """
        try:
            matches = match_products_to_clients()
            return json.dumps({
                "status": "ok",
                "total_matches": len(matches),
                "matches": matches,
            }, indent=2)
        except Exception as exc:
            logger.error("product_match_clients error: %s", exc)
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def product_list_recent(days: int = 7) -> str:
        """List products ingested in the last N days, newest first.

        days: look-back window (default 7). Returns all product types.
        """
        try:
            catalog = ProductCatalog()
            products = catalog.list_recent(days=days)
            return json.dumps({
                "status": "ok",
                "days": days,
                "count": len(products),
                "products": [
                    {
                        "product_id": p.product_id,
                        "name": p.name,
                        "supplier": p.supplier,
                        "product_type": p.product_type,
                        "destinations": p.destinations,
                        "pricing": p.pricing,
                        "matched_clients": p.matched_clients,
                        "status": p.status,
                        "intake_date": p.intake_date,
                        "tags": p.tags,
                    }
                    for p in products
                ],
            }, indent=2)
        except Exception as exc:
            logger.error("product_list_recent error: %s", exc)
            return json.dumps({"error": str(exc)})

    @server.tool()
    async def product_digest() -> str:
        """Generate a morning-briefing digest of new products from the last 7 days.

        Groups by product type, surfaces client matches, formats as markdown.
        Suitable for Telegram brief or email to Commander.
        """
        try:
            return generate_product_digest(days=7)
        except Exception as exc:
            logger.error("product_digest error: %s", exc)
            return f"Error generating product digest: {exc}"

    logger.info(
        "Product intake tools registered: product_scan_vendors, product_search, "
        "product_match_clients, product_list_recent, product_digest"
    )


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Usage: python3 thunderbird_product_intake.py <command>")
        print("Commands:")
        print("  scan [days]      — scan vendor emails (default 3 days)")
        print("  list [days]      — list recent products (default 7 days)")
        print("  match            — re-run client matching on all unmatched products")
        print("  digest [days]    — print morning briefing digest (default 7 days)")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    catalog = ProductCatalog()

    if cmd == "scan":
        days_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        products = scan_vendor_emails(days=days_arg)
        print(f"\n{len(products)} new products ingested:")
        for p in products:
            print(f"  {p.product_id}  {p.supplier:<22} {p.name[:55]}")
            if p.matched_clients:
                print(f"             Clients: {', '.join(p.matched_clients)}")

    elif cmd == "list":
        days_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        products = catalog.list_recent(days=days_arg)
        print(f"\n{len(products)} products (last {days_arg} days):")
        for p in products:
            print(f"  {p.product_id}  [{p.status:<9}]  {p.supplier:<20} {p.name[:50]}")

    elif cmd == "match":
        matches = match_products_to_clients()
        print(f"\n{len(matches)} match records:")
        for m in matches:
            print(f"  {m['product']}  →  {m['client']}  (score {m['match_score']}): {m['match_reason']}")

    elif cmd == "digest":
        days_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print(generate_product_digest(days=days_arg))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
