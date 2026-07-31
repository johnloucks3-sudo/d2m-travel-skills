# Task: audit whether "free lane" work ever silently falls through to metered Claude OAuth spend

## Context

Same overall concern as a parallel audit (spec_leak_audit_A, running separately, covering timer/
script inventory — do not duplicate that work, this thread is narrower and different: model-tier
FALL-THROUGH, not inventory). Commander's concern: 7-day OAuth usage (~10% tonight) may include
"menial" work that was SUPPOSED to be free (routed to OC's DeepSeek lane or otherwise off-meter)
but silently fell through to metered Claude instead. This is READ-ONLY forensic work — do not fix
anything, do not touch any file.

**Ground truth already established tonight:**
- `scripts/oc_worker.py` is the real OC lane. It polls a task board every 15s and, per its own
  code, dispatches each claimed task to headless Claude HAIKU via `OpsCenter/dispatch_claude.py`
  — using the SAME `CLAUDE_CODE_OAUTH_TOKEN` as everything else (confirmed:
  `scripts/oc_worker.py` loads `~/.claude/.credentials.json` and sets
  `env["CLAUDE_CODE_OAUTH_TOKEN"]` before spawning). Despite being called "OC" / "OpenCode" /
  "DeepSeek" in doctrine and dispatch logs (e.g. `[off Claude meter]` log lines seen tonight), it
  is ACTUALLY dispatching to Claude Haiku via the OAuth-metered path, not to a genuinely separate
  DeepSeek model. **This may be the single biggest finding of this whole audit — the "free" lane
  everyone believes is off-meter may not be.** Confirm or refute this precisely: does
  `OpsCenter/dispatch_claude.py`, when called by `oc_worker.py`, ALWAYS use
  `CLAUDE_CODE_OAUTH_TOKEN` + a `claude` CLI invocation (which spends the 5X quota regardless of
  which model tier is requested), or does it have a genuine non-Claude code path that the
  "[off Claude meter]" log line is describing correctly? Read `OpsCenter/dispatch_claude.py` end
  to end to answer this definitively — this is the crux of the whole audit.
- Every observation tonight of `delegation_outcomes.jsonl` rows with `seat: "OC"` showed
  `dispatch_mode: "async_poll"` and log lines claiming `[off Claude meter]` — but nobody has yet
  read `dispatch_claude.py` itself closely enough to confirm that claim is TRUE rather than a
  stale/inaccurate comment. If the OC lane has been quietly spending Claude Haiku on every single
  one of its dispatches (9 seen in one window alone tonight, more over a full week), that could
  easily be the dominant contributor to weekly OAuth usage — far more than any single timer.

## What to actually do

1. Read `OpsCenter/dispatch_claude.py` completely. Determine EXACTLY what it does when invoked:
   does it call the `claude` CLI binary (which always uses `CLAUDE_CODE_OAUTH_TOKEN` /
   `ANTHROPIC_API_KEY` and spends against whichever account's quota that credential belongs to,
   REGARDLESS of "haiku" being a cheaper model — cheaper does not mean free), or does it call an
   actually-separate, actually-free DeepSeek endpoint? Quote the exact subprocess/API call.

2. If `dispatch_claude.py` DOES use `CLAUDE_CODE_OAUTH_TOKEN`/the `claude` CLI (even for "Haiku"),
   this is a confirmed OAuth spend, and the "[off Claude meter]" log line in `oc_worker.py` is
   WRONG/misleading — every OC dispatch is actually metered spend on the same 5X quota as
   everything else, just on a cheaper model tier. State this finding explicitly and clearly if
   confirmed — do not soften it, this is exactly the kind of finding the Commander needs surfaced
   even though (especially because) it contradicts what several log lines and prior reports
   claimed tonight.

3. If step 1 shows `dispatch_claude.py` genuinely does NOT touch the OAuth token for OC-routed
   work (e.g., it branches on a caller-supplied flag/model param and only sets the OAuth env var
   for non-OC callers), then trace that branch precisely and quote the code that proves OC calls
   take the free path. Do not accept a comment or log string as proof — only actual conditional
   logic in the code counts as proof.

4. Quantify: count `delegation_outcomes.jsonl` rows with `seat: "OC"` and `action: "delegated"`
   over the last 7 days (`ts >= now - 7d`). This is the volume that's either genuinely free or a
   hidden leak depending on step 1's answer — report the count either way.

5. Separately, check `core/relay/task_delegation.py`'s `route_task()` and any other seat-routing
   logic in the repo (grep for `preferred_brain`, `route_task`, `seat.*=.*"CC"` fallback patterns)
   for any explicit "if OC/AG unavailable, fall back to CC" logic — if such fallback exists,
   determine whether it has fired recently (check `delegation_outcomes.jsonl` for `action:
   "self_executed"` rows with a `self_execute_rationale` mentioning OC or AG failure) and how
   often over 7 days.

6. Check `core/relay/contact_ag.py`'s `FALLBACK_MODELS` tuple — it includes
   `"claude-sonnet-4-6"` as a listed fallback for AG. Determine: under what conditions does
   `contact_ag()` actually select this fallback (read `_validate_model`/retry logic), and has it
   fired in the last 7 days? If AG has been silently falling back to Claude Sonnet on failures,
   that's Claude MAX spend disguised as an AG (supposedly Gemini/free) call — check
   `delegation_outcomes.jsonl` and any AG dispatch logs for evidence.

## Explicit exclusions
- Do NOT modify any file.
- Do NOT duplicate the timer/script inventory sweep — that's a separate parallel audit. Stay
  focused on model-tier fall-through / mislabeled-as-free spend.
- Report EVERY finding, including low-confidence ones, tagged with confidence and severity.

## Reply path
- Write your findings to the ABSOLUTE deliverable path given to you separately. Lead with the
  single most important answer: is the OC lane's "[off Claude meter]" claim TRUE or FALSE, stated
  in one unambiguous sentence, with the code you read as proof quoted directly.
- Print a one-line verdict starting "AG DONE:".
