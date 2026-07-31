import json
import pytest
from core.ops.thunderbird_rate_limit_guard import (
    GuardState,
    _compute_target_state,
    get_five_hour_pct,
    tokens_remaining,
)
import core.ops.thunderbird_rate_limit_guard as guard_mod


def test_get_five_hour_pct_valid(tmp_path, monkeypatch):
    cache_file = tmp_path / ".usage-cache.json"
    cache_file.write_text(
        json.dumps({"data": {"fiveHour": 93}, "error": False})
    )
    monkeypatch.setattr(guard_mod, "HUD_CACHE_PATH", cache_file)
    assert get_five_hour_pct() == 93.0


def test_get_five_hour_pct_missing_file(tmp_path, monkeypatch):
    cache_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr(guard_mod, "HUD_CACHE_PATH", cache_file)
    assert get_five_hour_pct() is None


def test_get_five_hour_pct_error_true(tmp_path, monkeypatch):
    cache_file = tmp_path / ".usage-cache.json"
    cache_file.write_text(
        json.dumps({"data": {"fiveHour": 93}, "error": True})
    )
    monkeypatch.setattr(guard_mod, "HUD_CACHE_PATH", cache_file)
    assert get_five_hour_pct() is None


def test_compute_target_state_fail_closed_on_none():
    target = _compute_target_state(None, 0.0, None)
    assert target in (GuardState.CRIT, GuardState.STOP)


def test_compute_target_state_five_hour_wins():
    target = _compute_target_state(5.0, 0.0, 93.0)
    assert target == GuardState.STOP


def test_tokens_remaining_none():
    assert tokens_remaining(None) == 0


def test_get_sonnet_weekly_pct_stale_data():
    from core.ops.thunderbird_rate_limit_guard import get_sonnet_weekly_pct
    # Ground-truth DB row is from 2026-05-20, which is > 24 hours old relative to 2026-07-31
    assert get_sonnet_weekly_pct() is None


def test_compute_target_state_sonnet_none_does_not_force_crit():
    # Healthy 14% weekly and 14% 5-hour, with stale/None Sonnet reading
    target = _compute_target_state(14.0, None, 14.0)
    assert target == GuardState.NORMAL

