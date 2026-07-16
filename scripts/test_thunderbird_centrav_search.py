"""Regression tests for core/travel/thunderbird_centrav_search.py bug fixes
(hale_decisions.md 2026-07-09 Centrav scraper price-extraction bug).

Bug 1 — scope mismatch: FareTripTypeInput was hardcoded to 'OneWay'.
Bug 2 — price selector: `/^\\$[\\d,]+$/` only matches whole-dollar strings,
so it could never capture Centrav's actual per-fare-card totals (always
cents-precision, e.g. "$514.40") — only the coarser whole-dollar Fare
Matrix summary cells. Ground truth used below is real captured data from
core/travel/data/airline_test_COS_GRB_2026-09-06.json (Jul 9 diagnostic
run) plus the Commander's live-portal figure ($933.40/2pax round trip).
"""
from __future__ import annotations

from core.travel.thunderbird_centrav_search import (
    _price_parse,
    _trip_type_value,
    _trip_type_tab_label,
)


def test_trip_type_value_defaults_to_oneway():
    assert _trip_type_value("oneway") == "OneWay"
    assert _trip_type_value("anything_else") == "OneWay"


def test_trip_type_value_roundtrip_no_longer_hardcoded():
    assert _trip_type_value("roundtrip") == "RoundTrip"


def test_trip_type_tab_label_matches_value():
    assert _trip_type_tab_label("oneway") == "One Way"
    assert _trip_type_tab_label("roundtrip") == "Round Trip"


def test_price_parse_prefers_cents_precision_fare_card_over_matrix_summary():
    # Real values captured 2026-07-09 for COS->GRB Sep 6, 2 pax economy:
    # whole-dollar Fare Matrix summary cells ($434, $514, $617, $559, ...)
    # mixed with a precise fare-card total ($514.40) that the old regex
    # could never capture at all.
    raw = ["$434", "$514", "$617", "$559", "$890", "$525", "$647", "$514.40"]
    total, pp = _price_parse(raw, adults=2)
    assert total == 514.40
    assert pp == 257.20


def test_price_parse_falls_back_to_whole_dollar_when_no_cents_present():
    # Legacy behavior preserved when no cents-precision candidate exists.
    raw = ["$434", "$514", "$617"]
    total, pp = _price_parse(raw, adults=2)
    assert total == 434.0
    assert pp == 217.0


def test_price_parse_matches_commander_ground_truth_round_trip_figure():
    # Commander's live-portal round trip total: $933.40 / 2 pax.
    raw = ["$933.40", "$1,026.00", "$1,199"]
    total, pp = _price_parse(raw, adults=2)
    assert total == 933.40
    assert pp == 466.70


def test_price_parse_filters_implausible_values():
    raw = ["$12", "$99999", "$514.40"]
    total, pp = _price_parse(raw, adults=2)
    assert total == 514.40


def test_price_parse_empty_input_returns_none():
    assert _price_parse([], adults=2) == (None, None)
