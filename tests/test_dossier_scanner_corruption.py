#!/usr/bin/env python3
"""
Offline regression tests for _check_corruption (core/booking/thunderbird_dossier_scanner.py).

2026-07-13 LIVE INCIDENT: Antigravity ran a real dossier_alert_digest task and
reported 11 dossiers (including the Commander's own Loucks files) as
"Repeated-line corruption ... DO NOT USE for client work. Restore from Drive
or git." All 11 were false positives — the heuristic flagged '---' (a normal
YAML frontmatter / markdown section-divider) as if it were duplicated content
from a write-loop bug. Traced via the raw MCP tool output cache
(~/.gemini/antigravity-cli/brain/<id>/.system_generated/steps/14/output.txt)
to confirm the false claim came from this function itself, not from
Antigravity's own reasoning — it faithfully reported what scan_dossiers told it.

Run: python -m pytest tests/test_dossier_scanner_corruption.py -v
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.booking.thunderbird_dossier_scanner import _check_corruption  # noqa: E402


def _write(content: str) -> Path:
    p = Path(tempfile.mktemp(suffix=".md"))
    p.write_text(content, encoding="utf-8")
    return p


class TestStructuralMarkersNotFlagged:
    def test_frontmatter_and_section_dividers_not_flagged(self):
        # Mirrors the real shape of a legitimate dossier: YAML frontmatter
        # open/close plus '---' before each markdown section header.
        content = (
            "---\nclient: Test\nbooking: 12345\n---\n"
            "# DOSSIER\n\n---\n\n## VOYAGE OVERVIEW\n\ntext\n\n"
            "---\n\n## KEY DATES\n\ntext\n\n"
            "---\n\n## FLIGHTS\n\ntext\n\n"
            "---\n\n## EXCURSIONS\n\ntext\n\n"
            "---\n\n## PAYMENTS\n\ntext\n\n"
            "---\n\n## NOTES\n\ntext\n\n"
            "---\n\n## STATUS\n\ntext\n\n"
            "---\n\n## CONTACT\n\ntext\n\n"
            "---\n\n## MISC\n\ntext\n\n"
            "---\n\n## END\n\ntext\n"
        )
        text = content
        lines = content.splitlines(keepends=True)
        p = _write(content)
        try:
            assert _check_corruption(p, text, lines) is None
        finally:
            p.unlink()

    def test_real_loucks_dossier_file_not_flagged(self):
        p = Path(__file__).resolve().parent.parent / "dossiers" / "Loucks_Regent_Grandeur_3122006.md"
        if not p.exists():
            return  # environment without dossiers/ present — skip, not a failure
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        assert _check_corruption(p, text, lines) is None


class TestGenuineCorruptionStillCaught:
    def test_duplicated_content_line_still_flagged(self):
        content = "Client: Test Client\n" + ("ERROR: retry failed, retrying connection...\n" * 20) + "Booking: 12345\n"
        lines = content.splitlines(keepends=True)
        p = _write(content)
        try:
            alert = _check_corruption(p, content, lines)
            assert alert is not None
            assert alert.category == "corruption"
            assert "ERROR: retry failed" in alert.message
        finally:
            p.unlink()

    def test_oversized_file_still_flagged(self):
        content = "x" * (600 * 1024)  # 600KB, over the 500KB threshold
        p = _write(content)
        try:
            alert = _check_corruption(p, content, content.splitlines(keepends=True))
            assert alert is not None
            assert "far exceeds normal range" in alert.message
        finally:
            p.unlink()

    def test_asterisk_and_underscore_dividers_also_excluded(self):
        content = "Client: Test\n" + ("***\n" * 15) + "Booking: 1\n" + ("___\n" * 15) + "Status: ok\n"
        lines = content.splitlines(keepends=True)
        p = _write(content)
        try:
            assert _check_corruption(p, content, lines) is None
        finally:
            p.unlink()
