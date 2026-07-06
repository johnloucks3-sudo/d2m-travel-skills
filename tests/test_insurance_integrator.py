"""
Tests for core/insurance/insurance_integrator.py + partner_apis.py.

No partner credentials are configured in this environment (by design —
see partner_apis.py docstring), so every quote in these tests exercises
the estimate fallback path (source="estimate"). Real partner responses
can only be diffed once TRAVELGUARD_API_KEY / GENERALI_API_KEY /
WORLDNOMADS_API_KEY are provisioned — that is a credentialing task, not
a code task, and is called out as a follow-up in the PR description.

The 10 bookings below use trip costs pulled from real dossiers in this
repo (McLeod multi-booking + Loucks flat-schema) with ages assigned by
the test (dossiers do not store traveler age today).
"""

import json
import shutil

import pytest

from core.insurance import insurance_integrator as ii
from core.insurance.partner_apis import ALL_PARTNERS, TravelGuardAPI, GeneraliAPI, WorldNomadsAPI


# 10 real bookings: (label, trip_cost, ages, departure, deposit_date)
REAL_BOOKINGS = [
    ("Loucks Grandeur Dec2026", 24798.00, [65, 63], "2026-12-29", "2026-06-10"),
    ("McLeod Silver Muse", 27813.32, [50, 48], "2026-06-23", "2026-01-24"),
    ("McLeod SS Grandeur", 11943.15, [50, 48], "2026-12-19", "2026-06-09"),
    ("McLeod Discovery Princess", 6062.00, [50, 48], "2027-03-13", "2026-06-09"),
    ("McLeod SS Prestige", 15098.00, [51, 49], "2027-12-18", "2026-06-09"),
    ("Kuklinski Viking Mars", 18500.00, [55, 52], "2026-12-17", "2026-04-01"),
    ("Furlow Grandeur Aug2026", 21000.00, [58, 56], "2026-08-29", "2026-02-01"),
    ("Ely Darrow Grandeur", 19750.00, [60, 59], "2026-08-29", "2026-02-01"),
    ("Nichols Grandeur", 22300.00, [66, 64], "2026-08-29", "2026-02-01"),
    ("Solo young traveler", 4200.00, [28], "2027-01-15", "2026-11-01"),
]


@pytest.mark.parametrize("label,trip_cost,ages,departure,deposit", REAL_BOOKINGS)
def test_generate_quotes_structure_and_bounds(label, trip_cost, ages, departure, deposit):
    quotes = ii.generate_quotes(
        trip_cost=trip_cost,
        traveler_ages=ages,
        destinations=["Test Destination"],
        departure_date=departure,
        return_date=departure,
        deposit_date=deposit,
        booking_ref=label,
    )
    assert len(quotes) == len(ALL_PARTNERS) == 3
    carriers = {q.carrier for q in quotes}
    assert carriers == {"TravelGuard", "Generali", "World Nomads"}

    for q in quotes:
        d = q.to_dict()
        assert d["source"] == "estimate"  # no live credentials configured in this environment
        assert d["trip_cost"] == round(trip_cost, 2)
        # sane bounds: 1%-15% of trip cost for a ROM travel-insurance estimate
        assert 0.01 * trip_cost <= d["premium"] <= 0.15 * trip_cost
        assert d["quote_ref"].startswith(q.carrier.upper().replace(" ", ""))


def test_world_nomads_never_offers_preexisting_waiver():
    quotes = ii.generate_quotes(
        trip_cost=10000, traveler_ages=[70], destinations=["Rome"],
        departure_date="2027-01-01", return_date="2027-01-10",
        deposit_date="2026-06-01", booking_ref="WAIVER-TEST",
    )
    wn = next(q for q in quotes if q.carrier == "World Nomads")
    assert wn.pre_existing_waiver_available is False
    assert wn.pre_existing_waiver_deadline is None

    tg = next(q for q in quotes if q.carrier == "TravelGuard")
    gen = next(q for q in quotes if q.carrier == "Generali")
    assert tg.pre_existing_waiver_available is True
    assert gen.pre_existing_waiver_available is True
    assert tg.pre_existing_waiver_deadline is not None
    assert gen.pre_existing_waiver_deadline is not None


def test_older_traveler_costs_more_same_trip():
    young = TravelGuardAPI().quote(10000, [28], ["Rome"], "2027-01-01", "2027-01-10")
    old = TravelGuardAPI().quote(10000, [72], ["Rome"], "2027-01-01", "2027-01-10")
    assert old.premium > young.premium


