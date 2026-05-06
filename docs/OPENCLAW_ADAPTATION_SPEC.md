# OpenClaw Pattern Adaptation — Architecture Spec
## Thunderbird OS · Dreams2Memories Travel, LLC
## 2026-05-03

---

## OVERVIEW

OpenClaw is #1 globally on OpenRouter (11.8T tokens). This spec adapts its 6 key architectural patterns into Thunderbird, layering on top of existing infrastructure without replacing any systems.

---

## P0: Messaging-Based Skill Builder (HIGHEST IMPACT)

### Current State
- ✅ `core/ai_infra/thunderbird_skill_builder.py` — Core engine exists (natural language → Python skill)
- ✅ `core/ai_infra/skill_builder_config.py` — Safety constraints, templates, validation
- ✅ `core/learning/thunderbird_skills_api.py` — Skills API for Files API upload
- ❌ NO `/build-skill` command handler in Telegram C2 bot
- ❌ NO MCP tool registration for skill builder
- ❌ NO hot-reload after skill creation

### Architecture
```
Commander → Telegram C2: /build-skill "description"
  → ThunderbirdSkillBuilder.classify_requirement()
  → ThunderbirdSkillBuilder.generate_skill_code() (Sonnet)
  → Safety validation (skill_builder_config.py)
  → Write to core/<domain>/ + tests/test_<skill>.py
  → MCP server hot-reload (register new tool)
  → Response to Commander with invocation example
```

### File Changes
1. **`core/communication/thunderbird_telegram_c2.py`** — Add `cmd_build_skill` handler
2. **`core/mcp/travel_mcp_server.py`** — Already imports `register_skills_tools` (line 52). Add skill builder MCP tools.
3. **`core/ai_infra/thunderbird_skill_builder.py`** — Add `register_skill_builder_tools()` function for MCP registration

### Dependencies
- Anthropic API (Sonnet for code generation)
- Existing skill builder engine
- MCP server (for tool registration)

---

## P1: Persistent Memory System

### Current State
- ✅ `core/ai_infra/thunderbird_persona_memory.py` — Per-persona memory directories
- ✅ `core/ai_infra/thunderbird_shared_memory.py` — Shared memory across personas
- ✅ `learning/thunderbird_conversation_bridge.py` — Persistent conversation memory
- ❌ NO vector embedding layer
- ❌ NO semantic recall

### Architecture
```
All wing communications → Embedding model → Vector store
  → Semantic search on query
  → Context injection into persona prompts
```

### Implementation
- Use `sentence-transformers` or OpenAI/OpenRouter embeddings
- Index: wing comms, mission outcomes, client interactions, dossier updates
- Store in SQLite with vector extensions or FAISS
- MCP tools: `search_memory_semantic`, `index_memory`, `recall_by_context`

### File Changes
1. **NEW: `core/ai_infra/thunderbird_memory_embeddings.py`** — Vector embedding layer
2. **`core/ai_infra/thunderbird_persona_memory.py`** — Add semantic search methods
3. **`core/mcp/travel_mcp_server.py`** — Register memory embedding tools

---

## P2: Proactive Heartbeat Assessments

### Current State
- ✅ `agents/thunderbird_morning_briefing.py` — Morning briefing (07:00 MDT)
- ✅ `core/ops/thunderbird_usage_monitor.py` — Usage monitoring
- ❌ NO proactive heartbeat cron job
- ❌ NO autonomous optimization scanning

### Architecture
```
Systemd timer (every 2 hours) → heartbeat_assessment.py
  → Scan inbox queues (opencode_inbox, claude_inbox)
  → Scan mission board for stale missions
  → Scan client dossiers for FPD alerts, gaps
  → Scan system health (disk, API quotas, service status)
  → Generate optimization recommendations
  → Alert Commander via Telegram if action needed
```

