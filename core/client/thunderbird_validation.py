"""
Thunderbird Trip Validation Pipeline
======================================

Two-tier validation using Claude Haiku MAX (fast) for email sweeps and Claude
Sonnet MAX (smart) for gap analysis. Ensures every booking segment is confirmed
before final payment or embarkation.

Architecture:
  1. CLAUDE MAX HAIKU PASS 1 — Email sweep: search Gmail for all booking-
     related emails per client, extract found segments into structured JSON
  2. SONNET PASS — Gap matrix: compare required segments (from REQUIRED_SEGMENTS
     template) against found segments, produce a gap report
   3. CLAUDE MAX SONNET PASS 2 — Targeted re-search: for each gap, Sonnet searches
      Gmail with narrower queries to find missing confirmations
  4. OUTPUT — Final validation report (dict + optional branded HTML draft)

Usage:
    from thunderbird_validation import validate_client, validate_all_active

    # Single client
    report = validate_client("furlow", voyage_type="cruise_10day")

    # All active clients
    reports = validate_all_active()

Standalone:  python3 thunderbird_validation.py --client furlow
Scheduler:   from thunderbird_validation import validate_all_active

Dependencies: thunderbird_gmail.py, thunderbird_model_router.py
"""

import json
import logging
import re
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

from adapters.claude_max_oauth import haiku_adapter, sonnet_adapter
from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIERS_DIR = THUNDERBIRD_DIR / "Dossiers"
VALIDATION_DIR = THUNDERBIRD_DIR / "validations"
VALIDATION_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Required Segments Templates
# ---------------------------------------------------------------------------

# The complete list of what a couple needs for a cruise trip.
# Each segment has: category, name, required (bool), notes

REQUIRED_SEGMENTS = {
    "cruise_standard": [
        # === PRE-CRUISE ===
        {"category": "documents",  "segment": "Passports valid 6+ months",    "required": True},
        {"category": "documents",  "segment": "Visa / entry requirements",    "required": True},
        {"category": "insurance",  "segment": "Travel insurance policy",      "required": True},
        {"category": "flights",    "segment": "Outbound flight leg 1",        "required": True},
        {"category": "flights",    "segment": "Outbound flight leg 2",        "required": False,  "notes": "If connecting"},
        {"category": "flights",    "segment": "Outbound seat assignments",    "required": False,  "notes": "Nice to have"},
        {"category": "transfers",  "segment": "Airport → hotel transfer",     "required": True},
        {"category": "hotel",      "segment": "Pre-cruise hotel (night 1)",   "required": True},
        {"category": "hotel",      "segment": "Pre-cruise hotel (night 2)",   "required": False,  "notes": "If multi-night pre"},
        {"category": "hotel",      "segment": "Pre-cruise hotel (night 3)",   "required": False,  "notes": "If multi-night pre"},
        {"category": "transfers",  "segment": "Hotel → port transfer",       "required": True},
        # === CRUISE ===
        {"category": "cruise",     "segment": "Cruise booking confirmed",     "required": True},
        {"category": "cruise",     "segment": "Suite/cabin assignment",       "required": True},
        {"category": "cruise",     "segment": "Cruise paid in full",          "required": True,   "notes": "Or final payment date known"},
        {"category": "dining",     "segment": "Specialty dining reserved",    "required": False,  "notes": "If available"},
        {"category": "excursions", "segment": "Shore excursions booked",      "required": False,  "notes": "Per port"},
        {"category": "cruise",     "segment": "Embarkation details",         "required": False},
        # === POST-CRUISE ===
        {"category": "transfers",  "segment": "Port → airport transfer",     "required": True},
        {"category": "hotel",      "segment": "Post-cruise hotel",           "required": False,  "notes": "If not flying same day"},
        {"category": "transfers",  "segment": "Hotel → airport transfer",    "required": False,  "notes": "If post hotel"},
        {"category": "flights",    "segment": "Return flight leg 1",         "required": True},
        {"category": "flights",    "segment": "Return flight leg 2",         "required": False,  "notes": "If connecting"},
        {"category": "flights",    "segment": "Return seat assignments",     "required": False},
        # === ADMIN ===
        {"category": "admin",      "segment": "Emergency contacts on file",  "required": False},
        {"category": "admin",      "segment": "Portal activated",            "required": False},
        {"category": "admin",      "segment": "Client dossier current",      "required": True},
    ],

    "cruise_with_pre_post": [
        # === DOCUMENTS ===
        {"category": "documents",  "segment": "Passports valid 6+ months",       "required": True},
        {"category": "documents",  "segment": "Visa / entry requirements",       "required": True},
        {"category": "documents",  "segment": "Visit Japan Web (if Japan)",      "required": False},
        {"category": "insurance",  "segment": "Travel insurance policy",         "required": True},
        # === OUTBOUND FLIGHTS ===
        {"category": "flights",    "segment": "Outbound flight leg 1",           "required": True},
        {"category": "flights",    "segment": "Outbound flight leg 2",           "required": False},
        {"category": "flights",    "segment": "Outbound seat assignments",       "required": False},
        {"category": "flights",    "segment": "Outbound PNR / e-ticket",        "required": True},
        # === PRE-CRUISE (3 days) ===
        {"category": "transfers",  "segment": "Airport → pre-hotel transfer",   "required": True},
        {"category": "hotel",      "segment": "Pre-cruise hotel night 1",        "required": True},
        {"category": "hotel",      "segment": "Pre-cruise hotel night 2",        "required": False},
        {"category": "hotel",      "segment": "Pre-cruise hotel night 3",        "required": False},
        {"category": "excursions", "segment": "Pre-cruise day 1 activity",       "required": False},
        {"category": "excursions", "segment": "Pre-cruise day 2 activity",       "required": False},
        {"category": "excursions", "segment": "Pre-cruise day 3 activity",       "required": False},
        {"category": "dining",     "segment": "Pre-cruise dinner reservations",  "required": False},
        {"category": "transfers",  "segment": "Hotel → port transfer",          "required": True},
        # === CRUISE ===
        {"category": "cruise",     "segment": "Cruise booking confirmed",        "required": True},
        {"category": "cruise",     "segment": "Suite/cabin assignment",          "required": True},
        {"category": "cruise",     "segment": "Cruise payment status",           "required": True},
        {"category": "cruise",     "segment": "Embarkation time & port",         "required": True},
        {"category": "dining",     "segment": "Embarkation night dining",        "required": False},
        {"category": "dining",     "segment": "Specialty dining reservations",   "required": False},
        {"category": "excursions", "segment": "Shore excursions (per port)",     "required": False},
        {"category": "cruise",     "segment": "Spa / wellness bookings",        "required": False},
        {"category": "cruise",     "segment": "Disembarkation details",         "required": False},
        # === POST-CRUISE (3 days) ===
        {"category": "transfers",  "segment": "Port → post-hotel transfer",     "required": True},
        {"category": "hotel",      "segment": "Post-cruise hotel night 1",       "required": False},
        {"category": "hotel",      "segment": "Post-cruise hotel night 2",       "required": False},
        {"category": "hotel",      "segment": "Post-cruise hotel night 3",       "required": False},
        {"category": "excursions", "segment": "Post-cruise day 1 activity",      "required": False},
        {"category": "excursions", "segment": "Post-cruise day 2 activity",      "required": False},
        {"category": "excursions", "segment": "Post-cruise day 3 activity",      "required": False},
        {"category": "dining",     "segment": "Post-cruise dinner reservations", "required": False},
        {"category": "transfers",  "segment": "Post-hotel → airport transfer",  "required": True},
        # === RETURN FLIGHTS ===
        {"category": "flights",    "segment": "Return flight leg 1",             "required": True},
        {"category": "flights",    "segment": "Return flight leg 2",             "required": False},
        {"category": "flights",    "segment": "Return seat assignments",         "required": False},
        {"category": "flights",    "segment": "Return PNR / e-ticket",          "required": True},
        # === ADMIN ===
        {"category": "admin",      "segment": "Emergency contacts on file",     "required": False},
        {"category": "admin",      "segment": "Portal activated",               "required": False},
        {"category": "admin",      "segment": "Client dossier current",         "required": True},
    ],
}

