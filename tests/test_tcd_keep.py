#!/usr/bin/env python3
"""
Offline tests for Keep integration (Phase 5a): permalink builder + collector.

No credentials, no network: the keep module is monkeypatched via
sys.modules before import, and permalink tests are pure functions.
    python -m pytest tests/test_tcd_keep.py -v
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import permalink  # noqa: E402


class TestKeepPermalink:
    def test_builds_note_url(self):
        link = permalink.keep_permalink("abc123XYZ")
        assert link == "https://keep.google.com/#NOTE/abc123XYZ"

    def test_strips_whitespace(self):
        assert permalink.keep_permalink("  note-1  ") == "https://keep.google.com/#NOTE/note-1"

    def test_empty_id_returns_blank(self):
        assert permalink.keep_permalink("") == ""
        assert permalink.keep_permalink("   ") == ""

    def test_derive_link_routes_keep_items(self):
        item = {"id": "keep-abc123", "title": "Flight confirmation"}
        assert permalink.derive_link(item) == "https://keep.google.com/#NOTE/abc123"

    def test_derive_source_path_routes_keep_items(self):
        assert permalink.derive_source_path({"id": "keep-abc123"}) == "keep:abc123"


class TestKeepCollector:
    def _install_fake_keep_module(self, monkeypatch, notes):
        fake = types.ModuleType("thunderbird_keep")
        fake.list_notes = lambda max_results=30: {
            "status": "success", "count": len(notes), "notes": notes,
        }
        monkeypatch.setitem(sys.modules, "thunderbird_keep", fake)
        monkeypatch.setitem(sys.modules, "api.thunderbird_keep", fake)

    def test_collect_keep_maps_notes_to_items(self, monkeypatch):
        from tcd import collectors
        notes = [
            {"id": "n1", "title": "Leslie Loucks flights", "text": "DEN Jul 18-25",
             "pinned": True, "color": "WHITE", "type": "note"},
            {"id": "n2", "title": "Grocery list", "text": "milk, eggs",
             "pinned": False, "color": "WHITE", "type": "list"},
        ]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        assert len(items) == 2
        ids = [i["id"] for i in items]
        assert "keep-n1" in ids and "keep-n2" in ids

    def test_collect_keep_sets_reference_inbox(self, monkeypatch):
        from tcd import collectors
        notes = [{"id": "n1", "title": "Note", "text": "", "pinned": False,
                  "color": "WHITE", "type": "note"}]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        assert items[0]["inbox"] == "reference"
        assert items[0]["type"] == "note"

    def test_collect_keep_pinned_gets_higher_priority(self, monkeypatch):
        from tcd import collectors
        notes = [
            {"id": "n1", "title": "Pinned", "text": "", "pinned": True,
             "color": "WHITE", "type": "note"},
            {"id": "n2", "title": "Not pinned", "text": "", "pinned": False,
             "color": "WHITE", "type": "note"},
        ]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        pinned = next(i for i in items if i["id"] == "keep-n1")
        unpinned = next(i for i in items if i["id"] == "keep-n2")
        assert pinned["priority"] == "p2"
        assert unpinned["priority"] == "routine"
        assert "pinned" in pinned["tags"]

    def test_collect_keep_skips_notes_without_id(self, monkeypatch):
        from tcd import collectors
        notes = [{"id": "", "title": "Broken", "text": "", "pinned": False,
                  "color": "WHITE", "type": "note"}]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        assert items == []

    def test_collect_keep_never_leaks_note_body_content(self, monkeypatch):
        # SECURITY REGRESSION TEST — 2026-07-12 live incident: an RSA private
        # key, a Cloudflare access token, and multiple raw API keys were
        # copied verbatim into the production Sheet because collect_keep
        # mirrored note.text into body/snippet. The Commander uses Keep as a
        # credentials store; body/snippet must NEVER contain the source
        # text, under ANY note content — not just obviously-named secrets.
        from tcd import collectors
        notes = [
            {"id": "n1", "title": "Grocery list", "text": "milk, eggs, bread",
             "pinned": False, "color": "WHITE", "type": "note"},
            {"id": "n2", "title": "Random Note", "text": "sk-ant-api03-FAKE_SECRET_VALUE_xyz",
             "pinned": False, "color": "WHITE", "type": "note"},
            {"id": "n3", "title": "🔑 API Keys", "text": "-----BEGIN RSA PRIVATE KEY-----\nMIIJ...",
             "pinned": False, "color": "WHITE", "type": "note"},
        ]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        for item in items:
            assert "milk" not in item["body"]
            assert "sk-ant-api03" not in item["body"]
            assert "BEGIN RSA PRIVATE KEY" not in item["body"]
            assert "milk" not in item["snippet"]
            assert "sk-ant-api03" not in item["snippet"]
            assert "BEGIN RSA PRIVATE KEY" not in item["snippet"]
        # Titles ARE allowed through — that's the point of the dashboard.
        titles = [i["title"] for i in items]
        assert "🔑 API Keys" in titles

    def test_collect_keep_untitled_fallback(self, monkeypatch):
        from tcd import collectors
        notes = [{"id": "n1", "title": "", "text": "some content", "pinned": False,
                  "color": "WHITE", "type": "note"}]
        self._install_fake_keep_module(monkeypatch, notes)
        items = collectors.collect_keep()
        assert items[0]["title"] == "(untitled note)"

    def test_collect_keep_failure_returns_empty_not_raises(self, monkeypatch):
        from tcd import collectors
        fake = types.ModuleType("thunderbird_keep")
        def boom(max_results=30):
            raise RuntimeError("no credentials")
        fake.list_notes = boom
        monkeypatch.setitem(sys.modules, "thunderbird_keep", fake)
        monkeypatch.setitem(sys.modules, "api.thunderbird_keep", fake)
        items = collectors.collect_keep()
        assert items == []

    def test_collected_keep_items_all_get_links(self, monkeypatch):
        from tcd import collectors
        notes = [{"id": "n1", "title": "Note", "text": "", "pinned": False,
                  "color": "WHITE", "type": "note"}]
        self._install_fake_keep_module(monkeypatch, notes)
        # collect_all enriches with derive_link — confirm the keep- prefix
        # routes through to a real keep.google.com permalink, not a Drive
        # search fallback.
        enriched = [collectors._enrich(i) for i in collectors.collect_keep()]
        assert enriched[0].link == "https://keep.google.com/#NOTE/n1"


class TestSmsCollector:
    def _install_fake_sms_module(self, monkeypatch, messages):
        fake = types.ModuleType("sms_gateway")
        fake.poll_inbox = lambda limit=30: messages
        monkeypatch.setitem(sys.modules, "sms_gateway", fake)
        monkeypatch.setitem(sys.modules, "tcd.sms_gateway", fake)

    def test_collect_sms_maps_messages_to_items(self, monkeypatch):
        from tcd import collectors
        messages = [
            {"id": "m1", "sender": "+17195551234", "text": "Client question",
             "receivedAt": "2026-07-12T10:00:00Z"},
        ]
        self._install_fake_sms_module(monkeypatch, messages)
        items = collectors.collect_sms()
        assert len(items) == 1
        assert items[0]["id"] == "sms-m1"
        assert items[0]["inbox"] == "operational"
        assert items[0]["from"] == "+17195551234"

    def test_collect_sms_skips_messages_without_id(self, monkeypatch):
        from tcd import collectors
        messages = [{"id": "", "sender": "+1", "text": "x", "receivedAt": ""}]
        self._install_fake_sms_module(monkeypatch, messages)
        assert collectors.collect_sms() == []

    def test_collect_sms_failure_returns_empty_not_raises(self, monkeypatch):
        from tcd import collectors
        fake = types.ModuleType("sms_gateway")
        def boom(limit=30):
            raise RuntimeError("gateway not configured")
        fake.poll_inbox = boom
        monkeypatch.setitem(sys.modules, "sms_gateway", fake)
        monkeypatch.setitem(sys.modules, "tcd.sms_gateway", fake)
        assert collectors.collect_sms() == []

    def test_collected_sms_items_get_sms_uri_links(self, monkeypatch):
        from tcd import collectors
        messages = [{"id": "m1", "sender": "+17195551234", "text": "Hi",
                    "receivedAt": "2026-07-12T10:00:00Z"}]
        self._install_fake_sms_module(monkeypatch, messages)
        enriched = [collectors._enrich(i) for i in collectors.collect_sms()]
        assert enriched[0].link == "sms:+17195551234"
