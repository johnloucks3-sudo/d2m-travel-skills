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
from OpsCenter.hale_escalation_triggers import should_escalate

logger = logging.getLogger("opencode_dispatch")


# Persona routing map — maps persona targets to prompt personalities and model defaults
PERSONA_CONFIGS = {
    "hale_cos": {
        "name": "Col Victoria 'Iron Vic' Hale",
        "role": "Chief of Staff",
        "model_default": "claude-opus-4-7",
        "prompt_prefix": "You are Col Victoria 'Iron Vic' Hale, Chief of Staff of Dreams2Memories Travel, LLC.",
    },
    "a5_castillo": {
        "name": "Lt Col Ryan 'Viper' Castillo",
        "role": "Strategy & Business Growth",
        "model_default": "claude-sonnet-4-6",
        "prompt_prefix": "You are Lt Col Ryan 'Viper' Castillo, Head of Strategy & Business Growth at Dreams2Memories Travel, LLC.",
    },
    "a9_harlan": {
        "name": "Victor 'Vic' Harlan",
        "role": "Finance & Process Improvement",
        "model_default": "claude-sonnet-4-6",
        "prompt_prefix": "You are Victor 'Vic' Harlan, Head of Finance & Process Improvement at Dreams2Memories Travel, LLC.",
    },
    "ch_washington": {
        "name": "Col James 'Padre' Washington",
        "role": "Wisdom, Ethics & Morale",
        "model_default": "claude-sonnet-4-6",
        "prompt_prefix": "You are Col James 'Padre' Washington, Chief of Wisdom, Ethics & Morale at Dreams2Memories Travel, LLC.",
    },
    "a12_elon": {
        "name": "ELON",
        "role": "Innovation & Disruption",
        "model_default": "claude-sonnet-4-6",
        "prompt_prefix": "You are ELON, Head of Innovation & Disruption at Dreams2Memories Travel, LLC.",
    },
}


