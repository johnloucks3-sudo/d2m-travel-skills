# THUNDERBIRD OS — INNOVATION MASTER INVENTORY
## Everything Discussed, Planned, or Deployed — Session 2026-03-20
## Dreams2Memories Travel, LLC

---

## STATUS KEY
- **DEPLOYED** = Code written, wired in, working
- **BUILDING** = Agent currently coding
- **READY** = Researched, decision made, awaiting build
- **EVALUATE** = Needs testing/trial before commitment
- **WATCH** = Track for future adoption

---

## 1. PREFERENCE LEARNING (3-Layer Architecture)

### Layer 1: Explicit Correction Learning
| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| Temporal versioning (valid_from/to/superseded_by) | ICAI research | **DEPLOYED** | $0 | Added to learning_rules.db |
| 3-tier priority hierarchy (inviolable/strong/contextual) | ICAI research | **DEPLOYED** | $0 | Priority-ordered injection |
| Context-sensitive retrieval (CIPHER/vector embeddings) | PRELUDE NeurIPS 2024 | **READY** | $0 | sqlite-vec or Mem0 |
| Positive framing audit of principles | ICAI research finding | **READY** | $0 | Audit existing principles |
| Per-recipient voice profiles (top 10 contacts) | Spark Mail / Dembe report | **READY** | $0 | Extend voice_ledger.json |
| LangMem metaprompt pattern | LangChain SDK | **WATCH** | $0 | Borrow pattern, not dependency |

### Layer 2: Passive Observation Learning
| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| Voice profile → learning compiler pipeline | Spark Mail inspiration | **DEPLOYED** | $0 | thunderbird_my_voice.py fixed |
| Auto-enrichment engine (Gmail/Drive/Calendar/Dossier) | Google Personal Intelligence | **DEPLOYED** | $0 | thunderbird_auto_enrich.py |
| Auto-enrich wired into Dani engine | Google PI | **BUILDING** | $0 | Agent: dani-wiring |
| Information delta tracker (semantic edit analysis) | Windsurf Cascade | **BUILDING** | $0 | Agent: info-delta-tracker |
| Conversation preference detection (auto-memory) | ChatGPT Memory | **BUILDING** | $0 | Agent: episodic-memory |
| Commander inbox → learning capture | ChatGPT auto-detect | **BUILDING** | $0 | Agent: active-learning-loop |
| Forward/reply pattern analysis | Windsurf Cascade | **READY** | $0 | Next sprint |
| Response time pattern analysis | Windsurf Cascade | **WATCH** | $0 | Needs instrumentation |
| Klipy-style auto CRM from all comms | Klipy CRM | **WATCH** | $0 | Dossier auto-population |

### Layer 3: Temporal Knowledge Graphs
| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| SQLite temporal extension | Dembe recommendation | **DEPLOYED** | $0 | valid_from/to columns live |
| Episodic memory table ("what worked before") | LangMem episodic | **BUILDING** | $0 | Agent: episodic-memory |
| Zep temporal knowledge graph | Reddit/community scan | **EVALUATE** | $25/mo | Phase 2 after 30-60 days data |
| Mem0 self-hosted memory layer | A2 research | **EVALUATE** | $0 | Alternative to Zep |
| Graphiti bi-temporal edges | Temporal KG report | **WATCH** | $0 | Phase 3 if needed |
| Trend detection + proactive alerts | Original architecture | **WATCH** | $0 | Needs data accumulation |

---

## 2. INFRASTRUCTURE & SECURITY

| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| MCP security lockdown (shell_exec, localhost bind) | Security audit | **BUILDING** | $0 | Agent: security-lockdown |
| Bearer token auth on REST API | Security audit | **BUILDING** | $0 | Agent: security-lockdown |
| Lasso MCP Gateway (auth/audit/injection detection) | Reddit scan | **EVALUATE** | $0 | Defense-in-depth layer |
| Cloudflare Access on mcp.d2mluxury.quest | Security audit | **READY** | $0 | Already in CF stack |
| Playwright MCP | Aven/Channels report | **DEPLOYED** | $0 | Installed via claude mcp add |
| Firecrawl MCP | GitHub/HN scan | **READY** | $0 | Free tier, 500 credits |
| Groq elimination (all files) | Standing order | **DEPLOYED** | $0 | 10 files cleaned |
| Innovation scanner + systemd timers | Original architecture | **BUILDING** | $0 | Agent: innovation-wiring |
| Active learning loop (/learn command) | Architecture design | **BUILDING** | $0 | Agent: active-learning-loop |
| Morning brief learning digest | Architecture design | **BUILDING** | $0 | Agent: active-learning-loop |

---

## 3. DANI ENHANCEMENTS

| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| Data Confidence Classifier (HIGH/MED/LOW/ZERO) | Prior session | **DEPLOYED** | $0 | thunderbird_data_confidence.py |
| Pre-Send Evaluator (regex leak scanner) | Prior session | **DEPLOYED** | $0 | thunderbird_presend_evaluator.py |
| Conversation State Machine (7 phases) | Prior session | **DEPLOYED** | $0 | thunderbird_conversation_state.py |
| Structured Response Library (6 templates) | Prior session | **DEPLOYED** | $0 | thunderbird_response_library.py |
| Dani Voice Agent (phone answering) | Competitor scan | **READY** | $150-180/mo | Retell AI, 2-3 day build |
| Voice profile injection into Dani | Voice learning research | **BUILDING** | $0 | Agent: dani-wiring |
| Auto-enrichment in Dani pipeline | Google PI | **BUILDING** | $0 | Agent: dani-wiring |
| Per-recipient voice rules | Spark Mail | **BUILDING** | $0 | Agent: dani-wiring |

