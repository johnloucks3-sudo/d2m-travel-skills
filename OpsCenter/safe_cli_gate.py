#!/usr/bin/env python3
"""
safe_cli_gate.py — Thunderbird Wing Safe-CLI Gatekeeper
=======================================================
Validates ExecutionManifests before allowing mcp2cli execution.
Implements the mandatory validation layer between AI agents and direct tool calls.

Architecture : OpsCenter/collaboration/safe_cli_architecture.md
Spec         : OpsCenter/collaboration/claude_gate_spec.md
Policy       : OpsCenter/policy_engine_rules.md
Schema       : OpsCenter/safe_cli_schema.json

Exit codes:
  0  — PASSED, mcp2cli exited 0
  1  — Manifest parse error
  2  — Policy BLOCKED
  3  — mcp2cli binary not found (FAIL-SAFE engaged)
  4  — mcp2cli timeout
  5  — mcp2cli subprocess error
  non-zero from mcp2cli is passed through
"""

import csv
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
STAR_LOG         = THUNDERBIRD_ROOT / "OpsCenter" / "star_protocol_log.csv"
DISSENT_LOG      = THUNDERBIRD_ROOT / "OpsCenter" / "collaboration" / "dissent_log.md"
ENV_TELEGRAM     = THUNDERBIRD_ROOT / ".env.telegram"
MCP2CLI_BIN      = THUNDERBIRD_ROOT / "OpsCenter/node_modules/.bin/mcp2cli"


# ── Telegram ───────────────────────────────────────────────────────────────────
def _load_telegram_env() -> dict:
    env: dict = {}
    if ENV_TELEGRAM.exists():
        for line in ENV_TELEGRAM.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def send_telegram_alert(message: str) -> None:
    """Fire a synchronous Telegram alert to Commander.  Best-effort — never raises."""
    try:
        import requests  # optional dep; graceful degradation if absent
        tenv = _load_telegram_env()
        token   = tenv.get("TELEGRAM_C2_BOT_TOKEN")   or os.environ.get("TELEGRAM_C2_BOT_TOKEN")
        chat_id = tenv.get("TELEGRAM_COMMANDER_ID")    or os.environ.get("TELEGRAM_COMMANDER_ID")
        if not token or not chat_id:
            print("[safe_cli_gate] Telegram creds missing — alert not sent.", file=sys.stderr)
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception as exc:
        print(f"[safe_cli_gate] Telegram alert failed: {exc}", file=sys.stderr)


# ── Audit Logging ─────────────────────────────────────────────────────────────
def log_star_protocol(manifest: dict, verdict: str, reason: str) -> None:
    """Append one row to star_protocol_log.csv.  Always fires — pass or block."""
    STAR_LOG.parent.mkdir(parents=True, exist_ok=True)
    write_header = not STAR_LOG.exists()
    with STAR_LOG.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow([
                "timestamp_utc", "task_id", "originating_agent",
                "requested_tool", "verdict", "reason",
            ])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            manifest.get("task_id", "UNKNOWN"),
            manifest.get("originating_agent", "UNKNOWN"),
            manifest.get("requested_tool", "UNKNOWN"),
            verdict,
            reason,
        ])


def log_dissent(manifest: dict, reason: str) -> None:
    """Append a human-readable dissent entry to dissent_log.md."""
    DISSENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = (
        f"\n## BLOCKED — {ts}\n"
        f"- **task_id:** {manifest.get('task_id', 'UNKNOWN')}\n"
        f"- **agent:** {manifest.get('originating_agent', 'UNKNOWN')}\n"
        f"- **tool:** {manifest.get('requested_tool', 'UNKNOWN')}\n"
        f"- **reason:** {reason}\n"
        f"---\n"
    )
    with DISSENT_LOG.open("a") as fh:
        fh.write(entry)


# ── PII Detection ─────────────────────────────────────────────────────────────
_PII_PATTERNS: dict[str, re.Pattern] = {
    "email":       re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "ssn":         re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ \-]?){13,16}\b"),
    "phone":       re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
}


def _luhn_check(number: str) -> bool:
    """Return True if the digit string passes the Luhn algorithm."""
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def scan_for_pii(arguments: Any) -> list:
    """Return list of PII type labels found in the JSON serialisation of arguments."""
    text = json.dumps(arguments)
    hits: list = []
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            if pii_type == "credit_card":
                # Only flag if at least one candidate passes Luhn
                if any(_luhn_check(m) for m in matches):
                    hits.append(pii_type)
            else:
                hits.append(pii_type)
    return hits


# ── Policy Engine ─────────────────────────────────────────────────────────────
# Whitelist — tools explicitly permitted (fnmatch globs, case-sensitive)
_TOOL_WHITELIST = [
    "calendar*",
    "driveList*",
    "driveRead*",
    "tessGet*",
    "*ReadMessage",
    "*ReadThread",
    "*SearchMessages",
    "*ListDrafts",
    "*ListLabels",
    "*GetProfile",
    "gmailCreateDraft",
    "draftClientEmail",
]

# Blacklist — tools denied unconditionally (fnmatch globs)
_TOOL_BLACKLIST = [
    "*Delete*",
    "*delete*",
    "*Trash*",
    "*trash*",
    "gmailSendEmail",
    "sendClientEmail",
    "*Send*Email",
    "*send*email",
]

# Banned substrings — checked in tool name + full argument text
_BANNED_STRINGS = [
    "Love Group Travel",
    "rm -rf",
]

# "Send" patterns in tool names that are not covered by blacklist globs
_SEND_SUBSTRINGS = ["send", "Send"]

# Valid originating agents
_KNOWN_AGENTS = {"OpenCode", "Claude", "Hale"}


