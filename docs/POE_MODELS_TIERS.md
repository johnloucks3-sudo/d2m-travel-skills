# POE MODELS — EFFECTIVE + ECONOMICAL TIERS (opencode.json)

**Status:** Applied 2026-08-06. Poe API (api.poe.com/v1, openai-compatible) accepts these model IDs.
Ground-truth tested: 45 text models live; GPT-5.x need `max_tokens` (not `max_completion_tokens`).

## EFFECTIVE (frontier reasoning)
| Model ID | Note |
|---|---|
| claude-opus-4.8 / 4.7 | Fully supported (tools + structured output) |
| claude-sonnet-4.6 / 4.5 | Fully supported |
| gpt-5.2 / 5.1 / 5.3-codex | Needs `maxTokens` in options; 400 w/ max_completion_tokens |
| gemini-3.1-pro | tools OK; `structuredOutputs: false` |
| grok-4.5 / grok-4 | Fully supported |
| kimi-k3 | tools OK; `structuredOutputs: false` |
| qwen3.5-397b-a17b | `structuredOutputs: false` |
| minimax-m3 | `structuredOutputs: false` |

## ECONOMICAL (cheap/fast)
| Model ID | Note |
|---|---|
| deepseek-v4-flash / v4-flash-e | Fully supported — current default workhorse |
| deepseek-v3.2 | Fully supported |
| gemini-3.6-flash | **text-only on Poe**: `supportsTools:false` + `structuredOutputs:false` |
| gemini-3.5-flash / 3.5-flash-lite / 3-flash | tools OK; `structuredOutputs: false` |
| grok-3-mini / grok-4.1-fast-non-reasoning | Fully supported |
| mistral-small-4 / minimax-m2.7 / glm-5 | `structuredOutputs: false` |

## KEY OPTION (AG empirical, verified)
```
"poe": {
  "npm": "@ai-sdk/openai-compatible",
  "options": { "baseURL": "https://api.poe.com/v1", "apiKey": "{env:POE_API_KEY}" },
  "models": {
    "gemini-3.6-flash": { "options": { "supportsTools": false, "structuredOutputs": false } },
    "gemini-3.5-flash": { "options": { "structuredOutputs": false } },
    "kimi-k3":          { "options": { "structuredOutputs": false } },
    "gpt-5.2":          { "options": { "maxTokens": 512 } }
  }
}
```
**NOTE (Claude caution):** `supportsTools`/`structuredOutputs` may be OpenCode capability flags vs SDK passthrough — if a model still 400s in opencode, flip to `"tool_call": false` / `"reasoning": false` at model level and re-test.
