#!/usr/bin/env python3
"""
rules_classifier.py
===================
Dreams2Memories Travel, LLC — Thunderbird Wing

ZERO-MODEL, RULES-FIRST email classifier (ELON incubator brief, P0).

Doctrine (Commander directive 2026-07-01):
  * NO model calls in the background/hot path. classify() is PURE — first-match-wins
    over a registry loaded from a local cache. It never touches the network and never
    invokes an LLM.
  * The client + supplier whitelist is authoritative:
      - PRIMARY source  = EARA Google Sheet ("EARA D2M Thunderbird v2")
      - BACKUP/fallback = dossier scan + hardcoded SUPPLIER_DOMAINS
        (from core.email.thunderbird_commander_inbox), used only when the sheet is
        unreachable AND no usable cache exists.
  * AI (deep_classify) is ON-DEMAND ONLY — never called from a background loop.

Author: Sterling (A7) — MISSION-ELON-INCUBATOR · 2026-07-01
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths / constants ───────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path(__file__).resolve().parents[2]

EARA_SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"  # EARA D2M Thunderbird v2
SERVICE_ACCOUNT_FILE = THUNDERBIRD_DIR / ".service_account_gemini.json"
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

REGISTRY_CACHE_PATH = THUNDERBIRD_DIR / "config" / "email_registry_cache.json"
REGISTRY_TTL_HOURS = 12

# Tabs / header names — verified live 2026-07-01 (match by HEADER NAME, not index)
CLIENT_TABS = (
    ("Registry_Clients", "Email"),
    ("Clients", "Email"),
)
SUPPLIER_TAB = "Reference_Suppliers"
SUPPLIER_DOMAIN_HEADER = "Domain (e.g. rssc.com)"
SUPPLIER_ACTIVE_HEADER = "Active (Yes/No)"

# ── Wing / self addresses ────────────────────────────────────────────────────
WING_ADDRESSES = {
    "d2mconcierge@gmail.com",
    "johnloucks3@gmail.com",
    "concierge@d2mluxury.quest",
    "d2m.concierge@gmail.com",
    "dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com",
}
WING_DOMAIN = "d2mluxury.quest"  # NOTE: gmail.com is NOT internal — prospects live there.

# ── Command-prefix detection (mirrors classify_email in commander_inbox) ─────
_CMD_RE = re.compile(r"^(cos|coo|hale|vic)\W", re.IGNORECASE)
_RE_FWD_RE = re.compile(r"^(re:|fwd:|fw:)\s*", re.IGNORECASE)

# ── Keyword sets ─────────────────────────────────────────────────────────────
_BOOKING_KW = (
    "booking confirmation", "reservation confirmed", "confirmation", "confirmed",
    "booking", "reservation", "itinerary", "e-ticket", "e-document",
    "final documents", "cruise confirmation", "your trip", "booking ref",
)
_INVOICE_KW = (
    "commission", "invoice", "payment", "remittance", "statement",
    "override", "net rate", "override check", "charge", "receipt",
)
_INTEL_KW = (
    "travel advisory", "port closure", "hurricane", "strike", "visa",
    "entry requirement", "isw", "intel",
)

# Positive client-inquiry signals — ported from classify_email() in
# core/email/thunderbird_commander_inbox.py (client_inquiry_signals list).
_CLIENT_INQUIRY_SIGNALS = (
    "i want to book", "we are interested in", "looking for a quote",
    "can you help with", "do you have availability",
    "please send me", "i need a hotel", "we need flights",
    "our family wants to", "hello dani", "dear dani", "hi john", "dear john",
    "questions about", "can you recommend", "looking for recommendations",
    "what options", "would like to discuss", "can we schedule a call",
    "schedule a time",
)

# Extended promo/newsletter regex — ported from scripts/triage_client_inquiry_noise.py
EXTENDED_PROMO = re.compile(
    r"(newsmax|dunkin|arbys|@costco|\.costco\.|anytimefitness|condenast|"
    r"rocketmoney|allrecipes|pointsguy|cruisecritic|teapartypatriots|"
    r"claremont\.org|spacewarfare|pwrmobile|exploringtwdc|justthenews|"
    r"@campaigns\.|@emails?\.|@email\.|@eml\.|@latest\.|@digital\.|"
    r"@emailinfo\.|@info\.)",
    re.IGNORECASE,
)

# ── Import canonical noise regex + dossier/hardcoded fallbacks (read-only) ──
# Import is best-effort and side-effect-free (no network, no cache read here).
try:
    from core.email.thunderbird_commander_inbox import (  # type: ignore
        _NOISE_PATTERNS,
        SUPPLIER_DOMAINS as _HARDCODED_SUPPLIER_DOMAINS,
    )
except Exception as e:  # pragma: no cover — module unavailable
    logger.debug("commander inbox helpers unavailable: %s — using minimal fallback", e)
    _NOISE_PATTERNS = re.compile(
        r"(no-?reply|noreply|newsletter|unsubscribe|@notification|@substack\.com)",
        re.IGNORECASE,
    )
    _HARDCODED_SUPPLIER_DOMAINS = {
        "silversea.com", "rssc.com", "regent.com", "viking.com", "cunard.com",
        "oceaniacruises.com", "seabourn.com",
    }


# ══════════════════════════════════════════════════════════════════════════════
# A. Registry loader
# ══════════════════════════════════════════════════════════════════════════════

# Module-level cached registry — loaded lazily on first classify(registry=None).
_MODULE_REGISTRY: dict | None = None


def _col_values_by_header(rows: list[list[str]], header: str) -> list[str]:
    """Return the column under `header` (row 1 = headers). Empty list if not found."""
    if not rows:
        return []
    headers = rows[0]
    try:
        idx = headers.index(header)
    except ValueError:
        return []
    return [r[idx] for r in rows[1:] if len(r) > idx]


def _fetch_from_sheet() -> dict:
    """Live pull from the EARA sheet. Raises on any failure (caller handles fallback).

    Isolated as its own function so tests can monkeypatch the network seam.
    """
    import gspread
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SHEETS_SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(EARA_SHEET_ID)

    client_emails: set[str] = set()
    for tab, header in CLIENT_TABS:
        try:
            rows = sh.worksheet(tab).get_all_values()
        except Exception as e:
            logger.warning("EARA tab %s unreadable: %s", tab, e)
            continue
        for val in _col_values_by_header(rows, header):
            v = (val or "").strip().lower()
            if v and "@" in v:
                client_emails.add(v)

    supplier_domains: set[str] = set()
    try:
        rows = sh.worksheet(SUPPLIER_TAB).get_all_values()
        headers = rows[0] if rows else []
        d_idx = headers.index(SUPPLIER_DOMAIN_HEADER) if SUPPLIER_DOMAIN_HEADER in headers else None
        a_idx = headers.index(SUPPLIER_ACTIVE_HEADER) if SUPPLIER_ACTIVE_HEADER in headers else None
        for r in rows[1:]:
            if d_idx is None or len(r) <= d_idx:
                continue
            domain = (r[d_idx] or "").strip().lower()
            if not domain:
                continue
            active = (r[a_idx].strip().lower() if a_idx is not None and len(r) > a_idx else "yes")
            if active == "yes":
                supplier_domains.add(domain)
    except Exception as e:
        logger.warning("EARA %s tab unreadable: %s", SUPPLIER_TAB, e)

    return {"client_emails": client_emails, "supplier_domains": supplier_domains}


def _load_from_dossiers() -> dict:
    """Backup source: dossier scan for clients + hardcoded supplier domains."""
    client_emails: set[str] = set()
    try:
        from core.email.thunderbird_commander_inbox import (  # type: ignore
            _populate_client_addresses,
            CLIENT_ADDRESSES,
        )
        _populate_client_addresses()
        client_emails = {e.lower() for e in CLIENT_ADDRESSES if e and "@" in e}
    except Exception as e:  # pragma: no cover — defensive
        logger.debug("dossier client scan unavailable: %s", e)
    supplier_domains = {d.lower().strip() for d in _HARDCODED_SUPPLIER_DOMAINS}
    return {"client_emails": client_emails, "supplier_domains": supplier_domains}


def _read_cache(cache_path: Path) -> dict | None:
    """Return cached registry if present + younger than TTL, else None."""
    try:
        if not cache_path.exists():
            return None
        data = json.loads(cache_path.read_text())
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600.0
        if age_h > REGISTRY_TTL_HOURS:
            return None
        return {
            "client_emails": {e.lower() for e in data.get("client_emails", [])},
            "supplier_domains": {d.lower() for d in data.get("supplier_domains", [])},
        }
    except Exception as e:
        logger.debug("registry cache read failed: %s", e)
        return None


def _write_cache(cache_path: Path, registry: dict) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "client_emails": sorted(registry["client_emails"]),
            "supplier_domains": sorted(registry["supplier_domains"]),
        }, indent=2))
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("registry cache write failed: %s", e)


def load_registry(force_refresh: bool = False, cache_path: Path | None = None) -> dict:
    """Return {"client_emails": set, "supplier_domains": set} (all lowercased).

    Zero-network hot path: reads the local cache if present and younger than
    REGISTRY_TTL_HOURS. Refreshes from the EARA sheet only when stale or
    force_refresh=True. On a successful sheet fetch, the cache is overwritten.

    Fallback order when a sheet refresh is needed:
      1. EARA sheet (PRIMARY)
      2. existing cache (even if stale) — better than nothing
      3. dossier scan + hardcoded supplier domains (BACKUP)
    Never raises — always returns a usable (possibly smaller) registry.
    """
    cp = cache_path or REGISTRY_CACHE_PATH

    if not force_refresh:
        cached = _read_cache(cp)
        if cached is not None:
            logger.debug("registry: using fresh cache (%s)", cp)
            return cached

    # Need a refresh: try the sheet first.
    try:
        registry = _fetch_from_sheet()
        _write_cache(cp, registry)
        logger.info(
            "registry: loaded from EARA sheet (%d clients, %d suppliers)",
            len(registry["client_emails"]), len(registry["supplier_domains"]),
        )
        return registry
    except Exception as e:
        logger.warning("registry: EARA sheet unreachable (%s) — trying fallbacks", e)

    # Sheet failed. Try any existing cache (even if stale) before dossiers.
    try:
        if cp.exists():
            data = json.loads(cp.read_text())
            reg = {
                "client_emails": {e.lower() for e in data.get("client_emails", [])},
                "supplier_domains": {d.lower() for d in data.get("supplier_domains", [])},
            }
            if reg["client_emails"] or reg["supplier_domains"]:
                logger.warning("registry: using STALE cache after sheet failure")
                return reg
    except Exception:
        pass

    # Last resort: dossiers + hardcoded suppliers.
    logger.warning("registry: falling back to dossier scan + hardcoded suppliers")
    return _load_from_dossiers()


def refresh_registry_cache() -> dict:
    """Force a sheet pull, overwrite the cache, and print counts. CLI --refresh."""
    reg = load_registry(force_refresh=True)
    print(
        f"Registry refreshed: {len(reg['client_emails'])} clients, "
        f"{len(reg['supplier_domains'])} suppliers → {REGISTRY_CACHE_PATH}"
    )
    return reg


def _get_registry(registry: dict | None) -> dict:
    """Resolve the registry for a classify() call: explicit arg, else module cache."""
    global _MODULE_REGISTRY
    if registry is not None:
        return registry
    if _MODULE_REGISTRY is None:
        _MODULE_REGISTRY = load_registry()
    return _MODULE_REGISTRY


# ══════════════════════════════════════════════════════════════════════════════
# B. classify — PURE, no network, no model
# ══════════════════════════════════════════════════════════════════════════════

def _sender_domain(sender_lower: str) -> str:
    return sender_lower.split("@")[-1] if "@" in sender_lower else ""


def _domain_matches(sender_lower: str, domains: set[str]) -> bool:
    """Domain equality / suffix match — NOT substring (blocks silversea.com@evil.com)."""
    dom = _sender_domain(sender_lower)
    for d in domains:
        if dom == d or sender_lower.endswith("@" + d):
            return True
    return False


def classify(sender: str, subject: str, body: str = "", registry: dict | None = None) -> str:
    """Classify an email. PURE — no network, no LLM call in this path.

    Ordered, first-match-wins. Categories:
      commander_directive | direct_command | internal_wing | booking_confirmation |
      financial | supplier_intel | client_inquiry | intel | spam | other
    """
    reg = _get_registry(registry)
    client_emails = reg.get("client_emails", set())
    supplier_domains = reg.get("supplier_domains", set())

    sender_lower = (sender or "").lower().strip()
    subject_raw = (subject or "").strip()
    subject_lower = subject_raw.lower()
    body_stripped = (body or "").strip()
    text_lower = subject_lower + " " + body_stripped.lower()

    # 1. Command prefixes win over the internal_wing self-address return.
    subj_de = _RE_FWD_RE.sub("", subject_raw)
    if subject_lower.startswith("cos, ") or subject_lower.startswith("hale, "):
        return "commander_directive"
    if _CMD_RE.match(subj_de) or _CMD_RE.match(body_stripped):
        return "direct_command"

    # Internal / self — wing addresses + @d2mluxury.quest ONLY (gmail.com is NOT internal).
    domain = _sender_domain(sender_lower)
    if sender_lower in WING_ADDRESSES or domain == WING_DOMAIN:
        return "internal_wing"

    # 2. Booking / invoice by subject keyword — BEFORE the noise short-circuit,
    #    so noreply@ confirmations survive (same rationale as email_ingestion_pipeline).
    if any(k in subject_lower for k in _INVOICE_KW):
        return "financial"
    if any(k in subject_lower for k in _BOOKING_KW):
        return "booking_confirmation"

    # 3. Noise fast-path → spam (canonical regex + extended promo).
    if _NOISE_PATTERNS.search(sender_lower) or EXTENDED_PROMO.search(sender_lower):
        return "spam"

    # 4. Registry supplier domain → financial / booking / supplier_intel.
    if _domain_matches(sender_lower, supplier_domains):
        if any(k in text_lower for k in _INVOICE_KW):
            return "financial"
        if any(k in text_lower for k in _BOOKING_KW):
            return "booking_confirmation"
        return "supplier_intel"

    # 5. Registry client email → client_inquiry (strongest positive signal).
    if sender_lower in client_emails:
        return "client_inquiry"

    # 6. Intel keywords.
    if any(k in subject_lower for k in _INTEL_KW):
        return "intel"

    # 7. Strong client-inquiry signals AND sender not noise/promo.
    is_noise = bool(_NOISE_PATTERNS.search(sender_lower) or EXTENDED_PROMO.search(sender_lower))
    if any(sig in text_lower for sig in _CLIENT_INQUIRY_SIGNALS) and not is_noise:
        return "client_inquiry"

    # 8. Default.
    return "other"


# ══════════════════════════════════════════════════════════════════════════════
# C. Helpers
# ══════════════════════════════════════════════════════════════════════════════

_D2M_RELEVANT = {
    "client_inquiry", "booking_confirmation", "financial",
    "commander_directive", "direct_command",
}


def is_d2m_relevant(category: str) -> bool:
    """True for categories that warrant a downstream (e.g. Telegram) alert.

    Telegram wiring is intentionally NOT done here — this only exposes the predicate.
    """
    return category in _D2M_RELEVANT


def deep_classify(sender: str, subject: str, body: str) -> str:
    """OPTIONAL AI classification path — ON-DEMAND ONLY.

    ⚠️ This function MAY call Gemini (a network + model round-trip). It MUST NEVER
    be called from a background loop or the classify() hot path. It exists solely
    for explicit, on-demand disambiguation of messages that rules mark as `other`.
    """
    try:
        import google.generativeai as genai  # imported inside the body on purpose
        import os
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return classify(sender, subject, body)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        cats = ("commander_directive direct_command internal_wing booking_confirmation "
                "financial supplier_intel client_inquiry intel spam other")
        prompt = (
            "Classify this email into EXACTLY ONE category. Reply with only the category.\n"
            f"Categories: {cats}\n\n"
            f"From: {sender}\nSubject: {subject}\n\n{body[:800]}"
        )
        resp = model.generate_content(prompt)
        cat = (resp.text or "").strip().lower().split()[0] if resp.text else "other"
        return cat if cat in cats.split() else classify(sender, subject, body)
    except Exception as e:
        logger.warning("deep_classify failed (%s) — falling back to rules", e)
        return classify(sender, subject, body)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Rules-first email classifier")
    ap.add_argument("--refresh", action="store_true", help="Force EARA sheet pull, refresh cache, print counts")
    args = ap.parse_args()
    if args.refresh:
        refresh_registry_cache()
    else:
        ap.print_help()
