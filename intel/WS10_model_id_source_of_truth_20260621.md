# WS-10 — Single Source of Truth for Claude Model IDs (ELON A12)
*2026-06-21 · adoption recommendation · priority med*

## NEED
Opus drifts across 4-5/4-6/4-7/4-8; sonnet 4-6 (78 refs); haiku 4-5 — all hardcoded as raw
`--model "claude-..."` string literals. 381 references across the repo. Upgrades require
shotgun edits; pinned IDs lag silently (opus pinned 4-7 in safeguards while running 4-8).

## VERDICT: BUILD a thin `model_ids` module over the Anthropic Models API. No SaaS exists or should.
There is no off-the-shelf product that "is the source of truth for Claude model IDs" — and buying
one would just be a stale mirror. Anthropic ALREADY publishes the live source of truth: the Models
API. The correct adoption is to consume it, not wrap it.

## THE SOURCE (verified 2026-06-21)
- `GET https://api.anthropic.com/v1/models`
- Headers: `x-api-key: $ANTHROPIC_API_KEY` · `anthropic-version: 2023-06-01`
- Returns `data[]` of `{id, display_name, created_at, type}`, **newest first** + pagination
  (`first_id`, `last_id`, `has_more`).
- Single-model lookup: `GET /v1/models/{id}` → 200 if the pinned ID resolves, 404 if it's dead.
- `ANTHROPIC_API_KEY` already present in repo (scripts/*.py). Zero new cost.

## Current GA IDs (as of 2026-06, from Models API + Anthropic docs)
| Tier | API id | Notes |
|---|---|---|
| Opus | `claude-opus-4-8` (most intelligent) | repo pins drift to 4-5/4-6/4-7 — STALE |
| Sonnet | `claude-sonnet-4-6` | 78 refs, currently correct |
| Haiku | `claude-haiku-4-5` (dated: `claude-haiku-4-5-20251001`) | correct |
| Fable | `Fable 5` GA 2026-06-09 | new family — confirm exact id via live endpoint before use |
NOTE: dated suffixes (e.g. `-20251001`) are the stable pins; bare aliases track latest minor.

## SMALLEST SAFE TRIAL (1 module + 1 timer, ~1h)
1. `core/ai_infra/model_ids.py` — constants `OPUS / SONNET / HAIKU / FABLE` + `resolve(tier)`.
   - Reads a pinned `config/model_ids.json` (the ONE place a human edits).
   - `verify_live()` calls `GET /v1/models/{id}` for each pin → True/False.
2. `scripts/model_id_check.py` + `model-id-check.timer` (daily 0600 MT, alongside ci-sweep):
   - Pins all resolve → RAZOR_SHARP, silent.
   - Any pin 404s OR a newer same-tier id appears at top of `data[]` → DULL → page Whetstone (A14);
     this IS the CI tech-adoption skill's currency check.
3. Migration: replace the 381 literals tier-by-tier with `model_ids.OPUS` etc. Sterling gates the
   refactor; do it in waves (safeguards/dispatch first — that's where the 4-7 lag bit us).

## WHY ADOPT NOW
- Fixes the exact failure that triggered WS-10: opus pinned 4-7 while 4-8 shipped. With the daily
  live check, that drift pages within 24h instead of lurking.
- Folds straight into existing CI razor-sharp doctrine (`config/ci_registry.json`, ci-sweep.timer) —
  this is literally the `tech-adoption` CI skill's model-currency probe, Whetstone-owned.
- One human-editable file kills the shotgun-edit pattern. Build-once-benefit-forever.

## RUNNERS-UP (real, but not the pick)
- **anthropics/skills `claude-api` skill** (github.com/anthropics/skills) — Anthropic-maintained
  reference doc of current model ids + migration guidance. GOOD as the human-readable companion to
  pin against, but it's docs, not a live resolver. Use it to seed `config/model_ids.json`; the API
  is the runtime check. FREE.
- **LiteLLM `model_prices_and_context_window.json`** (docs.litellm.ai) — community-maintained model
  registry (ids, ctx, pricing) already vendored in our archive. Broad coverage incl. pricing, BUT
  third-party + can lag Anthropic by days. WATCH as a pricing-data source only; not authoritative
  for ID currency.
- **OpenRouter `/api/v1/models`** (openrouter.ai) — live multi-provider model list. Useful for the
  free-model guardrail / OpenRouter side, NOT for canonical Anthropic GA ids (it remaps names).

## Sources
- https://docs.anthropic.com/en/api/models-list
- https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/models.md
- https://platform.claude.com/docs/en/about-claude/models/overview
- https://docs.litellm.ai/docs/providers/anthropic
- https://openrouter.ai/anthropic
