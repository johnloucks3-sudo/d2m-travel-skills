#!/usr/bin/env python3
"""Verify core/ops/three_voice_arbitration.py against the decision matrix in
docs/THREE_VOICE_ARBITRATION_PROTOCOL.md and docs/THREE_VOICE_ARBITRATION_GUIDE.md.

5 conflict scenarios (one per matrix branch) + edge cases (missing fields,
unclear/no-pattern conflict). No live I/O — logging is disabled in every call.

Run: python3 core/ops/test_three_voice_arbitration.py
"""
import sys

sys.path.insert(0, "/home/john/Thunderbird")

from core.ops.three_voice_arbitration import (
    ConflictSubmission,
    VoicePosition,
    run_arbitration,
    ESCALATE_TO_COMMANDER,
    RESOLVE_UNILATERALLY,
    REQUEST_MORE_INFO,
    PATTERN_1_TIME_VS_COST,
    PATTERN_2_BASELINE_VS_READY,
    PATTERN_3_COST_VS_STRATEGIC,
)

failures = []


def check(label, condition, detail=""):
    if not condition:
        failures.append(f"{label}: {detail}")


# ---------------------------------------------------------------------------
# Scenario 1 — Castillo time vs Harlan cost, financial impact > $5K -> ESCALATE
# ---------------------------------------------------------------------------
def test_scenario_1_time_vs_cost_escalates():
    sub = ConflictSubmission(
        submitter="Dembe (A2)",
        issue_title="Scenario 1 — Scandinavia portal readiness",
        disagreement_summary="Castillo wants more time to scenario-test; Harlan says waiting costs money.",
        castillo=VoicePosition(
            position="I need 72 hours for the three-scenario test before we publish.",
            recommendation="Hold the release 72 hours.",
        ),
        harlan=VoicePosition(
            position="The cost of delay on this decision is $2,000 per day in lost booking momentum.",
            recommendation="Move now.",
        ),
        financial_impact_usd=8000,
    )
    r = run_arbitration(sub, log=False)
    check("scenario1_pattern", PATTERN_1_TIME_VS_COST in r.patterns_detected, r.patterns_detected)
    check("scenario1_recommendation", r.recommendation == ESCALATE_TO_COMMANDER, r.recommendation)
    check("scenario1_case", r.decision_case == "TIMING", r.decision_case)


# ---------------------------------------------------------------------------
# Scenario 2 — same pattern, financial impact under $5K -> Hale arbitrates
# ---------------------------------------------------------------------------
def test_scenario_2_time_vs_cost_under_threshold_arbitrates():
    sub = ConflictSubmission(
        submitter="Dembe (A2)",
        issue_title="Scenario 2 — minor timing conflict",
        disagreement_summary="Castillo wants more time; Harlan flags a small cost of delay.",
        castillo=VoicePosition(
            position="I need 48 hours for the scenario test.",
            recommendation="Hold 48 hours.",
        ),
        harlan=VoicePosition(
            position="Cost of delay here is about $50 per day, negligible.",
            recommendation="Fine to wait.",
        ),
        financial_impact_usd=100,
    )
    r = run_arbitration(sub, log=False)
    check("scenario2_pattern", PATTERN_1_TIME_VS_COST in r.patterns_detected, r.patterns_detected)
    check("scenario2_recommendation", r.recommendation == RESOLVE_UNILATERALLY, r.recommendation)


# ---------------------------------------------------------------------------
# Scenario 3 — Sterling baseline vs Castillo ready, baseline gap material -> ARBITRATE
# ---------------------------------------------------------------------------
def test_scenario_3_baseline_vs_ready_material_arbitrates():
    sub = ConflictSubmission(
        submitter="Hale",
        issue_title="Scenario 3 — Dossier automation baseline gap",
        disagreement_summary="Sterling has no baseline; Castillo is ready to publish Option B.",
        castillo=VoicePosition(
            position="Option B is ready to publish now, strategically sound.",
            recommendation="Approve and publish.",
        ),
        sterling=VoicePosition(
            position="We have no baseline — cannot measure whether this improved anything.",
            recommendation="Build a measurement charter first.",
        ),
        baseline_gap_material=True,
    )
    r = run_arbitration(sub, log=False)
    check("scenario3_pattern", PATTERN_2_BASELINE_VS_READY in r.patterns_detected, r.patterns_detected)
    check("scenario3_recommendation", r.recommendation == RESOLVE_UNILATERALLY, r.recommendation)
    check("scenario3_case", r.decision_case == "PROCESS-GATE", r.decision_case)
    check("scenario3_rationale_mentions_material", "material" in r.rationale.lower(), r.rationale)