# ---------------------------------------------------------------------------
# Validation Schedule — Active 2026 Voyages
# ---------------------------------------------------------------------------
# Monthly validations on the booking-anniversary day-of-month,
# FINAL validation at T-14 days before departure.

VALIDATION_SCHEDULE = [
    {
        "client": "loucks",
        "voyage": "Silver Nova Pacific (Personal)",
        "departure": date(2026, 4, 10),
        "final_validation": date(2026, 3, 27),
        "booking_dom": 10,  # day-of-month for monthly validations
        "monthly_validations": [
            date(2026, 3, 10),  # Mar — current month
        ],
    },
    {
        "client": "westbrook",
        "voyage": "Silver Nova Pacific",
        "departure": date(2026, 4, 21),
        "final_validation": date(2026, 4, 7),
        "booking_dom": 21,
        "monthly_validations": [
            date(2026, 3, 21),
        ],
    },
    {
        "client": "mcleod",
        "voyage": "Silver Muse Mediterranean",
        "departure": date(2026, 6, 18),
        "final_validation": date(2026, 6, 4),
        "booking_dom": 25,  # booked Feb 25, 2025
        "monthly_validations": [
            date(2026, 3, 25),
            date(2026, 4, 25),
            date(2026, 5, 25),
        ],
    },
    {
        "client": "furlow",
        "voyage": "Regent Scandinavia (group: Furlow, Ely, Nichols)",
        "departure": date(2026, 8, 26),
        "final_validation": date(2026, 8, 12),
        "booking_dom": 1,  # aligned with Apr 1 FPD
        "monthly_validations": [
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
            date(2026, 7, 1),
            date(2026, 8, 1),
        ],
    },
    {
        "client": "ely",
        "voyage": "Regent Scandinavia (with Furlow group)",
        "departure": date(2026, 8, 26),
        "final_validation": date(2026, 8, 12),
        "booking_dom": 1,
        "monthly_validations": [
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
            date(2026, 7, 1),
            date(2026, 8, 1),
        ],
    },
    {
        "client": "nichols",
        "voyage": "Regent Scandinavia (with Furlow group)",
        "departure": date(2026, 8, 26),
        "final_validation": date(2026, 8, 12),
        "booking_dom": 1,
        "monthly_validations": [
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
            date(2026, 7, 1),
            date(2026, 8, 1),
        ],
    },
    {
        "client": "kuklinski",
        "voyage": "Viking Mars Panama Canal",
        "departure": date(2026, 12, 17),
        "final_validation": date(2026, 12, 3),
        "booking_dom": 15,
        "monthly_validations": [
            date(2026, 4, 15),
            date(2026, 5, 15),
            date(2026, 6, 15),
            date(2026, 7, 15),
            date(2026, 8, 15),
            date(2026, 9, 15),
            date(2026, 10, 15),
            date(2026, 11, 15),
        ],
    },
    {
        "client": "mcleod_regent",
        "voyage": "Regent SS Grandeur Lesser Antilles",
        "departure": date(2026, 12, 19),
        "final_validation": date(2026, 12, 5),
        "booking_dom": 19,
        "monthly_validations": [
            date(2026, 7, 19),
            date(2026, 8, 19),
            date(2026, 9, 19),
            date(2026, 10, 19),
            date(2026, 11, 19),
        ],
    },
    {
        "client": "loucks_regent",
        "voyage": "Regent SS Grandeur Miami→LA",
        "departure": date(2026, 12, 29),
        "final_validation": date(2026, 12, 15),
        "booking_dom": 29,
        "monthly_validations": [
            date(2026, 7, 29),
            date(2026, 8, 29),
            date(2026, 9, 29),
            date(2026, 10, 29),
            date(2026, 11, 29),
        ],
    },
]


