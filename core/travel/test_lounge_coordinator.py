#!/usr/bin/env python3
"""
Lounge Coordinator — Test Cases
Dreams2Memories Travel, LLC

5 synthetic client card portfolios (no real client card data exists yet —
see config/client_credit_cards.json header) exercising: multi-network overlap,
Star Alliance/reciprocal notes, a no-lounge card, an unknown/unlisted card,
reservation-required (Centurion) vs walk-in networks, and a client with zero
lounge access.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lounge_coordinator import (
    build_lounge_access_plan,
    eligible_networks,
    lounges_at_airport,
    load_card_benefits,
    load_lounge_directory,
    pre_authorize_entry,
    tp_data_block,
    unknown_cards,
    unmatched_cards,
)


def test_amex_platinum_denver_centurion_reservation_required():
    print("\n" + "=" * 70)
    print("TEST 1: Amex Platinum + Chase Sapphire Reserve — DEN, reservation-required lounge")
    print("=" * 70)

    plan = build_lounge_access_plan(
        client_name="John & Susan Loucks",
        cards=["Amex Platinum", "Chase Sapphire Reserve"],
        legs=[{"airport_code": "DEN", "airline": "United"}],
    )

    assert "Centurion Lounge" in plan["networks"], plan["networks"]
    assert "Priority Pass Select" in plan["networks"]
    den_lounges = plan["legs"][0]["lounges"]
    names = {l["name"] for l in den_lounges}
    assert "Amex Centurion Lounge Denver" in names, names
    assert "Capital One Lounge Denver" not in names  # no Capital One card in portfolio

    centurion = next(l for l in den_lounges if l["network"] == "Centurion Lounge")
    assert centurion["entry_method"] == "RESERVATION_REQUIRED", centurion
    assert centurion["action_needed"] is not None

    united_club_or_pp = [l for l in den_lounges if l["network"] != "Centurion Lounge"]
    for l in united_club_or_pp:
        assert l["entry_method"] == "WALK_IN_VERIFIED", l

    print(f"  Networks: {sorted(plan['networks'].keys())}")
    print(f"  DEN lounges: {[l['name'] for l in den_lounges]}")
    print("  PASS")


def test_capital_one_venture_x_denver_own_lounge():
    print("\n" + "=" * 70)
    print("TEST 2: Capital One Venture X — DEN, Capital One-branded lounge")
    print("=" * 70)

    plan = build_lounge_access_plan(
        client_name="John & Melissa Furlow",
        cards=["Capital One Venture X"],
        legs=[{"airport_code": "DEN", "airline": None}],
    )

    names = {l["name"] for l in plan["legs"][0]["lounges"]}
    assert "Capital One Lounge Denver" in names, names
    assert "Amex Centurion Lounge Denver" not in names

    guest_entry = plan["networks"]["Priority Pass Select"]
    assert guest_entry["guests"] == 2
    print(f"  DEN lounges: {sorted(names)}")
    print("  PASS")


def test_amex_gold_no_lounge_access():
    print("\n" + "=" * 70)
    print("TEST 3: Amex Gold only — zero lounge access, flagged not silently dropped")
    print("=" * 70)

    plan = build_lounge_access_plan(
        client_name="Erik McLeod & Melissa McGlasson",
        cards=["Amex Gold"],
        legs=[{"airport_code": "DEN", "airline": None}, {"airport_code": "FCO", "airline": None}],
    )

    assert plan["networks"] == {}
    assert "Amex Gold" in plan["no_lounge_cards"]
    for leg in plan["legs"]:
        assert leg["lounges"] == []

    blocks = tp_data_block(plan)
    assert blocks == [], "TP block must be empty when there is nothing to tell the client"
    print(f"  no_lounge_cards: {plan['no_lounge_cards']}")
    print("  PASS")


def test_unknown_card_surfaced_not_silently_dropped():
    print("\n" + "=" * 70)
    print("TEST 4: Unrecognized card name — surfaced for research, not silently ignored")
    print("=" * 70)

    plan = build_lounge_access_plan(
        client_name="Kyle & Rosalie Kuklinski",
        cards=["Citi Prestige", "Bilt Mastercard"],
        legs=[{"airport_code": "MUC", "airline": "United"}],
    )

    assert plan["unknown_cards"] == ["Bilt Mastercard"], plan["unknown_cards"]
    assert "Priority Pass Select" in plan["networks"]  # from Citi Prestige
    print(f"  unknown_cards: {plan['unknown_cards']}")
    print("  PASS")


def test_multi_leg_star_alliance_reciprocal_note_preserved():
    print("\n" + "=" * 70)
    print("TEST 5: United Club Infinite — multi-leg itinerary, reciprocal-note lounge surfaced")
    print("=" * 70)

    plan = build_lounge_access_plan(
        client_name="Al Ely & Amy Darrow",
        cards=["United Club Infinite Card"],
        legs=[
            {"airport_code": "DEN", "airline": "United"},
            {"airport_code": "MUC", "airline": "United"},
            {"airport_code": "FCO", "airline": "United"},
        ],
    )

    assert "United Club" in plan["networks"]
    assert "Priority Pass Select" in plan["networks"]

    muc = next(leg for leg in plan["legs"] if leg["airport_code"] == "MUC")
    assert any(l["network"] == "United Club" for l in muc["lounges"])
    star_alliance_lounge = next(l for l in muc["lounges"] if l["network"] == "United Club")
    assert "note" in star_alliance_lounge, "reciprocal-access condition must survive to output"

    fco = next(leg for leg in plan["legs"] if leg["airport_code"] == "FCO")
    assert any(l["network"] == "United Club" for l in fco["lounges"])

    for leg in plan["legs"]:
        for l in leg["lounges"]:
            assert l["entry_method"] == "WALK_IN_VERIFIED", l

    blocks = tp_data_block(plan)
    assert len(blocks) == 3
    print(f"  Legs with lounge access: {[b['airport_code'] for b in blocks]}")
    print("  PASS")


def run_all():
    tests = [
        test_amex_platinum_denver_centurion_reservation_required,
        test_capital_one_venture_x_denver_own_lounge,
        test_amex_gold_no_lounge_access,
        test_unknown_card_surfaced_not_silently_dropped,
        test_multi_leg_star_alliance_reciprocal_note_preserved,
    ]
    for t in tests:
        t()
    print("\n" + "=" * 70)
    print(f"ALL {len(tests)} TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
