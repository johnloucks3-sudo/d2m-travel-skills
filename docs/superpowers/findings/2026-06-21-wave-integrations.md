# Wave 1-3 Integration Record — 2026-06-21
*Daily Search Engine · Thunderbird Wing · Commander directive: "document all"*

---

## Daily Search Engine — Live as of 2026-06-21

**Architecture:** Perplexity `sonar` (live web search) → 31 categories × 8 parallel agents  
**Cost:** ~$0.15/wave · 4 waves/day target · ~$18/month  
**Output:** `intel/daily_search/waveN_{timestamp}.json`  
**Run:** `SEARCH_WAVE=N PERPLEXITY_API_KEY=... python3 intel/daily_search/thunderbird_daily_search.py`

### Wave Summary

| Wave | Result | Key Actions |
|---|---|---|
| 1 | 31/31 ✅ | Baseline. 6 weak prompts identified. |
| 2 | 31/31 ✅ | 6 prompts fixed. Atlas Ocean added. API key extraction fixed. ccusage OOM patched. |
| 3 | 31/31 ✅ | Clean compounding run. Integration candidates identified. |

### Why Perplexity (not Gemini, not Sonnet)
Perplexity sonar is a live web search engine — it fetches the actual 2026 web in real-time.
Sonnet and Gemini have training cutoffs and can't see June 2026 content.
Architecture: **Perplexity = fetch stage. Sonnet/Opus = analyze stage (Commander + Hale).**
They are not substitutes.

---

## Integrations Completed — 2026-06-21

### 1. Cloudflare Workers AI (`_call_cloudflare_workers_ai`)
- **File:** `core/ai_infra/thunderbird_model_router.py`
- **What:** Free LLM lane. 10,000 neurons/day, zero credit card required.
- **Model:** `@cf/meta/llama-3.1-8b-instruct` (and others available)
- **Status:** ⏳ WIRED — needs credentials
- **Commander action:** Get free account at dash.cloudflare.com → copy Account ID + create API token
- **Env vars needed:** `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`
- **Fallback:** Gemini Flash-Lite if keys absent

### 2. GitHub Models (`_call_github_models`)
- **File:** `core/ai_infra/thunderbird_model_router.py`
- **What:** Free LLM via GitHub infra (Azure backend). Phi-4, Llama 3.1, Mistral Small, Cohere.
- **Status:** ⏳ WIRED — needs credentials
- **Commander action:** Generate PAT at github.com/settings/tokens with `models:read` scope
- **Env var needed:** `GITHUB_TOKEN` or `GITHUB_PAT`
- **Fallback:** Gemini Flash-Lite if key absent

### 3. Presidio PII Fence (`core/security/pii_fence.py`)
- **What:** Mechanical PII enforcement before OpenCode/DeepSeek dispatch. Doctrine was already written — this is the enforcer.
- **Status:** ✅ LIVE — tested and verified
- **Smoke test results:**
  - `"Client John Smith (john@email.com) has booking PE164714008"` → `"Client <REDACTED> (<REDACTED>) has booking <BOOKING_REF>"`
  - `"2984034 for the Regent Grandeur voyage"` → `"<BOOKING_REF> for the Regent Grandeur voyage"`
  - General travel text → unchanged (no false positives)
- **Usage:** `from core.security.pii_fence import sanitize, sanitize_required`
- **Entities redacted:** PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, booking refs (regex)

### 4. PDF Intelligence — PyMuPDF (replaces Docling for now)
- **What:** Docling (preferred per wave research) blocked by missing system lib `libgthread-2.0.so.0` (OpenCV dependency). PyMuPDF installed as working alternative.
- **Status:** ✅ LIVE — tested on real booking PDFs
- **Smoke test:** Extracted 5,417 chars from 3-page booking confirmation (PE164714008) — names, booking ref, excursion details, contact info all captured
- **Usage:** `import fitz; doc = fitz.open(path); text = '\n'.join(page.get_text() for page in doc)`
- **Note:** Docling re-attempt when `sudo zypper install glib2-devel` resolves the OpenCV issue. PyMuPDF is production-capable for our booking PDF use case.

### 5. Promptfoo Prompt Regression Testing
- **What:** CI gate for prompt drift. Catches broken persona prompts when Claude models update.
- **Status:** ✅ INSTALLED — config scaffolded
- **Config:** `tests/prompts/promptfooconfig.yaml`
- **Tests wired:** Hale identity, PII fence gate, client email tone, WF-17 gate awareness
- **Run:** `cd tests/prompts && promptfoo eval`
- **Owner:** Sterling (A7) — wire into Sunday sweep

---

## Structural Findings — Wave 3 Confirms

### 3 Categories Need Direct Fetch (not Perplexity)
These categories are beyond what any search engine can reliably surface:

| # | Category | Problem | Wave 4 Fix |
|---|---|---|---|
| 2 | MCP Registry New Releases | Perplexity can't see glama.ai registry sorted-by-newest | Playwright fetch: `glama.ai/mcp/servers?sort=newest` |
| 13 | Cruise Line Intelligence | Press rooms, App Store release notes not in general search index | Direct fetch: cruise line press pages + App Store listings |
| 29 | Human Discourse | Reddit/HN thread-level posts not surfaced by sonar | Reddit API call or dedicated HN search |

### Key Intelligence Finds (Action Items for Wing)

**DEMBE:** Yardi added a Virtuoso Connector for Claude — first confirmed AI deployment in the Virtuoso network. Research + brief.

**ELON:** Claude Managed Agents — Anthropic's first-party cloud agent scheduling (beyond Routines, min 1h). Evaluate vs our systemd timers. `Claude Fable 5 / Mythos 5` confirmed in system card PDF — new model family exists.

**STERLING:** Promptfoo eval-native CI — teams treating prompt changes as deployable artifacts, running regression in GitHub Actions. Wire Promptfoo into Sunday sweep.

**WHETSTONE:** pgvectorscale rising as default over standalone Qdrant; Weaviate Engram + Chroma Context-1 are new memory layer products. Assessment needed vs our current Qdrant install.

**DANI:** TurboCall — 2026 voice entrant "voice-first with PMS depth" for hospitality. Evaluate for Commander's phone coverage (719-291-0742).

**HARLAN:** Anti-bot clarified — Bright Data + Oxylabs for Regent-level portals (paid). Firecrawl trial = LLM-friendly extraction only, NOT enterprise anti-bot. Focus Firecrawl trial on Viking brochure pages. Bright Data/Zyte = financial gate when we need real portal access.

---

## Keys Still Needed (Commander action)

| Key | Where | Why |
|---|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | dash.cloudflare.com | Free LLM lane |
| `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com | Free LLM lane |
| `GITHUB_TOKEN` | github.com/settings/tokens (models:read) | Free LLM lane |
| `FIRECRAWL_API_KEY` | firecrawl.dev | 500 free credits, NO-PAY GATE |

---

*— V. Hale, VCS · 2026-06-21 · Thunderbird Wing, D2M*
