# Integrate Every Tech Find — 2026-06-21 Sweep · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Integrate (or concretely unblock/close) every tool found by the discovery fleet, the coupled Whetstone→ELON hunt, and the airborne scanner — under the corrected adoption doctrine: a $0, reversible, non-client-path find is INTEGRATE_NOW, never parked on "TRIAL."

**Architecture:** Adopt-first for free/reversible tools; internal-wiring "finds" are fixed as code (not adopted); real-money tools get a $0 free trial with the spend decision flagged to the Commander; key-blocked tools become unblock tasks; genuine no-gos are closed with a reason. Every integration that is infrastructure registers a CI efficacy probe so it can't silently rot. All agent/model work runs under the existing guards: `scanner_guards.can_spend` ($5/day pre-call kill), `run_ledger` (per-run budget + FAILURE flag), the client-send gate tripwire, and the §2a 7-day client-path canary.

**Tech Stack:** Python 3 (`.venv/bin/python3`), Claude Code plugins, systemd user timers, Gmail API, `config/ci_registry.json` CI engine, npx (ccusage/Renovate), Gemini direct API (GEMINI_API_KEY), Perplexity API.

**Governing doctrine (binding):** `standing_orders/SO_TECH_VANGUARD_ELEVATION_20260621.md` §2b — *TRIAL is not a hedge.* A find is INTEGRATE_NOW unless (1) real money → Commander, (2) client-send/PII path → canary, (3) proven harm. Nothing else demotes.

---

## File Structure (what gets created/modified)

- `core/ai_infra/cheap_engine_router.py` — **create**: routes bulk non-PII work to Gemini Flash-Lite / Groq under the cost-kill, off MAX-OAuth.
- `core/ai_infra/thunderbird_model_router.py` — **modify**: retire OpenRouter `_call_*` path → direct-Gemini; wire live Perplexity for web-research.
- `core/learning/model_safeguards.py` — **modify**: delete dead OpenRouter constants; collapse grok to one ID.
- `scripts/a7_model_audit_gate.py` — **modify**: add model-id existence check.
- `scripts/ci_probe_model_router.py` — **create**: regression assert — RED if any retired-provider ref reappears.
- `OpsCenter/harlan_cost_monitor.py` — **modify**: ingest ccusage real spend + metered-pool awareness.
- `scripts/ci_probe_version_currency.py` — **create**: Renovate-backed dependency-staleness probe.
- `config/ci_registry.json` — **modify**: register version-currency + cost-meter CI skills.
- `intel/ADOPTION_LOG_20260621.md` — **create**: one-line ledger of every find's disposition (adopt/fix/spend-flag/unblock/close) for the Commander.
- Claude Code plugin config — **modify**: install security-guidance + wshobson/agents marketplace.

---

## PHASE 1 — INTEGRATE NOW ($0, reversible, non-client-path)

### Task 1: security-guidance (official Anthropic plugin)

**Files:** Claude Code plugin config (managed by `/plugin`); `intel/ADOPTION_LOG_20260621.md`

- [ ] **Step 1: Add the official marketplace + install**

Run (in a Claude Code session): `/plugin marketplace add anthropics/claude-plugins-official` then `/plugin install security-guidance`

- [ ] **Step 2: Verify it loads + fires**

Run one session editing a NON-protected script (e.g. `scripts/_scratch_test.py`) with a deliberately bad pattern (`API_KEY = "sk-test-123"`). Expected: security-guidance flags the hardcoded secret on the edit.

- [ ] **Step 3: Log adoption**

Append to `intel/ADOPTION_LOG_20260621.md`: `security-guidance — ADOPTED <date> — $0, automated security review on every edit; we had zero before.`

### Task 2: wshobson/agents (MIT marketplace, ~184 subagents)

**Files:** plugin config; `intel/ADOPTION_LOG_20260621.md`

