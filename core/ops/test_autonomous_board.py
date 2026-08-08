#!/usr/bin/env python3
"""test_autonomous_board.py — regression per CC guard (RT-MISSION 2026-08-07).

CC guard: normalize-before-hash, and a regression that collapses the REAL
historical Regent-cookie duplicate P0s (MISSION-001/007/011/033/037/046...)
into a single DDK. The event journal is the truth (P2); dedup keys are
computed from normalized fields (P1) so near-duplicates collide.
Owner: Wing (RT-MISSION). Build routed to A-staff (Sterling A7) via War Room.
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.ops.autonomous_board import (  # noqa: E402
    append_event, ddk_from_mission, ddkey, project_board,
)

TITLES = [
    "Resolve Regent cookie expiration — restore session access",
    "Close Regent cookie expiration P0 — restore session access",
    "Close Regent cookie P0 — restore authenticated agent-portal session",
    "Close Regent P0 — restore session cookie access",
    "Close Regent P0 — restore cookie/session access (consolidate with 001)",
    "Wire self-healing architecture to cover Regent credential failure",
    "Verify self-healing architecture covers Regent credential failure",
]

# The cookie/session-RESTORE cluster is the real duplicate-spam (5 variants).
# The self-healing-architecture cluster is a distinct workstream.
SESSION_CLUSTER = TITLES[:5]
SELFHEAL_CLUSTER = TITLES[5:]


def test_regent_dupes_collapse():
    """All cookie/session-restore variants MUST share ONE dedup key."""
    keys = {
        ddk_from_mission({"title": t, "source": "wing-tasking"})
        for t in SESSION_CLUSTER
    }
    assert len(keys) == 1, f"expected 1 dedup key for cookie cluster, got {keys}"
    # And the self-healing cluster is a separate concern (must NOT collide).
    sh = {
        ddk_from_mission({"title": t, "source": "wing-tasking"})
        for t in SELFHEAL_CLUSTER
    }
    assert len(sh) == 1, f"self-heal cluster should hold 1 distinct key, got {sh}"
    assert keys != sh, "cookie-restore and self-heal must not collide"
    print(f"PASS: cookie{len(SESSION_CLUSTER)} -> {keys}; selfheal{len(SELFHEAL_CLUSTER)} -> {sh}")


def test_normalize_before_hash():
    """Near-duplicate events differing only by instance detail -> same key."""
    a = ddkey("SESSION_EXPIRED", "REGENT", "ASPXAUTH")
    b = ddkey("session expired", "regent portal", "aspxauth 401 timeout")
    c = ddkey("SESSION_EXPIRED", "REGENT", "ASPXAUTH")
    assert a == b, f"raw-detail did not normalize: {a} != {b}"
    assert a == c
    print(f"PASS: ddkey normalization stable: {a}")


def test_journal_projection_resolves():
    """append OPEN then RESOLVED -> projection shows RESOLVED, single row."""
    tmp = pathlib.Path(tempfile.mkstemp(suffix=".jsonl")[1])
    try:
        append_event(tmp, {"event": "OPEN", "type": "FARE_CHANGE", "target": "LYONS", "code": ""})
        append_event(tmp, {"event": "RESOLVED", "type": "FARE_CHANGE", "target": "LYONS", "code": ""})
        proj = project_board(tmp)
        assert len(proj) == 1 and proj[0]["status"] == "RESOLVED", proj
        print("PASS: event->RESOLVED projection correct")
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    test_regent_dupes_collapse()
    test_normalize_before_hash()
    test_journal_projection_resolves()
    print("\nALL RT-MISSION regression tests passed.")