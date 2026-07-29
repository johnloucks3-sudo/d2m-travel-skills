"""
tests/test_staff_summary_sheet.py — regression suite for the USAF Staff Summary
Sheet model (core/staffing/staff_summary_sheet.py).

Covers the AF Form 1768 lifecycle (open → coordinate → decide → accomplish →
close), the two mandatory overlays the Commander stood up (CHIEF SILVER front +
back gate, anti-theater cross-seat certification), the chop-chain semantics
(nonconcur is recorded, not a veto), stage guards, and the OPR-aware wire into
core/relay/delegation_wiring.py.
"""
import json
import os
import tempfile

import pytest

from core.staffing import staff_summary_sheet as sss_mod
from core.staffing.staff_summary_sheet import (
    open_sss, coordinate, decide, accomplish, close_sss, render_sss,
    SSSError, ACTION_TYPES,
)


@pytest.fixture(autouse=True)
def _isolate_silver_ledger(tmp_path, monkeypatch):
    """CHIEF SILVER appends every frame/verdict to the real
    OpsCenter/silver_ledger.jsonl and hale_decisions.md. Redirect both to tmp so
    the suite never pollutes the live audit trail."""
    from core.silver import gate
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(gate, "DECISIONS", tmp_path / "hale_decisions.md")
    from core.staffing import directive_ledger
    monkeypatch.setattr(directive_ledger, "LEDGER", tmp_path / "mandatory_directives.jsonl")


@pytest.fixture
def artifact(tmp_path):
    """A real, non-empty artifact whose text carries the number the criteria
    promise, so CHIEF SILVER's back gate has something concrete to pass."""
    p = tmp_path / "product.txt"
    p.write_text("work product: 3 stages exercised, 5 rows present.\n")
    return str(p)


def _criteria(artifact):
    # Promise only numbers that actually appear in the artifact text (3 stages,
    # 5 rows). The artifact path is named separately as the ground-truth source,
    # so it must not be embedded here — its incidental digits would make Silver's
    # back gate (rightly) HOLD on numbers absent from the product.
    return "work product records 3 stages and 5 rows"


# ── FRONT gate ──────────────────────────────────────────────────────────────

def test_open_holds_on_vague_criteria(artifact):
    with pytest.raises(SSSError, match="front-frame HOLD"):
        open_sss("SSS-V", "vague", "prove it", opr="CC", action_type="APPR",
                 acceptance_criteria="make it good", ground_truth_sources=[artifact])


def test_open_holds_on_missing_ground_truth():
    with pytest.raises(SSSError, match="front-frame HOLD"):
        open_sss("SSS-G", "no source", "prove it", opr="CC", action_type="APPR",
                 acceptance_criteria="file has 3 rows",
                 ground_truth_sources=["/nonexistent/path/xyz.json"])


def test_bad_action_type_rejected(artifact):
    with pytest.raises(SSSError, match="action_type"):
        open_sss("SSS-A", "t", "p", opr="CC", action_type="NOPE",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact])


def test_missing_opr_rejected(artifact):
    with pytest.raises(SSSError, match="OPR"):
        open_sss("SSS-O", "t", "p", opr="", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact])


# ── Happy path + chop chain ─────────────────────────────────────────────────

def test_full_lifecycle_office_opr(artifact):
    s = open_sss("SSS-1", "Restore staffing model", "prove end to end",
                 opr="Dani", action_type="APPR", acceptance_criteria=_criteria(artifact),
                 ocr_chain=["Sterling", "Silver"], ground_truth_sources=[artifact],
                 certified_by="Hale")
    assert s["status"] == "in_coordination"
    coordinate(s, "Sterling", "concur")
    assert s["status"] == "in_coordination"          # one OCR still pending
    coordinate(s, "Silver", "concur_with_comment", "watch the gate")
    assert s["status"] == "coordinated"              # chain complete
    decide(s, "Commander", "APPROVED")
    assert s["status"] == "tasked"
    accomplish(s, artifact)
    assert s["status"] == "accomplished"
    close_sss(s, certified_by="Hale")
    assert s["status"] == "closed"
    assert s["certified_by"] == "Hale"
    assert "STAFF SUMMARY SHEET" in render_sss(s)


