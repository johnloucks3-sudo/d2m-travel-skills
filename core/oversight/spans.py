"""
core/oversight/spans.py — the Wing's delegation span ledger.

WHY THIS EXISTS
---------------
`core/staffing/delegation_outcomes.py` records a flat 13-field row per outcome.
That shape cannot express six things the Commander explicitly asked to see:

  * parent/child relationships (so "all phases of a delegation" is unanswerable)
  * elapsed time and budget (no timers)
  * tokens and cost (no cost-per-completed-task)
  * the pre-work spec (no "artifacts of planned delegations")
  * live todo state (no todo lists / progress)
  * heartbeat/lease (so LOST is undetectable — see below)

It also cannot be joined. The 2026-07-29 audit's gap #6: mission_board.json,
delegation_outcomes.jsonl, silver_ledger.jsonl (3,114 rows) and routing_log.md
all share an ID scheme and nothing stitches them. JSONL cannot index-join at
that size; SQLite can, and is already a competence in this repo.

THE FAILURE THIS IS BUILT AGAINST
---------------------------------
The audit found SIX oversight functions with zero call sites, including
`verify_and_record()` — the cross-engine claim checker CLAUDE.md declares
mandatory. Worse, `outstanding()` and `reconcile_oc.reconcile_due()` — the
lost-task detectors — are fed ONLY by `dispatch_to_oc()`, which nothing calls.
Zero dispatches means zero possible detections, forever, while the daily digest
prints green. The detector was never broken; its intake pipe was never connected.

Design rule, therefore: **this module must never depend on a future session
remembering to call it.** Writers are hooks and timers (see hooks/ and the
reaper timer), not voluntary calls. Anything requiring recall is presumed dead
on arrival — that is MAST code WING-2 and we measure ourselves on it.

CONTRACT
--------
Writes never raise. A telemetry failure must not mask or block the real work,
same contract as delegation_outcomes.record_outcome() and
hale_orchestrator.close_plan(). Reads may raise.

Field naming follows the OpenTelemetry GenAI semantic conventions (`gen_ai.*`)
where one applies, so a future export to Langfuse/Phoenix is a mapping and not
a migration. NOTE: those conventions are still Development-status upstream and
the spec page has moved; we adopt the NAMES, deliberately not a dependency.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from core.oversight import mast

ROOT = Path("/home/john/Thunderbird")
DB_PATH = ROOT / "OpsCenter" / "wing_spans.db"
# Append-only mirror. The two live brief engines read JSONL; keeping this write
# means nothing that works today breaks while the DB becomes the source of truth.
JSONL_MIRROR = ROOT / "OpsCenter" / "wing_spans.jsonl"

SEATS = ("CC", "OC", "AG", "SUBAGENT", "HUMAN")

# Lifecycle phases. Deliberately mirrors the existing SSS/mission 6-stage model
# rather than inventing a parallel vocabulary.
PHASES = ("spec", "dispatch", "work", "verify", "certify", "close")

STATUSES = (
    "RUNNING",
    "OK",             # completed and verified against ground truth
    "FAILED",         # completed, did not meet criteria
    "LOST",           # heartbeat went stale, no output — vanished
    "ABANDONED",      # exited cleanly, work incomplete, no failure declared
    "SILENT_SUCCESS", # work done, artifacts exist, never reported (WING-1)
    "BLOCKED",        # honestly blocked, escalated
)

TERMINAL_STATUSES = tuple(s for s in STATUSES if s != "RUNNING")
# Statuses that mean a human should hear about it.
FAILURE_STATUSES = ("FAILED", "LOST", "ABANDONED", "BLOCKED")

DEFAULT_LEASE_SECONDS = 1800  # 30 min; override per span via lease_seconds


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat()


def new_trace_id() -> str:
    return f"tr_{uuid.uuid4().hex[:16]}"


def new_span_id() -> str:
    return f"sp_{uuid.uuid4().hex[:12]}"


SCHEMA = """
CREATE TABLE IF NOT EXISTS spans (
    span_id            TEXT PRIMARY KEY,
    trace_id           TEXT NOT NULL,
    parent_span_id     TEXT,
    ticket_id          TEXT,            -- joins mission_board / SSS / silver_ledger
    seat               TEXT NOT NULL,
    agent_id           TEXT,            -- subagent id from SubagentStart hook
    agent_type         TEXT,
    model              TEXT,            -- gen_ai.request.model
    task_type          TEXT,
    phase              TEXT NOT NULL,
    status             TEXT NOT NULL,

    started_at         TEXT NOT NULL,
    ended_at           TEXT,
    elapsed_s          REAL,
    heartbeat_at       TEXT,            -- makes LOST detectable
    lease_expires_at   TEXT,

    input_tokens       INTEGER DEFAULT 0,   -- gen_ai.usage.input_tokens
    output_tokens      INTEGER DEFAULT 0,   -- gen_ai.usage.output_tokens
    cost_usd           REAL DEFAULT 0.0,

    spec_ref           TEXT,            -- pre-dispatch plan artifact
    transcript_ref     TEXT,            -- full agent<->agent messages
    artifact_refs      TEXT,            -- JSON list of real paths/commits/URLs
    todo               TEXT,            -- JSON list of {text,status}

    mast_code          TEXT,            -- FINAL code: rule- or human-assigned
    proposed_mast_code TEXT,            -- model may propose; never finalize
    verdict            TEXT,
    verified_by        TEXT,            -- must differ from `seat` to count
    ground_truth_ref   TEXT,            -- what was actually checked
    detail             TEXT,

    created_by         TEXT,            -- which hook/timer wrote this row
    meta               TEXT             -- JSON escape hatch
);
CREATE INDEX IF NOT EXISTS idx_spans_trace   ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_ticket  ON spans(ticket_id);
CREATE INDEX IF NOT EXISTS idx_spans_status  ON spans(status);
CREATE INDEX IF NOT EXISTS idx_spans_seat    ON spans(seat);
CREATE INDEX IF NOT EXISTS idx_spans_started ON spans(started_at);
CREATE INDEX IF NOT EXISTS idx_spans_parent  ON spans(parent_span_id);
CREATE INDEX IF NOT EXISTS idx_spans_live    ON spans(status, lease_expires_at);
"""


def _connect(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path or DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # WAL: concurrent readers (dashboard, brief engines) never block the
    # writer (hooks firing on every tool call).
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


@contextmanager
def _db(path: Optional[Path] = None):
    conn = _connect(path)
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Optional[Path] = None) -> Path:
    target = Path(path or DB_PATH)
    with _db(target):
        pass
    return target


def _mirror(row: dict, path: Optional[Path] = None) -> None:
    """Append-only JSONL mirror. Best-effort; never masks a real write."""
    target = Path(path or JSONL_MIRROR)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _jdump(v: Any) -> Optional[str]:
    if v is None:
        return None
    return json.dumps(v, ensure_ascii=False, default=str)


def _jload(v: Optional[str], default):
    if not v:
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


# ---------------------------------------------------------------- writers
# Every writer below swallows exceptions. Telemetry must never break work.

def open_span(
    *,
    seat: str,
    phase: str = "work",
    task_type: str = "",
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    ticket_id: str = "",
    agent_id: str = "",
    agent_type: str = "",
    model: str = "",
    spec_ref: str = "",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    todo: Optional[list] = None,
    created_by: str = "",
    meta: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Open a RUNNING span. Returns the row dict (with span_id/trace_id) even
    if persistence failed, so callers always have usable ids."""
    now = _now()
    row = {
        "span_id": new_span_id(),
        "trace_id": trace_id or new_trace_id(),
        "parent_span_id": parent_span_id,
        "ticket_id": ticket_id,
        "seat": seat,
        "agent_id": agent_id,
        "agent_type": agent_type,
        "model": model,
        "task_type": task_type,
        "phase": phase,
        "status": "RUNNING",
        "started_at": _iso(now),
        "ended_at": None,
        "elapsed_s": None,
        "heartbeat_at": _iso(now),
        "lease_expires_at": _iso(now + timedelta(seconds=lease_seconds)),
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "spec_ref": spec_ref,
        "transcript_ref": None,
        "artifact_refs": _jdump([]),
        "todo": _jdump(todo or []),
        "mast_code": None,
        "proposed_mast_code": None,
        "verdict": None,
        "verified_by": None,
        "ground_truth_ref": None,
        "detail": None,
        "created_by": created_by,
        "meta": _jdump(meta or {}),
    }
    try:
        with _db(db_path) as conn:
            cols = ",".join(row.keys())
            qs = ",".join("?" for _ in row)
            conn.execute(f"INSERT INTO spans ({cols}) VALUES ({qs})",
                         tuple(row.values()))
    except Exception:
        pass
    _mirror({"event": "open", **row})
    return row


