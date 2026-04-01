# TEAM MEMBER (API) DISTRIBUTION ARCHITECTURE
**To:** Commander (Yoda)
**From:** Goose (A-Staff Ops)
**Date:** 2026-04-01
**Objective:** Spread compute limits, prevent cycle timeouts, and match cognitive profiles to the optimal LLM API.

## 1. INVENTORY OF TEAM MEMBERS (AVAILABLE APIs)
Based on the API vault, the Wing has access to:
*   **Anthropic:** Claude 3.7 Sonnet / Opus
*   **Google:** Gemini 1.5/2.5 Pro & Flash
*   **Groq:** Llama-3 (Hyper-fast inference)
*   **DeepSeek:** V3 (Chat) & R1 (Reasoning)
*   **OpenAI:** GPT-4o / o1
*   **OpenRouter:** (Gateway to Perplexity, Mixtral, etc.)
*   **Specialty:** AI21 (Jamba), Kimi (Moonshot), Imagen/Nano-Banana, Poe API.

---

## 2. PERSONA TO API MAPPING (The Cognitive Roster)

| Slot | Persona | Role | Assigned API (Team Member) | Rationale |
|------|---------|------|---------------------------|-----------|
| **COS** | Hale | Orchestrator | **Claude 3.7 Sonnet** | Highest instruction-following and context management. Needs to organize the whole board. |
| **A2** | Dembe | Research & Intel | **DeepSeek (V3/R1)** | Exceptional at data extraction, logic parsing, and deep web research without heavy token cost. (Backup: Perplexity via OpenRouter). |
| **A3** | Dani | Client Concierge | **Claude 3.7 Sonnet** | The undisputed best at warm, human, nuanced luxury travel copy. No other model writes emails like Dani. |
| **A5** | Castillo | Strategy & Growth | **OpenAI o1 / DeepSeek R1** | Requires step-by-step business logic, margin analysis, and strategic forecasting. |
| **A6** | Luna | Romance & Narrative | **Kimi (Moonshot) / AI21** | Kimi is highly creative with massive context. AI21 excels at narrative generation. Used specifically for dream-layer writing. |
| **A7** | Sterling | Metrics & Audits | **Groq (Llama-3)** | Needs to instantly rip through log files, JSON payloads, and code to find inefficiencies. Groq's 800+ tokens/sec is perfect for high-speed auditing. |
| **A9** | Harlan | Finance & TESS | **Gemini 2.5 Pro** | Excellent native JSON handling, massive context window for reading massive TESS commission reports or PDFs. |
| **EXEC**| Naia | Visuals & Formats | **Imagen / Nano-Banana** | Generates the visual assets, formatting, and design elements. |
| **A12** | ELON | Innovation | **OpenRouter (Wildcards)** | Routed to experimental models (Mixtral, Cohere) to find non-standard solutions. |

---

## 3. TOOL DISTRIBUTION MAP (Load Balancing)

To prevent hitting rate limits (like Gemini's 10 RPM or Claude's daily limits), tools are permanently mapped to specific APIs.

### 🟢 GROQ (High Volume / Scraping / Triage) - *Near-zero latency*
*   `_runInnovationScan`, `_runWorldIntelligenceSweep` (Initial fast scrapes)
*   `_gmailSearchMessages`, `_driveSearch` (Fast indexing)
*   **Watcher/Scheduler Routing:** The 2-minute dormant scheduler will use Groq to evaluate IF a task needs doing. It costs almost nothing and takes 0.5 seconds.

### 🔵 DEEPSEEK (Logic / Extraction / Recon) - *High reasoning*
*   `_getMultiDomainIntel`, `_scrapeSpecificCruiseLine`
*   `_listTripDossiers`, `_driveGetFileInfo`
*   TESS Commission Audits & Database querying.

### 🟡 GEMINI (Data Processing / Large Docs) - *Massive Context*
*   `_driveReadDocument` (when reading 100-page PDFs)
*   `_systemHealthCheck`
*   `_calendarSyncBookings`

### 🟣 CLAUDE (Final Assembly / Client Facing) - *Premium Tokens*
*   `_draftClientEmail`, `_sendClientEmail`
*   `_gmailCreateDraft`
*   `_createTripDossierTool` (Final narrative assembly)
*   Only invoked when A3, A6, or COS are actively producing final output.

## 4. NEXT STEPS
Once Claude provides the architecture for the "Dormant 2-Minute Scheduler", we will use this exact matrix. The Scheduler (powered by Groq) will wake up, read the queue, and then dispatch the task to the correct API (e.g., waking DeepSeek for A2's research, or Claude for A3's emails) using the `llm_query.ts` tool.
