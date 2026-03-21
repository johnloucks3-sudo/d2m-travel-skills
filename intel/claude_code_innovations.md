# CLAUDE CODE & ANTHROPIC ECOSYSTEM — INNOVATION SCAN
## Dreams2Memories Travel, LLC — Thunderbird OS
## Compiled: 2026-03-20 | Classification: INTERNAL

---

## D2M RELEVANCE SUMMARY

- **Channels (Telegram push)** is the single most important innovation for Thunderbird. It replaces our custom C2 bot architecture with Anthropic's official, maintained pipeline — less code, better reliability, mobile command of the Wing from anywhere.
- **Agent Teams** formalizes what we've been doing ad hoc with `consult_persona` and staff meetings. A2/A3/A5/A9 can now run as true parallel agents with shared task lists and direct inter-agent messaging.
- **Subagent persistent memory** gives each Wing persona (Dani, Hale, Dembe, etc.) a learning memory that survives across sessions — the 8 Staff Skills ("capture the diff, extract the principle, apply forward") finally have a native persistence layer.
- **MCP Connector on API** eliminates the need for local MCP client code when calling remote servers — our cloudflared tunnel to Yoga could be replaced with direct API-level MCP calls.
- **Code Execution with MCP** pattern achieves 98.7% token reduction by having Claude write code against MCP tools instead of calling them individually — critical for our 120+ tool server where token burn is real.

---

## 1. CLAUDE CODE — NEW FEATURES

