"""
core/oversight/reaper.py — lost / abandoned / silent-success detection.

THE BUG THIS REPLACES
---------------------
`delegation_outcomes.outstanding()` and `reconcile_oc.reconcile_due()` already
implement lost-ticket detection correctly. They have never fired and never can,
because their only intake is `dispatch_to_oc()`, which the 2026-07-29 audit
confirmed has zero call sites. Zero dispatches, zero possible detections — while
the daily digest prints green. The detector was fine; the pipe was dry.

So this reaper takes its input from state that exists whether or not anyone
remembered to call a function:
  1. the span ledger (written by hooks, not by voluntary calls)
  2. mission_board.json directly (198 missions today)
It is driven by a systemd timer, never by a session.

THE THREE CASES THE COMMANDER NAMED SEPARATELY
----------------------------------------------
He asked to see "lost taskings", "exits from tasking that are not accomplished",
and "successful taskings" as distinct things. They are distinguished here by
GROUND TRUTH ON DISK — did the promised artifact actually get written? — never
by what the agent said:

  LOST            heartbeat stale, no artifacts     → the work vanished
  ABANDONED       exited, no artifacts, no failure  → walked away silently
  SILENT_SUCCESS  artifacts exist, never reported   → work done, report dropped

That third case is not hypothetical. On 2026-07-29 at 10:08 a research agent
wrote a 23KB deliverable and went idle without reporting it. Under the old
ledger it was indistinguishable from a total loss. It is MAST code WING-1.

Grading against environment state rather than the transcript is the published
mitigation for "false success / hallucinated completion", and it is the specific
lesson of the 2026-07-18 incident.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.oversight import mast, spans

ROOT = Path("/home/john/Thunderbird")
MISSION_BOARD = ROOT / "OpsCenter" / "mission_board.json"
REAPER_LOG = ROOT / "logs" / "oversight_reaper.log"
# The reaper's own liveness. A silent sensor is worse than no sensor: this repo
# has a documented "monitor EFFICACY not presence" lesson. If this file goes
# stale, the oversight layer itself is down and the digest must say so.
REAPER_HEARTBEAT = ROOT / "OpsCenter" / "state" / "oversight_reaper_heartbeat.json"

REAPER_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("oversight_reaper")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(REAPER_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [REAPER] %(levelname)s: %(message)s"))
    logger.addHandler(_h)

# A mission sitting in a working state longer than this with no movement is
# treated as needing a look. Deliberately generous — a false LOST is itself an
# oversight failure, and alert fatigue is the main way oversight systems die.
MISSION_STALE_HOURS = 48
WORKING_STATES = ("in_progress", "active", "assigned", "pending_review")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _artifacts_present(span: dict) -> tuple[bool, list[str]]:
    """GROUND TRUTH: do the claimed artifacts actually exist on disk?

    This is the whole anti-theater mechanism. We never ask the agent whether it
    finished; we look. Only local paths are checkable here — a URL or commit ref
    is not treated as present, because an unverifiable claim must not read as
    verified.
    """
    try:
        refs = json.loads(span.get("artifact_refs") or "[]")
    except Exception:
        refs = []
    found = []
    for r in refs:
        if not isinstance(r, str) or not r.startswith("/"):
            continue
        try:
            p = Path(r)
            if p.exists() and (p.is_dir() or p.stat().st_size > 0):
                found.append(r)
        except Exception:
            continue
    return bool(found), found


def classify_stale_span(span: dict) -> tuple[str, str, str]:
    """Return (status, mast_code, detail) for a span whose lease expired.

    Decided entirely from observable facts. No model is consulted.
    """
    has_artifacts, found = _artifacts_present(span)
    reported = bool(span.get("verdict") or span.get("detail"))

    code = mast.classify_mechanically(
        declared_done=False,
        artifacts_exist=has_artifacts,
        acceptance_criteria_met=None,
        heartbeat_stale=True,
        reported_result=reported,
        verification_ran=bool(span.get("verified_by")),
    )

    if has_artifacts and not reported:
        return ("SILENT_SUCCESS", "WING-1",
                f"Lease expired but {len(found)} artifact(s) exist on disk and were "
                f"never reported: {', '.join(found[:3])}. Work appears complete; "
                f"the report was dropped. Recoverable — do not re-run.")
    if has_artifacts:
        return ("ABANDONED", code or "FM-3.1",
                f"Lease expired mid-flight with partial output ({len(found)} artifact(s)). "
                f"Work incomplete, no failure declared.")
    return ("LOST", code or "FM-3.1",
            "Lease expired with no heartbeat and no artifacts on disk. "
            "No evidence any work survives.")


def reap_spans(*, db_path: Optional[Path] = None, dry_run: bool = False,
               now: Optional[datetime] = None) -> list[dict]:
    """Close out every RUNNING span past its lease. Returns what it did."""
    results = []
    for span in spans.stale(db_path=db_path, now=now):
        status, code, detail = classify_stale_span(span)
        results.append({
            "span_id": span["span_id"], "trace_id": span["trace_id"],
            "seat": span["seat"], "ticket_id": span.get("ticket_id") or "",
            "task_type": span.get("task_type") or "",
            "status": status, "mast_code": code, "detail": detail,
            "started_at": span.get("started_at"),
        })
        if dry_run:
            continue
        spans.close_span(span["span_id"], status=status, mast_code=code,
                         detail=detail, verdict=status,
                         ground_truth_ref="reaper:disk-check", db_path=db_path)
        logger.info("%s %s seat=%s ticket=%s — %s", status, span["span_id"],
                    span["seat"], span.get("ticket_id") or "-", detail)
    return results


def stale_missions(*, board_path: Optional[Path] = None,
                   hours: int = MISSION_STALE_HOURS,
                   now: Optional[datetime] = None) -> list[dict]:
    """Missions stuck in a working state with no movement.

    Reads mission_board.json DIRECTLY. This is the deliberate fix for the dry
    pipe: it does not matter whether anyone called a dispatch helper, because
    the board is written by the normal workflow regardless.
    """
    path = Path(board_path or MISSION_BOARD)
    cutoff = (now or _now()) - timedelta(hours=hours)
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        logger.error("cannot read mission board %s: %s", path, exc)
        return []

    missions = data.get("missions", data) if isinstance(data, dict) else data
    if isinstance(missions, dict):
        missions = list(missions.values())
    if not isinstance(missions, list):
        return []

    out = []
    for m in missions:
        if not isinstance(m, dict):
            continue
        status = str(m.get("status", "")).lower()
        if status not in WORKING_STATES:
            continue
        ts = (m.get("updated_at") or m.get("last_updated")
              or m.get("created_at") or "")
        try:
            when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if when < cutoff:
            out.append({
                "mission_id": m.get("id") or m.get("mission_id") or "?",
                "title": (m.get("title") or "")[:80],
                "status": status,
                "last_movement": when.isoformat(),
                "stale_hours": round(((now or _now()) - when).total_seconds() / 3600, 1),
                "owner": m.get("owner") or m.get("assigned_to") or "",
            })
    return sorted(out, key=lambda r: r["stale_hours"], reverse=True)


def write_heartbeat(summary: dict) -> None:
    """Record that the reaper itself ran. Monitors EFFICACY, not presence:
    a consumer can tell 'checked and clean' from 'never checked'."""
    try:
        REAPER_HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        REAPER_HEARTBEAT.write_text(json.dumps(
            {"last_run": _now().isoformat(), **summary}, indent=2))
    except Exception as exc:
        logger.error("heartbeat write failed: %s", exc)


def reaper_is_healthy(max_age_minutes: int = 90) -> tuple[bool, str]:
    """Is the oversight layer itself alive? Who watches the watchmen."""
    try:
        d = json.loads(REAPER_HEARTBEAT.read_text())
        last = datetime.fromisoformat(d["last_run"])
        age = (_now() - last).total_seconds() / 60
        if age > max_age_minutes:
            return False, f"reaper last ran {age:.0f}m ago (limit {max_age_minutes}m) — OVERSIGHT DOWN"
        return True, f"reaper healthy, last run {age:.0f}m ago"
    except FileNotFoundError:
        return False, "reaper has NEVER run — OVERSIGHT NOT RUNNING"
    except Exception as exc:
        return False, f"reaper heartbeat unreadable: {exc}"


def run(*, db_path: Optional[Path] = None, board_path: Optional[Path] = None,
        dry_run: bool = False, page: bool = True) -> dict:
    """One full reaper pass. Called by the systemd timer."""
    reaped = reap_spans(db_path=db_path, dry_run=dry_run)
    missions = stale_missions(board_path=board_path)

    summary = {
        "reaped": len(reaped),
        "lost": sum(1 for r in reaped if r["status"] == "LOST"),
        "abandoned": sum(1 for r in reaped if r["status"] == "ABANDONED"),
        "silent_success": sum(1 for r in reaped if r["status"] == "SILENT_SUCCESS"),
        "stale_missions": len(missions),
        "spans_checked": len(spans.live(db_path=db_path)) + len(reaped),
        "dry_run": dry_run,
    }

    if not dry_run:
        write_heartbeat(summary)

    if page and not dry_run:
        _page_if_needed(reaped, missions, summary)

    return {**summary, "detail": reaped, "missions": missions}


def _page_if_needed(reaped: list[dict], missions: list[dict], summary: dict) -> None:
    """Page only on things a human must act on.

    Alert fatigue is the primary failure mode of oversight systems, so
    SILENT_SUCCESS does NOT page — the work is on disk and recoverable; it goes
    in the digest. LOST and ABANDONED page, because work was expected and no
    longer exists.
    """
    actionable = [r for r in reaped if r["status"] in ("LOST", "ABANDONED")]
    if not actionable:
        return
    try:
        from core.staffing.delegation_outcomes import page_commander
        lines = [f"- {r['status']} {r['seat']} {r['ticket_id'] or r['span_id']} "
                 f"({r['mast_code']}): {r['detail'][:120]}" for r in actionable[:5]]
        page_commander(
            problem=f"{len(actionable)} delegation(s) lost or abandoned",
            discussion="\n".join(lines),
            action="Reaper closed them out and recorded MAST codes.",
            next_steps="Re-dispatch or write off. Stale missions: "
                       f"{len(missions)}.",
            source="CHIEF OVERSIGHT",
        )
    except Exception as exc:
        logger.error("page failed: %s", exc)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Wing oversight reaper")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-page", action="store_true")
    args = ap.parse_args()
    res = run(dry_run=args.dry_run, page=not args.no_page)
    print(json.dumps({k: v for k, v in res.items() if k != "detail"}, indent=2))
    for r in res["detail"]:
        print(f"  {r['status']:15} {r['seat']:4} {r['mast_code']:8} {r['detail'][:90]}")
    for m in res["missions"][:10]:
        print(f"  STALE-MISSION {m['mission_id']} {m['stale_hours']}h {m['title']}")
