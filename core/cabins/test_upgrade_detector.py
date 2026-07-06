#!/usr/bin/env python3
"""Tests for core/cabins/upgrade_detector.py — no network/browser required.

Run: python3 -m pytest core/cabins/test_upgrade_detector.py -v
"""

import json
import sys
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

import pytest

from core.cabins.upgrade_detector import (
    UpgradeOpportunity,
    WatchedBooking,
    cabin_tier_rank,
    detect_upgrade_for_booking,
    load_watches,
    parse_cabin_prices,
    run_sweep,
    save_opportunities,
    tier_order_for_line,
)


# ---------------------------------------------------------------------------
# cabin_tier_rank
# ---------------------------------------------------------------------------

def test_rank_orders_low_to_high():
    order = tier_order_for_line("regent")
    assert cabin_tier_rank("Deluxe Window Suite", order) < cabin_tier_rank("Concierge Suite", order)
    assert cabin_tier_rank("Concierge Suite", order) < cabin_tier_rank("Penthouse Suite", order)
    assert cabin_tier_rank("Penthouse Suite", order) < cabin_tier_rank("Regent Suite", order)


def test_rank_longest_match_wins():
    order = tier_order_for_line("regent")
    # "Deluxe Veranda Suite" should not be mistaken for a bare "veranda"/"deluxe" partial
    assert cabin_tier_rank("Deluxe Veranda Suite", order) == order.index("deluxe veranda suite")


def test_rank_unranked_returns_negative_one():
    assert cabin_tier_rank("Some Made-Up Category", tier_order_for_line("regent")) == -1


def test_line_specific_order_used_over_generic():
    assert tier_order_for_line("silversea") != tier_order_for_line("regent")
    assert tier_order_for_line("unknown-line") == tier_order_for_line(None)


# ---------------------------------------------------------------------------
# parse_cabin_prices
# ---------------------------------------------------------------------------

def test_parse_cabin_prices_finds_nearby_dollar_figure():
    text = "Concierge Suite E — from $4,199 per person, double occupancy. Penthouse Suite — from $3,999 per person."
    prices = parse_cabin_prices(text, ["concierge suite", "penthouse suite"])
    assert prices["concierge suite"] == 4199.0
    assert prices["penthouse suite"] == 3999.0


def test_parse_cabin_prices_ignores_out_of_range_numbers():
    text = "Cabin 863, Deck 8. Penthouse Suite — call for rates. Ref #12345678."
    prices = parse_cabin_prices(text, ["penthouse suite"])
    assert "penthouse suite" not in prices  # 12345678 exceeds sanity ceiling, no $ prefix either


def test_parse_cabin_prices_keeps_cheapest_sighting():
    text = "Penthouse Suite $5,500 (waitlist) ... later in page ... Penthouse Suite now $3,000 available"
    prices = parse_cabin_prices(text, ["penthouse suite"])
    assert prices["penthouse suite"] == 3000.0


# ---------------------------------------------------------------------------
# detect_upgrade_for_booking — the McLeod use case from the spec
# ---------------------------------------------------------------------------

def _mcleod_booking(current_price=3200.0, current_cabin="Deluxe Veranda Suite"):
    return WatchedBooking(
        booking_id="McLeod_TEST_001",
        client_name="Erik McLeod",
        ship="SS Grandeur",
        cruise_line="regent",
        current_cabin=current_cabin,
        current_price_pp=current_price,
        voyage_url="https://example.com/grandeur-dec2026",
        active=True,
    )


def test_flags_upgrade_when_penthouse_cheaper_than_current():
    booking = _mcleod_booking(current_price=3200.0)

    def fake_fetch(url):
        return "Penthouse Suite — now available at $3,000 per person due to a cancellation."

    opp = detect_upgrade_for_booking(booking, fetch_fn=fake_fetch)
    assert opp is not None
    assert isinstance(opp, UpgradeOpportunity)
    assert opp.available_upgrade == "penthouse suite"
    assert opp.upgrade_price_pp == 3000.0
    assert opp.price_delta == -200.0
    assert "LESS" in opp.recommendation
    assert opp.booking_id == "McLeod_TEST_001"


def test_flags_upgrade_when_within_price_delta_threshold():
    booking = _mcleod_booking(current_price=3200.0)

    def fake_fetch(url):
        return "Penthouse Suite available at $3,650 per person."

    opp = detect_upgrade_for_booking(booking, fetch_fn=fake_fetch)
    assert opp is not None
    assert opp.price_delta == 450.0


def test_does_not_flag_when_price_delta_too_high():
    booking = _mcleod_booking(current_price=3200.0)

    def fake_fetch(url):
        return "Penthouse Suite available at $4,500 per person."

    opp = detect_upgrade_for_booking(booking, fetch_fn=fake_fetch)
    assert opp is None