def test_no_ocr_chain_opens_coordinated(artifact):
    s = open_sss("SSS-N", "t", "p", opr="CC", action_type="INFO",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="OC")
    assert s["status"] == "coordinated"              # nothing to chop


def test_nonconcur_is_recorded_not_veto(artifact):
    s = open_sss("SSS-2", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ocr_chain=["Sterling"],
                 ground_truth_sources=[artifact], certified_by="Hale")
    coordinate(s, "Sterling", "nonconcur", "disagree on scope")
    assert s["status"] == "coordinated"              # chop complete despite nonconcur
    # the decision authority can still act, adjudicating the nonconcur
    decide(s, "Commander", "APPROVED", "override the nonconcur")
    assert s["status"] == "tasked"
    assert s["decision"]["adjudicated_nonconcurs"] == ["Sterling"]


def test_nonconcur_requires_reason(artifact):
    s = open_sss("SSS-3", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ocr_chain=["Sterling"],
                 ground_truth_sources=[artifact], certified_by="Hale")
    with pytest.raises(SSSError, match="nonconcur must state its reason"):
        coordinate(s, "Sterling", "nonconcur")


def test_adhoc_coordinator_appended(artifact):
    s = open_sss("SSS-4", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ocr_chain=["Sterling"],
                 ground_truth_sources=[artifact], certified_by="Hale")
    coordinate(s, "Harlan", "concur")                # not in the original chain
    offices = [e["office"] for e in s["ocr_chain"]]
    assert "Harlan" in offices
    assert s["status"] == "in_coordination"          # Sterling still pending


def test_disapproved_closes_dead(artifact):
    s = open_sss("SSS-5", "t", "p", opr="CC", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="OC")
    decide(s, "Commander", "DISAPPROVED", "not now")
    assert s["status"] == "closed"
    assert s["decision"]["disposition"] == "DISAPPROVED"


# ── Anti-theater + BACK gate ────────────────────────────────────────────────

def test_seat_opr_cannot_self_certify_at_open(artifact):
    with pytest.raises(SSSError, match="anti-theater"):
        open_sss("SSS-6", "t", "p", opr="OC", action_type="COORD",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 opr_seat="OC", certified_by="OC")


def test_office_opr_cannot_self_certify_at_close(artifact):
    s = open_sss("SSS-7", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="Dani")
    decide(s, "Hale", "APPROVED")
    accomplish(s, artifact)
    with pytest.raises(SSSError, match="anti-theater"):
        close_sss(s, certified_by="Dani")


def test_back_gate_holds_on_bare_claim(artifact):
    s = open_sss("SSS-8", "t", "p", opr="OC", action_type="COORD",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 opr_seat="OC", certified_by="CC")
    decide(s, "Hale", "NOTED")
    accomplish(s, "done, trust me")                  # bare claim, not a concrete ref
    with pytest.raises(SSSError, match="back-gate HOLD"):
        close_sss(s, certified_by="CC", cross_hale_evidence="logs/oc_verify.log@ok")


# ── Stage guards ────────────────────────────────────────────────────────────

def test_cannot_accomplish_before_tasked(artifact):
    s = open_sss("SSS-9", "t", "p", opr="CC", action_type="INFO",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="OC")
    with pytest.raises(SSSError, match="must be tasked"):
        accomplish(s, artifact)


def test_cannot_close_before_accomplished(artifact):
    s = open_sss("SSS-10", "t", "p", opr="CC", action_type="INFO",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="OC")
    decide(s, "Hale", "NOTED")
    with pytest.raises(SSSError, match="must be accomplished"):
        close_sss(s, certified_by="OC")


