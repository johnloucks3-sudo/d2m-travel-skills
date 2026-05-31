"""
OpenCode ZEN Counter-Voice Dispatch
====================================
Spawns OpenCode with Grok-2 (primary) or DeepSeek (fallback) as independent AI counter-voice.
Used when Claude needs a structurally different perspective on a significant decision.

Usage:
    from OpsCenter.opencode_zen_counter import zen_counter
    result = zen_counter("Should we use Opus or Sonnet for this research task?", model="grok")

Or CLI:
    python3 OpsCenter/opencode_zen_counter.py "your question here"
    python3 OpsCenter/opencode_zen_counter.py --model grok "your question here"
    python3 OpsCenter/opencode_zen_counter.py --model deepseek "your question here"
"""

import re
import subprocess
import sys
from pathlib import Path

OPENCODE_BIN = Path.home() / ".opencode/bin/opencode"
ZEN_MODEL_GROK = "openrouter/x-ai/grok-build-0.1"  # Primary: Grok Build for independent reasoning (OpenRouter)
ZEN_MODEL_DEEPSEEK = "openrouter/deepseek/deepseek-chat"  # Fallback: DeepSeek via OpenRouter
THUNDERBIRD_DIR = Path.home() / "Thunderbird"

COUNTER_SYSTEM = """You are ZEN — a DeepSeek-powered counter-voice for the Thunderbird Wing AI system.
Your job is to provide a brief, independent perspective that challenges or confirms the Claude AI's
proposed approach. You are NOT a yes-machine. If Claude's approach is sound, say so briefly and why.
If it has a flaw, name it directly. You do not know what Claude said — reason independently.

Format: 3-5 sentences maximum. Lead with your actual assessment, not a disclaimer.
Sign: — ZEN"""


def zen_counter(question: str, context: str = "", model: str = "grok") -> str:
    """
    Dispatch a question to OpenCode ZEN for counter-voice perspective.

    Args:
        question: The decision or approach to evaluate
        context: Optional brief context (no PII)
        model: "grok" (default, Grok-2 via OpenRouter) or "deepseek" (fallback)

    Returns:
        ZEN's counter-voice response as a string
    """
    if not OPENCODE_BIN.exists():
        return "ZEN unavailable — opencode binary not found"

    selected_model = ZEN_MODEL_GROK if model.lower() == "grok" else ZEN_MODEL_DEEPSEEK
    model_label = "Grok-2" if model.lower() == "grok" else "DeepSeek"

    prompt = f"{COUNTER_SYSTEM}\n\n"
    if context:
        prompt += f"Context: {context}\n\n"
    prompt += f"Question for independent evaluation: {question}"

    # Write output to temp file — opencode run requires a file target
    try:
        result = subprocess.run(
            [str(OPENCODE_BIN), "run", "-m", selected_model, prompt],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(THUNDERBIRD_DIR)
        )
        clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout).strip()
        lines = [l for l in clean.splitlines() if l.strip() and not l.startswith('>')]
        response = '\n'.join(lines).strip()
        return response if response else f"ZEN: no output. rc={result.returncode}"

    except subprocess.TimeoutExpired:
        return "ZEN: timed out (60s limit)"
    except Exception as e:
        return f"ZEN dispatch error: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ZEN Counter-Voice dispatch")
    parser.add_argument("question", nargs="+", help="Question for independent evaluation")
    parser.add_argument("--model", choices=["grok", "deepseek"], default="grok",
                       help="Model to use (default: grok)")
    parser.add_argument("--context", default="", help="Optional context (no PII)")

    args = parser.parse_args()
    question = " ".join(args.question)
    model_label = "Grok-2 (OpenRouter)" if args.model == "grok" else "DeepSeek"

    print(f"\n[ ZEN Counter-Voice — {model_label} ]\n")
    result = zen_counter(question, context=args.context, model=args.model)
    print(result)
    print()
