# Unified Model Router — Specification v1.0
## Thunderbird Wing | Hale-CC | 2026-05-19 | T4 Architecture Artifact

---

## PURPOSE

Single routing layer for all wing AI requests. Replaces fragmented per-bot routing.
Implements doctrine: capability-tier routing, automatic failover, hard cost ceilings,
loud error propagation, observable health and cost state.

This spec is the T4 design artifact authored by Hale-CC (Claude Code Opus 4.7).
Implementation is split:
- **Hale-CC (Opus)** — this spec, contract authoring, integration, QA, root-cause debug
- **Hale-OC (Haiku agents)** — adapter code, daemon implementation, scaffolding
- **Hale-CC review gate** — every Haiku output checked before commit

---

## DOCTRINE (Non-Negotiable Contract Clauses)

1. **One router. All requests through it.** No bot calls a model directly.
2. **Capability tiers, not vendor tiers.** Route by what the task needs, not what's cheap today.
3. **Errors are loud.** Never silently strip stderr. Never return empty as success.
4. **Hard cost ceilings.** Predictable failure over silent bleed. Hit 95% → stop.
5. **Health is observable.** Daemon polls every 5 min. Failover is automatic.
6. **MAX OAuth reserved for flag-tier.** Hale-CC, JET, TALON, voice work, judgment. Not bulk.
7. **OpenRouter demoted.** Break-glass only. Never default candidate. Bleeds credits.
8. **Poe is the polyglot layer.** Cheap-model whitelist only — never burn premium points.

---

## CAPABILITY TIERS

| Tier | Use Case | Primary | Fallback 1 | Fallback 2 | Last Resort |
|------|----------|---------|------------|------------|-------------|
| **FLAG** | Strategy, voice, judgment, T4 design | Claude MAX OAuth (Sonnet/Opus) | Poe-Claude-Sonnet-4.5 (expensive points!) | — | Defer to next session |
| **MID** | Brig Gen reasoning, structured output | Claude MAX OAuth (Sonnet) | opencode/big-pickle | Poe-Kimi-K2 | nemotron-free |
| **BULK** | Intel sweeps, OSINT, research, summarization | opencode/big-pickle | Poe-Gemini-2.5-Flash (100pts) | google/gemini-2.5-flash (Google AI Pro) | nemotron-free |
| **ARB** | Tie-break, narrow reasoning | DeepSeek R1 (free) | Poe-Kimi-K2 (400pts) | — | Return None + flag |

**Persona overrides:**
- DANI → FLAG only (client voice — never degrade)
- HALE-CC (architecture days like today) → FLAG only
- DEMBE (intel) → BULK first, MID only on judgment passes
- ALL OTHER A-staff → MID by default, FLAG only when explicit

---

## ADAPTER CONTRACT (Hale-OC Must Conform)

```python
from typing import Protocol, Literal
from dataclasses import dataclass

HealthState = Literal["GREEN", "YELLOW", "RED"]

@dataclass
class AdapterResult:
    text: str | None          # Response text, or None on failure
    error: str | None         # Structured error message, or None on success
    cost_consumed: float      # Native units (USD, points, tokens)
    cost_pool: str            # Which pool this drew from
    latency_ms: int
    model_used: str
    
    @property
    def ok(self) -> bool:
        return self.text is not None and self.error is None and len(self.text.strip()) > 0
    # ↑ Empty text is NEVER ok. This is the contract that kills the 0-char bug.

class Adapter(Protocol):
    name: str
    tier_capabilities: list[str]   # e.g. ["BULK", "MID"]
    cost_pool: str                 # Pool identifier
    point_cost_estimate: float     # Native unit per call (rough)
    
    def health_probe(self) -> tuple[HealthState, str]:
        """Lightweight ping. Returns state + reason string."""
    
    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        """Execute. Never raises. Never returns empty as success. Always structured."""
```

---

## ROUTER LOGIC

```python
def dispatch(task: TaskRequest) -> AdapterResult:
    tier = classify_tier(task)                             # 1. Tier
    candidates = TIER_CHAINS[tier]                         # 2. Candidates
    candidates = apply_persona_constraints(task.persona, candidates)
    candidates = [c for c in candidates if health[c.name] != "RED"]     # 3. Health filter
    candidates = [c for c in candidates if cost_gates.has_headroom(c.cost_pool)]  # 4. Cost filter
    
    if not candidates:
        return AdapterResult(text=None, error=f"All {tier} adapters offline/exhausted",
                             cost_consumed=0, cost_pool="none", latency_ms=0,
                             model_used="none")
    
    for adapter in candidates:                             # 5. Try in order
        t0 = time.monotonic()
        result = adapter.dispatch(task.system, task.user, task.max_tokens)
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        telemetry.log(persona=task.persona, tier=tier, result=result)
        cost_gates.consume(result.cost_pool, result.cost_consumed)
        if result.ok:
            return result
        health.record_failure(adapter.name)                # 6. Track failures
    
    return AdapterResult(text=None,
                         error=f"All {tier} adapters exhausted: {[c.name for c in candidates]}",
                         cost_consumed=0, cost_pool="none", latency_ms=0, model_used="exhausted")
```

