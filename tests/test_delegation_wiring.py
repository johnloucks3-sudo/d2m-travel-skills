"""Regression test for core/relay/delegation_wiring.py + its mission_board_sync wiring.

REGRESSION (2026-07-16): the cross-Hale task-delegation library
(core/relay/task_delegation.py) shipped as a Phase-0 building block that
NOTHING invoked -- the same "detection without execution" failure the design
exists to kill. Block 1 wires it live: assigning a mission to a real seat
(CC/OC/AG) must (a) validate the routing rationale, (b) actually write the
`assigned` lifecycle stage onto the C2 Fabric bus (hale_bus_state.json), and
(c) refuse to certify a ticket whose certifier == assignee (§3.5 anti-theater).

Hermeticity: c2_fabric_write and c2_fabric_read each import their OWN
HALE_BUS_PATH; both are redirected to a tmp file so "write event -> read it
back" is a real round trip against tmp state, never production
hale_bus_state.json. relay_handoff/relay_ack are stubbed so no test POSTs to
Telegram.
"""
import sys
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

import core.hale_bus.hale_bus_write as bus_write  # noqa: E402
import core.hale_bus.c2_fabric_read as fabric_read  # noqa: E402
import core.relay.delegation_wiring as wiring  # noqa: E402
from core.relay.task_delegation import route_task, CC, OC, AG  # noqa: E402


def _isolate_bus(tmp_path, monkeypatch):
    """Redirect every writer/reader of the bus to a tmp file. hale_bus_write
    owns HALE_BUS_PATH/LOCK_PATH; c2_fabric_read re-imports HALE_BUS_PATH into
    its own module namespace, so BOTH must be patched or the read side falls
    back to the real file."""
    bus_file = tmp_path / "hale_bus_state.json"
    lock_file = tmp_path / "hale_bus.lock"
    monkeypatch.setattr(bus_write, "HALE_BUS_PATH", bus_file)
    monkeypatch.setattr(bus_write, "LOCK_PATH", lock_file)
    # c2_fabric_write imports these names at call-time from hale_bus_write, but
    # it also bound HALE_BUS_PATH/LOCK_PATH at import — patch the write module too.
    import core.hale_bus.c2_fabric_write as fabric_write
    monkeypatch.setattr(fabric_write, "HALE_BUS_PATH", bus_file)
    monkeypatch.setattr(fabric_write, "LOCK_PATH", lock_file)
    monkeypatch.setattr(fabric_read, "HALE_BUS_PATH", bus_file)
    return bus_file


def _stub_relay(monkeypatch):
    sent = []
    monkeypatch.setattr(wiring, "relay_handoff",
                        lambda *a, **k: sent.append(("handoff", a, k)) or 1)
    monkeypatch.setattr(wiring, "relay_ack",
                        lambda *a, **k: sent.append(("ack", a, k)) or 2)
    return sent


# ── Routing decision correctness (Phase-0 contract still holds) ──────────────
def test_route_task_decisions():
    assert route_task("x", needs_judgment=True).seat == CC
    assert route_task("x", needs_large_context=True).seat == AG
    assert route_task("x", is_vision=True).seat == AG
    assert route_task("factbook_refresh").seat == OC
    assert route_task("summarize", claude_optional=True).seat == AG
    assert route_task("draft_something").seat == CC


# ── Bus event is actually written, then read back ────────────────────────────
def test_assigned_stage_written_and_readable(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)

    mission = {
        "id": "MISSION-TEST-1",
        "title": "refresh the factbook",
        "assigned_to": OC,
        "acceptance_criteria": "factbook.json regenerated with 12 rows",
        "certified_by": CC,
    }
    wiring.delegate_mission(mission, from_seat=CC, task_type="factbook_refresh")

    # Read it back from the (tmp) bus via the read-path module.
    events = fabric_read.get_channel_activity(channel="console")
    assigned = [e for e in events if e["ref"] == "MISSION-TEST-1"
                and e["event_type"] == "delegation_assigned"]
    assert len(assigned) == 1, f"expected one assigned event, got {events}"

    # route_task agrees with the chosen seat → rationale is marked validated.
    assert "routing validated" in mission["delegation_rationale"]


def test_full_lifecycle_events_land_on_bus(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)

    mid = "MISSION-TEST-2"
    mission = {"id": mid, "title": "pull data", "assigned_to": OC,
               "acceptance_criteria": "rows present", "certified_by": CC}
    wiring.delegate_mission(mission, task_type="data_pull")
    wiring.ack_receipt(OC, mid)
    wiring.submit_for_review(mid, OC, "output/data.json@commit abc123")
    wiring.certify_mission(mid, OC, CC, "output/data.json@commit abc123", "rows present")

    stages = [e["event_type"] for e in fabric_read.get_channel_activity(channel="console")
              if e["ref"] == mid]
    assert stages == [
        "delegation_assigned", "delegation_in_progress",
        "delegation_pending_review", "delegation_done",
    ], stages


