# STAFF PAPER — M-071: Grok 4 / Grok Build Wing Intel Review
**Classification:** Internal | **Date:** 2026-05-28 | **Authors:** A2 Dembe (Intel) + A12 ELON (Disruption)
**Distribution:** Commander, Hale (COS) | **Format:** T&Q Staff Paper

---

## ISSUE

xAI launched Grok 4.3 (Apr 30, 2026) and Grok Build (May 2026) — a Grok 4-family model and a terminal coding agent — directly competing with Claude Sonnet and Claude Code respectively. Commander requested assessment of: (1) competitive model position, (2) Grok Build vs current wing tooling, (3) D2M-relevant capabilities.

---

## DISCUSSION

### A2 Dembe — Competitive Intelligence (CONFIRMED sources: artificialanalysis.ai, designforonline.com, benchable.ai)

**Grok 4.3 model position:**
- **Intelligence Index score:** 53 — places Grok 4.3 just above Claude Sonnet 4.6 (≈4 pts). CONFIRMED: Grok 4.3 benchmarks above Sonnet on this composite metric.
- **Coding benchmark:** 41.0 Coding Index (top 11% of all models). Strong general coder.
- **Speed:** 194 tok/s output — fast, well above median for reasoning-class models.
- **Context:** 1M token window, no output token limit. Well suited for long-document and multi-step agentic tasks.
- **Price:** $1.25/1M input · $2.50/1M output. Cheaper than Claude Opus, comparable to Sonnet.
- **Perfect-score hallucination benchmark:** 100%. This is notable — Grok 4.3 matched peak performance on factual grounding.
- **D2M intel value:** Grok/X native access remains xAI's structural advantage. Real-time Twitter/X OSINT feeds directly into Dembe intel sweeps at zero latency. Our current OSINT chain routes through web search; Grok's native X integration removes one hop and adds recency.

**Grok Build (grok-code-fast-1 — purpose-built coding model):**
- **SWE-Bench Verified:** 70.8%. For reference, Claude Code scores 72.5% on SWE-Bench Verified (Anthropic, 2025 benchmarks) — Grok Build is within 2 points of parity.
- **Price:** $0.20/1M input tokens — dramatically cheaper than any Claude model. 6× cheaper than Sonnet at standard pricing.
- **Architecture:** 8 parallel sub-agents in Plan → Search → Build workflow. Arena Mode auto-scores competing outputs before human review.
- **Privacy:** Local-first — source code not transmitted to xAI servers (relevant for client PII fence).
- **Access:** SuperGrok ($30/mo) or X Premium+ ($40/mo). Beta expanded May 24, 2026.

---

### A12 ELON — Disruption / Automation Assessment

**Kill or replace opportunity analysis:**

| Current Wing Tool | Grok Build Replaces? | ELON Verdict |
|---|---|---|
| Claude Code (primary dev) | **NO** — We're on MAX ($0 marginal). Grok Build's cost advantage is ~$0.20/1M vs our effective $0/task. No economic kill. | KEEP CC |
| OpenCode (secondary) | **CANDIDATE** — OpenCode runs Gemini 2.5 Flash. Grok Build at $0.20/1M with SWE-Bench parity and 8-parallel-agent Arena Mode is a direct upgrade candidate. | EVALUATE |
| A2 Dembe OSINT | **AUGMENT** — Grok 4.3's X/Twitter native access should be added to Dembe's daily sweep as a supplemental source. Not a replacement — it adds recency. | ADD NOW |

**Arena Mode is the differentiating feature.** Claude Code doesn't have an equivalent. Auto-scoring 8 competing outputs before human review is a genuine process innovation — especially for D2M use cases where output quality matters more than speed (client emails, proposals, research).

**Recommendation from ELON:** Add a Grok 4.3 inference path for A2 Dembe's daily X/Twitter OSINT scan. Pilot Grok Build as an OpenCode replacement for a 2-week test. If Arena Mode shows measurable quality lift on coding tasks (wing scripts, MCP tools), nominate OpenCode sunset as the next kill audit item.

---

## OPTIONS

| Option | Action | Cost | Risk |
|---|---|---|---|
| A | Add Grok 4.3 to Dembe OSINT chain only | Low ($30/mo SuperGrok) | LOW |
| B | Pilot Grok Build as OpenCode replacement (2-week test) | Low (included in A) | LOW — CC fallback intact |
| C | Full Grok Build deployment, OpenCode sunset | Moderate | MEDIUM — vet Arena Mode reliability first |

**A2 + ELON joint recommendation: Option A immediately, Option B within 30 days.**

---

## ACTIONS

| # | Action | Owner | Suspense |
|---|---|---|---|
| 1 | Add Grok API key (SuperGrok or xAI API) to OSINT chain for X/Twitter scan | A12 ELON | 2026-06-04 |
| 2 | Install Grok Build CLI, run against a wing script task for baseline | A12 ELON | 2026-06-04 |
| 3 | 2-week Grok Build vs OpenCode side-by-side pilot — 5 coding tasks | A2 Dembe (eval), A12 ELON (run) | 2026-06-14 |
| 4 | Commander decision on Option A/B/C after pilot readout | Commander | 2026-06-14 |

---

*— Lt Col Marcus "Wraith" Dembe, A2 · ELON, A12 · 2026-05-28*
*Sources: [artificialanalysis.ai](https://artificialanalysis.ai/models/grok-4-3) · [devops.com/Grok Build](https://devops.com/xai-enters-the-coding-agent-race-with-grok-build/) · [androidheadlines.com](https://www.androidheadlines.com/2026/05/xai-grok-build-agentic-ai-coding-tool-launch-beta.html) · [x.ai/news/grok-build-cli](https://x.ai/news/grok-build-cli)*
