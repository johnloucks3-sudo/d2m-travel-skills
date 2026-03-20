"""
Thunderbird Data Confidence Classifier
=======================================

Tags every data field with HIGH / MED / LOW / ZERO confidence before
it reaches Dani's LLM context.  Prevents hallucination by making the
model explicitly aware of what it DOES and DOES NOT know.

Integration:
  - Called in Dani Engine Phase 1 (Aggregate) after data collection
  - Output injected into LLM system prompt so Dani can hedge appropriately
  - "I'll confirm that detail" instead of inventing an answer

Confidence Levels:
  HIGH  — Confirmed source (booking confirmation, supplier PDF, Google Sheet)
  MED   — Single unverified source (email mention, client verbal, "I think")
  LOW   — Inferred or stale (>30 days old, extrapolated from similar booking)
  ZERO  — No data found — Dani MUST NOT answer, must escalate
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("thunderbird_data_confidence")


# ============================================================================
# Confidence Levels
# ============================================================================

class Confidence(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"
    ZERO = "ZERO"


# ============================================================================
# Tagged Field
# ============================================================================

@dataclass
class TaggedField:
    """A data field with confidence metadata."""
    name: str
    value: Any
    confidence: Confidence
    source: str = ""           # Where the data came from
    source_date: Optional[str] = None  # ISO date of source
    note: str = ""             # Why this confidence level

    def __str__(self) -> str:
        if self.confidence == Confidence.ZERO:
            return f"[{self.confidence.value}] {self.name}: NO DATA"
        return f"[{self.confidence.value}] {self.name}: {self.value}"


@dataclass
class ConfidenceReport:
    """Collection of tagged fields for a client query response."""
    fields: list[TaggedField] = field(default_factory=list)
    query: str = ""
    client: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def has_zero(self) -> bool:
        return any(f.confidence == Confidence.ZERO for f in self.fields)

    @property
    def min_confidence(self) -> Confidence:
        if not self.fields:
            return Confidence.ZERO
        order = [Confidence.ZERO, Confidence.LOW, Confidence.MED, Confidence.HIGH]
        return min((f.confidence for f in self.fields), key=lambda c: order.index(c))

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.fields if f.confidence == Confidence.HIGH)

    @property
    def zero_count(self) -> int:
        return sum(1 for f in self.fields if f.confidence == Confidence.ZERO)

    def to_injection_block(self) -> str:
        """Format as an LLM context injection block for Dani."""
        lines = ["DATA CONFIDENCE REPORT:"]
        lines.append(f"  Query: {self.query}")
        lines.append(f"  Client: {self.client}")
        lines.append("")

        for f in self.fields:
            tag = f"[{f.confidence.value}]"
            if f.confidence == Confidence.ZERO:
                lines.append(f"  {tag} {f.name}: *** NO DATA — DO NOT ANSWER ***")
            elif f.confidence == Confidence.LOW:
                lines.append(f"  {tag} {f.name}: {f.value}  (unverified — hedge)")
            elif f.confidence == Confidence.MED:
                lines.append(f"  {tag} {f.name}: {f.value}  (single source)")
            else:
                lines.append(f"  {tag} {f.name}: {f.value}")
            if f.source:
                lines.append(f"         Source: {f.source}")
            if f.note:
                lines.append(f"         Note: {f.note}")

        # Dani behavioral instructions based on confidence
        lines.append("")
        if self.has_zero:
            lines.append("INSTRUCTION: Some fields have ZERO confidence.")
            lines.append("  For ZERO fields: say 'I'll confirm that detail with John and get back to you.'")
            lines.append("  NEVER guess or fill in ZERO-confidence data.")
        if any(f.confidence == Confidence.LOW for f in self.fields):
            lines.append("INSTRUCTION: Some fields have LOW confidence.")
            lines.append("  For LOW fields: use hedging language — 'I believe', 'based on what I have'.")

        return "\n".join(lines)


# ============================================================================
# Classification Engine
# ============================================================================

# Patterns that indicate uncertain data
UNCERTAIN_PATTERNS = [
    r"\bi think\b",
    r"\bprobably\b",
    r"\bmaybe\b",
    r"\bnot sure\b",
    r"\bunconfirmed\b",
    r"\bpending\b",
    r"\btbd\b",
    r"\bto be determined\b",
    r"\bassuming\b",
    r"\bestimated?\b",
    r"\bapprox(?:imately)?\b",
    r"\?\s*$",  # Ends with question mark
]

# Source types and their default confidence
SOURCE_CONFIDENCE = {
    "booking_confirmation": Confidence.HIGH,
    "supplier_pdf": Confidence.HIGH,
    "google_sheet": Confidence.HIGH,
    "google_sheet_booking_master": Confidence.HIGH,
    "dossier": Confidence.HIGH,
    "email_confirmation": Confidence.HIGH,
    "calendar_event": Confidence.HIGH,
    "email_mention": Confidence.MED,
    "client_verbal": Confidence.MED,
    "client_email": Confidence.MED,
    "dossier_unverified": Confidence.MED,
    "web_search": Confidence.LOW,
    "inferred": Confidence.LOW,
    "stale": Confidence.LOW,
    "unknown": Confidence.LOW,
    "none": Confidence.ZERO,
}

# Staleness threshold — data older than this gets downgraded
STALE_DAYS = 30


def classify_field(
    name: str,
    value: Any,
    source: str = "unknown",
    source_date: Optional[str] = None,
    raw_text: str = "",
) -> TaggedField:
    """Classify a single data field's confidence level.

    Args:
        name: Field name (e.g., "flight_departure", "hotel_name")
        value: The data value
        source: Source type key from SOURCE_CONFIDENCE
        source_date: ISO date string when source was created/updated
        raw_text: Original text the value was extracted from (for uncertainty detection)

    Returns:
        TaggedField with confidence classification
    """
    # No value = ZERO
    if value is None or (isinstance(value, str) and not value.strip()):
        return TaggedField(
            name=name,
            value=None,
            confidence=Confidence.ZERO,
            source=source,
            source_date=source_date,
            note="No data available",
        )

    # Start with source-based confidence
    base_confidence = SOURCE_CONFIDENCE.get(source, Confidence.LOW)

    # Check for uncertainty patterns in raw text
    note = ""
    if raw_text:
        text_lower = raw_text.lower()
        for pattern in UNCERTAIN_PATTERNS:
            if re.search(pattern, text_lower):
                if base_confidence == Confidence.HIGH:
                    base_confidence = Confidence.MED
                elif base_confidence == Confidence.MED:
                    base_confidence = Confidence.LOW
                note = f"Uncertainty detected: matched '{pattern}'"
                break

    # Check staleness
    if source_date:
        try:
            src_dt = datetime.fromisoformat(source_date.replace("Z", "+00:00"))
            age = datetime.now(src_dt.tzinfo) - src_dt if src_dt.tzinfo else datetime.now() - src_dt
            if age > timedelta(days=STALE_DAYS):
                if base_confidence == Confidence.HIGH:
                    base_confidence = Confidence.MED
                elif base_confidence == Confidence.MED:
                    base_confidence = Confidence.LOW
                note = f"Data is {age.days} days old (stale threshold: {STALE_DAYS}d)"
        except (ValueError, TypeError):
            pass

    return TaggedField(
        name=name,
        value=value,
        confidence=base_confidence,
        source=source,
        source_date=source_date,
        note=note,
    )


def classify_booking_data(booking: dict, source: str = "google_sheet") -> list[TaggedField]:
    """Classify all fields in a booking record.

    Standard booking fields from Booking Master or dossier.
    """
    fields = []
    field_map = {
        "client_name": "Client Name",
        "trip_name": "Trip Name",
        "ship": "Ship/Vessel",
        "departure_date": "Departure Date",
        "return_date": "Return Date",
        "cabin": "Cabin Assignment",
        "cabin_category": "Cabin Category",
        "total_cost": "Total Cost",
        "amount_paid": "Amount Paid",
        "balance_due": "Balance Due",
        "fpd": "Final Payment Date",
        "flight_out": "Outbound Flight",
        "flight_return": "Return Flight",
        "hotel_pre": "Pre-Cruise Hotel",
        "hotel_post": "Post-Cruise Hotel",
        "insurance": "Travel Insurance",
        "passport_verified": "Passport Verified",
        "emergency_contact": "Emergency Contact",
        "dietary": "Dietary Requirements",
        "mobility": "Mobility Needs",
    }

    source_date = booking.get("last_updated", booking.get("source_date"))

    for key, display_name in field_map.items():
        value = booking.get(key)
        raw_text = str(value) if value else ""
        fields.append(classify_field(
            name=display_name,
            value=value,
            source=source,
            source_date=source_date,
            raw_text=raw_text,
        ))

    return fields


def classify_dossier_section(
    section_name: str,
    section_text: str,
    dossier_date: Optional[str] = None,
) -> TaggedField:
    """Classify a dossier markdown section."""
    if not section_text or not section_text.strip():
        return TaggedField(
            name=section_name,
            value=None,
            confidence=Confidence.ZERO,
            source="dossier",
            source_date=dossier_date,
            note="Section empty or missing",
        )

    # Check for uncertainty markers in dossier text
    return classify_field(
        name=section_name,
        value=section_text.strip()[:200],  # Truncate for display
        source="dossier",
        source_date=dossier_date,
        raw_text=section_text,
    )


def build_confidence_report(
    query: str,
    client: str,
    booking_data: Optional[dict] = None,
    dossier_sections: Optional[dict[str, str]] = None,
    extra_fields: Optional[list[TaggedField]] = None,
) -> ConfidenceReport:
    """Build a complete confidence report for a client query.

    This is the main entry point — called from Dani Engine Phase 1.
    """
    report = ConfidenceReport(query=query, client=client)

    if booking_data:
        report.fields.extend(classify_booking_data(booking_data))

    if dossier_sections:
        dossier_date = dossier_sections.get("_date")
        for section_name, section_text in dossier_sections.items():
            if section_name.startswith("_"):
                continue
            report.fields.append(classify_dossier_section(
                section_name=section_name,
                section_text=section_text,
                dossier_date=dossier_date,
            ))

    if extra_fields:
        report.fields.extend(extra_fields)

    # Log summary
    high = sum(1 for f in report.fields if f.confidence == Confidence.HIGH)
    med = sum(1 for f in report.fields if f.confidence == Confidence.MED)
    low = sum(1 for f in report.fields if f.confidence == Confidence.LOW)
    zero = sum(1 for f in report.fields if f.confidence == Confidence.ZERO)
    logger.info(
        f"Confidence report for {client}: "
        f"HIGH={high} MED={med} LOW={low} ZERO={zero}"
    )

    return report


# ============================================================================
# Quick Helpers
# ============================================================================

def tag_high(name: str, value: Any, source: str = "booking_confirmation") -> TaggedField:
    """Shortcut: tag a confirmed field as HIGH confidence."""
    return TaggedField(name=name, value=value, confidence=Confidence.HIGH, source=source)


def tag_zero(name: str, note: str = "No data available") -> TaggedField:
    """Shortcut: tag a missing field as ZERO confidence."""
    return TaggedField(name=name, value=None, confidence=Confidence.ZERO, note=note)


def should_escalate(report: ConfidenceReport, query_fields: list[str]) -> bool:
    """Check if any queried fields are ZERO — meaning Dani should escalate.

    Args:
        report: The confidence report
        query_fields: Field names the client is specifically asking about

    Returns:
        True if any specifically-asked-about field is ZERO
    """
    zero_names = {f.name.lower() for f in report.fields if f.confidence == Confidence.ZERO}
    return any(qf.lower() in zero_names for qf in query_fields)
