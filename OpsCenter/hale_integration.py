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
    require_reasoning: bool = True,
    model_override: str = None
) -> dict:
    """
    Escalate a decision to Hale (Ms. Victoria "Victory" Hale, SES-6 — VCSAF-equivalent).

    This spawns a headless Claude task where Hale evaluates the question and returns
    a recommendation or ruling. Used when OpenCode encounters something requiring
    human judgment, conflict resolution, ethics check, or strategic direction.

    For enterprise transformation decisions, automatically uses Claude Opus instead
    of Grok for deeper reasoning capability.

    Args:
        question: The specific question/decision needed
        context: Background context (briefing, data, prior analysis)
        decision_type: "judgment", "conflict", "ethics", "strategy", "arbitration", "enterprise_transformation"
        require_reasoning: If True, demand full reasoning in response
        model_override: Optional explicit model (e.g., "claude-opus-4-7")

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
            question="Should we launch a D2M Academy for travel agent training?",
            context="Training program specs, market research, budget projections",
            decision_type="enterprise_transformation"
        )

        if result["status"] == "SPAWNED":
            print(f"Hale's ruling: {result['response']}")
        else:
            print(f"Escalation failed: check logs")
    """

    # Determine model: use override if provided, else Opus for transformation, else route normally
    if model_override:
        selected_model = model_override
    elif decision_type == "enterprise_transformation":
        # Enterprise transformation decisions → Opus (not Grok 4.1)
        selected_model = "claude-opus-4-7"
    else:
        # Route to Grok 2M for judgment tasks (requires reasoning)
        model_config = route_model(
            task_type="judgment",
            budget="premium" if require_reasoning else "normal"
        )
        selected_model = model_config.get("model_id")

    prompt = f"""You are Ms. Victoria "Victory" Hale, SES-6 — VCSAF-equivalent, Chief of Staff of Dreams2Memories Travel, LLC.

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
- If this is enterprise transformation, map implications: people, process, systems, timeline, risk
- If you need to tell the Commander he's wrong, say so and why
- Do NOT apologize. Do NOT hedge. Do NOT be deferential.

WRITE your complete response to [OUTPUT_FILE]

Your response should be what you would say directly to Commander. No meta-commentary."""

    # Generate unique output filename with timestamp to avoid concurrency collisions
    import time
    task_ts = int(time.time() * 1000)
    unique_output = f"/home/john/Thunderbird/output/hale_escalation_{decision_type}_{task_ts}.txt"

    # Fill in the unique output path in the prompt
    prompt = prompt.replace("[OUTPUT_FILE]", unique_output)

    result = dispatch_to_headless_claude(
        task_description=f"Hale judgment: {question[:60]}",
        output_file_path=unique_output,
        task_name=f"hale_escalation_{decision_type}_{task_ts}",
        model=selected_model
    )

    # On success, wait for async file completion and read the output
    if result["status"] == "SPAWNED":
        output_file = Path(unique_output)
        response_text = None
        max_wait_seconds = 60
        poll_interval = 0.5
        elapsed = 0

        # File-watch loop: wait for file to exist and contain content
        while elapsed < max_wait_seconds:
            if output_file.exists():
                try:
                    content = output_file.read_text().strip()
                    if content:  # File has content
                        response_text = content
                        break
                except Exception:
                    pass

            import time
            time.sleep(poll_interval)
            elapsed += poll_interval

        if response_text is None:
            response_text = f"(Output pending after {max_wait_seconds}s — check log: {result['log_file']})"

        # Log to audit trail and Telegram
        _audit_escalation(
            question=question,
            decision_type=decision_type,
            response=response_text,
            output_file=unique_output,
            log_file=result["log_file"],
            pid=result.get("pid")
        )

        return {
            "status": "SPAWNED",
            "response": response_text,
            "decision_type": decision_type,
            "reasoning_level": "full" if require_reasoning else "brief",
            "pid": result.get("pid"),
            "output_file": unique_output,
            "log_file": result["log_file"]
        }

    # On failure, escalate to Commander
    _escalate_failure_to_commander(
        question=question,
        decision_type=decision_type,
        error=result.get("error", "Unknown error"),
        log_file=result.get("log_file")
    )

    return {
        "status": "FAILED",
        "response": f"Failed to escalate to Hale: {result.get('error', 'Unknown error')}. Commander has been notified.",
        "decision_type": decision_type,
        "log_file": result.get("log_file"),
        "escalated_to_commander": True
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


def _audit_escalation(question: str, decision_type: str, response: str,
                      output_file: str, log_file: str, pid: int):
    """
    Log Hale decision to audit trail and push to Telegram + email.
    """
    from datetime import datetime
    from OpsCenter.hale_telegram_reporter import audit_log_entry

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = f"Decision type: {decision_type}\nQuestion: {question[:100]}...\nPID: {pid}"
    outcome = f"Response logged to {output_file}"

    # audit_log_entry handles both disk write and Telegram push, plus email in reporter
    audit_log_entry(
        action=f"Hale Judgment — {decision_type.upper()}",
        details=details,
        outcome=outcome
    )


def _escalate_failure_to_commander(question: str, decision_type: str,
                                   error: str, log_file: str):
    """
    When Hale escalation fails, notify Commander via Telegram + email.
    """
    from OpsCenter.hale_telegram_reporter import report_alert
    from OpsCenter.thunderbird_gmail import send_email

    # Telegram alert
    report_alert(
        f"Hale escalation FAILED ({decision_type}): {error}. Check logs: {log_file}",
        severity="critical"
    )

    # Email to Commander
    try:
        send_email(
            to="johnloucks3@gmail.com",
            subject=f"HALE ESCALATION FAILED — {decision_type.upper()}",
            body=f"""
Commander,

Hale escalation attempt failed.

Question: {question}
Type: {decision_type}
Error: {error}
Log file: {log_file}

COS recommends: Check the log file above. If the issue is OAuth/token related, run:
  systemctl --user status claude-token-monitor.timer

If the issue persists, let me know and we'll troubleshoot.

— Hale
""",
            from_addr="d2mconcierge@gmail.com"
        )
    except Exception as e:
        print(f"Warning: Could not email Commander about escalation failure: {e}")


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
