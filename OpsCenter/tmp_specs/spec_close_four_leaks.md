# Task: eliminate/minimize Claude MAX OAuth spend across 4 confirmed background sources

## Context

The Commander's Claude MAX 5X quota is shared by everything using `CLAUDE_CODE_OAUTH_TOKEN`
(loaded from `~/.claude/.credentials.json`). Two parallel forensic audits tonight (both by AG)
plus CC's own re-verification confirmed 4 real, currently-open, low-to-medium volume background
leaks. This task closes all four. **You have design latitude here** — this spec states the
objective and known constraints for each item, not a prescribed line-by-line diff. Decide the best
implementation given the real code, and state your reasoning in the deliverable.

**Already closed, do not touch:** `core/ci/self_observability.py`'s `dispatch_remediation()` —
its OAuth-touching attempt-3 auto-spawn fallback was already deleted earlier tonight (a separate
fix), confirmed via 2 historical `self_execute_rationale: "Claude fallback: attempt 3"` rows in
`OpsCenter/delegation_outcomes.jsonl` and zero going forward. Not in scope.

## The four items

### 1. `hooks/claude_oauth_keepalive.sh` — 38 real fires/week, Haiku
Currently runs `claude -p "ok"` every 90 minutes (`claude-oauth-keepalive.timer`) purely to keep
the OAuth token from expiring. This is a genuine, unnecessary spend: read the actual token
freshness requirement — `~/.claude/.credentials.json` likely has an expiry timestamp field (check
its actual JSON structure) — and replace the LLM ping with a local check that reads that field
directly. If the token genuinely needs a live network refresh (not just a read), determine the
correct non-LLM refresh mechanism (Claude Code's own OAuth refresh flow, if one exists outside the
CLI's inference path) rather than spending an inference call just to touch the token.

### 2. `OpsCenter/hale_incident_router.py` — 537 activations/week, real spawn rate UNCONFIRMED
Before touching code: determine the REAL spawn rate first, the same way ci-sentinel's "312" was
corrected down to "2." The file has a documented "stay silent, auto-heal, RULE_1" path (~line 378:
`RULE_1 applied: {service} auto-healed and verified — silent`) that likely means most of the 537
activations spend nothing. Cross-reference `journalctl --user -u hale-incident-handler.service
--since "2026-07-24 00:00"` against actual `spawn_headless_claude` call sites (~line 326-327) to
get a REAL 7-day count of LLM spawns, not just service activations. Report this real number
explicitly and clearly, whatever it turns out to be — even if it means this item was never a real
leak and needs no code change. If it IS a real, meaningful spawn rate: propose and implement the
lowest-risk reduction (route non-urgent/mechanical triage to the free OC/DeepSeek lane via
`core/relay/dispatch_oc.py`'s `dispatch_to_oc()`, following the same pattern already used in
`self_observability.py`'s `dispatch_remediation()` for reference — read that function for the
established pattern in this codebase, but do not modify it).

### 3. `OpsCenter/hale_brain_monitor_12h.py` — 18 fires/week, Haiku, twice-daily
Route this to the free OC/DeepSeek lane the same way, if the task content is mechanical enough
(read what the "brain state evaluation" prompt actually asks for — if it requires Claude-grade
judgment, say so explicitly and leave it, don't force a downgrade that degrades a genuinely
judgment-requiring task; if it's a mechanical state-summary task, route it).

### 4. `OpsCenter/hale_dispatcher.py` (visual-synthesis path only, `hale-visual-synthesis.service`)
— 7 fires/week, Sonnet/Haiku, daily
Same evaluation: read what the visual-synthesis task actually does. If it's data preparation /
formatting rather than creative/judgment work, route to free lane or downgrade model tier. If it
requires genuine visual/creative judgment, say so and leave it — do not blindly downgrade
everything to hit a number.

## Constraints — apply to all four
- **Never actually run** `hooks/claude_oauth_keepalive.sh`,
  `OpsCenter/hale_incident_router.py`, `OpsCenter/hale_brain_monitor_12h.py`, or
  `OpsCenter/hale_dispatcher.py` for real during testing/verification — these can send real
  Telegram messages, real Commander escalations, or real emails. Test any new logic in isolation
  (unit tests with mocked subprocess/file calls, `tempfile.mkdtemp()` for any file I/O), never
  against real state files or real services.
- **Do not restart or re-trigger any live systemd timer/service** as part of verification.
- **Do not touch** `core/ci/self_observability.py` (already fixed, out of scope) or
  `core/relay/dispatch_oc.py` / `core/relay/task_delegation.py` (read-only reference, do not
  modify).
- Preserve every existing function's external interface/return shape unless you have a specific,
  stated reason to change it — other code may call these functions.
- Where you conclude an item is NOT actually worth changing (e.g., item 2 turns out to have a
  real spawn rate near zero, or an item's task genuinely needs Claude judgment), say so plainly in
  the deliverable and make no code change for that item — a correct "leave it" is as valid an
  outcome as a fix, and is exactly the kind of honest finding this Wing's doctrine wants surfaced.

## Acceptance criteria (mechanically checkable — run yourself, for whichever files you touch)
```
python3 -m py_compile <every .py file you touch>
python3 -m pytest <any new/existing test file you touch or add> -q
git status --short hooks/ OpsCenter/hale_incident_router.py OpsCenter/hale_brain_monitor_12h.py OpsCenter/hale_dispatcher.py
```
Report the literal output of all commands you run, for every file you touch.

## Reply path
- Write your changes in place, plus any new test files needed.
- Write a deliverable to the ABSOLUTE path given to you separately: for EACH of the 4 items —
  what you found (including the corrected real spawn rate for item 2), what you changed and why
  (or why you left it unchanged), and literal acceptance-criteria output for anything touched.
- Report every uncertainty, tagged confidence/severity — do not filter for confidence.
- Print a one-line verdict starting "AG DONE:".
