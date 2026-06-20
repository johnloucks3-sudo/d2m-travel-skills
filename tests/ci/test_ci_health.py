import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.ci_health import run_probe, sweep


def test_run_probe_ok_on_true():
    ok, detail, ms, timed_out = run_probe("true")
    assert ok is True
    assert timed_out is False


def test_run_probe_fail_on_false():
    ok, detail, ms, timed_out = run_probe("false")
    assert ok is False


def test_sweep_returns_status_per_skill(monkeypatch):
    import core.ci.ci_health as h
    fake = {"replacement_policy": {"consecutive_failures_max": 3, "rolling_window_days": 7,
            "failures_in_window_max": 5, "latency_breach_factor": 3.0,
            "latency_breach_runs_of_last_5": 3, "consecutive_timeouts_max": 2},
            "skills": [
                {"id": "a", "name": "A", "ci_tool": "t", "health_probe": "true",
                 "currency_window_hours": 24, "reeval_cadence_days": 30, "fallback": "f",
                 "keeper": "whetstone", "latency_sla_ms": 15000, "active_workaround": None,
                 "last_verified": None, "last_reeval": "2026-06-20"},
            ]}
    monkeypatch.setattr(h, "load_registry", lambda *a, **k: fake)
    results = sweep(update_verified=False)
    assert results[0]["id"] == "a"
    assert results[0]["status"] in ("RAZOR_SHARP", "DULL", "RED", "REPLACE")
    assert "probe_ok" in results[0]
