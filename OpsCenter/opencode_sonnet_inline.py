#!/usr/bin/env python3
"""
OpenCode → Sonnet inline wrapper (NO SCREEN SWITCHING).

From OpenCode, run:
  python3 opencode_sonnet_inline.py "Your task description here"

Spawns Sonnet, waits for output, displays it inline. Returns to OpenCode immediately.
"""

import sys
import logging
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from OpsCenter.opencode_headless_claude_dispatch import spawn_sonnet_inline

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("opencode_sonnet")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 opencode_sonnet_inline.py 'Your task description'")
        print("\nExample:")
        print("  python3 opencode_sonnet_inline.py 'Analyze cruise pricing trends'")
        sys.exit(1)

    # Collect all args as task description
    task_description = " ".join(sys.argv[1:])
    task_name = "opencode_interactive"

    print(f"\n🚀 Dispatching to Sonnet...\n")

    # Spawn and wait
    result = spawn_sonnet_inline(task_description, task_name)

    # Display result
    if result["status"] == "SUCCESS":
        print("=" * 70)
        print(result["output"])
        print("=" * 70)
        print(f"\n✅ Done in {result['elapsed_seconds']:.1f}s")
    elif result["status"] == "TIMEOUT":
        print(f"⏱️  Timeout: {result['output']}")
    else:
        print(f"❌ Error: {result['output']}")

    print(f"Output saved: {result['output_file']}")
    print()


if __name__ == "__main__":
    main()
