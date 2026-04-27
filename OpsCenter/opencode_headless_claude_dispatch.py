#!/usr/bin/env python3
"""
OpenCode Headless Claude Dispatch Wrapper — LAYER 2

OpenCode MUST use this module exclusively for spawning headless Claude.
This enforces the prompt format with mandatory WRITE [PATH] instruction.

DO NOT call subprocess.Popen directly. Use this wrapper.

Standing Order 2026-04-24: Violations flagged by supervisor → escalated to COS
"""

import sys
import json
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude


def dispatch_to_headless_claude(
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    model: str = "claude-haiku-4-5-20251001"
) -> dict:
    """
    OpenCode MUST use this to spawn headless Claude.

    Wraps thunderbird_headless_spawn.spawn_headless_claude() and enforces:
    - Prompt format with mandatory WRITE [PATH] instruction
    - Proper task naming for logging
    - Error handling specific to OpenCode workflows

    Args:
        task_description: What Claude should do (e.g., "Analyze customer data")
        output_file_path: Where to write output (e.g., "/home/john/Thunderbird/output/analysis.txt")
        task_name: Descriptive name for logging (default: "opencode_task")
        model: Claude model (default: haiku-4-5-20251001)

    Returns:
        dict with spawn result:
        {
            "status": "SPAWNED" | "FATAL_*" | "SPAWN_FAILED",
            "pid": int (if SPAWNED),
            "output_file": str,
            "log_file": str,
            "error": str (if failed),
            "can_retry": bool
        }

    Raises:
        RuntimeError if status is not SPAWNED and can_retry=False

    Example:
        result = dispatch_to_headless_claude(
            task_description="Summarize the top cruise lines by customer rating",
            output_file_path="/home/john/Thunderbird/output/cruise_analysis.txt",
            task_name="cruise_analysis_opencode"
        )

        if result["status"] == "SPAWNED":
            print(f"Task running as PID {result['pid']}")
            print(f"Output will be in: {result['output_file']}")
        else:
            print(f"Failed to spawn: {result.get('error')}")
    """

    # ENFORCE: Build prompt with mandatory WRITE instruction
    prompt = f"""You are performing a task for Commander John Loucks of Dreams2Memories Travel, LLC.

TASK: {task_description}

INSTRUCTIONS:
1. Complete the task thoroughly and accurately
2. WRITE your complete output to {output_file_path}
3. Do NOT output anything to stdout or stderr
4. All output must go to {output_file_path}

Begin."""

    # Dispatch to foolproof spawn wrapper (uses stdin/stdout PIPE pattern)
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=output_file_path,
        model=model,
        task_name=task_name
    )

    # Handle fatal errors
    if result["status"] in ["FATAL_PREREQ", "FATAL_CREDS", "FATAL_BIN"] and not result.get("can_retry"):
        error_detail = result.get("error") or result.get("errors", ["Unknown error"])
        if isinstance(error_detail, list):
            error_detail = "; ".join(error_detail)
        raise RuntimeError(
            f"Cannot spawn headless Claude: {error_detail}\n"
            f"Check logs at {result.get('log_file')}"
        )

    return result


if __name__ == "__main__":
    # Test dispatch
    print("Testing OpenCode headless dispatch...")
    try:
        result = dispatch_to_headless_claude(
            task_description="List the top 3 luxury cruise lines and why they are popular.",
            output_file_path="/home/john/Thunderbird/output/test_opencode_dispatch.txt",
            task_name="test_opencode"
        )
        print(json.dumps(result, indent=2))
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
