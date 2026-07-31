from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from core.ci.ci_auto_repair_engine import repair_email_handling


def test_repair_email_handling_disabled_timer_enables(monkeypatch):
    """Test that when d2m-commander-digest.timer is disabled, repair_email_handling attempts to enable it with --now."""
    mock_run_calls = []

    def mock_subprocess_run(cmd, **kwargs):
        mock_run_calls.append(cmd)
        res = MagicMock()
        res.returncode = 0
        if "is-enabled" in cmd:
            res.stdout = "disabled\n"
        elif "is-active" in cmd:
            res.stdout = "inactive\n"
        else:
            res.stdout = "OK\n"
        return res

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    with patch.object(Path, "exists", return_value=True):
        res = repair_email_handling()

    assert res is True
    enable_cmd = ["systemctl", "--user", "enable", "--now", "d2m-commander-digest.timer"]
    assert enable_cmd in mock_run_calls


def test_repair_email_handling_active_timer_no_enable_needed(monkeypatch):
    """Test that when timer is already enabled and active, enable --now is not called."""
    mock_run_calls = []

    def mock_subprocess_run(cmd, **kwargs):
        mock_run_calls.append(cmd)
        res = MagicMock()
        res.returncode = 0
        if "is-enabled" in cmd:
            res.stdout = "enabled\n"
        elif "is-active" in cmd:
            res.stdout = "active\n"
        else:
            res.stdout = "OK\n"
        return res

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    with patch.object(Path, "exists", return_value=True):
        res = repair_email_handling()

    assert res is True
    enable_cmd = ["systemctl", "--user", "enable", "--now", "d2m-commander-digest.timer"]
    assert enable_cmd not in mock_run_calls


def test_repair_email_handling_missing_tokens_fails(monkeypatch):
    """Test that existing token-file check behavior is preserved: returns False if no tokens found."""
    def mock_subprocess_run(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        res.stdout = "enabled\n" if "is-enabled" in cmd else "active\n" if "is-active" in cmd else "OK\n"
        return res

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    with patch.object(Path, "exists", return_value=False):
        res = repair_email_handling()

    assert res is False
