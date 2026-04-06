Here's the full linkage:

---

# ⚠️ COMMANDER DIRECTIVE 2026-04-05: $0 COST TARGET
# Gemini burned $100 unexpectedly. NO Gemini in any autonomous loop.
# Deepseek is gone. Groq conditional. Qwen 3.6 Plus Free is the Goose engine.
# Goose covers EXEC (Blackboard interface).

## THUNDERBIRD MODEL / PERSONA / TOOL LINKAGE

### Layer 1: Model Router (`thunderbird_model_router.py`)
*Claude Code + direct Python calls. Routes by task type.*

| Task Type | Model | Cost/1M In | Personas | Use Case |
|---|---|---|---|---|
| `CLIENT_FACING` | Claude Sonnet 4 | $0 (Max) | Dani (A3), EXEC | Client emails, proposals |
| `CREATIVE` | Claude Sonnet 4 | $0 (Max) | Luna (A6), EXEC | Narratives, brand copy |
| `CRISIS` | Claude Sonnet 4 | $0 (Max) | COS (Hale) | Time-sensitive logistics |
| `STRATEGIC` | Claude Sonnet 4 | $0 (Max) | A5 (Viper), A9 (Vic) | Pricing, growth, business |
| `CODE_GENERATION` | Claude Sonnet 4 | $0 (Max) | ELON (A12) | Scripts, features |
| `VOICE_PROFILE` | Claude Sonnet 4 | $0 (Max) | EXEC | Tone analysis, voice rules |
| `MORNING_BRIEF` | Claude Sonnet 4 | $0 (Max) | COS (Hale) | Daily synthesis |
| `PRINCIPLE_EXTRACTION` | Claude Sonnet 4 | $0 (Max) | COS (Hale) | Staff Skill #1-3 |
| `ANALYTICAL` | Claude Sonnet 4 | $0 (Max) | A9 (Vic), A7 (Gauge) | Audits, comparisons |
| `RESPONSE_MONITOR` | Claude Sonnet 4 | $0 (Max) | COS (Hale) | QA gate over Haiku |
| `RESEARCH` | Claude Haiku 3 | $0 (Max) | A2 (Wraith) | Search, lookups |
| `OPERATIONAL` | Claude Haiku 3 | $0 (Max) | COS (Hale) | Status checks, routing |
| `CLASSIFICATION` | Claude Haiku 3 | $0 (Max) | COS (Hale) | Email triage |
| `DATA_EXTRACTION` | Claude Haiku 3 | $0 (Max) | — | Parsing structured data |
| `SUMMARIZATION` | Claude Haiku 3 | $0 (Max) | — | Quick summaries |
| `EXTRACTION` | Claude Haiku 3 | $0 (Max) | — | Data extraction |
| `CONTEXT_DUMP` | **Qwen 3.5 Flash** | $0.065 | — | Bulk context ingestion |
| `BULK_REVIEW` | **Qwen 3.5 Flash** | $0.065 | — | Codebase/doc review |
| `SIMPLE_ANALYSIS` | **Gemini 2.5 Flash-Lite** | $0.10 | — | Simple classification |
| `IMAGE` | FLUX.1 Schnell | $0 (free) | Luna (A6) | Destination art |

### Layer 2: OpsCenter Task Processor (`task_processor.py`)
*Telegram C2 → queue → Hale-Loop daemon. Routes by task bucket.*

| Task Bucket | Model | Tasks Included | Notes |
|---|---|---|---|
| **GROQ_TASKS** (misnomer — actually Gemini now) | **Gemini 2.5 Flash** | OPERATIONAL, CLASSIFICATION, SUMMARIZATION, RESEARCH, DATA_EXTRACTION, EXTRACTION | Hale's brain. Was 3.1 Pro (**fixed today**) |
| **GEMINI_TASKS** | Gemini 2.5 Flash | MORNING_BRIEF | Dedicated synthesis |
| **Everything else** | Claude MAX queue | CLIENT_FACING, CREATIVE, VOICE_PROFILE, CRISIS, STRATEGIC, CODE_GENERATION | Queued — MAX tokens are scarce |

### Layer 3: External Agents (Goose/Cline)
*Autonomous intel/scanning. Separate process.*

| Agent | Model | Use Case |
|---|---|---|
| Goose | Gemini 2.5 Flash | Intel scanning, research sweeps, bulk ops |
| Cline CLI | Gemini 2.5 Flash | YOLO mode coding tasks |

### Layer 4: Persona → Model Affinity

| Persona | Primary Model | Fallback | Scope |
|---|---|---|---|
| **COS (Hale)** | Gemini 2.5 Flash (OpsCenter) / Sonnet (Claude Code) | Gemini Flash | Orchestration, routing, briefs |
| **EXEC (Naia)** | Claude Sonnet 4 | — | Voice, brand, Commander's intent |
| **A2 Wraith** | Claude Haiku 3 | Gemini Flash | Research, intel |
| **A3 Dani** | Claude Sonnet 4 | Groq Llama (REVERIE) | Client-facing only |
| **A5 Viper** | Claude Sonnet 4 | — | Strategy, pricing |
| **A6 Luna** | Claude Sonnet 4 | — | Creative, narratives |
| **A7 Gauge** | Claude Sonnet 4 | — | Process improvement |
| **A9 Vic** | Claude Sonnet 4 | — | Finance, commissions |
| **A12 ELON** | Claude Sonnet 4 | — | Automation, code |
| **CH Padre** | Claude Sonnet 4 | — | Ethics, morale |

### Layer 5: API Keys & Providers

| Provider | Env Var | Cost Model | Status |
|---|---|---|---|
| Anthropic (Max) | `ANTHROPIC_API_KEY` | $0 (Max plan) | Active |
| Google AI Studio | `GOOGLE_AI_API_KEY` | $0.30/1M (Flash) | Active |
| OpenRouter | `OPENROUTER_API_KEY` | $0.065/1M (Qwen) | **Needs key in .env** |
| Groq | `GROQ_API_KEY` | $0.05/1M (Llama) | Active (REVERIE) |
| xAI (Grok) | `XAI_API_KEY` | $0.20/1M | Active (OSINT) |
| DeepSeek | `DEEPSEEK_API_KEY` | $0.14/1M | Active (PII-fenced) |
| Together AI | `TOGETHER_API_KEY` | Free (FLUX) | Active (images) |
| HuggingFace | `HF_API_KEY` | Free tier | Active |

### Fallback Chains (Post-Commander Directive)

```
Qwen 3.6 Plus Free → Claude Haiku 3 (MAX) → STOP (no escalation)
Claude Sonnet → STOP (fail gracefully, alert Commander)
Groq → STOP (conditional, alert Commander if unavailable)
NEVER → Gemini (explicitly excluded per Commander directive)
```

### Cost Targets
| Agent | Model | Cost/1M Input | Monthly Target |
|-------|-------|---------------|----------------|
| Goose | Qwen 3.6 Plus Free | $0 | $0 |
| Claude | Sonnet 4 (MAX OAuth) | $0 | $0 |
| Groq | Llama (conditional) | $0.05 | Monitor only |
