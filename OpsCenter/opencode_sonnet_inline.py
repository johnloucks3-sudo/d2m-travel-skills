#!/usr/bin/env python3
"""
OpenCode → Claude inline wrapper (NO SCREEN SWITCHING).

Usage:
  python3 opencode_sonnet_inline.py "Your task description here"
  python3 opencode_sonnet_inline.py "Your task" --model claude-opus-4-6

Spawns Claude (Sonnet or Opus), waits for output, displays inline.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from OpsCenter.opencode_headless_claude_dispatch import spawn_sonnet_inline

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("opencode_sonnet")

DEFAULT_MODEL = "claude-sonnet-4-6"


def main():
    # Parse args — pull --model flag if present, rest is task description
    args = sys.argv[1:]
    model = DEFAULT_MODEL
    model_label = "Sonnet"

    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            model_label = "Opus" if "opus" in model else "Sonnet"
            i += 2
        else:
            filtered.append(args[i])
            i += 1

    task_description = " ".join(filtered)

    if not task_description:
        print("Usage: python3 opencode_sonnet_inline.py 'Your task description'")
        print("       python3 opencode_sonnet_inline.py 'task' --model claude-opus-4-6")
        sys.exit(1)

    print(f"\n🚀 Dispatching to {model_label}...\n")

    result = spawn_sonnet_inline(task_description, "opencode_interactive", model=model)

    if result["status"] == "SUCCESS":
        print("=" * 70)
        print(result["output"])
        print("=" * 70)
        print(f"\n✅ Done in {result['elapsed_seconds']:.1f}s ({model_label})")
    elif result["status"] == "TIMEOUT":
        print(f"⏱️  Timeout: {result['output']}")
    else:
        print(f"❌ Error: {result['output']}")

    print(f"Output saved: {result['output_file']}")
    print()


if __name__ == "__main__":
    main()
