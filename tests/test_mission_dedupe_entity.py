"""Tests for entity-signature duplicate detection on the mission board.

THE INCIDENT (2026-07-29)
Twelve separate missions were created between Jul 15 and Jul 26 for ONE
$24,798 final payment. `scripts/generate_weekly_report.py` appended straight to
board["missions"], bypassing the one-and-done guard; and even had it called the
guard, `_find_open_duplicate` compares title WORD SETS, which a generator that
rewords the title every run defeats trivially.

Re-detecting a problem is not resolving it (MAST FM-1.3, step repetition).
These tests pin the fix: identity comes from the MONEY or the BOOKING REF, not
from the verb.
"""
from __future__ import annotations

import pytest

from OpsCenter.mission_board_sync import (
    _entity_matches,
    _entity_signature, _find_entity_duplicate, _find_open_duplicate)


# The twelve real titles from the incident.
REAL_FPD_TITLES = [
    "Surface Loucks Grandeur FPD — $24,798 due August 1",
    "Surface Loucks Grandeur FPD reminder at 7-day mark",
    "Commander review of Loucks Grandeur FPD — $24,798 due Aug 1",
    "Confirm Loucks Grandeur FPD payment mechanism before August 1",
    "Pay Loucks Grandeur FPD before August 1 deadline",
    "Surface Loucks FPD $24,798 to Commander — Aug 1 deadline",
    "Loucks Grandeur FPD — confirm payment track by July 25",
    "Confirm or escalate Loucks Grandeur FPD payment by July 31",
    "Confirm Loucks Grandeur FPD payment or contingency before August 1",
    "Confirm and execute Loucks Grandeur FPD — $24,798 due Aug 1",
    "Surface and execute Loucks Grandeur FPD before August 1",
    "Escalate Loucks Grandeur FPD for Commander payment authorization",
]


def _open(title, desc=""):
    return {"id": "MISSION-X", "title": title, "description": desc,
            "status": "pending_review"}


# ------------------------------------------------------------- signature

def test_money_plus_commitment_noun_is_a_signature():
    sig = _entity_signature("Surface Loucks Grandeur FPD — $24,798 due August 1")
    assert sig and "24798" in sig["amounts"]


def test_reworded_titles_share_one_signature():
    """The core fix: different verbs, same money, same identity."""
    a = _entity_signature("Pay Loucks Grandeur FPD $24,798 before Aug 1")
    b = _entity_signature("Escalate Loucks Grandeur FPD — $24,798 due Aug 1")
    assert _entity_matches(a, b)


def test_money_without_a_commitment_noun_is_not_a_signature():
    """'$24,798 in revenue' must not collide with '$24,798 due'."""
    assert _entity_signature("Q3 revenue reached $24,798 across bookings") is None


def test_booking_reference_is_a_signature():
    sig = _entity_signature("Loucks invoice #3122006 unpaid")
    assert sig and "3122006" in sig["refs"]


def test_shared_booking_ref_wins_even_when_amounts_differ():
    """A deposit and a balance on the SAME booking are the same commitment
    thread; the reference is the stronger signal."""
    a = _entity_signature("Loucks invoice #3122006 deposit $2,000")
    b = _entity_signature("Loucks invoice #3122006 balance due $24,798")
    assert _entity_matches(a, b)


def test_one_shared_word_is_not_enough_to_merge():
    """Guards against over-merging on a single common token."""
    a = _entity_signature("Loucks FPD deadline")
    b = _entity_signature("Furlow FPD deadline")
    assert not _entity_matches(a, b)


def test_no_signal_returns_none_rather_than_guessing():
    assert _entity_signature("Fix anansi fallback") is None
    assert _entity_signature("Mission Board capability") is None


# --------------------------------------------------------- duplicate find

def test_catches_the_real_twelve_as_duplicates_of_the_first():
    """Regression: all twelve must collapse onto one open mission."""
    board = [_open(REAL_FPD_TITLES[0])]
    for t in REAL_FPD_TITLES[1:]:
        # Titles carrying the amount are caught by entity signature; the rest
        # by the existing word-set fallback. Every one must be caught by ONE
        # of the two — that is the property that matters.
        hit = _find_entity_duplicate(board, t) or _find_open_duplicate(board, t)
        assert hit is not None, f"NOT deduped: {t!r}"


