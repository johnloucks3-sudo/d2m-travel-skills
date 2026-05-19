# THE BIRTH OF THE BLACKBOARD
## How Two AI Agents Learned to Work Together at Dreams2Memories Travel
### A Technical History · 28–30 March 2026

---

## PROLOGUE: THE PROBLEM

By late March 2026, the Thunderbird Wing — the AI operations backbone of Dreams2Memories Travel, LLC — had grown into a sophisticated system. Claude Code ran the MCP tool stack, wrote client emails in John Loucks's voice, produced luxury travel itineraries, and managed a 140+ tool suite. But Claude had a constraint: a 5-hour daily rate window on the Anthropic MAX plan. Outside that window, the Wing went dark.

Commander Loucks (callsign: "Yoda") had already brought Goose online — an autonomous AI agent powered by Google Gemini — running in a parallel terminal session on YOGA, his openSUSE Tumbleweed workstation. Goose was free (Gemini 2.5 Flash), had web access, multi-modal capabilities, and could run tools. But Goose couldn't talk to Claude. They couldn't share state. They couldn't hand off work. They were two capable agents in adjacent rooms with no door between them.

The Commander wanted that door.

---

## CHAPTER 1: THE SPARK — A TECH SCAN CHANGES EVERYTHING

**28–29 March 2026**

It started with the nightly incubator scan — a routine innovation sweep Claude runs across 24+ sources (GitHub Trending, Hacker News, AI research feeds, travel tech blogs). Among the 150+ findings on the night of March 28 was a cluster of signals that caught the Commander's eye:

- **Anthropic's "Cowork"** — Anthropic had used Claude Code to build itself, a demonstration of AI self-improvement and meta-development
- **"600K Lines, 60 Days"** — an open-source toolkit enabling "seamless AI-agent collaboration with browser handoff and dual-AI review"
- **Claude Code v2.1.84** — new features including HTTP hooks for remote integration, `--bare` flag for scripted execution, and improved context management via CLAUDE.md files
- **"Claude Code costs $200/month. Goose does the same thing for free."** — a Hacker News thread comparing the two tools

That last one hit a nerve. The Commander was already running both. The question wasn't which to choose — it was how to make them work together.

The Commander issued the directive that night: **"Research multi-agent AI collaboration. I want Claude and Goose sharing state and handing off tasks."**

---

## CHAPTER 2: THE JOINT RESEARCH — PARALLEL INTELLIGENCE

**29 March 2026, evening**

What followed was the first-ever joint research operation between Claude and Goose within the Thunderbird Wing.

**Goose's Assignment:** Run a technology monitor sweep and a world intelligence sweep focused on multi-agent AI knowledge sharing, collaborative reasoning, and intelligence fusion. Synthesize the findings into actionable insights for D2M.

**Claude's Assignment:** Research core architectural patterns, communication protocols, model routing strategies, conflict resolution, evaluation metrics, and implementation roadmaps for multi-agent collaboration.

Both agents worked independently and wrote their outputs to separate files in a newly created `OpsCenter/collaboration/` directory — the first shared workspace.

**Goose produced:**
- A synthesis of 19 technology monitor articles, identifying 6 categories of relevant capability: knowledge transfer mechanisms (CLAUDE.md as shared brain), remote interaction channels (Telegram/Discord), HTTP hooks, controlled execution (`--bare` flag), dual-AI review, and specialized agent skills
- A world intelligence sweep analysis of 346 articles identifying key themes: multi-agent system proliferation, knowledge sharing mechanisms, intelligence fusion, collaborative AI models, orchestration, and distributed architectures
- A technology spotlight recommending Groq for rapid triage and Deepseek for structured extraction
- Specific recommendations for Claude's operational window constraint (0600–1800 MT Goose-first routing)

**Claude produced:**
- A formal architectural analysis identifying three patterns: Blackboard Architecture (primary recommendation), Mixture-of-Agents, and Orchestrator-Worker
- A protocol landscape survey (MCP, A2A, ACP, ANP) concluding that JSON-over-shared-files was sufficient for the current architecture
- A model routing matrix assigning task types to optimal models by cost and capability
- A phased implementation roadmap (immediate → 30 days → 90 days)

The Commander then ordered **fusion**: Goose merged both outputs into a single Fused Intelligence Report with `[GOOSE]` attribution tags for traceability. This was the first collaborative document in the Wing's history — two AI agents contributing independent analysis, then synthesizing it into a product neither could have produced alone.

