"""
Vendor Pricing Negotiation — Dreams2Memories Travel
=====================================================
Rate-reduction decision logic for hotel/transfer vendor quotes (Taap/Expedia,
Mozio, Blacklane). Monitors quoted rates against historical averages and
decides whether to request a discount.

LIVE-NEGOTIATION FEASIBILITY (checked 2026-07-06, before building this):
None of the three integrated vendor surfaces expose a "request rate
reduction" API endpoint:
  - Taap (Expedia EPS Rapid, core/travel/thunderbird_expedia_taap.py) is a
    fixed agent-net rate search/booking API. No negotiate/discount call.
  - Mozio and Blacklane (creds/mozio_credentials.json,
    creds/blacklane_credentials.json) are partner-program API keys for
    quote/search + booking only — same story, confirmed via their partner
    program docs referenced in the credential notes.
There is no vendor to send a real "10% off" request to. Auto-firing rate
change requests at a vendor is also a client/vendor-contact action this
Wing's own doctrine (Supplier Contact Boundary — any communication that
could change a number or create a commitment) reserves for Commander
review before send. Real dispatch is therefore intentionally NOT wired to
any live network call: `dispatch()` is dry-run/simulated by default and
raises if a live send is attempted, per vendor, until a real negotiate
endpoint exists and Commander approval is obtained for autonomous send.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional

RESULTS_PATH = Path.home() / "Thunderbird" / "core" / "vendor" / "negotiation_results.json"
HISTORY_PATH = Path.home() / "Thunderbird" / "core" / "vendor" / "vendor_rate_history.json"


@dataclass
class VendorQuote:
    vendor: str  # "taap" | "mozio" | "blacklane"
    item_key: str  # property_id, route_id, or transfer route string — groups history
    rate: float
    currency: str = "USD"
    quote_ref: Optional[str] = None


@dataclass
class NegotiationRule:
    """Request `discount_pct` off when rate exceeds historical avg by `threshold_pct`."""
    threshold_pct: float = 10.0
    discount_pct: float = 10.0


@dataclass
class NegotiationResult:
    vendor: str
    item_key: str
    quote_ref: Optional[str]
    rate_old: float
    rate_new: Optional[float]
    discount_pct_requested: float
    discount_pct_achieved: Optional[float]
    success: bool
    mode: str  # "dry_run" | "live"
    reason: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VendorRateHistory:
    """Rolling historical-average rate tracker per vendor+item_key, JSON-backed."""

    def __init__(self, path: Path = HISTORY_PATH, max_samples: int = 20):
        self.path = path
        self.max_samples = max_samples
        self._data: dict[str, list[float]] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def _key(self, vendor: str, item_key: str) -> str:
        return f"{vendor}:{item_key}"

    def average(self, vendor: str, item_key: str) -> Optional[float]:
        samples = self._data.get(self._key(vendor, item_key))
        return mean(samples) if samples else None

    def record(self, vendor: str, item_key: str, rate: float) -> None:
        k = self._key(vendor, item_key)
        samples = self._data.setdefault(k, [])
        samples.append(rate)
        if len(samples) > self.max_samples:
            del samples[0]

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))


class VendorNegotiationChannel:
    """Base class — no vendor here exposes a live negotiate endpoint (see module docstring)."""

    vendor_name = "base"

    def dispatch(self, quote: VendorQuote, discount_pct: float, dry_run: bool = True) -> tuple[bool, Optional[float], str]:
        """Returns (success, rate_new, reason). Live send is not implemented — see class docstring."""
        if not dry_run:
            raise NotImplementedError(
                f"{self.vendor_name} exposes no rate-negotiation API endpoint. "
                "Live auto-negotiation is not available; this also requires "
                "Commander sign-off per the Supplier Contact Boundary before "
                "any autonomous vendor-facing send is enabled."
            )
        # Simulated acceptance model for dry-run testing only — not a real vendor response.
        accepted = discount_pct <= 10.0
        new_rate = round(quote.rate * (1 - discount_pct / 100), 2) if accepted else quote.rate
        reason = "simulated: within typical vendor tolerance" if accepted else "simulated: exceeds typical vendor tolerance"
        return accepted, new_rate, reason


class TaapNegotiationChannel(VendorNegotiationChannel):
    vendor_name = "taap"


class MozioNegotiationChannel(VendorNegotiationChannel):
    vendor_name = "mozio"


class BlacklaneNegotiationChannel(VendorNegotiationChannel):
    vendor_name = "blacklane"


CHANNELS: dict[str, VendorNegotiationChannel] = {
    "taap": TaapNegotiationChannel(),
    "mozio": MozioNegotiationChannel(),
    "blacklane": BlacklaneNegotiationChannel(),
}


class PricingNegotiator:
    def __init__(self, rule: NegotiationRule = NegotiationRule(), history: Optional[VendorRateHistory] = None,
                 results_path: Path = RESULTS_PATH):
        self.rule = rule
        self.history = history or VendorRateHistory()
        self.results_path = results_path
        self.results: list[NegotiationResult] = []
        if self.results_path.exists():
            self.results = [NegotiationResult(**r) for r in json.loads(self.results_path.read_text())]

    def should_negotiate(self, quote: VendorQuote) -> bool:
        avg = self.history.average(quote.vendor, quote.item_key)
        if avg is None:
            return False
        return quote.rate > avg * (1 + self.rule.threshold_pct / 100)

    def process(self, quote: VendorQuote, dry_run: bool = True) -> NegotiationResult:
        avg = self.history.average(quote.vendor, quote.item_key)
        channel = CHANNELS.get(quote.vendor)
        if channel is None:
            result = NegotiationResult(
                vendor=quote.vendor, item_key=quote.item_key, quote_ref=quote.quote_ref,
                rate_old=quote.rate, rate_new=None, discount_pct_requested=0.0,
                discount_pct_achieved=None, success=False, mode="dry_run" if dry_run else "live",
                reason=f"unknown vendor '{quote.vendor}'",
            )
        elif not self.should_negotiate(quote):
            result = NegotiationResult(
                vendor=quote.vendor, item_key=quote.item_key, quote_ref=quote.quote_ref,
                rate_old=quote.rate, rate_new=quote.rate, discount_pct_requested=0.0,
                discount_pct_achieved=0.0, success=False, mode="dry_run" if dry_run else "live",
                reason=f"rate within threshold of historical avg ({avg})" if avg is not None else "no historical average yet",
            )
        else:
            accepted, new_rate, reason = channel.dispatch(quote, self.rule.discount_pct, dry_run=dry_run)
            achieved_pct = round((1 - new_rate / quote.rate) * 100, 2) if accepted and new_rate else 0.0
            result = NegotiationResult(
                vendor=quote.vendor, item_key=quote.item_key, quote_ref=quote.quote_ref,
                rate_old=quote.rate, rate_new=new_rate, discount_pct_requested=self.rule.discount_pct,
                discount_pct_achieved=achieved_pct, success=accepted,
                mode="dry_run" if dry_run else "live", reason=reason,
            )
        self.history.record(quote.vendor, quote.item_key, quote.rate)
        self.results.append(result)
        return result

    def success_rate(self) -> float:
        attempted = [r for r in self.results if r.reason.startswith("simulated") or r.mode == "live"]
        if not attempted:
            return 0.0
        return round(sum(1 for r in attempted if r.success) / len(attempted) * 100, 2)

    def save(self) -> None:
        self.history.save()
        self.results_path.write_text(json.dumps([asdict(r) for r in self.results], indent=2))
