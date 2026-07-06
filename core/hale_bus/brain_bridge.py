#!/usr/bin/env python3
"""
BRAIN BRIDGE — HALE-OS Shared Task Claim Board
Thunderbird Wing · Dreams2Memories Travel, LLC

Atomic file-locked task board shared by Claude Code (CONDOR) and OpenCode (WIND).
Each seat claims one task at a time. depends_on blocks until predecessors complete.

Usage:
    bb = BrainBridge()
    bb.add("task-1", "Do X", lane="cc")
    bb.add("task-2", "Do Y", lane="oc", depends_on=["task-1"])
    task = bb.claim(lane="cc", agent="sterling")   # atomic — exactly one winner
    bb.complete("task-1", result="X done")
    tasks = bb.list_tasks(status="pending")

CLI:
    python3 core/hale_bus/brain_bridge.py list
    python3 core/hale_bus/brain_bridge.py add "title" --lane cc --depends task-1
    python3 core/hale_bus/brain_bridge.py claim --lane cc --agent hale
    python3 core/hale_bus/brain_bridge.py complete <id> --result "done"
    python3 core/hale_bus/brain_bridge.py status <id>
    python3 core/hale_bus/brain_bridge.py plan <json-file>   # load a split plan
"""

import fcntl
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# BRAIN_BRIDGE_BOARD_PATH override exists so tests/smoke-runs can point at a
# scratch file instead of the shared production board (mirrors the
# HALE_BUS_STATE_PATH pattern in core/hale_bus/hale_bus_write.py).
BRIDGE_PATH = Path(os.environ.get("BRAIN_BRIDGE_BOARD_PATH", str(Path(__file__).parent / "brain_bridge_board.json")))
LOCK_PATH   = BRIDGE_PATH.with_suffix(".lock")

VALID_LANES   = {"cc", "oc", "any"}
VALID_STATUSES = {"pending", "claimed", "complete", "blocked", "failed"}


# ── Qdrant semantic layer (lazy import) ────────────────────────────────────────

def _qdrant_embed_task(task: dict) -> None:
    """Best-effort embed a brain_bridge task into Qdrant. Silent on failure."""
    try:
        import sys as _sys
        _root = str(__file__).split('core/')[0]
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from core.memory.qdrant_memory import QdrantMemorySystem
        mem = QdrantMemorySystem()
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, prefix='bb_task_') as f:
            f.write(f"# Brain Bridge Task: {task.get('title','')}\n\n")
            f.write(f"task_id: {task.get('id','')}\n")
            f.write(f"lane: {task.get('lane','')}\n")
            f.write(f"priority: {task.get('priority','')}\n")
            f.write(f"status: {task.get('status','')}\n\n")
            f.write(task.get('description', ''))
            tmp = f.name
        try:
            mem.embed_new_memory(tmp)
        finally:
            os.unlink(tmp)
    except Exception as _e:
        import logging
        logging.getLogger("brain_bridge").debug("Qdrant embed skipped: %s", _e)


# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id() -> str:
    return "bb-" + uuid.uuid4().hex[:8]


# ── lock / persistence ─────────────────────────────────────────────────────────

