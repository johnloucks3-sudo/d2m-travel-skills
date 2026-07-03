#!/usr/bin/env python3
"""
thunderbird_poe_config.py — Poe model switcher + reference table
Wrapper around poe_call.py. Shows current table or sets POE_MODEL default.

Usage:
  python3 scripts/thunderbird_poe_config.py              # show full table
  python3 scripts/thunderbird_poe_config.py --model grok4  # set default + test
  python3 scripts/thunderbird_poe_config.py --model kimi --no-test
"""

import argparse
import subprocess
import sys
from pathlib import Path

POE_ENV = Path(__file__).parent.parent / "config" / "poe.env"
POE_CALL = Path(__file__).parent / "poe_call.py"

# ── MASTER TABLE ─────────────────────────────────────────────────────────────
# (KEY, POE_MODEL_ID, CTX, CAPABILITY, ALIASES, FLAGS)
# FLAGS: P=PII-fence  I=image-model
MODELS = [
    # ── Claude ──────────────────────────────────────────────────────────────
    ("claude",         "claude-sonnet-4.6",              "200K", "Default text",           "sonnet",                 ""),
    ("opus",           "claude-opus-4.8",                "200K", "Flagship",                "",                      ""),
    ("haiku",          "claude-haiku-4.5",               "200K", "Fast/cheap text",         "claude-haiku",          ""),
    ("cc",             "claude-code",                    "200K", "Code specialist",          "claude-code code",      ""),
    # ── Kimi ────────────────────────────────────────────────────────────────
    ("kimi",           "kimi-k2.5",                      "2M",   "Giant context",           "k2",                   "P"),
    ("kimi-think",     "kimi-k2-thinking",               "2M",   "Extended CoT",            "k2-think",             "P"),
    # ── Grok ────────────────────────────────────────────────────────────────
    ("grok",           "grok-3",                         "—",    "xAI baseline",            "",                      ""),
    ("grok4",          "grok-4.3",                       "2M",   "xAI advanced",            "",                      ""),
    ("grok-fast",      "grok-4.1-fast-non-reasoning",    "2M",   "Speed + reasoning",       "",                      ""),
    ("grok-imagine",   "grok-imagine-image",             "—",    "Image gen (xAI)",         "",                      "I"),
    # ── Gemini ──────────────────────────────────────────────────────────────
    ("gemini",         "gemini-3.5-flash",               "1M",   "Multimodal",              "flash",                 ""),
    ("gemini-pro",     "gemini-3.1-pro",                 "1M",   "Gemini Pro",              "",                      ""),
    # ── GPT ─────────────────────────────────────────────────────────────────
    ("gpt4",           "gpt-4o",                         "128K", "GPT flagship",            "4o gpt4o",              ""),
    ("gpt4-mini",      "gpt-4o-mini",                    "128K", "GPT budget",              "mini",                  ""),
    ("gpt41-nano",     "gpt-4.1-nano",                   "1M",   "GPT-4.1 nano",            "gpt4nano",              ""),
    ("gpt5-nano",      "gpt-5-nano",                     "400K", "GPT-5 nano",              "gpt5nano",              ""),
    ("gpt54-nano",     "gpt-5.4-nano",                   "400K", "GPT-5.4 nano",            "gpt54nano",             ""),
    # ── Speed ────────────────────────────────────────────────────────────────
    ("speed",          "llama-3.3-70b",                  "128K", "Fastest text",            "fast",                  ""),
    # ── DeepSeek ────────────────────────────────────────────────────────────
    ("deepseek",       "deepseek-v3.2",                  "128K", "DeepSeek baseline",       "",                      "P"),
    ("deepseek-v4",    "deepseek-v4-flash-e",            "128K", "DeepSeek V4",             "",                      "P"),
    ("r1",             "deepseek-v4-flash-e",            "128K", "V4 Flash cheap",           "",                      "P"),
    # ── Other ────────────────────────────────────────────────────────────────
    ("o3",             "o3",                             "200K", "Hard reasoning",          "",                      ""),
    # ── Nano Banana (image gen) ───────────────────────────────────────────────
    ("nano-banana",    "nano-banana",                    "—",    "Gemini 2.5 Flash image",  "banana",                "I"),
    ("nano-banana-2",  "nano-banana-2",                  "—",    "Google Imagen 4",         "banana2",               "I"),
    ("nano-banana-pro","nano-banana-pro",                "—",    "Gemini 3 Pro image",      "banana-pro",            "I"),
    ("nano-webui",     "nano-banana",                    "—",    "Nano WebUI → nano-banana","webui",                 "I"),
]


