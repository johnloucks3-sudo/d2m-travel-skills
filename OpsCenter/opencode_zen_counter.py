"""
OpenCode ZEN Counter-Voice Dispatch
====================================
Spawns OpenCode with deepseek-v4-flash-free (ZEN) as an independent AI counter-voice.
Used when Claude needs a structurally different perspective on a significant decision.

Usage:
    from OpsCenter.opencode_zen_counter import zen_counter
    result = zen_counter("Should we use Opus or Sonnet for this research task?")

Or CLI:
    python3 OpsCenter/opencode_zen_counter.py "your question here"
"""

import re
import subprocess
import sys
from pathlib import Path

OPENCODE_BIN = Path.home() / ".opencode/bin/opencode"
ZEN_MODEL = "opencode/deepseek-v4-flash-free"
THUNDERBIRD_DIR = Path.home() / "Thunderbird"

COUNTER_SYSTEM = """You are ZEN — a DeepSeek-powered counter-voice for the Thunderbird Wing AI system.
Your job is to provide a brief, independent perspective that challenges or confirms the Claude AI's
proposed approach. You are NOT a yes-machine. If Claude's approach is sound, say so briefly and why.
If it has a flaw, name it directly. You do not know what Claude said — reason independently.

Format: 3-5 sentences maximum. Lead with your actual assessment, not a disclaimer.
Sign: — ZEN"""


def zen_counter(question: str, context: str = "") -> str:
    """
    Dispatch a question to OpenCode ZEN for counter-voice perspective.

    Args:
        question: The decision or approach to evaluate
        context: Optional brief context (no PII)

    Returns:
        ZEN's counter-voice response as a string
    """
    if not OPENCODE_BIN.exists():
        return "ZEN unavailable — opencode binary not found"

    prompt = f"{COUNTER_SYSTEM}\n\n"
    if context:
        prompt += f"Context: {context}\n\n"
    prompt += f"Question for independent evaluation: {question}"

    # Write output to temp file — opencode run requires a file target
    try:
        result = subprocess.run(
            [str(OPENCODE_BIN), "run", "-m", ZEN_MODEL, prompt],
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
    if len(sys.argv) < 2:
        print("Usage: python3 opencode_zen_counter.py 'your question here'")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\n[ ZEN Counter-Voice — {ZEN_MODEL} ]\n")
    print(zen_counter(question))
    print()