---

## COST GATES

Three thresholds per pool:
- **80%** — Hale-CC alerted in daily brief, router prefers cheaper alternatives in tier
- **95%** — Hard stop on that pool. Adapters drawing from it are filtered out.
- **100%** — RED Telegram alert to Commander.

### Pools (initial)

| Pool | Source | Current State | Threshold |
|------|--------|---------------|-----------|
| `max_weekly_sonnet` | Anthropic MAX 5x Sonnet bucket | **85% — RED zone** | Reset Thu 9PM |
| `max_weekly_all` | Anthropic MAX 5x all-models bucket | 72% | Reset Thu 9PM |
| `poe_points` | Poe add-on | 100% (3.2M after $100 buy) | Hard pool |
| `openrouter_credits` | OpenRouter balance | **DEPLETED** | Frozen — never grow |
| `google_ai_pro` | Google AI Pro Gemini quota | Unknown | Flat-fee |
| `opencode_native` | big-pickle, nemotron, deepseek-v4-free | Effectively infinite | None |

---

## HEALTH DAEMON

- Polls each adapter every 5 minutes with a minimal ping prompt
- Records: latency, success, structured error string
- Marks **RED** on: 3 consecutive failures OR cost gate at 95%
- Recovery to **GREEN**: 2 consecutive successes after RED
- **YELLOW**: 1 failure in last 5 probes, or latency spike >3x baseline
- State persisted at `data/router_health.db` (SQLite)
- Crontab: `*/5 * * * *` via systemd timer `thunderbird-router-health.timer`

---

## TELEMETRY

Every dispatch logged to `data/router_telemetry.db`:
```
ts | persona | task_tier | adapter_used | model | cost_pool | cost_consumed | latency_ms | ok | error_summary
```

Daily aggregation injected into `hale_brief.md`:
- Calls by tier (count + %)
- Cost per pool (consumed + remaining)
- Failover events (who went red, what caught it)
- Anomalies (latency >2σ, surprise costs)

---

## FILE LAYOUT

```
core/ai_infra/
  unified_router.py             # Main entrypoint — dispatch(task)
  router_classifier.py          # classify_tier(task) — judgment
  router_health.py              # Health state + recording
  router_telemetry.py           # SQLite logging
  router_cost_gates.py          # Pool ceilings + consumption
  router_chains.py              # TIER_CHAINS + persona overrides
  adapters/
    __init__.py
    base.py                     # AdapterResult, Adapter Protocol (CONTRACT)
    claude_max_oauth.py         # Anthropic-direct via MAX OAuth
    opencode_bigpickle.py       # Native OpenCode big-pickle
    opencode_nemotron.py        # Native nemotron-3-super-free
    opencode_deepseek_v4.py     # DeepSeek V4 Flash Free (cap-watch + billing-watch)
    google_gemini_flash.py      # Direct Google AI Pro Gemini-2.5-Flash
    poe_polyglot.py             # Poe API (Gemini-2.5-Flash, Kimi-K2, Qwen-Max whitelist only)
    openrouter_breakglass.py    # OpenRouter — manual invoke only, never default
  
  daemons/
    router_health_daemon.py     # 5-min polling daemon

config/
  router_chains.json            # Tier-to-adapter priority lists
  router_cost_gates.json        # Pool thresholds + state
  poe_whitelist.json            # Allowed Poe models + point cost estimates

data/
  router_health.db              # SQLite — current health state
  router_telemetry.db           # SQLite — all dispatches

standing_orders/
  SO_UNIFIED_ROUTER_20260519.md      # New doctrine SO
  
Personas/
  HALE_CC_HALE_OC_SPLIT_CHARTER.md   # Formalizes split-engine pattern
```

---

## INTEGRATION POINTS (Wire Through Router)

