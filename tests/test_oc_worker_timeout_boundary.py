"""Tests for oc_worker.py's timeout-boundary deliverable check (2026-08-11 fix).

A task killed on the 300s timeout is not automatically a real failure -- if
its deliverable file exists and was written after the task was claimed, the
work actually completed near the kill boundary. This replaces a blind
bb.fail() with a freshness check.
"""
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _deliverable_proves_out(dl_path: str, claimed_at: str) -> bool:
    """Mirrors the inline logic in scripts/oc_worker.py's timeout handler."""
    try:
        dl = Path(dl_path)
        if dl.is_file() and claimed_at:
            claimed_ts = datetime.fromisoformat(claimed_at)
            dl_mtime = datetime.fromtimestamp(dl.stat().st_mtime, tz=timezone.utc)
            return dl_mtime >= claimed_ts
    except Exception:
        return False
    return False


def test_fresh_deliverable_after_claim_proves_out(tmp_path):
    claimed_at = datetime.now(timezone.utc).isoformat()
    time.sleep(0.05)
    dl = tmp_path / "deliverable.md"
    dl.write_text("real content")
    assert _deliverable_proves_out(str(dl), claimed_at) is True


def test_stale_deliverable_from_before_claim_does_not_prove_out(tmp_path):
    dl = tmp_path / "deliverable.md"
    dl.write_text("stale content from a previous run")
    time.sleep(0.05)
    claimed_at = datetime.now(timezone.utc).isoformat()
    assert _deliverable_proves_out(str(dl), claimed_at) is False


def test_missing_deliverable_does_not_prove_out(tmp_path):
    dl = tmp_path / "never_written.md"
    claimed_at = datetime.now(timezone.utc).isoformat()
    assert _deliverable_proves_out(str(dl), claimed_at) is False
