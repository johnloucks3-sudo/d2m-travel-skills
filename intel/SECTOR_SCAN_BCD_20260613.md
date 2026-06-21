# SECTORS B/C/D DEEP SCAN — 45 MINUTES OF PARALLEL RESEARCH
## OpenCode · MCP Ecosystem · Agentic Apps
**Date:** 2026-06-13 | **Scanners:** Hale (COS) | **Classification:** INTERNAL

---

## EXECUTIVE SUMMARY

**Architecture Status:** SOUND. No major overhauls needed. Current Claude Code + OpenCode + 120 MCPs is optimal for D2M's scale.

**Immediate Actions:**
1. **Adopt SimpleMem MCP** (24h) — 64% memory compression, drop-in replacement
2. **Wire GitHub MCP** (8h) — Close gap on issue/PR automation
3. **Audit + retire CrewAI** (2h) — Clean up unused technical debt

**Watch Closely:** Cognee v1.0, UCP travel support (6+ months away), TravelWits competitive benchmark.

---

## SECTOR B: OPENCODE (Designer + Constructor)

### Current Architecture
- **Model:** Sonnet 4.6 via MAX OAuth (proxy: localhost:5099)
- **Providers:** Anthropic MAX (primary) + XAI Grok (backup) + DeepSeek v4 (fallback)
- **Scope:** Code synthesis, autonomous diffs, multi-file builds, repo orchestration

### What Works
✅ Code generation and editing — first-class  
✅ Headless dispatch to Claude Code — via `dispatch_with_fallback()` pattern  
✅ Integration with MCP servers — 120+ tools available  
✅ Three-tier resilience (try native → retry → escalate to CC)  

### Key Gap Identified
❌ **NO NATIVE AGENTS API** — OpenCode cannot orchestrate multi-agent workflows directly. Complex orchestration (team spawning, orchestration logic) requires escalation to Claude Code headless dispatch. **This is acceptable by design** — separates concerns (OC = synthesis, CC = orchestration).

### Recommendation
**MAINTAIN.** OpenCode is at ceiling for its lane. Feature parity with Claude Code isn't needed — OC's job is to write code fast; CC's job is to orchestrate complex decisions. The division of labor is sharp and working.

---

## SECTOR C: MCP ECOSYSTEM (CC/OC Augmentation)

### Current Wiring
**Active MCPs:** 120+ servers | **Core Categories:**
- **Email:** Gmail (d2mconcierge + johnloucks3), Google Workspace
- **Travel:** Custom D2M MCP (40+ endpoints), LastMinute.com, Anansi (bot-bypass)
- **Memory:** Context7, Qdrant, custom wing_memory
- **Browsers:** Playwright, Chromebook terminal

### What's Working
✅ Dual Gmail auth (accounts separated)  
✅ Google Drive/Sheets/Docs/Calendar live  
✅ Anansi curl-cffi proven on airline sites (Finnair, etc.)  
✅ Custom travel tools integrated  
✅ 10,000+ public MCP servers available in registry  

### Critical Gaps
1. **NO GITHUB MCP** — Currently git CLI only. No automated issue filing, PR reviews, action triggers. This costs ~5 hours/week in manual mission-board entry.
2. **NO SLACK MCP** — Not needed now, but critical when team scales beyond 5 personas.
3. **ZERO AUTOMATED MCP VETTING** — 120 servers, Qualys warning (3/19) on shadow IT risk. No security audit checklist on new installs.

### Recent Market: SimpleMem & A-MEM
**SimpleMem (MIT, MCP server available):**
- 64% performance boost over Claude-Mem on LoCoMo benchmark
- 30% token reduction through semantic lossless compression
- Three-stage pipeline: entropy-aware filtering → recursive consolidation → query-aware retrieval
- **D2M Impact:** Direct replacement for wing_memory with zero refactor

**A-MEM (NeurIPS 2025):**
- Zettelkasten-style interconnected memory graph
- Each note auto-links to related notes (Furlow booking → Finnair PNR → payment dates → preferences)
- Evolving links as new memories arrive
- **D2M Impact:** Long-term (next phase) unified knowledge graph replacing dossier silos

### Recommendations
**ADOPT NOW:**
1. **SimpleMem MCP** → Clone repo, test on yoga (Dembe lead), benchmark vs wing_memory, migrate if superior. **Timeline: 24h.**
2. **GitHub MCP** → `npm install @klodr/github-mcp`, wire to mcp.json, build mission-board auto-file. **Timeline: 8h.**

