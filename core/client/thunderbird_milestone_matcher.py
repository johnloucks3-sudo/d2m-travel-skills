#!/usr/bin/env python3
"""
Birthday/Anniversary Trip Suggestion Engine
=============================================
Per docs/MCP_Claude_Travel_Business_Enhancements.md section 1C.

Scans client dossiers for upcoming birthdays/anniversaries (90-day window),
matches against upcoming voyage inventory (master_cruise.db) filtered by
client cruise-line/region preference, and produces a monthly suggestions
digest — an internal decision-support brief, NOT client-ready copy.

Two layers, deliberately decoupled:
  1. Pure matching logic (match_clients_to_voyages, next_occurrence, etc.)
     — no I/O, fully unit-testable with fixture data.
  2. Production I/O (dossier scanning, master_cruise.db query, email send)
     — best-effort against real, messy dossier text.

WF-17: this module NEVER sends to a client. Output is an internal digest
to the Commander (johnloucks3, full send FROM d2mconcierge) for review.
Creative-chain HARD RULE: draft skeletons only — Dani/Naia/Luna own final
client voice if the Commander greenlights outreach.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

THUNDERBIRD = Path(__file__).parent.parent.parent
DOSSIER_DIR = THUNDERBIRD / "dossiers"
CRUISE_DB = THUNDERBIRD / "output" / "cruises.db"
OUTPUT_DIR = THUNDERBIRD / "output" / "suggestions"

SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md"}

MILESTONE_WINDOW_DAYS = 90
VOYAGE_MIN_MONTHS_OUT = 3
VOYAGE_MAX_MONTHS_OUT = 18
TOP_N_OPTIONS = 3


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ClientMilestone:
    name: str
    email: Optional[str]
    milestone_type: str  # "birthday" | "anniversary"
    month: int
    day: int
    milestone_date: date         # next occurrence
    days_until: int
    preferred_lines: List[str] = field(default_factory=list)
    preferred_regions: List[str] = field(default_factory=list)
    source_dossier: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["milestone_date"] = self.milestone_date.isoformat()
        return d


@dataclass
class VoyageOption:
    line: str
    ship: str
    departure: str
    nights: int
    from_port: str
    region: str
    price_ind: Optional[float]
    booking_url: Optional[str] = None
    preference_match: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["price_label"] = (
            f"from ${self.price_ind:,.0f} (indicative)" if self.price_ind else "indicative pricing not on file"
        )
        return d


# ---------------------------------------------------------------------------
# Pure logic — unit-testable, no I/O
# ---------------------------------------------------------------------------

def next_occurrence(month: int, day: int, today: date) -> date:
    """Return the next calendar occurrence of month/day on or after today."""
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        # Feb 29 in a non-leap year — roll to Mar 1
        candidate = date(today.year, 3, 1) if month == 2 and day == 29 else date(today.year, month, 1)
    if candidate < today:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            candidate = date(today.year + 1, 3, 1)
    return candidate


def is_within_window(days_until_value: int, window_days: int = MILESTONE_WINDOW_DAYS) -> bool:
    return 0 <= days_until_value <= window_days


def voyage_in_horizon(departure_str: str, today: date,
                       min_months: int = VOYAGE_MIN_MONTHS_OUT,
                       max_months: int = VOYAGE_MAX_MONTHS_OUT) -> bool:
    """True if the voyage departs within [min_months, max_months] of today."""
    try:
        dep = datetime.strptime(departure_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return False
    if dep < today:
        return False
    months_out = (dep.year - today.year) * 12 + (dep.month - today.month)
    return min_months <= months_out <= max_months


def _region_match(client: ClientMilestone, voyage: Dict[str, Any]) -> bool:
    region = (voyage.get("region") or "").lower()
    return any(r.lower() in region or region in r.lower() for r in client.preferred_regions if r)


def _line_match(client: ClientMilestone, voyage: Dict[str, Any]) -> bool:
    line = (voyage.get("line") or "").lower()
    return any(pl.lower() in line or line in pl.lower() for pl in client.preferred_lines if pl)


def match_clients_to_voyages(
    clients: List[ClientMilestone],
    voyages: List[Dict[str, Any]],
    top_n: int = TOP_N_OPTIONS,
) -> List[Dict[str, Any]]:
    """Core matching logic. Pure function — voyages are pre-filtered dicts with
    keys: line, ship, departure, nights, from_port, region, price_ind[, booking_url].

    Ranking: preference match (line OR region) first, then soonest departure.
    Always returns up to top_n options per client, falling back to
    non-preference-matched voyages if fewer than top_n preference matches exist
    — a milestone client always gets a full set of options to consider.
    """
    suggestions = []
    for client in clients:
        scored = []
        for v in voyages:
            pref = _line_match(client, v) or _region_match(client, v)
            scored.append((pref, v))

        # Preference matches first (soonest departure within each bucket),
        # then everything else, soonest departure.
        scored.sort(key=lambda t: (not t[0], t[1].get("departure", "")))

        options = []
        for pref, v in scored[:top_n]:
            opt = VoyageOption(
                line=v.get("line", ""),
                ship=v.get("ship", ""),
                departure=v.get("departure", ""),
                nights=v.get("nights", 0),
                from_port=v.get("from_port", ""),
                region=v.get("region", ""),
                price_ind=v.get("price_ind"),
                booking_url=v.get("booking_url"),
                preference_match=pref,
            )
            options.append(opt.to_dict())

        suggestions.append({
            "client": client.to_dict(),
            "options": options,
        })
    return suggestions


# ---------------------------------------------------------------------------
# Production I/O — dossier scanning (best-effort against free-text dossiers)
# ---------------------------------------------------------------------------

_DOB_LINE_PATTERNS = [
    re.compile(r"\bDOB[:\s|]+([A-Za-z]+ \d{1,2},? \d{4})", re.IGNORECASE),
    re.compile(r"\bDOB[:\s|]+([A-Za-z]+ \d{1,2})\b(?!,? \d{4})", re.IGNORECASE),
]
_SPECIAL_OCCASION_PATTERN = re.compile(
    r"SPECIAL OCCASION\s*[—-]\s*([A-Za-z .'-]+?)'s (birthday|anniversary)[:\s]*([A-Za-z]+ \d{1,2})",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _parse_month_day(text: str) -> Optional[tuple]:
    """Parse 'Feb 9, 1983', 'July 22', 'June 24, 1983 (age 43)' -> (month, day)."""
    m = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})", text.strip())
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    try:
        day = int(m.group(2))
    except ValueError:
        return None
    if not (1 <= day <= 31):
        return None
    return (month, day)


def _extract_known_lines_and_regions(text: str) -> tuple:
    """Best-effort: which cruise lines / regions does this dossier mention
    (a proxy for 'past booking history / stated preference')."""
    known_lines = [
        "Regent Seven Seas", "Silversea", "Viking", "Oceania", "Crystal",
        "Azamara", "Seabourn", "Ponant", "Cunard", "Explora Journeys",
        "Windstar", "Princess",
    ]
    known_regions = [
        "Mediterranean", "Caribbean", "Scandinavia", "Baltic", "Alaska",
        "Asia & Pacific", "Asia", "Pacific", "Panama Canal", "Transatlantic",
        "South America", "Indian Ocean", "Africa", "Hawaii", "Antarctica",
    ]
    lines = sorted({ln for ln in known_lines if ln.lower() in text.lower()})
    regions = sorted({rg for rg in known_regions if rg.lower() in text.lower()})
    return lines, regions


def extract_milestones_from_dossiers(
    dossier_dir: Path = DOSSIER_DIR,
    today: Optional[date] = None,
    window_days: int = MILESTONE_WINDOW_DAYS,
) -> List[ClientMilestone]:
    """Best-effort scan of real dossiers for birthdays/anniversaries in the
    next `window_days`. Free-text source data — heuristic, not exhaustive.
    """
    today = today or date.today()
    results: List[ClientMilestone] = []

    if not dossier_dir.exists():
        logger.warning(f"Dossier dir not found: {dossier_dir}")
        return results

    for fp in sorted(dossier_dir.glob("*.md")):
        if fp.name in SKIP_FILES:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        lines, regions = _extract_known_lines_and_regions(text)
        emails = _EMAIL_PATTERN.findall(text)
        default_email = emails[0] if emails else None

        # SPECIAL OCCASION callouts carry a name + explicit type
        for m in _SPECIAL_OCCASION_PATTERN.finditer(text):
            name, mtype, date_text = m.group(1).strip(), m.group(2).lower(), m.group(3)
            parsed = _parse_month_day(date_text)
            if not parsed:
                continue
            month, day = parsed
            occ = next_occurrence(month, day, today)
            delta = (occ - today).days
            if not is_within_window(delta, window_days):
                continue
            results.append(ClientMilestone(
                name=name, email=default_email, milestone_type=mtype,
                month=month, day=day, milestone_date=occ, days_until=delta,
                preferred_lines=lines, preferred_regions=regions,
                source_dossier=fp.stem,
            ))

        # Bare DOB lines — treat as birthday, name unknown (dossier-level)
        for pat in _DOB_LINE_PATTERNS:
            for m in pat.finditer(text):
                parsed = _parse_month_day(m.group(1))
                if not parsed:
                    continue
                month, day = parsed
                occ = next_occurrence(month, day, today)
                delta = (occ - today).days
                if not is_within_window(delta, window_days):
                    continue
                # Skip if already captured via SPECIAL OCCASION for same date
                if any(r.month == month and r.day == day and r.source_dossier == fp.stem for r in results):
                    continue
                results.append(ClientMilestone(
                    name=fp.stem.replace("_", " "), email=default_email,
                    milestone_type="birthday", month=month, day=day,
                    milestone_date=occ, days_until=delta,
                    preferred_lines=lines, preferred_regions=regions,
                    source_dossier=fp.stem,
                ))

    return results


# ---------------------------------------------------------------------------
# Production I/O — voyage inventory (master_cruise.db)
# ---------------------------------------------------------------------------

def get_upcoming_voyages(
    db_path: Path = CRUISE_DB,
    today: Optional[date] = None,
    min_months: int = VOYAGE_MIN_MONTHS_OUT,
    max_months: int = VOYAGE_MAX_MONTHS_OUT,
) -> List[Dict[str, Any]]:
    """Pull priced, in-horizon voyages from master_cruise.db.

    Only rows with price_ind IS NOT NULL are returned — "3 options + pricing"
    requires pricing, and only ~17% of rows carry an indicative figure.
    """
    today = today or date.today()
    if not db_path.exists():
        logger.warning(f"master_cruise.db not found at {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT line, ship, departure, nights, from_port, region, "
            "price_ind, booking_url FROM cruises WHERE price_ind IS NOT NULL "
            "AND departure >= ?",
            (today.isoformat(),),
        ).fetchall()
    finally:
        conn.close()

    voyages = [dict(r) for r in rows]
    return [v for v in voyages if voyage_in_horizon(v["departure"], today, min_months, max_months)]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_digest_email_html(suggestions: List[Dict[str, Any]], month_label: str) -> str:
    """Internal decision-support skeleton — NOT client-ready copy.
    Creative-chain HARD RULE: this is Hale's routing scaffold, not Dani's voice.
    """
    rows = []
    for s in suggestions:
        c = s["client"]
        opts = s["options"]
        opt_html = "".join(
            f"<li>{o['line']} — {o['ship']} — {o['departure']} ({o['nights']}n, {o['from_port']}) "
            f"— {o['price_label']}{' ⭐ preference match' if o['preference_match'] else ''}</li>"
            for o in opts
        )
        rows.append(
            f"<p><b>{c['name']}</b> — {c['milestone_type']} in {c['days_until']} days "
            f"({c['milestone_date']}), source: {c.get('source_dossier') or 'n/a'}</p>"
            f"<ul>{opt_html or '<li>No priced voyages matched the horizon window</li>'}</ul>"
        )
    body = "".join(rows) if rows else "<p>No upcoming milestones found in the 90-day window.</p>"
    return (
        f"<h2>Birthday/Anniversary Trip Suggestions — {month_label}</h2>"
        f"<p><b>⚠️ WF-17 HOLD — internal decision-support only. Do not send to any client.</b> "
        f"Options are skeleton draft scaffolds pending the full creative chain "
        f"(Reyes → Luna → Naia → Dani) if the Commander greenlights outreach.</p>"
        f"{body}"
    )


def run_monthly_scan(
    today: Optional[date] = None,
    dossier_dir: Path = DOSSIER_DIR,
    db_path: Path = CRUISE_DB,
    output_dir: Path = OUTPUT_DIR,
    send_digest: bool = True,
) -> Dict[str, Any]:
    today = today or date.today()
    month_label = today.strftime("%B %Y")

    clients = extract_milestones_from_dossiers(dossier_dir, today)
    if not clients:
        logger.warning(
            "Milestone scan found ZERO clients with upcoming birthdays/anniversaries — "
            "verify parser against current dossier formats before assuming a genuinely quiet month."
        )

    voyages = get_upcoming_voyages(db_path, today)
    suggestions = match_clients_to_voyages(clients, voyages)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"suggestions_{today.strftime('%Y-%m')}.json"
    payload = {
        "generated": today.isoformat(),
        "month": month_label,
        "milestone_window_days": MILESTONE_WINDOW_DAYS,
        "voyage_horizon_months": [VOYAGE_MIN_MONTHS_OUT, VOYAGE_MAX_MONTHS_OUT],
        "clients_found": len(clients),
        "voyages_considered": len(voyages),
        "suggestions": suggestions,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info(f"Wrote {out_path} — {len(clients)} clients, {len(voyages)} priced voyages in horizon")

    if send_digest:
        _send_internal_digest(suggestions, month_label)

    return payload


def _send_internal_digest(suggestions: List[Dict[str, Any]], month_label: str) -> None:
    """Full send FROM d2mconcierge TO johnloucks3 — internal brief, not a
    client draft. Per CLAUDE.md 'INTEL, BRIEFS & FINAL STAFF COMMUNICATIONS'
    rule: internal reports skip the draft step entirely.
    """
    html = build_digest_email_html(suggestions, month_label)
    try:
        import sys
        sys.path.insert(0, str(THUNDERBIRD))
        from core.email.thunderbird_gmail import gmail_create_draft_sync
        # send_digest uses the draft helper in "full send" spirit by staging
        # to johnloucks3 with no client address involved — internal only.
        gmail_create_draft_sync(
            to="johnloucks3@gmail.com",
            subject=f"Birthday/Anniversary Trip Suggestions — {month_label} — WF-17 HOLD",
            body=html,
            stage_in="johnloucks3",
            label_review=True,
            persona_display="Hale",
            product_type="Milestone Suggestions Digest",
        )
    except Exception as e:  # pragma: no cover - network/OAuth dependent
        logger.error(f"Could not stage milestone digest email: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_monthly_scan(send_digest=False)
    print(json.dumps({k: v for k, v in result.items() if k != "suggestions"}, indent=2))
    print(f"Suggestions for {len(result['suggestions'])} client(s).")