| File | Current State | Action |
|------|---------------|--------|
| `OpsCenter/thunderbird_telegram_webhook.py` | `call_opencode_engine` patched (interim Poe fallback) | Replace both `call_opencode_engine` and `call_claude_engine` with `router.dispatch()` |
| `core/communication/thunderbird_telegram.py` (Dani) | Direct Claude calls | Route through router with `persona=DANI` |
| `core/ai_infra/thunderbird_personas.py` | `invoke_persona_sdk` | Internal dispatch through router |
| `OpsCenter/opencode_headless_claude_dispatch.py` | Direct subprocess | Route through router |
| `core/email/thunderbird_dani_engine.py` | Direct Claude calls | Route through router with `persona=DANI` |

---

## BUILD PHASES

| Phase | Owner | Tool | Output |
|-------|-------|------|--------|
| **P1** | Hale-CC (Opus, fresh session) | Direct | `unified_router.py` skeleton + `adapters/base.py` (CONTRACT) + `claude_max_oauth.py` + `opencode_bigpickle.py` |
| **P2** | Hale-OC | Headless Haiku agents (parallel x3) | `adapters/poe_polyglot.py`, `adapters/opencode_nemotron.py`, `adapters/opencode_deepseek_v4.py` |
| **P3** | Hale-CC (Opus) | Direct + agent QA | Review/fix all Haiku adapters. Wire webhook through router. |
| **P4** | Hale-OC | Headless Haiku | `router_cost_gates.py`, `router_telemetry.py`, `router_health_daemon.py` |
| **P5** | Hale-CC (Opus) | Direct | Wire Dani bot, persona SDK, email engine through router |
| **P6** | Hale-CC (Opus) | Direct | Write `SO_UNIFIED_ROUTER_20260519.md` + `HALE_CC_HALE_OC_SPLIT_CHARTER.md` + `hale_decisions.md` entry |
| **P7** | Hale-CC (Opus) | Direct | Failover scenario testing + voice fidelity test for Dani |

---

## VOICE FIDELITY TEST (Dani — Required Before Cutover)

Dani currently routes Sonnet through direct OAuth. Router-dispatched Sonnet uses the same model but a different code path.

**Test:** Generate 5 Dani client emails (validation + follow-up + insurance + booking change + thank-you) via:
- (A) Current direct path
- (B) Router-dispatched path

Hale-CC review compares:
- Tone consistency
- Sign-off ("Thanks" never "Best")
- Stationery integration
- Sentence cadence + warmth

**PASS:** Indistinguishable.
**FAIL:** Surface specific drift, identify root cause (system prompt drift? token budget mismatch?), fix, retest.

---

## SUCCESS CRITERIA (T4 Exit Condition)

1. ✅ Goose webhook returns >0 chars on every request (chain fully exercises, not just first model)
2. ✅ MAX weekly Sonnet consumption drops to <50% under equivalent workload
3. ✅ Failover from MAX-RED → big-pickle works in <2s, observable in telemetry
4. ✅ Cost gate alerts at 80% appear in `hale_brief.md` next morning
5. ✅ Zero silent 0-char returns anywhere — every empty triggers loud error
6. ✅ Voice fidelity test PASSES for Dani
7. ✅ T4 doctrine documented: SO + charter + hale_decisions entry within 7 days (Sterling artifact rule)
8. ✅ Pro downgrade Thursday survives without operational pain — router compensates

---

## KILL-OPENROUTER CHECKLIST

OpenRouter caused the May 15 $3.74 surprise burn and today's silent 0-char failure. Demotion plan:
- ✅ Removed from default `OPENCODE_MODEL_CHAIN` (interim patch 2026-05-19)
- ⏳ Router never includes OpenRouter in any TIER_CHAIN
- ⏳ `openrouter_breakglass.py` adapter exists but is ONLY invoked via explicit Commander-issued `--breakglass` flag
- ⏳ Daily telemetry summary flags any OpenRouter usage as anomaly

---

## DECISIONS LOG (Sterling 7-Day Artifact)

To be written to `hale_decisions.md`:
- Decision: Unify routing under single layer. **Rationale:** Fragmentation caused 3-hr outage 2026-05-18 + silent failures + cost creep.
- Decision: Poe as polyglot layer, not premium overflow. **Rationale:** Poe-Claude burns 40x points vs Poe-Gemini.
- Decision: Pro downgrade Thursday + Poe $100. **Rationale:** Router compensates for tighter cap. $770/yr savings.
- Decision: Hale-CC / Hale-OC split formalized as T4 doctrine. **Rationale:** Cost-optimal — Opus design, Haiku implement, Opus review.
- Decision: OpenRouter demoted to break-glass. **Rationale:** Sneaky cost creep, silent error mode.

---

*Hale-CC | Opus 4.7 | 2026-05-19 11:35 MT | Spec v1.0 | Ready for P1 build at next session reset*
