#!/usr/bin/env python3
"""
multi_brain_router.py — Route tasks to correct brain (Gemini / Sonnet / Opus)
=============================================================================
Brain 1: Gemini 2.5 Flash (FREE)  — research, data, bulk analysis
Brain 2: Claude Sonnet (Max plan) — client email, strategy, voice
Brain 3: Claude Opus (Max plan)   — tiebreaking, arbitration
Fallback: Claude Code (Max plan)  — system failures

Usage:
    from multi_brain_router import route_task
    result = route_task("analyze cruise lines", task_type="research", mission_id="M-001")
"""

import logging
from typing import Literal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

log = logging.getLogger(__name__)

# Import brain dispatchers
from OpsCenter.gemini_direct_dispatcher import dispatch_to_gemini
from OpsCenter.agent_runner import run_claude


def classify_task(task_type: str, content_sample: str = "") -> Literal["brain1", "brain2", "brain3", "fallback"]:
    """
    Classify task to correct brain based on type and complexity.

    Brain 1 (Gemini 2.5 Flash):
    - research, market_intel, data_extraction, scanning, competitor_analysis
    - bulk_analysis, routine_reports, log_analysis, price_monitoring
    - world_intel, ship_intel, innovation_scan

    Brain 2 (Claude Sonnet):
    - client_email, dani_response, proposal_copy, voice_matching
    - strategic_decision, tiebreaker, business_strategy, pricing_strategy

    Brain 3 (Claude Opus):
    - conflict_resolution, arbitration, complex_reasoning, policy_decision
    - complex_synthesis, multi_source_analysis

    Fallback (Claude Code):
    - Any task that requires full system resources or fails other brains
    """

    brain1_keywords = {
        "research", "scan", "intel", "competitor", "market", "price",
        "data_extract", "parse", "summarize", "bulk", "analyze_logs",
        "world_intel", "ship_intel", "innovation", "monitoring"
    }

    brain2_keywords = {
        "client_email", "dani", "proposal", "copy", "voice", "strategy",
        "business", "pricing", "decision", "tiebreak"
    }

    brain3_keywords = {
        "conflict", "arbitrate", "complex", "synthesis", "policy",
        "judgment", "evaluation", "weighting"
    }

    task_lower = task_type.lower()

    # Exact matches
    if any(kw in task_lower for kw in brain1_keywords):
        return "brain1"
    if any(kw in task_lower for kw in brain2_keywords):
        return "brain2"
    if any(kw in task_lower for kw in brain3_keywords):
        return "brain3"

    # Default: Brain 1 (safest, cheapest)
    return "brain1"


def route_task(
    task_text: str,
    task_type: str = "general",
    mission_id: str = None,
    preferred_brain: str = None,
) -> str:
    """
    Route task to correct brain and execute.

    Args:
        task_text: The task prompt/description
        task_type: Task classification (research, client_email, etc.)
        mission_id: Optional mission ID for logging
        preferred_brain: Override routing ("brain1", "brain2", "brain3")

    Returns:
        str: Result from the selected brain, or error message
    """

    # Determine brain
    if preferred_brain and preferred_brain in ("brain1", "brain2", "brain3", "fallback"):
        brain = preferred_brain
    else:
        brain = classify_task(task_type, task_text)

    log.info(f"[{mission_id}] Routing to {brain}: {task_type}")

    try:
        if brain == "brain1":
            # Gemini 2.5 Flash (FREE ops engine)
            result = dispatch_to_gemini(task_text, mission_id=mission_id, max_tokens=8000)
            return result

        elif brain == "brain2":
            # Claude Sonnet (Max plan — client facing, strategy)
            result = run_claude(
                f"[{mission_id}] TASK TYPE: {task_type}\n\n{task_text}",
                timeout=300,
                model="claude-sonnet-4-6",
            )
            return result[1] if result[0] else f"ERROR: {result[1]}"

        elif brain == "brain3":
            # Claude Opus (Max plan — arbitration, tiebreaking)
            result = run_claude(
                f"[{mission_id}] CRITICAL DECISION REQUIRED\nTASK TYPE: {task_type}\n\n{task_text}\n\nProvide definitive judgment with reasoning.",
                timeout=300,
                model="claude-opus-4-8",
            )
            return result[1] if result[0] else f"ERROR: {result[1]}"

        elif brain == "fallback":
            # Claude Code direct (system fallback)
            result = run_claude(
                f"[{mission_id}] SYSTEM FALLBACK\n\n{task_text}",
                timeout=300,
                model="claude-sonnet-4-6",
            )
            return result[1] if result[0] else f"ERROR: {result[1]}"

    except Exception as e:
        err = str(e)
        log.error(f"[{mission_id}] {brain} dispatch failed: {err}")
        # Escalate to fallback on any error
        if brain != "fallback":
            log.info(f"[{mission_id}] Escalating to fallback (Claude Code)")
            return route_task(task_text, task_type, mission_id, preferred_brain="fallback")
        return f"ERROR: {err}"


if __name__ == "__main__":
    # Test routing
    test_tasks = [
        ("Analyze cruise line pricing trends", "research"),
        ("Draft client email about Grandeur booking", "client_email"),
        ("Arbitrate between two conflicting recommendations", "arbitration"),
    ]

    for task_text, task_type in test_tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task_type}")
        print(f"{'='*60}")
        result = route_task(task_text, task_type=task_type, mission_id="TEST-001")
        print(result[:500] + ("..." if len(result) > 500 else ""))
