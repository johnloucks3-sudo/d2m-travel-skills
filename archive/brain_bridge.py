#!/usr/bin/env python3
"""
brain_bridge.py — HALE-OS master-plan board (claim-based, dependency-aware, two-lane).

The thinnest layer that makes Hale a durable super-manager over CC + OC.
One JSON ledger both planes read: CC seats claim via Agent Teams; OC seats claim
via the opencode-worker loop. Atomic file lock prevents double-claims. depends_on
edges enforce ordering. lane tags (cc|oc) route work; CC always owns merge.

Data model stolen from task-master-ai (depends_on + status + next-task pull).
Runtime NOT adopted (too heavy) — this is ~120 lines on the lock we already have.

Non-gated infrastructure. Does not touch the 6 protected email/relay files.
Authored 2026-07-02 (ELON/Fable) toward 100% Integration 2030.

CLI:
    python3 brain_bridge.py new  <plan_id>
    python3 brain_bridge.py add  <plan_id> <lane cc|oc> "<task>" [--dep T1 --dep T2] [--model sonnet]
    python3 brain_bridge.py claim <plan_id> <lane> <worker_id>      # atomic pull-next
    python3 brain_bridge.py done <plan_id> <task_id> [--result "..."]
    python3 brain_bridge.py list <plan_id>
"""
import json, os, sys, time, fcntl, argparse, datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parent / "OpsCenter" / "brain_bridge_board.json"
STATES = ("pending", "claimed", "in-progress", "completed", "failed")


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Board:
    """File-locked JSON board. The lock is the whole concurrency guarantee."""

    def __init__(self, path=BOARD):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"plans": {}}, indent=2))

    def _txn(self, mutate):
        """Open, exclusive-lock, read, mutate, write, unlock. Returns mutate()'s value."""
        with open(self.path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)          # blocks until we own the write
            try:
                data = json.load(f)
                result = mutate(data)
                f.seek(0); f.truncate()
                json.dump(data, f, indent=2)
                f.flush(); os.fsync(f.fileno())     # durable across restart
                return result
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    # ---- operations -------------------------------------------------------
    def new_plan(self, plan_id):
        def m(d):
            d["plans"].setdefault(plan_id, {"created": _now(), "tasks": {}})
            return plan_id
        return self._txn(m)

    def add(self, plan_id, lane, task, deps=None, model=None):
        assert lane in ("cc", "oc")
        def m(d):
            p = d["plans"].setdefault(plan_id, {"created": _now(), "tasks": {}})
            tid = f"T{len(p['tasks']) + 1}"
            p["tasks"][tid] = {
                "id": tid, "lane": lane, "task": task,
                "depends_on": deps or [], "model": model,
                "status": "pending", "worker": None,
                "claimed_at": None, "result": None, "updated": _now(),
            }
            return tid
        return self._txn(m)

    def claim(self, plan_id, lane, worker_id):
        """Atomic pull-next: first pending task in this lane whose deps are all done."""
        def m(d):
            p = d["plans"].get(plan_id)
            if not p:
                return None
            done = {t["id"] for t in p["tasks"].values() if t["status"] == "completed"}
            for t in p["tasks"].values():
                if t["lane"] != lane or t["status"] != "pending":
                    continue
                if all(dep in done for dep in t["depends_on"]):
                    t.update(status="claimed", worker=worker_id,
                             claimed_at=_now(), updated=_now())
                    return t
            return None                              # nothing claimable right now
        return self._txn(m)

    def done(self, plan_id, task_id, result=None, status="completed"):
        assert status in STATES
        def m(d):
            t = d["plans"][plan_id]["tasks"][task_id]
            t.update(status=status, result=result, updated=_now())
            return t
        return self._txn(m)

    def snapshot(self, plan_id):
        with open(self.path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)["plans"].get(plan_id, {})
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


def _print_plan(plan_id, plan):
    if not plan:
        print(f"(no plan '{plan_id}')"); return
    print(f"PLAN {plan_id}  created {plan.get('created')}")
    for t in plan["tasks"].values():
        dep = f" deps={t['depends_on']}" if t["depends_on"] else ""
        wk = f" @{t['worker']}" if t["worker"] else ""
        print(f"  {t['id']} [{t['lane']}] {t['status']:11}{wk}{dep}  {t['task'][:60]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new").add_argument("plan_id")
    a = sub.add_parser("add")
    a.add_argument("plan_id"); a.add_argument("lane", choices=["cc", "oc"])
    a.add_argument("task"); a.add_argument("--dep", action="append", default=[])
    a.add_argument("--model")
    c = sub.add_parser("claim")
    c.add_argument("plan_id"); c.add_argument("lane", choices=["cc", "oc"])
    c.add_argument("worker_id")
    dn = sub.add_parser("done")
    dn.add_argument("plan_id"); dn.add_argument("task_id"); dn.add_argument("--result")
    sub.add_parser("list").add_argument("plan_id")

    args = ap.parse_args()
    b = Board()
    if args.cmd == "new":
        print("created", b.new_plan(args.plan_id))
    elif args.cmd == "add":
        print("added", b.add(args.plan_id, args.lane, args.task, args.dep, args.model))
    elif args.cmd == "claim":
        t = b.claim(args.plan_id, args.lane, args.worker_id)
        print(json.dumps(t) if t else "NONE-CLAIMABLE")
    elif args.cmd == "done":
        print("done", b.done(args.plan_id, args.task_id, args.result)["id"])
    elif args.cmd == "list":
        _print_plan(args.plan_id, b.snapshot(args.plan_id))


if __name__ == "__main__":
    main()
