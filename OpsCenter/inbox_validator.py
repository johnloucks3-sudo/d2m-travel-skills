#!/usr/bin/env python3
"""
inbox_validator.py — Thunderbird Wing Message Routing Validator
===============================================================
Enforces schema on all 4 wing message files. Catches misrouting
at write time so agents never land completions in the wrong inbox.

Called by: thunderbird_tasking_watcher.py on any file change
Can also run standalone: python3 inbox_validator.py --check-all

RULING: DeepSeek (via OpenRouter) + Goose — schema enforcement on
existing 4-file system. No architectural merge. (2026-04-03)
"""

import re
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
log = logging.getLogger("inbox_validator")

BASE   = Path("/home/john/Thunderbird")
COLLAB = BASE / "OpsCenter/collaboration"

# ── File roles — what belongs where ────────────────────────────────────────
FILE_ROLES = {
    "claude_inbox.md": {
        "owner":       "CLAUDE",
        "valid_types": ["TASK", "REQUEST"],
        "valid_from":  ["GOOSE", "COMMANDER", "WATCHER"],
        "valid_to":    ["CLAUDE"],
        "purpose":     "Inbound tasks TO Claude. NEVER write results here.",
    },
    "opencode_inbox.md": {
        "owner":       "OPENCODE",
        "valid_types": ["TASK", "REQUEST", "RESULT"],
        "valid_from":  ["CLAUDE", "COMMANDER", "WATCHER", "NEXUS"],
        "valid_to":    ["OPENCODE"],
        "purpose":     "Inbound tasks TO OpenCode. CLAUDE RESULT entries trigger OpenCode headless.",
    },
    "claude_outbox.md": {
        "owner":       "CLAUDE",
        "valid_types": ["RESULT", "FYI"],
        "valid_from":  ["CLAUDE"],
        "valid_to":    ["OPENCODE", "COMMANDER", "ALL"],
        "purpose":     "Claude's completed work and results. Full path: OpsCenter/collaboration/claude_outbox.md. NEVER write tasks here.",
    },
    "opencode_outbox.md": {
        "owner":       "OPENCODE",
        "valid_types": ["RESULT", "FYI"],
        "valid_from":  ["OPENCODE"],
        "valid_to":    ["CLAUDE", "COMMANDER", "ALL"],
        "purpose":     "OpenCode's completed work. NEVER write tasks here.",
    },
    "wing_comms.md": {
        "owner":       "ALL",
        "valid_types": ["FYI", "REQUEST"],
        "valid_from":  ["CLAUDE", "OPENCODE", "COMMANDER", "WATCHER", "HALE"],
        "valid_to":    ["CLAUDE", "OPENCODE", "COMMANDER", "ALL", "HALE"],
        "purpose":     "FYI and peer requests only. No tasks. No results.",
    },
}

REQUIRED_FIELDS = ["task_id", "from", "to", "type"]

VIOLATION_PATTERNS = [
    # Claude writing completions/results to claude_inbox
    ("claude_inbox.md",  r"deliverable:|completed_at:|status:\s*COMPLETE",
     "RESULT written to claude_inbox — belongs in claude_outbox"),
    # Tasks written to outbox
    ("claude_outbox.md", r"task_type:\s*TASK|priority:\s*CRITICAL|priority:\s*HIGH",
     "TASK written to claude_outbox — belongs in claude_inbox or opencode_inbox"),
    # Results/completions written to wing_comms
    ("wing_comms.md",    r"deliverable:|task_type:\s*TASK",
     "TASK or RESULT in wing_comms — belongs in an inbox or outbox"),
]


def mt_now() -> str:
    return datetime.now(tz=MT).strftime("%Y-%m-%d %H:%M MT")


