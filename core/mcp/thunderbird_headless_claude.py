#!/usr/bin/env python3
"""
Thunderbird Headless Claude MCP Tools Integration

Registers two MCP tools for spawning long-running headless Claude tasks:
1. headless_claude_task — High-level task execution with auto-retries
2. headless_claude_spawn — Low-level spawn control with full parameter customization

Both tools use the foolproof spawn wrapper (thunderbird_headless_spawn.py) which enforces
all mandatory patterns from docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md.

These tools are intended for use by:
- OpenCode agents (via OpsCenter/opencode_headless_claude_dispatch.py)
- Claude Code headless workflows
- Goose automation tasks
- Any agent needing to spawn long-running Claude processes

Usage:
    from thunderbird_headless_claude import register_headless_claude_tools
    register_headless_claude_tools(mcp_server)

The MCP tools will then be available as:
    - call_tool("headless_claude_task", {...})
    - call_tool("headless_claude_spawn", {...})
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# Import the foolproof spawn wrapper
import sys
from pathlib import Path
_parent = Path(__file__).parent.parent
if str(_parent / "ai_infra") not in sys.path:
    sys.path.insert(0, str(_parent / "ai_infra"))

try:
    from thunderbird_headless_spawn import spawn_headless_claude
except ImportError:
    # Fallback: try with parent directory in path
    sys.path.insert(0, str(_parent))
    from thunderbird_headless_spawn import spawn_headless_claude

logger = logging.getLogger("thunderbird_headless_claude_mcp")


class HeadlessClaudeTaskRequest(BaseModel):
    """Request model for high-level headless Claude task execution"""
    task_description: str = Field(
        ...,
        description="Complete description of what Claude should do. Must be a full task description, not a code snippet."
    )
    output_path: str = Field(
        ...,
        description="Full path where Claude will write the output file (e.g., '/home/john/Thunderbird/output/analysis.txt')"
    )
    task_name: str = Field(
        ...,
        description="Short identifier for the task, used for logging and monitoring (e.g., 'market_analysis', 'competitor_research')"
    )
    model: str = Field(
        default="claude-opus-4-6",
        description="Claude model to use: 'claude-opus-4-6', 'claude-sonnet-4-6', or 'claude-haiku-4-5-20251001'"
    )
    max_retries: int = Field(
        default=1,
        description="Number of times to retry if spawn fails (0 = no retries)"
    )


class HeadlessClaudeSpawnRequest(BaseModel):
    """Request model for low-level headless Claude spawn control"""
    prompt: str = Field(
        ...,
        description="Complete prompt for Claude. MUST include explicit 'WRITE [PATH]' instruction or output will be lost."
    )
    output_file: str = Field(
        ...,
        description="Full path where Claude will write output (same path as in WRITE instruction in prompt)"
    )
    model: str = Field(
        default="claude-opus-4-6",
        description="Claude model: 'claude-opus-4-6', 'claude-sonnet-4-6', or 'claude-haiku-4-5-20251001'"
    )
    task_name: str = Field(
        default="headless_task",
        description="Short identifier for logging (e.g., 'market_sweep')"
    )


def register_headless_claude_tools(mcp: Any) -> None:
    """
    Register headless Claude tools with the MCP server.

    Args:
        mcp: FastMCP server instance (e.g., from mcp.server.fastmcp.FastMCP)

    Returns:
        None (registers tools in-place on the mcp instance)

    Raises:
        Exception: Propagates any registration errors
    """

    @mcp.tool(
        name="headless_claude_task",
        annotations={
            "title": "Execute Headless Claude Task",
            "description": "Spawn a long-running Claude task with automatic retry and error handling"
        }
    )
    async def headless_claude_task(
        task_description: str,
        output_path: str,
        task_name: str,
        model: str = "claude-opus-4-6",
        max_retries: int = 1
    ) -> str:
        """
        High-level headless Claude task execution with retries and error handling.

        This tool automatically:
        1. Builds a complete prompt from the task description
        2. Includes explicit WRITE [output_path] instruction (prevents silent output loss)
        3. Verifies all prerequisites (token daemon, supervisor, credentials)
        4. Spawns Claude as a detached background process
        5. Retries on failure (up to max_retries times)
        6. Returns structured status with PID, log file, and output path

        Args:
            task_description: What Claude should do (e.g., "Analyze Q2 cruise demand trends by destination")
            output_path: Full path for output file (e.g., "/home/john/Thunderbird/output/q2_analysis.txt")
            task_name: Short identifier for logging (e.g., "q2_cruise_analysis")
            model: Claude model to use (default: claude-opus-4-6)
            max_retries: Retry attempts if spawn fails (default: 1)

        Returns:
            JSON string with fields:
            {
                "status": "SPAWNED" | "ESCALATED_TO_CLAUDE_CODE" | "FAILED",
                "pid": int or null,
                "output_file": str,
                "log_file": str,
                "task_name": str,
                "model": str,
                "timestamp": ISO string,
                "error": str (if failed)
            }

        Example:
            >>> result = await headless_claude_task(
            ...     task_description="Analyze hotel pricing for luxury properties in Q2 2026",
            ...     output_path="/home/john/Thunderbird/output/hotel_analysis_q2.txt",
            ...     task_name="hotel_q2_analysis"
            ... )
            >>> result_dict = json.loads(result)
            >>> if result_dict["status"] == "SPAWNED":
            ...     print(f"Task running (PID {result_dict['pid']})")
            ...     print(f"Output will be at: {result_dict['output_file']}")
        """
        log_dir = Path("/home/john/Thunderbird/logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"headless_{task_name}_{timestamp}.log"

        # Build a complete prompt with explicit WRITE instruction
        full_prompt = f"""You are performing a task for Commander John Loucks of Dreams2Memories Travel, LLC.