# ── Cross-seat certifier enforcement (§3.5.3 anti-theater) ───────────────────
def test_self_certification_rejected_at_assignment(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    mission = {"id": "M", "title": "t", "assigned_to": OC,
               "acceptance_criteria": "crit", "certified_by": OC}
    try:
        wiring.delegate_mission(mission, task_type="data_pull")
        assert False, "expected DelegationError on certifier == assignee"
    except wiring.DelegationError as e:
        assert "self-certification" in str(e)


def test_self_certification_rejected_at_certify(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    try:
        wiring.certify_mission("M", OC, OC, "artifact.json", "crit")
        assert False, "expected DelegationError on self-certify"
    except wiring.DelegationError as e:
        assert "self-certification" in str(e)


def test_certify_requires_artifact(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    try:
        wiring.certify_mission("M", OC, CC, "   ", "crit")
        assert False, "expected DelegationError on missing artifact"
    except wiring.DelegationError as e:
        assert "verification_artifact" in str(e)


def test_delegation_requires_acceptance_criteria(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    mission = {"id": "M", "title": "t", "assigned_to": OC, "certified_by": CC}
    try:
        wiring.delegate_mission(mission, task_type="data_pull")
        assert False, "expected DelegationError on missing acceptance_criteria"
    except wiring.DelegationError as e:
        assert "acceptance_criteria" in str(e)


# ── The REAL wiring: add_mission fires delegation on a seat assignment ────────
def test_add_mission_seat_assignment_fires_delegation(tmp_path, monkeypatch):
    bus_file = _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)

    import OpsCenter.mission_board_sync as mbs
    board = {"missions": []}
    msg, mid = mbs.add_mission(
        board, "scrape and store the port pages",
        priority="P2", assigned_to=OC,
        acceptance_criteria="4 port pages saved under intel/",
        certified_by=CC, task_type="scrape_store",
    )
    assert mid is not None
    created = board["missions"][0]
    assert created["assigned_to"] == OC
    assert created["status"] == "assigned"
    assert created["certified_by"] == CC
    assert created["delegation_rationale"]
    # bus round-trip: the assigned stage actually landed
    assigned = [e for e in fabric_read.get_channel_activity(channel="console")
                if e["ref"] == mid and e["event_type"] == "delegation_assigned"]
    assert len(assigned) == 1


def test_add_mission_persona_owner_does_not_delegate(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)

    import OpsCenter.mission_board_sync as mbs
    board = {"missions": []}
    msg, mid = mbs.add_mission(board, "some hale task", assigned_to="Hale")
    created = board["missions"][0]
    assert created["status"] == "in_progress"
    assert "acceptance_criteria" not in created
    # nothing mirrored onto the bus for a persona-name assignment
    assert fabric_read.get_channel_activity(channel="console") == []


def test_add_mission_seat_without_criteria_rejected(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    import OpsCenter.mission_board_sync as mbs
    board = {"missions": []}
    try:
        mbs.add_mission(board, "seat task no crit", assigned_to=AG)
        assert False, "expected DelegationError: seat assignment needs acceptance_criteria"
    except wiring.DelegationError as e:
        assert "acceptance_criteria" in str(e)


# ── The real human/programmatic caller: the `delegate` CLI verb ──────────────
def test_cmd_delegate_fires_delegation_and_mirrors_bus(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    import OpsCenter.mission_board_sync as mbs
    board = {"missions": []}
    msg = mbs.cmd_delegate(
        board, "OC :: scrape the four Regent port pages :: 4 pages saved under intel/ :: P2 :: scrape_store")
    assert "Delegated" in msg
    created = board["missions"][0]
    assert created["assigned_to"] == OC and created["status"] == "assigned"
    assert created["certified_by"] == "CC"
    assigned = [e for e in fabric_read.get_channel_activity(channel="console")
                if e["ref"] == created["id"] and e["event_type"] == "delegation_assigned"]
    assert len(assigned) == 1


def test_cmd_delegate_rejects_self_certifier(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    import OpsCenter.mission_board_sync as mbs
    board = {"missions": []}
    # certifier == seat → §3.5 self-certification rejection surfaced as a clean message
    msg = mbs.cmd_delegate(board, "OC :: t :: crit :: P2 :: scrape_store :: OC")
    assert "rejected" in msg.lower() and "self-certification" in msg
    assert board["missions"] == []


def test_cmd_delegate_bad_seat(tmp_path, monkeypatch):
    _isolate_bus(tmp_path, monkeypatch)
    _stub_relay(monkeypatch)
    import OpsCenter.mission_board_sync as mbs
    assert "Unknown seat" in mbs.cmd_delegate({"missions": []}, "ZZ :: t :: crit")