- [ ] **Step 1:** `/plugin marketplace add wshobson/agents`
- [ ] **Step 2:** Install ONE relevant plugin only (e.g. an orchestrator pattern): `/plugin install <name>@wshobson`
- [ ] **Step 3:** Test it against a non-client task; if it doesn't earn its slot in one use, `/plugin uninstall` (reversibility is the safety).
- [ ] **Step 4:** Log: `wshobson/agents — ADOPTED (marketplace) <date> — $0 MIT; install-only-what-earns-it.`

### Task 3: ccusage → real cost meter (closes Harlan's blindness)

**Files:** Modify `OpsCenter/harlan_cost_monitor.py`; `intel/ADOPTION_LOG_20260621.md`

- [ ] **Step 1: Confirm ccusage runs**

Run: `npx -y ccusage@latest --json` — Expected: JSON with `daily[]` totals (real local Claude spend; the fleet verified ~$1,897.80). $0 to run.

- [ ] **Step 2: Add an ingest function to the cost monitor**

In `OpsCenter/harlan_cost_monitor.py`, add:

```python
import json, subprocess
def ccusage_spend():
    """Real Claude spend from ccusage (local JSONL). Returns (total_usd, days)."""
    try:
        out = subprocess.run(["npx","-y","ccusage@latest","--json"],
                             capture_output=True, text=True, timeout=120).stdout
        d = json.loads(out); days = d.get("daily", [])
        return round(sum(x.get("totalCost",0) for x in days),2), len(days)
    except Exception as e:
        return None, str(e)
```

- [ ] **Step 3: Test it returns a number**

Run: `.venv/bin/python3 -c "from OpsCenter.harlan_cost_monitor import ccusage_spend; print(ccusage_spend())"` — Expected: `(<float>, <int days>)`.

- [ ] **Step 4: Commit**

`git add OpsCenter/harlan_cost_monitor.py && git commit -m "feat(cost): integrate ccusage real-spend meter into harlan_cost_monitor"`

### Task 4: Gemini Flash-Lite bulk lane (off MAX — the rate-limit fix)

**Files:** Create `core/ai_infra/cheap_engine_router.py`

- [ ] **Step 1: Write the cheap-engine router with the cost-kill guard**

```python
#!/usr/bin/env python3
"""Route bulk, non-PII work to Gemini Flash-Lite (free-tier) off MAX-OAuth.
Every call is gated by scanner_guards.can_spend ($5/day pre-call kill)."""
import sys; from pathlib import Path; sys.path.insert(0, "/home/john/Thunderbird")
from core.ai_infra import scanner_guards as g
MODEL = "gemini-2.5-flash-lite"  # direct Google AI; GEMINI_PAID_TIER_APPROVED must stay unset
def cheap_complete(prompt: str, est_cost: float = 0.0) -> str | None:
    ok, why = g.can_spend("gemini", est_cost)
    if not ok:
        print("cheap-lane refused:", why); return None
    # call_gemini_large_context is the verified live direct-Google lane
    from core.ai_infra.thunderbird_model_router import call_gemini_large_context
    out = call_gemini_large_context(prompt, model=MODEL)
    g.record_spend("gemini", est_cost)
    return out
```

- [ ] **Step 2: Smoke test**

Run: `.venv/bin/python3 -c "from core.ai_infra.cheap_engine_router import cheap_complete; print(cheap_complete('Reply OK')[:40])"` — Expected: a Gemini response (or a clean `cheap-lane refused` if over cap). If `call_gemini_large_context` signature differs, adapt the call to the real one in `thunderbird_model_router.py`.

- [ ] **Step 3: Commit.** `git add core/ai_infra/cheap_engine_router.py && git commit -m "feat: cheap-engine bulk lane (Flash-Lite) under $5/day cost-kill"`

### Task 5: Renovate version-currency CI probe

**Files:** Create `scripts/ci_probe_version_currency.py`; modify `config/ci_registry.json`

- [ ] **Step 1: Write the probe** — runs `npx -y renovate --platform=local --dry-run` (or reads `renovate` output), RED if ≥1 dependency is ≥2 majors behind. Mirror the structure of `scripts/ci_probe_email_handling.py` (read state, `fail()` on threshold, exit 0/1).
- [ ] **Step 2: Verify** `.venv/bin/python3 scripts/ci_probe_version_currency.py` exits 0 on a current tree.
- [ ] **Step 3: Register** a `version-currency` CI skill in `config/ci_registry.json` (keeper=whetstone), pattern-identical to the `email-handling` entry.
- [ ] **Step 4: Commit.**

