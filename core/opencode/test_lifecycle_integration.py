"""
Integration test — OpenCode Lifecycle Architecture.

Exercises 3 mock clients (fixtures/mock_clients.json) against
lifecycle_event_handler to verify:
  1. Phase transitions fire the correct events (incl. multi-phase skips).
  2. Task queueing happens — one oc-lane brain_bridge task per active
     touchpoint, via an injected FakeBridge (never touches the shared
     production brain_bridge_board.json).
  3. Phase state persists across calls, keyed by booking_id.

Run: python3 -m pytest core/opencode/test_lifecycle_integration.py -v
"""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import core.opencode.lifecycle_event_handler as leh  # noqa: E402

FIXTURES_PATH = REPO_ROOT / "core" / "opencode" / "fixtures" / "mock_clients.json"


class FakeBridge:
    """Records queued tasks in memory — stands in for
    core.hale_bus.brain_bridge.BrainBridge so tests never write to the
    shared production board."""

    def __init__(self):
        self.tasks = []

    def add(self, title, description="", lane="any", priority="P1", **kwargs):
        tid = f"fake-{len(self.tasks)}"
        self.tasks.append({
            "id": tid, "title": title, "description": description,
            "lane": lane, "priority": priority,
        })
        return tid


def _load_fixture(booking_id: str) -> dict:
    clients = json.loads(FIXTURES_PATH.read_text())
    raw = next(c for c in clients if c["booking_id"] == booking_id)
    return {
        **raw,
        "booking_date": date.fromisoformat(raw["booking_date"]),
        "fpd": date.fromisoformat(raw["fpd"]),
        "embark_date": date.fromisoformat(raw["embark_date"]),
        "disembark_date": date.fromisoformat(raw["disembark_date"]),
        "payment_date": date.fromisoformat(raw["payment_date"]) if raw.get("payment_date") else None,
    }


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Point the module's phase-state file at a scratch path per test so
    tests never touch (or leak state through) the shared production file."""
    scratch = tmp_path / "lifecycle_phase_state.json"
    monkeypatch.setattr(leh, "STATE_PATH", scratch)
    return scratch


def test_normal_scenario_phase1_to_phase2_transition(isolated_state):
    client = _load_fixture("MOCK-NORMAL-001")
    bridge = FakeBridge()

    e1 = leh.check_client(client, as_of=date(2025, 10, 1), bridge=bridge)
    assert e1 is not None
    assert e1["event_type"] == "phase_assigned"
    assert e1["new_phase"] == "PHASE_1"

    # Same phase, later date within the same window -> no event.
    e_same = leh.check_client(client, as_of=date(2025, 10, 15), bridge=bridge)
    assert e_same is None

    e2 = leh.check_client(client, as_of=date(2026, 1, 1), bridge=bridge)
    assert e2 is not None
    assert e2["event_type"] == "phase_changed"
    assert e2["old_phase"] == "PHASE_1"
    assert e2["new_phase"] == "PHASE_2"
    assert e2["anchor_validation"]["pass"] is True
    assert e2["anchor_validation"]["warnings"] == []  # standard Regent T-120 gap, no drift


def test_early_embark_scenario_skips_phase2(isolated_state):
    """Last-minute Viking booking, full payment posted almost immediately —
    the client jumps straight from Craft to Polish, never dwelling in
    Execute, then rolls into Voyage days later."""
    client = _load_fixture("MOCK-EARLY-EMBARK-002")
    bridge = FakeBridge()

    e1 = leh.check_client(client, as_of=date(2026, 6, 5), bridge=bridge)
    assert e1["new_phase"] == "PHASE_1"

    e2 = leh.check_client(client, as_of=date(2026, 6, 20), bridge=bridge)
    assert e2["old_phase"] == "PHASE_1"
    assert e2["new_phase"] == "PHASE_3"
    assert e2["payment_status"] == "Paid"
    assert any("contract-term" in w for w in e2["anchor_validation"]["warnings"])

    e3 = leh.check_client(client, as_of=date(2026, 7, 10), bridge=bridge)
    assert e3["old_phase"] == "PHASE_3"
    assert e3["new_phase"] == "PHASE_4"


def test_late_fpd_scenario_flags_contract_term_and_transitions(isolated_state):
    """FPD only 9 days before embark on a nominally T-120 Regent contract —
    anchor_validation must flag the drift as a warning (not an error; the
    date order is still logically valid), and the phase jump past PHASE_2
    must still be detected correctly."""
    client = _load_fixture("MOCK-LATE-FPD-003")
    bridge = FakeBridge()

    e1 = leh.check_client(client, as_of=date(2025, 12, 1), bridge=bridge)
    assert e1["new_phase"] == "PHASE_1"

    e2 = leh.check_client(client, as_of=date(2026, 12, 9), bridge=bridge)
    assert e2["old_phase"] == "PHASE_1"
    assert e2["new_phase"] == "PHASE_3"
    assert e2["anchor_validation"]["pass"] is True
    assert any("contract-term" in w for w in e2["anchor_validation"]["warnings"])


def test_task_queueing_one_per_active_touchpoint(isolated_state):
    client = _load_fixture("MOCK-NORMAL-001")
    bridge = FakeBridge()

    leh.check_client(client, as_of=date(2025, 10, 1), bridge=bridge)
    tasks_before = len(bridge.tasks)

    event = leh.check_client(client, as_of=date(2026, 1, 1), bridge=bridge)
    assert len(bridge.tasks) == tasks_before + len(event["active_touchpoints"])
    assert all(t["lane"] == "oc" for t in bridge.tasks)


def test_state_persists_across_calls(isolated_state):
    client = _load_fixture("MOCK-NORMAL-001")
    leh.check_client(client, as_of=date(2025, 10, 1), bridge=FakeBridge())
    state = leh.load_phase_state()
    assert state["MOCK-NORMAL-001"]["phase_code"] == "PHASE_1"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
