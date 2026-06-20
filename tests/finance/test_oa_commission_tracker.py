import json
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.finance.oa_commission_tracker import rolling_received, tier_for, OATracker


def test_rolling_received_excludes_older_than_12_months():
    entries = [
        {"date": "2025-01-01", "d2m_received_usd": 5000.0},
        {"date": "2026-02-01", "d2m_received_usd": 3000.0},
        {"date": "2026-05-01", "d2m_received_usd": 2000.0},
    ]
    total = rolling_received(entries, as_of=date(2026, 6, 20))
    assert total == 5000.0


def test_tier_thresholds():
    assert tier_for(0.0) == 80
    assert tier_for(9999.99) == 80
    assert tier_for(10000.0) == 90
    assert tier_for(39999.99) == 90
    assert tier_for(40000.0) == 95


def test_tracker_reports_distance_to_next_tier(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "host": "Outside Agents, LLC",
        "thresholds": {"tier_90_usd": 10000, "tier_95_usd": 40000},
        "received": [{"date": "2026-06-01", "d2m_received_usd": 2500.0}],
    }))
    t = OATracker(ledger_path=ledger)
    status = t.status(as_of=date(2026, 6, 20))
    assert status["rolling_received_usd"] == 2500.0
    assert status["current_tier_pct"] == 80
    assert status["to_next_tier_usd"] == 7500.0
    assert status["crossed_90"] is False


def test_page_message_on_crossing(tmp_path):
    ledger = tmp_path / "l.json"
    ledger.write_text(json.dumps({
        "host": "Outside Agents, LLC",
        "thresholds": {"tier_90_usd": 10000, "tier_95_usd": 40000},
        "received": [{"date": "2026-06-01", "d2m_received_usd": 10500.0}],
    }))
    t = OATracker(ledger_path=ledger)
    msg = t.page_if_crossed(as_of=date(2026, 6, 20))
    assert msg is not None
    assert "90%" in msg and "$10,500" in msg


def test_no_page_below_threshold(tmp_path):
    ledger = tmp_path / "l2.json"
    ledger.write_text(json.dumps({"host": "OA", "thresholds": {}, "received": []}))
    t = OATracker(ledger_path=ledger)
    assert t.page_if_crossed(as_of=date(2026, 6, 20)) is None
