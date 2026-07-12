#!/usr/bin/env python3
"""
Offline tests for tcd.permalink — the deep-link builders (requirement #1).

No credentials or network: these are pure functions. Run:
    python -m pytest tests/test_tcd_permalink.py -v
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import permalink  # noqa: E402


class TestGmailPermalink:
    def test_builds_rfc822_search_link(self):
        link = permalink.gmail_permalink("<abc123@mail.example.com>")
        assert link.startswith("https://mail.google.com/mail/u/0/#search/rfc822msgid:")
        # angle brackets stripped, id URL-encoded (@ -> %40)
        assert "abc123%40mail.example.com" in link
        assert "<" not in link and ">" not in link

    def test_strips_and_quotes(self):
        link = permalink.gmail_permalink("  weird id/with?chars  ")
        assert "rfc822msgid:" in link
        # spaces / slashes / question marks are percent-encoded
        assert " " not in link.split("rfc822msgid:")[1]
        assert "/" not in link.split("rfc822msgid:")[1]

    def test_empty_message_id_returns_blank(self):
        assert permalink.gmail_permalink("") == ""
        assert permalink.gmail_permalink("   ") == ""
        assert permalink.gmail_permalink("<>") == ""

    def test_uses_api_id_would_be_wrong(self):
        # Guard the core research finding: we must search by Message-ID, never
        # embed a raw Gmail API id as if it were a permalink id.
        link = permalink.gmail_permalink("<real-message-id@x>")
        assert "rfc822msgid:" in link


class TestDriveAndGmailSearch:
    def test_drive_search_link_encodes_query(self):
        link = permalink.drive_search_link("Nancy Lyons")
        assert link == "https://drive.google.com/drive/search?q=Nancy%20Lyons"

    def test_drive_search_link_blank_query(self):
        assert permalink.drive_search_link("") == ""

    def test_gmail_search_link(self):
        link = permalink.gmail_search_link("FPD overdue")
        assert link.startswith("https://mail.google.com/mail/u/0/#search/")
        assert "FPD%20overdue" in link


class TestFirstNonempty:
    def test_returns_first_nonempty(self):
        assert permalink.first_nonempty("", "  ", "x", "y") == "x"

    def test_all_empty(self):
        assert permalink.first_nonempty("", None, "  ") == ""


class TestDeriveLink:
    def test_gmail_item_uses_message_id(self):
        item = {"id": "gmail-johnloucks3-18f", "title": "Hi",
                "message_id_header": "<m1@x>", "tags": ["gmail", "johnloucks3"]}
        link = permalink.derive_link(item)
        assert "rfc822msgid:" in link and "m1%40x" in link

    def test_gmail_item_falls_back_to_subject_search(self):
        item = {"id": "gmail-d2mconcierge-9a", "title": "Booking question",
                "message_id_header": "", "tags": ["gmail", "d2mconcierge"]}
        link = permalink.derive_link(item)
        assert link.startswith("https://mail.google.com/mail/u/0/#search/")
        assert "Booking" in link

    def test_calendar_htmllink_wins(self):
        item = {"id": "cal-1", "title": "Flight", "htmlLink": "https://calendar.google.com/event?eid=z"}
        assert permalink.derive_link(item) == "https://calendar.google.com/event?eid=z"

    def test_drive_webviewlink_wins(self):
        item = {"id": "drv-1", "title": "Doc", "webViewLink": "https://drive.google.com/file/d/xyz/view"}
        assert permalink.derive_link(item) == "https://drive.google.com/file/d/xyz/view"

    def test_dossier_uses_client_tag_drive_search(self):
        item = {"id": "dossier-Lyons_Nancy_Ken", "title": "Lyons dossier",
                "tags": ["dossier", "Lyons"]}
        link = permalink.derive_link(item)
        assert link.startswith("https://drive.google.com/drive/search?q=")
        assert "Lyons" in link

    def test_internal_item_always_gets_nonempty_link(self):
        item = {"id": "task-MISSION-814", "title": "Do the thing", "tags": []}
        assert permalink.derive_link(item)  # non-empty

    def test_degenerate_title_falls_back_to_filename(self):
        # Dossiers start with a YAML '---' line → title "---" is useless as a
        # search; the link must instead resolve to the humanized filename.
        item = {"id": "dossier-DOSSIER_DoorCounty_SisterBay_Sep2026",
                "title": "---", "tags": ["dossier"]}
        link = permalink.derive_link(item)
        assert "---" not in link
        assert "DoorCounty" in link and "SisterBay" in link

    def test_humanize_stem_strips_prefix_and_separators(self):
        assert permalink._humanize_stem("DOSSIER_DoorCounty_SisterBay_Sep2026") == \
            "DoorCounty SisterBay Sep2026"
        assert permalink._humanize_stem("SO_PDTAC_WORKFLOW_20260711") == \
            "PDTAC WORKFLOW 20260711"

    def test_is_degenerate(self):
        assert permalink._is_degenerate("---")
        assert permalink._is_degenerate("   ")
        assert not permalink._is_degenerate("Lyons")


class TestDeriveSourcePath:
    def test_maps_each_prefix(self):
        assert permalink.derive_source_path({"id": "so-SO_FOO"}) == "standing_orders/SO_FOO.md"
        assert permalink.derive_source_path({"id": "dossier-Bar"}) == "dossiers/Bar.md"
        assert permalink.derive_source_path({"id": "task-M1"}) == "hale_state.json:open_tasks"
        assert permalink.derive_source_path({"id": "alert-A1"}) == "hale_state.json:deferred_alerts"
        assert permalink.derive_source_path({"id": "proj-P1"}) == \
            "hale_state.json:project_tracking.active_projects"
        assert permalink.derive_source_path({"id": "gmail-johnloucks3-1"}) == "gmail:johnloucks3-1"

    def test_unknown_prefix_blank(self):
        assert permalink.derive_source_path({"id": "mystery-1"}) == ""
