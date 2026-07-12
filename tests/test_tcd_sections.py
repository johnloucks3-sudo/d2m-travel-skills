#!/usr/bin/env python3
"""
Offline tests for tcd.sections — Intel / Tech Scans / Next 7 Days collectors.

No credentials, no network: drive mirroring and calendar events are injected
via mirror_fn / calendar_events_fn params, and file scans point at tmp_path
fixtures via monkeypatched module-level paths.
    python -m pytest tests/test_tcd_sections.py -v
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import sections  # noqa: E402


def _fake_mirror(path, folder, mime):
    return f"https://drive.google.com/file/d/fake-{path.name}/view"


class TestCollectIntel:
    def test_finds_recent_md_reports(self, tmp_path, monkeypatch):
        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        (intel_dir / "daily_innovation_digest.md").write_text(
            "# Daily Innovation Digest\nSome content about DeepSeek R1.")
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        monkeypatch.setattr(sections, "INTEL_DIR", intel_dir)
        monkeypatch.setattr(sections, "SHIP_INTEL_DIR", tmp_path / "nonexistent")
        items = sections.collect_intel(mirror_fn=_fake_mirror)
        assert len(items) == 1
        assert items[0].id == "intel-daily_innovation_digest"
        assert items[0].title == "Daily Innovation Digest"
        assert "fake-daily_innovation_digest.md" in items[0].link
        assert items[0].stage == "REF"

    def test_excludes_files_older_than_window(self, tmp_path, monkeypatch):
        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        old_file = intel_dir / "old_report.md"
        old_file.write_text("# Old Report\nStale content.")
        old_time = time.time() - 30 * 86400
        import os
        os.utime(old_file, (old_time, old_time))
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        monkeypatch.setattr(sections, "INTEL_DIR", intel_dir)
        monkeypatch.setattr(sections, "SHIP_INTEL_DIR", tmp_path / "nonexistent")
        items = sections.collect_intel(days=14, mirror_fn=_fake_mirror)
        assert items == []

    def test_missing_intel_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "INTEL_DIR", tmp_path / "does_not_exist")
        monkeypatch.setattr(sections, "SHIP_INTEL_DIR", tmp_path / "also_missing")
        items = sections.collect_intel(mirror_fn=_fake_mirror)
        assert items == []

    def test_mirror_failure_falls_back_to_drive_search(self, tmp_path, monkeypatch):
        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        (intel_dir / "report.md").write_text("# Report\nContent.")
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        monkeypatch.setattr(sections, "INTEL_DIR", intel_dir)
        monkeypatch.setattr(sections, "SHIP_INTEL_DIR", tmp_path / "nonexistent")
        items = sections.collect_intel(mirror_fn=lambda p, f, m: "")
        assert len(items) == 1
        assert items[0].link.startswith("https://drive.google.com/drive/search?q=")

    def test_respects_max_items_cap(self, tmp_path, monkeypatch):
        intel_dir = tmp_path / "intel"
        intel_dir.mkdir()
        for i in range(10):
            (intel_dir / f"report_{i}.md").write_text(f"# Report {i}\nContent.")
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        monkeypatch.setattr(sections, "INTEL_DIR", intel_dir)
        monkeypatch.setattr(sections, "SHIP_INTEL_DIR", tmp_path / "nonexistent")
        items = sections.collect_intel(max_items=3, mirror_fn=_fake_mirror)
        assert len(items) == 3


class TestCollectTechscans:
    def test_finds_configured_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        ci_file = tmp_path / "config" / "ci_registry.json"
        ci_file.parent.mkdir(parents=True)
        ci_file.write_text('{"version": "1.0"}')
        monkeypatch.setattr(sections, "_TECHSCAN_FILES",
                            [("config/ci_registry.json", "CI/CD Tool Registry")])
        items = sections.collect_techscans(mirror_fn=_fake_mirror)
        assert len(items) == 1
        assert items[0].id == "techscan-ci_registry"
        assert "CI/CD Tool Registry" in items[0].title

    def test_stale_file_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        f = tmp_path / "OpsCenter" / "state" / "dead_code_report.txt"
        f.parent.mkdir(parents=True)
        f.write_text("dead code found")
        import os
        old_time = time.time() - 10 * 86400
        os.utime(f, (old_time, old_time))
        monkeypatch.setattr(sections, "_TECHSCAN_FILES",
                            [("OpsCenter/state/dead_code_report.txt", "Dead Code Report")])
        items = sections.collect_techscans(mirror_fn=_fake_mirror)
        assert len(items) == 1
        assert items[0].title.startswith("⚠ STALE")
        assert items[0].priority == "p1"

    def test_fresh_file_not_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        f = tmp_path / "OpsCenter" / "state" / "heartbeat_scan_latest.json"
        f.parent.mkdir(parents=True)
        f.write_text('{"status": "ok"}')
        monkeypatch.setattr(sections, "_TECHSCAN_FILES",
                            [("OpsCenter/state/heartbeat_scan_latest.json", "Heartbeat Scan")])
        items = sections.collect_techscans(mirror_fn=_fake_mirror)
        assert not items[0].title.startswith("⚠ STALE")
        assert items[0].priority == "routine"

    def test_missing_file_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        monkeypatch.setattr(sections, "_TECHSCAN_FILES",
                            [("config/does_not_exist.json", "Missing File")])
        items = sections.collect_techscans(mirror_fn=_fake_mirror)
        assert items == []

    def test_every_row_has_a_link(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sections, "ROOT", tmp_path)
        f = tmp_path / "config" / "ci_registry.json"
        f.parent.mkdir(parents=True)
        f.write_text("{}")
        monkeypatch.setattr(sections, "_TECHSCAN_FILES",
                            [("config/ci_registry.json", "CI Registry")])
        items = sections.collect_techscans(mirror_fn=_fake_mirror)
        assert all(i.link for i in items)


class TestCollectNext7:
    def test_calendar_events_included(self):
        fake_events = lambda: [
            {"id": "evt1", "summary": "Flight to Denver", "start": {"dateTime": "2026-07-15T10:00:00Z"},
             "htmlLink": "https://calendar.google.com/event?eid=abc", "location": "DEN"},
        ]
        items = sections.collect_next7(calendar_events_fn=fake_events)
        cal_items = [i for i in items if i.id.startswith("next7-cal-")]
        assert len(cal_items) == 1
        assert cal_items[0].link == "https://calendar.google.com/event?eid=abc"
        assert cal_items[0].title == "Flight to Denver"

    def test_no_calendar_events(self):
        items = sections.collect_next7(calendar_events_fn=lambda: [])
        assert not any(i.id.startswith("next7-cal-") for i in items)

    def test_fpd_within_window_included(self, monkeypatch):
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        future_fpd = (now + timedelta(days=3)).date().isoformat()
        fake_fpd_state = {"clients": [
            {"client": "McLeod", "dossier": "McLeod_McGlasson", "fpd": future_fpd,
             "payment_status": "OPEN", "fpd_amount": "11943.15"},
        ]}
        monkeypatch.setattr(sections, "_load_json",
                            lambda path, default=None: fake_fpd_state if path == sections.FPD_STATE
                            else (default if default is not None else {}))
        items = sections.collect_next7(calendar_events_fn=lambda: [], now=now)
        fpd_items = [i for i in items if i.id.startswith("next7-fpd-")]
        assert len(fpd_items) == 1
        assert "McLeod" in fpd_items[0].title
        assert fpd_items[0].link  # dossier link always non-empty

    def test_fpd_outside_window_excluded(self, monkeypatch):
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        far_future_fpd = (now + timedelta(days=30)).date().isoformat()
        fake_fpd_state = {"clients": [
            {"client": "Loucks", "dossier": "Loucks_SilverNova", "fpd": far_future_fpd},
        ]}
        monkeypatch.setattr(sections, "_load_json",
                            lambda path, default=None: fake_fpd_state if path == sections.FPD_STATE
                            else (default if default is not None else {}))
        items = sections.collect_next7(calendar_events_fn=lambda: [], now=now)
        assert not any(i.id.startswith("next7-fpd-") for i in items)

    def test_mission_suspense_within_window(self, monkeypatch):
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        future = (now + timedelta(days=2)).date().isoformat()
        fake_mb = {"missions": [{"id": "MISSION-001", "title": "Test mission",
                                 "suspense_date": future}], "active_missions": []}
        monkeypatch.setattr(sections, "_load_json",
                            lambda path, default=None: fake_mb if path == sections.MISSION_BOARD
                            else (default if default is not None else {}))
        items = sections.collect_next7(calendar_events_fn=lambda: [], now=now)
        mission_items = [i for i in items if i.id.startswith("next7-mission-")]
        assert len(mission_items) == 1
        assert "MISSION-001" in mission_items[0].title

    def test_mission_no_suspense_date_excluded(self, monkeypatch):
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        fake_mb = {"missions": [{"id": "MISSION-002", "suspense_date": None}], "active_missions": []}
        monkeypatch.setattr(sections, "_load_json",
                            lambda path, default=None: fake_mb if path == sections.MISSION_BOARD
                            else (default if default is not None else {}))
        items = sections.collect_next7(calendar_events_fn=lambda: [], now=now)
        assert not any(i.id.startswith("next7-mission-") for i in items)

    def test_all_next7_items_have_links(self, monkeypatch):
        now = datetime(2026, 7, 12, tzinfo=timezone.utc)
        fake_events = lambda: [{"id": "e1", "summary": "Event", "start": {"date": "2026-07-13"},
                                "htmlLink": "https://cal.google.com/e1", "location": ""}]
        fake_fpd = {"clients": [{"client": "X", "dossier": "X_dossier",
                                 "fpd": (now + timedelta(days=1)).date().isoformat()}]}
        monkeypatch.setattr(sections, "_load_json",
                            lambda path, default=None: fake_fpd if path == sections.FPD_STATE
                            else (default if default is not None else {}))
        items = sections.collect_next7(calendar_events_fn=fake_events, now=now)
        assert all(i.link for i in items)
