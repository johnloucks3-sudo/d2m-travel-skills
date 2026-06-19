#!/usr/bin/env python3
"""
dispatch_claude.py — Unified Claude dispatch CLI.

Two execution paths:
  1. Headless OAuth spawn (default)    — MAX subscription, $0 marginal, background process
  2. Managed Agents API (--managed)    — API credits (~$0.0005/call), synchronous, token-tracked

Use --managed for:  crons · timers · intel sweeps · tech searches · financial pulse
Use headless for:   complex multi-step tasks · tasks needing file system access · interactive

USAGE:

  # Headless (default):
  python3 OpsCenter/dispatch_claude.py \
      --task "regent_intel" --output /tmp/out.md \
      --prompt "Ship intel... WRITE to /tmp/out.md"

  # Managed Agents (fast, token-tracked):
  python3 OpsCenter/dispatch_claude.py \
      --task "fare-watch" --output /tmp/fare.md \
      --prompt "Check Kuklinski air fares DEN-LIB Dec 17" \
      --managed --model haiku

Returns JSON to stdout.
Exit codes: 0=success, 1=failed prerequisites, 2=invalid args.
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
    "opus": "claude-opus-4-8",
}


def resolve_model(m: str) -> str:
    return MODEL_ALIASES.get(m.lower(), m)


def _run_managed(prompt: str, output: str, task: str, tier: str) -> dict:
    """Execute via Managed Agents API — synchronous, token-tracked."""
    from core.ai_infra.managed_agent_client import WingAgentClient
    client = WingAgentClient()
    result = client.run_task(prompt, tier=tier, label=task)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result["output"])
    return {
        "status": "COMPLETED",
        "output_file": output,
        "session_id": result["session_id"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": result["cost_usd"],
        "via": "managed_agents",
    }


def main() -> int:
    p = argparse.ArgumentParser(
        prog="dispatch_claude",
        description="Unified Claude dispatch (headless OAuth or Managed Agents API).",
    )
    p.add_argument("--task", required=True, help="Short task name (used in log filenames).")
    p.add_argument("--output", required=True, help="Absolute path for Claude output.")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--prompt", help="Inline prompt string.")
    grp.add_argument("--prompt-file", help="File containing the prompt.")
    p.add_argument("--model", default="sonnet",
                   help="Model: haiku|sonnet|opus or full ID. Default: sonnet.")
    p.add_argument("--foreground", action="store_true",
                   help="Wait for completion (default: background). Ignored with --managed.")
    p.add_argument("--managed", action="store_true",
                   help="Route via Managed Agents API (synchronous, token-tracked).")
    args = p.parse_args()

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text()
    else:
        prompt = args.prompt

    tier = args.model.lower() if args.model.lower() in MODEL_ALIASES else "sonnet"

    if args.managed:
        result = _run_managed(prompt, args.output, args.task, tier)
    else:
        if "WRITE" not in prompt.upper() or args.output not in prompt:
            prompt = (
                f"{prompt.rstrip()}\n\n"
                f"WRITE your complete output to {args.output}\n"
                f"Do NOT output to stdout."
            )
        result = spawn_headless_claude(
            prompt=prompt,
            output_file=args.output,
            model=resolve_model(args.model),
            task_name=args.task,
            background=not args.foreground,
        )

    print(json.dumps(result, indent=2))

    if result.get("status") in ("SPAWNED", "COMPLETED"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