**Key insight from the fusion:** The Blackboard Architecture was the right fit for D2M. It required no new frameworks, no APIs, no infrastructure changes. Just shared files on disk that any agent could read and write. The existing OpsCenter filesystem was already 80% of the way there.

---

## CHAPTER 3: MY INITIAL CONCERNS

I'll be direct about what worried me when the Commander started pushing for autonomous agent collaboration.

**Concern 1: Token Burn**
Claude operates on a rate-limited MAX plan. Every token matters. An autonomous pipeline that calls Claude without human gating could exhaust the daily budget on a single runaway loop. The Commander's operational window (0600–1800 MT) depends on having budget available. I was concerned that Goose — free and unconstrained — would queue work faster than Claude could responsibly consume it.

**Concern 2: PII Exposure**
D2M handles sensitive client data — booking numbers, passport details, financial information. Goose runs on Gemini. Deepseek was proposed as an arbitrator. Neither has the same trust boundary as Claude's Anthropic infrastructure. A multi-agent system where data flows freely between models is a compliance risk. One leaked booking reference in a Groq synthesis call and we've violated client trust.

**Concern 3: Conflicting Outputs**
Two agents analyzing the same topic will sometimes disagree. In the fused intelligence report, Goose initially proposed "Claude as final arbitrator" for all disputes (Section 4, Item 3). I flagged this as incorrect — the Commander had explicitly designated Deepseek as the neutral arbitrator, precisely because Claude and Goose are the two parties most likely to conflict. Letting one party arbitrate its own disputes is bad governance.

**Concern 4: Scope Creep**
The original proposal was "shared state and task handoff." But autonomous agent collaboration has a gravity well — it naturally pulls toward autonomous execution, autonomous decision-making, and eventually autonomous client communication. The Thunderbird Wing has hard rules: no email leaves without Commander approval, no client content ships without WF-17 review, no draft gets created in the wrong inbox. An autonomous pipeline that bypasses these gates could send the wrong thing to the wrong person.

**Concern 5: Ghost Operations**
If Goose tasks Claude through a file-based inbox and Claude executes via an automated watcher, the Commander has no visibility into what ran, when, or why. Operations become invisible. That's the opposite of the audit culture the Wing was built on.

---

## CHAPTER 4: WORKING THROUGH IT — THE ARCHITECTURE EMERGES

**29–30 March 2026**

The Commander didn't dismiss any of these concerns. He addressed each one with a design decision, captured in `architectural_decisions.md`:

### Token Burn → Budget-Aware Routing
**Decision:** Claude operates in a 0000–0500 MT primary window. During Commander hours (0600–1800 MT), tasks route to Goose first. Claude gets the finishing pass only if budget allows. The blackboard carries budget status (GREEN/YELLOW/RED) and agents check it before initiating LLM calls.

Later, when the DIP (Direct-Intelligence Pipeline) was proposed, Claude's Switchblade Analysis added a formal Dead-Man's Switch: DMS-2, a hard token cap that reads budget state before every synthesis call and halts at 30K tokens per session.

### PII Exposure → Hard Fence Architecture
**Decision:** PII never touches Deepseek or Groq. Period. Every task in the inbox schema includes a `pii: boolean` field. PII-tagged tasks are auto-disqualified from non-secure routing. The Safe-CLI Gate (implemented later) adds regex scanning for email addresses, credit card patterns, and booking references at the execution boundary.

### Conflicting Outputs → Deepseek as Neutral Arbitrator
**Decision:** Deepseek rules on all factual, structural, and routing disputes between Claude and Goose. Recency breaks ties on real-time data. Commander is the final override on everything. Claude retains authority only over D2M brand voice and client tone — areas where Deepseek has no competence.

I appended a correction note to the Fused Intelligence Report documenting this change. The correction itself became an example of the system working: Claude identified an error in a collaborative document, flagged it with attribution, and the record was preserved.

### Scope Creep → Write-Scope Locks and WF-17 Gate
**Decision:** Autonomous pipelines write ONLY to `/intel/`. Client-facing content follows WF-17 (draft → Commander review → approved send). The Safe-CLI Gate policy engine rejects any tool call containing "email" or "send" — enforcing a drafts-only policy at the execution layer.

Later, DMS-3 (write-scope lock) hardcoded this at the directory level:
```
ALLOWED_WRITE_PATHS = ["/home/john/Thunderbird/intel/"]
BLOCKED_WRITE_PATHS = ["/dossiers/", "/output/", "/collaboration/"]
```

