"""
Tests for ag_memory_write.py — AG write-back capability.

Tests are filesystem-isolated: a temp dir replaces MEMORY_DIR for each test.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.memory.ag_memory_write import (
    ag_write_memory,
    MEMORY_DIR,
    _INDEX_FILE,
    _SLUG_RE,
    _find_section_line,
    _yaml_safe,
    _slugify,
)


@pytest.fixture
def tmp_memory(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr("core.memory.ag_memory_write.MEMORY_DIR", tmp)
    monkeypatch.setattr("core.memory.ag_memory_write._INDEX_FILE", tmp / "MEMORY.md")
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


class TestAgWriteMemory:
    def test_writes_file_with_correct_name(self, tmp_memory):
        r = ag_write_memory(mem_type="feedback", slug="test_note",
                            name="Test Note", description="A test", body="Hello")
        assert r["ok"]
        assert (tmp_memory / "feedback_test_note.md").exists()

    def test_invalid_type_rejected(self, tmp_memory):
        r = ag_write_memory(mem_type="invalid")
        assert not r["ok"]
        assert "invalid" in r.get("error", "").lower()

    def test_body_content_preserved(self, tmp_memory):
        r = ag_write_memory(mem_type="reference", slug="my_ref",
                            body="**bold** and `code`")
        assert r["ok"]
        content = (tmp_memory / "reference_my_ref.md").read_text()
        assert "**bold**" in content
        assert "`code`" in content

    def test_frontmatter_format(self, tmp_memory):
        r = ag_write_memory(mem_type="project", slug="test_project",
                            name="Test Project", description="A project test")
        content = (tmp_memory / "project_test_project.md").read_text()
        assert content.startswith("---")
        assert "name: test_project" in content
        assert "description:" in content and "A project test" in content
        assert "origin: ag" in content
        assert "engine: gemini" in content

    def test_overwrite_detected(self, tmp_memory):
        ag_write_memory(mem_type="feedback", slug="dup", body="first")
        r = ag_write_memory(mem_type="feedback", slug="dup", body="second")
        assert r["ok"]
        assert r["was_overwrite"] is True

    def test_no_overwrite_first_write(self, tmp_memory):
        r = ag_write_memory(mem_type="feedback", slug="fresh", body="first")
        assert r["was_overwrite"] is False

    def test_memory_index_updated(self, tmp_memory):
        ag_write_memory(mem_type="project", slug="idx_test",
                        name="Idx Test", description="check index")
        idx = (tmp_memory / "MEMORY.md").read_text()
        assert "Idx Test" in idx
        assert "project_idx_test.md" in idx

    def test_index_no_duplicate(self, tmp_memory):
        ag_write_memory(mem_type="feedback", slug="no_dup",
                        name="No Dup", description="first")
        ag_write_memory(mem_type="feedback", slug="no_dup",
                        name="No Dup", description="first")
        idx = (tmp_memory / "MEMORY.md").read_text()
        assert idx.count("no_dup") == 1

    def test_session_id_persisted(self, tmp_memory):
        r = ag_write_memory(mem_type="feedback", slug="sid_test",
                            session_id="abc123")
        content = (tmp_memory / "feedback_sid_test.md").read_text()
        assert "abc123" in content

    def test_auto_slug_from_name(self, tmp_memory):
        r = ag_write_memory(mem_type="feedback", name="My Cool Observation")
        assert r["ok"]
        assert "feedback_my-cool-observation" in r["path"]

    def test_empty_body_generates_fallback(self, tmp_memory):
        r = ag_write_memory(mem_type="feedback", slug="empty_body",
                            name="Empty", description="no body given")
        content = (tmp_memory / "feedback_empty_body.md").read_text()
        assert "AG write-back" in content

    def test_yaml_safe_colon_string(self):
        result = _yaml_safe("foo: bar")
        assert result.startswith('"')

    def test_yaml_safe_plain_string(self):
        result = _yaml_safe("hello world")
        assert result == "hello world"

    def test_slugify(self):
        assert _SLUG_RE.match(_slugify("Hello World!"))
        assert _slugify("Hello World!") == "hello-world"

    def test_find_section_line_exists(self):
        lines = ["# header", "## Existing Section", "some content"]
        pos = _find_section_line(lines, "Existing Section")
        assert pos == 2

    def test_find_section_line_missing(self):
        lines = ["# header", "## Other", "content"]
        pos = _find_section_line(lines, "Missing")
        assert pos == len(lines)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
