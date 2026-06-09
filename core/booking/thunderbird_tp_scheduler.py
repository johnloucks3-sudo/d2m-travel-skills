#!/usr/bin/env python3
"""
Thunderbird TP Scheduler — 23-Touchpoint Lifecycle Automation
==============================================================
Dreams2Memories Travel, LLC | core/booking/thunderbird_tp_scheduler.py

Automates the canonical 23-TP client lifecycle (SO 2026-04-17).
For each active dossier, computes exact due dates for all touchpoints
relative to departure date and FPD, then surfaces overdue / upcoming TPs
for injection into the morning briefing and mission board.

Usage:
    python3 thunderbird_tp_scheduler.py                # Scan all active dossiers
    python3 thunderbird_tp_scheduler.py --client Kuklinski
    python3 thunderbird_tp_scheduler.py --horizon 14   # Alert window in days (default 7)
    python3 thunderbird_tp_scheduler.py --json          # Machine-readable output
    python3 thunderbird_tp_scheduler.py --brief         # Brief-mode for morning inject

Reference: memory/reference_canonical_lifecycle_touchpoints.md
Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml  # PyYAML — parse dossier frontmatter

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"

# Files that are not client dossiers
SKIP_FILES = {
    "CLAUDE.md",
    "DOSSIER_Regent_Tips_Guide.md",
    "DANI_TESTER_BRIEFINGS.md",
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TPStatus(str, Enum):
    PENDING    = "pending"     # Not yet in window
    DUE        = "due"         # In window, not started
    IN_WINDOW  = "in_window"   # Active research/work window open
    OVERDUE    = "overdue"     # Past deadline, not completed
    COMPLETE   = "complete"    # Marked done in dossier or state file
    BLOCKED    = "blocked"     # Missing prerequisite (e.g. no FPD)
    SKIPPED    = "skipped"     # Conditional TP not applicable (e.g. TP 4.6 no FCC)


class DateRef(str, Enum):
    BOOKING    = "booking"     # Days after booking confirmation
    DEPARTURE  = "departure"   # Days before departure (E-X = negative offset)
    FPD        = "fpd"         # Days relative to Final Payment Due date
    POST_DEP   = "post_dep"    # Days after departure date (post-voyage)


# ---------------------------------------------------------------------------
# TP Definition — the 23 canonical touchpoints
# ---------------------------------------------------------------------------

@dataclass
class TPDef:
    """Static definition of one canonical touchpoint."""
    tp_id:       str          # e.g. "0.5", "1.1", "4.4"
    label:       str          # Human label
    phase:       int          # 0-5
    phase_name:  str
    # Trigger window: (ref, start_days, end_days)
    # start_days is offset from ref; end_days is the deadline offset.
    # Negative = before; positive = after.
    trigger_ref:   DateRef
    window_start:  int        # days offset from ref — start of work window
    window_end:    int        # days offset from ref — hard deadline
    staff_lead:    str
    weekly_reports: bool = False
    conditional:   bool = False  # True = only fires if prerequisite met
    conditional_note: str = ""
    notes:         str = ""


# The 23 canonical touchpoints — window_start and window_end are day offsets
# from the reference date. Negative = before that date. Positive = after.
CANONICAL_TPS: list[TPDef] = [
    # ── Phase 0: Onboarding ─────────────────────────────────────────────────
    TPDef("0.5",  "Welcome / Booking Validation",  0, "Onboarding",
          DateRef.BOOKING, 0, 7,
          "Dani + Naia", notes="Booking confirmation, suite, FPD, next steps"),

    TPDef("0.6",  "Insurance Advisory",             0, "Onboarding",
          DateRef.BOOKING, 7, 14,
          "A9 Harlan", notes="Pre-existing window check — quote Allianz/TG/IMG"),

    # ── Phase 1: Discovery ───────────────────────────────────────────────────
    TPDef("1.1",  "Voyage Preview (destination guide)",  1, "Discovery",
          DateRef.DEPARTURE, -240, -210,
          "A2 Dembe + A6 Luna", weekly_reports=True,
          notes="All ports research, narrative copy, imagery"),

    TPDef("1.2",  "Airfare Watch",  1, "Discovery",
          DateRef.DEPARTURE, -210, -180,
          "A2 Dembe + A5 Viper", weekly_reports=True,
          notes="Fare trends, routing options, booking recommendation"),

    TPDef("1.3",  "Hotel Options (pre/post cruise)",  1, "Discovery",
          DateRef.DEPARTURE, -210, -180,
          "A2 Dembe", weekly_reports=True,
          notes="3+3 options: name/link/images/reviews/price"),

    # ── Phase 2: Momentum ────────────────────────────────────────────────────
    TPDef("2.1",  "Excursion Research & Recs",  2, "Momentum",
          DateRef.DEPARTURE, -180, -120,
          "A2 Dembe", weekly_reports=True,
          notes="MUST complete before portal opening. Port-by-port."),

    TPDef("2.2",  "Monthly Validation (rolling)",  2, "Momentum",
          DateRef.DEPARTURE, -180, -30,
          "Hale", weekly_reports=True,
          notes="Status against validation matrix. Monthly, 1st of month."),

    TPDef("2.3",  "Culinary Arts / Kitchen Classes",  2, "Momentum",
          DateRef.DEPARTURE, -120, -90,
          "A2 Dembe", weekly_reports=True, conditional=True,
          conditional_note="Only if cruise line offers (Regent: Culinary Arts Kitchen)"),

    TPDef("2.4",  "Dining Reservations",  2, "Momentum",
          DateRef.DEPARTURE, -90, -60,
          "A2 Dembe", weekly_reports=True,
          notes="Specialty dining research, book on opening day"),

    TPDef("2.5",  "Document Audit",  2, "Momentum",
          DateRef.DEPARTURE, -90, -75,
          "Hale",
          notes="Passports, guest reg, visas, emergency contacts"),

    # ── Phase 3: Pre-Departure ───────────────────────────────────────────────
    TPDef("3.1",  "Pre-Voyage Brief",  3, "Pre-Departure",
          DateRef.DEPARTURE, -28, -21,
          "Hale + A2 + A6",
          notes="Comprehensive trip packet. Coincides with check-in."),

    TPDef("3.2",  "Final Confirmation",  3, "Pre-Departure",
          DateRef.DEPARTURE, -14, -7,
          "Hale",
          notes="All logistics locked. Print confirmations."),

    TPDef("3.3",  "Send-Off / Bon Voyage",  3, "Pre-Departure",
          DateRef.DEPARTURE, -5, -3,
          "Hale + A6",
          notes="Warm send-off, weather, last-minute tips"),

    # ── Phase 4: Payment ─────────────────────────────────────────────────────
    TPDef("4.1",  "Payment Reminder #1",  4, "Payment",
          DateRef.FPD, -21, -14,
          "Hale + A9",
          notes="Balance amount, payment options, timeline"),

    TPDef("4.2",  "Payment Reminder #2",  4, "Payment",
          DateRef.FPD, -14, -7,
          "Hale + A9",
          notes="Confirm method on file"),

    TPDef("4.3",  "Payment Goal",  4, "Payment",
          DateRef.FPD, -7, -1,
          "Hale + A9",
          notes="Target early payment"),

    TPDef("4.4",  "Final Payment Due",  4, "Payment",
          DateRef.FPD, 0, 0,
          "A9 + Hale",
          notes="CRITICAL — cancellation risk if missed"),

    TPDef("4.5",  "Payment Confirmation",  4, "Payment",
          DateRef.FPD, 1, 7,
          "A9",
          notes="Verify posted, update dossier"),

    TPDef("4.6",  "Apply FCC / Credits",  4, "Payment",
          DateRef.FPD, 0, 30,
          "A9", conditional=True,
          conditional_note="CONDITIONAL — only if FCC/credits exist"),

    # ── Phase 5: Post-Voyage ─────────────────────────────────────────────────
    TPDef("5.1",  "Welcome Home",  5, "Post-Voyage",
          DateRef.POST_DEP, 7, 10,
          "Hale",
          notes="Debrief, highlights, experience capture"),

    TPDef("5.2",  "Survey / Review Request",  5, "Post-Voyage",
          DateRef.POST_DEP, 14, 17,
          "A7 Gauge + Dani"),

    TPDef("5.3",  "Thank You + Referral",  5, "Post-Voyage",
          DateRef.POST_DEP, 21, 25,
          "Dani + Naia",
          notes="Gratitude, gentle referral ask"),

    TPDef("5.4",  "Next Voyage Plant + Commission Audit",  5, "Post-Voyage",
          DateRef.POST_DEP, 30, 35,
          "A5 Viper + A9",
          notes="Retention, next booking strategy, commission reconciliation"),
]

# Fast lookup by tp_id
TP_BY_ID: dict[str, TPDef] = {tp.tp_id: tp for tp in CANONICAL_TPS}


# ---------------------------------------------------------------------------
# Dossier — parsed client record
# ---------------------------------------------------------------------------

@dataclass
class DossierRecord:
    """Parsed client dossier with lifecycle-relevant dates."""
    path:           Path
    client:         str
    ship:           str = ""
    cruise_line:    str = ""
    departure:      Optional[date] = None
    return_date:    Optional[date] = None
    fpd:            Optional[date] = None
    fpd_amount:     Optional[float] = None
    booking_date:   Optional[date] = None   # None if absent — missing booking_date → BLOCKED
    status:         str = "active"
    parse_error:    Optional[str] = None
    completed_tps:  set = field(default_factory=set)  # TP IDs confirmed done in dossier frontmatter

    @property
    def is_schedulable(self) -> bool:
        return self.status == "active" and self.departure is not None


def _parse_date(val) -> Optional[date]:
    """Parse a YAML date value to Python date."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def load_dossier(path: Path) -> DossierRecord:
    """Parse YAML frontmatter from a dossier file."""
    rec = DossierRecord(path=path, client=path.stem)
    try:
        text = path.read_text(encoding="utf-8")
        # Extract --- ... --- frontmatter block
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            rec.parse_error = "No YAML frontmatter found"
            return rec
        fm = yaml.safe_load(match.group(1)) or {}
        rec.client      = str(fm.get("client", path.stem))
        rec.ship        = str(fm.get("ship", ""))
        rec.cruise_line = str(fm.get("cruise_line", ""))
        rec.status      = str(fm.get("status", "active")).lower()
        rec.departure   = _parse_date(fm.get("departure"))
        rec.return_date = _parse_date(fm.get("return"))
        rec.fpd         = _parse_date(fm.get("fpd"))
        raw_amt = fm.get("fpd_amount")
        rec.fpd_amount  = float(raw_amt) if raw_amt else None
        rec.booking_date = _parse_date(fm.get("booking_date"))
        # No mtime fallback — missing booking_date → BLOCKED (prevents spurious overdue alerts)
        completed_raw = fm.get("completed_tps", []) or []
        rec.completed_tps = set(str(t) for t in completed_raw)
    except Exception as exc:
        rec.parse_error = str(exc)
    return rec


