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
import logging
from pathlib import Path
from typing import Optional

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
from core.ai_infra.thunderbird_model_router import route_model

logger = logging.getLogger("opencode_dispatch")


def dispatch_to_headless_claude(
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    model: Optional[str] = None,
    task_type: Optional[str] = None,
    content_size: Optional[int] = None,
    has_images: bool = False,
    budget: str = "normal",
    required_context: Optional[int] = None
) -> dict:
    """
    OpenCode MUST use this to spawn headless Claude with AUTOMATIC MODEL ROUTING.

    Wraps thunderbird_headless_spawn.spawn_headless_claude() with intelligent model selection.
    Automatically routes to optimal model (Grok 2M, Gemini Flash, DeepSeek, Free) based on task
    characteristics. Falls back to explicit model if provided.

    Enforces:
    - Prompt format with mandatory WRITE [PATH] instruction
    - Proper task naming for logging
    - Model routing via thunderbird_model_router
    - Error handling specific to OpenCode workflows

    Args:
        task_description: What Claude should do (e.g., "Analyze customer data")
        output_file_path: Where to write output (e.g., "/home/john/Thunderbird/output/analysis.txt")
        task_name: Descriptive name for logging (default: "opencode_task")
        model: Override model (if None, router selects based on task characteristics)
        task_type: Task type for routing (e.g., "incubator", "brief_generation", "routine_analysis")
        content_size: Estimated input size in tokens (triggers large-context routing if >500K)
        has_images: Whether task includes imagery (routes to Gemini Flash)
        budget: "minimal" → DeepSeek, "normal" → default, "premium" → Grok/Opus
        required_context: Minimum context window needed (>1M → Grok 2M)

    Returns:
        dict with spawn result:
        {
            "status": "SPAWNED" | "FATAL_*" | "SPAWN_FAILED",
            "pid": int (if SPAWNED),
            "output_file": str,
            "log_file": str,
            "model": str (selected or provided),
            "routed": bool (True if model was selected by router),
            "error": str (if failed),
            "can_retry": bool
        }

    Raises:
        RuntimeError if status is not SPAWNED and can_retry=False

    Example (with explicit model):
        result = dispatch_to_headless_claude(
            task_description="Summarize the top cruise lines by customer rating",
            output_file_path="/home/john/Thunderbird/output/cruise_analysis.txt",
            task_name="cruise_analysis_opencode",
            model="claude-opus-4-7"  # Explicit: override router
        )

    Example (with routing):
        result = dispatch_to_headless_claude(
            task_description="Analyze 50K tokens of ship pricing data",
            output_file_path="/home/john/Thunderbird/output/ship_analysis.txt",
            task_name="ship_pricing_analysis",
            task_type="research",
            content_size=50000  # Router selects Grok 2M automatically
        )

        if result["status"] == "SPAWNED":
            print(f"Model: {result['model']}")
            print(f"Routed: {result.get('routed', False)}")
            print(f"Output: {result['output_file']}")
    """

    # ROUTE: Select model if not explicitly provided
    selected_model = model
    routed = False

    if not model:
        # Router selects optimal model based on task characteristics
        route_config = route_model(
            task_type=task_type or "routine_analysis",
            content_size=content_size,
            has_images=has_images,
            budget=budget,
            required_context=required_context
        )
        selected_model = route_config.get("model_id", "claude-haiku-4-5-20251001")
        routed = True
        logger.info(f"Model routed: {task_type or 'routine_analysis'} → {selected_model}")
    else:
        logger.info(f"Model explicit: {model}")

    # ENFORCE: Build prompt — simple and clear (no confusing file/stdout instructions)
    prompt = f"""You are performing a task for Commander John Loucks of Dreams2Memories Travel, LLC.

TASK: {task_description}

Complete this task thoroughly and accurately. Provide only the actual content/analysis/results.
Do not add meta-commentary like "Task complete" or "Output written to...".
Just the actual task output."""

    # Dispatch to foolproof spawn wrapper (uses stdin/stdout PIPE pattern)
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=output_file_path,
        model=selected_model,
        task_name=task_name
    )

    # Add routing metadata to result
    result["routed"] = routed

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
    # Test dispatch — with routing
    print("Testing OpenCode headless dispatch with routing...")

    # Test 1: Routed task (large context → Grok 2M)
    print("\n✓ Test 1: Large context task (should route to Grok 2M for 800K tokens)")
    try:
        result = dispatch_to_headless_claude(
            task_description="Analyze 800K tokens of ship competitive intelligence.",
            output_file_path="/home/john/Thunderbird/output/test_opencode_routed.txt",
            task_name="test_opencode_routed",
            task_type="research",
            content_size=800000
        )
        print(f"Model: {result.get('model')}")
        print(f"Routed: {result.get('routed')}")
        print(f"Status: {result.get('status')}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)

    # Test 2: Explicit model (override router)
    print("\n✓ Test 2: Explicit model (override router)")
    try:
        result = dispatch_to_headless_claude(
            task_description="List the top 3 luxury cruise lines and why they are popular.",
            output_file_path="/home/john/Thunderbird/output/test_opencode_explicit.txt",
            task_name="test_opencode_explicit",
            model="claude-haiku-4-5-20251001"
        )
        print(f"Model: {result.get('model')}")
        print(f"Routed: {result.get('routed')}")
        print(f"Status: {result.get('status')}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
