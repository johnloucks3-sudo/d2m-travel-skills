"""
core/comms/directive_executor.py — a reply means verified work, or it means nothing.

C2 RECALIBRATION task 11, Commander directive 2026-07-29:
    "not a damn thing is being DONE about message I am sending gmail.
     I get words back, no action."

He was describing a machine that was built to do exactly that. The directive sweep's
prompt instructed the model, verbatim:

    "Build/code task -> 'Wilco — logged to mission board: [brief description].
     Sterling/ELON execute. Completion report follows.'"

So a build request produced a confident sentence, a mission-board row, and nothing
else. The acknowledgement WAS the deliverable. Those prompts now forbid promise
language and point here instead — this module is what makes that redirection honest
rather than just quieter.

THE RULE
--------
A confirmation is emitted ONLY after the work is done AND independently verified
against ground truth. Every other outcome tells him plainly that it is not done.

    execute_directive(...) -> one of
        DONE       work completed, verification PASSED, artifact cited
        FAILED     execution raised; he is told what broke
        UNVERIFIED work claims to be done but verification could not confirm it
                   — reported as NOT done, never upgraded

UNVERIFIED is the important one. On 2026-07-18 CC self-reported a cross-Hale
delegation as complete when it had failed, which is why SO-2026-07-19 exists. An
unverifiable claim is not a smaller success; it is an unknown, and it is reported
as an unknown.

Verification runs on a DIFFERENT engine via integrity_check.verify_and_record —
CC checking CC's own work is not verification.
"""

from __future__ import annotations

import json
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from core.comms.email_mode_classifier import (
    MODE_CC,
    MODE_FYI,
    MODE_TASKING,
    classify_email_mode,
)

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "OpsCenter" / "directive_executions.jsonl"

DONE = "DONE"
FAILED = "FAILED"
UNVERIFIED = "UNVERIFIED"
TASKED = "TASKED"
LOGGED = "LOGGED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(row: dict) -> dict:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return row


def _unverified_reply(detail: str) -> str:
    """AG review 2026-07-29, finding 3. UNVERIFIED used to send NOTHING, which violates
    SO-2026-06-25 (email closed-loop: every Commander message gets a response, no silent
    reads). Silence is ambiguous — he cannot tell "still working" from "crashed" from
    "verification failed". So UNVERIFIED now closes the loop while refusing to imply
    completion. The rule was never "stay quiet"; it was "never claim done when it isn't"."""
    return ("NOT CONFIRMED — work was attempted but could not be independently verified.\n"
            f"Reason: {detail}\n\n"
            "Treat this as NOT done. Nothing here asserts completion.")


def _capture(directive_text: str, source: str) -> None:
    """Record the directive before touching it. A directive that is executed but never
    captured is how a MANDATORY instruction went missing on 2026-07-19.

    AG review 2026-07-29, finding 4: the original swallowed every exception with a bare
    `pass`, which guaranteed the exact failure it was written to prevent — just
    invisibly. Capture failure now falls back to a raw append here, so the record
    survives even when the ledger module does not.
    """
    try:
        from core.staffing.directive_ledger import capture
        capture(directive_text, source=source)
    except Exception as exc:
        _log({"ts": _now(), "status": "CAPTURE_FALLBACK", "source": source,
              "directive": directive_text[:500],
              "detail": f"directive_ledger.capture failed: {type(exc).__name__}: {exc}"})


def _create_email_mission(title: str, description: str, priority: str = "P1") -> tuple[str, Optional[str]]:
    """Create a real mission through mission_board_sync's own locked add_mission —
    the one place mission-creation + dedup logic lives (see its docstring). Tagged
    source="email" so TASKING-mode email tasking is distinguishable on the board
    from every other origin. Not called for FYI/CC — those create no work.

    Goes through tcd._imports.load_mission_board_sync() — the SAME intake path
    core/comms/slack_receiver.py's handle_view_submission() and tcd/writeback.py
    use, so Slack, Sheet, and Email converge on one store rather than three
    parallel mission-creation implementations (repo-layout/box-layout import
    shim included, not just the locking discipline)."""
    from tcd._imports import load_mission_board_sync

    mbs = load_mission_board_sync()
    fd = mbs.acquire_lock()
    try:
        board = mbs.load_board()
        message, mission_id = mbs.add_mission(
            board, title, description, priority, assigned_to="unassigned", source="email",
        )
        mbs.save_board(board, fd)
        return message, mission_id
    except Exception:
        mbs.release_lock(fd)
        raise


def route_email(
    directive_text: str,
    *,
    subject: str = "",
    to_addr: str = "",
    cc_addr: str = "",
    source: str = "commander_email",
    priority: str = "P1",
) -> dict:
    """Gmail as C2: classify an inbound Commander email into TASKING / FYI / CC
    and route it accordingly (Commander directive, directive ledger: "I want to
    use Gmail as a C2 tasking and FYI and CC capability").

    TASKING creates a real mission (source="email", via the locked add_mission
    path). FYI and CC create NO work — captured to the directive ledger (every
    Commander message, mandate-eligible) and logged here, nothing more.

    This is the entry point the inbound sweep should call per message; it does
    not send any reply — the reply path stays silent until verified, per
    execute_directive's rule above.
    """
    _capture(directive_text, source)
    mode, reason = classify_email_mode(
        subject=subject, body=directive_text, to_addr=to_addr, cc_addr=cc_addr
    )
    base: dict[str, Any] = {
        "ts": _now(), "source": source, "mode": mode, "reason": reason,
        "subject": (subject or "")[:200], "directive": directive_text[:500],
    }

    if mode != MODE_TASKING:
        # FYI / CC: informational. No mission, no reply — just the record.
        return _log({**base, "status": LOGGED, "mission_id": None,
                     "detail": f"{mode} — no work created ({reason})"})

    title = (subject or directive_text).strip()[:80] or "(no subject)"
    try:
        message, mission_id = _create_email_mission(title, directive_text[:2000], priority)
    except Exception as exc:
        return _log({**base, "status": FAILED, "mission_id": None,
                     "detail": f"{type(exc).__name__}: {exc}"})

    return _log({**base, "status": TASKED, "mission_id": mission_id, "detail": message})