def show_table():
    print()
    print("  POE MODEL REFERENCE — Thunderbird Wing")
    print("  API: https://api.poe.com/v1  |  Key: config/poe.env")
    print()
    print(f"  {'KEY':<16} {'POE MODEL ID':<36} {'CTX':<5} {'ALIASES':<20} CAPABILITY")
    print("  " + "─" * 100)

    section = None
    section_map = {
        "claude": "── Claude ──────────────────────────────────────────────────",
        "kimi":   "── Kimi (PII-FENCE 🔒) ────────────────────────────────────",
        "grok":   "── Grok ────────────────────────────────────────────────────",
        "gemini": "── Gemini ──────────────────────────────────────────────────",
        "gpt4":   "── GPT ─────────────────────────────────────────────────────",
        "speed":  "── Speed ───────────────────────────────────────────────────",
        "deepseek":"── DeepSeek (PII-FENCE 🔒) ────────────────────────────────",
        "o3":     "── Other ───────────────────────────────────────────────────",
        "nano-banana": "── Nano Banana — IMAGE GENERATION 📷 ───────────────────",
    }

    for key, model_id, ctx, cap, aliases, flags in MODELS:
        if key in section_map:
            print()
            print(f"  {section_map[key]}")
        badge = ""
        if "I" in flags: badge = " 📷"
        if "P" in flags: badge += " 🔒"
        print(f"  {key:<16} {model_id:<36} {ctx:<5} {aliases:<20} {cap}{badge}")

    print()
    print("  Legend: 🔒 strip client PII before sending  |  📷 image generation model")
    print()
    print("  Usage:")
    print("    python3 scripts/poe_call.py --model <KEY> --prompt \"...\"")
    print("    python3 scripts/thunderbird_poe_config.py --model <KEY>   # set default")
    print()


def set_default(model_key: str, do_test: bool = True):
    # Resolve to Poe model ID
    model_id = None
    for key, mid, *_ in MODELS:
        if key == model_key:
            model_id = mid
            break
    # Also check aliases
    if not model_id:
        for key, mid, ctx, cap, aliases, flags in MODELS:
            if model_key in aliases.split():
                model_id = mid
                model_key = key
                break
    if not model_id:
        print(f"ERROR: '{model_key}' not in table. Run without --model to see full list.", file=sys.stderr)
        sys.exit(1)

    # Update POE_MODEL in config/poe.env
    lines = POE_ENV.read_text().splitlines()
    new_lines = []
    updated = False
    for line in lines:
        if line.startswith("POE_MODEL="):
            new_lines.append(f"POE_MODEL={model_id}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"POE_MODEL={model_id}")
    POE_ENV.write_text("\n".join(new_lines) + "\n")

    print(f"✅ Default model set: {model_key} → {model_id}")

    if do_test:
        print(f"   Testing live... ", end="", flush=True)
        result = subprocess.run(
            [sys.executable, str(POE_CALL), "--model", model_key, "--prompt", "Reply OK"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"LIVE ✅")
        else:
            print(f"FAIL ❌ — {result.stderr.strip()[:80]}")


def main():
    parser = argparse.ArgumentParser(description="Poe model switcher — Thunderbird Wing")
    parser.add_argument("--model", "-m", help="Set default Poe model by KEY")
    parser.add_argument("--no-test", action="store_true", help="Skip live test when setting model")
    args = parser.parse_args()

    if args.model:
        set_default(args.model, do_test=not args.no_test)
    else:
        show_table()


if __name__ == "__main__":
    main()