---

## 4. AGENT & MCP ECOSYSTEM

| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| Claude Code Agent Teams | Claude Code innovations | **READY** | $0 | CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 already set |
| Subagent Persistent Memory | Claude Code innovations | **READY** | $0 | Per-persona memory dirs |
| MCP Connector on API | Claude Code innovations | **EVALUATE** | $0 | Simplify Chromebook→YOGA |
| Code Execution with MCP (98.7% token reduction) | Claude Code innovations | **EVALUATE** | $0 | Claude writes code against MCP |
| OpenClaw multi-channel agent (1 agent → Telegram/WhatsApp/Signal) | GitHub/HN scan | **EVALUATE** | $0 | 210K stars, solves multi-channel Dani |
| n8n MCP integration | Claude Code innovations | **WATCH** | $0 | Already have n8n workflows |
| A2A protocol compliance | Competitor scan | **WATCH** | $0 | For MAGOA/TESS integration |

---

## 5. TRAVEL INDUSTRY SPECIFIC

| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| Aven Hospitality MCP (35K hotels via MCP) | GitHub/HN scan | **READY** | $0? | No public app — email media@avenhospitality.com |
| TESS write API (6 methods) | Prior session | **DEPLOYED** | $0 | thunderbird_tess.py |
| Booking Master fixes (10 fixes) | Prior session | **DEPLOYED** | $0 | scripts/fix_booking_master.py |
| Audio briefings from dossiers (NotebookLM pattern) | Competitor scan | **EVALUATE** | $0 | "Listen to your trip overview" |
| Auto model routing (Opus/Sonnet/Haiku by task) | Competitor scan | **READY** | $0 | Upgrade existing model_router |

---

## 6. COMPETITIVE INTELLIGENCE

| Innovation | Source | Status | Cost | Notes |
|-----------|--------|--------|------|-------|
| ChatGPT abandoned direct bookings (Mar 2026) | Competitor scan | INTEL | — | Validates D2M concierge model |
| 30% travelers use AI for planning, 2% let AI book | Skift data / GitHub scan | INTEL | — | D2M sits in the sweet spot |
| Gemini Deep Research API (100+ source autonomous research) | Competitor scan | **EVALUATE** | $0 | A2 force multiplier |
| Windsurf Cascade action tracking | Competitor scan | INTEL | — | Inspired our Layer 2 design |
| Claude Code /voice (push-to-talk) | Claude Code scan | **READY** | $0 | Commander voice interface |
| Claude Code /loop (recurring prompts) | Claude Code scan | **EVALUATE** | $0 | Could replace some systemd timers |
| 128K max output tokens | Claude Code scan | **READY** | $0 | Available now |

---

## 7. GRANT NARRATIVE AMMUNITION

| Finding | Source | Significance |
|---------|--------|-------------|
| Multi-persona preference routing = novel contribution | Dembe report | Zero papers, zero production systems doing this |
| PRELUDE/CIPHER validates our architecture | NeurIPS 2024 | Academic validation of thunderbird_learning.py |
| "Adaptive Preference Learning from Behavioral Observation" | Dembe framing | Grant-ready term for our capability |
| D2M concierge model validated by ChatGPT retreat | Competitor scan | Market timing proof |
| 60% disabled veteran, USAFA, SDVOSB | Grant narrative | Eligibility confirmed |

---

## DEPLOYMENT WAVE PLAN

### WAVE 1: NOW (Agents Building — This Session)
1. Security lockdown (shell_exec, localhost, bearer token)
2. Dani wiring (auto-enrich, voice profile, per-recipient rules)
3. Active learning loop (/learn command, morning brief, inbox capture)
4. Information delta tracker (semantic edit analysis)
5. Episodic memory + conversation preference detection
6. Innovation scanner MCP tools + systemd timers

### WAVE 2: THIS WEEK
7. Firecrawl MCP signup + install
8. Aven Hospitality outreach email
9. Positive framing audit of existing principles
10. Context-sensitive retrieval (vector embeddings)
11. Cloudflare Access on MCP endpoint
12. Claude Code /voice evaluation

### WAVE 3: THIS MONTH
13. Dani Voice Agent (Retell AI, $150-180/mo)
14. Zep temporal knowledge graph trial ($25/mo)
15. OpenClaw multi-channel evaluation
16. Gemini Deep Research API for A2
17. Audio briefings from dossiers
18. Per-recipient voice profiles for top 10 contacts

### WAVE 4: NEXT QUARTER
19. A2A protocol compliance
20. Full temporal knowledge graph deployment
21. MCP Connector on API (architecture simplification)
22. Grant submission (with novel contribution evidence)

---

*Inventory compiled by COS (Col Victoria Hale), 2026-03-20*
*99 innovations tracked across 4 scout reports + 6 intel assessments*
*Standing order: Zero-based evaluation. The Domains decide. Commander decides.*
