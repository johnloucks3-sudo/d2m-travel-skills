#!/usr/bin/env python3
"""
Offline tests for tcd.assignment — deterministic D -> T staff routing.

    python -m pytest tests/test_tcd_assignment.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import assignment  # noqa: E402


class TestAssignOwner:
    def test_tech_item_routes_to_sterling(self):
        item = {"title": "CI pipeline regression on deploy watchdog", "type": "mission"}
        assert assignment.assign_owner(item) == "Sterling"

    def test_finance_item_routes_to_harlan(self):
        item = {"title": "Commission audit for Q3 invoice batch"}
        assert assignment.assign_owner(item) == "Harlan"

    def test_research_item_routes_to_dembe(self):
        item = {"title": "Cruise market intel on Silversea itinerary pricing"}
        assert assignment.assign_owner(item) == "Dembe"

    def test_client_item_routes_to_dani(self):
        item = {"title": "Client booking confirmation email", "sourcePath": "gmail:123"}
        assert assignment.assign_owner(item) == "Dani"

    def test_unmatched_item_defaults_to_hale(self):
        item = {"title": "Something with no domain keywords at all"}
        assert assignment.assign_owner(item) == "Hale"

    def test_never_returns_empty(self):
        assert assignment.assign_owner({}) == "Hale"

    def test_first_matching_rule_wins(self):
        # "mission" (Sterling rule) appears before any Dani-rule keyword.
        item = {"title": "mission board client follow-up"}
        assert assignment.assign_owner(item) == "Sterling"
