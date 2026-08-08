#!/usr/bin/env python3
"""kaizen_runner_oc.py — KAIZEN Approve & Execute: OC-seat ticket runner.

BLUF: Mirrors scripts/kaizen_runner.py's shape exactly, for seat=="OC"
tickets instead of "CC". Watches OpsCenter/tickets/*.json for open OC-seat
tickets whose `gates` list is empty; dispatches each directly via `opencode
run` (never the oc_worker.py queue — that wraps every task in a generic
"write your summary" prompt that competes with a real deliverable, a
confirmed failure mode from 2026-08-08). Tickets requesting any elevated
gate are SKIPPED and left `open` for Commander review — gates travel with
the ticket, never inherited.

Usage:
  python3 scripts/kaizen_runner_oc.py            # --dry-run (default)
  python3 scripts/kaizen_runner_oc.py --dry-run  # same
  python3 scripts/kaizen_runner_oc.py --live     # real thing

Re-entrancy: a non-blocking process lock (core.relay.task_templates.
acquire_runner_lock) means a second invocation of this same script exits
immediately if a prior one is still running. Before scanning, any ticket
stuck `in_progress` for this seat longer than 2x DISPATCH_TIMEOUT_S is
reclaimed as `blocked` (crashed/OOM'd prior run). Design bias: fail toward
late, never toward double-dispatch.

Result honesty: every written result is tagged verification: "hard" (the
ticket's verify_step passed is_checkable() at creation) or "soft" (a
human-typed form ticket, self-report only) — never silently upgraded.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.relay.oc_hygiene import before_dispatch
from core.relay.task_templates import (
    acquire_runner_lock, claim_ticket, read_open_tickets, reclaim_orphans,
)

OPENCODE_BIN = Path.home() / ".opencode" / "bin" / "opencode"
OC_MODEL = "opencode/deepseek-v4-flash-free"
TICKETS_DIR = Path.home() / "Thunderbird" / "OpsCenter" / "tickets"

MAX_RESULT_CHARS = 2000
DISPATCH_TIMEOUT_S = 300  # OC is fast; a hang past this isn't real work
LOCK_NAME = "kaizen-runner-oc"
SKIP_MSG = (
    "SKIPPED — elevated gates require Commander review, "
    "not unattended execution: {ticket_id}"
)


def run_oc(prompt: str, timeout_s: int = DISPATCH_TIMEOUT_S):
    """Direct opencode dispatch — the proven pattern, not oc_worker.py's
    queue. Gated by oc_hygiene.before_dispatch() so this doesn't pile onto
    an already-saturated concurrency slot (MAX_CONCURRENT=2)."""
    gate = before_dispatch()
    if not gate["ok"]:
        return subprocess.CompletedProcess(
            args=["opencode", "run"], returncode=429, stdout="",
            stderr=f"OC lane deferred: {gate['reason']}",
        )
    return subprocess.run(
        [str(OPENCODE_BIN), "run", "--model", OC_MODEL, prompt],
        capture_output=True, text=True, timeout=timeout_s,
        cwd=str(Path.home() / "Thunderbird"), start_new_session=True,
    )


def build_prompt(ticket: dict) -> str:
    return (
        ticket["spec"]
        + "\n\nDONE means exactly: "
        + ticket["verify_step"]
        + "\n\nWrite your result as your final output."
    )


def update_ticket(ticket: dict, status: str, result: str):
    ticket["status"] = status
    ticket["result"] = result[:MAX_RESULT_CHARS]
    ticket["verification"] = "hard" if ticket.get("verify_step_checkable") else "soft"
    path = TICKETS_DIR / f"{ticket['ticket_id']}.json"
    path.write_text(json.dumps(ticket, indent=2))


def dry_run_pass(tickets: list[dict]):
    print(f"[DRY-RUN] {len(tickets)} open ticket(s) scanned")
    for t in tickets:
        tid = t.get("ticket_id", "?")
        if t.get("seat") != "OC":
            print(f"  {tid}: seat={t.get('seat')!r} — NOT an OC ticket, ignored")
        elif t.get("gates"):
            print(f"  {tid}: gates={t.get('gates')!r} — {SKIP_MSG.format(ticket_id=tid)}")
        else:
            mode = "hard" if t.get("verify_step_checkable") else "soft"
            print(f"  {tid}: gates=[] verification={mode} — WOULD execute (spec + verify_step)")


def live_pass(tickets: list[dict]):
    for t in tickets:
        tid = t.get("ticket_id", "?")
        if t.get("seat") != "OC":
            print(f"{tid}: seat={t.get('seat')!r} — not an OC ticket, left as-is")
            continue
        if t.get("gates"):
            print(SKIP_MSG.format(ticket_id=tid))
            continue
        t = claim_ticket(t, TICKETS_DIR)  # status -> in_progress, claimed_at set
        prompt = build_prompt(t)
        print(f"{tid}: dispatching to OC ({OC_MODEL})...")
        try:
            r = run_oc(prompt)
        except subprocess.TimeoutExpired:
            update_ticket(t, "blocked", f"blocked: dispatch timed out ({DISPATCH_TIMEOUT_S}s)")
            print(f"{tid}: BLOCKED (timeout) — marked blocked")
            continue
        except Exception as exc:
            update_ticket(t, "blocked", f"blocked: dispatch error: {exc}")
            print(f"{tid}: BLOCKED (dispatch error) — marked blocked")
            continue
        if r.returncode == 0:
            result = (r.stdout or "").strip()
            update_ticket(t, "done", result or "(empty result)")
            print(f"{tid}: DONE — result recorded ({len(result)} chars)")
        else:
            err = (r.stderr or "").strip() or "(no stderr)"
            update_ticket(t, "blocked", f"blocked: returncode {r.returncode}: {err}")
            print(f"{tid}: BLOCKED (returncode {r.returncode}) — marked blocked")


def main():
    live = "--live" in sys.argv[1:]
    if live:
        lock = acquire_runner_lock(LOCK_NAME)
        if lock is None:
            print(f"[{LOCK_NAME}] another instance is already running — exiting")
            return
        reclaimed = reclaim_orphans("OC", DISPATCH_TIMEOUT_S, TICKETS_DIR)
        if reclaimed:
            print(f"[LIVE] reclaimed {len(reclaimed)} orphaned in_progress ticket(s): {reclaimed}")
        tickets = read_open_tickets()
        live_pass(tickets)
    else:
        tickets = read_open_tickets()
        dry_run_pass(tickets)


if __name__ == "__main__":
    main()
