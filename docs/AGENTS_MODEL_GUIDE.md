# AGENTS Model Guide

## Allowed OpenRouter Models (FREE only)

| Category | Model Key | OpenRouter ID | Cost | Best For |
|----------|-----------|---------------|------|----------|
| Reasoning & analysis | `deepseek-r1` | `openrouter/deepseek/deepseek-r1:free` | FREE | Logic, planning, step-by-step reasoning |
| Visualization & writing | `gemma-3` | `openrouter/google/gemma-3-27b-it:free` | FREE | Creative/descriptive tasks, layout suggestions |

## Poe.com Models — POLICY UPDATE

✅ **All Poe.com‑selected models are ALLOWED.**   If you select a model via Poe.com (using the Poe gateway), it is permitted regardless of its underlying provider or cost. The guardrail in `openrouter_call.py` only restricts direct OpenRouter model keys; it does not block Poe selections.

Operational steps:
1. Use the Poe gateway (`/poe` commands or `thunderbird_poe_config.py`) to choose any Poe bot/model.
2. Poe API is billed via your Poe subscription; no surprise OpenRouter charges.
3. When using Poe, prefix commands with `/poe` or set `POE_MODE=1` to route through Poe.

## Guardrail Enforcement

`scripts/openrouter_call.py` validates that only the listed OpenRouter keys (`gemma-3`, `deepseek-r1`, `deepseek-chat`) are used for direct OpenRouter calls. Any attempt to use a non‑listed OpenRouter model raises a clear `ValueError` showing the allowed list.

Poe.com selections bypass this check (no enforcement) to allow you safe, paid options that don't hit your OpenRouter budget.

## Usage Examples

```bash
# Direct OpenRouter (free tier)
python scripts/openrouter_call.py --model deepseek-r1 --prompt "Plan the migration in 5 steps."

# Coding on OpenRouter
python scripts/openrouter_call.py --model deepseek-chat --prompt "Write a FastAPI route for file upload."

# Poe (bypasses OpenRouter guardrail) — use Poe gateway or /poe commands
python scripts/thunderbird_poe_config.py --model gpt4   # switches Poe model
```

## Maintenance

- New free OpenRouter models can be added to `MODELS` in `scripts/openrouter_call.py` after evaluation.
- If a Poe model is to be used, select it via the Poe gateway; no code changes needed.
- Monitor OpenRouter usage; the guardrail prevents accidental non‑free calls.
- This file: update when allowed OpenRouter list changes.
- `scripts/openrouter_call.py`: update validation `MODELS` dict when adding free keys.
