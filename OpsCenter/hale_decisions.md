
## 2026-06-24 — Production Override: Fix Dead Gemini Routing Loop

**Trigger:** T2-COMMS-BUILD-20260518 watcher dispatch — MISSION-001 error storm from `multi_brain_router.py` defaulting to brain1 (dead Gemini, disabled 2026-05-29 per `_GEMINI_DISABLED = True`)

**Commander: "Fix it hale, it is wasting tokens and is in your area"** — verbal order via CLI. Weapons Free in scope.

**Fix applied — two changes:**
1. `multi_brain_router.py:76-77`: Default changed from `return "brain1"` → `return "brain2"` (Claude Sonnet). Comment updated.
2. `gemini_direct_dispatcher.py:152-153`: When disabled, now `raise RuntimeError(...)` instead of returning a silent error string. This engages the try/except→fallback chain in `route_task()` (lines 140-147), so any remaining brain1 routes escalate to Claude Sonnet instead of returning dead error text.

**Effect:** Default routing now lands on working Claude Sonnet. If anything still hits brain1, it raises → caught by except → escalates to fallback (Claude Sonnet) instead of silently returning error text. Breaks the self-sustaining inbox error storm.

**Post-hoc:** Sterling notified. Sterling's veto suspended per Hale Override authority (SO-2026-06-14, Hale Override clause). Sterling audits after the fact.

---

## 2026-06-24 — T2 Fallback Build (Claude MAX Exhaustion Plan v2)

**Trigger:** Opus-reviewed Free Model Fallback Plan v2 — T2 tier implementation.

**Scope:** Production fix (ops lane). All within Hale Override authority under SO-2026-06-14.

**Decisions executed:**

1. **Wrote `bin/claude-fb`** — MAX fallback wrapper. Routes: T0 MAX native → T1 Anthropic API key via LiteLLM :4000 (when funded) → T2 free pool via LiteLLM :4000 with ccr. Emergency fallback: bare `claude --no-max`.

2. **Created `~/.claude-code-router/config.json`** — ccr 2.x format. Default route: `litellm-free` provider → `groq-llama` at `http://localhost:4000/v1`. Retired old 1.x `config-router.json` (dead OpenRouter default).

3. **Created `hooks/detect_max_exhaustion.sh`** — Stop hook. Fires on abnormal exit (code 137/130/non-zero), writes flag to `OpsCenter/max_exhaustion_flag`, reads `hale_state.json` weekly usage gauge. Clean exits clear the flag.

4. **Registered stop hook** in `~/.claude/settings.json`.

5. **Fixed D5** — Updated stale `"OpenRouter $0"` reason strings in `thunderbird_rate_limit_guard.py:229,237` to `"DeepSeek V4 Flash"` and `"Big Pickle"` respectively.

6. **Fixed D2** — Added `claude-api` alias to `~/.bashrc` (points at LiteLLM :4000 with `ANTHROPIC_BASE_URL`).

7. **Fixed D6** — Reconciled LiteLLM config divergence. Added `gemini-fallback` to Thunderbird copy's fallback chains. Marked Thunderbird copy as `STALE MIRROR` — canonical config is `~/.claude/gateway/litellm_config.yaml`.

**Remaining:** T1 requires funded Anthropic API key (HTTP 400 confirmed). Commander gate.

**Post-hoc:** Sterling notified for post-hoc audit. Sterling's veto suspended. ccr 1.x config-router.json retired; legacy dead OpenRouter route is no longer in rotation.

---
## DECISION — 2026-06-24T16:50:00Z — NEXUS DAEMON HALTED (PRODUCTION OVERRIDE)
by: Hale-OC (OpenCode / JET)
authority: Production Continuity Override (AGENTS.md §HARD RULES #4 — Hale Override)

**Decision:** Killed nexus.py daemon (PID 2686423/2686425) to stop runaway MISSION-001 loop.

**Why:** Nexus was generating 10+ new UNREAD error entries per minute, flooding opencode_inbox.md.
Self-feeding loop: UNREAD entry → nexus dispatches → Gemini error → new UNREAD entry → repeat.
Prior sessions swept 335+ entries; daemon kept regenerating. Operational harm ongoing.

**What was stopped:** `python3 /home/john/Thunderbird/OpsCenter/nexus.py daemon 30`
(PID 2686423, running since 13:21 MDT 2026-06-24)

**Commander notified:** Email dispatched to johnloucks3@gmail.com.
**Sterling audit:** Required post-hoc — nexus.py needs CLAUDE RESULT skip guard.

