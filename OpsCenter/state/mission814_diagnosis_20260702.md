# MISSION-814 Diagnosis — CC-Fleet Subagent Validation
**Date:** 2026-07-02 · **Author:** Hale (Claude Code) · **Status:** ROOT CAUSE FOUND — partial fix applied, mission NOT closable with current providers

---

## TL;DR
cc-fleet 0.2.9 subagents fail against **both** Groq and Cerebras with **HTTP 404 (PROVIDER_API_ERROR)**. The dominant root cause is **an API-shape mismatch**, not credentials and not (only) model names:

- cc-fleet points the spawned `claude` binary at the provider via `ANTHROPIC_BASE_URL`, so `claude` calls the **Anthropic Messages API** (`POST /v1/messages`).
- Groq and Cerebras only expose the **OpenAI Chat Completions API** (`POST /chat/completions`). Neither serves `/v1/messages`.
- Result: every subagent job → 404. No OpenAI→Anthropic translation proxy is installed, so cc-fleet cannot drive these two providers as-is.

A secondary, real bug was also found and **fixed**: Cerebras was configured with a non-existent model (`llama-3.3-70b`). That alone would have failed even if the endpoint matched.

**MISSION-814's acceptance gate ("real LLM completion required before integration hooks") CANNOT be met with Groq/Cerebras direct.** Recommend pivoting to the mission's own fallback: a provider that speaks the Anthropic Messages API, OR an OpenAI→Anthropic proxy.

---

## Evidence (all verified live 2026-07-02)

### 1. Both API keys are VALID (raw OpenAI endpoint)
| Provider | Raw OpenAI `/chat/completions` test | Result |
|---|---|---|
| Groq (`llama-3.1-8b-instant`) | live completion | **OK** — returned content |
| Groq (`llama-3.3-70b-versatile`) | live completion | **OK** |
| Cerebras (`gpt-oss-120b`) | live completion | **OK** |
| Cerebras (`llama3.1-8b` / `llama-3.3-70b`) | live completion | `model_not_found` — model does not exist on this account |

Credentials are not the problem. The mission note "free API credentials invalid" is **incorrect** — keys work.

### 2. The real endpoint mismatch (dominant root cause)
```
POST https://api.groq.com/openai/v1/messages    → {"error":"Unknown request URL: POST /openai/v1/messages","code":"unknown_url"}
POST https://api.cerebras.ai/v1/messages        → (empty / no such endpoint)
```
cc-fleet's generated profile (`~/.claude/profiles/<provider>.json`) sets:
```json
"env": { "ANTHROPIC_BASE_URL": "https://api.cerebras.ai/v1", "ANTHROPIC_DEFAULT_SONNET_MODEL": "..." }
```
The spawned `claude` binary appends `/v1/messages` (Anthropic) to that base — which these providers don't serve.

### 3. cc-fleet subagent end-to-end (the mission's actual acceptance gate)
```
cc-fleet subagent cerebras --model gpt-oss-120b --json
  → {"ok":false,"error_code":"PROVIDER_API_ERROR","error_msg":"provider API error (HTTP 404)","api_error_status":404}
cc-fleet subagent groq --model llama-3.3-70b-versatile --json
  → {"ok":false,"error_code":"PROVIDER_API_ERROR","error_msg":"provider API error (HTTP 404)","api_error_status":404}
```
Prior stored subagent jobs corroborate: 2× groq FAILED, 1× cerebras FAILED (all pre-fix).

### 4. cc-fleet install is otherwise healthy
- Binary: `/home/john/.local/bin/cc-fleet` v0.2.9 (matches plugin 0.2.9)
- `cc-fleet doctor` → **core checks passed** (settings valid, profiles writable, keys reachable, skills installed). Only WARN is optional tmux (live-teammates only, irrelevant to out-of-tmux subagents).
- Not an npm package — it's a Go binary + Claude Code plugin (`ethanhq/cc-fleet`).

---

## Fix applied
**Cerebras model corrected** via the proper tool path (not hand-editing toml — cc-fleet regenerates a profile JSON that Claude Code reads):
```
cc-fleet edit cerebras --default-model gpt-oss-120b --strong-model gpt-oss-120b --fast-model gpt-oss-120b
```
Verified propagation to `~/.claude/profiles/cerebras.json` (all three ANTHROPIC_DEFAULT_*_MODEL now `gpt-oss-120b`). This removes the model-name blocker. The 404 endpoint blocker remains and is NOT fixable by config.
> Note: `~/.config/cc-fleet/providers.toml` and `~/.claude/profiles/cerebras.json` are outside the git repo; the change lives on the host, not in this commit.

Groq's configured model (`llama-3.3-70b-versatile`) is already valid on the OpenAI endpoint — no model change needed there; it fails only on the endpoint mismatch.

---

## Recommendation (ranked)
1. **Pivot to Poe-DeepSeek (mission's own fallback).** The Wing already runs DeepSeek/Grok via Poe agents (`poe-deepseek`, `poe-grok`, `poe-r1`) with points-based billing. Use those for the "cheap worker fleet" role instead of cc-fleet+Groq/Cerebras. Lowest effort, already validated in the Wing.
2. **If cc-fleet is required with Groq/Cerebras:** stand up an OpenAI→Anthropic translation proxy (LiteLLM proxy or `y-router`/`claude-code-router`), point `base_url` at the proxy's `/v1` (which serves `/v1/messages`), and re-test. This is a real build, not a config tweak.
3. **Do NOT** spend more time debugging credentials/model names — both are now correct; the wall is the API shape.

## MISSION-814 status update
- Blocker restated accurately: **API-shape mismatch (OpenAI-only providers vs Anthropic Messages requirement)**, not invalid credentials.
- Advisor gate (real completion) **remains OPEN** for Groq/Cerebras. Closable only via option 1 or 2 above.
- Cerebras model-name sub-bug: **CLOSED** (fixed + verified).

*— V. Hale, VCS · Thunderbird Wing · 2026-07-02*
