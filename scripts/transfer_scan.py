#!/usr/bin/env python3
"""
transfer_scan.py — Pre/Post-Cruise Transfer Price Scanner
===========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Promoted from test_transfer_scrapers.py + smoke_test_transfer_sites.py
scaffolding. Checks transfer options (airport→port, port→airport, etc.)
for bookings in the transfer window (≤90 days out) using Anansi.

Replaces Playwright-based kiwitaxi/welcomepickups scrapers (bot-walled)
with Anansi web search — same data signal, no browser dependency.
Consumed by Arc4-D lifecycle touchpoint.

Schedule: Daily via systemd timer (transfer-scan.timer)
State:    OpsCenter/state/transfer_scan_state.json
Log:      logs/transfer_scan.log
"""

import json
import logging
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
ANANSI = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "anansi")
DOSSIERS_DIR = THUNDERBIRD_ROOT / "dossiers"
STATE_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "state" / "transfer_scan_state.json"
LOG_PATH = THUNDERBIRD_ROOT / "logs" / "transfer_scan.log"

# ── Config ────────────────────────────────────────────────────────────────────
# Arc4-D transfer planning window: 30–90 days before departure
WINDOW_NEAR_DAYS = 90    # don't scan beyond this
WINDOW_FAR_DAYS = 0      # scan all bookings in the future (up to NEAR)
# Anansi timeout
ANANSI_TIMEOUT = 45
# Default pax for price lookups
DEFAULT_PAX = 2

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TRANSFER-SCAN] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_PATH)),
    ],
)
log = logging.getLogger(__name__)


# ── Dossier Parsing ───────────────────────────────────────────────────────────

