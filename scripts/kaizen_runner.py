#!/usr/bin/env python3
"""kaizen_runner.py — KAIZEN item #4: unattended headless CC ticket runner.

BLUF: Watches OpsCenter/tickets/*.json for open tickets and executes ONLY the
CC-seat ones whose `gates` list is empty (routine work, no elevated authority).
Tickets requesting any elevated gate are SKIPPED and left `open` for Commander
review — gates travel with the ticket, never inherited. THIS is the high-risk
item: unwatched execution, so the gate is non-negotiable.

Usage:
  python3 scripts/kaizen_runner.py            # --dry-run (default): print what
                                              #   WOULD happen, zero dispatch,
                                              #   zero file writes
  python3 scripts/kaizen_runner.py --dry-run  # same
  python3 scripts/kaizen_runner.py --live     # real thing

On --live, every touched ticket ends in `done` or `blocked`; nothing stays
`open` after a runner pass (except gate-skipped tickets, which explicitly stay
`open` for Commander review).

Design notes:
- Reuses core.relay.task_templates.read_open_tickets() and build/verify schema.
- Reuses the exact local-Claude dispatch pattern from scripts/rt_dispatch.py
  (env-pop ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN + --mcp-config +
  stdin=DEVNULL) — proven working, do NOT substitute an untested alternative.
- Defensive is_checkable() re-check on verify_step (already gated at ticket
  creation by build_cc_task(); if it somehow passes anyway, treat as blocked).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.relay.task_templates import read_open_tickets

CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
MCP_CONFIG = Path.home() / ".claude" / "mcp.json"
TICKETS_DIR = Path.home() / "Thunderbird" / "OpsCenter" / "tickets"

MAX_RESULT_CHARS = 2000
SKIP_MSG = (
    "SKIPPED — elevated gates require Commander review, "
    "not unattended execution: {ticket_id}"
)


def _claude_oauth_token() -> str:
    creds = json.loads((Path.home() / ".claude" / ".credentials.json").read_text())
    return creds["claudeAiOauth"]["accessToken"]


def run_local_claude(prompt: str, alias: str = "sonnet", timeout_s: int = 600):
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = _claude_oauth_token()
    cmd = [str(CLAUDE_BIN), "-p", prompt, "--model", alias,
           "--output-format", "text", "--mcp-config", str(MCP_CONFIG)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s,
                          env=env, stdin=subprocess.DEVNULL)


def build_prompt(ticket: dict) -> str:
    return (
        ticket["spec"]
        + "\n\nDONE means exactly: "
        + ticket["verify_step"]
        + "\n\nWrite your result as your final output."
    )


def eligible(ticket: dict) -> bool:
    return ticket.get("seat") == "CC" and not ticket.get("gates")


def update_ticket(ticket: dict, status: str, result: str):
    ticket["status"] = status
    ticket["result"] = result[:MAX_RESULT_CHARS]
    path = TICKETS_DIR / f"{ticket['ticket_id']}.json"
    path.write_text(json.dumps(ticket, indent=2))


def dry_run_pass(tickets: list[dict]):
    print(f"[DRY-RUN] {len(tickets)} open ticket(s) scanned")
    for t in tickets:
        tid = t.get("ticket_id", "?")
        if t.get("seat") != "CC":
            print(f"  {tid}: seat={t.get('seat')!r} — NOT a CC ticket, ignored")
        elif t.get("gates"):
            print(f"  {tid}: gates={t.get('gates')!r} — {SKIP_MSG.format(ticket_id=tid)}")
        else:
            print(f"  {tid}: gates=[] — WOULD execute (spec + verify_step)")


def live_pass(tickets: list[dict]):
    for t in tickets:
        tid = t.get("ticket_id", "?")
        if t.get("seat") != "CC":
            print(f"{tid}: seat={t.get('seat')!r} — not a CC ticket, left as-is")
            continue
        if t.get("gates"):
            print(SKIP_MSG.format(ticket_id=tid))
            continue
        try:
            from core.silver.gate import is_checkable
        except Exception as exc:  # gate module unavailable — fail closed
            update_ticket(t, "blocked", f"blocked: is_checkable() unavailable: {exc}")
            print(f"{tid}: BLOCKED (gate module unavailable) — marked blocked")
            continue
        if not is_checkable(t.get("verify_step", "")):
            update_ticket(
                t, "blocked",
                "blocked: verify_step failed is_checkable() at runtime",
            )
            print(f"{tid}: BLOCKED (uncheckable verify_step) — marked blocked")
            continue
        prompt = build_prompt(t)
        print(f"{tid}: dispatching to local Claude (sonnet)...")
        try:
            r = run_local_claude(prompt, alias="sonnet")
        except subprocess.TimeoutExpired:
            update_ticket(t, "blocked", "blocked: dispatch timed out (600s)")
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
    tickets = read_open_tickets()
    if live:
        live_pass(tickets)
    else:
        dry_run_pass(tickets)


if __name__ == "__main__":
    main()
