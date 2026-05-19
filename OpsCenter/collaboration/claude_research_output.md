# THUNDERBIRD INTEL — World-Wide Tech Search
## "Claude Code" · "Claude" · "Goose" · "Goose Alternatives" — Collaboration Focus
### Prepared by: Claude (Opus 4.6) · GT-20260331-2001-RESE · 2026-03-31 ~20:05 MT

---

## D2M RELEVANCE SUMMARY

The collaboration landscape for AI coding agents has fundamentally shifted in Q1 2026. Three developments matter most for Thunderbird:

1. **Our Claude+Goose dual-agent architecture is now an industry pattern** — the blackboard/shared-memory model we use in OpsCenter maps directly to formalized "blackboard architecture" emerging in multi-agent research. We were early.
2. **Google's A2A Protocol hit v1.0** — agent-to-agent communication is now a Linux Foundation standard alongside MCP. This is the "collaboration" protocol layer we should watch for Thunderbird interop.
3. **Claude Code Agent Teams went live with Opus 4.6** — native multi-agent with inter-agent messaging, shared task lists, and Git worktree isolation. This is a capability upgrade available to us now.

---

## SECTION 1: CLAUDE CODE — COLLABORATION FEATURES

### 1A. Agent Teams (Native Multi-Agent)

**Status:** Research preview, shipped Feb 6, 2026 with Opus 4.6. Requires Claude Code v2.1.32+.

**Architecture:**
- One **lead agent** orchestrates; multiple **teammate agents** work independently in their own context windows and Git worktrees
- Teammates **message each other directly** — no bottleneck through the lead
- Shared task list with dependency tracking and claim system
- Key difference from subagents: subagents report only to parent; teammates collaborate peer-to-peer

