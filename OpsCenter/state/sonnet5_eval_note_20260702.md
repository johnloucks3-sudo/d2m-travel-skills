# Sonnet 5 Evaluation Note — 2026-07-02
*Authored: Hale (COS) | Triggered by W7 research: Sonnet 5 shipped 2026-06-30*

## Status: Model ID TBD — Not yet confirmed in active infrastructure

### What shipped
Anthropic shipped a new Sonnet model on or around 2026-06-30. W7 report designates it "Sonnet 5."

### Current model ID inventory (active codebase)
| Location | Model ID in use |
|---|---|
| `~/.claude/settings.json` `"model"` key | `"sonnet"` (alias, resolves to current Sonnet) |
| `core/ai_infra/adapters/claude_max_oauth.py` | `claude-sonnet-4-6` (hardcoded) |
| `core/ai_infra/thunderbird_crewai.py` | `anthropic/claude-sonnet-4-6` |
| `core/ai_infra/thunderbird_skill_builder.py` | `claude-sonnet-4-6` (default arg) |
| `core/ai_infra/thunderbird_multi_agent.py` | `claude-sonnet-4-6` (default arg) |
| `core/ai_infra/thunderbird_personas.py` | `"sonnet"` alias + hardcoded fallback to `claude-sonnet-4-20250514` |

### No Sonnet 5 references found
`grep -rn 'sonnet-5|claude-sonnet-5'` across all active `.py`, `.json`, `.md`, `.sh` files (excluding archive/ and .venv/) returned **zero results**. The model is not yet in any Wing code.

### Model ID — Not yet determinable from local files
The Sonnet 5 model ID has not been published to this codebase. Expected format based on prior naming convention: `claude-sonnet-5` or `claude-sonnet-5-YYYYMMDD`. The Anthropic SDK `.venv` type stubs only include `claude-sonnet-4-6` — no 5.x entry yet at time of scan.

**DO NOT change model IDs without Commander approval.** This note is documentation only.

### Current routing behavior
- `keyword_router.py` routes by tier (`haiku` | `sonnet` | `opus`) — passes tier string, not hardcoded model ID
- `thunderbird_personas.py` resolves `"sonnet"` tier → current Sonnet via Claude Code's model alias
- `claude_max_oauth.py` adapter uses hardcoded `claude-sonnet-4-6` — this is the one file that would need an explicit update when Commander approves migration

### Sterling gate assessment
**HOLD pending confirmation.** Three open questions before adoption:

1. **Model ID confirmed?** — Need Anthropic docs or API response to confirm exact string
2. **Capability delta?** — What changed? If Sonnet 5 is a pure upgrade at same price, adopt immediately (Sterling gate FLIPS adoption-biased per SO_TECH_VANGUARD_ELEVATION_20260621)
3. **MAX plan coverage?** — Does Anthropic MAX subscription include Sonnet 5 at same rate cap, or does it meter differently?

### Recommended trial use case (when Commander approves)
First trial: `thunderbird_skill_builder.py` → generate_skill_code() — isolated, non-client-path, easy to A/B compare output quality. Low blast radius.

### Files requiring update when Commander approves migration
1. `core/ai_infra/adapters/claude_max_oauth.py` — `model_id="claude-sonnet-4-6"` → new ID (line ~94)
2. `core/ai_infra/thunderbird_crewai.py` — `CREWAI_LLM` constant (line 38)
3. `core/ai_infra/thunderbird_skill_builder.py` — default arg (line 92)
4. `core/ai_infra/thunderbird_multi_agent.py` — default arg (line 35)
5. `core/ai_infra/thunderbird_personas.py` — hardcoded fallback model string (line 761)

**Settings.json `"model": "sonnet"` alias will auto-resolve if Anthropic updates the alias — no change needed there.**

## Summary
Sonnet 5 shipped 2026-06-30. Model ID not yet confirmed in Wing infrastructure. Current routing uses `claude-sonnet-4-6` in 4 hardcoded locations. Recommend: (1) confirm model ID via Anthropic docs, (2) confirm MAX plan coverage, (3) trial on skill_builder first. Sterling gate: **HOLD pending model ID confirmation + MAX plan check.** No code changes made.

*— V. Hale, VCS · 2026-07-02*
