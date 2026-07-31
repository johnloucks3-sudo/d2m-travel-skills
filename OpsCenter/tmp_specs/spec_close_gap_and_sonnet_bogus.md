# Task: close the OAuth-spend coverage gap, and diagnose a bogus-looking CRIT/Sonnet-88% Telegram alert

## Context — two connected threads, investigate both

**Thread A — coverage gap.** An earlier forensic sweep (this same evening) checked 22 of 29
repo files referencing `CLAUDE_CODE_OAUTH_TOKEN` for overnight Claude spend. Two files were
missed because they are event-driven daemons, not timer-fired scripts:
- `/home/john/Thunderbird/api/thunderbird_api.py` (service: `thunderbird-api.service`, confirmed
  `active`, line ~1807 sets `env["CLAUDE_CODE_OAUTH_TOKEN"] = tok`)
- `/home/john/Thunderbird/OpsCenter/whatsapp_webhook.py` (service:
  `thunderbird-whatsapp-webhook.service`, confirmed `active`, line ~97 sets the same env var from
  `~/.claude/.credentials.json`)
A narrow `journalctl --since "2026-07-31 05:00"` grep for claude/dispatch/spawn found nothing for
either, but that is absence-of-evidence, not proof — these are request-driven, so a narrow grep
can miss real activity if the log format doesn't match the keywords searched.

**Thread B — a Telegram alert the Commander says is bogus and "eats tokens."** Full text he
received, verbatim:
```
🔴 Rate-Limit Guard — CRIT
Transition: STOP → CRIT
All models weekly: [UNKNOWN — telemetry unavailable]
5-hour window:    [██░░░░░░░░░░░░░░░░░░] 14.0%
Sonnet weekly:      [█████████████████░░░] 88.0%
Tokens used: 0
Remaining:  0M 000K tokens
🔴 GRACEFUL DEGRADATION ENGAGED
2026-07-31 11:51 UTC | Rate-Limit Guard v1.0
```
Note the internal inconsistency: 5-hour window is a HEALTHY 14%, yet the state is CRIT — because
`_compute_target_state()` in `core/ops/thunderbird_rate_limit_guard.py` lets the Sonnet axis
independently force CRIT/STOP (`SONNET_CRIT = 85`) regardless of the other axes. The Sonnet
figure (88.0%) comes from a THIRD, previously uninvestigated data source:
`get_sonnet_weekly_pct()` in the same file, which reads
`SELECT sonnet_weekly_pct FROM claude_usage_reports ORDER BY ts DESC LIMIT 1` from
`/home/john/Thunderbird/storage/ai_costs.db`. Nobody has checked whether that 88.0% is a live,
current figure or a stale one being read as if it were current — the function has no freshness
check at all, it just takes whatever the newest row says, however old that row is.

## What to actually do

### Thread A
1. Widen the investigation window to the last 48 hours (not just tonight) for both
   `thunderbird-api.service` and `thunderbird-whatsapp-webhook.service`:
   `journalctl --user -u thunderbird-api.service --since "2026-07-29 12:00" -o short-iso`
   `journalctl --user -u thunderbird-whatsapp-webhook.service --since "2026-07-29 12:00" -o short-iso`
   Search the FULL output (not just a keyword grep) for anything indicating a headless Claude
   spawn or Anthropic API call — read enough of `thunderbird_api.py` and `whatsapp_webhook.py`
   around their `CLAUDE_CODE_OAUTH_TOKEN` usage to know what log line THEY would actually emit if
   they fired (their own logging format, not a generic guess), then search for that exact pattern.
2. Report definitively: did either service spend OAuth-metered tokens in the last 48h? Cite the
   exact log lines or the exact absence with the exact command you ran to establish absence.

### Thread B
3. Inspect `/home/john/Thunderbird/storage/ai_costs.db`, table `claude_usage_reports`. Run
   (read-only, `sqlite3` CLI or Python `sqlite3` module):
   ```sql
   SELECT ts, sonnet_weekly_pct FROM claude_usage_reports ORDER BY ts DESC LIMIT 10;
   ```
   Report the actual rows. Determine: how old is the newest row? Is anything writing NEW rows to
   this table currently (check for a service/timer that inserts into it — grep the repo for
   `claude_usage_reports` and `INSERT INTO`)? If the writer is dead/disabled, the 88.0% is a
   FROZEN historical reading, not a live one — that is the root cause of a false CRIT.
