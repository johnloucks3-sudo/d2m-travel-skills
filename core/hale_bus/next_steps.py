#!/usr/bin/env python3
"""
next_steps.py — Shared "grab the reins" backlog for the Wing.

A single file-locked JSON queue that ANY brain writes to — Hale-CC (Claude Code),
Hale-OC (OpenCode), and the Commander (dictation). Purpose: no work goes undone
because someone hesitated to propose or claim it. You see an item, you claim it,
you do it, you mark it done. The Commander can dictate items straight in.

Store: core/hale_bus/next_steps.json  (shared, all instances read/write)
NO PII/secrets in the text (same rule as the bus — all instances read it).

CLI:
  next_steps.py add "text" [--by cc|oc|commander] [--priority P0|P1|P2] [--tag x]
  next_steps.py list [--status open|claimed|done] [--by ...]
  next_steps.py claim <id> --by cc|oc            # grab the reins
  next_steps.py done  <id> [--note "what happened"]
  next_steps.py drop  <id> [--note "why"]        # remove without doing
  next_steps.py dictate "text ..."               # Commander shortcut (== add --by commander --priority P1)

Both agents should `list --status open` at session start and after finishing a thread,
and CLAIM anything in their lane rather than leaving it.

Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-03
"""
import argparse
import fcntl
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(__file__).resolve().parent / "next_steps.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sid() -> str:
    return "ns-" + hex(int(time.time() * 1000))[-7:]


def _load_locked():
    STORE.touch(exist_ok=True)
    fd = open(STORE, "r+")
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        raw = fd.read().strip()
        data = json.loads(raw) if raw else {"items": [], "meta": {"created": _now()}}
    except Exception:
        data = {"items": [], "meta": {"created": _now()}}
    return fd, data


def _save(fd, data):
    fd.seek(0)
    fd.truncate()
    json.dump(data, fd, indent=2, ensure_ascii=False)
    fd.flush()
    os.fsync(fd.fileno())
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()


def add(text, by="cc", priority="P1", tag=None):
    fd, d = _load_locked()
    item = {"id": _sid(), "text": text, "by": by, "priority": priority,
            "tag": tag, "status": "open", "claimed_by": None,
            "added_at": _now(), "done_at": None, "note": None}
    d["items"].append(item)
    _save(fd, d)
    return item["id"]


def claim(item_id, by):
    fd, d = _load_locked()
    ok = False
    for it in d["items"]:
        if it["id"] == item_id and it["status"] == "open":
            it["status"] = "claimed"
            it["claimed_by"] = by
            it["claimed_at"] = _now()
            ok = True
    _save(fd, d)
    return ok


def close(item_id, status="done", note=None):
    fd, d = _load_locked()
    ok = False
    for it in d["items"]:
        if it["id"] == item_id and it["status"] != "done":
            it["status"] = status
            it["done_at"] = _now()
            if note:
                it["note"] = note
            ok = True
    _save(fd, d)
    return ok


def listing(status=None, by=None):
    _, d = _load_locked()
    fcntl.flock(_.fileno(), fcntl.LOCK_UN)
    _.close()
    out = d["items"]
    if status:
        out = [i for i in out if i["status"] == status]
    if by:
        out = [i for i in out if i["by"] == by]
    return out


def _fmt(i):
    tag = f" #{i['tag']}" if i.get("tag") else ""
    who = f" ({i['claimed_by']})" if i.get("claimed_by") else ""
    return f"[{i['status']:<7}] {i['id']} {i['priority']} by:{i['by']}{who}{tag}\n    {i['text']}"


def main():
    ap = argparse.ArgumentParser(description="Shared next-steps backlog (grab the reins)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("text"); a.add_argument("--by", default="cc"); a.add_argument("--priority", default="P1"); a.add_argument("--tag", default=None)
    di = sub.add_parser("dictate"); di.add_argument("text")
    li = sub.add_parser("list"); li.add_argument("--status", default=None); li.add_argument("--by", default=None)
    cl = sub.add_parser("claim"); cl.add_argument("id"); cl.add_argument("--by", required=True)
    dn = sub.add_parser("done"); dn.add_argument("id"); dn.add_argument("--note", default=None)
    dr = sub.add_parser("drop"); dr.add_argument("id"); dr.add_argument("--note", default=None)
    args = ap.parse_args()

    if args.cmd == "add":
        print("added:", add(args.text, args.by, args.priority, args.tag))
    elif args.cmd == "dictate":
        print("added (Commander):", add(args.text, "commander", "P1"))
    elif args.cmd == "list":
        items = listing(args.status, args.by)
        opens = [i for i in items if i["status"] == "open"]
        claimed = [i for i in items if i["status"] == "claimed"]
        print(f"NEXT STEPS — {len(opens)} open · {len(claimed)} claimed · {len(items)} total\n")
        for i in items:
            print(_fmt(i))
    elif args.cmd == "claim":
        print("claimed" if claim(args.id, args.by) else "not open / not found")
    elif args.cmd == "done":
        print("done" if close(args.id, "done", args.note) else "not found")
    elif args.cmd == "drop":
        print("dropped" if close(args.id, "dropped", args.note) else "not found")


if __name__ == "__main__":
    main()