def scan_dossiers(dossier_dir: Path = DOSSIER_DIR) -> list[DossierRecord]:
    """Load all active client dossiers."""
    records = []
    for path in sorted(dossier_dir.glob("*.md")):
        if path.name in SKIP_FILES or path.name.startswith("."):
            continue
        rec = load_dossier(path)
        if rec.status in ("active", "prospect"):
            records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Schedule computation
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTP:
    """One computed touchpoint instance for a specific client."""
    client:       str
    tp_def:       TPDef
    trigger_date: Optional[date]   # When work should start
    deadline:     Optional[date]   # Hard deadline
    status:       TPStatus = TPStatus.PENDING
    notes:        str = ""

    @property
    def tp_id(self) -> str:
        return self.tp_def.tp_id

    @property
    def label(self) -> str:
        return self.tp_def.label

    def to_dict(self) -> dict:
        return {
            "client":       self.client,
            "tp_id":        self.tp_id,
            "label":        self.label,
            "phase":        self.tp_def.phase,
            "phase_name":   self.tp_def.phase_name,
            "trigger_date": self.trigger_date.isoformat() if self.trigger_date else None,
            "deadline":     self.deadline.isoformat() if self.deadline else None,
            "status":       self.status.value,
            "staff_lead":   self.tp_def.staff_lead,
            "notes":        self.notes,
            "conditional":  self.tp_def.conditional,
        }


