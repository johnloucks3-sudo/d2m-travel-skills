#!/usr/bin/env python3
"""
Headless Claude Fallback to Claude Code — Layer 2B

If OpenCode's headless spawn fails, this escalates to Claude Code.

Standing Order 24 APR 2026: Fallback mechanism ensures mission continuity.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime


def escalate_to_claude_code(
    task_description: str,
    output_file_path: str,
    task_name: str = "escalated_task",
    model: str = "claude-haiku-4-5-20251001"
) -> dict:
    """
    Escalate headless Claude spawn to Claude Code directly.

    Used when OpenCode's headless dispatch fails with can_retry=True.

    This spawns Claude Code (the CLI) which handles:
    - Full OAuth token management
    - Full environment setup
    - Full error handling

    Args:
        task_description: What Claude should do
        output_file_path: Where to write output
        task_name: Descriptive task name
        model: Claude model to use

    Returns:
        dict with escalation result:
        {
            "status": "ESCALATED_TO_CLAUDE_CODE" | "ESCALATION_FAILED",
            "pid": int (if successful),
            "log_file": str,
            "output_file": str,
            "error": str (if failed)
        }
    """

    logs_dir = Path("/home/john/Thunderbird/logs")
    logs_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"claude_code_escalation_{task_name}_{ts}.log"

    # Build prompt for Claude Code
    prompt = f"""You are performing an escalated task for Commander John Loucks.

ESCALATION REASON: OpenCode headless dispatch failed. This task is now running under Claude Code.

ORIGINAL TASK: {task_description}

INSTRUCTIONS:
1. Complete the task thoroughly and accurately
2. WRITE your complete output to {output_file_path}
3. Do NOT output to stdout or stderr
4. All output must go to {output_file_path}

Begin immediately."""

    # Spawn Claude Code with full CLI
    try:
        with open(log_file, "w") as log_fh:
            proc = subprocess.Popen(
                [
                    "/home/john/.local/bin/claude",
                    "-p", prompt,
                    "--model", model
                ],
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                # ← Note: NOT using start_new_session here because we want Claude Code
                # to manage the session lifecycle itself
            )
    except FileNotFoundError:
        return {
            "status": "ESCALATION_FAILED",
            "error": "Claude Code binary not found at /home/john/.local/bin/claude",
            "log_file": str(log_file)
        }
    except Exception as e:
        return {
            "status": "ESCALATION_FAILED",
            "error": f"Failed to escalate to Claude Code: {e}",
            "log_file": str(log_file)
        }

    return {
        "status": "ESCALATED_TO_CLAUDE_CODE",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": output_file_path,
        "task_name": task_name,
        "model": model
    }


def dispatch_with_fallback(
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    model: str = "claude-haiku-4-5-20251001",
    max_retries: int = 1
) -> dict:
    """
    Dispatch to headless Claude with automatic fallback to Claude Code.

    This is the HIGH-LEVEL API for OpenCode. It:
    1. Tries OpenCode's native dispatch (Layer 2)
    2. If it fails with can_retry=True, tries again (up to max_retries)
    3. If it still fails, escalates to Claude Code (Layer 2B)
    4. If Claude Code escalation fails, returns error

    Args:
        task_description: What Claude should do
        output_file_path: Where to write output
        task_name: Descriptive task name
        model: Claude model to use
        max_retries: How many times to retry before escalating (default: 1)

    Returns:
        dict with final result:
        {
            "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
            "pid": int,
            "log_file": str,
            "output_file": str,
            "error": str (if failed),
            "retries_attempted": int,
            "escalated": bool
        }
    """

    from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

    retries_attempted = 0
    escalated = False

    # Try OpenCode's native dispatch
    while retries_attempted < max_retries:
        result = dispatch_to_headless_claude(
            task_description=task_description,
            output_file_path=output_file_path,
            task_name=task_name,
            model=model
        )

        if result["status"] == "SPAWNED":
            return {
                **result,
                "retries_attempted": retries_attempted,
                "escalated": False
            }

        if not result.get("can_retry"):
            # Fatal error, don't retry
            break

        retries_attempted += 1

    # OpenCode failed. Escalate to Claude Code.
    escalation_result = escalate_to_claude_code(
        task_description=task_description,
        output_file_path=output_file_path,
        task_name=task_name,
        model=model
    )

    if escalation_result["status"] == "ESCALATED_TO_CLAUDE_CODE":
        return {
            **escalation_result,
            "retries_attempted": retries_attempted,
            "escalated": True
        }

    # Both OpenCode and Claude Code failed.
    return {
        "status": "FAILED",
        "error": f"OpenCode dispatch failed ({retries_attempted} retries), Claude Code escalation also failed: {escalation_result.get('error')}",
        "log_file": escalation_result.get("log_file"),
        "retries_attempted": retries_attempted,
        "escalated": True
    }


"""
═════════════════════════════════════════════════════════════════════════════════
OPENCODE: HOW TO USE THE FALLBACK

Instead of:
    from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude
    result = dispatch_to_headless_claude(...)

Use this (with automatic fallback to Claude Code):
    from OpsCenter.headless_claude_fallback import dispatch_with_fallback
    result = dispatch_with_fallback(...)

That's it. The rest is automatic:
- Tries OpenCode dispatch
- Retries if needed
- Falls back to Claude Code if OpenCode fails
- Returns success or final error

═════════════════════════════════════════════════════════════════════════════════
"""


if __name__ == "__main__":
    # Test fallback
    print("Testing headless Claude dispatch with fallback...")
    result = dispatch_with_fallback(
        task_description="List the top 3 luxury cruise lines.",
        output_file_path="/home/john/Thunderbird/output/test_fallback.txt",
        task_name="test_fallback"
    )
    print(json.dumps(result, indent=2))
