"""
OpenCode ZEN Counter-Voice Dispatch
====================================
Spawns OpenCode with Grok Build (primary) or DeepSeek (fallback) as independent AI counter-voice.
Uses opencode_headless_grok_spawn for reliable process management and configuration.

Used when Claude needs a structurally different perspective on a significant decision.

Usage:
    from OpsCenter.opencode_zen_counter import zen_counter, zen_counter_async

    # Blocking (wait for answer)
    result = zen_counter("Should we use Opus or Sonnet?", model="grok")
    print(result)

    # Async (fire-and-forget)
    log_path = zen_counter_async("Counter this claim")
    print(f"Running in background, check {log_path}")

Or CLI:
    python3 OpsCenter/opencode_zen_counter.py "your question here"
    python3 OpsCenter/opencode_zen_counter.py --async "your question"
    python3 OpsCenter/opencode_zen_counter.py --model deepseek "your question"
"""

import sys
from pathlib import Path

from opencode_headless_grok_spawn import (
    spawn_grok,
    spawn_grok_custom,
    GrokSpawnConfig,
    SpawnMode,
)

COUNTER_SYSTEM = """You are ZEN — independent counter-voice for the Thunderbird Wing.
Your job: provide a brief perspective that challenges or confirms the proposal.
You are NOT a yes-machine. If the approach is sound, say so and why. If flawed, name it.
You don't know what was proposed — reason independently on merit.

Format: 2-4 sentences maximum. Lead with assessment, not disclaimers.
Sign: — ZEN"""


def zen_counter(question: str, context: str = "", model: str = "grok") -> str:
    """
    Dispatch a question to ZEN for counter-voice perspective (blocking).

    Args:
        question: The decision or approach to evaluate
        context: Optional brief context (no PII)
        model: "grok" (default, Grok Build) or "deepseek" (fallback)

    Returns:
        ZEN's counter-voice response as a string (or error message)
    """
    selected_model = "xai/grok-build-0.1" if model.lower() == "grok" else "deepseek/deepseek-chat"

    prompt = f"{COUNTER_SYSTEM}\n\n"
    if context:
        prompt += f"Context: {context}\n\n"
    prompt += f"Question: {question}"

    # Blocking mode — wait for answer
    result = spawn_grok(
        prompt,
        model=selected_model,
        blocking=True,
        timeout=30,
        verbose=False
    )

    if result.success:
        return result.output if result.output else "ZEN: no output generated"
    else:
        return f"ZEN dispatch error: {result.error}"


def zen_counter_async(question: str, context: str = "", model: str = "grok") -> Path:
    """
    Dispatch a question to ZEN for background analysis (async).

    Use when decision discussion is ongoing and you want Grok analyzing in parallel.
    Check log file later for perspective.

    Args:
        question: The decision or approach to evaluate
        context: Optional brief context (no PII)
        model: "grok" (default) or "deepseek"

    Returns:
        Path to log file (read after ~10s for output)
    """
    selected_model = "xai/grok-build-0.1" if model.lower() == "grok" else "deepseek/deepseek-chat"

    prompt = f"{COUNTER_SYSTEM}\n\n"
    if context:
        prompt += f"Context: {context}\n\n"
    prompt += f"Question: {question}"

    # Async mode — return immediately
    result = spawn_grok(
        prompt,
        model=selected_model,
        blocking=False,  # Async: fire-and-forget
        verbose=False
    )

    if result.success:
        return result.log_path
    else:
        raise RuntimeError(f"ZEN async dispatch failed: {result.error}")


def zen_counter_with_config(config: GrokSpawnConfig, question: str, context: str = "") -> str:
    """
    Dispatch with custom configuration.

    Args:
        config: GrokSpawnConfig instance
        question: The decision or approach to evaluate
        context: Optional brief context (no PII)

    Returns:
        ZEN's response (or error message)
    """
    prompt = f"{COUNTER_SYSTEM}\n\n"
    if context:
        prompt += f"Context: {context}\n\n"
    prompt += f"Question: {question}"

    result = spawn_grok_custom(config, prompt)

    if result.success:
        return result.output if result.output else "ZEN: no output generated"
    else:
        return f"ZEN dispatch error: {result.error}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ZEN Counter-Voice dispatch")
    parser.add_argument("question", nargs="+", help="Question for independent evaluation")
    parser.add_argument("--model", choices=["grok", "deepseek"], default="grok",
                       help="Model to use (default: grok)")
    parser.add_argument("--context", default="", help="Optional context (no PII)")
    parser.add_argument("--async", action="store_true", dest="async_mode",
                       help="Run async (background). Don't wait for answer.")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output (spawn details)")

    args = parser.parse_args()
    question = " ".join(args.question)
    model_label = "Grok Build (xAI)" if args.model == "grok" else "DeepSeek"

    if args.async_mode:
        # Async mode
        print(f"\n[ ZEN Counter-Voice (Async) — {model_label} ]\n")
        try:
            log_path = zen_counter_async(question, context=args.context, model=args.model)
            print(f"✓ Spawned in background")
            print(f"  Log: {log_path}")
            print(f"  Check in ~10s: cat {log_path}")
        except RuntimeError as e:
            print(f"❌ {e}")
            sys.exit(1)
    else:
        # Blocking mode
        print(f"\n[ ZEN Counter-Voice — {model_label} ]\n")
        if args.verbose:
            print("(Running... this may take 15-30 seconds)")
        result = zen_counter(question, context=args.context, model=args.model)
        print(result)
    print()
