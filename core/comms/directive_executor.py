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

FRONT-DESK RULE (Round Table 2026-08-08): every letter — TASKING / CC / FYI / ACK —
leaves with a threaded DISPOSITION receipt (WHO / RDD / ACTION / DELIVERABLE); no
inbound message is ever silently dropped, and ACK closes the ticket it answers.
"""

from __future__ import annotations

import hashlib
import json
import re
import traceback
from datetime import datetime, timedelta, timezone
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
# thread_id -> mission_id, so a later ACK in the same thread closes the ticket
# that thread created even when the caller cannot supply previous_mission_id.
THREAD_INDEX_PATH = ROOT / "OpsCenter" / "email_thread_missions.json"

DONE = "DONE"
FAILED = "FAILED"
UNVERIFIED = "UNVERIFIED"
TASKED = "TASKED"
LOGGED = "LOGGED"
ACKED = "ACKED"

# Seat routing for email-created work. OC is the default executor lane ($0);
# CC takes the letters that turn on judgment rather than execution.
_DEFAULT_SEAT = "OC"
_JUDGMENT_SEAT = "CC"
_URGENT_HOURS = 8
_STANDARD_HOURS = 24

# The board's own ground truth for an email-origin ticket. Silver's FRONT frame
# (core/silver/gate.silver_front_frame) refuses a seat delegation with no named
# ground-truth source, and checks that any path-like source actually exists.
_GROUND_TRUTH_SOURCES = [
    "OpsCenter/directive_executions.jsonl",
    "OpsCenter/mission_board.json",
]

# A letter whose entire body is one of these words is an acknowledgement, not
# work: it closes a ticket and gets a receipt, it never opens anything.
_ACK_ONLY_RE = re.compile(
    r"^\s*(?:roger|wilco|done|ok|okay|thanks|thank you|acknowledged|duly noted|copy)"
    r"[\s.!,;:\-–—]*$",
    re.IGNORECASE,
)

# Where the Commander's own words stop and quoted/forwarded matter begins.
_QUOTE_BOUNDARY_RE = re.compile(
    r"(-{2,}\s*forwarded message\s*-{2,}"
    r"|-{2,}\s*original message\s*-{2,}"
    r"|^on .{0,120}\bwrote:\s*$"
    r"|^from:\s*.+$"
    r"|^sent from my )",
    re.IGNORECASE | re.MULTILINE,
)

# Judgment work (route to CC) vs execution work (route to OC).
_JUDGMENT_RE = re.compile(
    r"\b(client|email to|draft|strategy|review|decide|architecture|approve|opinion)\b",
    re.IGNORECASE,
)
_URGENT_RE = re.compile(r"(\burgent\b|\bred\b|\basap\b|🔴)", re.IGNORECASE)


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


# ── front-desk helpers: WHO / RDD / ACTION, and the receipt itself ─────────
# Pure functions (no I/O) so the disposition of a letter is testable without a
# board, a mailbox, or a network.

def _own_words(body: str) -> list[str]:
    """The Commander's own lines, with quoted/forwarded matter cut away."""
    body = body or ""
    m = _QUOTE_BOUNDARY_RE.search(body)
    head = body[: m.start()] if m else body
    return [ln.strip() for ln in head.splitlines()
            if ln.strip() and not ln.strip().startswith(">")]


def _is_ack_only(body: str) -> bool:
    """True only for a solo ack phrase — "Roger." and nothing else. A body with
    a second line is a letter that happens to open politely, not an ack."""
    lines = _own_words(body)
    return len(lines) == 1 and bool(_ACK_ONLY_RE.match(lines[0]))


def _pick_seat(subject: str = "", body: str = "") -> str:
    """WHO. Judgment words -> CC; everything else -> OC, the free execution lane."""
    return _JUDGMENT_SEAT if _JUDGMENT_RE.search(f"{subject or ''}\n{body or ''}") else _DEFAULT_SEAT


def _certifier_for(seat: str) -> str:
    """Anti-theater (§3.5.3): the certifier can never be the assignee."""
    return "AG" if (seat or "").upper() == "CC" else "CC"


def _deadline_hours(subject: str = "", body: str = "") -> int:
    """RDD. Urgency markers pull the suspense in to 8h; standard is 24h."""
    return _URGENT_HOURS if _URGENT_RE.search(f"{subject or ''}\n{body or ''}") else _STANDARD_HOURS


