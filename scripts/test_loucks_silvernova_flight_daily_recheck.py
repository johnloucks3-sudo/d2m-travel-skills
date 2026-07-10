"""Tests for scripts/loucks_silvernova_flight_daily_recheck.py's parsing
logic. Regression test for a real bug found on the first live run:
the price regex matched a 'Markup Limit $408.00' line item as if it were
a fare, since it wasn't anchored to the CASH suffix every real fare card
uses."""
from __future__ import annotations

import json

import scripts.loucks_silvernova_flight_daily_recheck as recheck


def test_extract_lowest_price_ignores_markup_limit():
    text = (
        "Consolidator Fare $5,024.00 CASH\n"
        "Business Class Standard\n"
        "You can add a service fee separately.\n"
        "Markup Limit $408.00\n"
        "Cruise Fare $6,974.00 CASH\n"
    )
    assert recheck._extract_lowest_price(text) == 5024.0


def test_extract_lowest_price_none_when_no_cash_fares():
    text = "Markup Limit $408.00\nCash Discount -$122.05\n"
    assert recheck._extract_lowest_price(text) is None


def test_extract_ist_layover_hours_parses_duration():
    text = "IST -> VCE ... 13h 10m connection at IST"
    hours = recheck._extract_ist_layover_hours(text)
    assert hours == 13 + 10 / 60.0


def test_append_history_matches_existing_schema(tmp_path, monkeypatch):
    hist_file = tmp_path / "fare_history.json"
    hist_file.write_text("[]")
    monkeypatch.setattr(recheck, "FARE_HISTORY", hist_file)
    recheck._append_history("test-watch", 1234.0, "test note")
    data = json.loads(hist_file.read_text())
    assert len(data) == 1
    assert data[0]["watch_id"] == "test-watch"
    assert data[0]["price_pp"] == 1234.0
    assert data[0]["total"] == 2468.0
    assert "timestamp" in data[0]