### Task 6–8: Brand Voice plugin · Nested subagents · Agent Teams (patterns, $0)

- [ ] **Task 6 — Brand Voice plugin:** `/plugin install brand-voice@anthropics/knowledge-work-plugins`; point it at the 15 `feedback_voice_*` rules; **flag** its bundled `.mcp.json` against the lean-MCP doctrine (do not auto-enable extra MCP). Log adoption.
- [ ] **Task 7 — Nested subagents:** adopt the pattern in the *next* fleet run — a lead subagent spawns per-client children (e.g. the dossier-freshness scan across 17 clients). No install; it's a runtime technique. Log as `pattern adopted`.
- [ ] **Task 8 — Agent Teams (experimental):** enable in one bounded test; if it doesn't beat plain subagents, leave off. Log result.

---

## PHASE 2 — INTERNAL-FIX FINDS (code, not adoptions — the OpenRouter rot)

### Task 9: Decommission the dead OpenRouter path + regression assert

**Files:** Modify `core/ai_infra/thunderbird_model_router.py`, `core/learning/model_safeguards.py`; create `scripts/ci_probe_model_router.py`

- [ ] **Step 1:** Retire the OpenRouter-routed tiers in `thunderbird_model_router.py`; rewire `_call_gemini` to the live direct-Google path (`call_gemini_large_context` uses the funded `GEMINI_API_KEY`). For `_call_openrouter`/`_call_grok` with no live replacement, make them fail loudly (clear retirement error), not silently.
- [ ] **Step 2:** In `model_safeguards.py`, delete `DEEPSEEK_PRIMARY_MODEL` / `QWEN_PLUS_FREE_MODEL` / `DEEPSEEK_BULK_MODEL` / `FREE_OPENROUTER_BULK`; collapse grok to the single canonical `x-ai/grok-4.3`.
- [ ] **Step 3: Write the regression probe** `scripts/ci_probe_model_router.py`: `grep -rn 'openrouter' core/ --include=*.py | grep -v retired` → RED if any LIVE (uncommented) OpenRouter ref remains. This is Dembe's "can't be rediscovered" guard.
- [ ] **Step 4: Verify** `_call_*` no longer raises on the retired key and native-Claude fallback is intact; probe is RED now (refs exist) and GREEN after the rewire.
- [ ] **Step 5: Commit per file.**

### Task 10: WS-04 — wire the live Perplexity key (kill the OpenRouter web-research detour)

**Files:** Modify `core/ai_infra/thunderbird_model_router.py` (web-research route)

- [ ] **Step 1:** `PERPLEXITY_API_KEY` is SET and unused. Point the `WEB_RESEARCH` route at `https://api.perplexity.ai` (OpenAI-compatible) instead of the dead OpenRouter seam that returns ungrounded Gemini mislabeled as Sonar.
- [ ] **Step 2: Verify** a web-research call returns a grounded, cited result and logs `engine=perplexity` (not the false `openrouter`).
- [ ] **Step 3: Commit.**

### Task 11: a7_model_audit_gate — model-id existence check (the systemic guard)

**Files:** Modify `scripts/a7_model_audit_gate.py`

- [ ] **Step 1:** Add a check that every configured model ID resolves against the live/known catalog — this is WHY four fabricated IDs shipped.
- [ ] **Step 2: Test** it FAILS on a fake id (`gemini-3.1-flash-lite-preview-20260303`) and PASSES on real ones.
- [ ] **Step 3:** Make it a permanent gate rule; metric `model_id_existence_pass_rate=100%`. Commit.

---

## PHASE 3 — REAL-MONEY TOOLS (free trial = $0; the SPEND decision flags to Commander)

### Task 12: Firecrawl anti-bot fetch fallback (free-tier trial)

