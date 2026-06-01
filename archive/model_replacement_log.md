# Model Replacement Log — Qwen → DeepSeek V3.1

**Date:** 2026-04-07 (executed by Claude Opus)
**Task:** Replace ALL Qwen/Qwen3.6 references with DeepSeek V3.1 via OpenRouter
**Commander directive:** "Replace ALL references in Thunderbird code to qwen or qwen3.6 with DeepSeek-V3.1 OpenRouter, also remove erroneous references to DeepSeek chat"

## Scope

- **Total edits:** 170+ across ~40 files
- **Method:** 3 parallel agents (Python, MD, JSON) + manual surgical fixes
- **Preserved:** Historical intel reports, archive files, competitive analysis data (Qwen as market topic)

## Replacement Patterns

| Old Pattern | New Pattern | Context |
|-------------|-------------|---------|
| `opencode/qwen3.6-plus-free` | `openrouter/deepseek/deepseek-chat-v3.1` | OpenCode model ID |
| `qwen/qwen3.6-plus:free` | `deepseek/deepseek-chat-v3.1` | OpenRouter model ID |
| `qwen/qwen3-235b-a22b:free` | `deepseek/deepseek-chat-v3.1` | OpenRouter model ID |
| `qwen/qwen3.5-flash-02-23` | `deepseek/deepseek-chat-v3.1` | Bulk context model |
| `qwen/qwen-2.5-72b-instruct` | `deepseek/deepseek-chat-v3.1` | CrewAI model |
| `qwen/qwen3-32b` | `deepseek/deepseek-chat-v3.1` | Groq connector |
| `deepseek/deepseek-chat:free` | `openrouter/deepseek/deepseek-chat-v3.1` | .opencode.json |
| `deepseek-chat` (without v3.1) | `deepseek-chat-v3.1` | Direct API calls |
| `QWEN_MODEL` | `DEEPSEEK_MODEL` | Python variable names |
| `route_to_qwen` | `route_to_deepseek` | Function/action names |
| `dispatch_to_qwen` | `dispatch_to_deepseek` | Function names |
| `Brain 1: Qwen 3.6 Plus` | `Brain 1: DeepSeek V3.1` | Persona docs |
| `Goose/Qwen` | `OpenCode/DeepSeek` | Routing labels |
| `DeepSeek: PURGED` | *(removed)* | DeepSeek is now primary |

## Files Modified

### Python (operational code)
1. `.opencode.json` — model ID
2. `OpsCenter/nexus.py` — queue tracking, dispatch, routing, model chain
3. `OpsCenter/config.py` — allowed actions
4. `OpsCenter/keyword_router.py` — routing labels, comments, docstrings
5. `OpsCenter/keyword_router_test.py` — test assertions
6. `OpsCenter/hale_dispatcher.py` — Brain 1 model, all Qwen refs
7. `OpsCenter/thunderbird_tasking_watcher.py` — Tier 3 fallback
8. `OpsCenter/task_processor.py` — model variable, fallback comments
9. `OpsCenter/hale_context_scan.py` — model ID, function names
10. `OpsCenter/api_registry.py` — API entries
11. `OpsCenter/master_system_audit_v3.py` — audit model refs
12. `OpsCenter/thunderbird_telegram_gw.py` — telegram gateway model chain
13. `OpsCenter/stress_test.py` — deepseek-chat → deepseek-chat-v3.1
14. `OpsCenter/stress_test2.py` — deepseek-chat → deepseek-chat-v3.1
15. `core/learning/thunderbird_model_router.py` — 30+ replacements (constants, routing tables, aliases, functions)
16. `core/crewai/llm_router.py` — model IDs, base URLs
17. `core/ai_infra/thunderbird_switchblade.py` — text cleanup tag
18. `api/thunderbird_groq_connectors.py` — connector model

### Markdown (operational docs)
19. `AGENTS.md` — model references, decommission note
20. `AGENTS_NEW_TASKING.md` — default model
21. `Personas/hale_cos.md` — Brain 1, Brain dispatch, engine references
22. `hale_brief.md` — OpenCode model status
23. `hale_memory.md` — model routing memory
24. `hale_session_context.md` — scan context
25. `hale_decisions.md` — brain type field
26. `hale_init.md` — scan references
27. `HALE_ASSESSMENT_SUMMARY.md` — brain architecture, migration status
28. `OpsCenter/GOOSE_INIT.md` — model references
29. `OpsCenter/OPENCODE_INIT.md` — model avoidance note
30. `OpsCenter/collaboration/CLAUDE_HEADLESS_TOKEN_GUIDE.md` — Tier 3
31. `OpsCenter/collaboration/OPENCODE_OAUTH_TOKEN_FIX.md` — model ref
32. `OpsCenter/collaboration/NEXUS_MITIGATION_PLAN.md` — 28+ references
33. `OpsCenter/collaboration/NEXUS_AUDIT_REPORT.md` — 8+ references
34. `OpsCenter/client_lifecycle_revision_init.md` — model ref
35. `THUNDERBIRD_MASTER_PLAN.md` — model stack references
36. Various docs/ files — MULTI_MODEL_STACK, GOOSE_HEADLESS_CLAUDE_MAX_GUIDE, etc.

### JSON/Config
37. `hale_state.json` — system_health.opencode field
38. `OpsCenter/mission_board.json` — model references
39. `.claude/CLAUDE.md` — cost guardrails section

### Memory files
40. `MEMORY.md` — index description
41. `project_cost_optimization_apr2026.md` — routing tiers
42. `reference_goose_headless_claude_max.md` — fallback references

## NOT Modified (intentional)

- `intel/*.md` — Historical intel reports (Qwen as market topic)
- `Commander_Review/*.md` — Historical reviews
- `archive/*.html` — Archived content
- `business/*.md` — Historical business docs
- `config/voice_examples.json` — Real email subject line mentioning Qwen
- `OpsCenter/context_goose.json` — Historical context summary
- `core/intel/thunderbird_tech_monitor.py` — Qwen in competitor watch list (correct)
- `core/intel/thunderbird_grok_osint.py` — Qwen in OSINT search queries (correct)
- `OpsCenter/AUTONOMY_BUILD_TRACKER.md` — Historical log entry

## Verification

Run to confirm no operational Qwen refs remain:
```bash
grep -ri "qwen" --include="*.py" --include="*.json" --include="*.yaml" ~/Thunderbird/ | grep -v intel/ | grep -v archive/ | grep -v Commander_Review/ | grep -v business/ | grep -v voice_examples | grep -v context_goose | grep -v _tech_monitor | grep -v _grok_osint | grep -v AUTONOMY_BUILD
```

---
*Executed by Claude Opus 4.6 | 2026-04-07 | Commander-directed*