### File Changes
1. **NEW: `core/ops/thunderbird_heartbeat.py`** — Heartbeat assessment engine
2. **NEW: `deploy/d2m-heartbeat.timer`** — Systemd timer (every 2 hours)
3. **NEW: `deploy/d2m-heartbeat.service`** — Systemd service

---

## P3: Hot-Reloadable Configurations

### Current State
- ✅ `agents/thunderbird_model_dispatcher.py` — Model routing
- ✅ `OpsCenter/keyword_router.py` — Keyword-based traffic control
- ❌ NO file watcher for config changes
- ❌ NO hot-reload without restart

### Architecture
```
watchdog file watcher → detect config change
  → reload keyword_router patterns
  → reload model_dispatcher config
  → reload skill registry
  → NO restart of Telegram bots or MCP server
```

### File Changes
1. **NEW: `core/ops/thunderbird_config_watcher.py`** — File watcher with hot-reload
2. **`agents/thunderbird_model_dispatcher.py`** — Add reload hook
3. **`OpsCenter/keyword_router.py`** — Add reload hook

---

## P4: Multi-Agent Spawn from Chat

### Current State
- ✅ `core/ai_infra/thunderbird_headless_spawn.py` — Safe headless Claude spawn
- ✅ `core/ai_infra/thunderbird_a2a.py` — Agent-to-agent protocol
- ❌ NO `/spawn` command in Telegram C2
- ❌ NO aggregation of multi-agent results

### Architecture
```
Commander → Telegram C2: /spawn 3 "analyze cruise pricing"
  → Spawn 3 OpenCode instances with task variations
  → Each instance works independently
  → Aggregate results → consolidated report
  → Send to Commander
```

### File Changes
1. **`core/communication/thunderbird_telegram_c2.py`** — Add `cmd_spawn` handler
2. **NEW: `core/ai_infra/thunderbird_multi_agent.py`** — Multi-agent orchestration + aggregation

---

## P5: OAuth Self-Provisioning

### Current State
- ✅ `api/thunderbird_google_auth.py` — Google OAuth authorization
- ✅ `core/ai_infra/thunderbird_headless_spawn.py` — OAuth token loading
- ❌ NO self-healing OAuth module
- ❌ NO automatic token refresh detection + re-auth

### Architecture
```
Token expiry detector → detect expired/invalid tokens
  → Launch headless browser (Playwright)
  → Complete OAuth flow automatically
  → Store new tokens in creds/
  → Notify Commander
```

### File Changes
1. **NEW: `core/ops/thunderbird_oauth_self_heal.py`** — Self-healing OAuth module
2. **`api/thunderbird_google_auth.py`** — Add headless browser flow

---

## IMPLEMENTATION ORDER

1. **P0** — Messaging-Based Skill Builder (this session)
2. **P4** — Multi-Agent Spawn from Chat (this session)
3. **P2** — Proactive Heartbeat Assessments (this session)
4. **P3** — Hot-Reloadable Configurations (future)
5. **P1** — Persistent Memory System (future — requires embedding model)
6. **P5** — OAuth Self-Provisioning (future — requires Playwright browser automation)

---

## INTEGRATION POINTS

| Module | Integrates With |
|--------|----------------|
| P0 Skill Builder | Telegram C2, MCP Server, Anthropic Sonnet |
| P1 Memory | Persona memory, shared memory, conversation bridge |
| P2 Heartbeat | Systemd timers, Telegram C2, mission board, dossiers |
| P3 Config Watcher | Model dispatcher, keyword router, skill registry |
| P4 Multi-Agent | Headless spawn, A2A protocol, OpenCode |
| P5 OAuth Self-Heal | Google auth, Playwright, creds/ |

---

## SAFETY GUARANTEES

1. NO client-facing output without Commander approval (WF-17 gate)
2. NO replacement of existing systems — layer on top
3. All generated skills validated against safety constraints
4. All spawned agents use foolproof headless spawn wrapper
5. All OAuth operations require Commander notification
