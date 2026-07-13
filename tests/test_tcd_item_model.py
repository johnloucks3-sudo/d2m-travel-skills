#!/usr/bin/env python3
"""
Offline tests for tcd.item_model — the Sheet row schema.

    python -m pytest tests/test_tcd_item_model.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd.item_model import Item, SHEET_COLUMNS, _flatten_comments  # noqa: E402


class TestSchema:
    def test_columns_are_stable_and_ordered(self):
        # id first (AppSheet key); link + status present (requirements #1/#5).
        assert SHEET_COLUMNS[0] == "id"
        for col in ("link", "stage", "status", "sourcePath", "from"):
            assert col in SHEET_COLUMNS

    def test_row_aligns_to_columns(self):
        it = Item.from_legacy(
            {"id": "task-1", "inbox": "operational", "type": "brief",
             "priority": "p1", "title": "T", "from": "Mission Board",
             "date": "2026-07-12", "snippet": "s", "body": "b", "comments": []},
            link="https://x", source_path="hale_state.json:open_tasks",
            stage="A", status="OPEN")
        row = it.to_row()
        assert len(row) == len(SHEET_COLUMNS)
        d = dict(zip(SHEET_COLUMNS, row))
        assert d["id"] == "task-1"
        assert d["from"] == "Mission Board"   # 'from' column <- source attr
        assert d["link"] == "https://x"
        assert d["stage"] == "A"
        assert d["status"] == "OPEN"

    def test_to_dict_roundtrips_columns(self):
        it = Item.from_legacy({"id": "x", "title": "t"}, link="L",
                              source_path="", stage="D", status="OPEN")
        d = it.to_dict()
        assert set(d.keys()) == set(SHEET_COLUMNS)
        assert d["link"] == "L"

    def test_owner_column_present_and_defaults_empty(self):
        assert "owner" in SHEET_COLUMNS
        it = Item.from_legacy({"id": "x"}, link="L", source_path="",
                              stage="P", status="Open")
        assert it.owner == ""

    def test_owner_passed_through(self):
        it = Item.from_legacy({"id": "x"}, link="L", source_path="",
                              stage="T", status="Open", owner="Sterling")
        assert dict(zip(SHEET_COLUMNS, it.to_row()))["owner"] == "Sterling"


class TestCommentFlattening:
    def test_list_becomes_json_string(self):
        out = _flatten_comments([{"by": "Yoda", "text": "go"}])
        assert isinstance(out, str) and "Yoda" in out

    def test_empty(self):
        assert _flatten_comments([]) == ""
        assert _flatten_comments(None) == ""

    def test_string_passthrough(self):
        assert _flatten_comments("already text") == "already text"


class TestFromLegacyDefaults:
    def test_missing_fields_default_empty(self):
        it = Item.from_legacy({"id": "only-id"}, link="L", source_path="",
                              stage="REF", status="REF")
        assert it.title == "" and it.body == "" and it.source == ""
        assert it.status == "REF"