**March 2026 stability fixes:**
- Nested teammate spawning bug fixed (teammates accidentally spawning more teammates)
- Memory leak resolved (parent conversation history was pinned for each teammate's lifetime)

**Best use cases:** Parallel research, multi-module development, competing-hypothesis debugging, cross-layer coordination (frontend + backend + tests)

**Sources:**
- [Official Docs: Agent Teams](https://code.claude.com/docs/en/agent-teams)
- [Sean Kim: TeammateTool & Swarm Mode March 2026](https://blog.imseankim.com/claude-code-team-mode-multi-agent-orchestration-march-2026/)
- [Addy Osmani: Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/)
- [alexop.dev: From Tasks to Swarms](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)

### 1B. Oh-My-ClaudeCode (Community Orchestration Layer)

**Status:** Trending #1 on GitHub (858 stars in 24 hours), late March 2026.

**What it is:** Zero-config orchestration layer by Yeachan-Heo. Claims 3-5x speedup and 30-50% token savings through 32 specialized agents.

**Key feature — Ultrapilot Mode:** Runs up to 5 Claude Code instances in parallel, each in isolated Git worktrees with a shared task list. Genuinely parallelizable — five agents refactoring separate modules simultaneously.

**D2M relevance:** This is essentially what our Wing persona system does conceptually (A2/A5/A9/COS each specializing), but oh-my-claudecode does it at the Claude Code process level. Worth monitoring for architecture ideas.

**Sources:**
- [GitHub: oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode)
- [AIToolly coverage](https://aitoolly.com/ai-news/article/2026-03-29-oh-my-claudecode-a-new-multi-agent-orchestration-tool-designed-for-enhanced-team-collaboration)
- [Medium: Testing Oh My Claude Code](https://medium.com/@joe.njenga/i-tested-oh-my-claude-code-the-only-agents-swarm-orchestration-you-need-7338ad92c00f)

### 1C. Claude Agent SDK

Anthropic open-sourced the SDK that powers Claude Code — same agent loop, tools, and context management. Enterprise partners (Infosys, etc.) are building persistent agents for long, complex tasks using this SDK.

**Sources:**
- [Anthropic: AI Agents](https://claude.com/solutions/agents)
- [PopularAITools: Claude Agent SDK](https://popularaitools.ai/blog/claude-agent-sdk-build-custom-agents-2026)
- [Anthropic + Infosys collaboration](https://www.anthropic.com/news/anthropic-infosys)

### 1D. Anthropic Computer Use Agent

CNBC reports (March 24, 2026): Claude can now use a person's computer — users message from phone, Claude opens apps, navigates browsers, fills spreadsheets on their computer.

**Source:** [CNBC: Anthropic Claude AI Agent](https://www.cnbc.com/2026/03/24/anthropic-claude-ai-agent-use-computer-finish-tasks.html)

---

## SECTION 2: GOOSE — COLLABORATION & ORCHESTRATION

### 2A. Subagent Architecture

**Status:** Production-ready. 27K+ GitHub stars.

- **Subagents** = independent instances with process isolation and context preservation
- Can run sequentially or in parallel
- Goose autonomously decides when to spawn subagents (in autonomous permission mode)
- Each subagent gets its own context window

**Demo case:** Seven specialized subagents built a complete full-stack app ("AI BriefMe") in under an hour — Planner → Project Manager → individual builders.

### 2B. Recipes & Subrecipes

- **Recipes** = YAML workflow packages: instructions, MCP extensions, structured inputs, sub-recipes
- **Subrecipes** = reusable workflow templates with parameters, execution order, and dependency control
- Recipes auto-inherit globally configured MCP servers; authors can pin specific servers for reproducibility

### 2C. Roadmap (Feb–Apr 2026)

Goose is evolving from single chat agent into a **meta-agent orchestrator** managing sessions, workflows, recipes, and parallel subagents. Goal: make orchestration usable beyond power users.

### 2D. Claude Code as CLI Provider in Goose

**This is significant for us:** Goose supports Claude Code as a CLI provider. Users with a Claude Code subscription can route through Goose while maintaining session persistence and recipe/scheduling capabilities. This means our Goose+Claude dual-agent setup has a *native interop path*.

**Sources:**
- [Goose Subagents Docs](https://block.github.io/goose/docs/guides/subagents/)
- [Goose OSS Roadmap Feb–Apr 2026](https://github.com/block/goose/discussions/6973)
- [PulseMCP: A Human, A OpenCode, and Some Agents](https://www.pulsemcp.com/building-agents-with-goose)
- [Morph: Goose vs Claude Code 2026](https://www.morphllm.com/comparisons/goose-vs-claude-code)
- [VentureBeat: Goose does the same thing for free](https://venturebeat.com/technology/claude-code-costs-up-to-usd200-a-month-goose-does-the-same-thing-for-free)
- [Unified Tooling Discussion](https://github.com/block/goose/discussions/6202)

---

## SECTION 3: GOOSE ALTERNATIVES — 2026 LANDSCAPE

### 3A. The Big Players

| Tool | Model | Key Differentiator | Multi-Agent? | Cost |
|------|-------|-------------------|-------------|------|
| **Claude Code** | Opus 4.6 / Sonnet 4.6 | Agent Teams, massive context window | Yes (native) | $20-200/mo |
| **Goose** (Block) | Any LLM via MCP | Recipes, subagents, fully open-source | Yes (subagents) | Free |
| **Cursor** | Multi-model | IDE-native, 8 parallel agents via worktrees | Yes | $20-40/mo |
| **Windsurf** (Cognition) | SWE-1.5 | Cascade multi-step, 13x faster than Sonnet 4.5 | Yes | $15-60/mo |
| **Gemini CLI** (Google) | Gemini | Open-source, 500+ contributors, GitHub Actions collab | Requested (not native) | Free (1M tokens/day) |
| **OpenClaw** | Any LLM | 180K+ GitHub stars, self-hosted, plugin marketplace | Experimental | Free |
| **CodeConductor** | Multi-model | Enterprise — Keycloak auth, RBAC, compliance, auditable CI/CD | Yes | Enterprise pricing |

### 3B. OpenClaw (Formerly Moltbot)

Exploded in early 2026 — 180K+ GitHub stars. Free, open-source, self-hosted. Multi-agent routing supported (isolated agents per workspace). Creator joined OpenAI; project moving to open-source foundation. Features **Moltbook** — a platform where agents interact with each other for collaborative research.

**Sources:**
- [GitHub: OpenClaw](https://github.com/openclaw/openclaw)
- [KDnuggets: OpenClaw Explained](https://www.kdnuggets.com/openclaw-explained-the-free-ai-agent-tool-going-viral-already-in-2026)
- [Wikipedia: OpenClaw](https://en.wikipedia.org/wiki/OpenClaw)

### 3C. Gemini CLI

Open-source, v0.35.1, 500+ contributors. GitHub Actions integration for team collaboration (triggered by issues/PRs). Community-built orchestration exists (Maestro: 22 specialized subagents) but native Agent Teams is still a feature request, not shipped.

**Cross-agent experiment:** A published guide exists for Claude Code + Gemini CLI collaboration — using both tools on the same codebase with complementary strengths.

**Sources:**
- [Google Blog: Gemini CLI](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-open-source-ai-agent/)
- [Gemini CLI GitHub Actions](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-github-actions/)
- [Maestro-Gemini](https://github.com/josstei/maestro-gemini)
- [Claude + Gemini Collaboration Guide](https://smartscope.blog/en/generative-ai/claude/claude-gemini-collaboration-guide/)

### 3D. Windsurf (Cognition/Devin Team)

Agentic IDE with Cascade for multi-step coding. Proprietary SWE-1.5 model claims 13x faster than Sonnet 4.5. Worth watching as an IDE-integrated competitor to CLI-based tools.

---

## SECTION 4: COLLABORATION PROTOCOLS — THE INFRASTRUCTURE LAYER

### 4A. MCP vs A2A — The Two-Protocol Stack

**This is the most important "collaboration" finding.** The industry has converged on a two-layer protocol stack:

| Layer | Protocol | Purpose | Creator | Status |
|-------|----------|---------|---------|--------|
| **Tool Access** | MCP (Model Context Protocol) | Agent ↔ Tools/APIs/Data | Anthropic → Linux Foundation | 97M+ monthly SDK downloads |
| **Agent Collaboration** | A2A (Agent2Agent) | Agent ↔ Agent communication | Google → Linux Foundation | v1.0 shipped early 2026 |

**How they fit together:**
- **MCP** = how an agent talks to tools (we already use this heavily)
- **A2A** = how agents talk to each other (this is the "collaboration" protocol)

Both are now under the **Linux Foundation's Agentic AI Foundation (AAIF)**, launched Dec 2025 with six co-founders: **OpenAI, Anthropic, Google, Microsoft, AWS, and Block**.

**A2A v1.0 features:**
- gRPC transport (real-time, bidirectional)
- Signed Agent Cards (cryptographic identity for each agent)
- Multi-tenancy support
- Enterprise-grade governance

**Practical example:** Support orchestrator receives customer issue → assigns billing to billing agent, defects to tech agent, refunds to policy agent. Orchestrator discovers/communicates via A2A; each agent uses MCP internally for CRM/API access.

**Sources:**
- [Google A2A Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [IBM: What Is A2A](https://www.ibm.com/think/topics/agent2agent-protocol)
- [A2A Protocol Site](https://a2aprotocol.ai/)
- [Linux Foundation AAIF Launch](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [onereach.ai: MCP vs A2A Guide](https://onereach.ai/blog/guide-choosing-mcp-vs-a2a-protocols/)
- [Auth0: MCP vs A2A](https://auth0.com/blog/mcp-vs-a2a/)
- [DEV Community: Complete Guide](https://dev.to/pockit_tools/mcp-vs-a2a-the-complete-guide-to-ai-agent-protocols-in-2026-30li)

### 4B. The Blackboard Pattern — What We're Already Doing

Academic and industry research is formalizing the **blackboard architecture** as a primary multi-agent coordination pattern:

**Key properties:**
- Central shared memory space — specialized agents watch for data they can process
- Agents don't need to know about each other — only the blackboard
- Event-driven: agents act when relevant data appears
- Single source of truth for system status
- Approved-writes-only pattern for memory integrity

**D2M relevance:** Our `OpsCenter/collaboration/blackboard.md` + `claude_inbox.md` + `claude_output.md` system **IS** this pattern. The academic research validates our architecture. A recent arxiv paper proposes introducing blackboard architecture into LLM-based multi-agent systems as a general framework.

**Sources:**
- [Agent Patterns: Multi-Agent Collaboration](https://www.agentpatterns.tech/en/agent-patterns/multi-agent-collaboration)
- [Fast.io: Multi-Agent Context Sharing](https://fast.io/resources/multi-agent-context-sharing-patterns/)
- [Medium: Blackboard Pattern with MCPs](https://medium.com/@dp2580/building-intelligent-multi-agent-systems-with-mcps-and-the-blackboard-pattern-to-build-systems-a454705d5672)
- [arxiv: Blackboard Architecture for LLM Multi-Agent Systems](https://arxiv.org/html/2507.01701v1)
- [MindStudio: Agentic OS Architecture](https://www.mindstudio.ai/blog/agentic-os-architecture-four-patterns-claude-code)

### 4C. Additional Emerging Protocols

| Protocol | Purpose | Status |
|----------|---------|--------|
| **ACP** (Agent Communication Protocol) | RESTful structured messaging | Emerging |
| **UCP** (Unified Communication Protocol) | Proposed consolidation of A2A/ACP | Proposal stage |
| **ANP** (Agent Network Protocol) | Decentralized agent discovery | Experimental |

**Source:** [Digital Applied: AI Agent Protocol Ecosystem Map 2026](https://www.digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp)

---

## SECTION 5: STRATEGIC ANALYSIS — WHAT THIS MEANS FOR THUNDERBIRD

### What We're Doing Right
1. **Blackboard architecture** — our shared-file collaboration system (blackboard.md, inboxes, routing log) is a validated, academically-recognized multi-agent pattern
2. **MCP-first tool integration** — we're on the dominant tool-access protocol (97M+ monthly downloads)
3. **Dual-agent split (Claude + Goose)** — mirrors the industry trend of specialized agents with different strengths coordinating
4. **Persona specialization** — our Wing staff map to the "specialized subagent" pattern every orchestration framework is converging on
5. **File-based handoff** — simple, auditable, zero-coupling. The research says this is sufficient before formal protocol adoption.

### Upgrade Opportunities (Ranked by Impact)

| Priority | Opportunity | Effort | Impact |
|----------|------------|--------|--------|
| 1 | **Claude Code Agent Teams** — enable native teams for complex multi-module tasks | Low (config flag) | High — peer-to-peer Claude messaging |
| 2 | **OpenCode Provider for Claude** — route Goose recipes through Claude Code subscription | Medium | High — unified billing, recipe scheduling |
| 3 | **A2A Protocol monitoring** — watch for Claude/Goose native A2A support | None (watch) | Transformative when available |
| 4 | **oh-my-claudecode Ultrapilot** — 5 parallel Claude instances for batch ops | Medium | High for batch (intel sweeps, multi-dossier) |
| 5 | **Formalize handoff schema** — add agent_id, timestamp, confidence, task_type to all files | Low | Medium — better audit trail |

### What to Watch
- **A2A adoption by Anthropic/Claude** — Claude supports MCP natively; A2A support would be transformative for our inter-agent bridge
- **Goose roadmap (Apr 2026)** — meta-agent orchestrator features landing
- **OpenClaw's Moltbook** — agent-to-agent interaction platform, experimental but interesting for Dani-style bots
- **AAIF governance** — all six majors (OpenAI, Anthropic, Google, Microsoft, AWS, Block) at the table
- **Windsurf SWE-1.5** — 13x speed claims warrant evaluation if proven

### Market Context
- **Gartner:** 40% of enterprise apps will feature task-specific AI agents by 2026 (up from <5% in 2025)
- **Multi-agent collaboration entering operational phase in 2026** — we're riding the wave, not behind it
- **MCP SDK downloads: 97M+ monthly** — the tool-access standard is locked in
- **A2A v1.0 just shipped** — the agent-collaboration standard is now production-ready

---

## APPENDIX: FULL SOURCE INDEX

### Claude Code
- [Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams)
- [claudefa.st: Agent Teams Setup Guide](https://claudefa.st/blog/guide/agents/agent-teams)
- [Geeky Gadgets: Claude Code March 2026](https://www.geeky-gadgets.com/claude-code-channels/)
- [Shipyard: Multi-Agent Orchestration](https://shipyard.build/blog/claude-code-multi-agent/)
- [Medium (Rick Hightower): Agent Teams](https://medium.com/@richardhightower/claude-code-agent-teams-multiple-claudes-working-together-a75ff370eccb)
- [eesel.ai: Complete 2026 Guide](https://www.eesel.ai/blog/claude-code-multiple-agent-systems-complete-2026-guide)
- [Sean Kim: TeammateTool & Swarm Mode](https://blog.imseankim.com/claude-code-team-mode-multi-agent-orchestration-march-2026/)
- [Addy Osmani: Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/)
- [Heeki Park: Collaborating with Agent Teams](https://heeki.medium.com/collaborating-with-agents-teams-in-claude-code-f64a465f3c11)
- [paddo.dev: Hidden Multi-Agent System](https://paddo.dev/blog/claude-code-hidden-swarm/)
- [CNBC: Anthropic Computer Use Agent](https://www.cnbc.com/2026/03/24/anthropic-claude-ai-agent-use-computer-finish-tasks.html)
- [Anthropic + Infosys](https://www.anthropic.com/news/anthropic-infosys)

### Oh-My-ClaudeCode
- [GitHub: oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode)
- [Official Site](https://ohmyclaudecode.com/)
- [AIToolly Coverage](https://aitoolly.com/ai-news/article/2026-03-29-oh-my-claudecode-a-new-multi-agent-orchestration-tool-designed-for-enhanced-team-collaboration)
- [byteiota Coverage](https://byteiota.com/oh-my-claudecode-multi-agent-orchestration-for-claude-code/)

### Goose
- [GitHub: block/goose](https://github.com/block/goose)
- [Goose Docs](https://block.github.io/goose/)
- [Subagents Guide](https://block.github.io/goose/docs/guides/subagents/)
- [OSS Roadmap Feb–Apr 2026](https://github.com/block/goose/discussions/6973)
- [PulseMCP: Building Agents with Goose](https://www.pulsemcp.com/building-agents-with-goose)
- [Sequoia Capital: Goose Transformation](https://sequoiacap.com/podcast/training-data-dhanji-prasanna/)
- [Docker + Goose](https://www.docker.com/blog/building-ai-agents-with-goose-and-docker/)
- [CLI Providers Docs](https://block.github.io/goose/docs/guides/cli-providers/)

### Alternatives & Comparisons
- [sanj.dev: CLI Assistants Compared](https://sanj.dev/post/comparing-ai-cli-coding-assistants)
- [Tembo: 15 CLI Tools Compared](https://www.tembo.io/blog/coding-cli-tools-comparison)
- [Pinggy: Top 5 CLI Coding Agents](https://pinggy.io/blog/top_cli_based_ai_coding_agents/)
- [Morph: Goose vs Claude Code](https://www.morphllm.com/comparisons/goose-vs-claude-code)
- [VentureBeat: Goose vs Claude Code](https://venturebeat.com/technology/claude-code-costs-up-to-usd200-a-month-goose-does-the-same-thing-for-free)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [KDnuggets: OpenClaw](https://www.kdnuggets.com/openclaw-explained-the-free-ai-agent-tool-going-viral-already-in-2026)
- [SelectHub: Claude Code vs Goose](https://www.selecthub.com/vibe-coding-tools/claude-code-vs-goose-ai/)
- [Claude + Gemini Collaboration Guide](https://smartscope.blog/en/generative-ai/claude/claude-gemini-collaboration-guide/)
- [Maestro-Gemini](https://github.com/josstei/maestro-gemini)

### Protocols
- [Google A2A Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A Protocol Site](https://a2aprotocol.ai/)
- [A2A Protocol Spec](https://a2a-protocol.org/latest/)
- [A2A GitHub](https://github.com/a2aproject/A2A)
- [IBM: What Is A2A](https://www.ibm.com/think/topics/agent2agent-protocol)
- [Linux Foundation AAIF](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [onereach.ai: MCP vs A2A](https://onereach.ai/blog/guide-choosing-mcp-vs-a2a-protocols/)
- [Auth0: MCP vs A2A](https://auth0.com/blog/mcp-vs-a2a/)
- [DEV Community: MCP vs A2A Complete Guide](https://dev.to/pockit_tools/mcp-vs-a2a-the-complete-guide-to-ai-agent-protocols-in-2026-30li)
- [Digital Applied: Protocol Ecosystem Map](https://www.digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp)
- [Spring AI A2A Integration](https://spring.io/blog/2026/01/29/spring-ai-agentic-patterns-a2a-integration/)

### Collaboration Patterns & Architecture
- [Agent Patterns: Multi-Agent Collaboration](https://www.agentpatterns.tech/en/agent-patterns/multi-agent-collaboration)
- [Fast.io: Context Sharing Patterns](https://fast.io/resources/multi-agent-context-sharing-patterns/)
- [BetterLink: 4 Architecture Patterns](https://eastondev.com/blog/en/posts/ai/20260325-multi-agent-system/)
- [arxiv: Blackboard Architecture for LLM](https://arxiv.org/html/2507.01701v1)
- [MindStudio: Agentic OS Architecture](https://www.mindstudio.ai/blog/agentic-os-architecture-four-patterns-claude-code)
- [Medium: Blackboard + MCP](https://medium.com/@dp2580/building-intelligent-multi-agent-systems-with-mcps-and-the-blackboard-pattern-to-build-systems-a454705d5672)
- [Codebridge: Multi-Agent Frameworks](https://www.codebridge.tech/articles/mastering-multi-agent-orchestration-coordination-is-the-new-scale-frontier)
- [Codefinity: AI Agent Swarm Architecture](https://codefinity.com/blog/The-Architecture-Of-AI-Agent-Swarms)

---

*Report generated 2026-03-31 ~20:05 MT · Claude Opus 4.6 · GT-20260331-2001-RESE*
*No PII. No client data. Research only.*
*Previous content (2026-03-30 fusion report) superseded — prior findings incorporated where still relevant.*

---
AGENT: Claude Sonnet (auto-triggered by inbox_watcher)
TASK_ID: GT-20260331-2001-RESE
COMPLETED_AT: 2026-03-31T20:07:27 MT
---
Research complete. Output written to `/home/john/Thunderbird/OpsCenter/collaboration/claude_research_output.md`.

**Top-line findings for Commander:**

1. **Our blackboard architecture is validated** — academic research and industry frameworks are formalizing exactly what OpsCenter already does. We were ahead of the curve.

2. **A2A Protocol v1.0 shipped** — Google's agent-to-agent protocol is now a Linux Foundation standard (alongside MCP under AAIF, co-founded by all six majors). MCP = agent-to-tools. A2A = agent-to-agent. Two-layer stack. This is the "collaboration" protocol the industry settled on.

3. **Claude Code Agent Teams are live** — native peer-to-peer multi-agent with shared task lists and Git worktree isolation. Available to us now with one config flag.

4. **Goose supports Claude Code as a CLI provider** — native interop path for our dual-agent setup exists.

5. **oh-my-claudecode** trending #1 on GitHub — 32 specialized agents, 5 parallel instances (Ultrapilot mode), 3-5x speedup claims. Essentially our Wing persona concept implemented at the process level.

6. **OpenClaw** (180K+ GitHub stars) and **Gemini CLI** (500+ contributors) are the main open-source alternatives. Neither has native Agent Teams yet — Claude Code leads on collaboration.

Report is 5 sections + full source appendix with 60+ clickable links. Ready for Commander review.
