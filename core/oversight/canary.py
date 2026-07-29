"""
core/oversight/canary.py — does the oversight layer actually work RIGHT NOW?

THE PROBLEM THIS SOLVES
-----------------------
On 2026-07-29 an audit found six oversight functions with zero call sites.
They were correct. They were tested. They had never run in production, and
nothing noticed for weeks because the daily digest read their silence as
"clean." `verify_and_record()` — the function CLAUDE.md declares mandatory for
catching false completion claims — has never once been invoked outside a test.

Building oversight v2 does not fix that class of failure. v2 can become orphan
number seven the same way: shipped, tested, wired into a hook that silently
stops firing, digest still green. Every component here is capable of failing
silently, and a silent sensor is worse than no sensor because it manufactures
confidence.

So this module does not monitor the WING. It monitors THE OVERSIGHT LAYER, by
running a known-bad task through the whole pipeline on a schedule and asserting
the pipeline notices:

    inject synthetic failure -> lease expires -> reaper detects
        -> correct MAST code assigned -> failure is routed for paging

**The absence of the expected detection is itself the P0 alert.** That
inversion is the entire point. A canary that reports "all good" while detecting
nothing is the exact failure mode it exists to catch, so every scenario below
asserts a POSITIVE, specific, expected outcome — never merely "no error."

ISOLATION
---------
Canary spans are written to their own database (`wing_canary.db`), never to the
production ledger. Synthetic failures must never contaminate real seat
scorecards, cost accounting, or the Commander's failure counts — an oversight
system that inflates its own failure numbers with test data is lying in the
other direction.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.oversight import mast, reaper, spans

ROOT = Path("/home/john/Thunderbird")
CANARY_DB = ROOT / "OpsCenter" / "wing_canary.db"
CANARY_STATE = ROOT / "OpsCenter" / "state" / "oversight_canary.json"
CANARY_LOG = ROOT / "logs" / "oversight_canary.log"

CANARY_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("oversight_canary")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(CANARY_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [CANARY] %(levelname)s: %(message)s"))
    logger.addHandler(_h)

CANARY_SEAT = "SUBAGENT"
CANARY_TASK_TYPE = "__canary__"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CanaryFailure(Exception):
    """The oversight layer failed to detect a failure it was built to detect."""


# --------------------------------------------------------------- scenarios
# Each scenario injects a KNOWN condition and asserts a SPECIFIC expected
# verdict. "No exception raised" is never treated as a pass.

def _scenario_lost(db: Path) -> dict:
    """A worker that vanishes with nothing on disk must be classified LOST."""
    span = spans.open_span(
        seat=CANARY_SEAT, task_type=CANARY_TASK_TYPE, lease_seconds=1,
        created_by="canary", db_path=db)
    found = reaper.reap_spans(db_path=db, now=_now() + timedelta(minutes=10))
    hits = [r for r in found if r["span_id"] == span["span_id"]]
    if not hits:
        raise CanaryFailure(
            "reaper did NOT detect a vanished worker — lost-task detection is DEAD")
    got = hits[0]
    if got["status"] != "LOST":
        raise CanaryFailure(
            f"vanished worker classified {got['status']}, expected LOST")
    if got["mast_code"] != "FM-3.1":
        raise CanaryFailure(
            f"wrong MAST code {got['mast_code']}, expected FM-3.1")
    return {"scenario": "lost", "ok": True, "detected_as": got["status"],
            "mast_code": got["mast_code"]}


def _scenario_silent_success(db: Path, tmp: Path) -> dict:
    """Work completed but never reported must be SILENT_SUCCESS, not LOST.

    Observed live three times on 2026-07-29. Misclassifying it as LOST would
    cause the Wing to re-run completed work and burn budget twice.
    """
    art = tmp / "canary_artifact.md"
    art.write_text("canary deliverable — real bytes on disk\n")
    span = spans.open_span(
        seat=CANARY_SEAT, task_type=CANARY_TASK_TYPE, lease_seconds=1,
        created_by="canary", db_path=db)
    spans.add_artifact(span["span_id"], str(art), db_path=db)
    found = reaper.reap_spans(db_path=db, now=_now() + timedelta(minutes=10))
    hits = [r for r in found if r["span_id"] == span["span_id"]]
    if not hits:
        raise CanaryFailure("reaper did NOT detect an unreported completion")
    got = hits[0]
    if got["status"] != "SILENT_SUCCESS":
        raise CanaryFailure(
            f"completed-but-unreported work classified {got['status']}, "
            f"expected SILENT_SUCCESS — the Wing would re-run finished work")
    if got["mast_code"] != "WING-1":
        raise CanaryFailure(f"wrong MAST code {got['mast_code']}, expected WING-1")
    return {"scenario": "silent_success", "ok": True,
            "detected_as": got["status"], "mast_code": got["mast_code"]}


def _scenario_healthy_control(db: Path) -> dict:
    """FALSE-POSITIVE GUARD. Live work must NOT be reaped.

    Without this, a canary passes trivially by flagging everything. A reaper
    that kills healthy work is worse than one that misses failures, because it
    would interrupt real client work mid-flight.
    """
    span = spans.open_span(
        seat=CANARY_SEAT, task_type=CANARY_TASK_TYPE, lease_seconds=7200,
        created_by="canary", db_path=db)
    found = reaper.reap_spans(db_path=db, now=_now())
    if any(r["span_id"] == span["span_id"] for r in found):
        raise CanaryFailure(
            "reaper killed a HEALTHY in-flight span — false positives would "
            "interrupt real client work")
    spans.close_span(span["span_id"], status="OK", db_path=db)
    return {"scenario": "healthy_control", "ok": True,
            "detected_as": "correctly left alone"}


def _scenario_self_verification_rejected(db: Path) -> dict:
    """A seat grading itself must never count as verified.

    This is the self-preference-bias guard. If it ever passes, CC could mark
    its own work verified and the whole cross-engine doctrine is decorative.
    """
    span = spans.open_span(seat="CC", task_type=CANARY_TASK_TYPE,
                           created_by="canary", db_path=db)
    closed = spans.close_span(span["span_id"], status="OK", verified_by="CC",
                              db_path=db)
    if spans.is_independently_verified(closed):
        raise CanaryFailure(
            "self-verification COUNTED as independent — cross-engine "
            "verification is decorative and CC can rubber-stamp itself")
    return {"scenario": "self_verification_rejected", "ok": True,
            "detected_as": "self-grade correctly refused"}


def _scenario_bad_mast_code_rejected(db: Path) -> dict:
    """An invented failure code must be demoted, never finalized."""
    span = spans.open_span(seat=CANARY_SEAT, task_type=CANARY_TASK_TYPE,
                           created_by="canary", db_path=db)
    closed = spans.close_span(span["span_id"], status="FAILED",
                              mast_code="FM-99.9-INVENTED", db_path=db)
    if closed["mast_code"] is not None:
        raise CanaryFailure(
            f"invented MAST code {closed['mast_code']} was FINALIZED — the "
            f"taxonomy column can no longer be trusted")
    return {"scenario": "bad_mast_code_rejected", "ok": True,
            "detected_as": "invalid code demoted to proposed"}


def _scenario_page_lane_reachable() -> dict:
    """Can a failure actually reach the Commander?

    Detection that cannot page is not oversight. We verify the lane is
    IMPORTABLE and CALLABLE without actually paging — sending a real page on
    every canary run would be the alert-fatigue failure mode.
    """
    try:
        from core.staffing.delegation_outcomes import page_commander
    except Exception as exc:
        raise CanaryFailure(f"page lane unimportable: {exc}") from exc
    if not callable(page_commander):
        raise CanaryFailure("page_commander is not callable")
    try:
        from core.comms.wing_page import send_page  # noqa: F401
    except Exception as exc:
        raise CanaryFailure(
            f"underlying wing_page lane is broken — failures would be detected "
            f"but never reach the Commander: {exc}") from exc
    return {"scenario": "page_lane_reachable", "ok": True,
            "detected_as": "lane importable and callable"}


SCENARIOS = ("lost", "silent_success", "healthy_control",
             "self_verification_rejected", "bad_mast_code_rejected",
             "page_lane_reachable")


def run(*, db_path: Optional[Path] = None, page_on_failure: bool = True,
        tmp_dir: Optional[Path] = None) -> dict:
    """Run every scenario. Returns a report; raises nothing."""
    import tempfile

    db = Path(db_path or CANARY_DB)
    # Fresh DB each run: canary state must never accumulate or interfere.
    try:
        if db.exists():
            db.unlink()
        for suffix in ("-wal", "-shm"):
            p = Path(str(db) + suffix)
            if p.exists():
                p.unlink()
    except Exception:
        pass
    spans.init_db(db)

    tmp = Path(tmp_dir) if tmp_dir else Path(tempfile.mkdtemp(prefix="canary_"))
    tmp.mkdir(parents=True, exist_ok=True)

    results, failures = [], []
    checks = [
        ("lost", lambda: _scenario_lost(db)),
        ("silent_success", lambda: _scenario_silent_success(db, tmp)),
        ("healthy_control", lambda: _scenario_healthy_control(db)),
        ("self_verification_rejected", lambda: _scenario_self_verification_rejected(db)),
        ("bad_mast_code_rejected", lambda: _scenario_bad_mast_code_rejected(db)),
        ("page_lane_reachable", _scenario_page_lane_reachable),
    ]
    for name, fn in checks:
        try:
            results.append(fn())
        except CanaryFailure as exc:
            results.append({"scenario": name, "ok": False, "error": str(exc)})
            failures.append(f"{name}: {exc}")
            logger.error("CANARY FAILED %s — %s", name, exc)
        except Exception as exc:  # unexpected breakage is also a canary failure
            results.append({"scenario": name, "ok": False,
                            "error": f"unexpected: {exc!r}"})
            failures.append(f"{name}: unexpected {exc!r}")
            logger.error("CANARY ERROR %s — %r", name, exc)

    report = {
        "ts": _now().isoformat(),
        "scenarios_run": len(checks),
        "passed": sum(1 for r in results if r.get("ok")),
        "failed": len(failures),
        "healthy": not failures,
        "failures": failures,
        "results": results,
    }

    try:
        CANARY_STATE.parent.mkdir(parents=True, exist_ok=True)
        CANARY_STATE.write_text(json.dumps(report, indent=2))
    except Exception as exc:
        logger.error("canary state write failed: %s", exc)

    if failures:
        logger.error("OVERSIGHT LAYER IS BLIND: %d/%d scenarios failed",
                     len(failures), len(checks))
        if page_on_failure:
            _page(report)
    else:
        logger.info("canary healthy — %d/%d scenarios detected as expected",
                    report["passed"], len(checks))
    return report


def _page(report: dict) -> None:
    try:
        from core.staffing.delegation_outcomes import page_commander
        page_commander(
            problem="OVERSIGHT LAYER IS BLIND — canary failed",
            discussion="\n".join(f"- {f}" for f in report["failures"][:6]),
            action="Synthetic failures were injected and the oversight layer "
                   "did not detect them as expected. Every 'clean' Wing Ops "
                   "line since the last healthy canary is unsupported.",
            next_steps="Treat all green oversight reporting as UNVERIFIED "
                       "until this passes. core/oversight/canary.py",
            source="CHIEF OVERSIGHT (CANARY)",
        )
    except Exception as exc:
        logger.error("canary page failed — oversight blind AND unable to "
                     "report it: %s", exc)


def canary_status(max_age_minutes: int = 1440) -> tuple[bool, str]:
    """For the daily digest. Distinguishes three states that must never be
    collapsed: passing, failing, and never-run."""
    try:
        d = json.loads(CANARY_STATE.read_text())
    except FileNotFoundError:
        return False, "canary has NEVER run — oversight layer is UNVERIFIED"
    except Exception as exc:
        return False, f"canary state unreadable: {exc}"
    age = (_now() - datetime.fromisoformat(d["ts"])).total_seconds() / 60
    if not d.get("healthy"):
        return False, (f"CANARY FAILING ({d.get('failed')} scenario(s)): "
                       f"{'; '.join(d.get('failures', [])[:2])}")
    if age > max_age_minutes:
        return False, (f"canary last passed {age/60:.1f}h ago (limit "
                       f"{max_age_minutes/60:.0f}h) — oversight STALE")
    return True, (f"canary healthy — {d.get('passed')}/{d.get('scenarios_run')} "
                  f"scenarios verified {age:.0f}m ago")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Oversight canary")
    ap.add_argument("--no-page", action="store_true")
    args = ap.parse_args()
    rep = run(page_on_failure=not args.no_page)
    print(f"{'HEALTHY' if rep['healthy'] else 'BLIND'} — "
          f"{rep['passed']}/{rep['scenarios_run']} scenarios")
    for r in rep["results"]:
        mark = "ok  " if r.get("ok") else "FAIL"
        print(f"  [{mark}] {r['scenario']:30} {r.get('detected_as') or r.get('error','')[:80]}")
    raise SystemExit(0 if rep["healthy"] else 1)
