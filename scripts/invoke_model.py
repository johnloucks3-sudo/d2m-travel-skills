#!/usr/bin/env python3
"""
invoke_model.py — Call any OpenRouter model by alias from Claude Code.

Usage:
    python3 scripts/invoke_model.py GROK "What's the best cruise for families?"
    python3 scripts/invoke_model.py DEEPSEEK "Analyze this booking status"
    python3 scripts/invoke_model.py --list                # Show available models
    python3 scripts/invoke_model.py --id google/gemini-3.1-flash-lite-preview "prompt"

Model aliases:
    GROK      → xAI Grok 4.1 Fast          (2M context, ~$0.20/M)
    DEEPSEEK  → DeepSeek V4 Pro            (1M context, ~$0.305/M)
    GEMINI    → Gemini 3.1 Flash Lite      (1M context, ~$0.25/M)
    LLAMA     → Llama 4 Maverick           (1M context, ~$0.15/M)
    GPT       → GPT-4.1 Mini              (1M context, ~$0.40/M)
    HAIKU     → Claude Haiku 4.5           (200K context)
    MISTRAL   → Mistral Small 3.2          (128K context)
    SONNET    → Claude Sonnet 4.6          (200K context)
    OPUS      → Claude Opus 4.6            (200K context)

All responses are prefixed with the model name for attribution.
"""

import sys
from pathlib import Path
sys.path.insert(0, "/home/john/Thunderbird")
from OpsCenter.hale_dispatcher import HaleDispatcher

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    prompt = " ".join(args)
    if not prompt:
        print("No prompt provided.")
        return 1

    hale = HaleDispatcher()
    print(hale.dispatch(prompt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
