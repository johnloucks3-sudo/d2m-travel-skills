import sys
sys.path.insert(0, "/home/john/Thunderbird")
from datetime import datetime, timezone, timedelta
from core.ci.replacement import needs_replacement

NOW = datetime(2026, 6, 20, tzinfo=timezone.utc)
POLICY = {"consecutive_failures_max": 3, "rolling_window_days": 7,
          "failures_in_window_max": 5, "latency_breach_factor": 3.0,
          "latency_breach_runs_of_last_5": 3, "consecutive_timeouts_max": 2}


def _run(days_ago, ok, ms, timed_out=False):
    return {"ts": (NOW - timedelta(days=days_ago)).isoformat(), "ok": ok,
            "duration_ms": ms, "timed_out": timed_out}


def test_no_replace_when_healthy():
    hist = [_run(i, True, 1000) for i in range(5)]
    assert needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)[0] is False


def test_replace_on_3_consecutive_failures():
    hist = [_run(3, True, 1000), _run(2, False, 0), _run(1, False, 0), _run(0, False, 0)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "consecutive" in reason


def test_replace_on_rolling_failure_rate():
    # 5 failures within 7 days but NOT 3 consecutive (ends on a pass) — isolates the rolling trigger.
    hist = [_run(6, False, 0), _run(5, False, 0), _run(4, True, 1), _run(3, False, 0),
            _run(2, False, 0), _run(1, False, 0), _run(0, True, 1)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "in 7 days" in reason


def test_replace_on_latency_spike():
    hist = [_run(0, True, 50000)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "spike" in reason


def test_replace_on_sustained_latency():
    hist = [_run(4, True, 20000), _run(3, True, 1000), _run(2, True, 20000),
            _run(1, True, 1000), _run(0, True, 20000)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "sustained" in reason
