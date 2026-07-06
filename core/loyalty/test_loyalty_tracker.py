#!/usr/bin/env python3
"""
Loyalty Tracker — Test Cases
Dreams2Memories Travel, LLC

TEST 1 uses the 10 real bookings currently in KNOWN_BOOKINGS to verify tier
assignment matches actual booking count (real data tops out at 2 voyages/
client — no current client reaches Gold/Platinum).
TEST 2 uses synthetic data to exercise Gold/Platinum thresholds and discount
code generation, since no real client currently qualifies.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from loyalty_tracker import (
    build_all_records,
    build_loyalty_record,
    count_voyages_per_client,
    generate_discount_code,
    load_benefits,
    tier_for_voyage_count,
)


def _fake_booking(client: str) -> dict:
    return {"client": client, "embark_date": date(2026, 1, 1)}


def test_real_bookings_ten_clients():
    print("\n" + "=" * 70)
    print("TEST 1: 10 REAL CLIENTS FROM KNOWN_BOOKINGS")
    print("=" * 70)

    sys.path.insert(0, str(Path(__file__).parent.parent / "scheduling"))
    from thunderbird_anchor_dates import KNOWN_BOOKINGS

    bookings = dict(list(KNOWN_BOOKINGS.items())[:10])
    assert len(bookings) == 10, f"expected 10 bookings, got {len(bookings)}"

    counts = count_voyages_per_client(bookings)
    benefits_cfg = load_benefits()
    records = build_all_records(bookings, benefits_cfg)

    # Independently recompute expected counts and compare
    expected_counts: dict[str, int] = {}
    for bk in bookings.values():
        expected_counts[bk["client"]] = expected_counts.get(bk["client"], 0) + 1

    for client, expected in expected_counts.items():
        assert counts[client] == expected, (
            f"{client}: counted {counts[client]}, expected {expected}"
        )
        rec = records[client]
        assert rec["voyage_count"] == expected
        expected_tier = tier_for_voyage_count(expected, benefits_cfg)
        assert rec["tier"] == expected_tier, (
            f"{client}: tier {rec['tier']} != expected {expected_tier}"
        )
        print(f"  {client}: {expected} voyage(s) -> {rec['tier']} (code={rec['discount_code']})")

    print(f"PASS — {len(expected_counts)} distinct clients, all tiers match booking count")


def test_synthetic_tier_thresholds():
    print("\n" + "=" * 70)
    print("TEST 2: SYNTHETIC TIER BOUNDARIES (Bronze/Silver/Gold/Platinum)")
    print("=" * 70)

    benefits_cfg = load_benefits()

    cases = [
        (0, "None"),
        (1, "Bronze"),
        (2, "Silver"),
        (3, "Silver"),
        (4, "Gold"),
        (5, "Gold"),
        (6, "Platinum"),
        (9, "Platinum"),
    ]
    for count, expected_tier in cases:
        actual = tier_for_voyage_count(count, benefits_cfg)
        assert actual == expected_tier, f"count={count}: got {actual}, expected {expected_tier}"
        print(f"  voyage_count={count} -> {actual} (expected {expected_tier})")

    print("PASS — all tier boundaries correct")


def test_gold_client_kuklinski_example():
    print("\n" + "=" * 70)
    print("TEST 3: HYPOTHETICAL GOLD-TIER CLIENT (4 prior voyages)")
    print("=" * 70)

    benefits_cfg = load_benefits()
    rec = build_loyalty_record("Kyle & Rosalie Kuklinski", 4, benefits_cfg)

    assert rec["tier"] == "Gold"
    assert rec["discount_pct"] == benefits_cfg["Gold"]["discount_pct"]
    assert rec["onboard_credit_usd"] == benefits_cfg["Gold"]["onboard_credit_usd"]
    assert rec["priority_cabin_selection"] is True
    assert rec["discount_code"].startswith("D2M-GOL-")

    print(f"  {rec['client']}: {rec['voyage_count']} voyages -> {rec['tier']}")
    print(f"  Discount: {rec['discount_pct']}% | OBC: ${rec['onboard_credit_usd']} | Code: {rec['discount_code']}")
    print("PASS — matches the Gold-tier use case from the spec")


def test_discount_code_deterministic_and_unique():
    print("\n" + "=" * 70)
    print("TEST 4: DISCOUNT CODE — DETERMINISTIC + UNIQUE PER CLIENT")
    print("=" * 70)

    code_a1 = generate_discount_code("Jane Doe", "Gold")
    code_a2 = generate_discount_code("Jane Doe", "Gold")
    code_b = generate_discount_code("John Smith", "Gold")

    assert code_a1 == code_a2, "same client+tier must produce same code"
    assert code_a1 != code_b, "different clients must produce different codes"
    assert code_a1.startswith("D2M-GOL-")

    print(f"  Jane Doe (Gold): {code_a1} == {code_a2}")
    print(f"  John Smith (Gold): {code_b}")
    print("PASS — codes are deterministic and client-unique")


def test_no_voyages_no_discount_code():
    print("\n" + "=" * 70)
    print("TEST 5: ZERO-VOYAGE CLIENT GETS NO TIER, NO CODE")
    print("=" * 70)

    benefits_cfg = load_benefits()
    rec = build_loyalty_record("New Prospect", 0, benefits_cfg)

    assert rec["tier"] == "None"
    assert rec["discount_code"] is None

    print(f"  {rec['client']}: tier={rec['tier']}, code={rec['discount_code']}")
    print("PASS")


if __name__ == "__main__":
    test_real_bookings_ten_clients()
    test_synthetic_tier_thresholds()
    test_gold_client_kuklinski_example()
    test_discount_code_deterministic_and_unique()
    test_no_voyages_no_discount_code()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