- [ ] **Step 1:** Sign up free tier (500 credits, $0). Run `/scrape` of the two known-failing URLs (Viking CloudFront-403, an Imperva page) through Firecrawl Stealth.
- [ ] **Step 2:** Record success-rate vs our Camoufox+nodriver in `intel/ADOPTION_LOG_20260621.md`.
- [ ] **Step 3: GATE:** if it beats our stack, the $19/mo Hobby decision **reaches the Commander** (real money). Do not auto-subscribe. Free trial is adopt-now; paid is his call.

### Task 13: Omnigent budget/sandbox wrapper (Apache-2.0, $0)

- [ ] **Step 1:** Wrap ONE headless spawn (the overnight incubator) in an Omnigent per-run cost-budget policy + egress sandbox. $0 (model usage only, under the existing ledger).
- [ ] **Step 2:** Verify the spawn pauses at its budget ceiling. Log. (Model token cost only — within the $5/day + ledger.)

### Task 14: Claude Code Routines (meter before standardizing)

- [ ] **Step 1:** Port ONE low-stakes job (AM brief gen → johnloucks3) to a cloud Routine.
- [ ] **Step 2:** Run it alongside the existing systemd timer for one week; ccusage-meter the plan-usage cost per run (Task 3).
- [ ] **Step 3: GATE:** standardize only if the metered cost is acceptable — surface the number to the Commander.

---

## PHASE 4 — KEY-BLOCKED (unblock task, not a hedge)

### Task 15: Groq small-context lane (key FUNDED → integrate)

- [ ] **Step 1:** GROQ key is funded. Add a Groq route in `cheap_engine_router.py` for SMALL-context, high-count classify/extract/triage (fare deltas, label routing) — NOT page-ingest. Under the cost-kill.
- [ ] **Step 2:** Smoke test a classify call. Commit.

### Task 16: DeepSeek (key EMPTY → Commander provisions, then integrate)

- [ ] **Step 1:** `DEEPSEEK_API_KEY` is empty. **This is a Commander unblock, not a Wing task:** request the key be provisioned.
- [ ] **Step 2:** ONCE provisioned, add the DeepSeek off-peak synthesis route to `cheap_engine_router.py`. Until then it is **blocked, not adopted** — logged with the one blocker (no key), not hedged.

---

## PHASE 5 — CLOSE WITH REASON (genuine no-go, documented — not a queue)

- [ ] **Task 17:** In `intel/ADOPTION_LOG_20260621.md`, close these with the one-line reason (so they never get "re-discovered"):
  - **Jina AI Reader** — CLOSED: explicitly does not bypass anti-bot; breaks on Cloudflare. Firecrawl (Task 12) owns that need.
  - **browser-use** — CLOSED: an autonomous LLM agent, not a fetch lane — wrong shape.
  - **Cerebras** — CLOSED: 8,192-token free-tier context cap disqualifies our >8K page-ingest sweeps.
  - **Dependabot** — CLOSED: Renovate (Task 5) strictly dominates (handles non-package sources).

---

## Self-Review

**Spec coverage:** every find from the three sweeps maps to a task — adopt-now (T1–8), internal fix (T9–11), real-money/free-trial (T12–14), key-blocked unblock (T15–16), closed-with-reason (T17). No find is parked on a bare "TRIAL."

**Placeholder scan:** real commands/code in every code step. Two install tasks (T1–2, T6) depend on the interactive `/plugin` system — verification is the tool firing, not a unit test, which is correct for an install.

**Type consistency:** `scanner_guards.can_spend/record_spend`, `run_ledger`, `call_gemini_large_context` referenced consistently; the worker MUST confirm the real `call_gemini_large_context` signature in `thunderbird_model_router.py` before Task 4 Step 2 and adapt.

**Doctrine check:** classifications obey SO §2b — only real-money (T12 paid, T14 metered) and proven-harm reach a gate; everything $0/reversible is adopt-now.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-21-integrate-every-tech-find.md`. Two execution options:

**1. Subagent-Driven (recommended)** — one fresh subagent per task, review between tasks, fast iteration. Run each under the `run_ledger` budget so the integration spree stays metered.

**2. Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
