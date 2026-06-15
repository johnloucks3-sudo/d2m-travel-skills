# STAFF PAPER — Google AI Pro Integration into the Thunderbird AI Stack

**SPSA-2026-06-15 · Google AI Pro ($20/mo) + Gemini API Assessment**
**To:** Commander (Gen John "Yoda" Loucks) · COS Hale (VCSAF)
**From:** Hale, COS — Thunderbird Wing, Dreams2Memories Travel, LLC
**Date:** 2026-06-15
**Classification:** Internal · Architecture decision (no $ commitment in this paper)
**Re:** Commander mandate — "If I'm paying for it, we use it. NO OPENROUTER — straight Google AI."

---

## BLUF (Bottom Line Up Front)

1. **What you pay $20/mo for (Google AI Pro) does NOT include programmatic API access.** It is a *consumer UI* subscription — the Gemini app, NotebookLM Plus, Deep Research, Gemini-in-Workspace (Gmail/Docs/Sheets), creative models, and 5 TB storage. There are **no API keys, no API credits, and no developer access** in the AI Pro plan. Confirmed on Google's own plans page.

2. **The autonomous stack calls the Gemini API — which is billed separately, pay-as-you-go.** "Using what you pay for" via the *app* and "calling Gemini from our code" are two different products with two different bills. Be honest with yourself on this: the $20 sub buys you nothing your scripts can call.

3. **There is no OpenRouter bill to "save."** Today the orchestrator defaults *everything* to Claude MAX ($0 via OAuth); OpenRouter is reserved for arbitration and runs at effectively ~$0. So this migration is **not** a cost-cutting move — it is (a) honoring "use what I pay for" through the *app surfaces* at $0 marginal, and (b) optionally adding a **paid Gemini API fallback/diversity layer** for when Claude MAX hits weekly limits.

4. **The privacy crux that drives the architecture:** On the Gemini API, **FREE tier = Google trains on your prompts; PAID tier (billing enabled) = Google does NOT.** Our hard PII fence (client names, booking refs, payment data never leave to a trainable model) therefore means: **free-tier Gemini may only ever touch NON-PII work.** Any PII-bearing or client-facing task that goes to Gemini must go to **paid** Gemini (or stay on Claude MAX, which is paid and does not train).

5. **Recommendation:** Honor the mandate cleanly — kill the OpenRouter gateway (a security win: retires a hardcoded key), wire the *app* surfaces into daily ops at $0, and stand up Gemini API as a **secondary/diversity engine** with a strict free-vs-paid split governed by the PII fence. **Claude MAX stays primary** (already paid, $0 marginal, no-train). Projected new Gemini API spend: **$0–$8/mo expected, ~$25/mo high** under disciplined routing (math in §Cost Estimate). Move the Google keys into a secrets manager before any of this goes live (per the 2026-06-15 security audit).

---

## Background

The Commander subscribes to **Google AI Pro** ($19.99/mo). Directive: integrate it seriously into the Thunderbird AI stack, with two constraints — **"if I'm paying for it, we use it"** and **"NO OPENROUTER — straight Google AI."**

The stack already has a Gemini integration *partly built but unused in production*:
- **MISSION-127** (hale_state.json): "Gemini adapter re-enabled; GEMINI_LARGE_CONTEXT tier added (1M ctx, direct API); gemini_file_reader.py built; NotebookLM workspace setup PENDING Commander action."
- `core/ai_infra/gemini_client.py` (A7 Sterling, 2026-06-01) is a clean single-chokepoint wrapper that already maps **Flash-Lite → Haiku-tier, Flash → Sonnet-tier, 2.5 Pro → Opus-tier**, with an allowlist guard and Harlan usage logging.
- **But it has never run in production** — `core/ai_infra/data/gemini_usage.jsonl` contains **6 records, all `A7_smoke_test`**. Gemini is wired and idle.