### 1.1 Channels (Push Events into Sessions)
**What:** MCP servers can now push messages, alerts, and webhooks into a running Claude Code session. Launched March 20, 2026 as research preview.
**How it works:** `--channels` flag on session start. Official Telegram and Discord plugins ship first. Two-way: Claude reads events AND replies back through the same channel. Sender allowlist for security.
**D2M Application:**
- Replace custom `thunderbird_telegram_c2.py` with official Anthropic Telegram channel plugin
- Commander messages Telegram bot → pushes into Claude Code session → Claude has full local env access (files, git, MCP tools) → replies back via Telegram
- Morning briefing alerts, payment deadline warnings, client emails — all push into active session
- n8n webhook events (booking confirmations, commission notices) can push directly into Claude
**Implementation:** Install Telegram channel plugin, configure sender allowlist (Commander's Telegram ID), add `--channels telegram` to session launch
**Priority:** **NOW** — This is the official replacement for our custom C2 architecture

### 1.2 Agent Teams (Parallel Multi-Agent Coordination)
**What:** Multiple independent Claude Code sessions coordinating via shared task lists, inter-agent messaging, and centralized team lead. Experimental, enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
**How it works:** Lead session spawns teammates, each with own context window. Shared task list with claim/complete semantics. Direct teammate-to-teammate messaging. In-process or tmux split-pane display.
**D2M Application:**
- **Staff Meeting workflow:** COS (lead) spawns A2 (intel), A3 (logistics), A5 (strategy), A9 (finance) as real parallel agents
- **Client Research:** "Create a team with A2, A3, A9 to research Mediterranean options for the Kuklinski group" — each agent works independently, shares findings, challenges each other's analysis
- **Competing hypotheses debugging:** Multiple agents investigate booking discrepancies from different angles
- **Cross-domain proposals:** Frontend (portal), backend (API), content (Dani engine) worked in parallel
**Implementation:** Already have `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in CLAUDE.md. Create Wing agent definitions in `.claude/agents/` mapping to D2M personas.
**Priority:** **NOW** — We're already set up for this conceptually

### 1.3 Custom Subagents with Persistent Memory
**What:** Subagents are specialized AI assistants defined as Markdown files with YAML frontmatter. Each gets custom system prompt, tool restrictions, model selection, and persistent memory directory.
**How it works:** Files in `.claude/agents/` or `~/.claude/agents/`. Memory scopes: `user` (cross-project), `project` (version-controlled), `local` (gitignored). Memory stored as files in `agent-memory/` directories.
**D2M Application:**
- **Dani subagent** with `memory: project` — accumulates client voice preferences, relationship context, email tone patterns across sessions. The 8 Staff Skills become automatic.
- **Hale (COS) subagent** with `memory: user` — retains operational patterns, standing orders, Commander preferences globally
- **Dembe (A2) subagent** with `memory: project` — builds intel knowledge base over time, remembers which sources were useful for which clients
- **Harlan (A9) subagent** with `memory: project` — commission patterns, vendor rate history, markup calculations
- Each persona loads their character sheet via `skills` frontmatter field
**Implementation:** Create `.claude/agents/dani.md`, `.claude/agents/hale.md`, etc. with persona-specific prompts, tool restrictions, and memory scope.
**Priority:** **NOW** — Direct upgrade to `consult_persona` MCP tool

### 1.4 /loop (Recurring Task Automation)
**What:** Run a prompt or slash command on a recurring interval. `/loop 5m check the deploy` runs every 5 minutes.
**How it works:** Session-level cron. Configurable interval (default 10m). Can run slash commands or natural language prompts.
**D2M Application:**
- `/loop 30m scan commander inbox for new client emails` — real-time email monitoring
- `/loop 1h run payment deadline check` — proactive payment alerts
- `/loop 4h run competitive surveillance sweep` — cruise line price monitoring
- `/loop 15m check Telegram C2 for pending commands` — C2 heartbeat
- `/loop 2h run dossier scanner for gaps` — proactive dossier maintenance
**Implementation:** Add to session startup scripts or systemd service definitions
**Priority:** **NOW** — Replaces multiple systemd timers with in-session automation

### 1.5 Voice Mode (Push-to-Talk)
**What:** `/voice` command activates push-to-talk. Hold spacebar to speak, release to send. 20 languages supported. Optimized for technical terms.
**How it works:** Rolling out progressively (~5% of users in early March, expanding). Custom keybinding via `keybindings.json`. Works in terminal.
**D2M Application:**
- Commander dictates client notes, booking changes, or directives while mobile — no typing required
- Voice-driven trip planning sessions: "Dani, draft an email to the Furlows about their Finnair seat assignments"
- Hands-free operation on Chromebook during travel
**Implementation:** `/voice` in session. Rebind push-to-talk key if needed.
**Priority:** **SOON** — Waiting for broader rollout

### 1.6 /batch and /simplify (Bundled Slash Commands)
**What:** `/batch` runs multiple operations in sequence. `/simplify` reviews changed code for reuse, quality, and efficiency, then fixes issues.
**How it works:** Built-in slash commands, no configuration needed.
**D2M Application:**
- `/batch` to chain operations: scan inbox → update dossiers → generate morning brief → send via Telegram
- `/simplify` after any code changes to Thunderbird modules — automatic refactoring
**Implementation:** Available immediately in current Claude Code version
**Priority:** **SOON**

### 1.7 /effort (Adaptive Thinking Control)
**What:** Set model effort level per session or per skill. Options: `low`, `medium`, `high`, `max` (Opus 4.6 only).
**How it works:** `/effort high` in session, or `effort: high` in subagent/skill frontmatter.
**D2M Application:**
- **max** for client proposals, grant narratives, complex booking analysis
- **high** for standard operations, email drafting, dossier updates
- **medium** for routine queries, quick lookups
- **low** for status checks, simple file operations
- Each D2M subagent can have appropriate effort level baked in
**Implementation:** Add `effort` field to each persona subagent definition
**Priority:** **SOON** — Cost optimization lever

### 1.8 /btw (Side Questions)
**What:** Quick question that sees full conversation context but has no tool access. Answer is discarded after display (not added to history).
**How it works:** `/btw what was the commission rate we discussed?` — reads context, answers, doesn't consume context going forward.
**D2M Application:**
- Quick Commander questions during complex sessions without derailing the workflow
- "btw what was the Lyons' embarkation date?" without spawning a subagent or losing context
**Implementation:** Available immediately
**Priority:** **SOON**

### 1.9 /statusline (Custom Status Bar)
**What:** Customizable bottom bar showing real-time session metrics. Runs any shell script, receives JSON session data.
**How it works:** `/statusline` generates a script, or configure manually. Community tools: ccstatusline (Rust), claude-statusline (Go).
**D2M Application:**
- Display: active persona, current client context, token usage, git branch, active MCP connections
- Show pending Telegram messages count, unread Commander inbox items
- Commission calculations in progress, dossier completeness score
**Implementation:** Create custom statusline script showing D2M-relevant metrics
**Priority:** **WATCH**

### 1.10 Plugins & Marketplace
**What:** Plugin system for distributing skills, commands, agents, hooks, and MCP servers. 834+ plugins across 43 marketplaces.
**How it works:** `plugin.json` schema. Install via `/plugin marketplace add`. User, project, or local scope. Official Anthropic marketplace + community marketplaces.
**D2M Application:**
- Package Thunderbird OS components as plugins for potential distribution to other travel agencies
- Install community plugins for Canva integration (already connected via MCP), n8n workflow building, Telegram channel support
- Create D2M-specific marketplace for internal tooling
**Implementation:** Package existing skills/agents as plugin with `plugin.json`
**Priority:** **WATCH**

### 1.11 Worktree Isolation
**What:** `--worktree` flag creates isolated git worktree for each Claude session. Auto-cleanup on exit if no changes.
**How it works:** Creates `.claude/worktrees/<name>/` with isolated branch. Multiple sessions can work on same repo simultaneously.
**D2M Application:**
- Parallel development on Thunderbird modules without conflicts
- Test experimental features (new MCP tools, API endpoints) without risking main branch
- Agent teams can each work in their own worktree
**Implementation:** `claude --worktree` for isolated sessions
**Priority:** **SOON** — Already using worktrees (this session is in one)

---

## 2. CLAUDE AGENT SDK

### 2.1 Three-Layer Architecture (MCP + Skills + SDK)
**What:** Anthropic's agent stack: MCP (protocol for agent-tool communication), Agent Skills (portable capability packages), Agent SDK (runtime). Python v0.1.48, TypeScript v0.2.71.
**D2M Application:**
- Thunderbird OS maps perfectly to this: MCP (travel_mcp_server.py), Skills (persona instructions), SDK (telegram C2, batch runner)
- Align our architecture to Anthropic's official patterns for long-term maintainability
**Priority:** **NOW** — Architectural alignment

### 2.2 Programmatic / Headless Mode
**What:** Run Claude non-interactively via CLI (`-p` flag), Python SDK, or TypeScript SDK. Structured JSON output, session chaining, tool restrictions, streaming.
**How it works:** `claude -p "prompt" --output-format json`, or Python/TS SDK imports. Session resume via session IDs.
**D2M Application:**
- `thunderbird_batch_run.py` should use official Agent SDK instead of custom subprocess calls
- CI/CD pipeline for Thunderbird code quality (auto-review PRs, lint, test)
- Scheduled headless tasks: morning briefing generation, commission reconciliation, dossier scanning
- Chain sessions: intel gather → analysis → email draft → COS review → send
**Implementation:** Migrate batch runner to Agent SDK Python package
**Priority:** **NOW**

### 2.3 Memory Tool (Official API Primitive)
**What:** Official Anthropic memory tool for agents. Stores/retrieves information across conversations via memory file directory. 84% token reduction in extended workflows.
**How it works:** Visible tool calls — you can inspect exactly what's stored and retrieved. Combines with context editing (auto-clears old tool results when context grows).
**D2M Application:**
- Replace `thunderbird_shared_memory.py` and `hud_memory.db` with official memory primitive
- Each Wing persona gets a memory scope — Dani remembers client preferences, Hale remembers operational patterns
- Voice ledger entries persist automatically through memory tool
- Client relationship context survives across sessions without manual CLAUDE.md updates
**Implementation:** Enable memory tool in API calls, configure per-persona memory directories
**Priority:** **NOW** — Our biggest pain point (context loss between sessions)

### 2.4 Claude-Mem Plugin (Community)
**What:** Third-party plugin that auto-captures every tool invocation, compresses via Agent SDK, stores in SQLite with full-text search. ~10x token efficiency.
**How it works:** Observes tool I/O → semantic compression → SQLite storage → retrieval layers
**D2M Application:**
- Layer on top of official memory for comprehensive session capture
- Auto-document every booking change, client interaction, commission calculation
- Searchable history: "What did we discuss with the Furlows about Finnair in the last 3 sessions?"
**Implementation:** `npm install claude-mem` or equivalent plugin install
**Priority:** **SOON**

---

## 3. ANTHROPIC API

### 3.1 MCP Connector (Server-Side)
**What:** Connect to remote MCP servers directly from Messages API via `mcp_servers` parameter. No local client code needed. Anthropic handles connection management, tool discovery, error handling.
**How it works:** Pass MCP server URL + optional OAuth token in API request. Beta header required.
**D2M Application:**
- Chromebook → API call with `mcp_servers: [{url: "https://mcp.d2mluxury.quest"}]` → Yoga MCP tools
- Eliminates need for cloudflared tunnel for MCP specifically (though tunnel still useful for API/portal)
- Third-party MCP servers (Zapier, Asana, travel APIs) accessible without local setup
- Telegram bot can call API with MCP connector instead of maintaining local MCP client
**Implementation:** Update API calls to include `mcp_servers` parameter pointing to Yoga
**Priority:** **NOW** — Simplifies our architecture significantly

### 3.2 Code Execution Tool
**What:** Anthropic-hosted sandbox for running code. 50 free hours/day per org, $0.05/hr after.
**How it works:** `type: "code_execution"` tool in API request. Sandboxed container with Python, common libraries.
**D2M Application:**
- Commission calculations in sandboxed environment (no risk to local system)
- Data analysis on booking spreadsheets without local compute
- PDF generation, Excel manipulation in cloud sandbox
- Client-facing portal can offload compute-heavy operations
**Implementation:** Add `code_execution` tool to API requests where computation is needed
**Priority:** **SOON**

### 3.3 Code Execution WITH MCP (Pattern)
**What:** Instead of calling MCP tools individually (150k tokens), have Claude write and run code that calls MCP tools programmatically (2k tokens). 98.7% token reduction.
**How it works:** Claude writes a script that imports MCP tool functions, loops over data, processes results — one code execution call instead of 50 individual tool calls.
**D2M Application:**
- Batch booking operations: instead of 10 separate `tess_get_booking` calls, one script that iterates
- Commission reconciliation: single script that pulls all data, calculates, compares
- Multi-client fare watch: one execution that checks all watched routes
- Dossier scanner: single script that evaluates all dossiers for gaps
- **This is transformative for our 120+ tool server** — biggest cost/speed optimization available
**Implementation:** Refactor batch operations to use code execution pattern. May require exposing MCP tools as importable Python functions.
**Priority:** **NOW** — Immediate ROI on token costs

### 3.4 Files API
**What:** Upload files (PDF, DOCX, TXT, CSV, Excel, images) to `/v1/files`. Up to 350MB per file. Chunking for long documents. Citations to specific pages/sections.
**How it works:** Upload file → reference in messages → Claude reads with citations. Beta header required.
**D2M Application:**
- Upload booking confirmations (PDFs) and have Claude extract + cite specific terms
- Client documents (passports, travel insurance) securely stored via API
- Upload supplier rate sheets → auto-extract pricing with source citations
- Grant narrative drafts → Claude reviews with specific page/paragraph references
**Implementation:** Integrate Files API into `thunderbird_files_api.py` (already exists as module)
**Priority:** **SOON**

### 3.5 Citations API
**What:** Claude provides source attribution for claims. Cites specific passages from provided documents.
**How it works:** Add source documents to context → Claude automatically cites claims in output with document references.
**D2M Application:**
- Cruise line comparison reports with cited sources (brochures, websites, reviews)
- Intel reports citing specific articles, advisories, or data sources
- Client proposals referencing specific hotel reviews, excursion descriptions
- Grant narratives with properly cited statistics and claims
**Implementation:** Enable citations in API calls for intel and research outputs
**Priority:** **SOON**

### 3.6 Prompt Caching (1-Hour TTL)
**What:** Cache frequently used prompts for up to 1 hour. 90% cost reduction on cached reads. Stacks with batch processing (50% off) for up to 95% savings.
**How it works:** Set `cache_control` with `ttl: "1h"` on system prompts, persona definitions, or large context blocks. Max plan gets 1-hour automatically.
**D2M Application:**
- Cache persona system prompts (Dani character sheet, COS instructions) — reused constantly
- Cache client dossiers during active booking sessions
- Cache cruise line reference data, ship specifications
- Morning briefing template + intel data cached for the full briefing cycle
- **With Max plan, we already get 1-hour TTL automatically**
**Implementation:** Ensure system prompts use cache_control breakpoints at persona definitions
**Priority:** **NOW** — Free optimization on Max plan

### 3.7 Message Batches API
**What:** Submit large batches of messages for 50% cost reduction. Async processing with result polling.
**How it works:** POST batch of messages → receive batch ID → poll for results. 24-hour processing window.
**D2M Application:**
- `thunderbird_batch_run.py` 13 batch jobs → submit as Message Batch for 50% savings
- Bulk client email drafting (holiday greetings, trip reminders)
- Mass intel analysis (process 50 news articles at batch pricing)
- Weekly commission reconciliation across all active bookings
**Implementation:** Convert batch runner to use Batches API
**Priority:** **SOON** — Significant cost reduction

### 3.8 Token-Efficient Tool Use
**What:** Reduced token overhead when using tools. Fine-grained tool streaming GA on all models.
**D2M Application:**
- Direct benefit to our 120+ tool MCP server — every tool call costs less
- Real-time streaming of tool results to Telegram C2
**Implementation:** Ensure latest API version is used; benefit is automatic
**Priority:** **NOW** — Automatic benefit

### 3.9 Opus 4.6 Capabilities
**What:** 1M context window, 128k max output, adaptive thinking (auto-decides when to think deeply), `max` effort level, web search/fetch with dynamic filtering, compaction for infinite conversations, fast mode (2.5x speed at premium pricing).
**D2M Application:**
- 1M context = load entire client dossier + booking history + correspondence in one session
- 128k output = generate complete multi-day itineraries, full grant narratives in single response
- Adaptive thinking = Commander doesn't need to specify when to think deep vs. fast
- Compaction = sessions can run indefinitely without losing critical context
- Fast mode for time-sensitive operations (live booking, client on phone)
**Implementation:** Already using Opus 4.6 as default model
**Priority:** **NOW** — Already active, optimize usage

---

## 4. MCP ECOSYSTEM

### 4.1 Streamable HTTP Transport (Production-Ready)
**What:** MCP servers as remote services via HTTP. OAuth 2.1 authorization. `.well-known` URL discovery. Tool annotations (read-only vs. write).
**D2M Application:**
- Expose `travel_mcp_server.py` as proper Streamable HTTP service with OAuth
- Third-party travel MCP servers (Expedia, TourRadar) accessible via standard HTTP
- Load balancer friendly — horizontal scaling for peak booking seasons
**Implementation:** Add Streamable HTTP transport to MCP server alongside existing stdio/SSE
**Priority:** **SOON**

### 4.2 TravelOS MCP Server (Agentic Hospitality)
**What:** Production MCP server connecting hotel reservation systems to AI platforms. Real-time availability, rates, inventory inside AI interfaces.
**D2M Application:**
- Direct hotel availability queries without browser scraping
- Rate comparison across properties via standardized MCP interface
- Booking capability through AI interface — Dani could book directly
- Integration with our hotel search modules
**Implementation:** Evaluate TravelOS MCP server compatibility with our hotel search pipeline
**Priority:** **SOON** — Monitor for cruise line equivalents

### 4.3 n8n MCP Server
**What:** MCP server exposing n8n workflows as executable tools. Build, validate, and deploy n8n workflows from Claude Code.
**How it works:** Describe automation in natural language → Claude creates n8n workflow → deploys to your instance.
**D2M Application:**
- We already run 16 n8n workflows in `deploy/n8n/`. This lets Claude build and modify them directly.
- "Claude, create an n8n workflow that monitors d2mconcierge@gmail.com for booking confirmations and updates the dossier"
- Rapid prototyping of new automation workflows without manual n8n editor work
- Self-healing workflows: Claude detects n8n failures and fixes them
**Implementation:** Install n8n MCP server, connect to Yoga's n8n instance
**Priority:** **NOW** — Direct productivity multiplier for our n8n stack

### 4.4 MCP Gateway (Meta-Server)
**What:** Progressive disclosure server that exposes 9 meta-tools, dynamically provisions 25+ MCP servers on-demand. Reduces tool bloat.
**D2M Application:**
- Our 120+ tools create massive context overhead. Gateway could dynamically load only relevant tools per session.
- Client booking session → loads only booking/dossier/email tools
- Intel session → loads only research/web/analysis tools
- Reduces token cost and improves focus
**Implementation:** Evaluate MCP Gateway for D2M tool organization
**Priority:** **WATCH**

### 4.5 Canva MCP (Already Connected)
**What:** Design generation, editing, export via MCP. 32 tools for visual content.
**D2M Application:**
- Already connected (see MCP tool list). Use for:
- Client proposal visuals, trip brochures, social media content
- D2M brand materials automated generation
- Itinerary cover pages, destination mood boards
**Implementation:** Already available — increase utilization
**Priority:** **NOW** — Underutilized existing capability

### 4.6 Home Assistant MCP
**What:** Smart home control via MCP server integration.
**D2M Application:** Unconventional pick per Commander's "even some unreasonable innovations" directive:
- Office automation during work hours (lighting, temperature for focus)
- Demo capability for luxury travel clients who want smart hotel room control
**Implementation:** Install Home Assistant MCP if smart home devices present
**Priority:** **WATCH**

### 4.7 Agent-to-Agent (A2A) Economy via MCP
**What:** MCP roadmap includes agent-to-agent communication. Agents negotiate, delegate, coordinate without central orchestrator.
**D2M Application:**
- Dani agent negotiates with hotel/cruise line AI agents directly
- Booking agents from multiple suppliers coordinate availability checks
- Commission reconciliation agents from D2M and supplier sides validate independently
- This is the future of luxury travel booking — AI concierge to AI reservation system
**Implementation:** Monitor MCP roadmap; prepare Dani for A2A interactions
**Priority:** **WATCH** — 6-12 month horizon

---

## 5. COMMUNITY INNOVATIONS

### 5.1 Claude-Mem (Persistent Memory Compression)
**What:** Auto-captures every tool invocation, compresses with Agent SDK, stores in SQLite. 10x token efficiency. Full-text search across session history.
**D2M Application:** (See 2.4 above)
**Priority:** **SOON**

### 5.2 ccstatusline / claude-statusline
**What:** Community status bar tools (Rust/Go) with powerline styling, token tracking, git integration.
**D2M Application:** Custom D2M status bar showing Wing status, client context, token burn rate
**Priority:** **WATCH**

### 5.3 StudioMCPHub (Creative AI Tools)
**What:** 32 creative AI tools: image generation, upscaling, background removal, product mockups, watermarking, SVG vectorization.
**D2M Application:**
- Auto-generate destination imagery for proposals
- Upscale client-submitted photos for itinerary books
- Background removal for clean property photos
- Watermark D2M brand on shared images
**Implementation:** Install StudioMCPHub MCP server
**Priority:** **SOON**

### 5.4 Excalidraw Architect MCP
**What:** Auto-layout architecture diagrams with 50+ technology mappings.
**D2M Application:**
- Generate Thunderbird OS architecture diagrams for grant proposals
- Visual system maps for consultant presentations
- Client trip flow diagrams (airports → transfers → hotels → excursions)
**Priority:** **WATCH**

### 5.5 Firecrawl / Apify MCP Servers
**What:** Web scraping and data extraction via MCP.
**D2M Application:**
- Structured scraping of cruise line websites for pricing, availability
- Hotel review aggregation from multiple sources
- Competitor pricing intelligence
- Supplement existing `browse_url` and `bedsonline_browse_search` tools
**Implementation:** Install Firecrawl or Apify MCP server
**Priority:** **SOON**

### 5.6 Scheduled Tasks MCP (Already Connected)
**What:** Create scheduled tasks that run on demand or automatically on interval.
**D2M Application:**
- Already connected (see MCP tool list). Use for:
- Automated morning briefing generation
- Scheduled commission reconciliation
- Periodic dossier gap scanning
- Regular competitive surveillance sweeps
**Implementation:** Already available — create scheduled task definitions
**Priority:** **NOW** — Underutilized existing capability

### 5.7 Skills Gallery (Community Skills)
**What:** 192+ Claude Code skills across engineering, marketing, product, compliance, C-level advisory. Open standard works across Claude Code, Codex, Gemini CLI, Cursor.
**D2M Application:**
- `doc-coauthor` skill for grant narrative assistance
- `brand-guidelines` skill (already available) for D2M visual consistency
- `canvas-design` skill (already available) for proposal visuals
- PDF, DOCX, XLSX, PPTX skills (already available) for client deliverables
- `mcp-builder` skill (already available) for new MCP tool development
- `skill-creator` skill (already available) for building D2M-specific skills
**Implementation:** Audit available skills against D2M needs; install priority matches
**Priority:** **NOW**

---

## 6. HOOKS SYSTEM (EXPANDED)

### 6.1 HTTP Hooks (v2.1.63+)
**What:** POST JSON to a URL instead of running shell commands. No local scripts needed.
**D2M Application:**
- Hook into Thunderbird API endpoints directly: `PostToolUse` → POST to `api.d2mluxury.quest/log`
- Telegram notifications on specific events without local webhook scripts
- n8n workflow triggers from Claude Code events
**Implementation:** Convert shell hooks to HTTP hooks pointing at Thunderbird API
**Priority:** **NOW** — Simplifies our hooks architecture

### 6.2 PostCompact Hook
**What:** Fires after context compaction. Receives `compact_summary` with conversation summary.
**D2M Application:**
- Auto-save compaction summaries to session logs
- Push compaction summary to Telegram C2 so Commander knows what was preserved
- Feed compaction summaries into memory system for long-term retention
**Implementation:** Add PostCompact hook to settings.json
**Priority:** **SOON**

### 6.3 Elicitation / ElicitationResult Hooks
**What:** Intercept and override MCP server elicitation dialogs (form fields, browser URLs) and user responses.
**D2M Application:**
- Auto-fill common elicitation fields (client names, booking IDs)
- Validate user responses before sending to MCP servers
- Log all elicitation interactions for audit trail
**Implementation:** Add Elicitation hooks for commonly used MCP tools
**Priority:** **WATCH**

### 6.4 SubagentStart / SubagentStop Hooks
**What:** Hooks that fire when subagents begin or complete execution. Matcher targets specific agent types.
**D2M Application:**
- Log persona activations: "Dani started for Furlow email at 14:32"
- Setup/teardown for persona-specific resources (load client dossier on Dani start)
- Aggregate subagent results for COS review
**Implementation:** Add SubagentStart/SubagentStop hooks for Wing personas
**Priority:** **SOON**

### 6.5 TeammateIdle / TaskCompleted Hooks (Agent Teams)
**What:** Quality gates for agent teams. Exit code 2 sends feedback and keeps agent working / blocks task completion.
**D2M Application:**
- COS quality gate: no client deliverable marked complete without COS review
- Dani outputs must pass voice ledger check before completion
- Intel reports must include D2M Relevance Summary before marking done
**Implementation:** Create validation scripts for Wing quality standards
**Priority:** **SOON** — When agent teams are production-ready

---

## 7. ARCHITECTURE & COST OPTIMIZATION

### 7.1 Model Router by Effort Level
**What:** Each subagent/skill can specify model + effort independently.
**D2M Application:**
- Haiku for quick lookups, file scanning, status checks (A2 initial research)
- Sonnet for standard drafting, analysis, data processing (Dani email drafts, Harlan reports)
- Opus for complex client proposals, grant narratives, strategic analysis (EXEC, full staff meetings)
- Already have `thunderbird_model_router.py` — align with native effort/model system
**Implementation:** Map persona workloads to model tiers in subagent definitions
**Priority:** **NOW** — Direct cost savings

### 7.2 Prompt Caching + Batch Stacking
**What:** 90% savings (caching) + 50% savings (batch) = up to 95% cost reduction when combined.
**D2M Application:**
- Batch morning briefing generation with cached persona prompts
- Batch commission reconciliation across all bookings
- Batch dossier scanning with cached dossier templates
**Implementation:** Refactor batch runner to use Batches API with cache breakpoints
**Priority:** **SOON**

### 7.3 Compaction for Infinite Sessions
**What:** Auto-compaction at ~95% context. Configurable threshold via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`.
**D2M Application:**
- Long-running booking sessions that span hours without context loss
- Marathon grant writing sessions
- Multi-client morning briefing generation in single session
**Implementation:** Set compaction threshold to 80% for proactive summarization
**Priority:** **NOW** — Configure optimal threshold

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: NOW (This Week)
1. Create Wing persona subagents in `.claude/agents/` with persistent memory
2. Install and configure Telegram Channels plugin (replace custom C2)
3. Install n8n MCP server (connect to existing n8n workflows)
4. Enable Agent Teams for staff meeting workflow
5. Implement code execution with MCP pattern for batch operations
6. Convert shell hooks to HTTP hooks pointing at Thunderbird API
7. Audit and activate underutilized existing capabilities (Canva MCP, Scheduled Tasks MCP)

### Phase 2: SOON (This Month)
1. Migrate batch runner to Agent SDK + Batches API
2. Integrate Files API for document management
3. Set up /loop monitoring for key operational tasks
4. Install StudioMCPHub for creative asset generation
5. Add PostCompact and SubagentStart/Stop hooks
6. Implement MCP Connector for simplified Chromebook→Yoga access
7. Voice mode activation when available

### Phase 3: WATCH (Next Quarter)
1. Monitor MCP A2A developments for AI-to-AI booking
2. Evaluate MCP Gateway for tool organization
3. Track TravelOS and hospitality MCP servers
4. Plugin marketplace for D2M distribution
5. Excalidraw for architecture documentation
6. Home Assistant integration (if applicable)

---

## SOURCES

### Claude Code Features
- [Custom Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams)
- [Channels Documentation](https://code.claude.com/docs/en/channels)
- [Skills Documentation](https://code.claude.com/docs/en/skills)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Headless Mode / SDK](https://code.claude.com/docs/en/headless)
- [Statusline Customization](https://code.claude.com/docs/en/statusline)
- [Claude Code Changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [March 2026 Updates Overview](https://pasqualepillitteri.it/en/news/381/claude-code-march-2026-updates)
- [Claude Code Release Notes](https://releasebot.io/updates/anthropic/claude-code)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [VS Code Extension](https://code.claude.com/docs/en/vs-code)

### Anthropic API
- [Files API](https://docs.anthropic.com/en/docs/build-with-claude/files)
- [Citations API](https://docs.anthropic.com/en/docs/build-with-claude/citations)
- [Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [MCP Connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector)
- [Memory Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- [Agent Capabilities Announcement](https://www.anthropic.com/news/agent-capabilities-api)
- [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [What's New in Claude 4.6](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6)
- [Claude Opus 4.6](https://www.anthropic.com/claude/opus)
- [API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)

### Agent SDK
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Building Agents with Agent SDK](https://blog.promptlayer.com/building-agents-with-claude-codes-sdk/)
- [Complete Guide to Building Agents](https://nader.substack.com/p/the-complete-guide-to-building-agents)
- [Microsoft Agent Framework Integration](https://devblogs.microsoft.com/semantic-kernel/build-ai-agents-with-claude-agent-sdk-and-microsoft-agent-framework/)

### MCP Ecosystem
- [2026 MCP Roadmap](http://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP Production Challenges](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [MCP Auth (Stack Overflow)](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol/)
- [Streamable HTTP Security (Auth0)](https://auth0.com/blog/mcp-streamable-http/)
- [Official MCP Servers (GitHub)](https://github.com/modelcontextprotocol/servers)
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)
- [Azure Functions MCP Support](https://www.infoq.com/news/2026/01/azure-functions-mcp-support/)

### Travel Industry MCP
- [MCP Servers in Travel (AltexSoft)](https://www.altexsoft.com/blog/mcp-servers-travel/)
- [TravelOS MCP Server Launch](https://www.hospitalitynet.org/news/4131210/agentic-hospitality-launches-travelos-mcp-server-enabling-agentic-hotel-distribution-inside-ai-platforms)
- [Agentic Hotel Distribution](https://www.hospitalitynet.org/opinion/4127875.html)
- [MCP Impact on Travel](https://thepaypers.com/payments/interviews/understanding-mcp-and-its-impact-on-the-travel-industry)

### Community & Tools
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Community Skills (192+)](https://github.com/alirezarezvani/claude-skills)
- [n8n MCP Server](https://github.com/czlonkowski/n8n-mcp)
- [n8n Skills for Claude Code](https://github.com/czlonkowski/n8n-skills)
- [Claude-Mem Plugin](https://github.com/thedotmack/claude-mem)
- [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service)
- [Claude Code Telegram Bot](https://github.com/RichardAtCT/claude-code-telegram)
- [Official Telegram Plugin](https://github.com/anthropics/claude-plugins-official/blob/main/external_plugins/telegram/README.md)
- [Best MCP Servers 2026 (Builder.io)](https://www.builder.io/blog/best-mcp-servers-2026)
- [Best MCP Servers 2026 (Firecrawl)](https://www.firecrawl.dev/blog/best-mcp-servers-for-developers)
- [Most Popular MCP Tools 2026 (FastMCP)](https://fastmcp.me/blog/most-popular-mcp-tools-2026)

---

*Staff Paper from Col Victoria "Iron Vic" Hale, Chief of Staff, D2M Travel*
*Classification: INTERNAL — Commander's Eyes*
