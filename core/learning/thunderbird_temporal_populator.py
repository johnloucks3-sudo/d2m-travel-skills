"""
Thunderbird Temporal Populator — Dossier → Temporal Knowledge Graph
====================================================================
Reads all client dossiers in ~/Thunderbird/dossiers/*.md and extracts
temporal facts (preferences, travel dates, special occasions, cabin types,
dietary restrictions, destinations) into the temporal_facts table.

Deduplication: checks existing active facts before inserting.
Runs on startup and can be triggered on dossier change.

Usage:
    python3 thunderbird_temporal_populator.py              # Full scan
    python3 thunderbird_temporal_populator.py --dossier X  # Single dossier

Integration:
    from thunderbird_temporal_populator import populate_from_dossiers
    populate_from_dossiers()  # called at startup or on file change
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DOSSIER_DIR = Path(os.path.expanduser("~/Thunderbird/dossiers"))

# Files that are NOT client dossiers — skip these
SKIP_FILES = {
    "CLAUDE.md",
    "DANI_TESTER_BRIEFINGS.md",
    "DOSSIER_Regent_Tips_Guide.md",
}

# ---------------------------------------------------------------------------
# Entity key normalization
# ---------------------------------------------------------------------------

def _entity_key_from_filename(filename: str) -> str:
    """Derive a stable entity key from a dossier filename.

    Examples:
        Furlow_Regent_3071222.md    → furlow
        Lyons_Nancy_Ken.md         → lyons
        Loucks_Justin_Family.md    → loucks_justin
        DOSSIER_Grandeur_Scandinavia_Aug2026.md → grandeur_scandinavia
        McLeod_McGlasson_Multi.md  → mcleod
    """
    stem = filename.replace(".md", "")

    # Trip dossiers: DOSSIER_<Ship>_<Route>_<Date>
    if stem.startswith("DOSSIER_"):
        parts = stem.replace("DOSSIER_", "").split("_")
        # Take ship + route, drop date-like segments
        key_parts = [p.lower() for p in parts if not re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d{4}$', p, re.IGNORECASE)]
        return "_".join(key_parts[:2]) if key_parts else stem.lower()

    # Client dossiers: LastName_FirstName_... or LastName_Supplier_BookingNum
    parts = stem.split("_")
    last_name = parts[0].lower()

    # If second part looks like a first name (not a supplier), include it
    if len(parts) > 1:
        suppliers = {"regent", "viking", "silver", "princess", "cunard", "silversea", "personal", "multi", "family"}
        if parts[1].lower() not in suppliers and not parts[1].isdigit():
            return f"{last_name}_{parts[1].lower()}"

    return last_name


# ---------------------------------------------------------------------------
# Fact extraction patterns
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    r"(\w+ \d{1,2},?\s*\d{4})",   # March 25, 2026  or  Mar 25, 2026
    r"(\d{4}-\d{2}-\d{2})",        # 2026-03-25
]


def _parse_date_str(text: str) -> Optional[str]:
    """Try to parse a date string into ISO format."""
    text = text.strip().rstrip(",").strip()
    for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _extract_facts(entity_key: str, content: str, filename: str) -> List[Dict]:
    """Extract temporal facts from dossier content.

    Returns list of dicts ready for add_temporal_fact():
        {entity, attribute, value, valid_from, source, confidence, metadata}
    """
    facts: List[Dict] = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source = f"dossier:{filename}"

    # --- Cabin / suite preferences ---
    cabin_patterns = [
        (r'(?:cabin|suite|stateroom|category)\s*(?:type|preference)?[:\s]+([^\n|]+)', 0.85),
        (r'(?:Cabin|Suite)\s*#?\s*(\d{3,4})', 0.9),
        (r"(Penthouse|Veranda|Balcony|Concierge|Owner'?s?\s*Suite|Vista\s*Suite|Grand\s*Suite|Silver\s*Suite|Medallion\s*Suite)", 0.85),
    ]
    for pat, conf in cabin_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        for m in matches:
            val = m.strip().rstrip("|").strip()
            if val and len(val) > 2 and len(val) < 80:
                facts.append({
                    "entity": entity_key, "attribute": "cabin_preference",
                    "value": val, "valid_from": now_iso, "source": source,
                    "confidence": conf, "metadata": {"filename": filename},
                })

    # --- Dietary restrictions ---
    diet_patterns = [
        r'(?:diet(?:ary)?|allerg(?:y|ies)|food)\s*(?:restriction|preference|requirement)?[:\s]+([^\n|]+)',
        r'(?:vegetarian|vegan|gluten[- ]free|kosher|halal|lactose[- ]intolerant|no\s+\w+)',
    ]
    for pat in diet_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        for m in matches:
            val = m.strip().rstrip("|").strip() if isinstance(m, str) else m
            if val and len(val) > 2 and len(val) < 100:
                facts.append({
                    "entity": entity_key, "attribute": "dietary_restriction",
                    "value": val, "valid_from": now_iso, "source": source,
                    "confidence": 0.85, "metadata": {"filename": filename},
                })

    # --- Birthdays ---
    bday_pattern = r'(?:birthday|born|DOB|date\s+of\s+birth)[:\s]+(\w+ \d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})'
    for m in re.finditer(bday_pattern, content, re.IGNORECASE):
        parsed = _parse_date_str(m.group(1))
        if parsed:
            # Try to figure out whose birthday from surrounding text
            # Look at the 200 chars before the match for a name
            pre_context = content[max(0, m.start() - 200):m.start()]
            name_match = re.findall(r'([A-Z][a-z]+(?:\s+"[^"]+")?\s+[A-Z][a-z]+)', pre_context)
            person = name_match[-1] if name_match else entity_key
            facts.append({
                "entity": entity_key, "attribute": "birthday",
                "value": f"{person}: {parsed}", "valid_from": now_iso,
                "source": source, "confidence": 0.95,
                "metadata": {"filename": filename, "person": person},
            })

    # --- Anniversaries ---
    anniv_pattern = r'(?:anniversary|wedding\s*(?:date|anniversary))[:\s]+(\w+ \d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})'
    for m in re.finditer(anniv_pattern, content, re.IGNORECASE):
        parsed = _parse_date_str(m.group(1))
        if parsed:
            facts.append({
                "entity": entity_key, "attribute": "anniversary",
                "value": parsed, "valid_from": now_iso, "source": source,
                "confidence": 0.9, "metadata": {"filename": filename},
            })

    # --- Embarkation / travel dates ---
    travel_patterns = [
        (r'Embark(?:ation)?[:\s]+(\w+ \d{1,2},?\s*\d{4})', "embarkation_date"),
        (r'Disembark(?:ation)?[:\s]+(\w+ \d{1,2},?\s*\d{4})', "disembarkation_date"),
        (r'Final Payment[:\s]+(\w+ \d{1,2},?\s*\d{4})', "final_payment_date"),
    ]
    for pat, attr in travel_patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            parsed = _parse_date_str(m.group(1))
            if parsed:
                facts.append({
                    "entity": entity_key, "attribute": attr,
                    "value": parsed, "valid_from": now_iso, "source": source,
                    "confidence": 0.95, "metadata": {"filename": filename},
                })

    # --- Destinations ---
    dest_pattern = r'(?:Route|Destination|Itinerary)[:\s]+([^\n]+)'
    m = re.search(dest_pattern, content, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if val and len(val) > 3 and len(val) < 200:
            facts.append({
                "entity": entity_key, "attribute": "destination",
                "value": val, "valid_from": now_iso, "source": source,
                "confidence": 0.9, "metadata": {"filename": filename},
            })

    # --- Ship ---
    ship_pattern = r'(?:Ship|Vessel)[:\s]+([^\n|]+)'
    m = re.search(ship_pattern, content, re.IGNORECASE)
    if m:
        val = m.group(1).strip().rstrip("|").strip()
        if val and len(val) > 2 and len(val) < 80:
            facts.append({
                "entity": entity_key, "attribute": "ship",
                "value": val, "valid_from": now_iso, "source": source,
                "confidence": 0.95, "metadata": {"filename": filename},
            })

    # --- Service tier ---
    tier_pattern = r'(?:Service Tier|Relationship|Client Tier)[:\s|]+([^\n|]+)'
    m = re.search(tier_pattern, content, re.IGNORECASE)
    if m:
        val = m.group(1).strip().rstrip("|").strip()
        if val and len(val) > 2 and len(val) < 80:
            facts.append({
                "entity": entity_key, "attribute": "service_tier",
                "value": val, "valid_from": now_iso, "source": source,
                "confidence": 0.9, "metadata": {"filename": filename},
            })

    # --- Home location ---
    loc_pattern = r'(?:Home Location|Home|Location|Address)[:\s|]+([^\n|]+)'
    m = re.search(loc_pattern, content, re.IGNORECASE)
    if m:
        val = m.group(1).strip().rstrip("|").strip()
        if val and len(val) > 2 and len(val) < 120 and "NEEDED" not in val.upper():
            facts.append({
                "entity": entity_key, "attribute": "home_location",
                "value": val, "valid_from": now_iso, "source": source,
                "confidence": 0.85, "metadata": {"filename": filename},
            })

    return facts


# ---------------------------------------------------------------------------
# Deduplication check
# ---------------------------------------------------------------------------

def _fact_already_exists(backend, entity: str, attribute: str, value: str) -> bool:
    """Check if an active fact with the same entity+attribute+value already exists."""
    try:
        current = backend.query_fact_at_time(
            entity=entity,
            attribute=attribute,
            at_time=datetime.now(timezone.utc).isoformat(),
        )
        if current and current.get("value") == value:
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Main populator
# ---------------------------------------------------------------------------

def populate_from_dossiers(
    single_dossier: Optional[str] = None,
) -> Dict:
    """Read dossier files and store extracted facts in temporal memory.

    Args:
        single_dossier: If set, only process this one file (name or path).

    Returns:
        Summary dict: {files_scanned, facts_extracted, facts_stored, facts_skipped}
    """
    try:
        from thunderbird_temporal_memory import get_backend
    except ImportError as e:
        logger.error(f"Cannot import temporal memory backend: {e}")
        return {"error": str(e)}

    backend = get_backend()

    stats = {
        "files_scanned": 0,
        "facts_extracted": 0,
        "facts_stored": 0,
        "facts_skipped_duplicate": 0,
        "errors": 0,
    }

    if single_dossier:
        # Single dossier mode
        p = Path(single_dossier)
        if not p.exists():
            p = DOSSIER_DIR / single_dossier
        if not p.exists():
            return {"error": f"Dossier not found: {single_dossier}"}
        files = [p]
    else:
        if not DOSSIER_DIR.exists():
            logger.warning(f"Dossier directory not found: {DOSSIER_DIR}")
            return {"error": f"Directory not found: {DOSSIER_DIR}"}
        files = sorted(DOSSIER_DIR.glob("*.md"))

    for fpath in files:
        if fpath.name in SKIP_FILES:
            continue

        stats["files_scanned"] += 1

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read {fpath.name}: {e}")
            stats["errors"] += 1
            continue

        entity_key = _entity_key_from_filename(fpath.name)
        extracted = _extract_facts(entity_key, content, fpath.name)
        stats["facts_extracted"] += len(extracted)

        for fact in extracted:
            try:
                if _fact_already_exists(backend, fact["entity"], fact["attribute"], fact["value"]):
                    stats["facts_skipped_duplicate"] += 1
                    continue

                backend.add_temporal_fact(
                    entity=fact["entity"],
                    attribute=fact["attribute"],
                    value=fact["value"],
                    valid_from=fact["valid_from"],
                    source=fact["source"],
                    confidence=fact["confidence"],
                    metadata=fact.get("metadata"),
                )
                stats["facts_stored"] += 1
            except Exception as e:
                logger.warning(f"Failed to store fact {fact['entity']}.{fact['attribute']}: {e}")
                stats["errors"] += 1

    logger.info(
        f"Temporal populator complete: {stats['files_scanned']} files, "
        f"{stats['facts_extracted']} extracted, {stats['facts_stored']} stored, "
        f"{stats['facts_skipped_duplicate']} skipped (duplicate)"
    )
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    dossier_arg = None
    if "--dossier" in sys.argv:
        idx = sys.argv.index("--dossier")
        if idx + 1 < len(sys.argv):
            dossier_arg = sys.argv[idx + 1]

    result = populate_from_dossiers(single_dossier=dossier_arg)
    print(json.dumps(result, indent=2))