Current production routing (CLAUDE.md "Model Routing" + orchestrator):
- **Claude (MAX OAuth, $0 marginal)** = default for synthesis, client copy, judgment. Haiku/Sonnet/Opus tiers.
- **Grok Build (XAI direct key)** = ZEN counter-voice; **DeepSeek** = fallback. Invoked via OpenCode (`OpsCenter/opencode_zen_counter.py`).
- **OpenRouter** = the `multi_model_orchestrator.py` THOS gateway — but it *defaults to Claude MAX* and only touches OpenRouter for arbitration. Effective spend ~$0.
- **PII fence (hard rule):** OpenCode/DeepSeek/OpenRouter never receive client PII. Claude Sonnet may, when needed for client work.

---

## Discussion

### 1. The crux: Google AI Pro (consumer) vs. Gemini API (developer) — they are SEPARATE products and SEPARATE bills

**Google AI Pro — what the $20 buys (consumer, UI-only).** Per Google's plans page (one.google.com/about/google-ai-plans), AI Pro includes:
- Expanded access to **Gemini 3.1 Pro** *in the Gemini app* (gemini.google.com), 4× higher usage limits vs. free.
- **Deep Research** (autonomous multi-step web research agent → cited 10–50pp report).
- Expanded **NotebookLM** (NotebookLM Plus) — higher source/notebook limits.
- **Gemini in Workspace** — proofread in Gmail, "work smarter" in Docs/Sheets, Gmail inbox AI Overview (US), Chrome auto-browse (US).
- Creative models (image/music/video — Lyria 3, Veo-class), **5 TB** storage, plus bundles (YouTube Premium Lite, Google Home Premium, Health Premium).

