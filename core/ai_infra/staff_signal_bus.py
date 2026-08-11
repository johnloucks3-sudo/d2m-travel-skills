#!/usr/bin/env python3
"""
STAFF SIGNAL BUS — agent-to-agent collaboration substrate
=========================================================
Dreams2Memories Travel · Thunderbird Wing · built 2026-06-21

Commander: "If we had effective staff collab tools, all staff could be giving
inputs to each other — Dani/Dembe telling Whetstone what's stale, telling ELON
what they've encountered that's good for us. I refuse to accept our
agent-to-agent comm is sufficient. CODE this."

This IS the code. Any persona/agent posts a SIGNAL; the bus routes it to the
owner whose job it is to act, and produces a digest the brief and the next
tech-vanguard sweep consume. No prose, no opinion — a queryable SQLite bus with
a CLI any headless agent (Claude -p, OpenCode, a workflow agent) can call.

Signal types → default owner:
  STALE        → whetstone   (something is rotting / outdated / painful — trim it)
  CAPABILITY   → elon        (encountered a tool/pattern we should acquire)
  INTEL        → dembe       (market/competitor/reading signal worth plowing back)
  DISSENT      → hale        (a staff objection to surface to the Commander)
  ASK          → hale        (one persona needs another's input)

CLI:
  post   --from dembe --type CAPABILITY --subject "X" --detail "..." [--priority high] [--route elon]
  pull   --route elon [--status open]
  ack    --id 12 --by elon
  done   --id 12 --note "adopted, MISSION-330"
  digest [--json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("/home/john/Thunderbird/state/staff_signals.db")

# Two directions every staff member can use:
#   SUGGEST → CAPABILITY (acquire), INTEL (market/reading), STALE (trim)
#   OPINE   → OPINE (weigh in / observe), DISSENT (object), ASK (need input)
TYPE_ROUTE = {
    "STALE": "whetstone",      # suggest: something's rotting → trim it
    "CAPABILITY": "elon",      # suggest: encountered a tool we should acquire
    "INTEL": "dembe",          # suggest: market/competitor/reading signal
    "OPINE": "hale",           # opine: an observation / point of view to surface
    "DISSENT": "hale",         # opine: a logged objection for the Commander
    "ASK": "hale",             # opine: one persona needs another's input
}
VALID_TYPES = set(TYPE_ROUTE)

# The full wing cast wired into the bus — every seat can suggest AND opine.
# Internal personas are live now. Extended/gift participants are added ONLY on
# Commander confirmation (never assume a name — see Ron/Lindy note 2026-06-21).
STAFF_ROSTER = {
    # internal wing
    "hale": "COS / ops / synthesis / routing",
    "dani": "client products / client voice",
    "dembe": "research / market intel / reading",
    "sterling": "process / metrics / code / gates",
    "harlan": "financial verification",
    "elon": "tech adoption / acquire",
    "whetstone": "CI currency / trim",
    "reyes": "experience layer",
    "luna": "narrative / brand copy",
    "naia": "brand / voice / template",
    "grace": "gift-world / public-good persona",
}

# EXTENDED PERSONAS — the "lenses" (Personas/D2M_Extended_Personas.md, v1.0 2026-03-20).
# Commander 2026-06-21: re-activate + wire BOTH WAYS — they suggest AND opine.
# Client-sim lenses opine on client products (→ dani); intel/advisory/benchmark
# lenses suggest ecosystem tools + competitor capability (→ elon / dembe).
# default_route = where their OPINE/ASK lands; SUGGEST types still route by type.
EXTENDED_ROSTER = {
    # client-simulation lenses → opinions sharpen client products
    "rondo":    {"role": "CLT-01 tech-phobic elder (M,80) — digital-friction lens", "default_route": "dani"},
    "lindy":    {"role": "CLT-02 tech-phobic elder (F,80) — top referral / doc-design lens", "default_route": "dani"},
    "kyle":     {"role": "CLT-03 tech-eager early adopter — portal/UX speed lens", "default_route": "dani"},
    "nick":     {"role": "CLT-04 founder — zero-friction audit lens", "default_route": "sterling"},
    "erik":     {"role": "CLT-05 gold-standard engineer — completeness/accuracy lens", "default_route": "dani"},
    "melissa":  {"role": "CLT-06 experiential teacher — emotional-arc lens", "default_route": "dani"},
    # community intelligence + external advisory + benchmark → extend reach outward
    "signal":   {"role": "INT-01 (Jamie Cross) — Anthropic/AI ecosystem monitor", "default_route": "elon"},
    "anthro_a": {"role": "ADV-01 (Dr. Aria Patel) — Anthropic consultant lens", "default_route": "elon"},
    "anthro_p": {"role": "ADV-02 (Marcus Webb) — Anthropic product lens", "default_route": "elon"},
    "benchmark":{"role": "BNK-01 (Diane Kaufman) — peer-agency benchmarking", "default_route": "dembe"},
}


def _resolve_route(from_persona: str, type: str, route_to: str | None) -> str:
    if route_to:
        return route_to.lower()
    fp = from_persona.lower()
    # an extended lens OPINING/ASKING lands at its owner; SUGGEST routes by type
    if type in ("OPINE", "ASK") and fp in EXTENDED_ROSTER:
        return EXTENDED_ROSTER[fp]["default_route"]
    return TYPE_ROUTE[type]
VALID_PRIORITY = {"high", "med", "low"}
VALID_STATUS = {"open", "acked", "done"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT NOT NULL,
            from_persona  TEXT NOT NULL,
            type          TEXT NOT NULL,
            route_to      TEXT NOT NULL,
            subject       TEXT NOT NULL,
            detail        TEXT,
            priority      TEXT NOT NULL DEFAULT 'med',
            status        TEXT NOT NULL DEFAULT 'open',
            acked_by      TEXT,
            actioned_note TEXT,
            updated       TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_route_status ON signals(route_to, status)")
    return c


def post(from_persona: str, type: str, subject: str, detail: str = "",
         priority: str = "med", route_to: str | None = None) -> int:
    """A persona drops a signal. Returns the signal id. Routes by type unless overridden."""
    type = (type or "").upper()
    if type not in VALID_TYPES:
        raise ValueError(f"type must be one of {sorted(VALID_TYPES)}, got {type!r}")
    priority = priority if priority in VALID_PRIORITY else "med"
    route_to = _resolve_route(from_persona, type, route_to)
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO signals (ts, from_persona, type, route_to, subject, detail, priority, status, updated)"
            " VALUES (?,?,?,?,?,?,?, 'open', ?)",
            (_now(), from_persona.lower(), type, route_to, subject, detail, priority, _now()),
        )
        sid = int(cur.lastrowid or 0)
    if priority == "high":
        _telegram_page(sid, from_persona, type, route_to, subject)
    return sid


def _telegram_page(sid: int, from_persona: str, type: str, route_to: str, subject: str) -> None:
    """Page the Commander on high-priority signals. Best-effort — never crashes a post."""
    try:
        from core.communication.thunderbird_brief_telegram import send_telegram
        send_telegram(
            f"🔴 STAFF SIGNAL #{sid} [{type}] → {route_to}\n"
            f"From: {from_persona}\n{subject}"
        )
    except Exception as _e:
        import logging
        logging.getLogger("staff_signal_bus").warning("Telegram page failed: %s", _e)


def pull(route_to: str, status: str = "open") -> list[dict]:
    """An owner pulls their queue (default: open signals routed to them)."""
    with _conn() as c:
        q = "SELECT * FROM signals WHERE route_to=?"
        args = [route_to.lower()]
        if status != "all":
            q += " AND status=?"
            args.append(status)
        q += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'med' THEN 1 ELSE 2 END, id"
        return [dict(r) for r in c.execute(q, args)]


def set_status(signal_id: int, status: str, by: str | None = None, note: str | None = None) -> bool:
    if status not in VALID_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_STATUS)}")
    with _conn() as c:
        cur = c.execute(
            "UPDATE signals SET status=?, acked_by=COALESCE(?, acked_by),"
            " actioned_note=COALESCE(?, actioned_note), updated=? WHERE id=?",
            (status, by, note, _now(), signal_id),
        )
        return cur.rowcount > 0


def ack(signal_id: int, by: str) -> bool:
    return set_status(signal_id, "acked", by=by)


def done(signal_id: int, note: str = "") -> bool:
    return set_status(signal_id, "done", note=note)


def digest(open_only: bool = True) -> dict:
    """Bucket open signals by owner — what the brief and the next sweep consume."""
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM signals" + (" WHERE status!='done'" if open_only else "") +
            " ORDER BY route_to, CASE priority WHEN 'high' THEN 0 WHEN 'med' THEN 1 ELSE 2 END, id"
        )]
    by_route: dict[str, list[dict]] = {}
    for r in rows:
        by_route.setdefault(r["route_to"], []).append(r)
    return {
        "generated": _now(),
        "open_total": len(rows),
        "by_route": by_route,
        "counts": {k: len(v) for k, v in by_route.items()},
    }


def render_digest() -> str:
    d = digest()
    if not d["open_total"]:
        return "STAFF SIGNAL BUS — all queues clear."
    out = [f"## STAFF SIGNAL BUS — {d['open_total']} open"]
    for route, sigs in d["by_route"].items():
        out.append(f"\n### → {route.upper()} ({len(sigs)})")
        for s in sigs:
            flag = "🔴" if s["priority"] == "high" else "•"
            out.append(f"{flag} [{s['type']}] {s['subject']}  _(from {s['from_persona']}, #{s['id']})_")
            if s.get("detail"):
                out.append(f"    {s['detail'][:160]}")
    return "\n".join(out)


# ── CLI ────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Thunderbird staff signal bus")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("post")
    p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--detail", default="")
    p.add_argument("--priority", default="med")
    p.add_argument("--route", default=None)

    g = sub.add_parser("pull")
    g.add_argument("--route", required=True)
    g.add_argument("--status", default="open")
    g.add_argument("--json", action="store_true")

    a = sub.add_parser("ack"); a.add_argument("--id", type=int, required=True); a.add_argument("--by", required=True)
    dn = sub.add_parser("done"); dn.add_argument("--id", type=int, required=True); dn.add_argument("--note", default="")
    dg = sub.add_parser("digest"); dg.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "post":
        sid = post(args.frm, args.type, args.subject, args.detail, args.priority, args.route)
        with _conn() as c:
            row = c.execute("SELECT route_to FROM signals WHERE id=?", (sid,)).fetchone()
            route = row["route_to"] if row else "?"
        print(f"posted #{sid} → {route}")
    elif args.cmd == "pull":
        rows = pull(args.route, args.status)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{len(rows)} signal(s) → {args.route}:")
            for s in rows:
                print(f"  #{s['id']} [{s['priority']}/{s['type']}] {s['subject']} (from {s['from_persona']})")
    elif args.cmd == "ack":
        print("acked" if ack(args.id, args.by) else "not found")
    elif args.cmd == "done":
        print("done" if done(args.id, args.note) else "not found")
    elif args.cmd == "digest":
        print(json.dumps(digest(), indent=2) if args.json else render_digest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