def test_amount_in_description_still_matches_when_title_omits_it():
    """The generator often puts the number only in the body."""
    board = [_open("Loucks Grandeur FPD", "final payment of $24,798 due Aug 1")]
    hit = _find_entity_duplicate(
        board, "Escalate Grandeur payment", "FPD balance due $24,798")
    assert hit is not None


def test_different_amounts_are_not_merged():
    """A false merge is worse than a duplicate — it hides real work."""
    board = [_open("Furlow FPD — $8,200 due Sep 1")]
    assert _find_entity_duplicate(board, "Loucks FPD — $24,798 due Aug 1") is None


def test_closed_missions_do_not_suppress_a_new_one():
    """Once resolved, a recurrence is legitimately new work."""
    board = [{"id": "M-1", "title": "Loucks FPD $24,798 due Aug 1",
              "description": "", "status": "completed"}]
    assert _find_entity_duplicate(board, "Loucks FPD $24,798 due Aug 1") is None


def test_genuinely_distinct_work_is_not_merged():
    board = [_open("Fix anansi fallback")]
    assert _find_entity_duplicate(board, "Source air options for Scandinavia") is None
    assert _find_open_duplicate(board, "Source air options for Scandinavia") is None


def test_empty_board_is_safe():
    assert _find_entity_duplicate([], "Loucks FPD $24,798 due Aug 1") is None


def test_malformed_missions_do_not_crash_the_scan():
    board = [{"id": "M-1"}, {"title": None, "status": "active"}, _open("x")]
    assert _find_entity_duplicate(board, "Loucks FPD $24,798 due") is None


# ---------------------------------------------- false-merge guards (sweep)
# A 2026-07-29 duplicate sweep over the live board produced a bogus 15-mission
# cluster spanning a rental car, orphaned systemd units, and a client transfer
# dispute. Cause: `parties` were harvested from long DESCRIPTION prose, so
# unrelated work linked through generic tokens. These pin the fix.

from OpsCenter.mission_board_sync import _rarity_predicate


def test_parties_come_from_title_only_not_description_prose():
    """Generic words in a long description must not become identity."""
    sig = _entity_signature(
        "GRB Rental Car",
        "Commander's booking is live in TESS; verify against the client "
        "itinerary and confirm the payment record only after review.")
    assert sig is not None
    for junk in ("booking", "live", "tess", "client", "itinerary", "verify"):
        assert junk not in sig["parties"], f"{junk!r} leaked in from description"


def test_unrelated_ops_work_does_not_merge_via_description():
    """The exact bogus pairing from the sweep."""
    board = [_open("Resolve McLeod lifecycle contact and transfer dispute",
                   "8 days overdue; booking data live in TESS, verify payment")]
    hit = _find_entity_duplicate(
        board, "GRB Rental Car",
        "booking is live; confirm the payment record only")
    assert hit is None


def test_systemd_units_do_not_merge_with_tess_pipeline():
    board = [_open("Restore TESS pipeline and run commission cross-check",
                   "commission data live against MISSION-624")]
    hit = _find_entity_duplicate(
        board, "Five orphaned systemd units point at deleted scripts",
        "all disabled; live scripts recommend removal per MISSION-646")
    assert hit is None


def test_common_client_name_alone_cannot_identify_a_duplicate():
    """A busy client appears across many unrelated missions, so the name
    identifies nothing on its own."""
    board = [_open(f"Kuklinski task {i} payment") for i in range(20)]
    is_rare = _rarity_predicate(board)
    assert not is_rare("kuklinski")


def test_rare_shared_token_still_identifies_a_duplicate():
    """Furlow+Kuklinski FPD audits are genuinely one job."""
    board = ([_open(f"Kuklinski routing item {i} payment") for i in range(20)]
             + [_open("FPD deadline audit — Furlow and Kuklinski")])
    hit = _find_entity_duplicate(
        board, "Complete FPD audit for Furlow and Kuklinski")
    assert hit is not None
    assert hit["title"] == "FPD deadline audit — Furlow and Kuklinski"


def test_rarity_predicate_ignores_closed_missions():
    board = [{"id": f"M{i}", "title": "Kuklinski payment", "description": "",
              "status": "completed"} for i in range(30)]
    assert _rarity_predicate(board)("kuklinski")
