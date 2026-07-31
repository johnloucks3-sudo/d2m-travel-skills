# Task: find what consumed the Claude Code MAX OAuth quota overnight, and assess whether a reliable exhaustion prediction is even possible

## Context — read this fully before searching, it rules out a whole category of false leads

The Commander's Claude MAX plan is 5X, billed on a rolling 5-hour AND rolling 7-day window,
both tracked against ONE OAuth token (`~/.claude/.credentials.json` → `CLAUDE_CODE_OAUTH_TOKEN`).
Live reading right now (from `~/.claude/hud/.usage-cache.json`): `fiveHour: 8`, `sevenDay: 9`
(percent). The Commander reports the 7-day figure rose roughly 5 points overnight, before any
interactive work resumed. He wants the cause found and, if the data supports it, a prediction of
when the 7-day allowance will be exhausted at the observed rate.

**CRITICAL — already verified, do not re-investigate:** `core/ai_infra/managed_agent_client.py`'s
`WingAgentClient` (the primary path `ci-sentinel.timer` uses to auto-remediate crash-looping
services) authenticates with a SEPARATE `ANTHROPIC_API_KEY` (see `_load_api_key()`, line ~86),
NOT the OAuth token. Every `ci-sentinel` "managed_alert" strike with a `cost_usd` field is billed
on a DIFFERENT account entirely and does NOT touch the 5X MAX 5h/7d quota. Do not chase this path
as a cause of the MAX-quota rise — it is a real cost, just not this one.

**What DOES touch the OAuth quota** — the only three ways anything can spend against
`CLAUDE_CODE_OAUTH_TOKEN`:
1. An interactive Claude Code session (a human or an orchestrator typing into `claude`).
2. The "OC" lane: `scripts/oc_worker.py` polls a task board every 15s and dispatches each claimed
   task to headless Claude Haiku via `OpsCenter/dispatch_claude.py` — confirmed at
   `scripts/oc_worker.py:172-176`, it loads `~/.claude/.credentials.json` and sets
   `env["CLAUDE_CODE_OAUTH_TOKEN"]` before spawning.
3. Any OTHER script in this repo that independently does the same thing — loads
   `~/.claude/.credentials.json` / sets `CLAUDE_CODE_OAUTH_TOKEN` / spawns `claude -p` headless.
   This pattern is DOCUMENTED as the canonical way to spawn headless Claude in this repo's own
   `.claude/CLAUDE.md` ("CLAUDE HEADLESS DISPATCH" section) — so it is likely used in more than
   one place, not just `oc_worker.py`.