def test_does_not_flag_lower_or_equal_tier():
    booking = _mcleod_booking(current_price=3200.0, current_cabin="Penthouse Suite")

    def fake_fetch(url):
        # Only a lower/equal tier is available — nothing to upgrade into
        return "Concierge Suite available at $2,000 per person. Penthouse Suite available at $3,100."

    opp = detect_upgrade_for_booking(booking, fetch_fn=fake_fetch)
    assert opp is None


def test_no_voyage_url_skips_without_error():
    booking = _mcleod_booking()
    booking.voyage_url = None

    def fake_fetch(url):
        raise AssertionError("fetch_fn must not be called when voyage_url is missing")

    assert detect_upgrade_for_booking(booking, fetch_fn=fake_fetch) is None


def test_unranked_current_cabin_skips_without_error():
    booking = _mcleod_booking(current_cabin="Category Z-9000")

    def fake_fetch(url):
        raise AssertionError("fetch_fn must not be called when current cabin is unranked")

    assert detect_upgrade_for_booking(booking, fetch_fn=fake_fetch) is None


def test_fetch_failure_returns_none_not_exception():
    booking = _mcleod_booking()

    def failing_fetch(url):
        raise TimeoutError("scrape timed out")

    assert detect_upgrade_for_booking(booking, fetch_fn=failing_fetch) is None


def test_returns_cheapest_delta_when_multiple_upgrades_qualify():
    booking = _mcleod_booking(current_price=3200.0, current_cabin="Concierge Suite")

    def fake_fetch(url):
        return (
            "Penthouse Suite available at $3,400 per person. "
            "Regent Suite available at $3,250 per person."
        )

    opp = detect_upgrade_for_booking(booking, fetch_fn=fake_fetch)
    assert opp is not None
    assert opp.available_upgrade == "regent suite"
    assert opp.price_delta == 50.0


# ---------------------------------------------------------------------------
# run_sweep — end-to-end against a temp watch/output file pair
# ---------------------------------------------------------------------------

def test_run_sweep_writes_output_file(tmp_path):
    watch_path = tmp_path / "watches.json"
    output_path = tmp_path / "opportunities.json"

    watch_path.write_text(json.dumps([
        {
            "booking_id": "A", "client_name": "Alice Test", "ship": "SS Grandeur",
            "cruise_line": "regent", "current_cabin": "Deluxe Veranda Suite",
            "current_price_pp": 3200.0, "voyage_url": "https://example.com/a", "active": True,
        },
        {
            "booking_id": "B", "client_name": "Bob Test", "ship": "SS Grandeur",
            "cruise_line": "regent", "current_cabin": "Regent Suite",
            "current_price_pp": 9000.0, "voyage_url": "https://example.com/b", "active": True,
        },
        {
            "booking_id": "C", "client_name": "Carol Inactive", "ship": "SS Grandeur",
            "cruise_line": "regent", "current_cabin": "Deluxe Veranda Suite",
            "current_price_pp": 3200.0, "voyage_url": "https://example.com/c", "active": False,
        },
    ]))

    def fake_fetch(url):
        if url.endswith("/a"):
            return "Penthouse Suite available at $3,100 per person."
        return "Concierge Suite available at $2,000 per person."  # no upgrade for B (top tier)

    results = run_sweep(fetch_fn=fake_fetch, watch_path=watch_path, output_path=output_path)

    assert len(results) == 1
    assert results[0]["booking_id"] == "A"
    assert output_path.exists()
    assert json.loads(output_path.read_text()) == results


def test_run_sweep_dry_run_does_not_write(tmp_path):
    watch_path = tmp_path / "watches.json"
    output_path = tmp_path / "opportunities.json"
    watch_path.write_text(json.dumps([{
        "booking_id": "A", "client_name": "Alice Test", "ship": "SS Grandeur",
        "cruise_line": "regent", "current_cabin": "Deluxe Veranda Suite",
        "current_price_pp": 3200.0, "voyage_url": "https://example.com/a", "active": True,
    }]))

    def fake_fetch(url):
        return "Penthouse Suite available at $3,100 per person."

    run_sweep(fetch_fn=fake_fetch, watch_path=watch_path, output_path=output_path, dry_run=True)
    assert not output_path.exists()


def test_load_watches_ignores_unknown_extra_keys(tmp_path):
    watch_path = tmp_path / "watches.json"
    watch_path.write_text(json.dumps([{
        "booking_id": "A", "client_name": "Alice", "ship": "SS Grandeur",
        "current_cabin": "Deluxe Veranda Suite", "current_price_pp": 3200.0,
        "active": True, "note": "extra field from the seed config",
    }]))
    watches = load_watches(watch_path)
    assert len(watches) == 1
    assert watches[0].booking_id == "A"


def test_load_watches_skips_inactive():
    watches = load_watches()  # real seed file — all currently inactive pending verification
    assert all(w.active for w in watches)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