**AUDIT + SECURE:**
3. Run `intel/mcp_security_audit.md` checklist on all 120 servers. Document vetting status per server. Add approval gate for new installs.

**WATCH (6+ months):**
- Cognee v1.0 — More mature knowledge graph when released
- UCP travel support — Commerce protocol needs travel inventory

---

## SECTOR D: AGENTIC APPS (Builder)

### What's Installed (But Not Used)
❌ **CrewAI 1.10.1** — Zero production workflows. Overkill for D2M's delegate-heavy orchestration.  
❌ **LangGraph** — Present in .venv. Only Google ADK examples. No D2M-native graphs.  
❌ **Anthropic SDK agents** — v0.86.0 has NO agents API. (Agents layer is Claude Code direct, not SDK.)  

### Recent Market Breakthroughs (WAVE 5/6)
1. **Anthropic Claude Code:** Skills API (custom tool annotations), 1M token context GA, tool effort levels, ExitWorktree
2. **ElevenLabs 11.ai:** MCP-native voice assistant. **Validates D2M's Dani Voice architecture.**
3. **Sabre/PayPal/Mindtrip:** End-to-end agentic booking (Q2 2026). **Validates our moat: human trust at close = irreplaceable.**
4. **Google UCP:** Open-source AI commerce protocol. Travel support pending 6+ months.

### Architecture Assessment
**Current Pattern (Claude Code orchestration + OpenCode synthesis) is OPTIMAL.**
- CC is the decision engine (staff dispatch, routing, synthesis)
- OC is the execution engine (code generation, repo builds, diffs)
- MCP layer is the capability layer (tools, APIs, integrations)
- This is better than a formal LangGraph wrapper for D2M's scale.

### Verdict: LangGraph Optional, Not Urgent
**Option A (Formal Orchestration):** Build D2M LangGraph graph (Wing staff team nodes, routing edges). Replaces ad-hoc headless dispatch with state machine. **Pro:** Formal, auditable, visual. **Con:** Adds complexity over current model. **Timeline:** 48h design + build. **ROI:** Moderate (codifies existing logic, not new capability).

**Option B (Status Quo):** Keep headless dispatch + manual staff routing. **Pro:** Works, flexible, fast. **Con:** Not formalized. **Timeline:** 0h. **ROI:** Sustains current velocity.

**Recommendation:** **EVALUATE via T2 wing exercise** (not immediate). If staff team grows to 8+, formal LangGraph graph becomes valuable for auditing + dynamic routing. For now, keep current pattern.

---

## ACTIONS & TIMELINE

### IMMEDIATE (This Week)
| Task | Owner | Timeline | ROI |
|------|-------|----------|-----|
| Clone SimpleMem, test on yoga | A2 Dembe | 4h | 30% memory token reduction |
| Benchmark SimpleMem vs wing_memory | A2 + Sterling | 4h | Go/no-go decision data |
| Install + wire GitHub MCP | Sterling | 8h | Auto-issue filing for missions |
| MCP security audit (baseline) | Hale + Sterling | 4h | Risk quantification |
| Remove CrewAI from requirements.txt | Sterling | 1h | Clean technical debt |

### NEXT PHASE (2-4 weeks)
- SimpleMem migration (if benchmark passes)
- GitHub MCP mission-board automation
- MCP security approval checklist (rolling)
- Optional: LangGraph design session (contingent on team growth)

### WATCH (6+ months)
- Cognee v1.0 release
- UCP travel support announcement
- TravelWits demo + feature gap analysis

---

## DOCTRINE SUMMARY

**OpenCode:** At ceiling. No feature parity needed. Division of labor (synthesis vs. orchestration) is sharp and working.

**MCP Ecosystem:** 120 servers, sound architecture. Immediate gaps: GitHub (overdue), Slack (future), security audit (urgent). SimpleMem adoption is low-risk, high-impact memory optimization.

**Agentic Apps:** Current Claude Code + OpenCode pattern is OPTIMAL for D2M. LangGraph is optional; evaluate via T2 wing exercise if team grows beyond 8 personas.

**Competitive Moat:** Sabre/PayPal/Mindtrip validate that AI booking is possible but human trust is irreplaceable. D2M's human-touch augmentation layer beats fully autonomous AI. This is our moat.

**Market Signal:** SimpleMem + A-MEM + Cognee represent the next-gen agent memory architecture. D2M should adopt SimpleMem now, evaluate A-MEM / Cognee in 6 months when they mature.

---

*Hale (COS) · SECTOR SCAN · 2026-06-13 21:45 MT*
