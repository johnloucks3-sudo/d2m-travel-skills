# Task: exhaustive audit of every background source of Claude MAX OAuth spend

## Context

The Commander is on the Claude MAX 5X plan. Live reading tonight: 5-hour window ~19%, 7-day
window ~10%. His concern: if 10%/day is background/menial-task burn rather than his own
interactive work, that compounds to ~70% of the week on overhead alone, leaving ~30% headroom for
real work. He wants every background leak found. This is READ-ONLY forensic work — do not fix
anything, do not run any repair, do not touch any file.

**Ground truth already established tonight — do not re-derive, build on it:**
- The token that matters is `CLAUDE_CODE_OAUTH_TOKEN`, loaded from `~/.claude/.credentials.json`.
  Anything spawning `claude -p ...` with that env var set spends against the 5X quota.
- A SEPARATE `ANTHROPIC_API_KEY` (different account, different billing) is used by
  `core/ai_infra/managed_agent_client.py`'s `WingAgentClient` — this does NOT touch the 5X OAuth
  quota. Do not flag managed-agent-client spend as an OAuth leak; note it separately if found, but
  it is out of scope for "the 30% headroom" concern.
- 29 Python files in this repo reference `CLAUDE_CODE_OAUTH_TOKEN` (confirmed via
  `grep -rl "CLAUDE_CODE_OAUTH_TOKEN" --include=*.py /home/john/Thunderbird | grep -v
  /.claude/worktrees/`). Two of them — `api/thunderbird_api.py` and
  `OpsCenter/whatsapp_webhook.py` — were checked earlier tonight and confirmed CLEAN (zero fires)
  over a 48h window ending ~2026-07-31 12:42 UTC. The other 27 have NOT been exhaustively audited
  for firing frequency/cadence — only spot-checked for whether they were enabled.
- ~240 systemd user timers exist (`ls ~/.config/systemd/user/*.timer | wc -l`). Their `ExecStart`
  lines were checked once for literal `claude`/`anthropic` keywords and found clean — but that
  check is known to be insufficient: it missed `ci-sentinel.timer`, which reaches Claude spend
  from inside Python, not from its ExecStart line. Do not repeat the shallow ExecStart-only check;
  go deeper per the method below.

## What to actually do

1. Get the full list of 29 files:
   `grep -rl "CLAUDE_CODE_OAUTH_TOKEN" --include=*.py /home/john/Thunderbird | grep -v /.claude/worktrees/`

2. For EACH of the 29 files (skip the 2 already-cleared: `api/thunderbird_api.py`,
   `OpsCenter/whatsapp_webhook.py` — note them as "already cleared" in your output, don't re-audit):
   a. Read enough of the file to understand: is this invoked by a systemd timer/service (find
      which unit, via `grep -l <script-basename> ~/.config/systemd/user/*.service`), by another
      script calling it as a subprocess, by a cron-like poll loop, or is it dead/unused code with
      no live trigger at all?
   b. If it has a live trigger, determine the ACTUAL cadence: read the `.timer` file's
      `OnCalendar`/`OnUnitActiveSec`, or if triggered by another script's poll loop, find that
      loop's interval.
   c. Determine what model tier it requests when it spawns Claude (grep for `--model`,
      `"model":`, or similar in the spawn call — haiku / sonnet / opus / unspecified-default).
   d. Cross-reference against `journalctl --user -u <unit> --since "2026-07-24 00:00" -o short-iso`
      (7-day window) — count ACTUAL fires in that window (not just "timer exists"), and specifically
      count how many of those fires reached the actual Claude-spawning code path (a timer can fire
      without ever hitting the spend line if it early-exits — check the log lines around the spawn
      point to distinguish "ran but didn't spend" from "ran and spent").
   e. Also check `/home/john/Thunderbird/OpsCenter/delegation_outcomes.jsonl` for any rows with
      `seat: "CC"` and `action: "self_executed"` whose `ticket_id`/`task_type` correlate to this
      script, as a second independent signal of actual spend.

3. Separately, for the ~240 systemd timers NOT already covered by step 2 (i.e., timers whose
   service does NOT map to one of the 29 files): spot-check a sample for hidden Claude spend by a
   DEEPER method than grepping ExecStart — for each, read the actual Python entrypoint file (not
   just its systemd unit) and grep THAT file's full source (and one level of its own imports, if
   quick) for `CLAUDE_CODE_OAUTH_TOKEN`, `claude -p`, `anthropic.Anthropic(`, or
   `subprocess.*claude`. This is how `ci-sentinel` was found earlier — its systemd ExecStart line
   was clean but its Python called into a module that spawned Claude. Prioritize timers with short
   intervals (`OnUnitActiveSec` under 30 minutes) since those compound fastest — list the 20
   shortest-interval enabled timers and check each one specifically, even if not obviously
   Claude-related by name.

4. Rank every CONFIRMED live OAuth-spending source found (from steps 2 and 3) by estimated weekly
   fire count × apparent model tier (opus/sonnet spend far more per call than haiku). You will not
   have exact token counts — say so plainly rather than inventing a number — but fire-count ×
   tier-tier is a defensible severity ranking and is what the Commander needs to prioritize.

5. For each confirmed leak, note: is there an obvious downgrade available (e.g., this looks
   mechanical enough to route to OC's free DeepSeek lane, or the model tier could drop from
   sonnet/opus to haiku) — flag it, do not implement it.

## Explicit exclusions
- Do NOT modify, disable, or restart any file, timer, or service.
- Do NOT count `WingAgentClient`/`ANTHROPIC_API_KEY`-billed spend as an OAuth leak — note
  separately if found, out of primary scope.
- Do NOT re-audit `api/thunderbird_api.py` or `OpsCenter/whatsapp_webhook.py` — already cleared.
- Do NOT guess at token/cost figures you cannot verify — report fire-count and tier, flag
  cost-per-call as unknown if you cannot find it, do not fabricate a number.
- Report EVERY finding, including low-confidence ones, tagged with confidence and severity —
  this Wing's standing doctrine is coverage over filtering; a downstream review ranks them.

## Acceptance criteria (mechanically checkable — run yourself)
```
grep -rl "CLAUDE_CODE_OAUTH_TOKEN" --include=*.py /home/john/Thunderbird | grep -v /.claude/worktrees/ | wc -l
```
Must print 29 (or note explicitly if the real count differs and why). Report this literal output.

## Reply path
- Write a ranked findings table to the ABSOLUTE deliverable path given to you separately: file,
  trigger mechanism, cadence, model tier, 7-day fire count (or "could not determine" — say so),
  confidence, severity, downgrade opportunity if any.
- Print a one-line verdict starting "AG DONE:".
