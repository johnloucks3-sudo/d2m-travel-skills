#!/usr/bin/env python3
"""
Offline tests for tcd.sheet_sync --dry-run.

Exercises the full collect→enrich→row pipeline against the real on-disk Wing
state (hale_state.json, standing_orders/, dossiers/) with NO credentials and NO
writes to Google. Gmail is skipped (needs creds; verified live on the box).

    python -m pytest tests/test_tcd_sync_dryrun.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import sheet_sync  # noqa: E402
from tcd.item_model import SHEET_COLUMNS  # noqa: E402


class TestCollectRows:
    def test_collects_local_rows(self):
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        assert isinstance(rows, list) and len(rows) > 0

    def test_every_row_has_a_nonempty_link(self):
        # The Commander's #1 requirement: no dead ends.
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        missing = [r["id"] for r in rows if not r.get("link")]
        assert not missing, f"rows with no link: {missing[:10]}"

    def test_every_row_has_all_columns(self):
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        for r in rows:
            assert set(r.keys()) == set(SHEET_COLUMNS)

    def test_ids_are_unique(self):
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), "duplicate item ids would collide as Sheet keys"

    def test_stages_are_valid(self):
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        for r in rows:
            assert r["stage"] in ("P", "D", "T", "A", "C", "REF")

    def test_reference_items_present(self):
        # standing orders + dossiers should surface as REF material
        rows = sheet_sync.collect_rows(include_gmail=False, include_keep=False)
        refs = [r for r in rows if r["stage"] == "REF"]
        assert refs, "expected standing-order/dossier reference rows"


class TestDryRunCli:
    def test_dry_run_writes_json_with_all_rows_linked(self, tmp_path):
        out = tmp_path / "rows.json"
        rc = sheet_sync.main(["--dry-run", "--no-gmail", "--no-keep", "--out", str(out)])
        assert rc == 0
        payload = json.loads(out.read_text())
        assert payload["columns"] == SHEET_COLUMNS
        assert payload["count"] == len(payload["rows"])
        assert payload["count"] > 0
        assert all(r.get("link") for r in payload["rows"])

    def test_dry_run_touches_no_google_config(self, tmp_path):
        # Dry-run must not create/modify the live Sheet config.
        before = sheet_sync.CONFIG_PATH.exists()
        before_txt = sheet_sync.CONFIG_PATH.read_text() if before else None
        sheet_sync.main(["--dry-run", "--no-gmail", "--no-keep", "--out", str(tmp_path / "r.json")])
        after = sheet_sync.CONFIG_PATH.exists()
        assert before == after
        if before:
            assert sheet_sync.CONFIG_PATH.read_text() == before_txt
