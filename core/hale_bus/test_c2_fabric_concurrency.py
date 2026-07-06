#!/usr/bin/env python3
"""
UNIFIED C2 FABRIC — Phase 1 concurrency test.

Spawns real OS processes (not threads — fcntl exclusion is process-level)
that write concurrently to a SCRATCH bus file (never the production
hale_bus_state.json), mixing the new c2_fabric_write path with the legacy
append_channel_activity path, since both hit the same file in production.

Pass criteria: every one of the N*workers unique markers survives in the
final file with no lost updates ("0 conflicts" = no writer's update was
silently overwritten by another's read-modify-write). Valid JSON alone is
not sufficient — a lost update produces valid JSON.

Usage: python3 core/hale_bus/test_c2_fabric_concurrency.py
"""

import json
import multiprocessing
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

WRITES_PER_WORKER = 25


def _new_writer_worker(bus_path: str, worker_id: str, refs: list):
    os.environ["HALE_BUS_STATE_PATH"] = bus_path
    from core.hale_bus.c2_fabric_write import record_channel_event
    for ref in refs:
        record_channel_event("console", "concurrency_test", f"{worker_id}:{ref}", ref=ref)


def _legacy_writer_worker(bus_path: str, worker_id: str, refs: list):
    os.environ["HALE_BUS_STATE_PATH"] = bus_path
    from core.hale_bus.hale_bus_write import append_channel_activity
    for ref in refs:
        append_channel_activity("telegram", "concurrency_test_legacy", f"{worker_id}:{ref}", ref=ref)


def run_test() -> bool:
    tmp_dir = tempfile.mkdtemp(prefix="c2_fabric_concurrency_")
    bus_path = str(Path(tmp_dir) / "hale_bus_state_test.json")
    Path(bus_path).write_text(json.dumps({"bus_version": "1.0", "hale_instances": {}}))

    expected_refs = {}
    jobs = []
    worker_specs = [
        ("new_a", _new_writer_worker),
        ("new_b", _new_writer_worker),
        ("legacy_c", _legacy_writer_worker),
        ("legacy_d", _legacy_writer_worker),
    ]
    ctx = multiprocessing.get_context("fork")
    for worker_id, fn in worker_specs:
        refs = [f"{worker_id}-{uuid.uuid4().hex[:8]}" for _ in range(WRITES_PER_WORKER)]
        expected_refs[worker_id] = set(refs)
        p = ctx.Process(target=fn, args=(bus_path, worker_id, refs))
        jobs.append(p)

    for p in jobs:
        p.start()
    for p in jobs:
        p.join(timeout=60)

    all_expected = set()
    for refs in expected_refs.values():
        all_expected |= refs

    final_state = json.loads(Path(bus_path).read_text())
    found_refs = {e["ref"] for e in final_state.get("channel_activity", []) if e.get("ref")}

    missing = all_expected - found_refs
    exit_codes = [p.exitcode for p in jobs]

    print(f"Bus scratch file: {bus_path}")
    print(f"Workers exit codes: {exit_codes}")
    print(f"Expected markers: {len(all_expected)} | Found: {len(found_refs & all_expected)} | Missing: {len(missing)}")
    if missing:
        print(f"LOST UPDATES (conflict): {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")

    ok = len(missing) == 0 and all(c == 0 for c in exit_codes)
    print(f"\n{'PASS' if ok else 'FAIL'} — write_conflict_rate observed: "
          f"{0.0 if ok else len(missing) / len(all_expected):.4f}")

    metrics = final_state.get("c2_metrics", {})
    print(f"c2_metrics after test: {json.dumps(metrics)}")

    return ok


if __name__ == "__main__":
    sys.exit(0 if run_test() else 1)
