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
    Verify all mandatory daemon prerequisites before spawning.

    Real daemon names (corrected 2026-05-04):
    - claude-token-monitor.timer (user-level)
    - claude-oauth-keepalive.timer (user-level)
    - thunderbird-watchdog.timer (user-level)

    Returns:
        dict with status and details for each check
    """
    results = {}

    def _check_user_timer(name: str) -> bool:
        out = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True
        )
        return out.returncode == 0

    # CHECK 1: OAuth keepalive (refreshes the access token every ~90 min)
    results["oauth_keepalive_running"] = _check_user_timer("claude-oauth-keepalive.timer")
    if not results["oauth_keepalive_running"]:
        results["oauth_keepalive_error"] = (
            "OAuth keepalive timer inactive. Run: "
            "systemctl --user enable --now claude-oauth-keepalive.timer"
        )

    # CHECK 2: Token monitor (counts token usage, auxiliary)
    results["token_monitor_running"] = _check_user_timer("claude-token-monitor.timer")
    if not results["token_monitor_running"]:
        results["token_monitor_error"] = (
            "Token monitor timer inactive. Run: "
            "systemctl --user enable --now claude-token-monitor.timer"
        )

    # CHECK 3: Thunderbird watchdog (failure detection)
    results["watchdog_running"] = _check_user_timer("thunderbird-watchdog.timer")
    if not results["watchdog_running"]:
        results["watchdog_error"] = (
            "Thunderbird watchdog timer inactive. Run: "
            "systemctl --user enable --now thunderbird-watchdog.timer"
        )

    # CHECK 4: OAuth credentials file
    creds_path = Path.home() / ".claude" / ".credentials.json"
    results["creds_exist"] = creds_path.exists()
    if not results["creds_exist"]:
        results["creds_error"] = (
            f"Credentials file missing at {creds_path}. "
            "Have Commander re-authenticate in Claude Desktop."
        )

    # OAuth keepalive + creds are HARD requirements.
    # Token monitor + watchdog are SOFT (warn but don't block).
    results["hard_pass"] = all([
        results["oauth_keepalive_running"],
        results["creds_exist"]
    ])
    results["all_pass"] = all([
        results["oauth_keepalive_running"],
        results["token_monitor_running"],
        results["watchdog_running"],
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
        # CRITICAL: Strip ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL to force OAuth from credentials.json
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        # Inject room-res.com credentials for hotel rate search tasks
        room_res_email = os.getenv("ROOM_RES_EMAIL")
        room_res_password = os.getenv("ROOM_RES_PASSWORD")
        if room_res_email:
            env["ROOM_RES_EMAIL"] = room_res_email
        if room_res_password:
            env["ROOM_RES_PASSWORD"] = room_res_password

        return token, env
    except json.JSONDecodeError as e:
        raise ValueError(f"Credentials file corrupted: {e}")


def spawn_headless_claude(
    prompt: str,
    output_file: str,
    model: str = "claude-haiku-4-5-20251001",
    task_name: str = "task",
    background: bool = False,
    timeout: int = 300,
    mcp_config: str | None = None,
    extra_args: list[str] | None = None,
    system_prompt: str | None = None,
) -> Dict[str, Any]:
    mcp_config = mcp_config or "/home/john/.claude/mcp.json"
    extra_args = extra_args or []
    """
    FOOLPROOF headless Claude spawn wrapper.

    Two modes:
        background=False (default): SYNCHRONOUS — caller blocks for up to `timeout` seconds.
                                    Returns when output is fully written. Best for short tasks.
        background=True:            ASYNCHRONOUS — caller gets PID immediately and returns.
                                    Output written to output_file by detached subprocess.
                                    Caller must poll output_file or log_file for completion.
                                    Best for long-running builds (>5 min).

    Args:
        prompt: Complete prompt. For background=True, MUST include WRITE [PATH] instruction.
        output_file: Path where output will be written
        model: Claude model name OR alias ('haiku', 'sonnet', 'opus')
        task_name: Human-readable task name for logging
        background: If True, detach and return immediately. If False, block until done.
        timeout: Synchronous mode only. Max seconds to wait. Default 300 (5 min).
        extra_args: Optional list of extra CLI args to append (e.g. ["--json-schema", "{...}"])
        system_prompt: Optional system prompt. If provided, auto-adds ["--system-prompt", system_prompt] to extra_args.

    Returns:
        dict with status, PID, log_file, output_file, and any errors
    """
    if system_prompt:
        extra_args = (extra_args or []) + ["--system-prompt", system_prompt]

    # PRE-SPAWN VERIFICATION
    logs_dir = Path("/home/john/Thunderbird/logs")
    logs_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"claude_{task_name}_{ts}.log"

    # Verify HARD prerequisites only (oauth keepalive + creds)
    # Soft prereqs (token monitor, watchdog) warn but don't block
    prereq_check = verify_prerequisites()
    if not prereq_check["hard_pass"]:
        error_msgs = []
        if not prereq_check["oauth_keepalive_running"]:
            error_msgs.append(prereq_check.get("oauth_keepalive_error", "OAuth keepalive down"))
        if not prereq_check["creds_exist"]:
            error_msgs.append(prereq_check.get("creds_error", "Credentials missing"))

        return {
            "status": "FATAL_PREREQ",
            "errors": error_msgs,
            "can_retry": False,
            "log_file": str(log_file)
        }

    # Soft prereqs: log warnings, don't block
    if not prereq_check.get("token_monitor_running"):
        logger.warning(prereq_check.get("token_monitor_error", "Token monitor not running"))
    if not prereq_check.get("watchdog_running"):
        logger.warning(prereq_check.get("watchdog_error", "Watchdog not running"))

    # Load OAuth token (also strips ANTHROPIC_API_KEY)
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

    # Usage tracking output (for --output-usage flag)
    usage_dir = Path.home() / ".claude" / "projects" / "-home-john"
    usage_dir.mkdir(parents=True, exist_ok=True)
    usage_file = usage_dir / f"usage_{task_name}_{ts}.jsonl"

    if background:
        return _spawn_background(prompt, output_path, log_file, model, task_name, env, usage_file, extra_args, mcp_config)
    else:
        return _spawn_with_retry(prompt, output_path, log_file, model, task_name, env, timeout, usage_file, retries=2, extra_args=extra_args, mcp_config=mcp_config)


def _spawn_with_retry(prompt, output_path, log_file, model, task_name, env, timeout, usage_file, retries=2, attempt=1, extra_args=None, mcp_config=None):
    """Synchronous spawn with retry. retries=2 means 2 retries after initial attempt (3 total)."""
    extra_args = extra_args or []
    mcp_config = mcp_config or "/home/john/.claude/mcp.json"
    result = _spawn_synchronous(prompt, output_path, log_file, model, task_name, env, timeout, usage_file, extra_args, mcp_config)

    if result.get("status") == "COMPLETED":
        # Verify output is non-empty (catch silent failures)
        output_path_obj = Path(output_path)
        if output_path_obj.exists() and output_path_obj.stat().st_size > 0:
            return result
        else:
            result = {"status": "SILENT_FAILURE", "error": "Output file empty or missing", "can_retry": True, "log_file": str(log_file)}

    if result.get("can_retry") and attempt <= retries:
        logger.warning(f"Retry {attempt}/{retries} for {task_name}: {result.get('error', 'unknown error')}")
        # Escalate model tier on retry (haiku -> sonnet -> opus)
        model_tiers = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-7"]
        current = model
        for i, tier in enumerate(model_tiers):
            if tier in model and i + 1 < len(model_tiers):
                current = model_tiers[i + 1]
                logger.info(f"  Escalating model: {model} -> {current}")
                break
        return _spawn_with_retry(prompt, output_path, log_file, current, f"{task_name}_retry{attempt}", env, timeout, usage_file, retries, attempt + 1, extra_args=extra_args, mcp_config=mcp_config)

    return result


def _spawn_synchronous(prompt, output_path, log_file, model, task_name, env, timeout, usage_file, extra_args=None, mcp_config=None):
    """Synchronous spawn — block on communicate() until done or timeout."""
    extra_args = extra_args or []
    mcp_config = mcp_config or "/home/john/.claude/mcp.json"
    claude_bin = "/home/john/.local/bin/claude"
    try:
        cmd = [claude_bin, "--model", model, "--print", "--output-format", "text", "--mcp-config", mcp_config] + extra_args
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        output_path.write_text(stdout)
        with open(log_file, "w") as f:
            if stderr:
                f.write(f"STDERR:\n{stderr}\n\nSTDOUT:\n{stdout}\n")
            else:
                f.write(stdout)
    except FileNotFoundError:
        return {"status": "FATAL_BIN", "error": "Claude binary not found", "can_retry": False, "log_file": str(log_file)}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "error": f"Exceeded {timeout}s timeout", "can_retry": True, "log_file": str(log_file)}
    except Exception as e:
        return {"status": "SPAWN_FAILED", "error": str(e), "can_retry": True, "log_file": str(log_file)}

    logger.info(f"✅ Synchronous spawn complete: {task_name} -> {output_path}")
    return {
        "status": "COMPLETED",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": str(output_path),
        "model": model,
        "task_name": task_name,
        "can_retry": False
    }


def _spawn_background(prompt, output_path, log_file, model, task_name, env, usage_file, extra_args=None, mcp_config=None):
    """Background spawn — return PID immediately, output written by detached subprocess.

    Prompt MUST include 'WRITE [PATH]' instruction so the model writes to file.
    Stdout is redirected to log_file for debugging.
    """
    extra_args = extra_args or []
    mcp_config = mcp_config or "/home/john/.claude/mcp.json"
    # Use -p flag for true background mode (model writes to file via WRITE instruction in prompt)
    # CRITICAL: --mcp-config is REQUIRED. Without it, Claude spins up its own MCP
    # host and may enter D-state (uninterruptible sleep) waiting for connections.
    # The watcher service confirmed this pattern works (2026-05-17).
    claude_bin = "/home/john/.local/bin/claude"
    try:
        cmd = [claude_bin, "-p", prompt, "--model", model, "--output-format", "stream-json", "--mcp-config", mcp_config] + extra_args
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    except FileNotFoundError:
        return {"status": "FATAL_BIN", "error": "Claude binary not found", "can_retry": False, "log_file": str(log_file)}
    except Exception as e:
        return {"status": "SPAWN_FAILED", "error": str(e), "can_retry": True, "log_file": str(log_file)}

    logger.info(f"✅ Background spawn launched: {task_name} (PID {proc.pid}) -> {output_path}")
    return {
        "status": "SPAWNED",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": str(output_path),
        "model": model,
        "task_name": task_name,
        "background": True,
        "can_retry": False,
        "note": "Background mode — caller must poll output_file or log_file for completion."
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
