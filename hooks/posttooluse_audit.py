#!/usr/bin/env python3
"""
Thunderbird PostToolUse — Policy Audit Logger (Option 3 Backstop)
=================================================================
Dreams2Memories Travel, LLC

Fires after EVERY tool execution (allowed and blocked) and appends one
JSON line to logs/policy_audit.jsonl.

This is the net under structurally-uncoverable surfaces — browser JS when
not denylisted, unhooked cron/systemd calls, etc.  It is NOT a gate; it
never blocks execution.  It must never raise.

PostToolUse stdin schema (Claude Code hook format):
  {
    "tool_name": "Bash",
    "tool_input": { ... },          # tool arguments
    "tool_response": { ... }        # tool output / error
  }

Output schema (one JSON object per line):
  {
    "ts":       "<ISO-8601>",
    "tool":     "<tool_name>",
    "decision": "ALLOWED",          # PostToolUse = always allowed (gate is PreToolUse)
    "rule_id":  null,
    "excerpt":  "<first 100 chars of primary input field>",
    "session":  "<session id or null>"
  }
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOOK_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOK_DIR.parent
AUDIT_LOG = REPO_ROOT / "logs" / "policy_audit.jsonl"


def _excerpt(tool_input: dict) -> str:
    """Return the first 100 chars of the most meaningful input field."""
    # Priority order: command, code, content, query, prompt, url, path, then first value
    for key in ("command", "code", "content", "query", "prompt", "url", "path"):
        val = tool_input.get(key)
        if val and isinstance(val, str):
            return val[:100]
    # Fallback: first string value in the dict
    for val in tool_input.values():
        if isinstance(val, str) and val:
            return val[:100]
    return ""


def _session_id() -> str | None:
    """Best-effort extraction of the current Claude Code session id."""
    # Claude Code sets CLAUDE_SESSION_ID in the hook environment
    sid = os.environ.get("CLAUDE_SESSION_ID")
    if sid:
        return sid
    # Fallback: check for a session file written by the harness
    session_file = REPO_ROOT / "OpsCenter" / ".session_blast_fingerprint.json"
    try:
        data = json.loads(session_file.read_text())
        return data.get("session_id") or data.get("fingerprint")
    except Exception:
        pass
    return None


def _already_logged(ts: str) -> bool:
    """
    Check whether the last line of policy_audit.jsonl already records this
    exact timestamp (avoids duplicate entries if the hook fires twice for
    the same event, which can happen in some harness versions).
    """
    try:
        if not AUDIT_LOG.exists():
            return False
        # Read the last line efficiently
        with AUDIT_LOG.open("rb") as fh:
            # Seek to end, walk back to find last newline
            fh.seek(0, 2)
            size = fh.tell()
            if size == 0:
                return False
            # Read up to 512 bytes from the end
            read_size = min(512, size)
            fh.seek(-read_size, 2)
            tail = fh.read().decode("utf-8", errors="replace")
        last_line = tail.strip().rsplit("\n", 1)[-1].strip()
        if not last_line:
            return False
        entry = json.loads(last_line)
        return entry.get("ts") == ts
    except Exception:
        return False


def main() -> None:
    # --- 1. Parse stdin -------------------------------------------------------
    try:
        data = json.load(sys.stdin)
    except Exception:
        # Unparseable input — still exit 0
        return

    tool_name = data.get("tool_name") or data.get("tool") or "unknown"
    tool_input = data.get("tool_input") or {}
    # tool_response present but not inspected — this hook only audits, not gates

    # --- 2. Build the audit record -------------------------------------------
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Deduplicate: skip if the last entry has the exact same timestamp
    if _already_logged(ts):
        return

    record = {
        "ts": ts,
        "tool": tool_name,
        "decision": "ALLOWED",  # PostToolUse = execution already happened
        "rule_id": None,
        "excerpt": _excerpt(tool_input),
        "session": _session_id(),
    }

    # --- 3. Append to audit log ----------------------------------------------
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Entry point — wrapped in a blanket try/except so this hook NEVER raises
# ---------------------------------------------------------------------------
try:
    main()
except Exception:
    pass  # Backstop — silent failure is correct behavior

sys.exit(0)