def _parse_date(s: str) -> date | None:
    if not s:
        return None
    s = str(s).strip().strip('"\'')
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def _extract_field(text: str, *keys: str) -> str | None:
    for key in keys:
        m = re.search(rf'^{re.escape(key)}:\s*(.+)$', text, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"\'')
    return None


def _extract_embarkation_city(text: str) -> str | None:
    """Get embarkation city — port where cruise begins."""
    city = _extract_field(text, "embark_port", "embarkation_port", "embarkation_city")
    if city:
        return city
    # Narrative pattern: "Embarkation: August 29, 2026 — Stockholm, Sweden"
    m = re.search(r'Embarkation[:\s]+[^\n]*?—\s*([A-Za-z\s]+),', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_disembarkation_city(text: str) -> str | None:
    """Get disembarkation city — port where cruise ends."""
    city = _extract_field(text, "disembark_port", "disembarkation_port", "disembarkation_city")
    if city:
        return city
    m = re.search(r'Disembarkation[:\s]+[^\n]*?—\s*([A-Za-z\s]+),', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_origin_city(text: str) -> str | None:
    """Get client's home/origin city for transfer pricing (where they fly from)."""
    # Frontmatter fields
    city = _extract_field(text, "home_city", "origin_city", "home_airport", "home_port")
    if city:
        return city
    # Common patterns in dossier body: "flies from Denver", "home airport: DEN"
    m = re.search(r'(?:home airport|flies from|origin)[:\s]+([A-Z]{3})', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def enumerate_transfer_bookings() -> list[dict]:
    """
    Enumerate dossiers with upcoming departures in the transfer window.
    Returns list of booking dicts.
    """
    today = date.today()
    horizon = today + timedelta(days=WINDOW_NEAR_DAYS)
    bookings = []
    seen_keys: set[str] = set()

    for md_file in sorted(DOSSIERS_DIR.glob("*.md")):
        if md_file.name.upper() == "CLAUDE.md":
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            log.warning("Cannot read %s: %s", md_file.name, e)
            continue

        dep_str = _extract_field(text, "departure")
        if not dep_str or dep_str == "[REQUIRED] YYYY-MM-DD":
            continue
        dep = _parse_date(dep_str)
        if not dep:
            continue
        # Must be in future and within window
        if dep <= today or dep > horizon:
            continue

        ret_str = _extract_field(text, "return", "disembark", "return_date", "disembarkation_date")
        ret = _parse_date(ret_str) if ret_str else None

        embark_city = _extract_embarkation_city(text)
        disembark_city = _extract_disembarkation_city(text)
        origin_city = _extract_origin_city(text)
        client_name = md_file.stem.replace("DOSSIER_", "").replace("_", " ")

        key = f"{dep}|{embark_city or ''}|{md_file.stem}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        bookings.append({
            "dossier": md_file.name,
            "client_name": client_name,
            "departure": str(dep),
            "return_date": str(ret) if ret else None,
            "embark_city": embark_city,
            "disembark_city": disembark_city,
            "origin_city": origin_city,
        })
        log.info("  Transfer window booking: %s dep=%s embark=%s", md_file.stem, dep, embark_city)

    return bookings


# ── Anansi Search ─────────────────────────────────────────────────────────────

def search_transfer_price(
    from_loc: str,
    to_loc: str,
    travel_date: str,
    pax: int = DEFAULT_PAX,
) -> dict:
    """
    Use Anansi to price a transfer route. Never raises.
    """
    query = (
        f"private transfer {from_loc} to {to_loc} {travel_date} "
        f"{pax} passengers USD price sedan or van"
    )
    try:
        proc = subprocess.run(
            [ANANSI, query],
            capture_output=True, text=True, timeout=ANANSI_TIMEOUT,
            cwd=str(THUNDERBIRD_ROOT),
        )
        snippet = (proc.stdout or "").strip()[:800]
        status = "ok" if snippet else "empty"
        return {
            "from": from_loc,
            "to": to_loc,
            "date": travel_date,
            "pax": pax,
            "query": query,
            "snippet": snippet,
            "status": status,
            "rc": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        log.warning("Anansi timeout for %s→%s", from_loc, to_loc)
        return {"from": from_loc, "to": to_loc, "status": "timeout", "snippet": "", "rc": -1}
    except FileNotFoundError:
        log.warning("Anansi binary not found")
        return {"from": from_loc, "to": to_loc, "status": "anansi_missing", "snippet": "", "rc": -1}
    except Exception as e:
        log.warning("Anansi error %s→%s: %s", from_loc, to_loc, e)
        return {"from": from_loc, "to": to_loc, "status": "error", "snippet": str(e)[:200], "rc": -1}


# ── Main Scan ─────────────────────────────────────────────────────────────────

def run_scan() -> dict:
    """
    Run the full transfer scan. Returns state dict written to STATE_FILE.
    Never raises.
    """
    run_ts = datetime.now(timezone.utc).isoformat()
    log.info("Transfer scan started at %s", run_ts)

    bookings = []
    try:
        bookings = enumerate_transfer_bookings()
    except Exception as e:
        log.error("enumerate_transfer_bookings failed: %s", e)

    routes_checked: list[dict] = []

    for bk in bookings:
        dep = bk["departure"]
        ret = bk["return_date"]
        embark = bk.get("embark_city")
        disembark = bk.get("disembark_city")
        origin = bk.get("origin_city")

        # Airport → Embarkation port (pre-cruise inbound)
        if embark:
            # Use airport near embark city if no explicit origin
            from_loc = f"{embark} airport" if not origin else f"{origin} airport → {embark}"
            to_loc = f"{embark} cruise terminal"
            result = search_transfer_price(from_loc, to_loc, dep)
            routes_checked.append({
                "type": "inbound_transfer",
                "booking": bk["dossier"],
                "client": bk["client_name"],
                "route": f"{from_loc} → {to_loc}",
                "date": dep,
                "anansi": result,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            })
            log.info("  Inbound: %s → %s (%s): %s", from_loc, to_loc, dep, result["status"])

        # Disembarkation port → Airport (post-cruise outbound)
        if disembark and ret:
            from_loc = f"{disembark} cruise terminal"
            to_loc = f"{disembark} airport"
            result = search_transfer_price(from_loc, to_loc, ret)
            routes_checked.append({
                "type": "outbound_transfer",
                "booking": bk["dossier"],
                "client": bk["client_name"],
                "route": f"{from_loc} → {to_loc}",
                "date": ret,
                "anansi": result,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            })
            log.info("  Outbound: %s → %s (%s): %s", from_loc, to_loc, ret, result["status"])

    state = {
        "last_run": run_ts,
        "bookings_found": len(bookings),
        "routes_checked": len(routes_checked),
        "in_window_bookings": bookings,
        "results": routes_checked,
    }

    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
        log.info("State written to %s", STATE_FILE)
    except Exception as e:
        log.error("Failed to write state: %s", e)

    log.info(
        "Transfer scan complete. Bookings: %d. Routes checked: %d.",
        len(bookings), len(routes_checked)
    )
    return state


def main() -> int:
    try:
        state = run_scan()
        print(
            f"transfer_scan: {state.get('bookings_found', 0)} bookings, "
            f"{state.get('routes_checked', 0)} routes checked."
        )
        return 0
    except Exception as e:
        log.error("transfer_scan FATAL: %s", e)
        print(f"transfer_scan ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
