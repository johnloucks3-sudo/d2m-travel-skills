#!/usr/bin/env python3
"""
sync_poe_opencode.py — poe-sync
Injects Poe provider + model list into ~/.config/opencode/opencode.json
so OpenCode's ctrl+m model picker shows Poe models at subscription cost.

Usage:
  python3 scripts/sync_poe_opencode.py          # sync
  python3 scripts/sync_poe_opencode.py --check  # verify only
  alias: poe-sync (in ~/.bashrc)
"""

import json
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path(__file__).resolve().parent.parent
POE_ENV     = THUNDERBIRD / "config" / "poe.env"
OC_CONFIG   = Path.home() / ".config" / "opencode" / "opencode.json"

# ── Wing model list — Poe model IDs → display names ───────────────────────────
# Key = raw Poe model ID (what Poe's /v1/models returns)
# Val = display name shown in OpenCode ctrl+m picker
MODELS = {
    # Claude
    "claude-sonnet-4.6":              "Claude Sonnet 4.6",
    "claude-opus-4.8":                "Claude Opus 4.8",
    "claude-haiku-4.5":               "Claude Haiku 4.5",
    "claude-code":                    "Claude Code",
    # Grok
    "grok-3":                         "Grok 3",
    "grok-4.3":                       "Grok 4.3 (2M ctx)",
    "grok-4.1-fast-non-reasoning":    "Grok 4.1 Fast",
    # Gemini
    "gemini-3.5-flash":               "Gemini 3.5 Flash (1M ctx)",
    "gemini-3.1-pro":                 "Gemini 3.1 Pro (1M ctx)",
    # GPT
    "gpt-4o":                         "GPT-4o",
    "gpt-4o-mini":                    "GPT-4o Mini",
    "gpt-4.1-nano":                   "GPT-4.1 Nano (1M ctx)",
    "gpt-5-nano":                     "GPT-5 Nano",
    "gpt-5.4-nano":                   "GPT-5.4 Nano",
    "o3":                             "o3 (reasoning)",
    # DeepSeek — PII-FENCE: no client data
    "deepseek-v3.2":                  "DeepSeek V3.2 [PII-FENCE]",
    "deepseek-v4-flash-e":            "DeepSeek V4 Flash [PII-FENCE]",
    # Kimi — PII-FENCE
    "kimi-k2.5":                      "Kimi K2.5 (2M ctx) [PII-FENCE]",
    "kimi-k2-thinking":               "Kimi K2 Thinking (2M ctx) [PII-FENCE]",
    # Speed
    "llama-3.3-70b":                  "Llama 3.3 70B (fast)",
}


def load_api_key() -> str:
    if not POE_ENV.exists():
        sys.exit(f"ERROR: {POE_ENV} not found")
    for line in POE_ENV.read_text().splitlines():
        line = line.strip()
        if line.startswith("POE_API_KEY=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip()
    sys.exit("ERROR: POE_API_KEY not found in config/poe.env")


def load_oc_config() -> dict:
    if OC_CONFIG.exists():
        return json.loads(OC_CONFIG.read_text())
    return {"$schema": "https://opencode.ai/config.json"}


def build_poe_provider(api_key: str) -> dict:
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Poe (subscription)",
        "options": {
            "baseURL": "https://api.poe.com/v1",
            "apiKey": api_key,
        },
        "models": {
            model_id: {"name": display}
            for model_id, display in MODELS.items()
        },
    }


def sync(check_only: bool = False) -> None:
    api_key = load_api_key()
    masked  = api_key[:12] + "..." + api_key[-4:]

    config = load_oc_config()
    config.setdefault("provider", {})
    config["provider"]["poe"] = build_poe_provider(api_key)

    if check_only:
        print(f"Key  : {masked}")
        print(f"Config: {OC_CONFIG}")
        print(f"Models: {len(MODELS)}")
        print("OK — would sync (pass no flags to apply)")
        return

    OC_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Synced {len(MODELS)} Poe models → {OC_CONFIG}")
    print(f"Key  : {masked}")
    print(f"Usage: ctrl+m → poe/<model-id>")
    print("Restart OpenCode to pick up changes.")


if __name__ == "__main__":
    check = "--check" in sys.argv
    sync(check_only=check)
