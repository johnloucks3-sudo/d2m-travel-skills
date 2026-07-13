#!/usr/bin/env python3
"""
Offline tests for tcd.overrides — the missing persistence layer between a
Commander/Hale stage move and the next full sheet_sync recompute.

    python -m pytest tests/test_tcd_overrides.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import overrides  # noqa: E402


class TestLoadSave:
    def test_missing_file_returns_empty(self, tmp_path):
        assert overrides.load_overrides(tmp_path / "nope.json") == {}

    def test_corrupt_file_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        assert overrides.load_overrides(p) == {}

    def test_round_trip(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.save_overrides({"task-1": {"stage": "T"}}, p)
        assert overrides.load_overrides(p) == {"task-1": {"stage": "T"}}


class TestSetOverrideMerges:
    def test_stage_only_preserves_existing_owner(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.set_override("task-1", stage="D", owner="Sterling", path=p)
        overrides.set_override("task-1", stage="T", path=p)
        entry = overrides.load_overrides(p)["task-1"]
        assert entry == {"stage": "T", "owner": "Sterling"}

    def test_owner_only_preserves_existing_stage(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.set_override("task-1", stage="D", path=p)
        overrides.set_override("task-1", owner="Dani", path=p)
        entry = overrides.load_overrides(p)["task-1"]
        assert entry == {"stage": "D", "owner": "Dani"}

    def test_blank_id_is_noop(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.set_override("", stage="D", path=p)
        assert not p.exists()


class TestClearOverride:
    def test_clear_removes_entry(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.set_override("task-1", stage="D", path=p)
        overrides.clear_override("task-1", path=p)
        assert overrides.load_overrides(p) == {}

    def test_clear_missing_id_is_noop(self, tmp_path):
        p = tmp_path / "o.json"
        overrides.save_overrides({"task-1": {"stage": "D"}}, p)
        overrides.clear_override("task-999", path=p)
        assert overrides.load_overrides(p) == {"task-1": {"stage": "D"}}


class TestApplyOverride:
    def test_override_wins_over_derived(self):
        ov = {"task-1": {"stage": "T"}}
        assert overrides.apply_override("task-1", "P", ov) == "T"

    def test_no_override_falls_back_to_derived(self):
        assert overrides.apply_override("task-1", "P", {}) == "P"

    def test_empty_stage_in_entry_falls_back_to_derived(self):
        # Defensive: a malformed entry with no "stage" key shouldn't blank a row.
        ov = {"task-1": {"owner": "Dani"}}
        assert overrides.apply_override("task-1", "P", ov) == "P"


class TestApplyOwner:
    def test_owner_present(self):
        ov = {"task-1": {"stage": "T", "owner": "Sterling"}}
        assert overrides.apply_owner("task-1", ov) == "Sterling"

    def test_owner_absent_defaults_empty(self):
        assert overrides.apply_owner("task-1", {}) == ""
