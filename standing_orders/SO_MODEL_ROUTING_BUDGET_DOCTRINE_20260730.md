# Standing Order — Model Routing & Budget Ownership Doctrine
**Date:** 2026-07-30
**Issued by:** Commander (John Loucks)
**Context:** Follows the 2026-07-30 Poe point burn incident (~99,147 points lost to an
unpriced agentic benchmark run in five minutes — see `core/relay/engine_limits.py`) and
the same-day OC model benchmark (`OpsCenter/oc_model_benchmark_2026-07-30.md`, S3213).
The Commander is drawing a line under both: **he owns this strategy**, not Hale by
default — the guardrails that would have prevented the burn incident should have
existed already, and their absence was his to correct, not staff's to improvise around.

## Directive

1. **Ownership.** This budget/routing strategy is Commander-issued, not a CC
   recommendation adopted after the fact. Staff (CC, OC, AG, and all named personas)
   are informed, not consulted, on the strategy itself.

2. **Be stingy with Claude/CC points.** CC self-execution against the Claude MAX bucket
   is the most constrained resource (5X, $100/mo per the 2026-07-29 halving) and should
   be spent deliberately — see existing `[[project_wing_oversight_delegation_transparency]]`
   delegation-first doctrine, reinforced here.

3. **Opus 5 as lead project manager.** Use Opus 5 as the standing lead PM across
   projects. Track its usage as a percentage displayed under the chyron alongside
   Sonnet/all-models/Poe/ZEN. **Status: not yet instrumented** — `core/ops/usage_chyron.py`
   and the `ai_costs.db` schema it reads (`claude_usage_reports`) currently carry only
   `sonnet_weekly_pct` / `all_models_weekly_pct`, no per-model Opus breakdown. Needs a
   data source before the chyron line can be added; tracked as open work below.

4. **OC → DeepSeek v4 ZEN when suitable.** Already the running configuration —
   `opencode/deepseek-v4-flash-free` (Zen free tier) per `[[reference_delegation_lane_config]]`
   (2026-07-29 fix). No change made; this directive confirms it stands.

5. **AG/Google → Gemini 3.5 Flash by default, 3.1 Pro only when the job calls for it.**
   Implemented this session: `core/relay/contact_ag.py` `DEFAULT_MODEL` flipped from
   `"Gemini 3.1 Pro (High)"` to `"Gemini 3.5 Flash (High)"`; `FALLBACK_MODELS` now leads
   with `"Gemini 3.1 Pro (High)"` for down/limited retries. Callers who know a task needs
   Pro-grade reasoning pass `model="Gemini 3.1 Pro (High)"` explicitly. CLAUDE.md updated
   to match.

6. **Poe reservoir target.** Draw the balance down to **800,000–900,000 by 19 Aug 2026**
   so the ~600,000 monthly replenish lands under the 1,500,000 carryover cap with margin
   and nothing evaporates. **Never exceed 1,500,000 on/after 19 Aug.** Burn only through
   `POE_WHITELIST` or Commander-approved models — per the existing fail-closed rule in
   `engine_limits.check_poe_model()`, a model is never whitelisted without a measured
   per-message price; **do not discover a price by spending**. Constants added this
   session: `POE_BURNDOWN_TARGET_DATE/MIN/MAX`, `POE_HARD_CAP` in `core/relay/engine_limits.py`.
   Open item: the burn-down candidates named in the 2026-07-30 benchmark
   (`poe/kimi-k2.5`, `poe/kimi-k2-thinking`, `poe/grok-4.3`, `poe/novita/glm-5`) are not
   yet priced — look up their per-message cost in Poe's model explorer and add to
   `POE_POINTS_PER_MESSAGE` before routing real burn-down volume through them.

7. **Check before final allocation, not before every task.** Before committing a
   non-trivial project's final resource allocation (which engine, which model tier),
   check current Claude/Poe/OC/AG headroom — `usage_chyron.py` for the live read,
   `engine_limits.check_headroom()` / `check_poe_model()` for the gate. Not required
   per-task; required at the point a project's spend gets locked in.

8. **CHIEF SILVER + adversary review — ad hoc projects and plans.** Bring SILVER
   (certification authority, `SO_STERLING_HALE_AG_GATE_20260727.md`) and an adversarial
   review (`devils-advocate` skill) into **every ad hoc project** as a standard step, not
   an opt-in. For every **plan**, surface the option to involve them explicitly before
   execution starts — the Commander decides whether to invoke, but the offer is
   mandatory. **Status: doctrine captured, not yet wired into tooling** — no code change
   made to the plan-mode flow or ad hoc task dispatch this session; needs its own scoping
   pass (likely an addition alongside the existing `plan_mode_mandates.py` PreToolUse hook).

9. **HEADLESS CLAUDE & MODEL ROUTING IN OC & AG (Directive 2026-07-31).**
   OpenCode (OC) and Anti-Gravity (AG) sessions must NEVER dispatch raw `ask` or `ask-opus` CLI calls.
   Claude capacity in CC is limit-rated at 25% of capacity (5X MAX bucket, $100/mo).
   **APPROVED EXCEPTION (Commander directive 2026-07-31):** Cross-engine validation using Claude Sonnet through AG (`contact_ag.py --model "Claude Sonnet 4.6 (Thinking)"` or native AG Sonnet subagent) IS explicitly APPROVED for validation and audits. Routine verifications default to AG Gemini 3.6 Flash / 3.1 Pro or OC DeepSeek v4.



## Why this fixes what it responds to

The 2026-07-30 burn happened because no guard existed between "run a benchmark" and
"spend 99K points" — the fix that followed (`engine_limits.py`'s fail-closed pricing
gate) was reactive. This SO makes the follow-on strategy proactive and Commander-owned:
explicit numeric targets (not vague "be careful"), a named check point (final
allocation, not every keystroke), and routing defaults that cost less by default
(3.5 Flash, DeepSeek Zen) with explicit escalation rather than expensive-by-default with
no override discipline.

## Open items (not closed by this SO)

- Opus 5 % instrumentation in the chyron — needs a data source, then a `usage_chyron.py`
  line and (if per-model split isn't already logged) a schema addition.
- Per-message pricing for the named burn-down candidate models.
- Silver + adversary auto-invoke wiring for ad hoc projects / plan offers.

## Related

- `OpsCenter/oc_model_benchmark_2026-07-30.md` — the benchmark this strategy responds to.
- `core/relay/engine_limits.py` — Poe spend guard, burn-down constants.
- `core/relay/contact_ag.py` — AG default model.
- `[[reference_delegation_lane_config]]`, `[[project_wing_oversight_delegation_transparency]]`.
- `SO_STERLING_HALE_AG_GATE_20260727.md` — SILVER certification authority.
