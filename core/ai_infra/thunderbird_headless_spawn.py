#!/usr/bin/env python3
"""
Thunderbird Headless Claude Spawn Wrapper — FOOLPROOF LAYER 1

This is the ONLY safe way to spawn headless Claude. All agents (OpenCode, Goose, Claude Code)
MUST use this module. Direct subprocess.Popen calls are forbidden.

Enforces ALL 5 mandatory patterns from docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md:
1. Token refresh daemon verification
2. OAuth credentials file verification
3. Haiku supervisor daemon verification
4. OAuth token injection into environment
5. start_new_session=True detachment

CRITICAL: Violations detected by supervisor → escalated to COS
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("thunderbird_headless_spawn")


def verify_prerequisites() -> Dict[str, Any]:
    """
    Verify all 3 mandatory daemon prerequisites before spawning.

    Returns:
        dict with status and details for each check
    """
    results = {}

    # CHECK 1: Token refresh daemon
    token_refresh = subprocess.run(
        ["systemctl", "is-active", "claude-token-refresh.timer"],
        capture_output=True,
        text=True
    )
    results["token_refresh_running"] = token_refresh.returncode == 0
    if not results["token_refresh_running"]:
        results["token_refresh_error"] = "Token refresh daemon inactive. Run: sudo systemctl enable --now claude-token-refresh.timer"

    # CHECK 2: Haiku supervisor daemon
    supervisor = subprocess.run(
        ["systemctl", "is-active", "claude-haiku-supervisor.timer"],
        capture_output=True,
        text=True
    )
    results["supervisor_running"] = supervisor.returncode == 0
    if not results["supervisor_running"]:
        results["supervisor_error"] = "Haiku supervisor inactive. Run: sudo systemctl enable --now claude-haiku-supervisor.timer"

    # CHECK 3: OAuth credentials file
    creds_path = Path.home() / ".claude" / ".credentials.json"
    results["creds_exist"] = creds_path.exists()
    if not results["creds_exist"]:
        results["creds_error"] = f"Credentials file missing at {creds_path}. Have Commander re-authenticate in Claude Desktop."

    results["all_pass"] = all([
        results["token_refresh_running"],
        results["supervisor_running"],
        results["creds_exist"]
    ])

    return results


def load_oauth_token() -> tuple[str, Dict[str, Any]]:
    """
    Load OAuth token from credentials file and build environment dict.

    Returns:
        (token: str, env: dict) where env is dict(os.environ) with token injected

    Raises:
        ValueError if credentials cannot be loaded
    """
    creds_path = Path.home() / ".claude" / ".credentials.json"

    if not creds_path.exists():
        raise ValueError(
            f"Credentials file missing at {creds_path}. "
            "Have Commander re-authenticate in Claude Desktop app."
        )

    try:
        creds = json.loads(creds_path.read_text())
        token = creds.get("claudeAiOauth", {}).get("accessToken")

        if not token:
            raise ValueError("No accessToken in credentials file")

        env = dict(os.environ)
        # CRITICAL: Strip ANTHROPIC_API_KEY to force OAuth from credentials.json
        env.pop("ANTHROPIC_API_KEY", None)
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        return token, env
    except json.JSONDecodeError as e:
        raise ValueError(f"Credentials file corrupted: {e}")


def spawn_headless_claude(
    prompt: str,
    output_file: str,
    model: str = "claude-haiku-4-5-20251001",
    task_name: str = "task"
) -> Dict[str, Any]:
    """
    FOOLPROOF headless Claude spawn wrapper.

    Enforces ALL patterns from docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md.

    Uses stdin/stdout PIPE pattern (NOT -p/--print flag) to enable OAuth authentication.
    The -p flag disables OAuth; we use communicate() instead.

    Args:
        prompt: Complete prompt (WRITE instruction still recommended but not required here)
        output_file: Path where output will be written
        model: Claude model to use (default: haiku-4-5-20251001)
        task_name: Human-readable task name for logging

    Returns:
        dict with status, PID, log_file, output_file, and any errors

    Raises:
        No exceptions. Always returns status dict. Caller must check status field.
    """

    # PRE-SPAWN VERIFICATION (all mandatory)
    logs_dir = Path("/home/john/Thunderbird/logs")
    logs_dir.mkdir(exist_ok=True)

    # Generate unique log file
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"claude_{task_name}_{ts}.log"

    # Verify prerequisites
    prereq_check = verify_prerequisites()
    if not prereq_check["all_pass"]:
        error_msgs = []
        if not prereq_check["token_refresh_running"]:
            error_msgs.append(prereq_check.get("token_refresh_error", "Token refresh daemon down"))
        if not prereq_check["supervisor_running"]:
            error_msgs.append(prereq_check.get("supervisor_error", "Supervisor daemon down"))
        if not prereq_check["creds_exist"]:
            error_msgs.append(prereq_check.get("creds_error", "Credentials missing"))

        return {
            "status": "FATAL_PREREQ",
            "errors": error_msgs,
            "can_retry": False,
            "log_file": str(log_file)
        }

    # Load OAuth token
    try:
        token, env = load_oauth_token()
    except ValueError as e:
        return {
            "status": "FATAL_CREDS",
            "error": str(e),
            "can_retry": False,
            "log_file": str(log_file)
        }

    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Spawn subprocess with stdin/stdout PIPE pattern (OAuth-friendly)
    # This uses communicate() instead of -p flag, which disables OAuth
    try:
        proc = subprocess.Popen(
            [
                "/home/john/.local/bin/claude",
                "--model", model,
                "--output-format", "text"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,  # ← CRITICAL: Detaches process
        )

        # Communicate with the process (sends prompt via stdin)
        stdout, stderr = proc.communicate(input=prompt, timeout=300)

        # Write output to file
        output_path.write_text(stdout)

        # Log any stderr
        if stderr:
            with open(log_file, "w") as f:
                f.write(f"STDERR:\n{stderr}\n\nSTDOUT:\n{stdout}\n")
        else:
            with open(log_file, "w") as f:
                f.write(stdout)

    except FileNotFoundError:
        return {
            "status": "FATAL_BIN",
            "error": "Claude binary not found at /home/john/.local/bin/claude",
            "can_retry": False,
            "log_file": str(log_file)
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "error": "Claude process exceeded 300 second timeout",
            "can_retry": True,
            "log_file": str(log_file)
        }
    except Exception as e:
        return {
            "status": "SPAWN_FAILED",
            "error": f"Failed to spawn subprocess: {e}",
            "can_retry": True,
            "log_file": str(log_file)
        }

    # Success
    logger.info(f"✅ Executed headless Claude for task '{task_name}'")
    logger.info(f"   Model: {model}")
    logger.info(f"   Output: {output_file}")
    logger.info(f"   Logs: {log_file}")

    return {
        "status": "SPAWNED",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": output_file,
        "model": model,
        "task_name": task_name,
        "can_retry": False
    }


if __name__ == "__main__":
    # Quick test
    print("Testing headless spawn wrapper...")
    result = spawn_headless_claude(
        prompt="Say 'Test successful'",
        output_file="/tmp/test_headless_spawn.txt",
        task_name="test"
    )
    print(json.dumps(result, indent=2))