def dispatch_to_headless_claude(
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    model: Optional[str] = None,
    task_type: Optional[str] = None,
    content_size: Optional[int] = None,
    has_images: bool = False,
    budget: str = "normal",
    required_context: Optional[int] = None,
    full_prompt: Optional[str] = None
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
        full_prompt: Optional complete prompt to use instead of building default prompt (for persona dispatch)

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
    # Use full_prompt if provided (for persona dispatch), otherwise build default
    if full_prompt:
        prompt = full_prompt
    else:
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


def dispatch_to_persona(
    persona_target: str,
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    decision_type: str = "judgment",
    model_override: Optional[str] = None,
    context: Optional[dict] = None
) -> dict:
    """
    Dispatch task to a specific A-staff persona using headless Claude.

    This implements tier-based routing: instead of always routing to Hale,
    routes to the appropriate specialist (A5 for strategy, A9 for finance,
    CH for ethics, etc.) for more efficient decision-making.

    Args:
        persona_target: Persona identifier (e.g., "a5_castillo", "ch_washington")
        task_description: The decision/task to present
        output_file_path: Where persona's response should be written
        task_name: Task name for logging
        decision_type: Type of decision (judgment, strategy, ethics, etc.)
        model_override: Optional explicit model override
        context: Optional context dict (converted to JSON for briefing)

    Returns:
        dict with result from headless Claude dispatch
    """
    import time

    # Get persona config
    persona_config = PERSONA_CONFIGS.get(persona_target, PERSONA_CONFIGS["hale_cos"])

    # Determine model: use override if provided, else use persona default
    selected_model = model_override or persona_config["model_default"]

    # Generate unique output filename with timestamp to avoid concurrency collisions
    task_ts = int(time.time() * 1000)
    unique_output = output_file_path.replace(".txt", f"_{persona_target}_{task_ts}.txt")

    # Build persona-specific prompt
    prompt = f"""{persona_config['prompt_prefix']}

DECISION REQUEST — {decision_type.upper()}

Question:
{task_description}

Context:
{json.dumps(context) if context else "(No additional context)"}

---

RESPOND AS {persona_config['name'].upper()}:
- Your recommendation or ruling (direct, measured, authoritative)
- Brief reasoning if judgment is non-obvious
- If strategy, marshal evidence
- If ethics check, state your position clearly
- If enterprise transformation, map implications: people, process, systems, timeline, risk
- Do NOT apologize. Do NOT hedge.

WRITE your complete response to {unique_output}

Your response should be what you would say directly to Commander. No meta-commentary."""

    # Dispatch to headless Claude with explicit model and full persona prompt
    result = dispatch_to_headless_claude(
        task_description=f"{persona_config['name']} judgment: {task_description[:60]}",
        output_file_path=unique_output,
        task_name=f"persona_dispatch_{persona_target}_{task_ts}",
        model=selected_model,  # Explicit model, no routing
        full_prompt=prompt  # Pass the persona-specific prompt
    )

    # On success, wait for async file completion and read output
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

            import time as time_module
            time_module.sleep(poll_interval)
            elapsed += poll_interval

        if response_text is None:
            response_text = f"(Output pending after {max_wait_seconds}s — check log: {result['log_file']})"

        # Log to audit trail
        from OpsCenter.hale_telegram_reporter import audit_log_entry
        audit_log_entry(
            action=f"{persona_config['name']} — {decision_type.upper()}",
            details=f"Decision type: {decision_type}\nQuestion: {task_description[:100]}...\nPID: {result.get('pid')}",
            outcome=f"Response logged to {unique_output}"
        )

        return {
            "status": "SPAWNED",
            "response": response_text,
            "decision_type": decision_type,
            "persona": persona_target,
            "persona_name": persona_config["name"],
            "model": selected_model,
            "pid": result.get("pid"),
            "output_file": unique_output,
            "log_file": result["log_file"]
        }

    # On failure, escalate to Commander
    from OpsCenter.hale_telegram_reporter import report_alert
    from OpsCenter.thunderbird_gmail import send_email

    # Telegram alert
    report_alert(
        f"{persona_config['name']} dispatch FAILED ({decision_type}): {result.get('error')}. Check logs: {result.get('log_file')}",
        severity="critical"
    )

    # Email to Commander
    try:
        send_email(
            to="johnloucks3@gmail.com",
            subject=f"{persona_config['name'].upper()} DISPATCH FAILED — {decision_type.upper()}",
            body=f"""
Commander,

{persona_config['name']} dispatch attempt failed.

Question: {task_description}
Type: {decision_type}
Error: {result.get('error', 'Unknown error')}
Log file: {result.get('log_file')}

COS recommends: Check the log file above. If the issue is OAuth/token related, run:
  systemctl --user status claude-token-monitor.timer

If the issue persists, let me know and we'll troubleshoot.

— {persona_config['name']}
""",
            from_addr="d2mconcierge@gmail.com"
        )
    except Exception as e:
        logger.warning(f"Could not email Commander about dispatch failure: {e}")

    return {
        "status": "FAILED",
        "response": f"Failed to dispatch to {persona_config['name']}: {result.get('error', 'Unknown error')}. Commander has been notified.",
        "decision_type": decision_type,
        "persona": persona_target,
        "log_file": result.get("log_file"),
        "escalated_to_commander": True
    }


def dispatch_with_escalation_check(
    task_description: str,
    output_file_path: str,
    task_name: str = "opencode_task",
    context: Optional[dict] = None,
    **dispatch_kwargs
) -> dict:
    """
    OpenCode dispatch with automatic tier-based escalation checking.

    Before dispatching to standard Claude, checks if the task matches any
    escalation triggers and routes to the appropriate A-staff persona:
    - A5 (Castillo) for strategy/supplier approval/client relationships
    - A9 (Harlan) for financial commitments
    - CH (Washington) for ethics/reputational risk
    - A12 (ELON) for innovation questions
    - Hale (COS) for conflict resolution, policy exceptions, enterprise transformation

    Args:
        task_description: Task description
        output_file_path: Output file path
        task_name: Task name for logging
        context: Optional context dict with metadata (margin_percent, commission_value, etc.)
        **dispatch_kwargs: Additional arguments to dispatch_to_headless_claude

    Returns:
        dict with dispatch result (either from persona or standard Claude)
    """
    # Check if this task should escalate and to whom
    should_esc, decision_type, reason, model_override, persona_target = should_escalate(task_description, context)

    if should_esc:
        persona_config = PERSONA_CONFIGS.get(persona_target, PERSONA_CONFIGS["hale_cos"])
        logger.info(f"🔼 Escalating to {persona_config['name']}: {reason}" + (f" (using {model_override})" if model_override else ""))

        result = dispatch_to_persona(
            persona_target=persona_target or "hale_cos",
            task_description=task_description,
            output_file_path=output_file_path,
            task_name=task_name,
            decision_type=decision_type or "judgment",
            model_override=model_override,
            context=context
        )
        result["escalated"] = True
        return result
    else:
        # Standard dispatch
        logger.debug(f"Standard dispatch: {task_name}")
        return dispatch_to_headless_claude(
            task_description=task_description,
            output_file_path=output_file_path,
            task_name=task_name,
            **dispatch_kwargs
        )


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

    # Test 3: Escalation trigger (should route to A5 Castillo for strategy)
    print("\n✓ Test 3: Escalation trigger (should route to A5 Castillo for strategy)")
    try:
        result = dispatch_with_escalation_check(
            task_description="Should we consolidate cruise suppliers to 3 lines or diversify to 8?",
            output_file_path="/home/john/Thunderbird/output/test_escalation.txt",
            task_name="test_escalation",
            context={"supply_chain_impact": True}
        )
        print(f"Escalated: {result.get('escalated', False)}")
        print(f"Persona: {result.get('persona')}")
        print(f"Persona Name: {result.get('persona_name')}")
        print(f"Status: {result.get('status')}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)

    # Test 4: Finance escalation (should route to A9 Harlan)
    print("\n✓ Test 4: Finance escalation (should route to A9 Harlan for financial commitment)")
    try:
        result = dispatch_with_escalation_check(
            task_description="Should we approve a $25K investment in a new supplier relationship?",
            output_file_path="/home/john/Thunderbird/output/test_finance_escalation.txt",
            task_name="test_finance_escalation",
            context={}
        )
        print(f"Escalated: {result.get('escalated', False)}")
        print(f"Persona: {result.get('persona')}")
        print(f"Persona Name: {result.get('persona_name')}")
        print(f"Status: {result.get('status')}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)

    # Test 5: Ethics escalation (should route to CH Washington)
    print("\n✓ Test 5: Ethics escalation (should route to CH Washington for ethics)")
    try:
        result = dispatch_with_escalation_check(
            task_description="A client expects luxury but we booked them a budget cabin. Rebook or manage expectation?",
            output_file_path="/home/john/Thunderbird/output/test_ethics_escalation.txt",
            task_name="test_ethics_escalation",
            context={}
        )
        print(f"Escalated: {result.get('escalated', False)}")
        print(f"Persona: {result.get('persona')}")
        print(f"Persona Name: {result.get('persona_name')}")
        print(f"Status: {result.get('status')}")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
