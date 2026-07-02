# LLM Fallback Strategy — Poe Priority
**Status:** ✅ LIVE (updated 2026-06-27 — Poe is primary fallback)

## Overview
When Claude MAX token quota is exhausted, fallback to cheaper providers in priority order:

**Tier 1 (Primary):** Poe (DeepSeek V3.2, Grok 4.3, R1) — **2-5x cheaper than Cerebras**
**Tier 2 (Backup):** DeepInfra/Groq via gateway
**Tier 3 (Last resort):** Cerebras direct API

### Tools
1. **pswitch** — Provider switcher (shell function) — routes Claude Code to alternative LLM providers
2. **llim** — LLM Inference Manager (Python) — direct API queries (use as last resort)

---

## Fallback Strategy — Cost Priority

| Tier | Provider | Cost | Status | Command |
|------|----------|------|--------|---------|
| **1️⃣ Primary** | **Poe: DeepSeek V3.2** | $0.000025–0.00003/tk | ✅ 194,914 pts available | `pswitch ds` |
| **1️⃣ Primary** | **Poe: Grok 4.3** | $0.00003–0.00005/tk | ✅ Available | `pswitch grok` |
| **1️⃣ Primary** | **Poe: DeepSeek R1** | $0.00005–0.00008/tk | ✅ Reasoning | `pswitch r1` |
| **2️⃣ Secondary** | Groq Llama-3.3 | $0.00001/tk (free) | ✅ Free tier | `pswitch groq` |
| **2️⃣ Secondary** | DeepInfra Llama-3.3 | $0.00006/tk | ⚠️ $10 balance | `pswitch di` |
| **3️⃣ Last resort** | Cerebras GPT-7B | $0.00012/tk | ✅ Free: 5M/mo | `pswitch cerebras` or `llim` |

**Cost for 50M tokens/month:**
- Poe (DeepSeek): **$1,250–1,500** ✅ Best
- Groq: **$500** (free tier only)
- DeepInfra: **$3,000**
- Cerebras: **$6,000** ❌ Most expensive

---

## pswitch (Provider Switcher)

### What it does
Shell function that sets environment variables to route Claude Code requests through a gateway to alternative LLM providers.

### Usage — Recommended Order
```bash
# Check current provider
pswitch status

# TIER 1: Use Poe (cheapest, best quality)
pswitch ds       # DeepSeek V3.2 (usually best all-around)
pswitch grok     # Grok 4.3 (fast, good for reasoning)
pswitch r1       # DeepSeek R1 (chain-of-thought, PII fence)

# TIER 2: Free/cheap alternatives
pswitch groq     # Groq Llama-3.3 (completely free)
pswitch di       # DeepInfra Llama-3.3 (low cost, pay from $10 balance)

# TIER 3: Last resort
pswitch cerebras # Cerebras (5M free/mo, then $0.00012/tk)

# Switch back to native Claude
pswitch a

# Check gateway health
pswitch ping
```

### Available Providers (via gateway:4000)
- **Poe: DeepSeek V3.2** — best bang for buck (`pswitch ds`)
- **Poe: Grok 4.3** — fast, good reasoning (`pswitch grok`)
- **Poe: DeepSeek R1** — chain-of-thought, PII fence (`pswitch r1`)
- **Groq Llama-3.3** — free tier (`pswitch groq`)
- **DeepInfra** — paid, cheap (`pswitch di`)
- **Cerebras** — expensive fallback (`pswitch cerebras`)
- **Gemini 2.5 Flash** — via API key (`pswitch gemini`)

### When to use
When you need to route a Claude Code session to a fallback provider without creating a new session.

---

## llim (LLM Inference Manager) — Last Resort Only

### ⚠️ When to use
**Use ONLY when pswitch providers are unavailable.** This tool bypasses the gateway and costs more.

### What it does
Python tool that makes direct API calls to inference providers (Cerebras, DeepInfra, Groq) without going through the gateway. Useful for:
- Testing provider connectivity when gateway is down
- Direct inference as absolute last resort
- Getting provider-specific response metadata

### Usage
```bash
# Query Cerebras DIRECTLY (most expensive, last resort)
llim "Your prompt here"

# Or specify provider
llim --provider cerebras "Your prompt"
llim --provider deepinfra "Your prompt"
llim --provider groq "Your prompt"
```