def heartbeat(span_id: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS,
              todo: Optional[list] = None, db_path: Optional[Path] = None) -> bool:
    """Renew liveness. A worker that stops calling this becomes reapable —
    this single field is what makes LOST detectable at all."""
    now = _now()
    try:
        with _db(db_path) as conn:
            if todo is not None:
                conn.execute(
                    "UPDATE spans SET heartbeat_at=?, lease_expires_at=?, todo=? "
                    "WHERE span_id=? AND status='RUNNING'",
                    (_iso(now), _iso(now + timedelta(seconds=lease_seconds)),
                     _jdump(todo), span_id))
            else:
                conn.execute(
                    "UPDATE spans SET heartbeat_at=?, lease_expires_at=? "
                    "WHERE span_id=? AND status='RUNNING'",
                    (_iso(now), _iso(now + timedelta(seconds=lease_seconds)),
                     span_id))
        return True
    except Exception:
        return False


def close_span(
    span_id: str,
    *,
    status: str,
    verdict: str = "",
    verified_by: str = "",
    ground_truth_ref: str = "",
    mast_code: Optional[str] = None,
    proposed_mast_code: Optional[str] = None,
    artifact_refs: Optional[list] = None,
    transcript_ref: str = "",
    detail: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    todo: Optional[list] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Close a span to a terminal status.

    `verified_by` is only meaningful when it differs from the span's own seat —
    self-verification is recorded but never counts as verification. See
    `is_independently_verified()`; the reason is LLM self-preference bias, whose
    named mitigation is a judge from a different model family.

    `mast_code` must be a valid code (MAST or WING extension) or it is demoted
    to `proposed_mast_code`, keeping the finalized column trustworthy.
    """
    if mast_code and not mast.is_valid(mast_code):
        proposed_mast_code = proposed_mast_code or mast_code
        mast_code = None
    try:
        with _db(db_path) as conn:
            cur = conn.execute("SELECT * FROM spans WHERE span_id=?", (span_id,))
            existing = cur.fetchone()
            if existing is None:
                return None
            started = datetime.fromisoformat(existing["started_at"])
            now = _now()
            elapsed = (now - started).total_seconds()
            merged_artifacts = _jload(existing["artifact_refs"], [])
            if artifact_refs:
                merged_artifacts = list(dict.fromkeys(
                    [*merged_artifacts, *artifact_refs]))
            conn.execute(
                "UPDATE spans SET status=?, ended_at=?, elapsed_s=?, verdict=?, "
                "verified_by=?, ground_truth_ref=?, mast_code=?, "
                "proposed_mast_code=?, artifact_refs=?, transcript_ref=?, "
                "detail=?, input_tokens=?, output_tokens=?, cost_usd=?, "
                "todo=COALESCE(?, todo) WHERE span_id=?",
                (status, _iso(now), elapsed, verdict or None,
                 verified_by or None, ground_truth_ref or None, mast_code,
                 proposed_mast_code, _jdump(merged_artifacts),
                 transcript_ref or existing["transcript_ref"], detail or None,
                 input_tokens or existing["input_tokens"],
                 output_tokens or existing["output_tokens"],
                 cost_usd or existing["cost_usd"],
                 _jdump(todo) if todo is not None else None,
                 span_id))
            cur = conn.execute("SELECT * FROM spans WHERE span_id=?", (span_id,))
            out = dict(cur.fetchone())
    except Exception:
        return None
    _mirror({"event": "close", **out})
    return out


def add_artifact(span_id: str, ref: str, db_path: Optional[Path] = None) -> bool:
    try:
        with _db(db_path) as conn:
            cur = conn.execute("SELECT artifact_refs FROM spans WHERE span_id=?",
                               (span_id,))
            r = cur.fetchone()
            if r is None:
                return False
            refs = _jload(r["artifact_refs"], [])
            if ref not in refs:
                refs.append(ref)
            conn.execute("UPDATE spans SET artifact_refs=? WHERE span_id=?",
                         (_jdump(refs), span_id))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- readers

def get_span(span_id: str, db_path: Optional[Path] = None) -> Optional[dict]:
    with _db(db_path) as conn:
        r = conn.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
        return dict(r) if r else None


def trace(trace_id: str, db_path: Optional[Path] = None) -> list[dict]:
    """Every span in a delegation lineage, ordered. This is the query that
    answers 'show me all phases of this delegation' — audit gap #6."""
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spans WHERE trace_id=? ORDER BY started_at",
            (trace_id,)).fetchall()
        return [dict(r) for r in rows]


