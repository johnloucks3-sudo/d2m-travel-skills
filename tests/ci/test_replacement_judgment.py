import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.replacement import judge_replacement


def test_escalate_when_client_affecting_and_spend_gate():
    component = {"client_affecting": True, "wraps": [], "spend_gate": "fare-quoting"}
    j = judge_replacement(component, "3 consecutive failures")
    assert j["action"] == "ESCALATE_REPLACE"
    assert j["criticality"] == 1.0
    assert j["rebuild_cost"] == 0.7


def test_auto_replace_low_impact_internal_with_fallback():
    component = {"client_affecting": False, "wraps": [], "spend_gate": None,
                 "fallback": "static-report"}
    j = judge_replacement(component, "latency spike")
    assert j["impact"] < 0.30
    assert j["action"] == "AUTO_REPLACE"
    assert j["degraded_mode_exists"] == 1.0


def test_middle_band_escalates_v1_default():
    component = {"client_affecting": True, "wraps": [], "spend_gate": None,
                 "fallback": "manual-procedure"}
    j = judge_replacement(component, "sustained slowness")
    assert 0.30 <= j["impact"] <= 0.70
    assert j["action"] == "ESCALATE_REPLACE"
