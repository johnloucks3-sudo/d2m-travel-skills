#!/usr/bin/env python3
"""
Offline tests for tcd.staging — P-D-T-A-C stage/status derivation.

    python -m pytest tests/test_tcd_staging.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd.staging import derive_stage, derive_status, STAGES  # noqa: E402


class TestDeriveStage:
    def test_reference_items_are_ref(self):
        assert derive_stage({"id": "so-SO_X", "inbox": "reference"}) == "REF"
        assert derive_stage({"id": "dossier-Y", "inbox": "reference"}) == "REF"

    def test_proposals_are_proposed(self):
        assert derive_stage({"id": "elon-verify-latest", "type": "paper"}) == "P"
        assert derive_stage({"id": "x", "type": "paper"}) == "P"

    def test_decisions_and_alerts_are_decide(self):
        assert derive_stage({"id": "alert-1", "type": "decision"}) == "D"
        assert derive_stage({"id": "alert-2", "type": "email"}) == "D"

    def test_incoming_gmail_is_proposed(self):
        assert derive_stage({"id": "gmail-johnloucks3-1", "type": "email"}) == "P"

    def test_active_task_is_accomplishing(self):
        assert derive_stage({"id": "task-M1", "tags": ["active"]}) == "A"

    def test_blocked_task_is_tasked(self):
        assert derive_stage({"id": "task-M2", "tags": ["blocked"]}) == "T"

    def test_done_task_is_certify(self):
        assert derive_stage({"id": "task-M3", "tags": ["done"]}) == "C"

    def test_project_is_accomplishing(self):
        assert derive_stage({"id": "proj-P1"}) == "A"

    def test_every_result_is_a_valid_stage(self):
        samples = [
            {"id": "so-A", "inbox": "reference"},
            {"id": "elon-x", "type": "paper"},
            {"id": "alert-1", "type": "decision"},
            {"id": "gmail-a-1", "type": "email"},
            {"id": "task-1", "tags": ["active"]},
            {"id": "proj-1"},
            {"id": "weird-1"},
        ]
        for s in samples:
            assert derive_stage(s) in STAGES


class TestDeriveStatus:
    def test_ref_stage_is_ref_status(self):
        assert derive_status({"id": "so-x"}, "REF") == "REF"

    def test_workflow_items_open(self):
        assert derive_status({"id": "task-1"}, "A") == "OPEN"
        assert derive_status({"id": "alert-1"}, "D") == "OPEN"

    def test_phase0_never_disposes(self):
        for stage in STAGES:
            assert derive_status({"id": "x"}, stage) in ("OPEN", "REF")