### Supported Providers (Direct APIs only)
- **cerebras** — Cerebras Cloud ($0.00012/tk — EXPENSIVE)
- **deepinfra** — DeepInfra Llama-3.3-70B (paid)
- **groq** — Groq Llama-3.3-70B (free)

### Output Format
```json
{
  "status": "OK",
  "provider": "cerebras",
  "model": "gpt-oss-120b",
  "response": "The LLM response text",
  "tokens_used": 128,
  "timestamp": "2026-06-27T14:50:00.123456"
}
```

### When to use
- Testing if a provider is available when Claude MAX is exhausted
- Getting direct inference without gateway/environment routing
- Debugging provider connectivity

---

## Configuration

### API Keys (in .env)
```bash
CEREBRAS_API_KEY=csk-cm34cj2th2ykwyej3trwfvhrwjh9w2k95x33kee32mxhpchr
DEEPINFRA_API_KEY=dUE37MCP2LIpWNhcRXId24EPGXkyHO0x
GROQ_API_KEY=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
```

### Claude Code Permissions (settings.json)
```json
{
  "permissions": {
    "allow": [
      "Bash(pswitch)",
      "Bash(llim)"
    ]
  }
}
```

---

## Cerebras Models Available
- `gpt-oss-120b` — GPT-OSS 120B (default for llim)
- `zai-glm-4.7` — GLM 4.7

---

## Troubleshooting

### llim returns 404 model_not_found
**Problem:** `{"error": "HTTP 404: model ... does not exist or you do not have access"}`
**Solution:** Check available models with curl:
```bash
curl -H "Authorization: Bearer $(cat ~/.config/cc-fleet/secrets/cerebras)" \
  https://api.cerebras.ai/v1/models
```

### pswitch cerebras doesn't work in Claude Code
**Problem:** `ANTHROPIC_BASE_URL` is set but requests still hit Claude API
**Solution:** Use `llim` directly instead — it doesn't rely on environment routing.

### llim connection refused
**Problem:** `Connection refused` or timeout
**Solution:** Check API key and endpoint:
```bash
CEREBRAS_API_KEY=$(cat ~/.config/cc-fleet/secrets/cerebras)
curl -H "Authorization: Bearer $CEREBRAS_API_KEY" \
  https://api.cerebras.ai/v1/models
```

---

## Architecture & Recommended Fallback Flow

### Decision Tree (When Claude MAX exhausted)
```
Claude MAX tokens exhausted
    ↓
YES: Use pswitch ds (DeepSeek V3.2 via Poe)
    ├─ Cost: $0.000025/tk, quality: excellent
    ├─ Points: 194,914 available (~$1,500 worth)
    └─ Runtime: full Claude Code session continues
    
IF Poe points depleted:
    ├─ Try: pswitch groq (free Groq tier)
    ├─ Or: pswitch di (DeepInfra, $10 balance)
    └─ Last: pswitch cerebras (expensive, $0.00012/tk)

IF gateway down (rare):
    └─ Use: llim --provider groq (direct free API)
```

### pswitch flow (RECOMMENDED)
```
Claude Code session
    ↓
pswitch ds  (or grok, r1, groq, di, cerebras)
    ↓
(sets ANTHROPIC_BASE_URL, ANTHROPIC_MODEL env vars)
    ↓
Gateway (http://localhost:4000/v1)
    ↓
Poe / Groq / DeepInfra / Cerebras API
```

### llim flow (LAST RESORT ONLY)
```
Claude Code session
    ↓
llim --provider groq "prompt"  (direct, bypasses gateway)
    ↓
Direct HTTPS to provider API
    ↓
Provider response
    ↓
JSON output
```

---

## 📋 Recommendation

**When Claude MAX is exhausted:**
```bash
# PRIMARY CHOICE
pswitch ds    # DeepSeek V3.2 via Poe (~$0.000025/tk, excellent quality)

# SECONDARY (if Poe points low)
pswitch groq  # Free Groq tier (~$0.00001/tk)

# AVOID (too expensive)
# Don't use: pswitch cerebras, llim cerebras ($0.00012/tk = 5x cost of Poe)
```

---

*Updated 2026-06-27 14:55 MT | Poe set as primary fallback | Cost analysis: Poe 2-5x cheaper | Cerebras moved to tier 3*
