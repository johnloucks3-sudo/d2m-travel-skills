import sys
sys.path.insert(0, "/home/john/Thunderbird")
from datetime import datetime, timezone, timedelta
from core.ci.self_observability import classify, should_dispatch

NOW = datetime(2026, 6, 20, 16, 0, tzinfo=timezone.utc)


def test_healthy_unit_no_breach():
    assert classify(nrestarts=0, errors=0) == []
    assert classify(nrestarts=4, errors=99) == []  # just under both thresholds


def test_restart_breach():
    r = classify(nrestarts=50027, errors=0)
    assert len(r) == 1 and "restarts" in r[0]


def test_error_breach():
    r = classify(nrestarts=0, errors=4628)
    assert len(r) == 1 and "errors" in r[0]


def test_both_breach():
    r = classify(nrestarts=10, errors=500)
    assert len(r) == 2


def test_should_dispatch_first_time():
    assert should_dispatch("x.service", state={}, now=NOW) is True


def test_should_not_dispatch_within_cooldown():
    state = {"x.service": {"last_dispatch": (NOW - timedelta(minutes=10)).isoformat()}}
    assert should_dispatch("x.service", state=state, now=NOW, cooldown_min=30) is False


def test_should_dispatch_after_cooldown():
    state = {"x.service": {"last_dispatch": (NOW - timedelta(minutes=45)).isoformat()}}
    assert should_dispatch("x.service", state=state, now=NOW, cooldown_min=30) is True


def test_band_restarts_uses_delta_not_cumulative():
    # cumulative NRestarts huge, but ZERO new restarts since last scan → clean
    from core.ci.self_observability import band_restarts
    tripped, _ = band_restarts({"nrestarts": 50027, "restarts_recent": 0})
    assert tripped is False
    tripped2, _ = band_restarts({"nrestarts": 50027, "restarts_recent": 6})
    assert tripped2 is True
