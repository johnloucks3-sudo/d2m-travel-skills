#!/usr/bin/env python3
"""Cruise Discovery inquiry handler — MISSION-804 Dani integration.

Detects a cruise-discovery inquiry in an inbound client email (subject+body),
extracts destination/months/line/party-size, queries the master cruise DB via
scripts/query_cruise_db.py, and returns a structured context block for
injection into Dani's AGGREGATE phase.

Never sends anything itself. Never talks to a client. Pure data lookup —
consumed by thunderbird_dani_email.py's _phase_aggregate(), which feeds it
into the ARTIST phase as context, ahead of the existing COS-review /
draft-only ADVOCATE gate. See docs/cruise_discovery_client_workflow_20260702.md.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERY_SCRIPT = REPO_ROOT / "scripts" / "query_cruise_db.py"

TRIGGER_KEYWORDS = ("cruise", "sailing", "destination")

REGIONS = [
    "Mediterranean", "Caribbean", "Alaska", "Norway", "Scandinavia",
    "Asia & Pacific", "Asia", "Pacific", "Antarctica", "South America",
    "Transatlantic", "Northern Europe", "Baltic", "Middle East",
]

LINES = [
    "Regent Seven Seas Cruises", "Regent", "Silversea Cruises", "Silversea",
    "Seabourn", "Viking Ocean", "Viking", "Oceania Cruises", "Oceania",
    "Crystal Cruises", "PONANT", "Ritz-Carlton Yacht Collection",
    "Atlas Ocean Voyages", "Paul Gauguin Cruises",
]

MONTH_NAMES = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
)


def is_cruise_discovery_inquiry(subject: str, body: str) -> bool:
    text = f"{subject}\n{body}".lower()
    return any(kw in text for kw in TRIGGER_KEYWORDS)


def _extract_region(text: str) -> Optional[str]:
    for region in REGIONS:
        if region.lower() in text:
            return region
    return None


def _extract_line(text: str) -> Optional[str]:
    for line in LINES:
        if line.lower() in text:
            return line
    return None


def _extract_months(text: str) -> Optional[str]:
    found = [m for m in MONTH_NAMES if re.search(rf"\b{m}[a-z]*\b", text)]
    return " ".join(found) if found else None


def _extract_party_size(text: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,2})\s*(?:guests|people|pax|of us|passengers)\b", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\bparty of\s*(\d{1,2})\b", text)
    if m:
        return int(m.group(1))
    return None


def extract_params(subject: str, body: str) -> dict:
    text = f"{subject}\n{body}".lower()
    return {
        "destination": _extract_region(text),
        "months": _extract_months(text),
        "line": _extract_line(text),
        "party_size": _extract_party_size(text),
    }


def query_matches(destination=None, months=None, line=None, limit=5) -> list:
    if not any([destination, months, line]):
        return []

    cmd = [sys.executable, str(QUERY_SCRIPT), "--limit", str(limit)]
    if destination:
        cmd += ["--destination", destination]
    if months:
        cmd += ["--months", months]
    if line:
        cmd += ["--line", line]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        if isinstance(data, dict) and data.get("error"):
            return []
        return data if isinstance(data, list) else []
    except Exception:
        return []


def build_context_block(subject: str, body: str) -> Optional[str]:
    """Returns a context block string for Dani's AGGREGATE phase, or None
    if this email isn't a cruise-discovery inquiry / no matches found.

    No prices in DB — matches are itinerary-only. Dani surfaces top options
    and offers a 2-hour pricing follow-up per the workflow doc; she does not
    quote a price from this block.
    """
    if not is_cruise_discovery_inquiry(subject, body):
        return None

    params = extract_params(subject, body)
    matches = query_matches(
        destination=params["destination"],
        months=params["months"],
        line=params["line"],
        limit=5,
    )
    if not matches:
        return None

    lines = ["[CRUISE DISCOVERY MATCHES — master_cruise.db, no prices]"]
    if params["party_size"]:
        lines.append(f"Party size mentioned: {params['party_size']}")
    for m in matches:
        lines.append(
            f"- {m.get('line', '')} {m.get('ship', '')} — "
            f"{m.get('departure', 'date TBD')}, {m.get('nights', '?')} nights, "
            f"{m.get('route', '')} ({m.get('region', '')})"
        )
    lines.append(
        "No pricing in DB. If client wants pricing, tell them D2M will have "
        "pricing within 2 hours (Centrav/Perx/direct portal per SLA) — "
        "do not invent a price."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    # Manual smoke test
    subj = "Mediterranean cruise in May?"
    bod = "Hi, we're a party of 6 looking for a Silversea Mediterranean sailing in May 2027. Any options?"
    block = build_context_block(subj, bod)
    print(block or "No match / not a cruise-discovery inquiry.")