4. Count how many times the guard has transitioned CRIT/STOP due to the Sonnet axis specifically
   (i.e., `sonnet_pct >= SONNET_CRIT` while the weekly/5h axes were healthy) by reading
   `/home/john/Thunderbird/config/rate_guard_state.json`'s `transitions` array and cross-
   referencing against a live re-check of what `get_sonnet_weekly_pct()` returns right now. If the
   guard has been flapping (repeated transitions in and out of CRIT because a stale 88% sits right
   at the threshold, or because it never changes and something else flaps around it), report the
   transition count and timestamps.
5. Check for a Telegram feedback loop: does anything in this repo (e.g.
   `OpsCenter/thunderbird_telegram_gw.py`, which is one of the 29 OAuth-referencing files) LISTEN
   for incoming Telegram messages FROM the Wing's own bot and process them through headless
   Claude — i.e., could the guard's own alert, once posted to Telegram, be picked back up and
   "handled" by another Claude-spawning process, creating a self-inflicted loop? Read enough of
   `thunderbird_telegram_gw.py`'s message-handling logic to answer definitively yes/no with a
   cited line number, not a guess.

### Fix, if Thread B confirms the 88% is stale/frozen (only if confirmed — do not fix a hypothesis)
6. If step 3 confirms the newest `claude_usage_reports` row is stale (no writer currently updates
   it), apply the SAME fail-closed principle already used elsewhere in this file for
   `get_weekly_pct()`: add a freshness check to `get_sonnet_weekly_pct()` — if the newest row's
   `ts` is older than a reasonable threshold (propose 24 hours; state your reasoning if you pick a
   different number), return `0.0` is WRONG per the fail-closed doctrine already established
   tonight (stale must never look like "safe/zero" either) — instead return `None`, exactly
   mirroring `get_weekly_pct()`'s contract. Then update `_compute_target_state()`'s sonnet axis:
   `sonnet_pct: Optional[float] = None` (change the default and the type), and when `sonnet_pct is
   None`, do NOT force CRIT/STOP from a value that no longer exists — a stale/missing Sonnet
   reading should fall back to the ROLLBACK floor used elsewhere for "this axis has no current
   opinion," NOT to CRIT (unlike the weekly axis, which fails closed to CRIT because losing that
   read entirely is itself alarming — losing a THIRD, redundant, currently-broken data source is
   not comparably alarming, and forcing false CRIT/STOP off a dead sensor is the exact bug being
   fixed). State this reasoning explicitly in your deliverable so it can be checked, don't just
   change the behavior silently.
7. If step 3 shows the table IS being actively updated and 88.0% is genuinely current: do NOT
   change any code. Report that the alert is real, not bogus, and say so plainly — do not force a
   fix onto a working system just because the Commander called it bogus from the Telegram side;
   verify first.

## Explicit exclusions
- Do NOT touch `core/ci/self_observability.py` (already fixed tonight, out of scope).
- Do NOT touch anything in `thunderbird_api.py` or `whatsapp_webhook.py` — Thread A is read-only
  investigation, not a fix task.
- Do NOT send any real Telegram message, do not write to `config/rate_guard_state.json`, do not
  call `evaluate()` for real.
- If you make the Thread B fix, ONLY touch `core/ops/thunderbird_rate_limit_guard.py`. Re-run the
  existing test suite (`tests/test_rate_limit_guard_5h.py`) and confirm it still passes — if your
  change to `_compute_target_state`'s signature breaks an existing test, fix the test to match the
  new, intentional behavior, and say exactly what you changed and why.

## Acceptance criteria (mechanically checkable — run these yourself)
```
git status --short api/thunderbird_api.py OpsCenter/whatsapp_webhook.py    # must be empty (no edits)
python3 -m py_compile core/ops/thunderbird_rate_limit_guard.py             # must exit 0
python3 -m pytest tests/test_rate_limit_guard_5h.py -q                     # must exit 0
```
Report the literal output of all three, plus the literal SQL query result from step 3.

## Reply path
- Write your findings AND (if applicable) your fix in place, plus a deliverable to the ABSOLUTE
  path given to you separately containing: Thread A verdict with evidence, Thread B root-cause
  finding with the actual SQL rows quoted, whether a fix was applied and why/why not, and the
  literal acceptance-criteria command output.
- Report every uncertainty, tagged as such — do not filter for confidence.
- Print a one-line verdict starting "AG DONE:".
