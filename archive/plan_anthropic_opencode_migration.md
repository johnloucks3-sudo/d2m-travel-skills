# WING EXERCISE — Anthropic OpenCode Migration Assessment

## PROMPT CHARTER
1. **SUCCESS CRITERIA:** Complete assessment of all code, config, and router changes needed to run OpenCode with a direct Anthropic API key instead of OpenRouter/Poe. Verified by audit of every file that references model selection, provider config, or API key routing.
2. **SCOPE IN:** opencode.json, AGENTS.md model stack, dispatch_claude.py, keyword_router, wind_staff.py, all slash command templates (ask/ask-opus/ask-haiku), any env-var-dependent routing.
3. **SCOPE OUT:** Claude MAX OAuth path (dispatch_claude.py stays on MAX — that's THE premium channel, not competing). Poe/Ollama providers remain as fallback.
4. **NAMED STAFF:** A5 Viper (strategy/routing), A7 Sterling (audit metrics), JET/WIND (implementation).
5. **TOKEN/TIME BUDGET:** Assessment = 1h. Implementation = 2-3h. Assess before implement.
6. **EXIT CONDITION:** If assessment reveals Anthropic key is already routed correctly via MAX proxy (localhost:5099) and no changes are needed, stop and report.

---

## PHASE 1 — CURRENT STATE AUDIT

### Environment
| Variable | Value | Purpose | Issue |
|----------|-------|---------|-------|
| `ANTHROPIC_API_KEY` | `sk-proj-...` | Direct Anthropic key | Set but intercepted |
| `ANTHROPIC_BASE_URL` | `http://localhost:5099` | MAX OAuth proxy | **THIS IS THE PROBLEM** — routes all Anthropic calls through MAX, not the API key |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | OpenRouter | Stale — Commander migrating away |
| `OPENCODE_DEFAULT_MODEL` | not set | OpenCode default | Falls back to opencode.json |

### Config files
| File | Current | Needs Change |
|------|---------|--------------|
| `opencode.json` | Providers: Poe (Claude Haiku), Ollama (Qwen/Phi) | Add `anthropic` provider with Sonnet/Haiku/Opus |
| `AGENTS.md` model stack | Default: opencode/big-pickle. Conditionals route to dispatch_claude | Update default to Anthropic Sonnet. Clarify MAX vs API key paths. |
| `dispatch_claude.py` | Strips ANTHROPIC_API_KEY, uses MAX OAuth | **No change needed** — this is the premium MAX channel, keep separate |
| `keyword_router_v2.py` | Routes by task type | May need to update model refs |
| `wind_staff.py` | Persona dispatch | May need to update model refs |
| `opencode_memory.md` | Session state | Update model stack |

### Root cause of "reverted to MAX"
`ANTHROPIC_BASE_URL=http://localhost:5099` is set in the environment. This is a local proxy that authenticates via Claude MAX OAuth. Any OpenCode model that resolves through the Anthropic provider will hit this proxy first, which redirects to MAX. The Commander's `sk-proj-` key is set but never reached — the proxy intercepts before the key is read.

---

## PHASE 2 — REQUIRED CHANGES

### 1. `opencode.json` — Add Anthropic Provider
```json
"anthropic": {
  "npm": "@ai-sdk/anthropic",
  "name": "Anthropic Direct",
  "models": {
    "claude-sonnet-4-6": {
      "name": "Claude Sonnet 4.6"
    },
    "claude-haiku-4-5": {
      "name": "Claude Haiku 4.5"
    },
    "claude-opus-4-7": {
      "name": "Claude Opus 4.7"
    }
  }
}
```
Uses `ANTHROPIC_API_KEY` env var automatically (no hardcoded key in config).

### 2. Environment — Reset ANTHROPIC_BASE_URL
`ANTHROPIC_BASE_URL=http://localhost:5099` must be **unset** or set conditionally.
- When OpenCode needs the key, unset it: `unset ANTHROPIC_BASE_URL`
- When dispatch_claude.py needs MAX, keep or restore it
- Solution: wrapper script that toggles based on which engine is running

### 3. `AGENTS.md` — Update Model Stack
- Default OpenCode model → `anthropic/claude-sonnet-4-6`
- dispatch_claude.py stays on MAX OAuth (Sonnet/Opus)
- Routing table: "Client copy → Claude MAX. Infrastructure → Anthropic key. Bulk → free tier."

### 4. Slash Commands — Verify Templates
- `/ask` → dispatch_claude.py (MAX) — no change
- `/ask-opus` → dispatch_claude.py (MAX) — no change
- `/ask-haiku` → dispatch_claude.py (MAX) — no change
- These are correct — MAX is the premium path, Anthropic key is for OpenCode's interactive use

### 5. `keyword_router.py` — Model Refs
Update references from `opencode/big-pickle` or OpenRouter model names to `anthropic/claude-sonnet-4-6`.

### 6. `wind_staff.py` — Model Refs
Same update for persona dispatch model references.

### 7. `opencode_memory.md`
Update model stack at end of session.

---

## PHASE 3 — DECISIONS (Commander must decide)

| # | Decision | Options | Recommended |
|---|----------|---------|-------------|
| 1 | **Default OpenCode model** | Anthropic Sonnet vs keep big-pickle (free) | Sonnet for cap, big-pickle for cost. Conditional: use big-pickle for bulk scanning, Sonnet for reasoning. |
| 2 | **ANTHROPIC_BASE_URL handling** | (a) Unset globally, create MAX wrapper vs (b) wrapper script to toggle | (b) Wrapper — keeps MAX working for dispatch_claude |
| 3 | **MAX vs API key for what** | MAX = client output, strategy, high-stakes. API key = interactive dev, infrastructure, bulk. | Clear routing — document in AGENTS.md |

---

## EXECUTION PLAN

### Step 1: Fix env var collision (10 min)
```bash
# Script: scripts/opencode_env.sh
# Unset the proxy when running OpenCode interactively
unset ANTHROPIC_BASE_URL
export ANTHROPIC_API_KEY=sk-proj-...
exec opencode "$@"
```

### Step 2: Update opencode.json (10 min)
Add Anthropic provider with 3 models (Sonnet, Haiku, Opus).

### Step 3: Update AGENTS.md model stack (10 min)
New routing table reflecting Anthropic API key as primary OpenCode channel.

### Step 4: Audit keyword_router + wind_staff (15 min)
Find all model references, update to Anthropic model IDs.

### Step 5: Test (15 min)
```bash
opencode run -m anthropic/claude-sonnet-4-6 "test connectivity"
```

### Step 6: Update dispatch_claude.py NOTICE (5 min)
Add comment that it exclusively uses MAX OAuth, not the env var.

---

## DURABLE ARTIFACTS
- [ ] `scripts/opencode_env.sh` — env wrapper
- [ ] `opencode.json` — updated with Anthropic provider
- [ ] `AGENTS.md` — model stack updated
- [ ] `keyword_router_v2.py` — model refs updated
- [ ] `wind_staff.py` — model refs updated (if needed)
- [ ] Audit entry in `hale_decisions.md`

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MAX breaks if ANTHROPIC_BASE_URL unset | High | High | Wrapper script toggle, not global unset |
| API key rate-limited vs MAX unlimited | Medium | Medium | Keep MAX for heavy lifting, API key for interactive |
| OpenCode doesn't support @ai-sdk/anthropic | Low | Medium | Verify npm package exists |
| dispatch_claude.py conflicts with new key | Low | Low | dispatch_claude.py deliberately strips env var already |

---

*Assessment by COS Hale — WING EXERCISE T2 Operational*
*Next: Commander review → ELON gate decision → JET implementation*
