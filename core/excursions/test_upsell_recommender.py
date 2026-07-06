"""Tests for the shore excursion upsell recommender.

Runs against the real client dossiers and real catalog scrapes already on
disk — no fixtures, no mocked client data. Per the task's request to
"measure acceptance rate": there is no historical send/accept data
anywhere in this repo yet (no upsell campaign has ever gone out), so an
acceptance rate cannot be honestly computed. `test_readiness_metrics`
reports what IS measurable now (schema validity, catalog coverage, score
distribution) and states plainly why acceptance rate is not yet available.
"""
from __future__ import annotations

from core.excursions import upsell_recommender as rec


def test_loads_real_client_profiles():
    profiles = rec.load_client_profiles()
    assert len(profiles) >= 10, "expected at least 10 real booking dossiers"
    names = {p.full_name for p in profiles}
    # spot-check real clients referenced in the task/roster are present
    assert any("Furlow" in n for n in names)
    assert any("Ely" in n or "Darrow" in n for n in names)
    assert any("Nichols" in n for n in names)
    assert any("Loucks" in n for n in names)


def test_prospects_and_test_fixtures_excluded():
    profiles = rec.load_client_profiles()
    for p in profiles:
        assert "PROSPECT" not in p.dossier_path
        assert "E2E Test" not in p.full_name
        assert "HALE TEST" not in p.full_name


def test_all_inclusive_regent_clients_confirmed_zero_not_unknown():
    """Furlow/Ely/Nichols are Regent Choice — $0.00 included excursions.
    This must be tagged CONFIRMED_ZERO_ALL_INCLUSIVE, not UNKNOWN — the
    negative-space rule: a real $0 is a fact, absence of data is not."""
    profiles = {p.full_name: p for p in rec.load_client_profiles()}
    furlow = next(p for n, p in profiles.items() if "Furlow" in n)
    assert furlow.prior_spend_confidence == "CONFIRMED_ZERO_ALL_INCLUSIVE"
    assert furlow.prior_spend_pp == 0.0


def test_pro_bono_relationships_get_zero_score_no_upsell():
    """Lyons and Westbrook are friend/pro-bono relationships — must never
    receive a revenue-driving upsell recommendation."""
    profiles = rec.load_client_profiles()
    lyons = next(p for p in profiles if "Lyons" in p.full_name)
    recs = rec.recommend_for_client(lyons)
    assert len(recs) == 1
    assert recs[0].tier == "EXCLUDED_PRO_BONO"
    assert recs[0].recommendation_score == 0.0
    assert recs[0].estimated_spend is None


def test_premium_tier_triggers_above_200pp_threshold():
    """Loucks Silver Nova has a real confirmed prior spend > $200/pp
    (from catalog browse history) — must trigger PREMIUM tier with
    private-tour candidates, per the task's stated business rule."""
    profiles = rec.load_client_profiles()
    loucks_nova = next(
        p for p in profiles
        if "Loucks" in p.full_name and p.cruise_line == "Silversea"
        and p.prior_spend_pp and p.prior_spend_pp > 200
    )
    recs = rec.recommend_for_client(loucks_nova)
    assert recs, "expected recommendations for Loucks Silver Nova"
    assert all(r.tier == "PREMIUM" for r in recs)
    assert all(r.estimated_spend and r.estimated_spend > 0 for r in recs)


def test_first_time_client_gets_combo_savings_not_premium():
    profiles = rec.load_client_profiles()
    furlow = next(p for p in profiles if "Furlow" in p.full_name)
    assert not furlow.is_repeat_client
    recs = rec.recommend_for_client(furlow)
    assert all(r.tier != "PREMIUM" for r in recs)


def test_repeat_client_without_confirmed_spend_gets_light_upsell():
    """McLeod/McGlasson are repeat clients (4 bookings) but most of those
    dossiers have no confirmed excursion spend data yet — should degrade
    to LIGHT_UPSELL, not be forced into COMBO_SAVINGS (that tier is for
    genuine first-timers) or PREMIUM (no evidence supports it)."""
    profiles = rec.load_client_profiles()
    mcleod = [p for p in profiles if "McLeod" in p.full_name and p.prior_spend_pp is None]
    assert mcleod, "expected at least one McLeod booking with unknown prior spend"
    for p in mcleod:
        assert p.is_repeat_client
        recs = rec.recommend_for_client(p)
        assert all(r.tier == "LIGHT_UPSELL" for r in recs)