def get_upcoming_validations(within_days: int = 30) -> List[Dict]:
    """Return validations due within the next N days."""
    today = date.today()
    cutoff = today + timedelta(days=within_days)
    upcoming = []

    for entry in VALIDATION_SCHEDULE:
        # Check final validation
        fv = entry["final_validation"]
        if today <= fv <= cutoff:
            upcoming.append({
                "client": entry["client"],
                "voyage": entry["voyage"],
                "date": fv.isoformat(),
                "type": "FINAL",
                "departure": entry["departure"].isoformat(),
                "days_to_departure": (entry["departure"] - today).days,
            })

        # Check monthly validations
        for mv in entry.get("monthly_validations", []):
            if today <= mv <= cutoff:
                upcoming.append({
                    "client": entry["client"],
                    "voyage": entry["voyage"],
                    "date": mv.isoformat(),
                    "type": "monthly",
                    "departure": entry["departure"].isoformat(),
                    "days_to_departure": (entry["departure"] - today).days,
                })

    upcoming.sort(key=lambda x: x["date"])
    return upcoming


# Client registry — maps last name to known search terms and dossier
CLIENT_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _load_client_registry() -> Dict[str, Dict[str, Any]]:
    """Build client registry from dossier files."""
    registry = {}
    if not DOSSIERS_DIR.is_dir():
        return registry
    for f in DOSSIERS_DIR.glob("*.md"):
        parts = f.stem.split("_")
        if parts:
            key = parts[0].lower()
            registry[key] = {
                "dossier_path": str(f),
                "dossier_name": f.stem,
                "search_names": [parts[0]],  # Will be enriched
            }
    return registry


# ---------------------------------------------------------------------------
# CLAUDE MAX HAIKU PASS 1 — Email Sweep
# ---------------------------------------------------------------------------

SWEEP_SYSTEM_PROMPT = """You are a travel booking extraction specialist for Dreams2Memories Travel, LLC.

Given a batch of email snippets for a specific client, extract ALL booking segments you can find.

Return a JSON array where each element is:
{
  "category": "flights|hotel|transfers|cruise|insurance|excursions|dining|documents|admin",
  "segment": "brief description matching the required segments list",
  "status": "confirmed|pending|cancelled|unknown",
  "details": "key details: confirmation #, dates, amounts, seat assignments, etc.",
  "source_subject": "email subject line where this was found"
}

RULES:
- Extract EVERY booking segment — flights, hotels, transfers, cruise, insurance, excursions, dining
- Include confirmation numbers, PNRs, booking references whenever visible
- Include seat assignments for flights
- Include dates, times, amounts
- Return ONLY valid JSON array. No markdown fences, no explanation.
- If no segments found, return []"""


def _search_gmail_for_client(service, client_name: str,
                              extra_terms: Optional[List[str]] = None,
                              max_results: int = 30) -> List[Dict]:
    """Search Gmail for all booking-related emails for a client."""
    # Build search queries
    queries = [
        f"from:{client_name}",
        f"to:{client_name}",
        f"subject:{client_name}",
        f"{client_name} booking",
        f"{client_name} confirmation",
        f"{client_name} reservation",
    ]
    if extra_terms:
        for term in extra_terms:
            queries.append(f"{client_name} {term}")

    seen_ids = set()
    emails = []

    for query in queries:
        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            for msg_stub in results.get("messages", []):
                if msg_stub["id"] not in seen_ids:
                    seen_ids.add(msg_stub["id"])
                    msg = service.users().messages().get(
                        userId="me", id=msg_stub["id"], format="full"
                    ).execute()
                    payload = msg.get("payload", {})
                    headers = _extract_headers(
                        payload.get("headers", []),
                        {"From", "To", "Subject", "Date"}
                    )
                    body = _decode_body(payload)
                    if len(body) > 4000:
                        body = body[:4000] + "\n...[TRUNCATED]"
                    emails.append({
                        "id": msg["id"],
                        "headers": headers,
                        "body": body,
                    })
        except Exception as e:
            logger.warning("Gmail search failed for query '%s': %s", query, e)

    logger.info("Found %d unique emails for client '%s'", len(emails), client_name)
    return emails


