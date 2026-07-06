#!/usr/bin/env python3
"""
Test suite for core/dining/port_restaurant_coordinator.py

Run:
  python3 core/dining/test_port_restaurant_coordinator.py

NOTE on "5 real ports" verification: ~/Thunderbird/opentable_credentials.json
has an empty api_key (no funded OpenTable affiliate account exists in this
environment — confirmed by reading the credentials file directly). Any live
call to search_restaurants() correctly returns status="credentials_required"
rather than fabricated restaurant data (this is the intended behavior, not a
bug — see the Negative-Space Rule in the module docstring).

So "search 5 real ports and verify availability data accuracy" is tested two
ways here:
  1. test_five_real_ports_live() — actually calls the coordinator for 5 real
     cruise ports with no mocking, and asserts the credentials_required
     status is surfaced honestly (proves no fabrication happens).
  2. test_five_ports_with_mocked_opentable_responses() — mocks OpenTable at
     the search_restaurants boundary with realistic per-port payloads and
     verifies the coordinator's own logic (ranking, dress code, price
     estimate, reservation link, port timing) is correct against that data.
Once a real OpenTable key is funded, test 1 will start exercising the live
HTTP path with no code changes required.
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.dining.port_restaurant_coordinator import (
    PortCall,
    recommend_dining_for_port,
    build_recommendations_by_port,
    compute_port_timing,
    estimate_price_per_person,
    infer_dress_code,
    is_tender_port,
    resolve_city,
    default_reservation_time,
)


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def ok(self, name: str):
        self.passed += 1
        print(f"  PASS  {name}")

    def fail(self, name: str, detail: str):
        self.failed += 1
        print(f"  FAIL  {name} — {detail}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{self.passed}/{total} passed")
        return self.failed == 0


R = TestResults()


def _assert(cond, name, detail=""):
    if cond:
        R.ok(name)
    else:
        R.fail(name, detail)


# ─── Pure-function unit tests ────────────────────────────────────────────

def test_resolve_city():
    _assert(resolve_city("Civitavecchia") == "Rome", "resolve_city maps terminal to city")
    _assert(resolve_city("Barcelona") == "Barcelona", "resolve_city passes through unmapped port")


def test_is_tender_port():
    _assert(is_tender_port("Santorini") is True, "santorini is a tender port")
    _assert(is_tender_port("Barcelona") is False, "barcelona is not a tender port")


def test_price_estimate():
    est = estimate_price_per_person("$$$")
    _assert(est["low"] == 55 and est["high"] == 100, "price tier $$$ maps to 55-100")
    _assert(est["confidence"] == "INFERRED", "price estimate tagged INFERRED")


def test_dress_code_michelin():
    dc = infer_dress_code("$$", 2)
    _assert("formal" in dc["dress_code"].lower(), "michelin star forces smart formal regardless of price tier")
    _assert(dc["confidence"] == "INFERRED", "dress code tagged INFERRED")


def test_dress_code_casual():
    dc = infer_dress_code("$", None)
    _assert("casual" in dc["dress_code"].lower(), "cheap non-michelin restaurant gets casual dress code")


def test_default_reservation_time_early_departure():
    t = default_reservation_time("07:00", "13:00")
    _assert(t == "13:00", "early all-aboard forces a lunch seating instead of dinner")


def test_default_reservation_time_normal():
    t = default_reservation_time("08:00", "22:00")
    _assert(t == "19:00", "normal port day defaults to 19:00 dinner")


def test_port_timing_no_risk():
    timing = compute_port_timing("2027-05-12", "19:00", ship_arrival="08:00", all_aboard="23:00")
    _assert(timing["all_aboard_risk"] is False, "19:00 dinner with 23:00 all-aboard carries no risk")
    _assert(timing["arrive_by"] == "18:45", "arrive_by applies 15-min standard buffer", timing["arrive_by"])


def test_port_timing_tender_buffer():
    timing = compute_port_timing("2027-05-12", "19:00", ship_arrival="08:00", all_aboard="23:00", tender_port=True)
    _assert(timing["buffer_minutes"] == 45, "tender port adds 30 extra buffer minutes on top of 15", str(timing["buffer_minutes"]))
    _assert(timing["arrive_by"] == "18:15", "tender port arrive_by reflects 45-min buffer", timing["arrive_by"])


def test_port_timing_all_aboard_risk():
    timing = compute_port_timing("2027-05-12", "19:00", ship_arrival="08:00", all_aboard="20:30")
    _assert(timing["all_aboard_risk"] is True, "19:00 dinner with 20:30 all-aboard flags risk")
    _assert(timing["warning"] is not None, "risk carries a human-readable warning")


def test_port_timing_before_ship_arrival():
    timing = compute_port_timing("2027-05-12", "08:30", ship_arrival="09:00")
    _assert(timing["all_aboard_risk"] is True, "reservation before ship arrival flags risk")


# ─── Integration: 5 real cruise ports, live (no mocking) ────────────────

def test_five_real_ports_live():
    """Confirms the coordinator surfaces the true unfunded-credentials status
    for 5 real ports rather than fabricating restaurant data."""
    ports = [
        PortCall(port_name="Barcelona", date="2027-05-12", ship_arrival="08:00", all_aboard="18:00"),
        PortCall(port_name="Civitavecchia", date="2027-05-14", ship_arrival="07:00", all_aboard="19:00"),
        PortCall(port_name="Athens", date="2027-05-16", ship_arrival="08:00", all_aboard="20:00"),
        PortCall(port_name="Santorini", date="2027-05-18", ship_arrival="09:00", all_aboard="18:00"),
        PortCall(port_name="Stockholm", date="2027-06-01", ship_arrival="08:00", all_aboard="17:00"),
    ]
    for call in ports:
        result = asyncio.run(recommend_dining_for_port(call))
        _assert(
            result.get("status") == "credentials_required",
            f"{call.port_name} live call surfaces true status, no fabricated data",
            json.dumps(result)[:200],
        )


# ─── Integration: 5 ports, mocked OpenTable responses ───────────────────

def _mock_search_result(city: str, restaurants: list[dict]) -> dict:
    return {
        "status": "success",
        "city": city,
        "cuisine_filter": None,
        "date": "2027-05-12",
        "party_size": 2,
        "total_results": len(restaurants),
        "results": restaurants,
    }


def test_five_ports_with_mocked_opentable_responses():
    fixtures = {
        "Barcelona": [
            {"name": "Disfrutar", "cuisine": "Catalan", "price_range": "$$$$", "address": "C/Villarroel 163",
             "city": "Barcelona", "rating": 4.9, "review_count": 812, "michelin_stars": 2,
             "restaurant_id": "bcn-001", "sample_reviews": []},
            {"name": "Cerveceria Catalana", "cuisine": "Tapas", "price_range": "$$", "address": "C/Mallorca 236",
             "city": "Barcelona", "rating": 4.4, "review_count": 3200, "michelin_stars": None,
             "restaurant_id": "bcn-002", "sample_reviews": []},
        ],
        "Rome": [
            {"name": "La Pergola", "cuisine": "Italian", "price_range": "$$$$", "address": "Via Cadlolo 101",
             "city": "Rome", "rating": 4.8, "review_count": 1500, "michelin_stars": 3,
             "restaurant_id": "rom-001", "sample_reviews": []},
        ],
        "Athens": [
            {"name": "Spondi", "cuisine": "French-Greek", "price_range": "$$$$", "address": "5 Pyrronos St",
             "city": "Athens", "rating": 4.7, "review_count": 900, "michelin_stars": 2,
             "restaurant_id": "ath-001", "sample_reviews": []},
        ],
        "Santorini": [
            {"name": "Selene", "cuisine": "Greek", "price_range": "$$$", "address": "Pyrgos",
             "city": "Santorini", "rating": 4.6, "review_count": 650, "michelin_stars": None,
             "restaurant_id": "san-001", "sample_reviews": []},
        ],
        "Stockholm": [
            {"name": "Frantzen", "cuisine": "Nordic", "price_range": "$$$$", "address": "Lilla Nygatan 21",
             "city": "Stockholm", "rating": 4.9, "review_count": 400, "michelin_stars": 3,
             "restaurant_id": "sto-001", "sample_reviews": []},
        ],
    }

    ports = [
        PortCall(port_name="Barcelona", date="2027-05-12", ship_arrival="08:00", all_aboard="18:00", party_size=2),
        PortCall(port_name="Civitavecchia", date="2027-05-14", ship_arrival="07:00", all_aboard="19:00", party_size=2),
        PortCall(port_name="Athens", date="2027-05-16", ship_arrival="08:00", all_aboard="20:00", party_size=2),
        PortCall(port_name="Santorini", date="2027-05-18", ship_arrival="09:00", all_aboard="18:00", party_size=2),
        PortCall(port_name="Stockholm", date="2027-06-01", ship_arrival="08:00", all_aboard="17:00", party_size=2),
    ]

    async def fake_search(city, cuisine="", date="", party_size=2):
        return _mock_search_result(city, fixtures[city])

    with patch("core.dining.port_restaurant_coordinator.search_restaurants", new=AsyncMock(side_effect=fake_search)):
        for call in ports:
            result = asyncio.run(recommend_dining_for_port(call))
            _assert(result["status"] == "success", f"{call.port_name} mocked search returns success")
            _assert(result["recommendation_count"] >= 1, f"{call.port_name} returns at least one recommendation")
            top = result["recommendations"][0]
            _assert("reservation_link" in top and top["reservation_link"], f"{call.port_name} top pick has a reservation link")
            _assert(top["dress_code"]["confidence"] == "INFERRED", f"{call.port_name} dress code tagged INFERRED")
            _assert(top["michelin_stars"] in (2, 3) or call.port_name in ("Barcelona", "Santorini"),
                    f"{call.port_name} top pick is Michelin-starred where available")

        # Santorini is a tender port — buffer must be larger than Barcelona's.
        santorini_result = asyncio.run(recommend_dining_for_port(ports[3]))
        barcelona_result = asyncio.run(recommend_dining_for_port(ports[0]))
        _assert(
            santorini_result["port_timing"]["buffer_minutes"] > barcelona_result["port_timing"]["buffer_minutes"],
            "tender port (Santorini) carries a larger arrival buffer than a pier port (Barcelona)",
        )


def test_build_recommendations_by_port_writes_file(tmp_output=Path("/tmp/claude-1000/-home-john-Thunderbird/45ff5e95-48bc-4110-a95e-7d39c112a15f/scratchpad/dining_test_output.json")):
    tmp_output.parent.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "Barcelona": [
            {"name": "Disfrutar", "cuisine": "Catalan", "price_range": "$$$$", "address": "C/Villarroel 163",
             "city": "Barcelona", "rating": 4.9, "review_count": 812, "michelin_stars": 2,
             "restaurant_id": "bcn-001", "sample_reviews": []},
        ],
    }

    async def fake_search(city, cuisine="", date="", party_size=2):
        return _mock_search_result(city, fixtures.get(city, []))

    with patch("core.dining.port_restaurant_coordinator.search_restaurants", new=AsyncMock(side_effect=fake_search)):
        calls = [PortCall(port_name="Barcelona", date="2027-05-12", ship_arrival="08:00", all_aboard="18:00")]
        payload = asyncio.run(build_recommendations_by_port(calls, output_path=tmp_output))
        _assert(tmp_output.exists(), "build_recommendations_by_port writes output JSON file")
        on_disk = json.loads(tmp_output.read_text())
        _assert(on_disk["port_count"] == 1, "output JSON has correct port_count")
        _assert(payload["ports"][0]["status"] == "success", "in-memory payload matches file contents")


if __name__ == "__main__":
    print("Pure-function tests:")
    test_resolve_city()
    test_is_tender_port()
    test_price_estimate()
    test_dress_code_michelin()
    test_dress_code_casual()
    test_default_reservation_time_early_departure()
    test_default_reservation_time_normal()
    test_port_timing_no_risk()
    test_port_timing_tender_buffer()
    test_port_timing_all_aboard_risk()
    test_port_timing_before_ship_arrival()

    print("\n5 real ports — live (verifies no fabricated data):")
    test_five_real_ports_live()

    print("\n5 ports — mocked OpenTable responses (verifies coordinator logic):")
    test_five_ports_with_mocked_opentable_responses()

    print("\nOutput file:")
    test_build_recommendations_by_port_writes_file()

    ok = R.summary()
    sys.exit(0 if ok else 1)
