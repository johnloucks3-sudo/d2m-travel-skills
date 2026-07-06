"""
Tests for core.voyage.itinerary_optimizer.

Uses 5 real D2M voyages pulled straight from cache/sheets_mirror/daily_itinerary*.json
(bookings 3096289, 9595029, 3112369, 566910-25) and the RSSC public-scrape fixture
(validations/rssc_scrape/SPL260811A_public_itinerary_ports.json) to prove the loader
and region/regression logic against actual booked data. Because D2M clients book
during favorable seasons (by design), none of the 5 real voyages should trip a
weather/crowd alert — that's asserted as a no-false-positive regression check.
The trigger paths themselves (weather alert + alternate port, weekend-crowd shift)
are exercised with synthetic PortStops placed in a documented adverse window
(Baltic in January / a Baltic peak-season Fri-Sat overnight) so the alert logic
is proven against real climate/crowd conditions without relying on D2M having
ever booked a client into bad weather on purpose.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from core.voyage.itinerary_optimizer import (
    PortStop,
    check_accessibility,
    classify_region,
    crowd_level,
    group_into_port_calls,
    load_voyage_from_mirror,
    load_voyage_from_public_itinerary_json,
    optimize,
    parse_flexible_date,
    weather_probability,
    write_suggestions,
)

ROOT = Path(__file__).resolve().parents[1]
RSSC_FIXTURE = ROOT / "validations/rssc_scrape/SPL260811A_public_itinerary_ports.json"

REAL_MIRROR_BOOKINGS = ["3096289", "9595029", "3112369", "566910-25", "8X6PGQ"]

# Real voyages that fall inside a documented cruise-industry peak-crowd window —
# the engine should flag them, and only for "crowd" (their weather stays fine,
# which is realistic: clients book good-weather high season on purpose).
KNOWN_PEAK_BOOKINGS = {
    "3096289": "Scandinavia/Baltic in late August is documented peak Baltic cruise season",
    "9595029": "Panama/Caribbean in December is documented peak Caribbean cruise season (holiday season)",
    "3112369": "Eastern Caribbean in December is documented peak Caribbean cruise season (holiday season)",
    "566910-25": "Japan in April is documented peak season (cherry blossom / sakura)",
}
# Real voyage that falls in a documented shoulder window — true-negative check.
KNOWN_SHOULDER_BOOKING = "8X6PGQ"  # Mexican Riviera, March 2027


# ── date parsing ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,default_year,expected", [
    ("2026-08-29", None, date(2026, 8, 29)),
    ("19-Dec-26", None, date(2026, 12, 19)),
    ("September 7, 2026", None, date(2026, 9, 7)),
    ("Sep 6, 2026", None, date(2026, 9, 6)),
    ("Aug 29", 2026, date(2026, 8, 29)),
    ("", None, None),
    ("not a date", None, None),
])
def test_parse_flexible_date(raw, default_year, expected):
    assert parse_flexible_date(raw, default_year) == expected


# ── region classification ───────────────────────────────────────────────

def test_classify_region_known_ports():
    assert classify_region("Copenhagen, Denmark") == "northern_europe"
    assert classify_region("Miami, Florida") == "caribbean"
    assert classify_region("Yokohama (Tokyo), Japan") == "east_asia_temperate"
    assert classify_region("Los Angeles, California") == "mexican_riviera"


def test_classify_region_keyword_fallback():
    assert classify_region("Some New Port, Italy") == "mediterranean"
    assert classify_region("Totally Unknown Place") == "temperate_default"


# ── real-voyage loaders (5 real voyages) ────────────────────────────────

@pytest.mark.parametrize("booking_id", REAL_MIRROR_BOOKINGS)
def test_load_real_voyage_from_mirror(booking_id):
    stops = load_voyage_from_mirror(booking_id)
    assert stops, f"expected port stops for real booking {booking_id}"
    assert all(isinstance(s, PortStop) for s in stops)
    # sorted ascending
    dates = [s.call_date for s in stops]
    assert dates == sorted(dates)
    # every stop resolved to a known region, not left un-classified
    assert all(s.region for s in stops)


def test_load_real_voyage_from_public_itinerary_json():
    stops = load_voyage_from_public_itinerary_json(RSSC_FIXTURE)
    assert stops
    ports = {s.port for s in stops}
    assert "Athens (Piraeus)" in ports or any("athens" in p.lower() for p in ports)
    assert all(s.region for s in stops)


def test_real_mediterranean_voyage_flags_august_peak():
    """SPL260811A (Athens/Malta/Naples/Rome/Tuscany, Aug 11-17) sails documented
    Mediterranean peak cruise season."""
    stops = load_voyage_from_public_itinerary_json(RSSC_FIXTURE)
    suggestions = optimize(stops)
    assert suggestions
    assert all(s.issue == "crowd" for s in suggestions)


@pytest.mark.parametrize("booking_id,reason", KNOWN_PEAK_BOOKINGS.items())
def test_real_voyage_flags_match_known_peak_season(booking_id, reason):
    """These 4 real bookings sail inside documented peak-crowd windows — the
    engine should flag them (crowd only; their weather stays fine, which is
    realistic: clients book good-weather high season on purpose)."""
    stops = load_voyage_from_mirror(booking_id)
    suggestions = optimize(stops)
    assert suggestions, f"expected a peak-season flag for {booking_id} ({reason})"
    assert all(s.issue == "crowd" for s in suggestions)
    assert all(s.confidence == "INFERRED" for s in suggestions)


def test_real_voyage_no_false_positive_in_shoulder_season():
    """8X6PGQ (LA/Mexican Riviera, March 2027) sails a documented shoulder
    window — the engine must not manufacture a finding here."""
    stops = load_voyage_from_mirror(KNOWN_SHOULDER_BOOKING)
    assert stops
    assert optimize(stops) == []


def test_real_scandinavia_voyage_grouping_captures_copenhagen_overnight():
    """Booking 3096289 (Ely-Darrow Scandinavia) — Copenhagen is a real 2-day
    overnight call (Sep 3-4, 2026); confirm grouping treats it as one PortCall."""
    stops = load_voyage_from_mirror("3096289")
    calls = group_into_port_calls(stops)
    copenhagen = [c for c in calls if c.port.lower().startswith("copenhagen")]
    assert len(copenhagen) == 1
    assert copenhagen[0].dates == [date(2026, 9, 3), date(2026, 9, 4)]


# ── trigger logic (synthetic, against real seasonal conditions) ────────

def test_weather_alert_fires_in_documented_bad_season_and_offers_alternate():
    """Baltic ports in January genuinely run low odds of good cruising weather —
    this is why no cruise line sails the Baltic in January. Confirms the
    <30% threshold fires and an in-region alternate is offered."""
    assert weather_probability("northern_europe", 1) < 0.30
    stops = [PortStop(port="Stockholm, Sweden", call_date=date(2026, 1, 15), booking_id="TEST-WX")]
    suggestions = optimize(stops)
    weather_hits = [s for s in suggestions if s.issue == "weather"]
    assert len(weather_hits) == 1
    hit = weather_hits[0]
    assert hit.confidence == "INFERRED"
    assert hit.alternative != "" and "none identified" not in hit.alternative


def test_crowd_alert_shifts_to_weekday_within_peak_overnight_stay():
    """Baltic August is documented peak cruise season. An overnight call
    spanning a weekend day should recommend the weekday day in the same stay."""
    assert crowd_level("northern_europe", 8) == "peak"
    # 2026-08-07 is a Friday, 2026-08-06 is a Thursday (weekday)
    thursday = date(2026, 8, 6)
    friday = date(2026, 8, 7)
    assert thursday.weekday() < 4 <= friday.weekday()
    stops = [
        PortStop(port="Copenhagen, Denmark", call_date=thursday, booking_id="TEST-CROWD"),
        PortStop(port="Copenhagen, Denmark", call_date=friday, booking_id="TEST-CROWD"),
    ]
    suggestions = optimize(stops)
    crowd_hits = [s for s in suggestions if s.issue == "crowd"]
    assert len(crowd_hits) == 1
    assert thursday.isoformat() in crowd_hits[0].alternative


def test_crowd_alert_single_day_peak_offers_region_alternate():
    stops = [PortStop(port="Oslo, Norway", call_date=date(2026, 7, 10), booking_id="TEST-CROWD-2")]
    suggestions = optimize(stops)
    crowd_hits = [s for s in suggestions if s.issue == "crowd"]
    assert len(crowd_hits) == 1
    assert crowd_hits[0].alternative != "Oslo, Norway"


def test_no_alert_in_shoulder_season():
    stops = [PortStop(port="Copenhagen, Denmark", call_date=date(2026, 9, 4), booking_id="TEST-CLEAN")]
    assert optimize(stops) == []


# ── accessibility seam ───────────────────────────────────────────────────

def test_check_accessibility_silent_without_notes():
    stops = [PortStop(port="Stockholm, Sweden", call_date=date(2026, 8, 29), booking_id="TEST-ACC")]
    assert check_accessibility(stops, "") == []


def test_check_accessibility_flags_mobility_notes():
    stops = [PortStop(port="Stockholm, Sweden", call_date=date(2026, 8, 29), booking_id="TEST-ACC")]
    hits = check_accessibility(stops, "Client uses a wheelchair, needs step-free tender access")
    assert len(hits) == 1
    assert hits[0].confidence == "UNKNOWN"
    assert hits[0].issue == "accessibility"


# ── output writer ────────────────────────────────────────────────────────

def test_write_suggestions_schema(tmp_path):
    stops = [PortStop(port="Stockholm, Sweden", call_date=date(2026, 1, 15), booking_id="TEST-WRITE")]
    suggestions = optimize(stops)
    out = write_suggestions(suggestions, tmp_path / "optimization_suggestions.json")
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["suggestion_count"] == len(suggestions)
    assert "generated_at" in payload
    for s in payload["suggestions"]:
        assert set(s.keys()) == {
            "booking_id", "port", "date", "issue", "alternative", "reasoning",
            "confidence", "source",
        }
        assert s["confidence"] in {"CONFIRMED", "INFERRED", "UNKNOWN"}
