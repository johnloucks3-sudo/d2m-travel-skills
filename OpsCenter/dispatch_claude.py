#!/usr/bin/env python3
"""
dispatch_claude.py — One-shot CLI for headless Claude spawning.

The CORRECT entry point for OpenCode (running Gemini 3.1 Flash Lite) and any
other non-Python agent that needs to dispatch a task to headless Claude.

Strips the stale ANTHROPIC_API_KEY automatically (via the foolproof wrapper),
verifies daemons, injects MAX OAuth, uses start_new_session=True, redirects
logs, and selects the right model.

USAGE — three forms, all work:

  # 1. Inline prompt, default Sonnet, background:
  python3 OpsCenter/dispatch_claude.py \
      --task "regent_splendor_intel" \
      --output /home/john/Thunderbird/output/splendor.md \
      --prompt "Produce a ship intel report... WRITE to /home/john/Thunderbird/output/splendor.md"

  # 2. Prompt from file (preferred for long prompts):
  python3 OpsCenter/dispatch_claude.py \
      --task "regent_splendor_intel" \
      --output /home/john/Thunderbird/output/splendor.md \
      --prompt-file /tmp/my_prompt.txt

  # 3. Explicit model + foreground (waits for completion):
  python3 OpsCenter/dispatch_claude.py \
      --task "quick_check" \
      --output /tmp/check.txt \
      --prompt "Say hi" \
      --model claude-haiku-4-5-20251001 \
      --foreground

Returns JSON to stdout: {"status":"SPAWNED","pid":...,"log_file":...,"output_file":...}

Exit codes: 0=spawned, 1=failed prerequisites, 2=invalid args.

DO NOT bypass this wrapper. Direct `claude -p ...` and `nohup claude ... &` will
fail because the shell carries a stale ANTHROPIC_API_KEY that preempts OAuth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude


MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


def resolve_model(m: str) -> str:
    return MODEL_ALIASES.get(m.lower(), m)


def main() -> int:
    p = argparse.ArgumentParser(
        prog="dispatch_claude",
        description="Foolproof CLI for headless Claude spawning (MAX OAuth, $0 marginal).",
    )
    p.add_argument("--task", required=True, help="Short task name (used in log filenames).")
    p.add_argument("--output", required=True, help="Absolute path where Claude will WRITE its output.")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--prompt", help="Inline prompt string.")
    grp.add_argument("--prompt-file", help="File containing the prompt.")
    p.add_argument("--model", default="sonnet",
                   help="Model: haiku|sonnet|opus or full ID. Default: sonnet.")
    p.add_argument("--foreground", action="store_true",
                   help="Wait for completion (default: background).")
    args = p.parse_args()

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text()
    else:
        prompt = args.prompt

    if "WRITE" not in prompt.upper() or args.output not in prompt:
        prompt = (
            f"{prompt.rstrip()}\n\n"
            f"WRITE your complete output to {args.output}\n"
            f"Do NOT output to stdout."
        )

    model = resolve_model(args.model)

    result = spawn_headless_claude(
        prompt=prompt,
        output_file=args.output,
        model=model,
        task_name=args.task,
        background=not args.foreground,
    )

    print(json.dumps(result, indent=2))

    if result.get("status") in ("SPAWNED", "COMPLETED"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