# ---------------------------------------------------------------------------
# Scenario 4 — Harlan cost vs Castillo strategic, multi-year commitment -> ESCALATE
# ---------------------------------------------------------------------------
def test_scenario_4_cost_vs_strategic_multiyear_escalates():
    sub = ConflictSubmission(
        submitter="Sterling (A7)",
        issue_title="Scenario 4 — Supplier relationship exit",
        disagreement_summary="Harlan says exit costs too much; Castillo says this is strategically essential.",
        castillo=VoicePosition(
            position="Exiting this supplier is strategically essential to our capability portfolio "
                     "for the next several years.",
            recommendation="Exit the relationship.",
        ),
        harlan=VoicePosition(
            position="This costs more than the benefit justifies — 40% of our operational budget in "
                     "transition fees.",
            recommendation="Do not exit.",
        ),
        time_horizon_days=365,
    )
    r = run_arbitration(sub, log=False)
    check("scenario4_pattern", PATTERN_3_COST_VS_STRATEGIC in r.patterns_detected, r.patterns_detected)
    check("scenario4_recommendation", r.recommendation == ESCALATE_TO_COMMANDER, r.recommendation)
    check("scenario4_case", r.decision_case == "DIRECTION", r.decision_case)


# ---------------------------------------------------------------------------
# Scenario 5 — no recognized pattern -> Hale arbitrates (the "Else" branch)
# ---------------------------------------------------------------------------
def test_scenario_5_no_pattern_arbitrates():
    sub = ConflictSubmission(
        submitter="Hale",
        issue_title="Scenario 5 — routine disagreement",
        disagreement_summary="Minor disagreement on excursion vendor selection, no strategy/finance/process split.",
        castillo=VoicePosition(position="Vendor A is fine.", recommendation="Use Vendor A."),
        harlan=VoicePosition(position="Vendor B is $30 cheaper.", recommendation="Use Vendor B."),
    )
    r = run_arbitration(sub, log=False)
    check("scenario5_no_pattern", r.patterns_detected == [], r.patterns_detected)
    check("scenario5_recommendation", r.recommendation == RESOLVE_UNILATERALLY, r.recommendation)
    check("scenario5_case", r.decision_case == "NONE", r.decision_case)


# ---------------------------------------------------------------------------
# Edge case — missing required fields -> REQUEST_MORE_INFO, graceful (no exception)
# ---------------------------------------------------------------------------
def test_edge_missing_fields_requests_info():
    sub = ConflictSubmission()  # nothing filled in at all
    r = run_arbitration(sub, log=False)
    check("edge_missing_recommendation", r.recommendation == REQUEST_MORE_INFO, r.recommendation)
    check("edge_missing_case", r.decision_case == "INCOMPLETE", r.decision_case)
    check("edge_missing_fields_listed", len(r.missing_fields) > 0, r.missing_fields)


# ---------------------------------------------------------------------------
# Edge case — pattern detected but the structured field the matrix needs is
# missing (Harlan's dollar figure never given) -> REQUEST_MORE_INFO, not a crash
# ---------------------------------------------------------------------------
def test_edge_pattern_without_financial_data_requests_info():
    sub = ConflictSubmission(
        submitter="Dembe (A2)",
        issue_title="Edge — time vs cost, no dollar figure on record",
        disagreement_summary="Castillo wants more time; Harlan objects on cost, but no number was given.",
        castillo=VoicePosition(position="I need more time for the scenario test.", recommendation="Hold."),
        harlan=VoicePosition(position="Waiting costs us, cost of delay is real.", recommendation="Move now."),
        # financial_impact_usd intentionally omitted
    )
    r = run_arbitration(sub, log=False)
    check("edge_pattern_no_$_recommendation", r.recommendation == REQUEST_MORE_INFO, r.recommendation)
    check("edge_pattern_no_$_missing_field", "financial_impact_usd" in r.missing_fields, r.missing_fields)


# ---------------------------------------------------------------------------
# Edge case — explicit invoke with no other structured data still resolves
# gracefully (pattern recorded, falls through to Hale's own authority)
# ---------------------------------------------------------------------------
def test_edge_explicit_invoke_only():
    sub = ConflictSubmission(
        submitter="Castillo (A5)",
        issue_title="Edge — explicit invoke, ambiguous conflict",
        disagreement_summary="Explicit call for Three Voice Arbitration, no clean pattern otherwise.",
        explicit_invoke=True,
    )
    r = run_arbitration(sub, log=False)
    check("edge_explicit_no_exception", r is not None)
    check("edge_explicit_recommendation_valid",
          r.recommendation in (RESOLVE_UNILATERALLY, REQUEST_MORE_INFO, ESCALATE_TO_COMMANDER),
          r.recommendation)


def main():
    tests = [
        test_scenario_1_time_vs_cost_escalates,
        test_scenario_2_time_vs_cost_under_threshold_arbitrates,
        test_scenario_3_baseline_vs_ready_material_arbitrates,
        test_scenario_4_cost_vs_strategic_multiyear_escalates,
        test_scenario_5_no_pattern_arbitrates,
        test_edge_missing_fields_requests_info,
        test_edge_pattern_without_financial_data_requests_info,
        test_edge_explicit_invoke_only,
    ]
    for t in tests:
        t()

    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"PASSED — {len(tests)}/{len(tests)} tests")
    sys.exit(0)


if __name__ == "__main__":
    main()
