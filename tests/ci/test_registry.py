import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.registry import load_registry, razor_sharp_status


def _entry(**kw):
    base = {"id": "x", "currency_window_hours": 24, "reeval_cadence_days": 30,
            "last_verified": None, "last_reeval": "2026-06-20"}
    base.update(kw)
    return base


def test_load_registry_returns_skills():
    reg = load_registry(Path("/home/john/Thunderbird/config/ci_registry.json"))
    ids = {s["id"] for s in reg["skills"]}
    assert {"portal-access", "web-fetch", "headless-dispatch", "credential-keepalive", "tech-adoption"} <= ids


def test_red_when_probe_failed():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    assert razor_sharp_status(_entry(), probe_ok=False, now=now) == "RED"


def test_dull_when_currency_stale():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    stale = (now - timedelta(hours=48)).isoformat()
    assert razor_sharp_status(_entry(last_verified=stale, currency_window_hours=24), probe_ok=True, now=now) == "DULL"


def test_razor_sharp_when_fresh_and_green():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    fresh = (now - timedelta(hours=1)).isoformat()
    e = _entry(last_verified=fresh, last_reeval="2026-06-19", currency_window_hours=24, reeval_cadence_days=30)
    assert razor_sharp_status(e, probe_ok=True, now=now) == "RAZOR_SHARP"
