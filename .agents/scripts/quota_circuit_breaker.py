#!/usr/bin/env python3
"""
Antigravity Quota Circuit-Breaker Hook Companion Script
Location: /home/john/Thunderbird/.agents/scripts/quota_circuit_breaker.py

Invoked by .agents/hooks.json on Stop / PostInvocation lifecycle events.
Scans hook payload stdin and transcript logs for Google AI Pro / Antigravity
quota exhaustion ("Individual quota reached", "Resets in Xh Ym Zs").

Actions on quota exhaustion:
1. Appends notice to /home/john/Thunderbird/OpsCenter/collaboration/blackboard.md:
   "## AG QUOTA EXHAUSTED [<ISO8601 timestamp>] — resets in <parsed duration> — session going dark now"
2. Dispatches Telegram alert:
   python3 /home/john/Thunderbird/core/relay/wing_relay.py send AG "AG quota exhausted, going dark, resets ~<duration>"
"""

import sys
import json
import re
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BLACKBOARD_PATH = Path("/home/john/Thunderbird/OpsCenter/collaboration/blackboard.md")
WING_RELAY_PATH = Path("/home/john/Thunderbird/core/relay/wing_relay.py")
STDIN_LOG_PATH = Path("/home/john/Thunderbird/logs/ag_hook_stdin_last.json")
DEDUP_LOCK_PATH = Path("/home/john/Thunderbird/logs/ag_quota_last_trigger.json")

QUOTA_PATTERN = re.compile(r"individual\s+quota\s+reached", re.IGNORECASE)
RESETS_IN_PATTERN = re.compile(r"resets\s+in\s+([0-9]+\s*[hmsd](?:\s*[0-9]+\s*[hmsd])*|[^\.\,\;\n\r]+)", re.IGNORECASE)


def log_stdin_payload(raw_input: str, parsed_json: dict):
    """Save raw input payload for schema inspection."""
    try:
        STDIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "raw": raw_input,
            "parsed": parsed_json
        }
        with open(STDIN_LOG_PATH, "w") as f:
            json.dump(rec, f, indent=2)
    except Exception:
        pass


def extract_duration(text: str) -> str:
    """Extract duration string following 'resets in'."""
    match = RESETS_IN_PATTERN.search(text)
    if match:
        dur = match.group(1).strip()
        # Clean up any trailing quote or unwanted text
        dur = re.sub(r'["\'\.\,].*$', '', dur).strip()
        if dur:
            return dur
    return "UNKNOWN"


def search_text_for_quota(text: str) -> tuple[bool, str]:
    """Check text for quota exhaustion signatures and parse duration."""
    if not text:
        return False, "UNKNOWN"
    
    has_quota_str = bool(QUOTA_PATTERN.search(text))
    has_resets_str = "resets in" in text.lower()

    if has_quota_str or has_resets_str:
        duration = extract_duration(text)
        return True, duration

    return False, "UNKNOWN"


def check_transcript_file(file_path: Path) -> tuple[bool, str]:
    """Read recent lines of transcript file to check for quota errors."""
    if not file_path.exists():
        return False, "UNKNOWN"
    try:
        # Read last 100KB of transcript
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            seek_pos = max(0, size - 102400)
            f.seek(seek_pos)
            content = f.read()
            return search_text_for_quota(content)
    except Exception:
        return False, "UNKNOWN"


def is_recently_triggered(cooldown_seconds: int = 60) -> bool:
    """Avoid spamming duplicate blackboard writes if multiple hook events fire concurrently."""
    if DEDUP_LOCK_PATH.exists():
        try:
            data = json.loads(DEDUP_LOCK_PATH.read_text())
            last_ts = data.get("timestamp", 0)
            if (datetime.now(timezone.utc).timestamp() - last_ts) < cooldown_seconds:
                return True
        except Exception:
            pass
    return False


def record_trigger_timestamp():
    """Update deduplication lock file."""
    try:
        DEDUP_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec = {"timestamp": datetime.now(timezone.utc).timestamp()}
        DEDUP_LOCK_PATH.write_text(json.dumps(rec))
    except Exception:
        pass


def execute_circuit_breaker(duration: str):
    """Perform blackboard append and wing relay alert."""
    if is_recently_triggered(60):
        return

    record_trigger_timestamp()
    iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bb_line = f"## AG QUOTA EXHAUSTED [{iso_ts}] — resets in {duration} — session going dark now\n"

    # 1. Append to blackboard.md
    try:
        BLACKBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BLACKBOARD_PATH, "a", encoding="utf-8") as f:
            f.write(bb_line)
    except Exception as e:
        sys.stderr.write(f"Error writing to blackboard: {e}\n")

    # 2. Invoke wing_relay.py CLI
    if WING_RELAY_PATH.exists():
        relay_msg = f"AG quota exhausted, going dark, resets ~{duration}"
        cmd = ["python3", str(WING_RELAY_PATH), "send", "AG", relay_msg]
        try:
            subprocess.run(cmd, timeout=10, check=False)
        except Exception as e:
            sys.stderr.write(f"Error executing wing_relay: {e}\n")


def main():
    raw_input = ""
    parsed_json = {}
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input.strip():
                parsed_json = json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"Error reading stdin JSON: {e}\n")

    log_stdin_payload(raw_input, parsed_json)

    # 1. Search raw input / payload structure
    found, duration = search_text_for_quota(raw_input)

    # 2. Search transcript file if provided in payload
    if not found:
        t_path_str = parsed_json.get("transcriptPath") or parsed_json.get("transcript_path")
        if t_path_str:
            found, duration = check_transcript_file(Path(t_path_str))

    # 3. If found, execute circuit breaker actions
    if found:
        execute_circuit_breaker(duration)

    # Always output valid JSON object for hook contract
    print(json.dumps({}))


if __name__ == "__main__":
    main()