def _matches_any(name: str, patterns: list) -> bool:
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def run_policy_engine(manifest: dict) -> tuple:
    """
    Evaluate the manifest against all policy rules.

    Returns:
        (passed: bool, reason: str)
        passed=True  → execution allowed
        passed=False → execution denied
    """
    tool      = manifest.get("requested_tool", "")
    arguments = manifest.get("arguments", {})
    args_text = json.dumps(arguments)

    # ── 1. Required field presence ──────────────────────────────────────────
    for field in ("task_id", "timestamp", "originating_agent", "requested_tool"):
        if not manifest.get(field):
            return False, f"Manifest missing required field: '{field}'"

    # ── 2. Known agent ─────────────────────────────────────────────────────
    agent = manifest["originating_agent"]
    if agent not in _KNOWN_AGENTS:
        return False, f"Unknown originating_agent: '{agent}'"

    # ── 3. Blacklist (unconditional deny) ──────────────────────────────────
    if _matches_any(tool, _TOOL_BLACKLIST):
        return False, (
            f"Tool '{tool}' matches deny-list — destructive/send operations prohibited"
        )

    # ── 4. Drafts-only send policy ─────────────────────────────────────────
    # Deny any tool whose name contains a send-action substring UNLESS it is
    # already on the whitelist.
    for substr in _SEND_SUBSTRINGS:
        if substr in tool and not _matches_any(tool, _TOOL_WHITELIST):
            return False, (
                f"Tool '{tool}' contains send-action substring '{substr}' "
                f"and is not in the drafts-only whitelist"
            )

    # ── 5. Banned string scan ──────────────────────────────────────────────
    full_text = tool + " " + args_text
    for banned in _BANNED_STRINGS:
        if banned in full_text:
            return False, f"Banned string detected: '{banned}'"

    # ── 6. PII scan on arguments ───────────────────────────────────────────
    pii_hits = scan_for_pii(arguments)
    if pii_hits:
        return False, f"PII detected in arguments: {', '.join(pii_hits)}"

    # ── 7. security_context explicit flags ────────────────────────────────
    sc = manifest.get("security_context", {})
    if sc.get("pii_check") is True and pii_hits:
        return False, "PII gate triggered by security_context.pii_check"

    return True, "PASSED"


# ── Manifest Loading ──────────────────────────────────────────────────────────
def load_manifest() -> dict:
    """
    Load manifest from:
      argv[1] — file path   (if the arg resolves to an existing file)
      argv[1] — raw JSON    (otherwise)
      stdin   — fallback
    """
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        p = Path(arg)
        if p.exists() and p.is_file():
            return json.loads(p.read_text())
        return json.loads(arg)
    return json.load(sys.stdin)


# ── Entry Point ───────────────────────────────────────────────────────────────
def main() -> int:
    # ── Load manifest ──────────────────────────────────────────────────────
    try:
        manifest = load_manifest()
    except (json.JSONDecodeError, FileNotFoundError, ValueError, OSError) as exc:
        msg = f"invalid or missing manifest: {exc}"
        print(json.dumps({"status": "ERROR", "reason": msg}), file=sys.stderr)
        return 1

    # ── Policy engine ──────────────────────────────────────────────────────
    passed, reason = run_policy_engine(manifest)
    verdict = "PASSED" if passed else "BLOCKED"

    # ── Always audit ───────────────────────────────────────────────────────
    log_star_protocol(manifest, verdict, reason)

    # ── Handle block ───────────────────────────────────────────────────────
    if not passed:
        log_dissent(manifest, reason)
        send_telegram_alert(
            f"\U0001f6ab Safe-CLI Gate BLOCKED\n"
            f"Task  : {manifest.get('task_id', 'UNKNOWN')}\n"
            f"Agent : {manifest.get('originating_agent', 'UNKNOWN')}\n"
            f"Tool  : {manifest.get('requested_tool', 'UNKNOWN')}\n"
            f"Reason: {reason}"
        )
        print(json.dumps({"status": "BLOCKED", "reason": reason}), flush=True)
        return 2

    # ── FAIL-SAFE: binary must exist ───────────────────────────────────────
    if not Path(MCP2CLI_BIN).exists():
        err = f"mcp2cli binary not found at {MCP2CLI_BIN} — FAIL-SAFE engaged, all execution disabled"
        log_star_protocol(manifest, "ERROR", err)
        send_telegram_alert(
            f"\u26a0\ufe0f Safe-CLI Gate FAIL-SAFE\n"
            f"mcp2cli not found — execution disabled until human override.\n"
            f"Task: {manifest.get('task_id', 'UNKNOWN')}"
        )
        print(json.dumps({"status": "ERROR", "reason": err}), file=sys.stderr, flush=True)
        return 3

    # ── Execute via mcp2cli ────────────────────────────────────────────────
    tool      = manifest["requested_tool"]
    arguments = manifest.get("arguments", {})
    cmd = [MCP2CLI_BIN, tool, json.dumps(arguments)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = {
            "status":     "OK",
            "task_id":    manifest.get("task_id"),
            "tool":       tool,
            "returncode": result.returncode,
            "stdout":     result.stdout,
            "stderr":     result.stderr,
        }
        print(json.dumps(output), flush=True)
        return result.returncode

    except subprocess.TimeoutExpired:
        err = "mcp2cli execution timed out after 60s"
        log_star_protocol(manifest, "ERROR", err)
        print(json.dumps({"status": "ERROR", "reason": err}), file=sys.stderr, flush=True)
        return 4

    except Exception as exc:
        err = f"mcp2cli subprocess error: {exc}"
        log_star_protocol(manifest, "ERROR", err)
        print(json.dumps({"status": "ERROR", "reason": err}), file=sys.stderr, flush=True)
        return 5


if __name__ == "__main__":
    sys.exit(main())