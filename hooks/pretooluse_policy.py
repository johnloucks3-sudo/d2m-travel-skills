#!/usr/bin/env python3
"""
Wing Policy Engine — PreToolUse hook for Claude Code.
Intercepts Bash, Edit/Write/MultiEdit, browser MCP, and Gmail MCP calls
BEFORE they execute. Fails CLOSED: any error = DENY (exit 2).

Hook signal protocol (Claude Code):
  ALLOW: sys.exit(0) with no output
  DENY:  sys.stderr.write(message) + sys.exit(2)

Do NOT use exit(1) — Claude Code treats that as a non-blocking error (fail-OPEN).

Implementation notes (fail-closed correctness):
  * The wing_policy import lives INSIDE the guarded try. If the engine or its
    registry is broken, the import raises here and we DENY (exit 2) — never the
    code-1 traceback that would fail OPEN.
  * sys.exit() is called exactly ONCE, at module bottom, OUTSIDE every try, so a
    SystemExit (a BaseException) can never be swallowed by an `except Exception`
    and mis-routed into the deny path.
  * stdin field mapping: Claude Code gives {tool_name, tool_input{...}}. The
    policy registry reads ctx["tool"], ctx["command"], ctx["recipient"], etc.,
    so we translate explicitly — a verbatim pass-through would never populate
    `recipient` from a Gmail draft's `to`, and the client-send gate would not
    fire.
"""

import json
import os
import sys
import time

REPO_ROOT = "/home/john/Thunderbird"
_AUDIT_LOG = os.path.join(REPO_ROOT, "logs", "policy_audit.jsonl")

# Make the engine importable regardless of cwd. Doing this at top level is safe
# (no I/O, no exceptions); the actual import is inside the guarded try below.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _hook_audit(tool, decision, rule_id, command_excerpt):
    """Best-effort audit line. NEVER raises, NEVER changes the exit code."""
    try:
        os.makedirs(os.path.dirname(_AUDIT_LOG), exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": "pretooluse_hook",
            "tool": tool,
            "decision": decision,
            "rule_id": rule_id,
            "command_excerpt": (command_excerpt or "")[:100],
        }
        with open(_AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        # The audit path is best-effort. A logging failure must never open the gate.
        return


def _build_ctx(data):
    """
    Translate a Claude Code PreToolUse payload into the action_ctx dict the
    wing_policy registry expects. All access is defensive — a minimal or
    malformed payload yields a benign ctx, never an exception.
    """
    tool_name = ""
    tool_input = {}
    if isinstance(data, dict):
        tool_name = data.get("tool_name") or data.get("tool") or ""
        ti = data.get("tool_input")
        if isinstance(ti, dict):
            tool_input = ti

    def _g(*keys):
        for k in keys:
            v = tool_input.get(k)
            if isinstance(v, str) and v.strip():
                return v
            if v not in (None, "", {}, []):
                return v
        return None

    ctx = {
        "tool": tool_name,
        "platform": "claude_code",
    }

    # Bash
    command = _g("command")
    if command is not None:
        ctx["command"] = command

    # Edit / Write / MultiEdit / NotebookEdit — target path
    file_path = _g("file_path", "path", "notebook_path", "filePath")
    if file_path is not None:
        ctx["file_path"] = file_path

    # Browser navigation
    url = _g("url")
    if url is not None:
        ctx["url"] = url

    # Gmail / email MCP — recipient + body, under any of the common param names
    recipient = _g("recipient", "to", "toAddress", "email", "send_to")
    if recipient is not None:
        # Gmail "to" can be a list — normalize to a comma-joined string
        if isinstance(recipient, (list, tuple)):
            recipient = ",".join(str(x) for x in recipient if x)
        ctx["recipient"] = recipient

    payload = _g("payload", "body", "text", "message", "content", "html")
    if payload is not None:
        ctx["payload"] = payload

    return ctx


def _excerpt_for_audit(ctx):
    for k in ("command", "file_path", "url", "recipient"):
        v = ctx.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def _evaluate():
    """
    Returns (exit_code, stderr_message). NEVER calls sys.exit.
    On ANY failure path, returns the DENY signal (exit 2). This is the entire
    fail-closed surface — every branch that is not a confirmed ALLOW denies.
    """
    # --- read + parse stdin (fail closed on bad/empty input) ---
    try:
        raw = sys.stdin.read()
    except Exception as e:
        return 2, f"[WING POLICY] BLOCKED: failed to read tool invocation ({e!r})"

    if not raw or not raw.strip():
        # PreToolUse always provides JSON. Empty stdin is an anomaly → DENY.
        _hook_audit("?", "DENY", "HOOK-EMPTY-STDIN", "")
        return 2, "[WING POLICY] BLOCKED: empty tool invocation payload (fail-closed)"

    try:
        data = json.loads(raw)
    except Exception as e:
        _hook_audit("?", "DENY", "HOOK-BAD-JSON", raw[:100])
        return 2, f"[WING POLICY] BLOCKED: malformed tool invocation JSON ({e!r})"

    # --- build context (defensive; should not raise) ---
    try:
        ctx = _build_ctx(data)
    except Exception as e:
        _hook_audit("?", "DENY", "HOOK-CTX-ERROR", "")
        return 2, f"[WING POLICY] BLOCKED: could not build policy context ({e!r})"

    excerpt = _excerpt_for_audit(ctx)
    tool = ctx.get("tool", "?")

    # --- import + invoke the engine (fail closed on import OR runtime error) ---
    try:
        from core.policy.wing_policy import check
        result = check(ctx)
    except Exception as e:
        # Engine unimportable or threw despite its own guards → DENY.
        _hook_audit(tool, "DENY", "POLICY-ENGINE-UNAVAILABLE", excerpt)
        return 2, f"[WING POLICY] BLOCKED: policy engine unavailable, failing closed ({e!r})"

    # --- interpret the result ---
    try:
        allowed = bool(getattr(result, "allowed"))
        decision = getattr(result, "decision", "UNKNOWN")
        rule_id = getattr(result, "rule_id", None)
        message = getattr(result, "message", "") or "blocked by policy"
    except Exception as e:
        _hook_audit(tool, "DENY", "POLICY-RESULT-MALFORMED", excerpt)
        return 2, f"[WING POLICY] BLOCKED: malformed policy result, failing closed ({e!r})"

    _hook_audit(tool, decision if allowed else f"BLOCK/{decision}", rule_id, excerpt)

    if allowed:
        return 0, None

    # allowed is False → DENY or GATE. A PreToolUse hook cannot run an
    # interactive Commander approval, so both surface-and-block here.
    return 2, f"[WING POLICY] BLOCKED: {message}"


# ---------------------------------------------------------------------------
# Single exit point — OUTSIDE every try so SystemExit is never swallowed.
# The outermost guard guarantees that even an unexpected failure in _evaluate
# itself produces a DENY (exit 2), never a bare traceback (exit 1, fail-open).
# ---------------------------------------------------------------------------
_exit_code = 2
_stderr_msg = "[WING POLICY] BLOCKED: hook failed closed (unhandled)"
try:
    _exit_code, _stderr_msg = _evaluate()
except BaseException as _e:  # noqa: BLE001 — fail closed on absolutely everything
    _exit_code = 2
    _stderr_msg = f"[WING POLICY] BLOCKED: hook fault, failing closed ({_e!r})"

if _stderr_msg:
    try:
        sys.stderr.write(_stderr_msg + "\n")
    except Exception:
        pass

sys.exit(_exit_code)
