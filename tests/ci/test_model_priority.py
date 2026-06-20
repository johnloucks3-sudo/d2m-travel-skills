import sys
sys.path.insert(0, "/home/john/Thunderbird")
from datetime import datetime, timezone, timedelta
from core.ci.model_priority import _is_active, _should_yield

NOW = datetime(2026, 6, 20, 16, 0, tzinfo=timezone.utc)


def _rec(owner_class, mins_left):
    return {"owner_class": owner_class,
            "until": (NOW + timedelta(minutes=mins_left)).isoformat()}


def test_no_record_not_active():
    assert _is_active(None, NOW) is False


def test_expired_not_active():
    assert _is_active(_rec("ci", -1), NOW) is False


def test_active_when_in_window():
    assert _is_active(_rec("ci", 2), NOW) is True


def test_routine_yields_to_active_ci():
    assert _should_yield(_rec("ci", 2), "routine", NOW) is True


def test_routine_does_not_yield_when_expired():
    assert _should_yield(_rec("ci", -1), "routine", NOW) is False


def test_ci_does_not_yield_to_ci_equal_rank():
    assert _should_yield(_rec("ci", 2), "ci", NOW) is False


def test_ci_yields_to_commander():
    assert _should_yield(_rec("commander", 2), "ci", NOW) is True


def test_commander_never_yields():
    assert _should_yield(_rec("ci", 2), "commander", NOW) is False