def _haiku_extract_segments(emails: List[Dict], client_name: str) -> List[Dict]:
    """Send emails to Claude Haiku MAX in batches for segment extraction."""
    if not emails:
        return []

    all_segments = []
    batch_size = 5  # Process 5 emails at a time to stay within context

    for i in range(0, len(emails), batch_size):
        batch = emails[i:i + batch_size]

        # Build email summaries for the batch
        email_text = ""
        for idx, email in enumerate(batch, 1):
            h = email["headers"]
            email_text += f"\n--- EMAIL {idx} ---\n"
            email_text += f"From: {h.get('From', '?')}\n"
            email_text += f"To: {h.get('To', '?')}\n"
            email_text += f"Date: {h.get('Date', '?')}\n"
            email_text += f"Subject: {h.get('Subject', '(no subject)')}\n"
            email_text += f"Body:\n{email['body']}\n"

        user = f"CLIENT: {client_name}\n\nEMAILS:\n{email_text}"

        try:
            result = haiku_adapter.dispatch(
                system=SWEEP_SYSTEM_PROMPT, user=user,
                max_tokens=2000,
            )
            if result.error:
                logger.error("Haiku extraction failed in batch %d: %s", i, result.error)
                continue

            raw = result.text.strip()
            # Strip markdown fences
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            segments = json.loads(raw)
            if isinstance(segments, list):
                all_segments.extend(segments)
            logger.info("Haiku extracted %d segments from batch %d-%d",
                       len(segments) if isinstance(segments, list) else 0,
                       i + 1, min(i + batch_size, len(emails)))
        except json.JSONDecodeError as e:
            logger.error("Haiku returned invalid JSON in batch %d: %s", i, e)
        except Exception as e:
            logger.error("Haiku extraction failed in batch %d: %s", i, e)

    return all_segments


# ---------------------------------------------------------------------------
# DOSSIER EXTRACTION — Parse existing dossier for known segments
# ---------------------------------------------------------------------------