# Commands that cannot falsify anything. AG review 2026-07-29, finding 1: the caller
# supplies its own ground truth, so `echo 'it worked'` graded itself PASS.
_TRIVIAL_CMD = re.compile(r"^\s*(echo|true|:|printf)\b", re.I)


def _reject_trivial_ground_truth(cmds: list[str]) -> Optional[str]:
    """A verification command must be capable of returning a FAILING answer."""
    real = [c for c in cmds if not _TRIVIAL_CMD.match(c or "")]
    if not real:
        return ("every ground_truth_cmd is trivial (echo/true/printf) — these cannot "
                "falsify a claim, so they verify nothing. Supply a command that reads "
                "real state and can fail.")
    return None


def execute_directive(
    directive_text: str,
    work: Callable[[], Any],
    *,
    claims: list[str],
    ground_truth_cmds: Optional[list[str]] = None,
    source: str = "commander_email",
    ticket_id: str = "",
    engine: str = "AG",
    verify: bool = True,
) -> dict:
    """Run the work, verify it on another engine, and only then allow a confirmation.

    `claims`            — what you assert is now true, in checkable terms.
    `ground_truth_cmds` — shell commands whose output proves or disproves the claims.
                          Without these there is nothing to verify AGAINST, so the
                          result is UNVERIFIED regardless of how well the work went.

    Returns {status, reply_text, artifact, detail, ...}. `reply_text` is safe to send:
    it never promises, and it is empty for statuses that have earned no confirmation.
    """
    _capture(directive_text, source)
    base: dict[str, Any] = {"ts": _now(), "ticket_id": ticket_id, "source": source,
                            "directive": directive_text[:500], "claims": claims}

    # AG review finding 2: empty claims meant verify_and_record had nothing to falsify,
    # and the DONE branch fell back to the generic "directive executed" — reporting
    # completion for work that may have failed. A claim is not optional.
    if not claims or not any(str(c).strip() for c in claims):
        return _log({**base, "status": UNVERIFIED,
                     "detail": "no claims supplied — nothing to verify, so nothing can be asserted",
                     "reply_text": _unverified_reply(
                         "no verifiable claim was stated for this directive")})

    # 1. Do the work.
    try:
        artifact = work()
    except Exception as exc:
        return _log({**base, "status": FAILED,
                     "detail": f"{type(exc).__name__}: {exc}",
                     "traceback": traceback.format_exc()[-1200:],
                     "reply_text": (
                         f"FAILED — {type(exc).__name__}: {exc}\n\n"
                         "Not done. No workaround attempted without your call.")})

    # 2. Verification is not optional, and it is not done by the engine that did the work.
    if not verify:
        return _log({**base, "status": UNVERIFIED, "artifact": str(artifact)[:400],
                     "detail": "verification explicitly skipped by caller",
                     "reply_text": _unverified_reply("verification was skipped")})

    if not ground_truth_cmds:
        return _log({**base, "status": UNVERIFIED, "artifact": str(artifact)[:400],
                     "detail": ("no ground_truth_cmds supplied — nothing to verify the "
                                "claims against, so completion cannot be asserted"),
                     "reply_text": _unverified_reply("no ground-truth check was supplied")})

    trivial = _reject_trivial_ground_truth(ground_truth_cmds)
    if trivial:
        return _log({**base, "status": UNVERIFIED, "artifact": str(artifact)[:400],
                     "detail": trivial, "reply_text": _unverified_reply(trivial)})

    try:
        from core.staffing.integrity_check import verify_and_record
        v = verify_and_record(claims, ground_truth_cmds=ground_truth_cmds,
                              engine=engine, ticket_id=ticket_id,
                              task_type="directive_execution")
    except Exception as exc:
        return _log({**base, "status": UNVERIFIED, "artifact": str(artifact)[:400],
                     "detail": f"verification engine unreachable: {type(exc).__name__}: {exc}",
                     "reply_text": _unverified_reply(
                         f"the independent verification engine was unreachable ({type(exc).__name__})")})

    verdict = str(v.get("verdict", "")).upper()
    if verdict != "PASS":
        return _log({**base, "status": UNVERIFIED, "artifact": str(artifact)[:400],
                     "verdict": verdict, "detail": v.get("discrepancy_detail", "")[:600],
                     "reply_text": _unverified_reply(
                         f"independent verification returned {verdict}: "
                         f"{str(v.get('discrepancy_detail',''))[:200]}")})

    # 3. Earned. Cite the artifact — a confirmation without one is just a nicer promise.
    return _log({**base, "status": DONE, "artifact": str(artifact)[:400],
                 "verdict": verdict, "verified_by": engine,
                 "reply_text": (f"Done — {claims[0] if claims else 'directive executed'}\n"
                                f"Artifact: {artifact}\n"
                                f"Verified independently by {engine}.")})


def should_reply(result: dict) -> bool:
    """Every outcome closes the loop; only DONE may imply completion.

    Originally UNVERIFIED sent nothing. AG's adversarial review (2026-07-29) showed that
    violates SO-2026-06-25 and makes silence ambiguous — the Commander cannot separate
    "still working" from "crashed" from "verification failed". The fix is not to speak
    more confidently, it is to speak plainly about what is NOT confirmed.
    """
    return bool(result.get("reply_text"))


def recent(n: int = 20) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-n:]