def _compute_ref_date(tp: TPDef, rec: DossierRecord) -> Optional[date]:
    """Resolve the reference date for a TP given a dossier record."""
    if tp.trigger_ref == DateRef.BOOKING:
        return rec.booking_date
    elif tp.trigger_ref == DateRef.DEPARTURE:
        return rec.departure
    elif tp.trigger_ref == DateRef.FPD:
        return rec.fpd
    elif tp.trigger_ref == DateRef.POST_DEP:
        return rec.return_date  # departure fires mid-voyage; return_date is correct anchor
    return None


def generate_schedule(rec: DossierRecord, today: Optional[date] = None) -> list[ScheduledTP]:
    """
    Compute the full 23-TP schedule for one dossier record.
    Returns list of ScheduledTP instances with status evaluated against today.
    """
    today = today or date.today()
    scheduled = []

    for tp in CANONICAL_TPS:
        ref = _compute_ref_date(tp, rec)
        stp = ScheduledTP(client=rec.client, tp_def=tp, trigger_date=None, deadline=None)

        # Completion check — TP marked done in dossier frontmatter, skip window eval
        if tp.tp_id in rec.completed_tps:
            stp.status = TPStatus.COMPLETE
            scheduled.append(stp)
            continue

        if ref is None:
            # Blocked — required reference date not in dossier
            stp.status = TPStatus.BLOCKED
            stp.notes = f"Missing ref: {tp.trigger_ref.value}"
            scheduled.append(stp)
            continue

        # Compute absolute dates
        stp.trigger_date = ref + timedelta(days=tp.window_start)
        stp.deadline     = ref + timedelta(days=tp.window_end)

        # Status evaluation
        if stp.deadline < today:
            stp.status = TPStatus.OVERDUE
        elif stp.trigger_date <= today <= stp.deadline:
            stp.status = TPStatus.IN_WINDOW
        elif stp.trigger_date > today:
            stp.status = TPStatus.PENDING
        else:
            stp.status = TPStatus.DUE

        scheduled.append(stp)

    return scheduled


