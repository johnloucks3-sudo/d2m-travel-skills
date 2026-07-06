"""
Booking cancellation risk scoring.

DATA REALITY CHECK (2026-07-06): There is no labeled cancellation-outcome
history in this system. TESS/dossiers/KNOWN_BOOKINGS record exactly one
cancellation ever (Westbrook, medical emergency, unrelated to payment/
engagement signals). A logistic regression needs many labeled examples per
feature to fit and validate; one event can't train or validate anything,
and an AUC number computed against it would be fabricated. See
train_logistic_regression() below for what unblocks the ML version.

Until that data exists, this module scores risk with a transparent, hand-
weighted heuristic over signals that are actually available. It is not a
statistical model and makes no accuracy claim — it is a triage ranking
so Dani can prioritize retention outreach (the stated use case).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


HIGH_RISK_THRESHOLD = 70

# Weight rationale (COS judgment call, not fitted — revisit once real
# cancellation labels exist):
#   FPD lateness is the strongest observable distress signal we have
#   (a client who is late paying is a client reconsidering the trip).
#   Engagement (email opens) is the next best proxy for continued intent.
#   Prior cancellations is a small per-client prior, not overweighted
#   because n=1 in our history is not enough to trust heavily.
#   Days-to-departure scales urgency, not risk itself, so it acts as a
#   late multiplier rather than a flat weight.
WEIGHTS = {
    "fpd_overdue": 40,       # 0-40 scaled by days overdue
    "no_engagement": 25,     # flat if the client hasn't opened lifecycle emails
    "prior_cancellations": 20,  # 20 per prior cancellation, capped
    "competitor_activity": 15,  # flat if flagged (rarely available)
}


@dataclass
class BookingFeatures:
    booking_id: str
    days_to_departure: Optional[int] = None
    fpd_status: str = "unknown"           # "PAID" | "PENDING" | "OVERDUE" | "unknown"
    fpd_days_overdue: int = 0
    prior_cancellations: int = 0
    email_engagement: str = "unknown"     # "opened" | "no_opens" | "unknown"
    competitor_activity: bool = False
    # Which fields actually came from a real source vs. a default fill-in.
    # Drives the confidence score below.
    known_fields: set = field(default_factory=set)


@dataclass
class RiskResult:
    booking_id: str
    risk_score: int
    confidence: float
    recommendation: str
    flagged_for_intervention: bool
    signal_breakdown: dict


def score_booking(f: BookingFeatures) -> RiskResult:
    """Deterministic weighted heuristic. Not a trained model — see module docstring."""
    breakdown = {}

    fpd_component = 0.0
    if f.fpd_status == "OVERDUE":
        fpd_component = min(WEIGHTS["fpd_overdue"], f.fpd_days_overdue * 4)
    breakdown["fpd_overdue"] = round(fpd_component, 1)

    engagement_component = WEIGHTS["no_engagement"] if f.email_engagement == "no_opens" else 0.0
    breakdown["no_engagement"] = engagement_component

    prior_component = min(WEIGHTS["prior_cancellations"], f.prior_cancellations * 20)
    breakdown["prior_cancellations"] = prior_component

    competitor_component = WEIGHTS["competitor_activity"] if f.competitor_activity else 0.0
    breakdown["competitor_activity"] = competitor_component

    raw_score = fpd_component + engagement_component + prior_component + competitor_component

    # Urgency multiplier: same distress signals matter more the closer to
    # departure. Neutral (1.0x) beyond 90 days out or when unknown.
    multiplier = 1.0
    if f.days_to_departure is not None and f.days_to_departure <= 90:
        multiplier = 1.0 + (90 - max(f.days_to_departure, 0)) / 90 * 0.3  # up to 1.3x

    risk_score = max(0, min(100, round(raw_score * multiplier)))

    known = f.known_fields
    trackable = {"fpd_status", "email_engagement", "prior_cancellations", "competitor_activity"}
    confidence = round(len(known & trackable) / len(trackable), 2) if trackable else 0.0

    flagged = risk_score > HIGH_RISK_THRESHOLD
    recommendation = (
        f"Flag for retention intervention (risk {risk_score} > {HIGH_RISK_THRESHOLD}). "
        "Dani outreach: specialty dining/perk offer or check-in call."
        if flagged
        else f"No intervention needed (risk {risk_score} <= {HIGH_RISK_THRESHOLD}). Monitor at next lifecycle touchpoint."
    )

    return RiskResult(
        booking_id=f.booking_id,
        risk_score=risk_score,
        confidence=confidence,
        recommendation=recommendation,
        flagged_for_intervention=flagged,
        signal_breakdown=breakdown,
    )


def features_from_known_booking(booking_key: str, booking: dict, today: Optional[date] = None) -> BookingFeatures:
    """Build features from a core/scheduling/thunderbird_anchor_dates.KNOWN_BOOKINGS entry.

    Only fills fields that entry actually carries (fpd_status, embark_date).
    Engagement, prior-cancellation count, and competitor activity are not
    present in KNOWN_BOOKINGS and stay 'unknown'/0 until a real source
    (email-open tracking, TESS history) is wired in.
    """
    today = today or date.today()
    known = set()

    days_to_departure = None
    embark = booking.get("embark_date")
    if embark:
        days_to_departure = (embark - today).days
        known.add("days_to_departure")

    fpd_status_raw = booking.get("fpd_status", "unknown")
    fpd = booking.get("fpd")
    fpd_days_overdue = 0
    fpd_status = "unknown"
    if fpd_status_raw == "PAID":
        fpd_status = "PAID"
        known.add("fpd_status")
    elif fpd_status_raw == "PENDING" and fpd:
        overdue_days = (today - fpd).days
        if overdue_days > 0:
            fpd_status = "OVERDUE"
            fpd_days_overdue = overdue_days
        else:
            fpd_status = "PENDING"
        known.add("fpd_status")

    return BookingFeatures(
        booking_id=booking_key,
        days_to_departure=days_to_departure,
        fpd_status=fpd_status,
        fpd_days_overdue=fpd_days_overdue,
        known_fields=known,
    )


def write_risk_json(result: RiskResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {
            "booking_id": result.booking_id,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "recommendation": result.recommendation,
            "flagged_for_intervention": result.flagged_for_intervention,
            "signal_breakdown": result.signal_breakdown,
            "threshold": HIGH_RISK_THRESHOLD,
            "method": "weighted_heuristic_v1",
        },
        indent=2,
    ))
    return out_path


def train_logistic_regression(*_args, **_kwargs):
    """Not implemented — no labeled outcome data exists to train or validate against.

    To build the real version:
      1. Log every booking's terminal outcome (completed / cancelled) plus the
         feature snapshot at scoring time — this system logs neither today.
      2. Accrue enough cancelled examples across enough bookings for a 4-5
         feature logistic regression to fit without overfitting (rule of
         thumb: >=10 cancelled events per feature, so >=40-50 cancellations
         minimum) and a held-out set to compute AUC honestly.
      3. Wire this function to read that log, fit with sklearn, and report
         AUC on the held-out split — then it replaces score_booking() above.
    Calling this now would require inventing labels, so it raises instead.
    """
    raise NotImplementedError(
        "No cancellation-outcome dataset exists yet. See docstring for what's needed. "
        "Use score_booking() (weighted heuristic) until then."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Score a booking's cancellation risk (heuristic v1)")
    parser.add_argument("--booking-id", required=True)
    parser.add_argument("--days-to-departure", type=int, default=None)
    parser.add_argument("--fpd-status", default="unknown", choices=["PAID", "PENDING", "OVERDUE", "unknown"])
    parser.add_argument("--fpd-days-overdue", type=int, default=0)
    parser.add_argument("--prior-cancellations", type=int, default=0)
    parser.add_argument("--email-engagement", default="unknown", choices=["opened", "no_opens", "unknown"])
    parser.add_argument("--competitor-activity", action="store_true")
    parser.add_argument("--out", default=None, help="Path to write cancellation_risk.json")
    args = parser.parse_args()

    known = set()
    if args.fpd_status != "unknown":
        known.add("fpd_status")
    if args.email_engagement != "unknown":
        known.add("email_engagement")
    known.add("prior_cancellations")
    known.add("competitor_activity")

    feats = BookingFeatures(
        booking_id=args.booking_id,
        days_to_departure=args.days_to_departure,
        fpd_status=args.fpd_status,
        fpd_days_overdue=args.fpd_days_overdue,
        prior_cancellations=args.prior_cancellations,
        email_engagement=args.email_engagement,
        competitor_activity=args.competitor_activity,
        known_fields=known,
    )
    result = score_booking(feats)
    out_path = Path(args.out) if args.out else Path(f"OpsCenter/state/cancellation_risk_{args.booking_id}.json")
    write_risk_json(result, out_path)
    print(json.dumps(result.__dict__, indent=2, default=str))
    print(f"Written to {out_path}")