def test_no_catalog_falls_back_to_reyes_routing_not_fabricated_price():
    """Clients without a scraped catalog file must never get a fabricated
    estimated_spend — the honest output is a routing note to Reyes (A8)."""
    profiles = rec.load_client_profiles()
    nichols = next(p for p in profiles if "Nichols" in p.full_name)
    recs = rec.recommend_for_client(nichols)
    assert len(recs) == 1
    assert recs[0].estimated_spend is None
    assert "Reyes" in recs[0].upsell_option


def test_transfer_and_zero_price_catalog_entries_excluded():
    """The Kuklinski Panama catalog scrape includes $0 port-transfer line
    items alongside real excursions — these must never surface as an
    upsell 'combo' (caught during dev: combo bundles were pricing at
    $0.00 because transfer listings sorted to the bottom)."""
    profiles = rec.load_client_profiles()
    kuklinski = next(p for p in profiles if p.key == "Kuklinski")
    recs = rec.recommend_for_client(kuklinski)
    assert recs
    for r in recs:
        if r.estimated_spend is not None:
            assert r.estimated_spend > 0


def test_output_schema_matches_spec():
    required_fields = {"excursion_id", "upsell_option", "recommendation_score", "estimated_spend"}
    records = rec.build_all_recommendations()
    assert records
    for r in records:
        d = r.to_dict()
        assert required_fields.issubset(d.keys())
        assert 0.0 <= r.recommendation_score <= 100.0


def test_write_output_round_trips(tmp_path):
    records = rec.build_all_recommendations()
    out = rec.write_output(records, tmp_path / "excursion_upsells.json")
    import json
    loaded = json.loads(out.read_text())
    assert len(loaded) == len(records)


def test_budget_guidance_facts_returns_data_not_prose():
    """TP template integration point — must return structured facts for
    Reyes/Dani to turn into copy, never finished client-facing sentences
    (creative-chain rule: Hale/generic code routes, does not originate
    content in Reyes/Luna/Naia/Dani's domain)."""
    facts = rec.budget_guidance_facts("Ely")
    assert set(facts.keys()) == {"tier", "top_upsell_option", "estimated_spend", "confidence", "source"}
    if facts["top_upsell_option"]:
        assert len(facts["top_upsell_option"]) < 120  # a label, not a paragraph


def test_readiness_metrics_honest_reporting(capsys):
    """This is the closest honest substitute for 'acceptance rate' the
    task asked for. Real acceptance rate requires a live campaign send +
    client response — that data does not exist yet anywhere in this repo.
    Reports what IS measurable today instead of fabricating a number."""
    records = rec.build_all_recommendations()
    total = len(records)
    with_real_price = sum(1 for r in records if r.estimated_spend is not None)
    with_confirmed_confidence = sum(
        1 for r in records if r.confidence in {"CONFIRMED", "CONFIRMED_ZERO_ALL_INCLUSIVE"}
    )
    by_tier: dict[str, int] = {}
    for r in records:
        by_tier[r.tier] = by_tier.get(r.tier, 0) + 1

    print(f"\n--- Upsell Recommender Readiness Report ({total} recommendations) ---")
    print(f"Catalog price coverage: {with_real_price}/{total} "
          f"({with_real_price / total:.0%}) — rest routed to Reyes for live quote")
    print(f"Confirmed spend-history confidence: {with_confirmed_confidence}/{total} "
          f"({with_confirmed_confidence / total:.0%})")
    print(f"Tier distribution: {by_tier}")
    print("Acceptance rate: NOT MEASURABLE — no client has ever received an "
          "upsell send from this engine. Requires a live TP campaign with "
          "tracked accept/decline responses before this metric exists.")

    assert total > 0
    assert with_real_price >= 0  # sanity — the honest number, whatever it is
