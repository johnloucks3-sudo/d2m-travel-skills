"""
Cruise Intel Pipeline — Shared Utilities
parse_date, norm_ship, find_match, region filter, ship-line lookup
"""
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from config import MONTH_MAP, EUROPE_MED_KEYWORDS, PONANT_EXCLUDE_PORTS, SHIP_LINE_MAP


# ── Date parsing ───────────────────────────────────────────────────────────────

def parse_date(ds: str) -> Optional[date]:
    """
    Parse date strings from all four sources into a date object.
    Handles: '18 Oct 2026', 'Oct 3, 2026', '2026-10-18', 'October 3-10 2026',
             'October 31 November 7 2026', '10/03/26'
    """
    if not ds:
        return None
    ds = str(ds).strip()

    for fmt in ('%d %b %Y', '%b %d, %Y', '%Y-%m-%d', '%m/%d/%y', '%d/%m/%y'):
        try:
            return datetime.strptime(ds, fmt).date()
        except ValueError:
            pass

    # Cross-month range: "October 31 November 7 2026" — take first date
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2})[-–]', ds)
    if m and m.group(1) in MONTH_MAP:
        return date(2026, MONTH_MAP[m.group(1)], int(m.group(2)))

    m = re.match(r'([A-Za-z]+)\s+(\d{1,2})\s+[A-Za-z]', ds)
    if m and m.group(1) in MONTH_MAP:
        return date(2026, MONTH_MAP[m.group(1)], int(m.group(2)))

    return None


# ── Ship name normalization ────────────────────────────────────────────────────

VESSEL_PREFIXES = [
    'M/V ', 'M.V. ', 'MV ', 'MS ', 'SS ', 'S/V ', 'SV ',
    'RY ', 'MY ', 'M/S ', 'ms ', 'mv ',
]

# Canonical aliases: map non-standard names → canonical form for cross-source matching.
# Keys are lowercased partial or full ship names; values are the canonical lowercased form.
_SHIP_ALIASES: dict[str, str] = {
    'seadream cruise 1': 'seadream i',
    'seadream cruise 2': 'seadream ii',
    # Generic "seadream" (from seadream.com gstack — no ship number) maps to the prefix
    # so it can match either vessel when find_match uses startswith logic.
    # NOTE: don't alias 'seadream' itself — keep it as-is so find_match can fuzzy-match.
}

def norm_ship(name: str) -> str:
    """Strip vessel prefixes, apply canonical aliases, lowercase for dedup matching."""
    if not name:
        return ''
    n = str(name).strip()
    for pfx in VESSEL_PREFIXES:
        if n.startswith(pfx):
            n = n[len(pfx):]
            break
    n = n.lower().strip()
    return _SHIP_ALIASES.get(n, n)


# ── Cross-source matching ──────────────────────────────────────────────────────

def find_match(
    ship_norm: str,
    dep_date: Optional[date],
    entries: List[Dict[str, Any]],
    tolerance: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Find an existing entry matching ship name + departure date within tolerance days.
    Dedup key: normalized ship + date ±1 day. Never match on route strings.
    """
    if not dep_date:
        return None
    for e in entries:
        e_norm = e.get('ship_norm', '')
        # Exact match OR prefix match for generic names (e.g. "seadream" matches "seadream i")
        if e_norm == ship_norm or e_norm.startswith(ship_norm + ' ') or ship_norm.startswith(e_norm + ' '):
            e_date = e.get('departure_date_obj')
            if e_date and abs((dep_date - e_date).days) <= tolerance:
                return e
    return None


# ── Region filter ──────────────────────────────────────────────────────────────

_SOUTHERN_HEMISPHERE_EXCLUDE = (
    'antarctica', 'antarctic', 'falkland', 'south georgia',
    'ushuaia', 'patagonia', 'tierra del fuego', 'south shetland',
    'south pole', 'drake passage',
)

def is_europe_med_arctic(from_port: str, to_port: str, route_name: str = '') -> bool:
    """Return True if any port or route text matches European/Med/Arctic keywords.
    Explicit exclusion: Southern Hemisphere expedition keywords win over 'arctic' substring.
    """
    text = (from_port + ' ' + to_port + ' ' + route_name).lower()
    if any(ex in text for ex in _SOUTHERN_HEMISPHERE_EXCLUDE):
        return False
    return any(kw in text for kw in EUROPE_MED_KEYWORDS)


def is_ponant_excluded(from_port: str, to_port: str) -> bool:
    """Return True if voyage should be excluded from Ponant results."""
    combined = (from_port + ' ' + to_port).lower()
    return any(ex in combined for ex in PONANT_EXCLUDE_PORTS)


# ── Ship-to-line lookup ────────────────────────────────────────────────────────

def resolve_cruise_line(ship_name: str, fallback: str = '') -> str:
    """
    Look up cruise line from ship name using SHIP_LINE_MAP.
    Returns fallback if no match found.
    """
    for key, line in SHIP_LINE_MAP.items():
        if ship_name.startswith(key) or key in ship_name:
            return line
    return fallback


# ── Flag normalization ─────────────────────────────────────────────────────────

def normalize_flag(val) -> str:
    """Normalize source presence flags to 'Y' or ''."""
    if val in (True, 'YES', 'Y', '1', 'True', 'true', 1):
        return 'Y'
    return ''


# ── Progress printer ──────────────────────────────────────────────────────────

def progress(i: int, total: int, label: str, extra: str = '') -> None:
    pct = int(100 * i / total) if total else 0
    bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
    suffix = f'  {extra}' if extra else ''
    print(f'\r[{bar}] {pct:3d}%  [{i:3d}/{total}]  {label[:50]}{suffix}', end='', flush=True)
    if i == total:
        print()