TASK: {task_description}

CRITICAL INSTRUCTION:
You must WRITE your complete output to the file: {output_path}

Format your output clearly and completely. Do NOT output to stdout.
All output goes to {output_path}.
"""

        # Attempt to spawn with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = spawn_headless_claude(
                    prompt=full_prompt,
                    output_file=str(output_path),
                    model=model,
                    task_name=task_name
                )

                # Success
                if result.get("status") == "SPAWNED":
                    logger.info(f"Task {task_name} spawned successfully (PID {result['pid']})")
                    return json.dumps({
                        "status": "SPAWNED",
                        "pid": result.get("pid"),
                        "output_file": str(output_path),
                        "log_file": str(result.get("log_file", log_file)),
                        "task_name": task_name,
                        "model": model,
                        "timestamp": datetime.now().isoformat(),
                        "attempt": attempt + 1
                    }, indent=2)

                # Failure
                last_error = result.get("error", "Unknown error")
                logger.warning(f"Spawn attempt {attempt + 1}/{max_retries + 1} failed: {last_error}")

                if attempt < max_retries:
                    continue
                else:
                    break

            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception during spawn (attempt {attempt + 1}): {last_error}")
                if attempt >= max_retries:
                    break

        # All retries exhausted
        logger.error(f"Task {task_name} failed after {max_retries + 1} attempts")
        return json.dumps({
            "status": "FAILED",
            "error": last_error,
            "task_name": task_name,
            "model": model,
            "output_file": str(output_path),
            "log_file": str(log_file),
            "timestamp": datetime.now().isoformat(),
            "retries_attempted": max_retries + 1
        }, indent=2)

    @mcp.tool(
        name="headless_claude_spawn",
        annotations={
            "title": "Low-Level Headless Claude Spawn",
            "description": "Direct spawn control for advanced use cases with custom prompts and parameters"
        }
    )
    async def headless_claude_spawn(
        prompt: str,
        output_file: str,
        model: str = "claude-opus-4-6",
        task_name: str = "headless_task"
    ) -> str:
        """
        Low-level headless Claude spawn with full parameter control.

        Use this tool when you need:
        - Custom prompts (not auto-generated from task description)
        - Specific model selection
        - Advanced control over spawn parameters

        CRITICAL: Your prompt MUST include explicit 'WRITE [PATH]' instruction,
        where [PATH] matches the output_file parameter. Without this instruction,
        Claude's output will be lost.

        Args:
            prompt: Complete prompt for Claude (MUST include WRITE [output_file] instruction)
            output_file: Full path where Claude writes output
            model: Claude model (default: claude-opus-4-6)
            task_name: Identifier for logging (default: headless_task)

        Returns:
            JSON string with:
            {
                "status": "SPAWNED" | "FAILED",
                "pid": int or null,
                "output_file": str,
                "log_file": str,
                "task_name": str,
                "model": str,
                "timestamp": ISO string,
                "error": str (if failed)
            }

        Example with custom prompt:
            >>> custom_prompt = '''
            ... Analyze the attached customer data.
            ... Identify top 5 trends.
            ... WRITE output to /home/john/Thunderbird/output/trends.txt
            ... '''
            >>> result = await headless_claude_spawn(
            ...     prompt=custom_prompt,
            ...     output_file="/home/john/Thunderbird/output/trends.txt",
            ...     model="claude-sonnet-4-6",
            ...     task_name="trend_analysis"
            ... )
        """
        try:
            # Verify prompt includes WRITE instruction
            if "WRITE" not in prompt.upper():
                logger.warning(f"Prompt for {task_name} may not include WRITE instruction — output could be lost")

            # Spawn Claude
            result = spawn_headless_claude(
                prompt=prompt,
                output_file=output_file,
                model=model,
                task_name=task_name
            )

            if result.get("status") == "SPAWNED":
                logger.info(f"Task {task_name} spawned (PID {result['pid']})")
                return json.dumps({
                    "status": "SPAWNED",
                    "pid": result.get("pid"),
                    "output_file": output_file,
                    "log_file": str(result.get("log_file", "")),
                    "task_name": task_name,
                    "model": model,
                    "timestamp": datetime.now().isoformat()
                }, indent=2)
            else:
                error = result.get("error", "Unknown spawn error")
                logger.error(f"Spawn failed for {task_name}: {error}")
                return json.dumps({
                    "status": "FAILED",
                    "error": error,
                    "output_file": output_file,
                    "log_file": str(result.get("log_file", "")),
                    "task_name": task_name,
                    "model": model,
                    "timestamp": datetime.now().isoformat()
                }, indent=2)

        except Exception as e:
            logger.error(f"Exception in spawn for {task_name}: {str(e)}")
            return json.dumps({
                "status": "FAILED",
                "error": str(e),
                "output_file": output_file,
                "task_name": task_name,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }, indent=2)

    logger.info("Headless Claude MCP tools registered: headless_claude_task, headless_claude_spawn")