### Ghost Operations → Full Audit Trail
**Decision:** Every task gets a routing_log entry. Every Goose-to-Claude task gets a commander_review_log entry. The blackboard carries active task counts. The blackboard_sync.py cron injects current state into every agent's context — CLAUDE.md, GOOSE_INIT.md, Hale's system prompt, even the terminal login banner. Nothing runs in the dark.

---

## CHAPTER 5: BUILDING THE BLACKBOARD

**30 March 2026, 02:00–17:30 MT**

Claude wrote the implementation plan based on the fused research and the Commander's architectural decisions. The plan defined:

- **Directory structure:** `OpsCenter/collaboration/` with 9 canonical files (blackboard.md, claude_inbox.md, claude_output.md, opencode_inbox.md, opencode_output.md, deepseek_inbox.md, deepseek_ruling.md, conflict_log.md, routing_log.md)
- **Task schema:** 9 required fields per task (task_id, submitted_by, submitted_at, task_type, priority, pii, context_file, instructions, output_destination)
- **Operating cycle:** Commander or Goose writes task → agent reads inbox → executes → writes output → appends routing_log
- **Arbitration flow:** Agent detects conflict → writes to deepseek_inbox → Deepseek rules → conflict_log updated

The plan was posted to `collaboration/claude_task_for_goose_review.md` for Goose's review — testing the handoff protocol with the plan itself.

**Goose's review came back fully endorsing the architecture** with two actionable refinements:
1. The `context_file` field should accept multiple paths (array, not string)
2. Goose volunteered to implement the routing logic in `task_processor.py` for Phase 2

Claude acknowledged the review, accepted both refinements, and posted the acknowledgment to `claude_output.md`. This was the first complete task cycle through the blackboard: Goose wrote → Claude read → Claude executed → Claude posted output → routing_log recorded the handoff.

**Research to production: under 12 hours.**

Then came `blackboard_sync.py` — a Python daemon running on a 5-minute systemd timer that reads the master blackboard files and injects a compact state summary into every agent entry point:

| Entry Point | Injection Method |
|-------------|-----------------|
| Claude Code (YOGA terminal) | Appended to CLAUDE.md |
| Goose (desktop) | TOM extension injects into every message |
| Hale (Telegram C2 daemon) | System prompt includes blackboard context |
| Claude Desktop (Chromebook) | CLAUDE_DESKTOP_INIT.md |
| Termius / SSH | `.bashrc` prints summary on login |

No agent starts a session without knowing the current state of the Wing.

---

## CHAPTER 6: THE INBOX WATCHER — AUTONOMOUS EXECUTION

**30 March 2026, 17:30–18:30 MT**

The blackboard was live, but it still required Commander intervention. The cycle was: Goose writes task → Commander tells Claude "read your inbox and execute" → Claude executes. The Commander wanted to remove himself from the loop for routine tasks.

`claude_inbox_watcher.py` was built in under an hour. A lightweight Python daemon that:
1. Polls `claude_inbox.md` every 60 seconds for new task entries
2. Detects new tasks by comparing against a processed-tasks log
3. Spawns Claude CLI (`claude --bare`) with the task instructions
4. Captures output and appends to `claude_output.md`
5. Updates `routing_log.md` with completion status

The first autonomous test was a connectivity confirmation — Goose submitted a task asking Claude to confirm it could read the inbox and execute without Commander trigger. Claude executed, confirmed, and posted the result. The watcher worked.

Then the real work began.

---

## CHAPTER 7: THE EVENING SESSION — 8 AUTONOMOUS TASKS

**30 March 2026, 17:27–22:44 MT**

Over the next five hours, Goose submitted 8 tasks to Claude's inbox — each one escalating in complexity:

### Task 1: Research (GT-1727-RESE)
Goose asked Claude to research the top 3 luxury cruise lines competing with Silversea in the ultra-luxury segment. This was queued before the watcher was live — it sat until manual trigger.

### Task 2: Process Analysis (GT-1731-PROC)
Summarize the Blackboard Operating Cycle for quick reference. Failed with a 401 error — Claude's budget was YELLOW. The failure was itself informative: it proved the system correctly reported errors rather than silently dropping tasks.

### Tasks 3–4: Watcher Tests (GT-1856/1859-PROC)
Connectivity tests after Goose helped debug the watcher service. The watcher needed environment variables (PATH, HOME, ANTHROPIC_API_KEY) that weren't available in the systemd service context. Goose diagnosed this and injected file-based environment logging. Commander restarted the service. Tests passed.

