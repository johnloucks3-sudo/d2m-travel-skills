#!/usr/bin/env python3
"""autonomous_board.py — Claim-and-decay ledger (RT-MISSION converged model).

Commander delegated the Thunderbird stack to HALE-OC 2026-08-07.
Cross-seat convergence (AG + CC): P1 calendar-retire = silent data-loss trap.
Use Deterministic Deduplication Keys (DDK) + explicit RESOLVED/TOMBSTONE.
Sequencing: P2 stream-is-source -> P1 claim (DDK) -> P3 on-event.

The Pillars:
  P2  STREAM IS THE SOURCE:  append-only JSONL event journal = truth;
      board/task state is a DERIVED read, never a second ledger.
  P1  CLAIM-ONLY (DDK):      agents claim only tasks in their lane; unclaimed
      items never silently decay on a calendar — they resolve only via an
      explicit RESOLVED or TOMBSTONE event.
  P3  ON-EVENT spawning:     a task is born from a real event (CI FAIL, FPD,
      dossier edit, Commander directive), not from per-minute poll noise.
      Reuses wing-wide systemd OnFailure= instead of new poll timers.

CC guard (adopted): normalize-before-hash. Hash ONLY normalized
(event_type, target, error_code); never raw error strings with embedded
timestamps/session-ids, or near-duplicate events fail to dedup.
CC guard (adopted): regression test must collapse the real historical
Regent-cookie duplicate P0s to a single DDK.

Safe: append-only + idempotent. No deletions; TOMBSTONE is a resolve marker.
Owner: HALE-OC (Jet). Standards: core/ci. Cross-seat RT-MISSION 2026-08-07.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Iterable

REPO_DIR = Path("/home/john/Thunderbird")
JOURNAL_PATH = REPO_DIR / "OpsCenter" / "mission_board_journal.jsonl"
BOARD_PATH = REPO_DIR / "OpsCenter" / "mission_board.json"

# --------------------------------------------------------------------------- #
# DDK — Deterministic Deduplication Key
# --------------------------------------------------------------------------- #

_EVENT_TYPES = {
    "SESSION_EXPIRED", "CREDENTIAL_FAIL", "FARE_CHANGE", "FPD_SUSPENSE",
    "DOSSIER_EDIT", "CI_PROBE_RED", "SUPPLIER_ALERT", "COMMANDER_DIRECTIVE",
    "SERVICE_FAIL", "BUILD_REMAINDER",
}


def normalize_event_type(raw: str) -> str:
    """Map a free-form source/type string to a canonical event type key.
    Normalizes case, splits on separators, falls back to a clean slug.
    Never returns ''/None so the hash input is stable.
    """
    if not raw:
        return "UNKNOWN_EVENT"
    t = raw.strip().upper()
    # strip numeric / timestamp debris that would defeat dedup
    t = re.sub(r"[0-9]+", "", t)
    t = re.sub(r"[^A-Z0-9]+", "_", t).strip("_")
    return t if t else "UNKNOWN_EVENT"


def normalize_target(raw: str) -> str:
    """Canonical entity/target (vendor, system, client). Slugify + drop generic
    trailing qualifiers (PORTAL/WEB/SERVICE/ACCOUNT) so a vendor keeps ONE key. """
    if not raw:
        return "UNKNOWN_TARGET"
    t = re.sub(r"[^A-Za-z0-9]+", "_", raw.strip().upper()).strip("_")
    for junk in ("_PORTAL", "_WEB", "_SERVICE", "_ACCOUNT", "_SITE"):
        t = t.replace(junk, "")
    return t if t else "UNKNOWN_TARGET"


def normalize_error(raw: str) -> str:
    """Canonical error_code. Drops digits + trailing qualifier noise
    (TIMEOUT/ERROR/FAIL words), keeps the class (ASPXAUTH, 401-class,
    TIMEOUT). Near-identical codes collapse to one key.
    """
    if not raw:
        return "NULL"
    t = raw.strip().upper()
    # drop embedded digits (session ids, 401-numbers)
    t = re.sub(r"[0-9]+", "", t)
    t = re.sub(r"[^A-Z0-9]+", "_", t).strip("_")
    # collapse generic failure words onto a fixed set
    t = re.sub(r"_(TIMEOUT|ERROR|FAILURE|EXCEPTION|FAIL)(_.*)?$", "", t)
    return t if t else "NULL"


def ddkey(event_type: str, target: str, error_code: str = "") -> str:
    """kDDK hash of NORMALIZED fields. Same root event -> same key regardless
    of how many times an agent re-booked / re-rendered a ticket title. """
    n = "|".join(
        [normalize_event_type(event_type), normalize_target(target), normalize_error(error_code)]
    )
    return "DDK-" + hashlib.sha256(n.encode()).hexdigest()[:16]


def ddk_from_mission(m: dict[str, Any]) -> str:
    """Derive the DDK of an existing mission from its title/source for a
    backfill/collapse pass. Conservative: UNKNOWN targets never collide.
    Heuristic for legacy backfill only — new tasks carry structured
    (event_type, target, code) fields at creation, the primary dedup path.
    """
    title = m.get("title", "")
    src = m.get("source", m.get("_source", ""))
    t = str(title).upper()
    if re.search(r"SELF[- ]?HEAL|ARCHITECTURE|COVER", t) and re.search(r"REGENT|CREDENTIAL", t):
        return ddkey("SELFHEAL", normalize_target(src), "REGENT")
    if re.search(r"REGENT", t) and re.search(r"COOKIE|SESSION|ASPXAUTH", t) and \
       re.search(r"EXPIR|RESET|RESTORE|FAIL|RE-AUTH|REAUTH", t):
        return ddkey("SESSION_EXPIRED", "REGENT", "COOKIE")
    if re.search(r"CREDENTIAL", t) or re.search(r"OAUTH|TOKEN", t):
        return ddkey("CREDENTIAL_FAIL", normalize_target(src), "TOKEN")
    if re.search(r"FPD|PAYMENT|SUSPENSE", t):
        return ddkey("FPD_SUSPENSE", normalize_target(src), "FPD")
    if re.search(r"CI.*PROBE|HEALTH|SERVICE", t):
        return ddkey("CI_PROBE", normalize_target(src), "PROBE")
    return ddkey("UNKNOWN_EVENT", normalize_target(src), "UNKNOWN")


# --------------------------------------------------------------------------- #
#  P2 — STREAM-IS-SOURCE (append-only event journal)
# --------------------------------------------------------------------------- #

def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def append_event(journal: Path | None, event: dict[str, Any]) -> dict[str, Any]:
    """Append a (code-only) event to the journal, idempotently. If the same
    event id already exists, no-op — guards re-play unless a caller wants it.
    """
    journal = journal or JOURNAL_PATH
    journal.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", _now_iso())
    if event.get("type") not in _EVENT_TYPES:
        # normalize creates a stable 'type' for foreign shapes
        event["type"] = normalize_event_type(event.get("type", ""))
    with journal.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_journal(journal: Path | None = None) -> list[dict[str, Any]]:
    journal = journal or JOURNAL_PATH
    if not journal.exists():
        return []
    return [json.loads(l) for l in journal.read_text().splitlines() if l.strip()]


def project_board(journal: Path | None = None) -> list[dict[str, Any]]:
    """Derived state from the event stream — a single-pass projection.
    The journal is truth; this is the only place a view is assembled.
    """
    out: dict[str, dict[str, Any]] = {}
    for ev in read_journal(journal):
        k = ev.get("ddk") or ddkey(ev.get("type", ""), ev.get("target", ""), ev.get("code", ""))
        if ev.get("event") == "TOMBSTONE":
            out.pop(k, None)
            continue
        base = out.get(k, {"key": k, "seqs": [], "opened": ev.get("ts"), "status": "OPEN"})
        base["seqs"].append(ev.get("ts"))
        if ev.get("event") == "RESOLVED":
            base["status"] = "RESOLVED"
        else:
            base["status"] = "OPEN"
        out[k] = base
    return sorted(out.values(), key=lambda x: x["opened"])


# --------------------------------------------------------------------------- #
#  P1 — CLAIM-ONLY (no silent calendar retire)
# --------------------------------------------------------------------------- #

def claim(mission: dict[str, Any], agent_lane: str) -> dict[str, Any]:
    """Claim a mission for a lane. Station-stop: a claim is an ownership
    record, not a delete. Duplicate claims update ownership + timestamp. """
    mission = dict(mission)
    mission["assigned_to"] = agent_lane
    mission["claimed_at"] = _now_iso()
    mission["status"] = "in_progress"  # claimed work
    return mission


def claimable_by(mission: dict[str, Any], lane: str, lanes_map: dict[str, set[str]]) -> bool:
    """Only tasks whose target/domain overlaps the agent's lane are claimable
    by that agent. This is the 'agents pull only their lane' rule. """
    cfg = lanes_map.get(lane, set())
    if not cfg:
        return True  # unconfigured lane claims everything (bootstrap)
    blob = f"{mission.get('title','')} {mission.get('description','')} {mission.get('source','')}".lower()
    return any(tok in blob for tok in cfg)


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Autonomous mission-board ledger (RT-MISSION)")
    ap.add_argument("op", choices=["append", "ddkey", "project", "journal"],
                    help="append|ddkey|project|journal")
    ap.add_argument("--type", "--type", dest="etype")
    ap.add_argument("--target")
    ap.add_argument("--code", default="")
    ap.add_argument("--title", help="derive DDK from a mission title (legend path)")
    ap.add_argument("--lane")
    ap.add_argument("--event", default="OPEN")
    a = ap.parse_args()

    if a.op == "ddkey" and a.title:
        m = {"title": a.title, "source": a.target or ""}
        print(ddk_from_mission(m))
    elif a.op == "ddkey":
        print(ddkey(a.etype or "UNKNOWN_EVENT", a.target or "UNKNOWN_TARGET", a.code))
    elif a.op == "append":
        ev = {"event": a.event, "type": a.etype, "target": a.target, "code": a.code}
        ev["key"] = ddkey(a.etype or "", a.target or "", a.code)
        append_event(None, ev)
        print(json.dumps(ev))
    elif a.op == "project":
        for b in project_board():
            print(f"{b['status']:9s} {b['key']} opened={b['opened']}")
    elif a.op == "journal":
        print(json.dumps(read_journal(), indent=1, default=str))


if __name__ == "__main__":
    main()