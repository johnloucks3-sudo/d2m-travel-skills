# Task: gate automatic Claude spend in core/ci/self_observability.py

## Context
`dispatch_remediation(breach: dict) -> dict` in `/home/john/Thunderbird/core/ci/self_observability.py`
(function starts at the `def dispatch_remediation` line, currently ~line 337) can spend Claude
inference automatically with NO check on how much of the 5-hour rolling OAuth usage window is
left. Tonight that window is at 92%. A separate module (`oc_worker.py`) states "Claude fallback
is DELIBERATELY not automatic" — but `self_observability.py`'s attempt-3 fallback DOES spawn a
headless Claude process automatically via `subprocess.Popen`. These two policies contradict each
other. Resolve the contradiction in favor of `oc_worker.py`: no automatic Claude spawn, ever.

## Changes required (exact)

1. Add a new module-level function, placed near the top of the file after the existing imports,
   before `dispatch_remediation`:

   ```python
   def _claude_spend_allowed() -> bool:
       """Fail-closed guard: True only if the 5-hour OAuth usage window has headroom.
       Reads the SAME live usage cache the Commander's status bar reads. Any failure
       to read/parse it, or a missing figure, or a reported error, means NOT allowed —
       never default to permissive on a broken read."""
       import json as _json
       from pathlib import Path as _Path
       cache_path = _Path.home() / ".claude" / "hud" / ".usage-cache.json"
       try:
           raw = _json.loads(cache_path.read_text())
       except Exception:
           return False
       if raw.get("error"):
           return False
       five_hour = raw.get("data", {}).get("fiveHour")
       if five_hour is None:
           return False
       return five_hour < 85
   ```

2. In `dispatch_remediation`, immediately after the line `prompt = _fix_prompt(breach)` and
   BEFORE the existing `try:` block that calls the managed agent (the block starting
   `import concurrent.futures` / `from core.ai_infra.managed_agent_client import WingAgentClient`),
   insert a guard that skips ALL Claude spend (both the managed-agent strike AND the fallback)
   when `_claude_spend_allowed()` is False:

   ```python
   if not _claude_spend_allowed():
       try:
           from core.relay.dispatch_oc import dispatch_to_oc
           tid = f"ci-fix-{unit}-{u_st['attempts']}"
           res = dispatch_to_oc(
               task=prompt,
               acceptance_criteria=f"Service {unit} is no longer crash-looping or error-spiking.",
               ticket_id=tid,
               task_type="ci-remediation",
           )
           return {"unit": unit, "dispatched": True, "via": "oc_async_budget_guard",
                   "ticket_id": res.get("ticket_id")}
       except Exception as oc_e:
           notify_hale("CLAUDE_BUDGET_GUARD_BLOCKED", unit,
                       f"5h usage guard blocked auto-Claude spend; OC dispatch also failed: {oc_e}")
           return {"unit": unit, "dispatched": False, "escalate": True,
                   "error": f"claude_budget_guard_active; oc_dispatch_failed: {oc_e}"}
   ```

   (`notify_hale` is already defined later in this same module — Python resolves it fine at
   call time since the module is fully loaded before `dispatch_remediation` ever runs.)

3. In the existing exception-fallback block (the `except Exception as e:` block that currently,
   on the FINAL allowed attempt, builds a `subprocess.Popen([...])` call to spawn a headless
   Claude process with `--model sonnet` and `start_new_session=True`) — DELETE that automatic
   spawn entirely. Replace it with an escalation-only path: write the same `out` report-path
   scaffold, call `notify_hale(...)` and the existing `escalate_to_commander(unit, ...)` helper
   (already used elsewhere in this file — reuse it, do not reinvent it), and return
   `{"unit": unit, "dispatched": False, "escalate": True, "error": str(e), "report": str(out)}`.
   No code path in this function may call `subprocess.Popen` targeting a Claude process, under
   any circumstance, after this change.

4. Update the existing `record_outcome(...)` call in that same fallback block: it currently logs
   `action="self_executed"`. Since no self-execution happens anymore, either remove this specific
   call or change its `action`/`self_execute_rationale` to accurately describe an escalation, not
   a self-execute. Check `core/staffing/delegation_outcomes.py` for the set of valid `action`
   values before choosing — do not invent a new enum value it does not already support; if none
   fits cleanly, it is acceptable to drop this particular `record_outcome` call rather than log a
   false label.

## Explicit exclusions
- Do NOT touch any other function in this file.
- Do NOT modify `core/relay/dispatch_oc.py`, `core/staffing/delegation_outcomes.py`, or any file
  outside `core/ci/self_observability.py`.
- Do NOT run this file's real remediation logic against any live systemd unit or send any real
  Telegram/managed-agent/Commander-escalation call while testing. Testing must be static
  (compile + grep checks) plus, if you write a unit test, it must call `_claude_spend_allowed()`
  directly with a MONKEYPATCHED cache path pointed at a file under `tempfile.mkdtemp()` — never
  read-then-assert against, and never write to, the real
  `~/.claude/hud/.usage-cache.json`.

## Acceptance criteria (mechanically checkable — run these yourself before reporting done)
Run from `/home/john/Thunderbird`:
```
python3 -m py_compile core/ci/self_observability.py          # must exit 0
grep -c "_claude_spend_allowed" core/ci/self_observability.py  # must print 2 or more (defined + called)
grep -c "start_new_session=True" core/ci/self_observability.py # must print 0 (auto-spawn removed)
grep -c "def _claude_spend_allowed" core/ci/self_observability.py  # must print 1
```
Report the literal output of all four commands. If any does not match, the work is not done —
say so plainly rather than reporting success.

## Reply path
- Write your full modified file in place at `/home/john/Thunderbird/core/ci/self_observability.py`
  (absolute path — this is inside the repo you were given via `--add-dir`, not your sandbox).
- Also write a short deliverable to the ABSOLUTE path given to you separately, containing: the
  literal output of the four acceptance-criteria commands above, and a one-line summary of what
  changed at each of the numbered points 1–4.
- Print a one-line verdict starting "AG DONE:".