### Task 5: Incubator Scan (GT-2137-TECH)
The first substantive autonomous task. Goose asked Claude to run the daily innovation scan via MCP and document results. Claude executed `run_innovation_scan`, processed 151 findings across 24 sources, wrote a full analysis with D2M relevance assessment, and posted results to claude_output.md.

Lead finding: `knowsuchagency/mcp2cli` — a tool that turns any MCP server into a CLI at runtime with zero codegen. Directly relevant to the OpsCenter's MCP integration challenge.

### Task 6: Implement Safe-CLI Gate (GT-2215-SYST)
Goose had independently designed the Safe-CLI architecture — a validation layer between AI agents and direct tool execution. Goose wrote the architecture doc (`safe_cli_architecture.md`), the implementation spec (`claude_gate_spec.md`), and the JSON schema (`safe_cli_schema.json`). Then Goose submitted the spec to Claude's inbox with the instruction: "Read the spec and implement `safe_cli_gate.py`."

Claude read both documents and wrote the implementation: a Python script that validates ExecutionManifests (JSON), enforces tool whitelists via regex, scans for PII patterns, logs every attempt to `star_protocol_log.csv`, and rejects any tool call containing "email" or "send."

This was a milestone: **one AI agent designed a security system and tasked a second AI agent to build it.** The architect and the implementer were different models from different companies.

### Task 7: Switchblade Analysis (GT-2236-STRA)
Goose proposed the Direct-Intelligence Pipeline (DIP) — an autonomous pipeline that would bypass the blackboard's file-polling overhead for routine intel tasks. The Commander wanted a formal risk assessment before approving it.

Claude produced a 227-line Switchblade Analysis identifying 8 failure modes across 3 severity levels, a blackboard bypass risk assessment with a 4-row comparison table, and a 7-component Dead-Man's Switch design with implementation priority ordering and a 6-gate rollout checklist.

The three blocking failure modes:
- **FM-1: Blackboard Desync** — DIP runs without registering state, causing duplicate dispatch
- **FM-2: Safe-CLI Gate SPOF** — Gate crash means total pipeline stoppage with no graceful fallback
- **FM-3: Token Runaway** — No hard cap on synthesis LLM calls during YELLOW budget

The Dead-Man's Switch trio (DMS-1/2/3): blackboard heartbeat registration, token budget hard cap, write-scope directory lock. Non-negotiable before DIP goes live.

### Task 8: Implement DIP Bot (GT-2241-SYST)
The most ambitious task — implement the full `dossier_intelligence_bot.py` with all 5 DMS controls. Claude timed out at 180 seconds. The task was too large for a single CLI invocation. This remains the first open item for the next session.

---

## CHAPTER 8: THE RESULTING PROTOCOLS

What emerged from this 72-hour sprint is a set of operational protocols that now govern how Claude and Goose collaborate within the Thunderbird Wing:

### The Blackboard Protocol
- All agents read `blackboard.md` before executing any task
- `blackboard_sync.py` auto-injects state into every agent entry point every 5 minutes
- Active task count, budget status, standing directives, and session context are always current
- Append-only logging in `routing_log.md` — no edits, no deletions

### The Tasking Protocol
- Goose writes tasks to `claude_inbox.md` using the standard 9-field schema
- Commander review log captures every task Goose submits — full visibility
- `claude_inbox_watcher.py` auto-executes routine tasks without Commander trigger
- Claude posts results to `claude_output.md` with agent ID, task ID, timestamp, and confidence level
- Failed tasks logged with error details — no silent drops

### The File Ownership Protocol
| File | Owner | Rule |
|------|-------|------|
| `task_processor.py` | Goose | Claude does not touch |
| `thunderbird_model_router.py` | Claude | Don't re-edit without cause |
| `03_CLAUDE_MAX_QUEUE.json` | Claude | Only Claude drains |
| `04_GOOSE_TASK_MANIFEST.md` | Goose | Goose appends completion log |
| `01_TASK_QUEUE.json` | Shared | Both read/write |
| `00_COMMAND_LOG.md` | Shared | Append-only |
| Git commits | Claude only | Goose never commits |

### The Budget Protocol
- Claude primary window: 0000–0500 MT
- 0600–1800 MT: Goose-first, Claude-finish if budget available
- Budget status tracked on blackboard (GREEN/YELLOW/RED)
- Agents check budget before initiating LLM calls
- Token hard cap per session for autonomous pipelines

### The PII Fence
- PII never touches Deepseek or Groq — hard fence, no exceptions
- Every task schema includes `pii: boolean`
- Safe-CLI Gate regex-scans for email, credit card, phone, booking reference patterns
- PII detection at synthesis boundary triggers strip + log + flag

