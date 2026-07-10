"""Tests for the birthday/anniversary trip suggestion matching engine.

Fixtures: 5 clients with known preferences, 6 upcoming voyages.
Covers date-window logic (next_occurrence, is_within_window, voyage_in_horizon)
and the pure matching engine (match_clients_to_voyages).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.client.thunderbird_milestone_matcher import (
    ClientMilestone,
    next_occurrence,
    is_within_window,
    voyage_in_horizon,
    match_clients_to_voyages,
    MILESTONE_WINDOW_DAYS,
)

TODAY = date(2026, 7, 6)


# ---------------------------------------------------------------------------
# Date-window helpers
# ---------------------------------------------------------------------------

def test_next_occurrence_future_this_year():
    assert next_occurrence(8, 31, TODAY) == date(2026, 8, 31)


def test_next_occurrence_rolls_to_next_year_if_passed():
    assert next_occurrence(1, 15, TODAY) == date(2027, 1, 15)


def test_next_occurrence_today_is_valid():
    assert next_occurrence(TODAY.month, TODAY.day, TODAY) == TODAY


def test_next_occurrence_feb29_non_leap_rolls_to_mar1():
    result = next_occurrence(2, 29, date(2027, 1, 1))
    assert result == date(2027, 3, 1)


def test_is_within_window_true_inside_90_days():
    assert is_within_window(45) is True


def test_is_within_window_false_beyond_90_days():
    assert is_within_window(91) is False


def test_is_within_window_false_negative():
    assert is_within_window(-1) is False


def test_voyage_in_horizon_excludes_past_departure():
    assert voyage_in_horizon("2020-01-01", TODAY) is False


def test_voyage_in_horizon_excludes_too_far_out():
    # 30 months out, default max is 18
    assert voyage_in_horizon("2029-01-06", TODAY) is False


def test_voyage_in_horizon_excludes_too_soon():
    # 1 month out, default min is 3
    assert voyage_in_horizon("2026-08-06", TODAY) is False


def test_voyage_in_horizon_includes_mid_window():
    # ~8 months out
    assert voyage_in_horizon("2027-03-06", TODAY) is True


# ---------------------------------------------------------------------------
# Fixtures: 5 clients, 6 voyages
# ---------------------------------------------------------------------------

def _client(name, milestone_type, month, day, lines=None, regions=None, today=TODAY):
    occ = next_occurrence(month, day, today)
    return ClientMilestone(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        milestone_type=milestone_type,
        month=month,
        day=day,
        milestone_date=occ,
        days_until=(occ - today).days,
        preferred_lines=lines or [],
        preferred_regions=regions or [],
        source_dossier=f"{name}_dossier",
    )


def make_five_clients(today=TODAY):
    return [
        # 1. Birthday in 30 days, prefers Silversea + Mediterranean
        _client("Amy Ely", "birthday", 8, 5, lines=["Silversea"], regions=["Mediterranean"], today=today),
        # 2. Anniversary in 60 days, prefers Regent Seven Seas
        _client("Bill Spencer", "anniversary", 9, 4, lines=["Regent Seven Seas"], today=today),
        # 3. Birthday in 10 days, prefers Viking + Panama Canal
        _client("Carla Nichols", "birthday", 7, 16, lines=["Viking"], regions=["Panama Canal"], today=today),
        # 4. Anniversary in 89 days (just inside window), no strong preference
        _client("Dana Furlow", "anniversary", 10, 3, today=today),
        # 5. Birthday in 5 days, prefers Oceania + Caribbean
        _client("Erik McLeod", "birthday", 7, 11, lines=["Oceania"], regions=["Caribbean"], today=today),
    ]


def make_six_voyages():
    return [
        {  # matches Amy (Silversea + Mediterranean)
            "line": "Silversea Cruises", "ship": "Silver Nova", "departure": "2027-03-06",
            "nights": 10, "from_port": "Barcelona", "region": "Mediterranean", "price_ind": 8500.0,
        },
        {  # matches Bill (Regent Seven Seas)
            "line": "Regent Seven Seas Cruises", "ship": "Seven Seas Grandeur", "departure": "2027-01-10",
            "nights": 12, "from_port": "Miami", "region": "Caribbean", "price_ind": 14200.0,
        },
        {  # matches Carla (Viking + Panama Canal)
            "line": "Viking Ocean Cruises", "ship": "Viking Mars", "departure": "2027-02-15",
            "nights": 16, "from_port": "Los Angeles", "region": "Panama Canal", "price_ind": 11000.0,
        },
        {  # matches Erik (Oceania + Caribbean)
            "line": "Oceania Cruises", "ship": "Oceania Vista", "departure": "2027-01-20",
            "nights": 10, "from_port": "Miami", "region": "Caribbean", "price_ind": 6200.0,
        },
        {  # generic fallback, no strong preference match for anyone
            "line": "Cunard", "ship": "Queen Anne", "departure": "2027-04-01",
            "nights": 7, "from_port": "Southampton", "region": "Transatlantic", "price_ind": 3200.0,
        },
        {  # out-of-horizon voyage (too far out) — should never surface
            "line": "Regent Seven Seas Cruises", "ship": "Seven Seas Mariner", "departure": "2029-06-01",
            "nights": 30, "from_port": "Sydney", "region": "Asia & Pacific", "price_ind": 40000.0,
        },
    ]


# ---------------------------------------------------------------------------
# Matching engine tests
# ---------------------------------------------------------------------------

def test_all_five_clients_get_suggestions():
    clients = make_five_clients()
    voyages = make_six_voyages()[:-1]  # drop the out-of-horizon one, as production would
    suggestions = match_clients_to_voyages(clients, voyages)
    assert len(suggestions) == 5
    for s in suggestions:
        assert len(s["options"]) > 0


def test_preference_match_ranked_first():
    clients = make_five_clients()
    voyages = make_six_voyages()[:-1]
    suggestions = match_clients_to_voyages(clients, voyages)

    amy = next(s for s in suggestions if s["client"]["name"] == "Amy Ely")
    assert amy["options"][0]["line"] == "Silversea Cruises"
    assert amy["options"][0]["preference_match"] is True


def test_line_preference_matches_across_full_line_name():
    clients = make_five_clients()
    voyages = make_six_voyages()[:-1]
    suggestions = match_clients_to_voyages(clients, voyages)

    bill = next(s for s in suggestions if s["client"]["name"] == "Bill Spencer")
    assert bill["options"][0]["line"] == "Regent Seven Seas Cruises"
    assert bill["options"][0]["preference_match"] is True


def test_no_preference_client_still_gets_top_n_fallback():
    clients = make_five_clients()
    voyages = make_six_voyages()[:-1]
    suggestions = match_clients_to_voyages(clients, voyages, top_n=3)

    dana = next(s for s in suggestions if s["client"]["name"] == "Dana Furlow")
    assert len(dana["options"]) == 3
    assert all(o["preference_match"] is False for o in dana["options"])


def test_top_n_respected():
    clients = make_five_clients()
    voyages = make_six_voyages()[:-1]
    suggestions = match_clients_to_voyages(clients, voyages, top_n=2)
    for s in suggestions:
        assert len(s["options"]) <= 2


def test_price_label_present_for_priced_voyage():
    clients = [make_five_clients()[0]]
    voyages = [make_six_voyages()[0]]
    suggestions = match_clients_to_voyages(clients, voyages)
    assert "indicative" in suggestions[0]["options"][0]["price_label"]
    assert "8,500" in suggestions[0]["options"][0]["price_label"]


def test_days_until_all_clients_within_90_day_window():
    clients = make_five_clients()
    for c in clients:
        assert is_within_window(c.days_until, MILESTONE_WINDOW_DAYS), (
            f"{c.name} milestone {c.days_until} days out — fixture setup should keep all 5 in-window"
        )


def test_empty_client_list_returns_empty_suggestions():
    assert match_clients_to_voyages([], make_six_voyages()) == []


def test_no_matching_voyages_still_returns_client_entry_with_no_options():
    clients = [make_five_clients()[0]]
    suggestions = match_clients_to_voyages(clients, [])
    assert len(suggestions) == 1
    assert suggestions[0]["options"] == []