def test_cannot_decide_a_drafted_sheet_twice(artifact):
    s = open_sss("SSS-11", "t", "p", opr="CC", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="OC")
    decide(s, "Hale", "APPROVED")
    with pytest.raises(SSSError, match="cannot decide"):
        decide(s, "Hale", "APPROVED")


# ── MANDATORY cross-Hale gate ───────────────────────────────────────────────

def _run_to_accomplished(opr_seat, artifact, *, ocr=None, opr_failed=False):
    s = open_sss("SSS-CH", "seat sheet", "p", opr=opr_seat, action_type="COORD",
                 acceptance_criteria="work product records 3 stages and 5 rows",
                 ocr_chain=ocr or ([opr_seat] if opr_failed else []),
                 ground_truth_sources=[artifact], opr_seat=opr_seat, certified_by="CC")
    if opr_failed:
        coordinate(s, opr_seat, "nonconcur", "could not deliver")
    decide(s, "Hale", "NOTED")
    accomplish(s, artifact)
    return s


def test_cross_hale_close_requires_evidence(artifact):
    s = _run_to_accomplished("OC", artifact)
    with pytest.raises(SSSError, match="no concrete evidence"):
        close_sss(s, certified_by="CC")                 # no evidence → blocked
    close_sss(s, certified_by="CC", cross_hale_evidence="logs/oc_verify.log@ok")
    assert s["status"] == "closed"
    assert s["cross_hale_cert"]["seat"] == "CC"


def test_cross_hale_failed_opr_seat_blocks_close(artifact):
    s = _run_to_accomplished("AG", artifact, opr_failed=True)
    with pytest.raises(SSSError, match="failed to deliver"):
        close_sss(s, certified_by="CC", cross_hale_evidence="logs/x@ok")


def test_cross_hale_certifier_must_be_a_seat(artifact):
    s = _run_to_accomplished("OC", artifact)
    with pytest.raises(SSSError, match="real cross-Hale seat"):
        close_sss(s, certified_by="Sterling", cross_hale_evidence="logs/x@ok")


def test_block_and_reopen_reassign(artifact):
    s = _run_to_accomplished("AG", artifact, opr_failed=True)
    from core.staffing.staff_summary_sheet import block_sss, reopen_sss
    block_sss(s, "AG failed, no cross-Hale delivery")
    assert s["status"] == "blocked"
    reopen_sss(s, "tasked", "reassign to OC", new_opr="OC", new_opr_seat="OC")
    assert s["status"] == "tasked" and s["opr"] == "OC"
    # a reopened sheet has no lingering nonconcur from the NEW opr, so it can close
    accomplish(s, artifact)
    close_sss(s, certified_by="CC", cross_hale_evidence="logs/oc@ok")
    assert s["status"] == "closed"


def test_directive_ledger_binds_mandate(tmp_path, monkeypatch, artifact):
    from core.staffing import directive_ledger as dl
    monkeypatch.setattr(dl, "LEDGER", tmp_path / "md.jsonl")
    dl.capture("Do something entirely new that is mandatory", source="msgX")
    assert any(m["mandatory"] for m in dl.active_mandates())
    keys = dl.active_gate_keys()
    assert any(k.startswith("unmapped:") for k in keys)
    # a sheet opened with an unmapped mandate cannot close without an ack
    s = open_sss("SSS-M", "t", "p", opr="OC", action_type="COORD",
                 acceptance_criteria="work product records 3 stages and 5 rows",
                 ground_truth_sources=[artifact], opr_seat="OC", certified_by="CC")
    assert any(k.startswith("unmapped:") for k in s["mandates"])
    decide(s, "Hale", "NOTED"); accomplish(s, artifact)
    with pytest.raises(SSSError, match="unmet mandatory directive"):
        close_sss(s, certified_by="CC", cross_hale_evidence="logs/x@ok")


