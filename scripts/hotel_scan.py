#!/usr/bin/env python3
"""
hotel_scan.py — Pre/Post-Cruise Hotel Price Scanner
=====================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Scans for hotel pricing opportunities near active booking embarkation/
disembarkation ports within the hotel-scan window (≤120 days out).
Uses Anansi (Wing default web tool) — no paid API, no Playwright.
Fails SOFT: logs errors, writes state, never raises.

Schedule: Daily via systemd timer (hotel-scan.timer)
State:    OpsCenter/state/hotel_scan_state.json
Log:      logs/hotel_scan.log
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
STATE_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "state" / "hotel_scan_state.json"
LOG_PATH = THUNDERBIRD_ROOT / "logs" / "hotel_scan.log"

# ── Config ────────────────────────────────────────────────────────────────────
# Scan window: bookings departing within this many days
WINDOW_DAYS = 120
# Hotel stay duration (nights pre-cruise or post-cruise)
HOTEL_NIGHTS = 1
# Anansi query timeout
ANANSI_TIMEOUT = 45

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HOTEL-SCAN] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_PATH)),
    ],
)
log = logging.getLogger(__name__)


# ── Dossier Parsing ───────────────────────────────────────────────────────────

def _parse_date(s: str) -> date | None:
    """Parse YYYY-MM-DD with optional surrounding quotes."""
    if not s:
        return None
    s = s.strip().strip('"\'')
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def _extract_field(text: str, *keys: str) -> str | None:
    """Extract value from 'key: value' line (YAML-like frontmatter or inline)."""
    for key in keys:
        m = re.search(rf'^{re.escape(key)}:\s*(.+)$', text, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"\'')
    return None


def _extract_embarkation_port(text: str) -> str | None:
    """Extract embarkation port city from dossier narrative or frontmatter."""
    # Check frontmatter first
    port = _extract_field(text, "embark_port", "embarkation_port", "embarkation_city")
    if port:
        return port
    # Parse "Embarkation: Month DD, YYYY — City, Country" pattern
    m = re.search(r'Embarkation[:\s]+[^\n]*?—\s*([A-Za-z\s]+),', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_disembarkation_port(text: str) -> str | None:
    """Extract disembarkation port city from dossier narrative or frontmatter."""
    port = _extract_field(text, "disembark_port", "disembarkation_port", "disembarkation_city")
    if port:
        return port
    m = re.search(r'Disembarkation[:\s]+[^\n]*?—\s*([A-Za-z\s]+),', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_return_date(text: str) -> date | None:
    """Extract return/disembarkation date from dossier."""
    val = _extract_field(text, "return", "disembark", "disembarkation_date", "return_date")
    if val:
        return _parse_date(val)
    return None


def enumerate_active_bookings() -> list[dict]:
    """
    Scan all dossier .md files for active bookings with departure dates
    within the scan window. Returns list of booking dicts with:
      - dossier, departure, return_date, embark_port, disembark_port, client_name
    """
    today = date.today()
    horizon = today + timedelta(days=WINDOW_DAYS)
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

        ret = _extract_return_date(text)
        embark_port = _extract_embarkation_port(text)
        disembark_port = _extract_disembarkation_port(text)

        # Client name heuristic from filename
        client_name = md_file.stem.replace("DOSSIER_", "").replace("_", " ")

        # Deduplicate by (departure, embark_port)
        key = f"{dep}|{embark_port or ''}|{md_file.stem}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        bookings.append({
            "dossier": md_file.name,
            "client_name": client_name,
            "departure": str(dep),
            "return_date": str(ret) if ret else None,
            "embark_port": embark_port,
            "disembark_port": disembark_port,
        })
        log.info("  Found booking: %s dep=%s port=%s", md_file.stem, dep, embark_port)

    return bookings


# ── Anansi Search ─────────────────────────────────────────────────────────────

def search_hotel_price(city: str, check_in: str, check_out: str, guests: int = 2) -> dict:
    """
    Use Anansi to search for hotel prices in a city for given dates.
    Returns dict with snippet and status; never raises.
    """
    query = (
        f"hotel price {city} check in {check_in} check out {check_out} "
        f"{guests} guests USD per night luxury hotel"
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
            "query": query,
            "snippet": snippet,
            "status": status,
            "rc": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        log.warning("Anansi timeout for city=%s", city)
        return {"query": query, "snippet": "", "status": "timeout", "rc": -1}
    except FileNotFoundError:
        log.warning("Anansi binary not found at %s", ANANSI)
        return {"query": query, "snippet": "", "status": "anansi_missing", "rc": -1}
    except Exception as e:
        log.warning("Anansi error for city=%s: %s", city, e)
        return {"query": query, "snippet": "", "status": "error", "rc": -1}


# ── Main Scan ─────────────────────────────────────────────────────────────────

def run_scan() -> dict:
    """
    Run the full hotel scan. Returns state dict for STATE_FILE.
    Never raises — all errors are logged and reflected in state.
    """
    run_ts = datetime.now(timezone.utc).isoformat()
    log.info("Hotel scan started at %s", run_ts)

    bookings = []
    try:
        bookings = enumerate_active_bookings()
    except Exception as e:
        log.error("enumerate_active_bookings failed: %s", e)

    windows: list[dict] = []

    for booking in bookings:
        dep = booking["departure"]
        ret = booking["return_date"]
        embark_port = booking.get("embark_port")
        disembark_port = booking.get("disembark_port")

        # Pre-cruise: night before embarkation
        if embark_port and dep:
            try:
                dep_dt = date.fromisoformat(dep)
                pre_checkin = str(dep_dt - timedelta(days=1))
                pre_checkout = str(dep_dt)
                result = search_hotel_price(embark_port, pre_checkin, pre_checkout)
                windows.append({
                    "type": "pre_cruise",
                    "booking": booking["dossier"],
                    "client": booking["client_name"],
                    "port": embark_port,
                    "check_in": pre_checkin,
                    "check_out": pre_checkout,
                    "anansi": result,
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                })
                log.info("  Pre-cruise %s: %s → status=%s", embark_port, dep, result["status"])
            except Exception as e:
                log.warning("Pre-cruise scan error for %s: %s", booking["dossier"], e)
                windows.append({
                    "type": "pre_cruise",
                    "booking": booking["dossier"],
                    "client": booking["client_name"],
                    "port": embark_port,
                    "check_in": None,
                    "check_out": dep,
                    "anansi": {"status": "error", "snippet": str(e)},
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                })

        # Post-cruise: night after disembarkation
        if disembark_port and ret:
            try:
                ret_dt = date.fromisoformat(ret)
                post_checkin = str(ret_dt)
                post_checkout = str(ret_dt + timedelta(days=1))
                result = search_hotel_price(disembark_port, post_checkin, post_checkout)
                windows.append({
                    "type": "post_cruise",
                    "booking": booking["dossier"],
                    "client": booking["client_name"],
                    "port": disembark_port,
                    "check_in": post_checkin,
                    "check_out": post_checkout,
                    "anansi": result,
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                })
                log.info("  Post-cruise %s: %s → status=%s", disembark_port, ret, result["status"])
            except Exception as e:
                log.warning("Post-cruise scan error for %s: %s", booking["dossier"], e)

    state = {
        "last_run": run_ts,
        "bookings_found": len(bookings),
        "windows_scanned": len(windows),
        "in_window_bookings": bookings,
        "results": windows,
    }

    # Write state — soft fail if can't write
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
        log.info("State written to %s", STATE_FILE)
    except Exception as e:
        log.error("Failed to write state: %s", e)

    log.info(
        "Hotel scan complete. Bookings in window: %d. Windows scanned: %d.",
        len(bookings), len(windows)
    )
    return state


def main() -> int:
    try:
        state = run_scan()
        windows = state.get("windows_scanned", 0)
        bookings = state.get("bookings_found", 0)
        print(f"hotel_scan: {bookings} bookings in window, {windows} hotel windows scanned.")
        return 0
    except Exception as e:
        log.error("hotel_scan FATAL: %s", e)
        print(f"hotel_scan ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
