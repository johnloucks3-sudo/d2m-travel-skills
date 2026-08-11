import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.replacement import judge_replacement

LOG_PATH = Path("/home/john/Thunderbird/intel/failure_graph_events.jsonl")


def _line_count() -> int:
    if not LOG_PATH.exists():
        return 0
    return len(LOG_PATH.read_text().splitlines())


def test_judge_replacement_appends_graph_event():
    existed_before = LOG_PATH.exists()
    before = _line_count()

    component = {"id": "fare-quoting", "client_affecting": True, "wraps": [],
                 "spend_gate": "fare-quoting"}
    judge_replacement(component, "3 consecutive failures")

    assert _line_count() == before + 1
    last = json.loads(LOG_PATH.read_text().splitlines()[-1])
    assert last["component"] == "fare-quoting"
    assert last["reason"] == "3 consecutive failures"
    assert last["action"] == "ESCALATE_REPLACE"
    assert "impact" in last
    assert "timestamp" in last

    if not existed_before:
        LOG_PATH.unlink()
