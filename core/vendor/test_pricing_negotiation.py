"""
Tests for core/vendor/pricing_negotiation.py — fixtures only, no live vendor calls.

Live vendor negotiation ("10 real negotiations against live APIs") is NOT
exercised here: Taap/Mozio/Blacklane expose no rate-negotiation endpoint
(confirmed against core/travel/thunderbird_expedia_taap.py and the Mozio/
Blacklane partner credential docs), and even if one existed, a live send
crosses the Supplier Contact Boundary gate (Commander sign-off required
for any vendor-facing communication that could change a number). See the
module docstring in pricing_negotiation.py for the full finding.
"""

import json
import tempfile
from pathlib import Path

import pytest

from core.vendor.pricing_negotiation import (
    NegotiationRule,
    PricingNegotiator,
    VendorQuote,
    VendorRateHistory,
    CHANNELS,
)


@pytest.fixture
def tmp_negotiator():
    with tempfile.TemporaryDirectory() as d:
        history = VendorRateHistory(path=Path(d) / "history.json")
        results_path = Path(d) / "results.json"
        yield PricingNegotiator(rule=NegotiationRule(threshold_pct=10.0, discount_pct=10.0),
                                 history=history, results_path=results_path)


def _seed_history(negotiator: PricingNegotiator, vendor: str, item_key: str, rates: list[float]):
    for r in rates:
        negotiator.history.record(vendor, item_key, r)


def test_no_negotiation_without_history(tmp_negotiator):
    quote = VendorQuote(vendor="taap", item_key="hotel-123", rate=280.0)
    result = tmp_negotiator.process(quote, dry_run=True)
    assert result.success is False
    assert "no historical average" in result.reason


def test_no_negotiation_within_threshold(tmp_negotiator):
    _seed_history(tmp_negotiator, "taap", "hotel-123", [250.0, 245.0, 255.0])
    quote = VendorQuote(vendor="taap", item_key="hotel-123", rate=260.0)  # ~4% above avg 250
    result = tmp_negotiator.process(quote, dry_run=True)
    assert result.success is False
    assert result.discount_pct_requested == 0.0


def test_negotiation_triggers_above_threshold(tmp_negotiator):
    _seed_history(tmp_negotiator, "taap", "hotel-123", [240.0, 240.0, 240.0])
    quote = VendorQuote(vendor="taap", item_key="hotel-123", rate=280.0, quote_ref="Q1")  # 16.7% above avg
    result = tmp_negotiator.process(quote, dry_run=True)
    assert result.success is True
    assert result.discount_pct_requested == 10.0
    assert result.rate_new == pytest.approx(252.0)
    assert result.discount_pct_achieved == pytest.approx(10.0)


def test_unknown_vendor_rejected(tmp_negotiator):
    quote = VendorQuote(vendor="acme", item_key="x", rate=100.0)
    result = tmp_negotiator.process(quote, dry_run=True)
    assert result.success is False
    assert "unknown vendor" in result.reason


@pytest.mark.parametrize("vendor", ["taap", "mozio", "blacklane"])
def test_live_dispatch_not_implemented(vendor):
    """Confirms no live negotiate call is wired for any of the three vendors."""
    channel = CHANNELS[vendor]
    quote = VendorQuote(vendor=vendor, item_key="x", rate=100.0)
    with pytest.raises(NotImplementedError):
        channel.dispatch(quote, discount_pct=10.0, dry_run=False)


def test_success_rate_tracking(tmp_negotiator):
    _seed_history(tmp_negotiator, "mozio", "route-A", [50.0, 50.0])
    tmp_negotiator.process(VendorQuote(vendor="mozio", item_key="route-A", rate=70.0), dry_run=True)  # triggers, succeeds (<=10%)
    tmp_negotiator.process(VendorQuote(vendor="mozio", item_key="route-A", rate=50.0), dry_run=True)  # no trigger
    assert tmp_negotiator.success_rate() == 100.0


def test_results_persist_to_disk(tmp_negotiator):
    _seed_history(tmp_negotiator, "blacklane", "airport-hotel", [90.0, 90.0])
    tmp_negotiator.process(VendorQuote(vendor="blacklane", item_key="airport-hotel", rate=110.0, quote_ref="BL-1"),
                            dry_run=True)
    tmp_negotiator.save()
    saved = json.loads(tmp_negotiator.results_path.read_text())
    assert len(saved) == 1
    assert saved[0]["vendor"] == "blacklane"
    assert saved[0]["quote_ref"] == "BL-1"