> **Critical finding (verified on Google's page):** AI Pro provides **UI-only access** through Google's consumer apps. **No programmatic API access, no Gemini API credits, no developer API keys.** API access is a separate offering (Google AI Studio / Vertex AI), not part of the consumer subscription.

**Gemini API (Google AI Studio) — what our code actually calls (developer, pay-as-you-go).** This is the programmatic path: get a key at aistudio.google.com, call `generativelanguage.googleapis.com`, pay per token. There is a **free tier** (rate-limited) and a **paid tier** (billing enabled). This is what `gemini_client.py` already targets.

**Vertex AI** — the enterprise path: the same Gemini models served through Google Cloud (GCP), billed via a GCP project with IAM, VPC controls, and enterprise data terms. Heavier to operate; warranted only if/when D2M needs enterprise data-residency or GCP-native governance. **Not recommended now** — overkill for a one-person agency.

**Honest bottom line:** Using the **app** (NotebookLM, Deep Research, Gemini-in-Gmail) *is* "using what you pay for" and costs **$0 marginal**. But it cannot be called from the autonomous stack. The moment a script needs Gemini, it hits the **API**, which the $20 sub does **not** cover. The two never connect.

---

### 2. Current-stack assessment

| Component | State | Finding |
|---|---|---|
| `core/ai_infra/gemini_client.py` | Built, allowlist-guarded, Harlan-logged | **Production-ready.** Clean 3-tier mapping. The right chokepoint. |
| `core/ai_infra/gemini_file_reader.py` | Built (12.9 KB) | Large-context file reader — pairs with GEMINI_LARGE_CONTEXT tier. |
| Gemini production usage | **6 smoke tests only** | Wired but **never used in anger.** This is the gap MISSION-127 should close. |
| `multi_model_orchestrator.py` | OpenRouter THOS gateway | Defaults to Claude MAX; OpenRouter ~$0. **Hardcoded OpenRouter key at line 27** (security audit H10). |
| `agents/thunderbird_llm_proxy.py` | Together AI proxy, port 3002 | **Hardcoded Together key at line 14** (audit H10). Separate concern; not OpenRouter, but same key-hygiene class. |
| ZEN counter-voice | Grok (XAI) primary / DeepSeek fallback | Model **diversity** is its whole value — see §Recommendation. |
| Keys present in `.env` | `GEMINI_API_KEY`, `GOOGLE_AI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY` (all point at the same AI Studio key), plus `OPENROUTER_API_KEY`, `XAI_API_KEY`, (DeepSeek purged) | Three Google aliases already exist. `gemini_client.py` reads `GOOGLE_AI_API_KEY`. |

**Volume basis (stated honestly — it is thin).** We do **not** have a clean token/day meter:
- `gemini_usage.jsonl` = smoke tests only (no production signal).
- `hale_state.json → brain_routing_log` = **5 entries** total (sparse).
- `OpsCenter/usage_ledger.json` = **mission-runs, not tokens** — ~30 routine runs/day on busy days (Jun 9–10), 4 on a quiet day (Jun 15).

So the cost estimate below is built from **explicit assumptions**, not a measured meter. Treat it as a planning range, not a forecast.

---

### 3. Data-governance constraint that decides the architecture

From Google's pricing page (ai.google.dev/gemini-api/docs/pricing), the free-vs-paid data terms are the inverse of intuition:

| Tier | Google trains on your prompts/outputs? |
|---|---|
| **Free tier** | **YES** — "Content used to improve our products." |
| **Paid tier** (billing enabled) | **NO** — "Content not used to improve our products." |

This collides directly with our **hard PII fence**. The mapping that respects both:

- **Free-tier Gemini (Flash / Flash-Lite)** inherits the *exact* fence that governs OpenRouter today → **non-PII work only** (research synthesis on public data, classification of non-client text, log scans). $0, but Google may train on it — so never client data.
- **PII-bearing or client-facing** work → **Claude MAX** (paid, no-train, $0 marginal) **or paid Gemini** (no-train). **Never free-tier Gemini.**

This is cleaner and more honest than a 1:1 "replace OpenRouter roles with Gemini" swap.

---

### 4. Options

- **Option A — App-only ("use what I pay for," literally).** Wire NotebookLM/Deep Research/Gemini-in-Workspace into human-in-the-loop ops. $0 marginal. **Does not touch the autonomous stack at all.** Fully honors the $20 but adds zero programmatic capability.
- **Option B — App + free-tier API only.** A, plus route non-PII cheap ops to free-tier Flash-Lite. $0, but rate-limited and Google-trains-on-it (non-PII fence holds). Fragile under load (free RPM/RPD caps).
- **Option C — App + tiered API (free for non-PII, paid for PII/quality), Claude MAX stays primary. [RECOMMENDED]** Honors the mandate on both fronts: app surfaces at $0, Gemini API as a real second engine with the free/paid split governed by the PII fence. Small, controllable paid spend.
- **Option D — Gemini-primary (replace Claude MAX).** Rejected. Claude MAX is already paid and $0 marginal; displacing it *adds* cost and throws away a paid asset. Also collapses model diversity. Counter to the four-roles "use what's paid for" logic applied to MAX.

---

## Cost Estimate (show the math)

**Pricing — verified on Google's pricing page (paid tier, per 1M tokens):**

| Model | Input (≤200K) | Output (≤200K) | Tier role |
|---|---|---|---|
| Gemini 2.5 Flash-Lite | **$0.10** | **$0.40** | Haiku-equivalent (cheap ops) |
| Gemini 2.5 Flash | **$0.30** | **$2.50** | Sonnet-equivalent (fallback synth) |
| Gemini 2.5 Pro | **$1.25** | **$10.00** | Opus-equivalent (high-quality) |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | newer Lite |
| Gemini 3.5 Flash | $1.50 | $9.00 | newer Flash |
| Gemini 3.1 Pro (Preview) | $2.00 ($4 >200K) | $12.00 ($18 >200K) | newest Pro · **no free tier · no-train** |

**Assumptions (explicit — adjust these and the total moves):**
- Wing makes **~30–60 Gemini API calls/day** *only when Claude MAX is throttled or for non-PII bulk ops* (most work stays on MAX). Call this the "fallback/diversity" load, not the whole stack.
- Average call: **~2,000 input tokens + ~600 output tokens** (digest-style — our token-discipline SO caps outputs).
- Routing split of those calls: **70% Flash-Lite** (cheap ops/classification), **25% Flash** (synthesis fallback), **5% 2.5 Pro** (hard reasoning).

**Per-call cost:**
- Flash-Lite: (2000 × $0.10 + 600 × $0.40) / 1e6 = **$0.00044**
- Flash: (2000 × $0.30 + 600 × $2.50) / 1e6 = **$0.00210**
- 2.5 Pro: (2000 × $1.25 + 600 × $10.00) / 1e6 = **$0.00850**

**Blended per-call** = (0.70 × 0.00044) + (0.25 × 0.00210) + (0.05 × 0.00850) = **$0.00126/call**

| Scenario | Calls/day | Monthly cost (×30) |
|---|---|---|
| **Low** (20 calls/day, mostly Flash-Lite) | 20 | **~$0.55/mo** |
| **Expected** (45 calls/day, blend above) | 45 | **~$1.70/mo** |
| **High** (150 calls/day, heavier Flash/Pro mix) | 150 | **~$8–$12/mo** |
| **Worst-case ceiling** (Gemini becomes primary, 400 calls/day, Pro-heavy) | 400 | **~$25–$40/mo** |

**Interpretation:** Under the recommended routing (Claude MAX primary, Gemini as non-PII + fallback), **expected new spend ≈ $2/mo; realistic high ≈ $8–12/mo.** This is *additive* to the $20 app sub — there is no OpenRouter bill being replaced (current OpenRouter ≈ $0).

**Can we live in the free tier?** Partly. Free-tier Flash/Flash-Lite carry RPM/RPD caps (the wing's bursty mission-runs can trip RPD on a busy night), and **free tier trains on the data** — so free tier is usable **only for non-PII** work. PII and client copy must be paid (or Claude MAX). The honest answer: **free tier covers the cheap non-PII tail; the rest needs paid or MAX.**

> ⚠️ **Stale-doc finding:** `gemini_client.py` docstrings cite "2.5 Pro free: 5 RPM/250K TPD." Sources indicate Google **pulled Pro models from the free tier (≈ Apr 1 2026)** — newest **3.1 Pro Preview has NO free tier.** The wrapper's free-tier allowlist may need a refresh; verify live RPM/RPD before relying on free Pro.

---

## Recommendation

**Adopt Option C.** Specifics:

### A. Honor "use what I pay for" — wire the $20 app surfaces into ops ($0 marginal)
1. **NotebookLM Plus** → research & dossier prep. Upload client dossiers / cruise-line PDFs / port research; use it as the grounded Q&A layer (it answers only from uploaded sources — good for fact-discipline / Rule 1). Closes the MISSION-127 "NotebookLM workspace PENDING" item. *(Human-in-the-loop; not an autonomous call.)*
2. **Deep Research** → intel sweeps & competitor/destination scans. Commander or Hale-via-app runs it; output feeds the brief.
3. **Gemini-in-Workspace** → Gmail proofread / Docs drafting assist for the Commander's own pen (not a substitute for the creative chain or WF-17).

> These are real uses of the paid sub. None of them is a stack API call — and that's the point: the app value is real and free-at-margin.

### B. Stand up Gemini API as a SECONDARY / diversity engine (paid tier where it matters)
Map the existing `gemini_client.py` tiers into production, governed by the PII fence:

| Current role | Engine | Notes |
|---|---|---|
| **Cheap ops / Haiku-tier** (classification, log scans, non-PII extraction) | **Gemini 2.5 Flash-Lite** — **free tier OK** | Non-PII only (free = trains). $0. |
| **Synthesis fallback / Sonnet-tier** when Claude MAX is throttled | **Gemini 2.5 Flash — PAID** | Paid = no-train → may carry PII. ~$2/1M out. |
| **High-quality / Opus-tier** hard reasoning fallback | **Gemini 2.5 Pro — PAID** | Use sparingly. No-train. |
| **Primary synthesis & ALL client copy** | **Claude MAX (unchanged)** | Already paid, $0 marginal, no-train. Stays primary. |
| **ZEN counter-voice** | **KEEP Claude MAX or Grok — do NOT convert to Gemini** | Diversity is the value; Gemini-reviewing-Gemini is not a counter-voice. Pair Gemini-vs-Claude if you want a Google voice in the room. |

### C. Honor "NO OPENROUTER" — retire the gateway cleanly
- **Kill the OpenRouter path** in `multi_model_orchestrator.py` (it already defaults to Claude MAX; OpenRouter is vestigial). This **also retires the hardcoded OpenRouter key at line 27** — a direct security-audit win (H10).
- **Judgment call to flag, not silently make:** the **XAI/Grok-direct** ZEN counter-voice is *not* OpenRouter and gives genuine model diversity. The mandate says "no OpenRouter," not "no non-Google." **Recommend keeping Grok-direct (or Claude) as the diverse counter-voice;** killing it to be "all-Google" would weaken the counter-voice's core purpose. Commander's call.

### Migration steps
1. **Secrets first (gate).** Move `GOOGLE_AI_API_KEY` (+ the two aliases) out of world-readable `.env` into the secrets manager the audit recommends (**Infisical / Doppler**, runtime injection). Do **not** add Gemini load on top of the current key-exposure (audit H5/H10). Add IP/referrer restriction on the Google API key in Cloud Console.
2. **Enable billing** on the AI Studio project (flips Flash/Pro to **no-train** paid tier; raises rate limits). Keep a separate **free-tier project** for non-PII Flash-Lite if you want $0 on that tail.
3. **Refresh `gemini_client.py`** allowlist/quotas for the post-Apr-2026 free-tier reality (Pro may be paid-only now); add a paid-vs-free routing flag so PII work never selects a free-tier model.
4. **Flip cheap-ops** non-PII routes to `call_gemini_lite`; add Gemini as the **fallback** when Claude MAX returns a 429/throttle (max_proxy already does Haiku fallback — add Gemini Flash as a second fallback).
5. **Decommission OpenRouter** in the orchestrator; remove the hardcoded key.
6. **Meter it.** `gemini_usage.jsonl` already logs every call (Harlan). Add a weekly cost line to the AM brief so spend stays visible.

### Risks
- **Rate limits / RPD trips** on bursty mission-run nights (free tier especially). Mitigation: paid tier for anything load-bearing; throttle/backoff in the client (already present).
- **Free-tier data-use** — the #1 risk. One client name through a free-tier call = PII-fence breach + Google training on it. Mitigation: code-enforced free-vs-paid routing flag (step 3); never let a PII path select a free model.
- **Key security** — Google keys are currently in world-readable `.env`; the audit flagged this. **Gate the whole rollout behind the secrets-manager move.**
- **Stale free-tier assumptions** in the wrapper docstrings (Pro free tier likely gone). Verify live before relying on it.
- **Model-diversity loss** if Grok/Claude counter-voice is replaced by Gemini. Keep a non-Google voice in the room.

---

## Sources

- Google AI plans (AI Pro contents, $19.99, UI-only): https://one.google.com/about/google-ai-plans/
- Gemini API pricing (per-1M-token rates, free-vs-paid data terms): https://ai.google.dev/gemini-api/docs/pricing
- Gemini subscriptions overview (AI Pro / Ultra): https://gemini.google/subscriptions/
- Third-party pricing breakdowns (cross-check, Jun 2026): https://www.finout.io/blog/gemini-pricing-in-2026 · https://developer.puter.com/tutorials/gemini-api-pricing/
- Internal: `core/ai_infra/gemini_client.py` · `core/ai_infra/gemini_file_reader.py` · `core/multi_model/multi_model_orchestrator.py` · `OpsCenter/opencode_zen_counter.py` · `hale_state.json` (MISSION-127, brain_routing_log) · `OpsCenter/usage_ledger.json` · `core/ai_infra/data/gemini_usage.jsonl` · `OpsCenter/security/SECURITY_AUDIT_2026-06-15.md` (H5/H10 key hygiene)

---

*Prepared by Hale, COS — Thunderbird Wing, Dreams2Memories Travel, LLC · 2026-06-15*
*No financial commitment authorized by this paper. Billing-enable + secrets-manager move are Commander-gated steps.*
*— V. Hale, VCS*