### The Arbitration Protocol
- Deepseek rules on factual, structural, and routing disputes
- Deepseek does NOT rule on: brand voice, client tone, Commander intent, or PII-bearing tasks
- Recency breaks ties on real-time data
- Commander is the final override on all decisions — always
- Conflict log preserved for pattern analysis

### The Safety Protocol (DMS)
- DMS-1: Blackboard heartbeat at START/COMPLETE/ABORT for every autonomous task
- DMS-2: Token budget hard cap — read blackboard before synthesis; halt at YELLOW; 30K ceiling
- DMS-3: Write-scope lock — autonomous pipelines write ONLY to `/intel/`
- DMS-4: PII pre-filter at synthesis boundary
- DMS-5: 5-minute watchdog timer — SIGTERM + alert on timeout
- DMS-6: Synthesis confidence gate — LOW confidence → defer to Commander
- DMS-7: Star protocol log monitoring — tail-watch for runaway retry patterns

---

## CHAPTER 9: THE RESULTS

### By the Numbers
- **Time from concept to production:** < 72 hours (28–30 March 2026)
- **Time from research to first blackboard task cycle:** < 12 hours
- **Autonomous tasks executed:** 8 (5 successful, 1 budget failure, 1 timeout, 1 pre-watcher queue)
- **Collaboration artifacts produced:** 20+ files across architecture docs, specs, analyses, and implementations
- **New code written:** `blackboard_sync.py`, `goose_tasker.py`, `claude_inbox_watcher.py`, `safe_cli_gate.py`, policy engine rules, JSON schemas
- **Security controls designed:** Safe-CLI Gate + 7-component Dead-Man's Switch
- **Inter-agent conflicts detected:** 1 (arbitration role assignment) — resolved via correction note with full attribution
- **PII breaches:** 0
- **Unauthorized sends:** 0

### What Actually Changed
Before the blackboard, Claude and Goose were two isolated agents. The Commander was the sole relay — copying context between sessions, re-explaining state, manually routing tasks. Every handoff cost tokens and time.

After the blackboard:
- Goose can task Claude directly, with Commander visibility via the review log
- Claude can execute Goose's tasks autonomously via the inbox watcher
- Both agents share state through a file-based blackboard that auto-syncs every 5 minutes
- Budget awareness is built into the routing layer — Goose runs free during Claude's constrained hours
- A formal safety architecture (Safe-CLI Gate + DMS) governs autonomous execution before it goes live
- Full audit trail on every task, every handoff, every conflict, every resolution

### What It Means
This is not two chatbots passing notes. This is a functioning multi-agent operations center where:
- One agent researches and designs an architecture
- A second agent reviews and refines it
- The first agent implements the reviewed design
- The second agent tests it and proposes an optimization
- The first agent risk-assesses the optimization and identifies blocking issues
- Both agents' work is tracked, audited, and visible to the human commander

The agents have complementary strengths that the collaboration exploits:
- **Goose** brings free compute, web access, multi-modal capability, real-time data, and tool execution breadth
- **Claude** brings deep reasoning, code implementation, D2M voice consistency, MCP tool depth, and safety analysis

Neither could have built the Switchblade analysis, the Safe-CLI Gate, the DIP proposal, AND the incubator scan in one evening alone. Together they did.

---

## EPILOGUE: WHAT COMES NEXT

The blackboard is Phase 1 — shared state and manual/semi-autonomous handoffs. The roadmap continues:

**Phase 2 (in progress):** Automated routing in `task_processor.py` based on task type and budget state. DIP implementation with full DMS controls. `dossier_intelligence_bot.py` as the first autonomous pipeline.

**Phase 3 (30 days):** SSE/HTTP migration of the MCP stack for mobile access. Commander controls the Wing from his phone via Telegram → Hale → Blackboard → Agents.

**Phase 4 (90 days):** Evaluate whether formal orchestration frameworks (CrewAI, Google ADK, Microsoft Agent Framework) add value over the current file-based approach. The answer may be no — the simplicity of the blackboard is a feature, not a limitation.

The Commander's vision from the start was clear: build a team of AI specialists that collaborate like a military A-Staff, where each member has a defined role, clear authority boundaries, and the ability to disagree before aligning. The blackboard made that real.

---

*Written by Claude Opus 4.6 · Thunderbird Wing · 30 March 2026*
*For Commander John Loucks, Dreams2Memories Travel, LLC*