def by_ticket(ticket_id: str, db_path: Optional[Path] = None) -> list[dict]:
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spans WHERE ticket_id=? ORDER BY started_at",
            (ticket_id,)).fetchall()
        return [dict(r) for r in rows]


def live(db_path: Optional[Path] = None) -> list[dict]:
    """Everything currently RUNNING — the live progress view."""
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spans WHERE status='RUNNING' ORDER BY started_at"
        ).fetchall()
        return [dict(r) for r in rows]


def stale(db_path: Optional[Path] = None, now: Optional[datetime] = None) -> list[dict]:
    """RUNNING spans whose lease has expired — candidates for the reaper."""
    cutoff = _iso(now or _now())
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spans WHERE status='RUNNING' AND lease_expires_at IS NOT NULL "
            "AND lease_expires_at < ? ORDER BY lease_expires_at", (cutoff,)).fetchall()
        return [dict(r) for r in rows]


def is_independently_verified(span: dict) -> bool:
    """Verification only counts when someone OTHER than the worker did it.

    Self-grading is the named LLM self-preference bias; the published
    mitigation is a judge from a different model family. A span verified by
    its own seat is recorded, but must never be counted as verified.
    """
    vb = (span.get("verified_by") or "").strip()
    return bool(vb) and vb != (span.get("seat") or "").strip()


def unverified_closures(since_days: int = 7, db_path: Optional[Path] = None) -> list[dict]:
    """Spans that closed OK with no independent verification. These are the
    'green on silence' rows — the denominator the digest must show."""
    cutoff = _iso(_now() - timedelta(days=since_days))
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spans WHERE status='OK' AND started_at>=?", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows if not is_independently_verified(dict(r))]
