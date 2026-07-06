"""
partner_apis.py — Travel insurance partner API wrappers
=========================================================
Thin wrappers around three insurance partner quote endpoints: TravelGuard
(AIG), Generali (CSA), World Nomads. Each wrapper tries a live API call
first (requires an API key in the environment); if no key is configured
or the call fails, it falls back to a deterministic ROM (rough-order-of-
magnitude) estimate so the Wing can still stage a TP 0.5 quote block.

Readiness note (2026-07-06): none of the three partners has credentials
configured yet (`TRAVELGUARD_API_KEY` / `GENERALI_API_KEY` /
`WORLDNOMADS_API_KEY` are unset). Estimates are clearly flagged
source="estimate" — never presented to a client as a bindable quote.
Swap in real credentials + confirm the live request/response shape
against each partner's actual B2B agent API docs before trusting
source="live_api" output for a client send (WF-17 still gates that).
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def _parse_date(d) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()


# Age-banded base rate: percentage of insured trip cost, by carrier.
# ROM figures pending live API confirmation — see module docstring.
_AGE_BANDS = [
    (0, 29, 0.028),
    (30, 39, 0.032),
    (40, 49, 0.036),
    (50, 59, 0.042),
    (60, 69, 0.050),
    (70, 79, 0.068),
    (80, 130, 0.095),
]


def _age_base_rate(age: int) -> float:
    for lo, hi, rate in _AGE_BANDS:
        if lo <= age <= hi:
            return rate
    return _AGE_BANDS[-1][2]


@dataclass
class InsuranceQuote:
    carrier: str
    plan_name: str
    premium: float
    trip_cost: float
    coverage_highlights: list
    pre_existing_waiver_available: bool
    pre_existing_waiver_deadline: Optional[str]
    source: str  # "live_api" | "estimate"
    quote_ref: str
    link: str
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "carrier": self.carrier,
            "plan_name": self.plan_name,
            "premium": round(self.premium, 2),
            "trip_cost": round(self.trip_cost, 2),
            "coverage_highlights": self.coverage_highlights,
            "pre_existing_waiver_available": self.pre_existing_waiver_available,
            "pre_existing_waiver_deadline": self.pre_existing_waiver_deadline,
            "source": self.source,
            "quote_ref": self.quote_ref,
            "link": self.link,
        }


class InsurancePartnerAPI:
    """Base class — carrier subclasses set class attrs and override _live_api_call."""

    carrier_name = "base"
    plan_name = "Standard"
    api_key_env = ""
    base_url = ""
    carrier_multiplier = 1.0
    waiver_window_days: Optional[int] = None  # days from deposit date; None = no waiver offered
    coverage_highlights = [
        "Trip cancellation and interruption",
        "Emergency medical + evacuation",
        "Baggage delay/loss",
    ]
    booking_link_base = ""

    def __init__(self):
        self.api_key = os.environ.get(self.api_key_env, "") or None

    def quote(
        self,
        trip_cost: float,
        traveler_ages: list,
        destinations: list,
        departure_date,
        return_date,
        deposit_date=None,
        booking_ref: str = "",
    ) -> InsuranceQuote:
        if self.api_key and requests is not None:
            live = self._live_api_call(
                trip_cost, traveler_ages, destinations, departure_date, return_date, deposit_date
            )
            if live is not None:
                return live
        return self._estimate(trip_cost, traveler_ages, destinations, deposit_date, booking_ref)

    def _live_api_call(
        self, trip_cost, traveler_ages, destinations, departure_date, return_date, deposit_date
    ) -> Optional[InsuranceQuote]:
        """Attempt a real partner quote call. Returns None (falls back to estimate) on any failure."""
        try:
            resp = requests.post(
                self.base_url,
                json={
                    "api_key": self.api_key,
                    "trip_cost": trip_cost,
                    "traveler_ages": traveler_ages,
                    "destinations": destinations,
                    "departure_date": str(departure_date),
                    "return_date": str(return_date),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return InsuranceQuote(
                carrier=self.carrier_name,
                plan_name=data.get("plan_name", self.plan_name),
                premium=float(data["premium"]),
                trip_cost=trip_cost,
                coverage_highlights=data.get("coverage_highlights", self.coverage_highlights),
                pre_existing_waiver_available=data.get("pre_existing_waiver_available", False),
                pre_existing_waiver_deadline=data.get("pre_existing_waiver_deadline"),
                source="live_api",
                quote_ref=data.get("quote_ref", ""),
                link=data.get("link", self.booking_link_base),
                raw=data,
            )
        except Exception as exc:  # noqa: BLE001 — any partner API failure falls back to estimate
            logger.warning("%s live API call failed, falling back to estimate: %s", self.carrier_name, exc)
            return None

    def _estimate(self, trip_cost, traveler_ages, destinations, deposit_date, booking_ref) -> InsuranceQuote:
        oldest_age = max(traveler_ages) if traveler_ages else 40
        base_rate = _age_base_rate(oldest_age) * self.carrier_multiplier
        premium = round(trip_cost * base_rate, 2)

        waiver_available = self.waiver_window_days is not None
        waiver_deadline = None
        if waiver_available and deposit_date is not None:
            dep = _parse_date(deposit_date)
            if dep is not None:
                waiver_deadline = date.fromordinal(dep.toordinal() + self.waiver_window_days).isoformat()

        quote_ref = f"{self.carrier_name.upper().replace(' ', '')}-EST-{booking_ref or 'NA'}"

        return InsuranceQuote(
            carrier=self.carrier_name,
            plan_name=self.plan_name,
            premium=premium,
            trip_cost=trip_cost,
            coverage_highlights=self.coverage_highlights,
            pre_existing_waiver_available=waiver_available,
            pre_existing_waiver_deadline=waiver_deadline,
            source="estimate",
            quote_ref=quote_ref,
            link=self.booking_link_base,
        )


class TravelGuardAPI(InsurancePartnerAPI):
    carrier_name = "TravelGuard"
    plan_name = "Preferred"
    api_key_env = "TRAVELGUARD_API_KEY"
    base_url = "https://api.travelguard.com/v1/quotes"  # placeholder — confirm against agent API docs
    carrier_multiplier = 1.00
    waiver_window_days = 15
    coverage_highlights = [
        "Trip cancellation/interruption (100%/150%)",
        "Emergency medical $50,000+",
        "Medical evacuation $500,000+",
        "Pre-existing condition waiver (15-day window)",
    ]
    booking_link_base = "https://www.travelguard.com/"


class GeneraliAPI(InsurancePartnerAPI):
    carrier_name = "Generali"
    plan_name = "Premium"
    api_key_env = "GENERALI_API_KEY"
    base_url = "https://api.generalitravelinsurance.com/v1/quotes"  # placeholder
    carrier_multiplier = 1.05
    waiver_window_days = 14
    coverage_highlights = [
        "Trip cancellation/interruption (100%/150%)",
        "Emergency medical $50,000",
        "Medical evacuation $1,000,000",
        "Pre-existing condition waiver (14-day window)",
        "Cancel For Any Reason upgrade available",
    ]
    booking_link_base = "https://www.generalitravelinsurance.com/"


class WorldNomadsAPI(InsurancePartnerAPI):
    carrier_name = "World Nomads"
    plan_name = "Explorer"
    api_key_env = "WORLDNOMADS_API_KEY"
    base_url = "https://api.worldnomads.com/v1/quotes"  # placeholder
    carrier_multiplier = 1.15
    waiver_window_days = None  # World Nomads does not offer a pre-existing condition waiver
    coverage_highlights = [
        "Trip cancellation/interruption",
        "Emergency medical + evacuation",
        "Adventure activities coverage (200+ activities)",
        "No pre-existing condition waiver — excluded by default",
    ]
    booking_link_base = "https://www.worldnomads.com/"


ALL_PARTNERS = [TravelGuardAPI, GeneraliAPI, WorldNomadsAPI]
