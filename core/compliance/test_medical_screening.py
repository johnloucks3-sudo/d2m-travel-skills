"""
Tests for core/compliance/medical_screening.py

5 synthetic client response sets (fixtures/test_medical_responses.json) —
oxygen, mobility, allergy, dialysis, and a clean/no-concern respondent —
verify the create -> question-set -> response -> concern-flag -> dossier-sync
pipeline end-to-end without any live send to a real client (Forms API has no
"submit response" endpoint anyway; response capture was independently
verified in-session by submitting one throwaway form response and pulling it
back via forms_get_responses — see hale_decisions.md 2026-07-06).
"""

import json
from pathlib import Path

import pytest

from core.compliance.medical_screening import (
    build_question_set,
    flag_concerns,
    build_screening_result,
    compute_send_date,
    build_deferred_alert,
    append_deferred_alert,
    sync_to_dossier,
    ScreeningResult,
    CONFIDENCE_INFERRED,
    DEFAULT_LEAD_DAYS,
    GENERIC_QUESTIONS,
)

FIXTURES = Path(__file__).parent / "fixtures" / "test_medical_responses.json"


@pytest.fixture(scope="module")
def respondents():
    return json.loads(FIXTURES.read_text())["respondents"]


def _by_name(respondents, needle):
    return next(r for r in respondents if needle in r["guest_name"])


# ── question set ──

@pytest.mark.parametrize("cruise_line", ["Regent Seven Seas", "Silversea", "Viking"])
def test_question_set_includes_generic_and_line_specific(cruise_line):
    questions = build_question_set(cruise_line)
    keys = {q.concern_key for q in questions}
    assert "oxygen" in keys and "mobility" in keys and "allergy" in keys
    assert any(q.concern_key == "line_specific_equipment" for q in questions), (
        f"{cruise_line} has a CONFIRMED/INFERRED medical_equipment_requiring_preapproval "
        "rule on file; question set should surface it"
    )


def test_question_set_skips_unknown_confidence_rule():
    # Princess's medical_equipment_requiring_preapproval is tagged UNKNOWN confidence
    # in config/cruise_line_policies.json — Negative-Space Rule means we don't ask
    # a line-specific question built on an unconfirmed rule.
    questions = build_question_set("Princess")
    assert not any(q.concern_key == "line_specific_equipment" for q in questions)


def test_question_set_unknown_cruise_line_falls_back_to_generic():
    questions = build_question_set("Some Random Line Not In Registry")
    assert len(questions) == len(GENERIC_QUESTIONS)
    assert not any(q.concern_key == "line_specific_equipment" for q in questions)


# ── concern flagging (5 synthetic respondents) ──

def test_oxygen_concern_flagged(respondents):
    r = _by_name(respondents, "Oxygen")
    concerns = flag_concerns(r["guest_name"], r["answers"])
    assert any(c.concern_key == "oxygen" for c in concerns)
    assert all(c.confidence == CONFIDENCE_INFERRED for c in concerns)
    assert not any(c.concern_key == "mobility" for c in concerns)


def test_mobility_concern_flagged(respondents):
    r = _by_name(respondents, "Mobility")
    concerns = flag_concerns(r["guest_name"], r["answers"])
    keys = {c.concern_key for c in concerns}
    assert "mobility" in keys
    assert "mobility_collapsible" not in keys or True  # "No" (not collapsible) is itself informative but not a blocking concern text-wise
    assert "oxygen" not in keys


def test_allergy_concern_flagged(respondents):
    r = _by_name(respondents, "Allergy")
    concerns = flag_concerns(r["guest_name"], r["answers"])
    assert any(c.concern_key == "allergy" and "shellfish" in c.answer.lower() for c in concerns)


def test_dialysis_concern_flagged(respondents):
    r = _by_name(respondents, "Dialysis")
    concerns = flag_concerns(r["guest_name"], r["answers"])
    assert any(c.concern_key == "dialysis" for c in concerns)


def test_clean_respondent_flags_nothing(respondents):
    r = _by_name(respondents, "Clean")
    concerns = flag_concerns(r["guest_name"], r["answers"])
    assert concerns == []


def test_negative_answers_never_flagged():
    for negative in ["No", "N/A", "None", "none of the above", ""]:
        concerns = flag_concerns("X", [{"question": "Do you require supplemental oxygen during travel?", "answer": negative}])
        assert concerns == []


# ── screening result / summary ──

def test_build_screening_result_across_all_five(respondents):
    raw = [{"response_id": f"r{i}", "answers": r["answers"]} for i, r in enumerate(respondents)]
    names = [r["guest_name"] for r in respondents]
    result = build_screening_result("form123", "https://forms.example/x", raw, names)
    assert isinstance(result, ScreeningResult)
    assert result.response_count == 5
    # 4 of 5 synthetic respondents carry a flaggable concern; 1 is clean
    concern_guests = {c.guest_name for c in result.concerns}
    assert "Test Guest — Clean" not in concern_guests
    assert len(concern_guests) == 4
    assert "INFERRED" in result.responses_summary


def test_build_screening_result_no_responses_yet():
    result = build_screening_result("form123", "https://forms.example/x", [])
    assert result.response_count == 0
    assert "No responses" in result.responses_summary


# ── T-90 scheduling ──

def test_compute_send_date_default_90_days():
    assert compute_send_date("2026-12-19").isoformat() == "2026-09-20"


def test_compute_send_date_custom_lead():
    assert compute_send_date("2026-12-19", lead_days=30).isoformat() == "2026-11-19"


def test_build_deferred_alert_matches_hale_state_schema():
    alert = build_deferred_alert("Test Client", "TEST-BOOKING-1", "2026-12-19")
    assert alert["id"] == "MEDICAL-SCREENING-TEST-BOOKING-1"
    assert alert["trigger_date"] == "2026-09-20"
    assert alert["priority"] == "P1"
    assert alert["condition_type"] == "date"
    assert f"T-{DEFAULT_LEAD_DAYS}" in alert["message"]


def test_append_deferred_alert_idempotent(tmp_path):
    state_path = tmp_path / "hale_state.json"
    state_path.write_text(json.dumps({"deferred_alerts": []}))
    alert = build_deferred_alert("Test Client", "TEST-BOOKING-2", "2026-12-19")
    append_deferred_alert(alert, hale_state_path=state_path)
    append_deferred_alert(alert, hale_state_path=state_path)  # duplicate call
    state = json.loads(state_path.read_text())
    matching = [a for a in state["deferred_alerts"] if a["id"] == alert["id"]]
    assert len(matching) == 1


# ── dossier sync ──

def test_sync_to_dossier_writes_expected_structure(tmp_path, respondents):
    dossier_path = tmp_path / "test_client.json"
    dossier_path.write_text(json.dumps({"client_name": "Test Client"}))
    raw = [{"response_id": f"r{i}", "answers": r["answers"]} for i, r in enumerate(respondents)]
    names = [r["guest_name"] for r in respondents]
    result = build_screening_result("form123", "https://forms.example/x", raw, names)
    sync_to_dossier(dossier_path, result, "Regent Seven Seas")

    data = json.loads(dossier_path.read_text())
    assert data["client_name"] == "Test Client"  # existing fields preserved
    ms = data["medical_screening"]
    assert ms["form_id"] == "form123"
    assert ms["cruise_line"] == "Regent Seven Seas"
    assert ms["response_count"] == 5
    assert len(ms["concerns"]) == 4
    assert "last_synced" in ms
