# M1 Self-Observability Gate Implementation Deliverable

## Change Summary (Points 1–4)
1. **Point 1**: Added `_claude_spend_allowed()` module-level function to check if the 5-hour OAuth usage window is under 85% headroom (reading `~/.claude/hud/.usage-cache.json`), failing closed on any read/parse error.
2. **Point 2**: Inserted a budget guard in `dispatch_remediation()` immediately following `prompt = _fix_prompt(breach)` that routes remediation to OpenCode (`dispatch_to_oc`) or escalates to Hale/Commander when `_claude_spend_allowed()` returns `False`, skipping all Claude inference spend.
3. **Point 3**: Completely removed the automatic `subprocess.Popen` headless Claude spawn in the exception fallback block, replacing it with an escalation-only path calling `notify_hale` and `escalate_to_commander`.
4. **Point 4**: Removed the `record_outcome` call logging `action="self_executed"` from the fallback block as no self-execution occurs upon fallback.

## Acceptance Criteria Command Outputs

1. Command: `python3 -m py_compile core/ci/self_observability.py`
```
Exit code: 0
```

2. Command: `grep -c "_claude_spend_allowed" core/ci/self_observability.py`
```
2
```

3. Command: `grep -c "start_new_session=True" core/ci/self_observability.py`
```
0
```

4. Command: `grep -c "def _claude_spend_allowed" core/ci/self_observability.py`
```
1
```