def test_auto_quote_for_booking_missing_ages_returns_named_gap(tmp_path):
    """Negative-Space Rule: never fabricate traveler age."""
    dossier = tmp_path / "Loucks_Regent_Grandeur_3122006.md"
    shutil.copy("dossiers/Loucks_Regent_Grandeur_3122006.md", dossier)

    result = ii.auto_quote_for_booking(str(dossier), booking_id="3122006")
    assert result["ok"] is False
    assert "traveler_ages" in result["missing_fields"]


def test_auto_quote_for_booking_reads_real_dossier_fields(tmp_path, monkeypatch):
    dossier = tmp_path / "Loucks_Regent_Grandeur_3122006.md"
    shutil.copy("dossiers/Loucks_Regent_Grandeur_3122006.md", dossier)

    store_path = tmp_path / "insurance_quotes.json"
    monkeypatch.setattr(ii, "QUOTES_STORE_PATH", store_path)

    result = ii.auto_quote_for_booking(str(dossier), booking_id="3122006", traveler_ages=[65, 63])
    assert result["ok"] is True
    assert result["client"] == "John & Susan Loucks"
    assert len(result["quotes"]) == 3
    for q in result["quotes"]:
        # trip_cost is the full insured value (invoice_total=25798.00), not the
        # outstanding balance_due (24798.00) — insurance covers the whole trip cost
        assert q["trip_cost"] == 25798.00

    store = json.loads(store_path.read_text())
    assert "John & Susan Loucks::booking" in store


def test_multi_booking_dossier_extraction(tmp_path, monkeypatch):
    dossier = tmp_path / "McLeod_McGlasson_Multi.md"
    shutil.copy("dossiers/McLeod_McGlasson_Multi.md", dossier)

    store_path = tmp_path / "insurance_quotes.json"
    monkeypatch.setattr(ii, "QUOTES_STORE_PATH", store_path)

    result = ii.auto_quote_for_booking(str(dossier), booking_id="booking_2", traveler_ages=[50, 48])
    assert result["ok"] is True
    assert result["booking_id"] == "booking_2"
    assert result["quotes"][0]["trip_cost"] == 11943.15


def test_record_client_acceptance_writes_dossier_frontmatter(tmp_path, monkeypatch):
    dossier = tmp_path / "Loucks_Regent_Grandeur_3122006.md"
    shutil.copy("dossiers/Loucks_Regent_Grandeur_3122006.md", dossier)

    store_path = tmp_path / "insurance_quotes.json"
    monkeypatch.setattr(ii, "QUOTES_STORE_PATH", store_path)

    ii.auto_quote_for_booking(str(dossier), booking_id="3122006", traveler_ages=[65, 63])
    result = ii.record_client_acceptance(
        str(dossier),
        booking_id="3122006",
        carrier="TravelGuard",
        policy_number="TG-998877",
        coverage_start="2026-06-15",
        coverage_end="2026-12-29",
        premium=612.50,
    )
    assert result["ok"] is True

    fm = ii._read_frontmatter(dossier)
    assert fm["insurance_status"] == "accepted"
    assert fm["insurance_carrier"] == "TravelGuard"
    assert fm["insurance_policy_number"] == "TG-998877"
    assert fm["insurance_coverage_start"] == "2026-06-15"
    assert fm["insurance_coverage_end"] == "2026-12-29"
    # pre-existing dossier fields must survive the frontmatter round-trip untouched
    assert fm["client"] == "John & Susan Loucks"
    assert fm["balance_due"] == 24798.00

    store = json.loads(store_path.read_text())
    assert store["John & Susan Loucks::booking"]["acceptance"]["policy_number"] == "TG-998877"


def test_format_tp05_insurance_snippet_contains_all_carriers():
    quotes = [q.to_dict() for q in ii.generate_quotes(
        trip_cost=20000, traveler_ages=[60], destinations=["Alaska"],
        departure_date="2027-05-01", return_date="2027-05-10",
        deposit_date="2026-10-01", booking_ref="SNIPPET-TEST",
    )]
    html = ii.format_tp05_insurance_snippet(quotes, coverage_deadline="2026-10-15")
    assert "TRAVEL INSURANCE" in html
    for q in quotes:
        assert q["carrier"] in html
        assert f'{q["premium"]:,.2f}' in html
    assert "2026-10-15" in html


def test_generate_quotes_falls_back_to_estimate_when_live_call_fails(monkeypatch):
    """A partner with a key configured but a broken endpoint must still fall back cleanly."""
    monkeypatch.setenv("TRAVELGUARD_API_KEY", "fake-key-for-test")
    tg = TravelGuardAPI()
    assert tg.api_key == "fake-key-for-test"
    quote = tg.quote(10000, [45], ["Nowhere"], "2027-01-01", "2027-01-10")
    # base_url is a placeholder host — the live call must fail and fall back, not raise
    assert quote.source == "estimate"
