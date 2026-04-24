#!/usr/bin/env python3
"""
Ollama Task Runner — invoked by keyword_router for Tier-1 (local inference) tasks.
Reads task text from stdin or --task-id from claude_inbox.md.
Writes result to stdout and logs to OpsCenter/collaboration/ollama_task_log.md.

Usage:
    echo "summarize: <text>" | python3 ollama_run_task.py
    python3 ollama_run_task.py --task-id TASK-XYZ
"""

import sys
import os
import argparse
import json
import time
from datetime import datetime

sys.path.insert(0, "/home/john/Thunderbird")
from core.ai_infra.thunderbird_ollama_client import OllamaWithFallback, OllamaClient

LOG_FILE = "/home/john/Thunderbird/OpsCenter/collaboration/ollama_task_log.md"


def log_result(task_id, prompt, result):
    entry = (
        f"\n---\n"
        f"## {datetime.now().strftime('%Y-%m-%d %H:%M MT')} | {task_id or 'stdin'}\n"
        f"**Source:** {result.get('source','?')} | "
        f"**Latency:** {result.get('latency_ms','?')}ms | "
        f"**Model:** {result.get('model','?')}\n\n"
        f"**Prompt:** {prompt[:200]}\n\n"
        f"**Response:** {result.get('text','')[:500]}\n"
    )
    with open(LOG_FILE, "a") as f:
        f.write(entry)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", help="Task ID to look up in claude_inbox.md")
    parser.add_argument("--model", default="phi3:mini", help="Ollama model to use")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    llm = OllamaWithFallback(OllamaClient(model=args.model, timeout=args.timeout))

    if args.task_id:
        # Read task text from claude_inbox.md
        inbox = "/home/john/Thunderbird/claude_inbox.md"
        task_text = None
        if os.path.exists(inbox):
            with open(inbox) as f:
                content = f.read()
            # Find the task block
            marker = f"## TASK: {args.task_id}"
            if marker in content:
                block = content.split(marker)[1].split("\n---")[0]
                task_text = block.strip()
        if not task_text:
            print(f"[ollama_run_task] Task {args.task_id} not found in inbox", file=sys.stderr)
            sys.exit(1)
        prompt = task_text
    else:
        # Read from stdin
        prompt = sys.stdin.read().strip()
        if not prompt:
            print("[ollama_run_task] No input. Pipe text or use --task-id.", file=sys.stderr)
            sys.exit(1)

    result = llm.generate(prompt)
    print(result["text"])
    print(f"[source:{result['source']} model:{result['model']} latency:{result['latency_ms']}ms]",
          file=sys.stderr)
    log_result(args.task_id, prompt, result)


if __name__ == "__main__":
    main()