def get_actionable_tps(
    schedule: list[ScheduledTP],
    horizon_days: int = 7,
    today: Optional[date] = None,
) -> list[ScheduledTP]:
    """
    Return TPs that need attention: overdue + in-window + due within horizon_days.
    Excludes BLOCKED and PENDING (not yet near).
    """
    today = today or date.today()
    horizon = today + timedelta(days=horizon_days)
    results = []
    for stp in schedule:
        if stp.status == TPStatus.OVERDUE:
            results.append(stp)
        elif stp.status == TPStatus.IN_WINDOW:
            results.append(stp)
        elif stp.status == TPStatus.PENDING and stp.trigger_date and stp.trigger_date <= horizon:
            stp.status = TPStatus.DUE
            results.append(stp)
    return results


# ---------------------------------------------------------------------------
# Multi-dossier scan
# ---------------------------------------------------------------------------

def scan_all_actionable(
    horizon_days: int = 7,
    today: Optional[date] = None,
    dossier_dir: Path = DOSSIER_DIR,
    client_filter: Optional[str] = None,
) -> list[ScheduledTP]:
    """
    Scan all active dossiers. Return all actionable TPs sorted by deadline.
    Suitable for morning briefing injection.
    """
    today = today or date.today()
    records = scan_dossiers(dossier_dir)
    all_actionable: list[ScheduledTP] = []

    for rec in records:
        if not rec.is_schedulable:
            continue
        if client_filter and client_filter.lower() not in rec.client.lower():
            continue
        if rec.parse_error:
            logger.warning(f"Dossier parse error [{rec.path.name}]: {rec.parse_error}")
            continue
        schedule = generate_schedule(rec, today)
        actionable = get_actionable_tps(schedule, horizon_days, today)
        all_actionable.extend(actionable)

    # Sort: OVERDUE first, then by deadline ascending
    priority = {TPStatus.OVERDUE: 0, TPStatus.IN_WINDOW: 1, TPStatus.DUE: 2}
    all_actionable.sort(key=lambda t: (priority.get(t.status, 9), t.deadline or date.max))
    return all_actionable


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_brief(tps: list[ScheduledTP], today: Optional[date] = None) -> str:
    """Format actionable TPs as a briefing-style table (Telegram-safe)."""
    today = today or date.today()
    if not tps:
        return "TP Scheduler: No TPs due or overdue in scan window."

    lines = [f"*TP LIFECYCLE SCAN — {today.isoformat()}*", ""]
    for stp in tps:
        status_icon = {"overdue": "🔴", "in_window": "🟡", "due": "🟠"}.get(stp.status.value, "⚪")
        deadline_str = stp.deadline.isoformat() if stp.deadline else "???"
        days_rel = (stp.deadline - today).days if stp.deadline else 0
        rel = f"({'+' if days_rel >= 0 else ''}{days_rel}d)"
        lines.append(
            f"{status_icon} *TP {stp.tp_id}* [{stp.client}] — {stp.label}\n"
            f"   Deadline: {deadline_str} {rel} | Lead: {stp.tp_def.staff_lead}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Thunderbird TP Scheduler — 23-Touchpoint Lifecycle Automation"
    )
    p.add_argument("--client",   help="Filter by client name (partial match)")
    p.add_argument("--horizon",  type=int, default=7,
                   help="Alert horizon in days (default 7)")
    p.add_argument("--json",     action="store_true", help="Output as JSON")
    p.add_argument("--brief",    action="store_true", help="Brief mode for morning inject")
    p.add_argument("--all",      action="store_true", help="Show all TPs including pending")
    p.add_argument("--dossier-dir", type=Path, default=DOSSIER_DIR,
                   help="Path to dossier directory")
    return p


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    today = date.today()

    actionable = scan_all_actionable(
        horizon_days=args.horizon,
        today=today,
        dossier_dir=args.dossier_dir,
        client_filter=args.client,
    )

    if args.json:
        print(json.dumps([t.to_dict() for t in actionable], indent=2, default=str))
    elif args.brief:
        print(format_brief(actionable, today))
    else:
        if not actionable:
            print(f"No TPs due or overdue within {args.horizon}-day window.")
            return
        print(f"\nTP SCHEDULER — {today.isoformat()} — {args.horizon}-day window")
        print(f"{'TP':6} {'CLIENT':20} {'STATUS':12} {'DEADLINE':12} {'LEAD'}")
        print("-" * 80)
        for stp in actionable:
            deadline = stp.deadline.isoformat() if stp.deadline else "blocked"
            print(f"{'TP '+stp.tp_id:6} {stp.client[:20]:20} {stp.status.value:12} "
                  f"{deadline:12} {stp.tp_def.staff_lead}")
        print(f"\n{len(actionable)} touchpoints require attention.")


if __name__ == "__main__":
    main()
