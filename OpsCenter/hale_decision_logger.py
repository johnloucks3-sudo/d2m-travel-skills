#!/usr/bin/env python3
"""
Hale Autonomous Decision Logger — Persistence Layer

Enables OpenCode to log autonomous decisions to hale_decisions.md so they persist
across context transitions (OpenCode → Claude Code). Without this, Hale's autonomy
is invisible and unmeasurable.

Usage:
    from OpsCenter.hale_decision_logger import log_autonomous_decision

    log_autonomous_decision(
        decision_description="Escalated task to Sonnet due to large context",
        domain="Model Routing",
        decision_type="routine",
        outcome="correct",
        autonomy_tier="T1",
        notes="Context size >500K tokens detected. Auto-routed to Sonnet via MAX."
    )

This writes the decision to hale_decisions.md in real-time, ensuring it persists
when context switches to Claude Code.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal


def log_autonomous_decision(
    decision_description: str,
    domain: str,
    decision_type: Literal["routine", "tactical", "strategic"],
    outcome: Literal["correct", "incorrect", "escalated_correctly", "pending"],
    autonomy_tier: Literal["T1", "T2", "T3", "T4"] = "T1",
    notes: Optional[str] = None,
    trust_points: Optional[int] = None
) -> bool:
    """
    Log an autonomous decision to hale_decisions.md with full persistence.

    Args:
        decision_description: One-line summary of the decision
        domain: Decision domain (e.g., "Model Routing", "Email Classification", "Staff Task Routing")
        decision_type: "routine" (T1), "tactical" (T2), "strategic" (T3+)
        outcome: "correct", "incorrect", "escalated_correctly", or "pending"
        autonomy_tier: T1 (low sensitivity), T2 (medium), T3 (high), T4 (critical)
        notes: Optional context/reasoning
        trust_points: Optional explicit trust point change; calculated by default

    Returns:
        True if logged successfully, False if failed
    """

    # Validate inputs
    if not decision_description.strip():
        print("❌ Decision description required")
        return False

    # Build log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate trust points if not provided
    if trust_points is None:
        # T1 routine correct = +1 point
        # T2 tactical correct = +2 points
        # T3+ strategic = +3-5 points depending on outcome
        if outcome == "correct":
            trust_points = 1 if decision_type == "routine" else (2 if decision_type == "tactical" else 3)
        elif outcome == "escalated_correctly":
            trust_points = 1  # Correct judgment to escalate
        elif outcome == "incorrect":
            trust_points = -2  # Penalty for wrong autonomous decision
        else:  # pending
            trust_points = 0

    # Format the log entry
    entry = f"""
### {timestamp} — Autonomous Decision (Tier {autonomy_tier})

**Decision:** {decision_description}

**Domain:** {domain}
**Type:** {decision_type}
**Outcome:** {outcome}
**Trust Points:** {trust_points:+d}
**Autonomy Tier:** {autonomy_tier}
"""

    if notes:
        entry += f"**Notes:** {notes}\n"

    entry += "\n---\n"

    # Write to hale_decisions.md
    try:
        decisions_file = Path("/home/john/Thunderbird/hale_decisions.md")

        if decisions_file.exists():
            # Append to existing file (before the last separator)
            content = decisions_file.read_text()
            # Insert before the final marker if it exists
            if content.endswith("\n"):
                updated_content = content + entry
            else:
                updated_content = content + "\n" + entry
            decisions_file.write_text(updated_content)
        else:
            # Create new file
            decisions_file.write_text(entry)

        print(f"✅ Autonomous decision logged ({autonomy_tier} {decision_type}: {outcome})")
        return True

    except Exception as e:
        print(f"❌ Failed to log decision: {e}")
        return False


def log_model_escalation(
    task_description: str,
    original_model: str,
    escalated_model: str,
    reason: str,
    context_size_estimate: Optional[int] = None
) -> bool:
    """
    Log a model escalation decision (e.g., Haiku → Sonnet due to context size).

    Args:
        task_description: What task triggered the escalation
        original_model: Model that was first tried
        escalated_model: Model escalated to
        reason: Why escalation was necessary
        context_size_estimate: Optional estimated token count

    Returns:
        True if logged successfully
    """

    notes = f"Escalated from {original_model} → {escalated_model}\nReason: {reason}"
    if context_size_estimate:
        notes += f"\nEstimated context size: {context_size_estimate:,} tokens"

    return log_autonomous_decision(
        decision_description=f"Model escalation: {task_description}",
        domain="Model Routing",
        decision_type="routine",
        outcome="correct",
        autonomy_tier="T1",
        notes=notes
    )


if __name__ == "__main__":
    # Test: Log a sample decision
    log_autonomous_decision(
        decision_description="Escalated large-context task to Sonnet",
        domain="Model Routing",
        decision_type="routine",
        outcome="correct",
        autonomy_tier="T1",
        notes="Content size >500K tokens. Auto-routed via MAX subscription."
    )
    print("\nDecision logger deployed. Ready for OpenCode integration.")