One specific prior-known contributor, now CLOSED: earlier tonight (before ~0000 MT 2026-07-31),
`core/ci/self_observability.py`'s `dispatch_remediation()` had an UNGATED automatic fallback that
spawned a headless Claude process via `subprocess.Popen([...DISPATCH_CLAUDE..., "--model",
"sonnet"...], start_new_session=True)` on attempt 3 of any CI remediation. That code path was
DELETED at approximately 2026-07-31 00:00 MT (git-uncommitted, but the file on disk no longer has
it — confirm this yourself with a grep, don't take my word for it). If `ci-sentinel` fired on a
crash-looping service BEFORE that deletion landed, and hit attempt 3, it would have spent real
OAuth-metered tokens with `--model sonnet` — a plausible, well-timed contributor to "overnight."

## What to actually do

1. Establish the actual wall-clock window to investigate: from 2026-07-30 23:00 MT
   (2026-07-31 05:00 UTC) — roughly when this evening's work began — through now. Convert to UTC
   for all log/journal queries (MT is UTC-6 in this period, no DST ambiguity needed, just use
   `date -d` or equivalent, or pass explicit UTC timestamps).

2. Search for evidence of EACH of the three quota-spending paths above, in this window:

   **a. OC lane activity.** Read `/home/john/Thunderbird/OpsCenter/delegation_outcomes.jsonl` —
   count rows with `seat: "OC"` and `action: "delegated"` whose `ts` falls in the window. Cross-
   reference against `journalctl --user -u opencode-worker.service --since "2026-07-30 23:00" -o
   short-iso` (adjust unit name if `systemctl --user status opencode-worker.service` shows a
   different exact name — check first) for actual dispatch/completion log lines with timestamps
   and any token/duration info Reported. Report count of dispatches, and whether any single one
   looks unusually large (long duration, big prompt).

   **b. The now-deleted auto-headless-spawn fallback.** Confirm via
   `git log -p --since="2026-07-30 20:00" -- core/ci/self_observability.py` (or `git diff` against
   the working tree if uncommitted — check `git status` first) exactly when the
   `subprocess.Popen(...DISPATCH_CLAUDE...)` block was removed. Then search
   `/home/john/Thunderbird/OpsCenter/ci_awareness.jsonl` for any `event` entries in the window
   BEFORE that deletion timestamp with `event` values like `"ENGAGE"` where the corresponding
   `delegation_outcomes.jsonl` row (correlate by `unit`/`ticket_id`/timestamp) shows
   `action: "self_executed"` and `dispatch_mode: "self"` — that combination is the fingerprint of
   the now-closed leak actually firing. Report every match found, with timestamps.

   **c. Any OTHER script that spawns headless Claude with the OAuth token.** Run:
   ```
   grep -rln "CLAUDE_CODE_OAUTH_TOKEN" --include=*.py /home/john/Thunderbird | grep -v /.claude/worktrees/
   ```
   For every file found (besides `oc_worker.py` and the now-removed one in
   `self_observability.py`), read enough of it to determine: (i) is it invoked by an enabled
   systemd timer/service, (ii) did it actually run in the investigation window — check with
   `journalctl --user -u <matching-service-name> --since "2026-07-30 23:00" -o short-iso` if a
   matching unit exists, or check the script's own log output file if it writes one. Report every
   file found and whether it fired in-window.

3. **Interactive session accounting.** This Claude Code session itself has been running since
   roughly 2026-07-30 23:00 MT and is a real, expected, non-mysterious contributor to usage. Do
   NOT try to separate "this session's" tokens from the total — you have no way to measure that
   from outside the session. Just note plainly that interactive-session usage is expected and is
   NOT part of what needs explaining; the goal is to find UNEXPLAINED/background contributors.

4. **Assess whether an exhaustion prediction is honestly possible.** Check whether ANY file in
   this repo stores a TIME-SERIES of the 5h or 7d usage percentage (not just the current single
   reading in `~/.claude/hud/.usage-cache.json`, which overwrites itself every 60s with no
   history, and not just `config/rate_guard_state.json`, which only stores `last_five_hour_pct`,
   never `last_pct`/weekly since `get_weekly_pct()` still returns `None` every time `ccusage`
   fails). If you find NO historical time-series anywhere, say so explicitly and do NOT compute a
   projected exhaustion date/time from a single data point plus a guessed rate — that would be
   fabricated precision, which the Commander has explicitly told this Wing he does not want
   ("NO EMBELLISHMENT... state the fact, cite the source"). Instead, report: (a) confirmation that
   no real projection is currently possible, (b) exactly what minimal change would make one
   possible (e.g., "guard already runs every 5 min via `thunderbird-rate-limit-guard.timer` and
   already stores `last_five_hour_pct` — extending it to also store timestamped weekly samples
   once `get_weekly_pct()` is unblocked would give N days of history within N days").

## Explicit exclusions
- Do NOT modify any file. This is investigation only — read-only. If you believe a fix is
  warranted, describe it in your report; do not apply it.
- Do NOT re-investigate `managed_agent_client.py` / `ANTHROPIC_API_KEY` — already resolved, stated
  above as context, not a task item.
- Do NOT guess at or invent a burn rate or exhaustion date if the underlying data does not support
  one. An honest "insufficient data" is the correct and expected answer if that is what you find.
- Do NOT run any command that sends real Telegram messages, real Commander escalations, or any
  write to `OpsCenter/delegation_outcomes.jsonl`, `OpsCenter/ci_awareness.jsonl`, or
  `config/rate_guard_state.json` — read them, never write to them.

## Acceptance criteria (mechanically checkable — run these yourself)
```
git status --short core/ci/self_observability.py    # must show clean or unrelated changes only —
                                                       # confirms you did not touch this file
wc -l /home/john/Thunderbird/OpsCenter/delegation_outcomes.jsonl   # confirm you actually read a
                                                                     # file of this size, not zero
```
Report the literal output of both.

## Reply path
- Write your findings to the ABSOLUTE deliverable path given to you separately, structured as:
  1. Ranked list of confirmed/probable contributors to the overnight OAuth-quota rise, each with
     timestamps and evidence (log lines, jsonl rows, git log entries) — cite what you actually
     read, quote it, don't summarize from memory.
  2. Explicit statement on whether any other script besides `oc_worker.py` sets
     `CLAUDE_CODE_OAUTH_TOKEN`, and whether it fired in-window.
  3. Explicit statement on whether a real exhaustion projection is possible right now, and if not,
     the minimal fix that would make one possible going forward.
  4. Anything uncertain or low-confidence — report it anyway, tagged as such. Do not filter for
     confidence; a downstream review does that.
- Print a one-line verdict starting "AG DONE:".