# ── Commander human override (SO 2026-07-29) ────────────────────────────────
# CHIEF SILVER's back-gate exists to stop an AI seat from self-certifying a
# hollow completion; it was never meant to interrogate the Commander. A human
# close must succeed with NO artifact/criteria/gate, but an AI seat's close
# must remain fully gated, and the override must be attributed + visible in
# the ledger (never a silent bypass).

def test_human_override_closes_with_no_artifact_at_all(artifact):
    """The whole point: a human close needs nothing checkable."""
    s = open_sss("SSS-HO1", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="Hale")
    decide(s, "Hale", "APPROVED")
    # deliberately never call accomplish() — no verification_artifact exists
    close_sss(s, human_override="Commander", human_note="Yoda said close it")
    assert s["status"] == "closed"
    assert s["certified_by"] == "Commander"
    assert "COMMANDER OVERRIDE" in s["logs"][-1]


def test_human_override_is_case_insensitive_but_reserved(artifact):
    s = open_sss("SSS-HO2", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="Hale")
    decide(s, "Hale", "APPROVED")
    close_sss(s, human_override="commander")   # lowercase still accepted
    assert s["status"] == "closed"


def test_ai_seat_cannot_self_attribute_human_override(artifact):
    """An AI seat passing its own name as `human_override` must be rejected —
    only the literal Commander identity may bypass the gate."""
    s = open_sss("SSS-HO3", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="Hale")
    decide(s, "Hale", "APPROVED")
    with pytest.raises(SSSError, match="human_override must be"):
        close_sss(s, human_override="CC")
    assert s["status"] != "closed"


def test_ai_seat_close_still_fully_gated_no_human_override(artifact):
    """REGRESSION GUARD: without human_override, a seat-executed sheet must
    still clear anti-theater + mandatory cross-Hale evidence + Silver back-gate
    — none of that logic may be weakened by the new override path."""
    s = _run_to_accomplished("AG", artifact)
    with pytest.raises(SSSError, match="no concrete evidence"):
        close_sss(s, certified_by="OC")             # no cross_hale_evidence → still blocked
    close_sss(s, certified_by="OC", cross_hale_evidence="logs/oc_verify.log@ok")
    assert s["status"] == "closed"
    assert s["certified_by"] == "OC"                 # NOT "Commander" — real gate ran


def test_human_override_writes_distinct_ledger_row(artifact, tmp_path, monkeypatch):
    from core.silver import gate
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "ledger.jsonl")
    s = open_sss("SSS-HO4", "t", "p", opr="Dani", action_type="APPR",
                 acceptance_criteria=_criteria(artifact), ground_truth_sources=[artifact],
                 certified_by="Hale")
    decide(s, "Hale", "APPROVED")
    close_sss(s, human_override="Commander")
    rows = [json.loads(line) for line in gate.LEDGER.read_text().splitlines()]
    override_rows = [r for r in rows if r["mission_id"] == "SSS-HO4" and r["verdict"] == "OVERRIDE"]
    assert len(override_rows) == 1
    assert override_rows[0]["overridden_by"] == "Commander"
    # distinguishable from a real PASS — never confusable with "the gate ran and passed"
    assert not any(r["mission_id"] == "SSS-HO4" and r["verdict"] == "PASS"
                   and r["stage"] == "back" for r in rows)


# ── OPR-aware delegation wire ───────────────────────────────────────────────

def test_delegation_wiring_reads_opr_field():
    from core.relay.delegation_wiring import delegate_mission
    m = {"id": "MISSION-X", "title": "opr-driven", "opr": "OC",
         "acceptance_criteria": "file has 3 rows",
         "ground_truth_sources": [], "certified_by": "CC"}
    # ground_truth empty → Silver front-frame HOLD is expected; but the seat must
    # resolve from `opr` (not raise the "not a seat" error) to get that far.
    from core.relay.delegation_wiring import DelegationError
    with pytest.raises(DelegationError, match="front-frame HOLD"):
        delegate_mission(m)
    assert m["assigned_to"] == "OC"                  # opr mirrored into alias
