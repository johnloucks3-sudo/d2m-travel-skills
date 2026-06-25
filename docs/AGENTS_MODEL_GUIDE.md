# THUNDERBIRD — Poe Model Guide
*Updated 2026-06-25 | OpenRouter RETIRED | Poe.com direct API only*

---

## Architecture

```
Claude Code / scripts
        │
        ▼
scripts/poe_call.py
        │
        ▼
https://api.poe.com/v1/chat/completions
Bearer sk-poe-vLKz... (config/poe.env)
        │
        ▼
   Poe routes to selected model
   (points-based, no per-token billing)
```

---

## Quick Reference

```bash
# Use any model
python3 scripts/poe_call.py --model <KEY> --prompt "..."

# Show full table
python3 scripts/thunderbird_poe_config.py

# Set default model (also live-tests it)
python3 scripts/thunderbird_poe_config.py --model grok4

# Check API key health
python3 scripts/poe_call.py --check

# List ALL 380+ live Poe models
python3 scripts/poe_call.py --models
```

---

## Model Table — All Validated 2026-06-25

| KEY | POE MODEL ID | CTX | CAPABILITY | ALIASES |
|---|---|---|---|---|
| `claude` | `claude-sonnet-4.6` | 200K | Default text | `sonnet` |
| `opus` | `claude-opus-4.8` | 200K | Flagship (on demand) | — |
| `haiku` | `claude-haiku-4.5` | 200K | Fast / cheap text | `claude-haiku` |
| `cc` | `claude-code` | 200K | Code specialist | `claude-code`, `code` |
| `kimi` 🔒 | `kimi-k2.5` | 2M | Giant context | `k2` |
| `kimi-think` 🔒 | `kimi-k2-thinking` | 2M | Extended CoT | `k2-think` |
| `grok` | `grok-3` | — | xAI baseline | — |
| `grok4` | `grok-4.3` | 2M | xAI advanced reasoning | — |
| `grok-fast` | `grok-4.1-fast-non-reasoning` | 2M | Speed + reasoning | — |
| `grok-imagine` 📷 | `grok-imagine-image` | — | Image gen (xAI) | — |
| `gemini` | `gemini-3.5-flash` | 1M | Multimodal | `flash` |
| `gemini-pro` | `gemini-3.1-pro` | 1M | Gemini Pro | — |
| `gpt4` | `gpt-4o` | 128K | GPT flagship | `4o`, `gpt4o` |
| `gpt4-mini` | `gpt-4o-mini` | 128K | GPT budget | `mini` |
| `gpt41-nano` | `gpt-4.1-nano` | 1M | GPT-4.1 nano fast | `gpt4nano` |
| `gpt5-nano` | `gpt-5-nano` | 400K | GPT-5 nano | `gpt5nano` |
| `gpt54-nano` | `gpt-5.4-nano` | 400K | GPT-5.4 nano | `gpt54nano` |
| `speed` | `llama-3.3-70b` | 128K | Fastest text | `fast` |
| `deepseek` 🔒 | `deepseek-v3.2` | 128K | DeepSeek baseline | — |
| `deepseek-v4` 🔒 | `deepseek-v4-flash-e` | 128K | DeepSeek V4 | — |
| `r1` 🔒 | `deepseek-r1-n` | 128K | Chain-of-thought | — |
| `o3` | `o3` | 200K | Hard reasoning | — |
| `nano-banana` 📷 | `nano-banana` | — | Gemini 2.5 Flash image | `banana` |
| `nano-banana-2` 📷 | `nano-banana-2` | — | Google Imagen 4 | `banana2` |
| `nano-banana-pro` 📷 | `nano-banana-pro` | — | Gemini 3 Pro image | `banana-pro` |
| `nano-webui` 📷 | `nano-banana` | — | WebUI → falls back | `webui` |

**🔒 PII-FENCE** — strip client names, booking refs, payment amounts before sending  
**📷 IMAGE** — image generation model, not text

---

## Routing by Task

| Task | Use | Why |
|---|---|---|
| Client emails, proposals, voice | `claude` (Sonnet) | Best D2M voice, 200K ctx |
| Heavy architecture / judgment | `opus` | Flagship, use sparingly |
| Quick lookups, status checks | `haiku` | Fast, cheap |
| Code review / generation | `cc` | Claude Code specialist |
| Giant docs / 2M context | `kimi` | 🔒 PII-FENCE |
| Counter-voice / arbitration | `r1` or `o3` | CoT reasoning |
| Speed priority | `grok-fast` or `speed` | Low latency |
| Image generation | `nano-banana` or `grok-imagine` | Gemini vs xAI |
| Independent DeepSeek opinion | `deepseek-v4` | 🔒 PII-FENCE |

---

## Key Rotation

When your Poe key expires or gets revoked:

```
1. Go to: poe.com/api_key
2. Copy the current key
3. Edit: config/poe.env  →  POE_API_KEY=sk-poe-...
4. Verify: python3 scripts/poe_call.py --check
```

> **Note:** `load_api_key()` reads `config/poe.env` first — shell `$POE_API_KEY`
> is only a fallback. Stale env vars won't override the file.

---

## OpenRouter Status

**RETIRED 2026-06-25.** `scripts/openrouter_call.py` is a dead redirect shim —
it immediately re-routes all calls to `poe_call.py` and exits. No OpenRouter
API is contacted. `OPENROUTER_API_KEY` in `.env` is empty by design.