def _extract_dossier_segments(dossier_path: str) -> List[Dict]:
    """Parse a dossier markdown file and extract known booking segments."""
    try:
        content = Path(dossier_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Failed to read dossier %s: %s", dossier_path, e)
        return []

    segments = []

    # Extract flights
    flight_pattern = re.compile(
        r'\|\s*(OUT|RET)\s*\d?\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|',
        re.IGNORECASE
    )
    for m in flight_pattern.finditer(content):
        direction = "Outbound" if "OUT" in m.group(1).upper() else "Return"
        flight = m.group(2).strip()
        route = m.group(3).strip()
        depart = m.group(4).strip()
        arrive = m.group(5).strip()
        seats = m.group(6).strip()
        leg = "leg 1" if "1" in m.group(1) or m.group(1).strip() in ("OUT", "RET") else "leg 2"

        segments.append({
            "category": "flights",
            "segment": f"{direction} flight {leg}",
            "status": "confirmed",
            "details": f"{flight} {route} dep {depart} arr {arrive}" + (f" seats {seats}" if seats and seats != "—" else ""),
            "source_subject": "dossier",
        })

    # Extract PNRs
    pnr_match = re.search(r'\*\*PNR[s]?:\*\*\s*(.+)', content)
    if pnr_match:
        segments.append({
            "category": "flights",
            "segment": "Outbound PNR / e-ticket",
            "status": "confirmed",
            "details": pnr_match.group(1).strip(),
            "source_subject": "dossier",
        })
        segments.append({
            "category": "flights",
            "segment": "Return PNR / e-ticket",
            "status": "confirmed",
            "details": pnr_match.group(1).strip(),
            "source_subject": "dossier",
        })

    # Extract hotel bookings
    hotel_pattern = re.compile(
        r'\|\s*([^|]*\d[^|]*)\s*\|\s*([^|]*(?:Hotel|Haymarket|Hilton|Scandic|Baglioni)[^|]*)\s*\|',
        re.IGNORECASE
    )
    for m in hotel_pattern.finditer(content):
        segments.append({
            "category": "hotel",
            "segment": "Pre-cruise hotel night 1",
            "status": "confirmed",
            "details": f"Booking {m.group(1).strip()}: {m.group(2).strip()}",
            "source_subject": "dossier",
        })

    # Extract transfers
    transfer_pattern = re.compile(
        r'\|\s*([^|]*\d[^|]*)\s*\|\s*([^|]*[Tt]ransfer[^|]*)\s*\|',
        re.IGNORECASE
    )
    for m in transfer_pattern.finditer(content):
        segments.append({
            "category": "transfers",
            "segment": "Airport → hotel transfer",
            "status": "confirmed",
            "details": f"Booking {m.group(1).strip()}: {m.group(2).strip()}",
            "source_subject": "dossier",
        })

    # Extract cruise booking
    if re.search(r'(?:Regent|Silversea|Oceania|Viking|Cunard)', content, re.IGNORECASE):
        suite_match = re.search(r'Suite\s+(\d+)', content)
        booking_match = re.search(r'Booking\s+(\d+)', content)
        segments.append({
            "category": "cruise",
            "segment": "Cruise booking confirmed",
            "status": "confirmed",
            "details": f"Booking {booking_match.group(1) if booking_match else '?'}, Suite {suite_match.group(1) if suite_match else '?'}",
            "source_subject": "dossier",
        })

    # Extract insurance
    if re.search(r'(?:Allianz|insurance|CFAR)', content, re.IGNORECASE):
        ins_match = re.search(r'(?:Allianz|insurance)[^.]*', content, re.IGNORECASE)
        segments.append({
            "category": "insurance",
            "segment": "Travel insurance policy",
            "status": "confirmed" if "confirmed" in content.lower() or "paid" in content.lower() else "pending",
            "details": ins_match.group(0).strip() if ins_match else "Insurance mentioned",
            "source_subject": "dossier",
        })

    # Extract passports
    if re.search(r'passport.*(?:confirmed|verified|expires|renewed)', content, re.IGNORECASE):
        segments.append({
            "category": "documents",
            "segment": "Passports valid 6+ months",
            "status": "confirmed",
            "details": "Passport verified per dossier",
            "source_subject": "dossier",
        })

    return segments


# ---------------------------------------------------------------------------
# SONNET PASS — Gap Matrix Analysis
# ---------------------------------------------------------------------------

GAP_MATRIX_SYSTEM_PROMPT = """You are a senior travel operations analyst for Dreams2Memories Travel, LLC.

You will receive:
1. A list of REQUIRED segments for this trip type
2. A list of FOUND segments (from email sweep + dossier)

Your job: produce a gap analysis matrix. For each required segment, determine if it was found, partially found, or missing.

Return a JSON object:
{
  "client": "client name",
  "analysis_date": "YYYY-MM-DD",
  "total_required": N,
  "total_found": N,
  "total_missing": N,
  "total_partial": N,
  "coverage_pct": N,
  "segments": [
    {
      "category": "flights|hotel|transfers|cruise|insurance|excursions|dining|documents|admin",
      "segment": "segment name from required list",
      "required": true/false,
      "status": "found|partial|missing|not_applicable",
      "matched_detail": "detail from found segment or null",
      "gap_note": "what's missing or needs verification, or null",
      "search_suggestion": "Gmail search query to find this, or null"
    }
  ],
  "critical_gaps": ["list of missing REQUIRED segments"],
  "recommendations": ["list of action items"]
}

RULES:
- Match found segments to required segments using semantic similarity, not exact match
- A found segment with incomplete info (e.g., flight without seat assignment) = "partial"
- Be thorough — every required segment must appear in the output
- For missing segments, suggest a specific Gmail search query that might find it
- Return ONLY valid JSON. No markdown fences."""


def _sonnet_gap_analysis(client_name: str, required: List[Dict],
                          found: List[Dict]) -> Dict:
    """Send required + found segments to Claude Sonnet for gap analysis."""
    query = f"""CLIENT: {client_name}
ANALYSIS DATE: {datetime.now().strftime('%Y-%m-%d')}

REQUIRED SEGMENTS:
{json.dumps(required, indent=2)}

FOUND SEGMENTS (from email sweep + dossier):
{json.dumps(found, indent=2)}

Produce the gap analysis matrix.
Return ONLY valid JSON. No markdown fences, no explanations outside the JSON."""

    try:
        adapter_result = sonnet_adapter.dispatch(
            system=GAP_MATRIX_SYSTEM_PROMPT, user=query,
            max_tokens=4000,
        )
        if adapter_result.error:
            raise RuntimeError(adapter_result.error)

        raw = adapter_result.text.strip()
        # Strip markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        logger.info("Sonnet gap analysis: %d required, %d found, %d missing, %d partial",
                    parsed.get("total_required", 0),
                    parsed.get("total_found", 0),
                    parsed.get("total_missing", 0),
                    parsed.get("total_partial", 0))
        return parsed

    except json.JSONDecodeError as e:
        logger.error("Sonnet returned invalid JSON: %s\nRaw: %s", e, raw[:500])
        return {"error": f"JSON parse failed: {e}", "raw": raw[:500]}
    except Exception as e:
        logger.error("Sonnet gap analysis failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# CLAUDE MAX SONNET PASS 2 — Targeted Re-Search for Gaps
# ---------------------------------------------------------------------------

TARGETED_SEARCH_PROMPT = """You are searching for a specific missing travel booking segment.

Given the search results (email snippets), determine if the missing segment is present.

Return JSON:
{
  "found": true/false,
  "status": "confirmed|pending|not_found",
  "details": "extracted details or null",
  "source_subject": "email subject where found, or null"
}

Return ONLY valid JSON."""


def _sonnet_targeted_search(service, client_name: str,
                             gaps: List[Dict]) -> List[Dict]:
    """For each gap with a search_suggestion, run a targeted Gmail search + Claude Sonnet MAX."""
    results = []

    for gap in gaps:
        search_query = gap.get("search_suggestion")
        if not search_query:
            results.append({
                "segment": gap.get("segment", "?"),
                "found": False,
                "status": "not_found",
                "details": "No search query suggested",
            })
            continue

        # Search Gmail
        try:
            gmail_results = service.users().messages().list(
                userId="me", q=search_query, maxResults=5
            ).execute()

            messages = gmail_results.get("messages", [])
            if not messages:
                results.append({
                    "segment": gap.get("segment", "?"),
                    "found": False,
                    "status": "not_found",
                    "details": f"No results for: {search_query}",
                })
                continue

            # Read the messages and send to Claude Sonnet MAX
            email_text = ""
            for msg_stub in messages[:3]:
                msg = service.users().messages().get(
                    userId="me", id=msg_stub["id"], format="full"
                ).execute()
                payload = msg.get("payload", {})
                headers = _extract_headers(
                    payload.get("headers", []),
                    {"From", "To", "Subject", "Date"}
                )
                body = _decode_body(payload)
                if len(body) > 2000:
                    body = body[:2000]
                email_text += f"\nFrom: {headers.get('From', '?')}\n"
                email_text += f"Subject: {headers.get('Subject', '?')}\n"
                email_text += f"Body:\n{body}\n---\n"

            user = f"LOOKING FOR: {gap.get('segment', '?')}\nCLIENT: {client_name}\n\nEMAILS:\n{email_text}"

            adapter_result = sonnet_adapter.dispatch(
                system=TARGETED_SEARCH_PROMPT, user=user,
                max_tokens=300,
            )
            if adapter_result.error:
                raise RuntimeError(adapter_result.error)

            raw = adapter_result.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
            result["segment"] = gap.get("segment", "?")
            results.append(result)

        except Exception as e:
            logger.error("Targeted search failed for '%s': %s",
                        gap.get("segment", "?"), e)
            results.append({
                "segment": gap.get("segment", "?"),
                "found": False,
                "status": "error",
                "details": str(e),
            })

    return results


# ---------------------------------------------------------------------------
# Validation Report Generator
# ---------------------------------------------------------------------------

def _merge_research_into_matrix(gap_matrix: Dict,
                                 research_results: List[Dict]) -> Dict:
    """Update gap matrix with results from targeted re-search."""
    # Build lookup from research
    research_map = {}
    for r in research_results:
        research_map[r.get("segment", "")] = r

    # Update segments in the matrix
    for seg in gap_matrix.get("segments", []):
        if seg.get("status") in ("missing", "partial"):
            match = research_map.get(seg.get("segment", ""))
            if match and match.get("found"):
                seg["status"] = "found"
                seg["matched_detail"] = match.get("details", "")
                seg["gap_note"] = f"Found in re-search: {match.get('source_subject', '?')}"

    # Recalculate totals
    segments = gap_matrix.get("segments", [])
    found = sum(1 for s in segments if s.get("status") == "found")
    missing = sum(1 for s in segments if s.get("status") == "missing" and s.get("required"))
    partial = sum(1 for s in segments if s.get("status") == "partial")
    total_req = sum(1 for s in segments if s.get("required"))

    gap_matrix["total_found"] = found
    gap_matrix["total_missing"] = missing
    gap_matrix["total_partial"] = partial
    gap_matrix["coverage_pct"] = round(found / max(total_req, 1) * 100, 1)

    # Update critical gaps
    gap_matrix["critical_gaps"] = [
        s["segment"] for s in segments
        if s.get("status") == "missing" and s.get("required")
    ]

    return gap_matrix


# ---------------------------------------------------------------------------
# HTML Validation Report (No Commission!)
# ---------------------------------------------------------------------------

def _render_validation_html(report: Dict, client_name: str) -> str:
    """Render a branded HTML validation report.

    NOTE: Per Commander directive (Mar 12, 2026), NO commission info
    is included — these may be sent directly to clients.
    """
    segments = report.get("segments", [])
    coverage = report.get("coverage_pct", 0)

    # Color code
    if coverage >= 90:
        badge_color = "#2ecc71"  # Green
        badge_text = "READY"
    elif coverage >= 70:
        badge_color = "#f39c12"  # Orange
        badge_text = "GAPS FOUND"
    else:
        badge_color = "#e74c3c"  # Red
        badge_text = "ACTION NEEDED"

    # Build segment rows
    rows_html = ""
    category_order = ["documents", "insurance", "flights", "transfers",
                      "hotel", "cruise", "dining", "excursions", "admin"]

    for cat in category_order:
        cat_segments = [s for s in segments if s.get("category") == cat]
        if not cat_segments:
            continue

        rows_html += f"""
        <tr><td colspan="4" style="background:#152540;color:#c9a84c;
            font-weight:bold;padding:10px;text-transform:uppercase;
            letter-spacing:1px;border-bottom:2px solid #c9a84c;">
            {cat.replace('_', ' ')}</td></tr>"""

        for seg in cat_segments:
            status = seg.get("status", "missing")
            if status == "found":
                icon = "&#10003;"
                color = "#2ecc71"
            elif status == "partial":
                icon = "&#9888;"
                color = "#f39c12"
            elif status == "not_applicable":
                icon = "&#8212;"
                color = "#8a9ab5"
            else:
                icon = "&#10007;"
                color = "#e74c3c"

            req = "*" if seg.get("required") else ""
            detail = seg.get("matched_detail") or seg.get("gap_note") or ""
            if len(detail) > 120:
                detail = detail[:120] + "..."

            rows_html += f"""
            <tr style="border-bottom:1px solid #1e3358;">
                <td style="padding:8px;color:{color};font-size:18px;
                    text-align:center;width:30px;">{icon}</td>
                <td style="padding:8px;color:#e8e8e8;">
                    {seg.get('segment', '?')}{req}</td>
                <td style="padding:8px;color:#8a9ab5;font-size:13px;">
                    {detail}</td>
                <td style="padding:8px;color:{color};font-weight:bold;
                    text-align:center;">{status.upper()}</td>
            </tr>"""

    # Critical gaps section
    critical_html = ""
    critical_gaps = report.get("critical_gaps", [])
    if critical_gaps:
        items = "".join(f"<li style='color:#e74c3c;margin:4px 0;'>{g}</li>"
                       for g in critical_gaps)
        critical_html = f"""
        <div style="background:#2a1520;border:1px solid #e74c3c;
             border-radius:8px;padding:16px;margin:20px 0;">
            <h3 style="color:#e74c3c;margin:0 0 8px 0;">
                Critical Gaps — Action Required</h3>
            <ul style="margin:0;padding-left:20px;">{items}</ul>
        </div>"""

    # Recommendations
    recs_html = ""
    recommendations = report.get("recommendations", [])
    if recommendations:
        items = "".join(f"<li style='color:#e8c97a;margin:4px 0;'>{r}</li>"
                       for r in recommendations)
        recs_html = f"""
        <div style="background:#1e3358;border:1px solid #c9a84c;
             border-radius:8px;padding:16px;margin:20px 0;">
            <h3 style="color:#c9a84c;margin:0 0 8px 0;">
                Recommendations</h3>
            <ul style="margin:0;padding-left:20px;">{items}</ul>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d1b2e;font-family:Georgia,'Times New Roman',serif;">
<div style="max-width:720px;margin:0 auto;padding:30px 20px;">

    <!-- Header -->
    <div style="text-align:center;border-bottom:2px solid #c9a84c;padding-bottom:20px;margin-bottom:24px;">
        <h1 style="color:#c9a84c;font-size:28px;margin:0;letter-spacing:2px;">
            DREAMS2MEMORIES TRAVEL</h1>
        <p style="color:#8a9ab5;margin:8px 0 0 0;font-size:14px;letter-spacing:1px;">
            TRIP VALIDATION REPORT</p>
    </div>

    <!-- Client & Status Badge -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
        <div>
            <h2 style="color:#e8e8e8;margin:0;font-size:22px;">
                {client_name.title()}</h2>
            <p style="color:#8a9ab5;margin:4px 0 0 0;">
                {report.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))}</p>
        </div>
        <div style="background:{badge_color};color:#0d1b2e;padding:8px 20px;
             border-radius:4px;font-weight:bold;font-size:14px;letter-spacing:1px;">
            {badge_text} &mdash; {coverage:.0f}%
        </div>
    </div>

    <!-- Summary Stats -->
    <div style="display:flex;gap:16px;margin-bottom:24px;">
        <div style="flex:1;background:#152540;border-radius:8px;padding:16px;text-align:center;">
            <div style="color:#2ecc71;font-size:28px;font-weight:bold;">
                {report.get('total_found', 0)}</div>
            <div style="color:#8a9ab5;font-size:12px;">CONFIRMED</div>
        </div>
        <div style="flex:1;background:#152540;border-radius:8px;padding:16px;text-align:center;">
            <div style="color:#f39c12;font-size:28px;font-weight:bold;">
                {report.get('total_partial', 0)}</div>
            <div style="color:#8a9ab5;font-size:12px;">PARTIAL</div>
        </div>
        <div style="flex:1;background:#152540;border-radius:8px;padding:16px;text-align:center;">
            <div style="color:#e74c3c;font-size:28px;font-weight:bold;">
                {report.get('total_missing', 0)}</div>
            <div style="color:#8a9ab5;font-size:12px;">MISSING</div>
        </div>
    </div>

    <!-- Segment Matrix -->
    <table style="width:100%;border-collapse:collapse;background:#0d1b2e;">
        {rows_html}
    </table>

    {critical_html}
    {recs_html}

    <!-- Footer -->
    <div style="text-align:center;border-top:1px solid #1e3358;padding-top:16px;margin-top:30px;">
        <p style="color:#8a9ab5;font-size:12px;margin:0;">
            Dreams2Memories Travel, LLC &mdash; Trip Validation</p>
        <p style="color:#8a9ab5;font-size:11px;margin:4px 0 0 0;">
            * = required segment &nbsp;|&nbsp; Generated {datetime.now().strftime('%b %d, %Y %I:%M %p')}</p>
    </div>

</div>
</body></html>"""

    return html


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def validate_client(client_key: str,
                     voyage_type: str = "cruise_standard",
                     skip_email: bool = False) -> Dict:
    """Run the full validation pipeline for a single client.

    Args:
        client_key: lowercase client last name (must match dossier filename)
        voyage_type: key into REQUIRED_SEGMENTS template
        skip_email: if True, skip Gmail sweep (use dossier only)

    Returns:
        Complete validation report dict
    """
    logger.info("=" * 60)
    logger.info("VALIDATION START: %s (%s)", client_key, voyage_type)
    logger.info("=" * 60)

    # 0. Load required segments template
    required = REQUIRED_SEGMENTS.get(voyage_type)
    if not required:
        return {"error": f"Unknown voyage type: {voyage_type}"}

    # 1. Find client dossier
    registry = _load_client_registry()
    client_info = registry.get(client_key)
    dossier_path = client_info["dossier_path"] if client_info else None

    # 2. Extract segments from dossier
    dossier_segments = []
    if dossier_path:
        dossier_segments = _extract_dossier_segments(dossier_path)
        logger.info("Dossier extraction: %d segments", len(dossier_segments))

    # 3. CLAUDE MAX HAIKU PASS 1 — Email sweep
    email_segments = []
    if not skip_email:
        try:
            service = _get_gmail_service()
            emails = _search_gmail_for_client(
                service, client_key,
                extra_terms=["flight", "hotel", "transfer", "cruise",
                            "insurance", "PNR", "seat", "excursion"]
            )
            email_segments = _haiku_extract_segments(emails, client_key)
            logger.info("Email extraction: %d segments", len(email_segments))
        except Exception as e:
            logger.error("Email sweep failed: %s", e)

    # Combine all found segments (deduplicate by segment name)
    all_found = dossier_segments + email_segments
    seen_segments = set()
    deduped = []
    for seg in all_found:
        key = (seg.get("category", ""), seg.get("segment", "").lower())
        if key not in seen_segments:
            seen_segments.add(key)
            deduped.append(seg)
        else:
            # Keep the one with more details
            for existing in deduped:
                if (existing.get("category", ""), existing.get("segment", "").lower()) == key:
                    if len(seg.get("details", "")) > len(existing.get("details", "")):
                        existing["details"] = seg["details"]
                    break

    logger.info("Total unique segments: %d", len(deduped))

    # 4. SONNET PASS — Gap matrix analysis
    logger.info("Calling Sonnet for gap analysis...")
    gap_matrix = _sonnet_gap_analysis(client_key, required, deduped)

    if "error" in gap_matrix:
        logger.error("Sonnet gap analysis failed: %s", gap_matrix["error"])
        return gap_matrix

    # 5. CLAUDE MAX HAIKU PASS 2 — Targeted re-search for gaps
    missing_segments = [
        s for s in gap_matrix.get("segments", [])
        if s.get("status") == "missing" and s.get("search_suggestion")
    ]

    if missing_segments and not skip_email:
        logger.info("Re-searching %d gaps...", len(missing_segments))
        try:
            service = _get_gmail_service()
            research = _sonnet_targeted_search(service, client_key, missing_segments)
            gap_matrix = _merge_research_into_matrix(gap_matrix, research)
        except Exception as e:
            logger.error("Targeted re-search failed: %s", e)

    # 6. Save validation report
    report_path = VALIDATION_DIR / f"{client_key}_validation_{datetime.now().strftime('%Y%m%d')}.json"
    report_path.write_text(json.dumps(gap_matrix, indent=2), encoding="utf-8")
    logger.info("Report saved: %s", report_path)

    # 7. Save HTML report (no auto-draft per SO-2026-03-21)
    html = _render_validation_html(gap_matrix, client_key)
    html_path = VALIDATION_DIR / f"{client_key}_validation_{datetime.now().strftime('%Y%m%d')}.html"
    html_path.write_text(html, encoding="utf-8")
    logger.info("HTML report saved: %s", html_path)

    logger.info("VALIDATION COMPLETE: %s — %.0f%% coverage, %d critical gaps",
                client_key,
                gap_matrix.get("coverage_pct", 0),
                len(gap_matrix.get("critical_gaps", [])))

    return gap_matrix


def validate_all_active(voyage_type: str = "cruise_standard") -> Dict[str, Dict]:
    """Run validation for all active clients with dossiers."""
    registry = _load_client_registry()
    results = {}

    for client_key in sorted(registry.keys()):
        try:
            results[client_key] = validate_client(
                client_key, voyage_type=voyage_type,
            )
        except Exception as e:
            logger.error("Validation failed for %s: %s", client_key, e)
            results[client_key] = {"error": str(e)}

    return results


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Trip Validation")
    parser.add_argument("--client", "-c", help="Client last name (lowercase)")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Validate all active clients")
    parser.add_argument("--type", "-t", default="cruise_standard",
                       choices=list(REQUIRED_SEGMENTS.keys()),
                       help="Voyage type template")
    parser.add_argument("--no-email", action="store_true",
                       help="Skip email sweep (dossier only)")
    args = parser.parse_args()

    if args.all:
        results = validate_all_active(
            voyage_type=args.type,
        )
        for name, report in results.items():
            cov = report.get("coverage_pct", 0)
            gaps = len(report.get("critical_gaps", []))
            print(f"  {name}: {cov:.0f}% coverage, {gaps} critical gaps")
    elif args.client:
        report = validate_client(
            args.client, voyage_type=args.type,
            skip_email=args.no_email,
        )
        print(json.dumps(report, indent=2))
    else:
        parser.print_help()