def _acquire(blocking: bool = True) -> object:
    """Return open lock fd; raises BlockingIOError if non-blocking and contested."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = open(LOCK_PATH, "w")
    flag = fcntl.LOCK_EX if blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(fd, flag)
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def _release(fd) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def _load() -> dict:
    if not BRIDGE_PATH.exists():
        return {"tasks": {}, "meta": {"created": _now(), "version": "1.0"}}
    with open(BRIDGE_PATH) as f:
        return json.load(f)


def _save(board: dict, fd) -> None:
    with open(BRIDGE_PATH, "w") as f:
        json.dump(board, f, indent=2)
    _release(fd)


# ── public API ─────────────────────────────────────────────────────────────────

class BrainBridge:
    """Atomic shared task board for CC/OC Agent Teams."""

    # ── write ops (always lock) ────────────────────────────────────────────────

    def add(
        self,
        title: str,
        description: str = "",
        lane: str = "any",
        depends_on: Optional[list] = None,
        priority: str = "P1",
        task_id: Optional[str] = None,
    ) -> str:
        """Add a task. Returns task id."""
        assert lane in VALID_LANES, f"lane must be one of {VALID_LANES}"
        tid = task_id or _short_id()
        fd = _acquire()
        board = _load()
        board["tasks"][tid] = {
            "id": tid,
            "title": title,
            "description": description,
            "lane": lane,
            "priority": priority,
            "depends_on": depends_on or [],
            "status": "pending",
            "claimed_by": None,
            "claimed_at": None,
            "completed_at": None,
            "result": None,
            "created_at": _now(),
        }
        board["meta"]["last_updated"] = _now()
        task = board["tasks"][tid]
        _save(board, fd)
        _qdrant_embed_task(task)
        return tid

    def search_tasks(self, query: str, top_k: int = 10) -> list[dict]:
        """Semantic search across brain_bridge tasks via Qdrant. Degrades gracefully if Qdrant down."""
        try:
            import sys as _sys
            _root = str(__file__).split('core/')[0]
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from core.memory.qdrant_memory import QdrantMemorySystem
            mem = QdrantMemorySystem()
            raw = mem.search_memories(f"brain bridge task: {query}", top_k=top_k)
            # post-filter to brain_bridge task chunks. Payload keys are filename/filepath/content
            # (NOT 'source') — bb tasks embed as temp files named bb_task_*.md.
            def _hay(r):
                return (r.get('filename', '') + ' ' + r.get('filepath', '') + ' ' + r.get('content', '')).lower()
            results = [r for r in raw if 'bb_task_' in _hay(r) or 'brain bridge task' in _hay(r)]
            # On first successful search after a failure, backfill any missing tasks
            self._backfill_missing_tasks()
            return results
        except Exception as _e:
            import logging
            logging.getLogger("brain_bridge").debug("Qdrant search_tasks failed: %s", _e)
            return []

    def _backfill_missing_tasks(self) -> None:
        """
        Reconciliation: On first successful Qdrant connect after outage,
        re-embed any tasks not yet in the index.
        Silent on failure — best-effort operation.
        """
        try:
            import sys as _sys
            _root = str(__file__).split('core/')[0]
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from core.memory.qdrant_memory import QdrantMemorySystem

            # Load all tasks from board
            board = _load()
            all_tasks = list(board["tasks"].values())

            if not all_tasks:
                return

            mem = QdrantMemorySystem()

            # For each task, try a semantic search to see if it's in the index
            # If not found, re-embed it
            for task in all_tasks:
                try:
                    task_query = f"brain bridge task: {task.get('id')} {task.get('title')}"
                    found = mem.search_memories(task_query, top_k=3)
                    # Task IDs live in the embedded chunk CONTENT (payload has content/filename,
                    # NOT 'source'). Check content for the task_id.
                    task_id = task.get('id')
                    is_indexed = any(task_id in (r.get('content', '') or '') for r in found)

                    if not is_indexed:
                        # Re-embed this task
                        _qdrant_embed_task(task)
                except Exception:
                    # Silent on individual failures — keep trying other tasks
                    pass
        except Exception:
            # Silent on backfill failure — don't block Qdrant operations
            pass

    def claim(self, lane: str, agent: str) -> Optional[dict]:
        """
        Atomically claim the highest-priority pending task for this lane.
        Returns the task dict if claimed, None if nothing available.
        Skips tasks whose depends_on are not yet complete.
        """
        fd = _acquire()
        board = _load()
        tasks = board["tasks"]

        # collect completed ids for depends_on check
        done_ids = {tid for tid, t in tasks.items() if t["status"] == "complete"}

        # find claimable tasks: pending + lane match + dependencies met
        candidates = [
            t for t in tasks.values()
            if t["status"] == "pending"
            and (t["lane"] == lane or t["lane"] == "any")
            and all(dep in done_ids for dep in t["depends_on"])
        ]

        if not candidates:
            _release(fd)
            return None

        # pick highest priority (P0 > P1 > P2), then earliest created
        priority_rank = {"P0": 0, "P1": 1, "P2": 2}
        candidates.sort(key=lambda t: (priority_rank.get(t["priority"], 9), t["created_at"]))
        task = candidates[0]

        task["status"] = "claimed"
        task["claimed_by"] = agent
        task["claimed_at"] = _now()
        board["meta"]["last_updated"] = _now()
        _save(board, fd)
        return task

    def complete(self, task_id: str, result: str = "") -> bool:
        """Mark task complete. Returns True on success."""
        fd = _acquire()
        board = _load()
        if task_id not in board["tasks"]:
            _release(fd)
            return False
        t = board["tasks"][task_id]
        t["status"] = "complete"
        t["completed_at"] = _now()
        t["result"] = result
        board["meta"]["last_updated"] = _now()
        _save(board, fd)
        return True

    def fail(self, task_id: str, reason: str = "") -> bool:
        """Mark task failed (back to board for retry or inspection)."""
        fd = _acquire()
        board = _load()
        if task_id not in board["tasks"]:
            _release(fd)
            return False
        t = board["tasks"][task_id]
        t["status"] = "failed"
        t["result"] = reason
        t["claimed_by"] = None
        t["claimed_at"] = None
        board["meta"]["last_updated"] = _now()
        _save(board, fd)
        return True

    def load_plan(self, plan: list) -> list:
        """
        Bulk-load a split plan. Each item: {title, lane, description?, depends_on?, priority?, id?}
        Returns list of assigned task ids in order.
        """
        ids = []
        for item in plan:
            tid = self.add(
                title=item["title"],
                description=item.get("description", ""),
                lane=item.get("lane", "any"),
                depends_on=item.get("depends_on", []),
                priority=item.get("priority", "P1"),
                task_id=item.get("id"),
            )
            ids.append(tid)
        return ids

    def reset(self) -> None:
        """Wipe the board. Use for test teardown."""
        fd = _acquire()
        board = {"tasks": {}, "meta": {"created": _now(), "version": "1.0"}}
        _save(board, fd)

    # ── read ops (no lock needed) ──────────────────────────────────────────────

    def list_tasks(self, status: Optional[str] = None, lane: Optional[str] = None) -> list:
        board = _load()
        tasks = list(board["tasks"].values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if lane:
            tasks = [t for t in tasks if t["lane"] == lane or t["lane"] == "any"]
        tasks.sort(key=lambda t: t["created_at"])
        return tasks

    def get(self, task_id: str) -> Optional[dict]:
        board = _load()
        return board["tasks"].get(task_id)

    def status_summary(self) -> dict:
        tasks = self.list_tasks()
        summary = {s: 0 for s in VALID_STATUSES}
        for t in tasks:
            summary[t["status"]] = summary.get(t["status"], 0) + 1
        summary["total"] = len(tasks)
        return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli():
    import argparse

    bb = BrainBridge()
    p = argparse.ArgumentParser(description="Brain Bridge — HALE-OS claim board")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list").add_argument("--status", default=None)

    a = sub.add_parser("add")
    a.add_argument("title")
    a.add_argument("--desc", default="")
    a.add_argument("--lane", default="any", choices=["cc", "oc", "any"])
    a.add_argument("--depends", nargs="*", default=[])
    a.add_argument("--priority", default="P1")
    a.add_argument("--id", default=None, dest="task_id")

    c = sub.add_parser("claim")
    c.add_argument("--lane", required=True, choices=["cc", "oc", "any"])
    c.add_argument("--agent", required=True)

    d = sub.add_parser("complete")
    d.add_argument("task_id")
    d.add_argument("--result", default="")

    f = sub.add_parser("fail")
    f.add_argument("task_id")
    f.add_argument("--reason", default="")

    s = sub.add_parser("status")
    s.add_argument("task_id")

    sr = sub.add_parser("search")
    sr.add_argument("query")
    sr.add_argument("--top-k", type=int, default=10)

    pl = sub.add_parser("plan")
    pl.add_argument("json_file")

    sub.add_parser("summary")
    sub.add_parser("reset")

    args = p.parse_args()

    if args.cmd == "list":
        tasks = bb.list_tasks(status=args.status)
        if not tasks:
            print("Board empty.")
            return
        for t in tasks:
            deps = f" (needs: {','.join(t['depends_on'])})" if t["depends_on"] else ""
            print(f"[{t['status']:8}] {t['id']} | lane:{t['lane']} | {t['priority']} | {t['title']}{deps}")
            if t["claimed_by"]:
                print(f"           → claimed by {t['claimed_by']} at {t['claimed_at']}")
            if t["result"]:
                print(f"           → result: {t['result'][:80]}")

    elif args.cmd == "add":
        tid = bb.add(args.title, description=args.desc, lane=args.lane,
                     depends_on=args.depends, priority=args.priority, task_id=args.task_id)
        print(f"Added: {tid}")

    elif args.cmd == "claim":
        task = bb.claim(lane=args.lane, agent=args.agent)
        if task:
            print(f"Claimed: {task['id']} — {task['title']}")
            print(json.dumps(task, indent=2))
        else:
            print(f"Nothing to claim for lane={args.lane}")

    elif args.cmd == "complete":
        ok = bb.complete(args.task_id, result=args.result)
        print("Done." if ok else f"Task not found: {args.task_id}")

    elif args.cmd == "fail":
        ok = bb.fail(args.task_id, reason=args.reason)
        print("Marked failed." if ok else f"Task not found: {args.task_id}")

    elif args.cmd == "status":
        t = bb.get(args.task_id)
        print(json.dumps(t, indent=2) if t else f"Not found: {args.task_id}")

    elif args.cmd == "search":
        results = bb.search_tasks(args.query, top_k=args.top_k)
        if not results:
            print(f"No results for: {args.query}")
        else:
            print(f"Found {len(results)} results:")
            for r in results:
                source = r.get('source', 'unknown')
                score = r.get('score', 0)
                text = r.get('text', '')[:100]
                print(f"  {source} (score: {score:.3f}) — {text}...")

    elif args.cmd == "plan":
        plan = json.loads(Path(args.json_file).read_text())
        ids = bb.load_plan(plan)
        print(f"Loaded {len(ids)} tasks: {', '.join(ids)}")

    elif args.cmd == "summary":
        print(json.dumps(bb.status_summary(), indent=2))

    elif args.cmd == "reset":
        bb.reset()
        print("Board wiped.")

    else:
        p.print_help()


if __name__ == "__main__":
    _cli()
