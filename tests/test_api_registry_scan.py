#!/usr/bin/env python3
"""
tests/test_api_registry_scan.py — Unit tests for scripts/api_registry_scan.py

Tests cover:
  - .env parsing (_load_dotenv)
  - scan_status logic for all five states
  - key_present display formatting
  - run_scan() output shape and counters (mocked .env)
  - Sheets sync is NOT called in tests — patched out entirely

Run:
    cd /home/john/Thunderbird
    python3 -m pytest tests/test_api_registry_scan.py -v
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os

import pytest

# ── ensure project root is importable ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.api_registry_scan import (
    _load_dotenv,
    _scan_status,
    _key_present_display,
    run_scan,
    print_summary,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_dotenv(tmp_path):
    """Write a small .env file and return its Path."""
    content = """
# Thunderbird .env
ANTHROPIC_API_KEY=sk-ant-test-123
GROQ_API_KEY=gsk_test_456
GITHUB_TOKEN=ghp_test_789
XAI_API_KEY=xai-test-abc

# RETIRED key (commented out — should NOT be parsed as present)
# OPENAI_API_KEY=sk-retired

EMPTY_VALUE=
"""
    p = tmp_path / ".env"
    p.write_text(content)
    return p


@pytest.fixture
def minimal_registry(tmp_path):
    """Write a small api_registry.json and return its Path."""
    data = {
        "_meta": {"description": "test registry"},
        "credentials": [
            {
                "name": "Anthropic API",
                "env_var": "ANTHROPIC_API_KEY",
                "tier": "paid",
                "monthly_cost_usd": 20,
                "monthly_limit": "usage-based",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "active",
                "notes": "Test key",
                "added": "2026-01-01",
            },
            {
                "name": "Groq",
                "env_var": "GROQ_API_KEY",
                "tier": "free",
                "monthly_cost_usd": 0,
                "monthly_limit": "rate-limited",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "active",
                "notes": "Test groq",
                "added": "2026-01-01",
            },
            {
                "name": "Missing Key Service",
                "env_var": "MISSING_SERVICE_KEY",
                "tier": "paid",
                "monthly_cost_usd": 10,
                "monthly_limit": "usage-based",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "active",
                "notes": "Key not in .env",
                "added": "2026-01-01",
            },
            {
                "name": "Claude OAuth",
                "env_var": None,
                "tier": "MAX subscription",
                "monthly_cost_usd": 100,
                "monthly_limit": "40%",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "active",
                "notes": "OAuth — no env var",
                "added": "2026-01-01",
            },
            {
                "name": "Disabled Service",
                "env_var": "DISABLED_KEY",
                "tier": "paid",
                "monthly_cost_usd": 5,
                "monthly_limit": "none",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "disabled",
                "notes": "Turned off",
                "added": "2026-01-01",
            },
            {
                "name": "Expired Service",
                "env_var": "EXPIRED_KEY",
                "tier": "paid",
                "monthly_cost_usd": 5,
                "monthly_limit": "none",
                "usage_warning_pct": 80,
                "expires": "2025-01-01",
                "status": "expired",
                "notes": "Expired trial",
                "added": "2026-01-01",
            },
            {
                "name": "Pending Service",
                "env_var": "PENDING_KEY",
                "tier": "paid",
                "monthly_cost_usd": 0,
                "monthly_limit": "none",
                "usage_warning_pct": 80,
                "expires": None,
                "status": "pending_key",
                "notes": "Waiting for key",
                "added": "2026-06-22",
            },
        ],
    }
    p = tmp_path / "api_registry.json"
    p.write_text(json.dumps(data))
    return p


# ─────────────────────────────────────────────────────────────────────────────
# _load_dotenv tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadDotenv:
    def test_parses_present_keys(self, sample_dotenv):
        keys = _load_dotenv(sample_dotenv)
        assert "ANTHROPIC_API_KEY" in keys
        assert "GROQ_API_KEY" in keys
        assert "GITHUB_TOKEN" in keys
        assert "XAI_API_KEY" in keys

    def test_ignores_commented_keys(self, sample_dotenv):
        keys = _load_dotenv(sample_dotenv)
        assert "OPENAI_API_KEY" not in keys

    def test_includes_empty_value_keys(self, sample_dotenv):
        """A key with an empty value is still present in .env — count it."""
        keys = _load_dotenv(sample_dotenv)
        assert "EMPTY_VALUE" in keys

    def test_missing_file_returns_empty_set(self, tmp_path):
        keys = _load_dotenv(tmp_path / "nonexistent.env")
        assert keys == set()

    def test_blank_lines_ignored(self, tmp_path):
        p = tmp_path / ".env"
        p.write_text("\n\n\nFOO=bar\n\n")
        keys = _load_dotenv(p)
        assert keys == {"FOO"}


# ─────────────────────────────────────────────────────────────────────────────
# _scan_status tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScanStatus:
    """Tests for the five scan_status outcomes."""

    def test_active_key_present_is_ok(self):
        entry = {"status": "active", "env_var": "SOME_KEY"}
        kp, ss = _scan_status(entry, {"SOME_KEY"})
        assert kp is True
        assert ss == "OK"

    def test_active_oauth_no_env_var_is_ok(self):
        entry = {"status": "active", "env_var": None}
        kp, ss = _scan_status(entry, set())
        assert kp is None
        assert ss == "OK"

    def test_active_key_missing_is_missing_key(self):
        entry = {"status": "active", "env_var": "MISSING_KEY"}
        kp, ss = _scan_status(entry, set())
        assert kp is False
        assert ss == "MISSING_KEY"

    def test_pending_key_is_pending(self):
        entry = {"status": "pending_key", "env_var": "FUTURE_KEY"}
        kp, ss = _scan_status(entry, set())
        assert kp is None
        assert ss == "PENDING"

    def test_disabled_is_disabled(self):
        entry = {"status": "disabled", "env_var": "OLD_KEY"}
        kp, ss = _scan_status(entry, {"OLD_KEY"})
        assert kp is None
        assert ss == "DISABLED"

    def test_expired_is_expired(self):
        entry = {"status": "expired", "env_var": "EXP_KEY"}
        kp, ss = _scan_status(entry, {"EXP_KEY"})
        assert kp is None
        assert ss == "EXPIRED"


# ─────────────────────────────────────────────────────────────────────────────
# _key_present_display tests
# ─────────────────────────────────────────────────────────────────────────────

class TestKeyPresentDisplay:
    def test_yes_when_present(self):
        assert _key_present_display(True, "SOME_KEY") == "YES"

    def test_no_when_missing(self):
        assert _key_present_display(False, "SOME_KEY") == "NO"

    def test_na_oauth_when_env_var_none(self):
        assert _key_present_display(None, None) == "N/A (OAuth)"

    def test_na_when_key_present_none_but_env_var_set(self):
        # e.g. disabled/expired — env_var is defined but key_present is None
        assert _key_present_display(None, "DISABLED_KEY") == "N/A"


# ─────────────────────────────────────────────────────────────────────────────
# run_scan integration tests (no live Sheets)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunScan:
    """Patch REGISTRY_PATH to use the minimal fixture; pass sample_dotenv."""

    def test_output_shape(self, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)

        assert "scanned_at" in result
        assert "total" in result
        assert "ok_count" in result
        assert "warning_count" in result
        assert "error_count" in result
        assert "credentials" in result
        assert isinstance(result["credentials"], list)

    def test_credential_count(self, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        assert result["total"] == 7

    def test_ok_count_correct(self, minimal_registry, sample_dotenv, monkeypatch):
        """Anthropic (present), Groq (present), Claude OAuth (None env_var) → 3 OK."""
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        assert result["ok_count"] == 3

    def test_error_count_correct(self, minimal_registry, sample_dotenv, monkeypatch):
        """MISSING_SERVICE_KEY (active, not in .env) + EXPIRED → 2 errors."""
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        assert result["error_count"] == 2

    def test_warning_count_correct(self, minimal_registry, sample_dotenv, monkeypatch):
        """Disabled + Pending → 2 warnings."""
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        assert result["warning_count"] == 2

    def test_each_credential_has_required_fields(self, minimal_registry, sample_dotenv, monkeypatch):
        required = {"name", "env_var", "tier", "monthly_cost_usd", "monthly_limit",
                    "status", "key_present", "scan_status", "notes"}
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        for cred in result["credentials"]:
            missing = required - set(cred.keys())
            assert not missing, f"{cred.get('name')} missing: {missing}"

    def test_missing_dotenv_does_not_crash(self, minimal_registry, tmp_path, monkeypatch):
        """If .env is absent, all active+env_var creds should be MISSING_KEY."""
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=tmp_path / "no_such_file.env")
        missing_key_names = {
            c["name"] for c in result["credentials"] if c["scan_status"] == "MISSING_KEY"
        }
        # Anthropic, Groq, and Missing Key Service are all active with an env_var
        assert "Anthropic API" in missing_key_names
        assert "Groq" in missing_key_names

    def test_scan_status_values_are_valid(self, minimal_registry, sample_dotenv, monkeypatch):
        valid = {"OK", "PENDING", "MISSING_KEY", "DISABLED", "EXPIRED"}
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        result = run_scan(dotenv_path=sample_dotenv)
        for cred in result["credentials"]:
            assert cred["scan_status"] in valid, \
                f"{cred['name']}: unexpected scan_status '{cred['scan_status']}'"


# ─────────────────────────────────────────────────────────────────────────────
# Sheets sync: verify it is called correctly (not live)
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetsSyncMocked:
    """Verify sync_to_sheets delegates to the right Sheets calls."""

    def test_sync_calls_clear_and_batch_update(self, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        status = run_scan(dotenv_path=sample_dotenv)

        mock_clear = MagicMock(return_value={})
        mock_batch = MagicMock(return_value={})
        mock_ai_id = "16fuzoeD5WiR6loB7C2EbQJVbJ65admvrF_8oX8LBOd4"

        # Inject a fake core.data.sheets_write module
        fake_module = types.ModuleType("core.data.sheets_write")
        fake_module.clear_range = mock_clear
        fake_module.batch_update = mock_batch
        fake_module.AI_METRICS_SHEET_ID = mock_ai_id

        with patch.dict(sys.modules, {"core.data.sheets_write": fake_module}):
            from scripts.api_registry_scan import sync_to_sheets
            result = sync_to_sheets(status)

        assert result is True
        mock_clear.assert_called_once()
        mock_batch.assert_called_once()

    def test_sync_returns_false_on_exception(self, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        status = run_scan(dotenv_path=sample_dotenv)

        fake_module = types.ModuleType("core.data.sheets_write")
        fake_module.clear_range = MagicMock(side_effect=Exception("Auth error"))
        fake_module.batch_update = MagicMock()
        fake_module.AI_METRICS_SHEET_ID = "fake_id"

        with patch.dict(sys.modules, {"core.data.sheets_write": fake_module}):
            from scripts.api_registry_scan import sync_to_sheets
            result = sync_to_sheets(status)

        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# print_summary smoke test
# ─────────────────────────────────────────────────────────────────────────────

class TestPrintSummary:
    def test_prints_without_error(self, capsys, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        status = run_scan(dotenv_path=sample_dotenv)
        print_summary(status, sheets_ok=None)      # dry-run variant
        captured = capsys.readouterr()
        assert "API Registry Scan" in captured.out
        assert str(status["total"]) in captured.out

    def test_prints_sheets_ok(self, capsys, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        status = run_scan(dotenv_path=sample_dotenv)
        print_summary(status, sheets_ok=True)
        captured = capsys.readouterr()
        assert "Synced to Google Sheets" in captured.out

    def test_prints_sheets_failed(self, capsys, minimal_registry, sample_dotenv, monkeypatch):
        monkeypatch.setattr("scripts.api_registry_scan.REGISTRY_PATH", minimal_registry)
        status = run_scan(dotenv_path=sample_dotenv)
        print_summary(status, sheets_ok=False)
        captured = capsys.readouterr()
        assert "Sheets sync failed" in captured.out
