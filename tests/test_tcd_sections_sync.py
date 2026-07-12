#!/usr/bin/env python3
"""
Offline tests for tcd.sections_sync — critically, that --dry-run performs
NO live Drive writes. A real live-verification run caught this bug: the
first dry-run implementation called the real mirror_file() by default,
which silently created two production Drive folders and uploaded files
during what was supposed to be a side-effect-free check.

    python -m pytest tests/test_tcd_sections_sync.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import sections_sync  # noqa: E402


class TestDryRunNoLiveWrites:
    def test_dry_run_passes_noop_mirror_to_intel_and_techscans(self, monkeypatch):
        seen = {}
        def fake_collect_intel(**kwargs):
            seen["intel_mirror_fn"] = kwargs.get("mirror_fn")
            return []
        def fake_collect_techscans(**kwargs):
            seen["techscans_mirror_fn"] = kwargs.get("mirror_fn")
            return []
        def fake_collect_next7(**kwargs):
            return []
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "Intel", fake_collect_intel)
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "TechScans", fake_collect_techscans)
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "Next7", fake_collect_next7)
        sections_sync.main(["--dry-run"])
        assert seen["intel_mirror_fn"] is sections_sync._noop_mirror
        assert seen["techscans_mirror_fn"] is sections_sync._noop_mirror
        # Confirm the noop genuinely returns "" (no Drive call, no link fabricated)
        assert sections_sync._noop_mirror(Path("/x"), "folder", "text/plain") == ""

    def test_dry_run_writes_json_output(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "Intel", lambda **kw: [])
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "TechScans", lambda **kw: [])
        monkeypatch.setitem(sections_sync.SECTION_COLLECTORS, "Next7", lambda **kw: [])
        out = tmp_path / "sections.json"
        rc = sections_sync.main(["--dry-run", "--out", str(out)])
        assert rc == 0
        payload = json.loads(out.read_text())
        assert set(payload["tabs"].keys()) == {"Intel", "TechScans", "Next7"}