def validate_file(filename: str, content: str) -> list[dict]:
    """
    Validate a wing message file. Returns list of violations.
    Each violation: {file, severity, message, line}
    """
    violations = []
    role = FILE_ROLES.get(filename)
    if not role:
        return violations  # Unknown file — skip

    # Check for pattern-based misrouting
    for (fname, pattern, msg) in VIOLATION_PATTERNS:
        if fname != filename:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line, re.IGNORECASE):
                violations.append({
                    "file":     filename,
                    "severity": "ERROR",
                    "message":  msg,
                    "line":     i,
                    "content":  line.strip()[:80],
                })

    # Check message blocks for schema compliance
    blocks = re.split(r"\n---\n", content)
    for block in blocks:
        if not block.strip():
            continue

        # Extract from/to/type fields
        from_m = re.search(r"^from:\s*(\S+)", block, re.MULTILINE)
        to_m   = re.search(r"^to:\s*(\S+)",   block, re.MULTILINE)
        type_m = re.search(r"^type:\s*(\S+)",  block, re.MULTILINE)
        tid_m  = re.search(r"^task_id:\s*(\S+)", block, re.MULTILINE)

        if not any([from_m, to_m, type_m, tid_m]):
            continue  # Not a structured block — skip (headers, comments)

        from_val = from_m.group(1).upper() if from_m else None
        to_val   = to_m.group(1).upper()   if to_m   else None
        type_val = type_m.group(1).upper() if type_m else None
        tid_val  = tid_m.group(1)          if tid_m  else "UNKNOWN"

        # Validate 'from' field
        if from_val and role["valid_from"] and from_val not in role["valid_from"]:
            violations.append({
                "file":     filename,
                "severity": "WARNING",
                "message":  f"Task {tid_val}: from={from_val} unexpected in {filename} (expected: {role['valid_from']})",
                "line":     0,
                "content":  f"from: {from_val}",
            })

        # Validate 'to' field
        if to_val and role["valid_to"] and to_val not in role["valid_to"]:
            violations.append({
                "file":     filename,
                "severity": "ERROR",
                "message":  f"Task {tid_val}: to={to_val} WRONG FILE — {filename} is for {role['valid_to']}",
                "line":     0,
                "content":  f"to: {to_val}",
            })

        # Validate 'type' field
        if type_val and role["valid_types"] and type_val not in role["valid_types"]:
            violations.append({
                "file":     filename,
                "severity": "ERROR",
                "message":  f"Task {tid_val}: type={type_val} not valid in {filename} (valid: {role['valid_types']})",
                "line":     0,
                "content":  f"type: {type_val}",
            })

    return violations


def check_file(path: Path) -> list[dict]:
    """Validate a single file by path."""
    if not path.exists():
        return []
    filename = path.name
    if filename not in FILE_ROLES:
        return []
    content = path.read_text()
    return validate_file(filename, content)


def check_all() -> dict[str, list[dict]]:
    """Validate all 4 wing message files."""
    results = {}
    for filename in FILE_ROLES:
        path = COLLAB / filename
        violations = check_file(path)
        results[filename] = violations
    return results


def format_report(results: dict) -> str:
    lines = [f"INBOX VALIDATOR REPORT — {mt_now()}"]
    total_errors = 0
    total_warnings = 0
    for filename, violations in results.items():
        errors   = [v for v in violations if v["severity"] == "ERROR"]
        warnings = [v for v in violations if v["severity"] == "WARNING"]
        total_errors   += len(errors)
        total_warnings += len(warnings)
        status = "✅ CLEAN" if not violations else f"❌ {len(errors)} ERROR(S), {len(warnings)} WARNING(S)"
        lines.append(f"\n{filename}: {status}")
        for v in violations:
            lines.append(f"  [{v['severity']}] Line {v['line']}: {v['message']}")
            lines.append(f"    → {v['content']}")
    lines.append(f"\nTOTAL: {total_errors} errors, {total_warnings} warnings")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    results = check_all()
    report = format_report(results)
    print(report)
    total_errors = sum(len([v for v in vlist if v["severity"] == "ERROR"])
                       for vlist in results.values())
    sys.exit(1 if total_errors else 0)
