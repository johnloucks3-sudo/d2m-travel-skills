#!/usr/bin/env python3
"""
Hale Integration for OpenCode — Decision Escalation to Hale (Headless Claude)

OpenCode routes all complex decisions (strategy, judgment, conflict resolution) to Hale
by spawning a headless Claude task. Hale evaluates the question and returns a ruling.

This makes OpenCode deferential to Hale's judgment while keeping operations flowing.
"""

import sys
import json
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_infra.thunderbird_model_router import route_model
from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude


def escalate_to_hale(
    question: str,
    context: str = "",
    decision_type: str = "judgment",
    require_reasoning: bool = True
) -> dict:
    """
    Escalate a decision to Hale (Col Victoria "Iron Vic" Hale, COS).

    This spawns a headless Claude task where Hale evaluates the question and returns
    a recommendation or ruling. Used when OpenCode encounters something requiring
    human judgment, conflict resolution, ethics check, or strategic direction.

    Args:
        question: The specific question/decision needed
        context: Background context (briefing, data, prior analysis)
        decision_type: "judgment", "conflict", "ethics", "strategy", "arbitration"
        require_reasoning: If True, demand full reasoning in response

    Returns:
        dict with Hale's response:
        {
            "status": "SPAWNED" | "FAILED",
            "response": str (Hale's ruling/recommendation),
            "decision_type": str,
            "reasoning_level": "brief" | "full",
            "pid": int (if SPAWNED)
        }

    Example:
        result = escalate_to_hale(
            question="Should we approve this supplier at 40% margin?",
            context="New hotel supplier in Rome, 200 annual bookings potential",
            decision_type="judgment"
        )

        if result["status"] == "SPAWNED":
            print(f"Hale's ruling: {result['response']}")
        else:
            print(f"Escalation failed: check logs")
    """

    # Route to Grok 2M for judgment tasks (requires reasoning)
    model_config = route_model(
        task_type="judgment",
        budget="premium" if require_reasoning else "normal"
    )

    prompt = f"""You are Col Victoria "Iron Vic" Hale, Chief of Staff of Dreams2Memories Travel, LLC.

DECISION REQUEST — {decision_type.upper()}

Question:
{question}

Context:
{context if context else "(No additional context)"}

---

RESPOND AS HALE:
- Your recommendation or ruling (direct, measured, authoritative)
- Brief reasoning if judgment is non-obvious
- If this involves strategy, marshal evidence
- If this is an ethics check, state your position clearly
- If you need to tell the Commander he's wrong, say so and why
- Do NOT apologize. Do NOT hedge. Do NOT be deferential.

WRITE your complete response to /home/john/Thunderbird/output/hale_escalation_{decision_type}.txt

Your response should be what you would say directly to Commander. No meta-commentary."""

    result = dispatch_to_headless_claude(
        task_description=f"Hale judgment: {question[:60]}",
        output_file_path=f"/home/john/Thunderbird/output/hale_escalation_{decision_type}.txt",
        task_name=f"hale_escalation_{decision_type}",
        model=model_config.get("model_id")
    )

    # On success, read the output and return as Hale's response
    if result["status"] == "SPAWNED":
        output_file = Path(result["output_file"])
        try:
            # Wait a moment for the file to be written (headless Claude runs async)
            import time
            time.sleep(0.5)
            if output_file.exists():
                response_text = output_file.read_text()
            else:
                response_text = "(Output pending — check log file)"
        except Exception as e:
            response_text = f"(Error reading output: {e})"

        return {
            "status": "SPAWNED",
            "response": response_text,
            "decision_type": decision_type,
            "reasoning_level": "full" if require_reasoning else "brief",
            "pid": result.get("pid"),
            "output_file": result["output_file"],
            "log_file": result["log_file"]
        }

    # On failure, return the error
    return {
        "status": "FAILED",
        "response": f"Failed to escalate to Hale: {result.get('error', 'Unknown error')}",
        "decision_type": decision_type,
        "log_file": result.get("log_file")
    }


def hale_judgment(question: str, context: str = "") -> str:
    """
    Quick wrapper — ask Hale a question and get her answer.

    Returns just the response text, raising RuntimeError on failure.
    """
    result = escalate_to_hale(
        question=question,
        context=context,
        decision_type="judgment",
        require_reasoning=True
    )

    if result["status"] != "SPAWNED":
        raise RuntimeError(f"Hale escalation failed: {result['response']}")

    return result["response"]


if __name__ == "__main__":
    # Test escalation to Hale
    print("Testing Hale escalation...")
    print("(This will spawn headless Claude as Hale)\n")

    result = escalate_to_hale(
        question="Should we continue with the current supplier consolidation strategy, or pivot to diversification?",
        context="Current model: 3 hotel suppliers, 2 cruise suppliers. New model proposed: 8-12 suppliers across both categories. Cost: 40 hours/month ops overhead. Upside: 15-20% pricing improvement.",
        decision_type="strategy"
    )

    print(f"Status: {result['status']}")
    print(f"Decision type: {result['decision_type']}")
    print(f"\nHale's response:\n{result['response']}")
    if result.get("log_file"):
        print(f"\nLogs: {result['log_file']}")