def _mission_rdd(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _action_line(subject: str = "", body: str = "") -> str:
    """ACTION. The first real line of the letter, subject as fallback."""
    lines = _own_words(body)
    first = lines[0] if lines else (subject or "").strip()
    return (first[:200] or "(no action stated)")


def _checkable_criteria(action: str) -> str:
    """Silver's FRONT frame rejects acceptance criteria a second seat could not
    verify without asking the assignee. A one-line email order usually names
    nothing checkable, so the receipt row it produces is named explicitly."""
    try:
        from core.silver.gate import is_checkable
        if is_checkable(action):
            return action
    except Exception:
        pass
    return f"{action} — verifiable against the receipt row in {_GROUND_TRUTH_SOURCES[0]}"


def _leaf_token(thread_id: str = "", message_id: str = "", subject: str = "") -> str:
    """Stable short id for THIS letter (the leaf of its thread), so a receipt
    can be tied back to the exact message that produced it."""
    raw = f"{thread_id}|{message_id}|{subject}".encode("utf-8", "replace")
    return hashlib.sha1(raw).hexdigest()[:10]


def _render_receipt(mode: str, mission_id: Optional[str], who: str, rdd: str,
                    action: str, deliverable: str, note: str = "") -> str:
    """The DISPOSITION block — the reply every letter earns. It states what was
    done with the letter; it never promises what will be done with the work."""
    lines = [
        f"DISPOSITION — {mode}",
        f"WHO:         {who or '—'}",
        f"RDD:         {rdd or '—'}",
        f"ACTION:      {action or '—'}",
        f"DELIVERABLE: {deliverable or '—'}",
        f"TICKET:      {mission_id or '—'}",
    ]
    if note:
        lines.append(f"NOTE:        {note}")
    return "\n".join(lines)


# ── thread ↔ ticket linkage ────────────────────────────────────────────────

def _thread_index_load() -> dict:
    try:
        return json.loads(THREAD_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _thread_index_put(thread_id: str, mission_id: str) -> None:
    if not thread_id or not mission_id:
        return
    try:
        idx = _thread_index_load()
        idx[thread_id] = mission_id
        THREAD_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        THREAD_INDEX_PATH.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    except Exception as exc:
        _log({"ts": _now(), "status": "THREAD_INDEX_FAIL", "thread_id": thread_id,
              "mission_id": mission_id, "detail": f"{type(exc).__name__}: {exc}"})


def _thread_index_get(thread_id: str) -> Optional[str]:
    return _thread_index_load().get(thread_id) if thread_id else None


_ALREADY_CLOSED = ("closed", "completed", "complete", "done", "cancelled")


def _set_mission_closed(mission_id: str, note: str) -> bool:
    """Lock the board, mark one mission closed, save (save_board releases the
    lock). Returns False when the mission does not exist OR is already closed —
    a receipt must never claim to have closed something it did not.

    The already-closed guard is what keeps a SECOND ack on the same thread
    honest: the thread index still points at the ticket the thread created, so
    without this check a follow-up "Thanks" would re-close a finished mission
    and report that as work. It falls through to "no new work" instead."""
    if not mission_id:
        return False
    from tcd._imports import load_mission_board_sync

    mbs = load_mission_board_sync()
    fd = mbs.acquire_lock()
    try:
        board = mbs.load_board()
        missions = board.get("missions", board.get("active_missions", []))
        target = next((m for m in missions if m.get("id") == mission_id), None)
        if target is None or str(target.get("status", "")).lower() in _ALREADY_CLOSED:
            mbs.release_lock(fd)
            return False
        target["status"] = "closed"
        target["updated_at"] = _now()
        target.setdefault("logs", []).append(f"{_now()}: {note}")
        mbs.save_board(board, fd)
        return True
    except Exception:
        mbs.release_lock(fd)
        raise


def _close_ack_ticket(mission_id: str) -> bool:
    """ACK closes the ticket it answers — the log line, not a new mission."""
    return _set_mission_closed(mission_id, "closed by Commander ACK (email C2)")


def _close_created_fyi(mission_id: str) -> bool:
    """FYI is a filed row, not work: created for the record, closed on arrival."""
    return _set_mission_closed(mission_id, "FYI filed — closed at creation (email C2)")


def _create_email_mission(title: str, description: str, priority: str = "P1",
                          assigned_to: str = "hale", acceptance_criteria: str = "",
                          deadline_hours: int = 24) -> tuple[str, Optional[str]]:
    """Create a real mission through mission_board_sync's own locked add_mission —
    the one place mission-creation + dedup logic lives (see its docstring). Tagged
    source="email" so email-origin work is distinguishable on the board from every
    other origin.

    2026-08-08: WHO / RDD / ACTION are now forwarded rather than hardcoded to
    "unassigned" — assigned_to is a real seat for TASKING/CC, which puts the
    ticket on the cross-Hale delegation path (add_mission -> delegate_mission).
    That path is gated: it requires acceptance criteria a second seat can check,
    a named ground-truth source, and a certifier that differs from the assignee.
    All three are supplied here, or the letter would produce nothing but a
    DelegationError.

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
            board, title, description, priority,
            assigned_to=assigned_to, source="email",
            acceptance_criteria=acceptance_criteria,
            certified_by=_certifier_for(assigned_to),
            deadline_hours=deadline_hours,
            ground_truth_sources=list(_GROUND_TRUTH_SOURCES),
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
    thread_id: str = "",
    message_id_id: str = "",
    previous_mission_id: Optional[str] = None,
) -> dict:
    """Gmail as C2 front desk: classify an inbound Commander email and dispose of
    it — every letter leaves with a receipt (Round Table 2026-08-08).

        TASKING / CC — a real mission, WHO=seat, RDD=deadline, ACTION=criteria.
                       CC creates work too: the Commander's stated intent is that
                       being copied is being tasked, not merely informed.
        FYI          — a mission created and closed on arrival: a filed row, not work.
        ACK          — a solo "Roger."/"Done." closes the ticket it answers
                       (previous_mission_id, else the thread's ticket) and logs;
                       with no ticket to close it logs "no new work".

    Returns the disposition dict, including `receipt` — the DISPOSITION block the
    sweep sends back threaded. This function still sends nothing itself; the
    reply path for WORK stays silent until verified, per execute_directive above.
    A receipt reports the disposition of the letter, never the completion of the
    work.
    """
    _capture(directive_text, source)
    mode, reason = classify_email_mode(
        subject=subject, body=directive_text, to_addr=to_addr, cc_addr=cc_addr
    )
    leaf = _leaf_token(thread_id, message_id_id, subject)
    action = _action_line(subject, directive_text)
    base: dict[str, Any] = {
        "ts": _now(), "source": source, "mode": mode, "reason": reason,
        "subject": (subject or "")[:200], "directive": directive_text[:500],
        "thread_id": thread_id, "message_id": message_id_id, "leaf_token": leaf,
        "action": action, "who": "", "rdd": "",
    }

    # ── ACK: closes a ticket, never opens one ─────────────────────────────
    if _is_ack_only(directive_text):
        target = previous_mission_id or _thread_index_get(thread_id)
        closed = False
        if target:
            try:
                closed = _close_ack_ticket(target)
            except Exception as exc:
                return _log({**base, "status": FAILED, "mission_id": target,
                             "receipt": _render_receipt(
                                 "ACK", target, "—", "—", action,
                                 "ticket NOT closed", f"{type(exc).__name__}: {exc}"),
                             "detail": f"ack close failed: {type(exc).__name__}: {exc}"})
        if closed:
            return _log({**base, "status": ACKED, "mission_id": target,
                         "receipt": _render_receipt(
                             "ACK", target, "—", "—", action,
                             f"Acknowledged, ticket {target} closed"),
                         "detail": f"acknowledged — ticket {target} closed"})
        return _log({**base, "status": LOGGED, "mission_id": None,
                     "receipt": _render_receipt(
                         "ACK", None, "—", "—", action,
                         "logged — no new work",
                         "no open ticket referenced by this thread"),
                     "detail": "acknowledgement logged — no ticket referenced, no new work"})

    title = (subject or directive_text).strip()[:80] or "(no subject)"

    # ── FYI: filed row, closed at creation ────────────────────────────────
    if mode == MODE_FYI:
        try:
            message, mission_id = _create_email_mission(
                title, directive_text[:2000], priority,
                assigned_to="hale", acceptance_criteria=_checkable_criteria(action),
                deadline_hours=_STANDARD_HOURS,
            )
            if mission_id:
                _close_created_fyi(mission_id)
        except Exception as exc:
            return _log({**base, "status": FAILED, "mission_id": None,
                         "receipt": _render_receipt(
                             "FYI", None, "—", "—", action, "NOT filed",
                             f"{type(exc).__name__}: {exc}"),
                         "detail": f"{type(exc).__name__}: {exc}"})
        return _log({**base, "status": LOGGED, "mission_id": mission_id,
                     "receipt": _render_receipt(
                         "FYI", mission_id, "—", "—", action,
                         "filed and closed — no work created",
                         "" if mission_id else message[:160]),
                     "detail": f"FYI filed ({reason}) — {message}"})

    # ── TASKING / CC: real work, real seat, real suspense ─────────────────
    who = _pick_seat(subject, directive_text)
    hours = _deadline_hours(subject, directive_text)
    rdd = _mission_rdd(hours)
    criteria = _checkable_criteria(action)
    base.update({"who": who, "rdd": rdd})

    try:
        message, mission_id = _create_email_mission(
            title, directive_text[:2000], priority,
            assigned_to=who, acceptance_criteria=criteria, deadline_hours=hours,
        )
    except Exception as exc:
        return _log({**base, "status": FAILED, "mission_id": None,
                     "receipt": _render_receipt(
                         mode, None, who, rdd, action, "NO ticket created",
                         f"{type(exc).__name__}: {exc}"),
                     "detail": f"{type(exc).__name__}: {exc}"})

    if not mission_id:
        # add_mission blocked an open duplicate. Say so — do not report a ticket
        # that does not exist, and do not silently create a second one.
        return _log({**base, "status": LOGGED, "mission_id": None,
                     "receipt": _render_receipt(
                         mode, None, who, rdd, action,
                         "already tracked — no new ticket", message[:160]),
                     "detail": message})

    _thread_index_put(thread_id, mission_id)
    return _log({**base, "status": TASKED, "mission_id": mission_id,
                 "receipt": _render_receipt(
                     mode, mission_id, who, rdd, action,
                     f"{mission_id} on the board; {who} verifies against "
                     f"{_GROUND_TRUTH_SOURCES[0]} by RDD"),
                 "detail": message})


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
