# Competitive AI Model Intelligence — March 10, 2026
## 12 Models Evaluated for Thunderbird OS

---

### Executive Summary

Claude remains the best choice for Thunderbird OS's core orchestration, creative output, and MCP-powered agentic workflows. But the cost gap has widened dramatically — competitors now offer comparable tool-use capabilities at 1/10th to 1/25th the price. The strategic play: **cheap models for volume, Claude for judgment.**

---

## The Landscape: 12 Models Ranked by Thunderbird Relevance

### TIER 1 — Immediate Action

**1. Meta Llama 4 Scout (109B MoE, 17B active) — UPGRADE NOW**
- **Price:** $0.11/1M input, $0.34/1M output on Groq
- **Context:** 10 MILLION tokens — industry-leading
- **Why it matters:** Drop-in replacement for our Llama 3.3-70B on Groq. Same provider, same infrastructure. The 10M context window means we could feed an entire client's booking history, all dossiers, and all correspondence into a single prompt. Available on Groq now, likely on free tier.
- **Weakness:** No native MCP support.

**2. Google Gemini 2.5 Flash — EVALUATE**
- **Price:** $0.30/1M input, $2.50/1M output
- **Context:** 1M tokens
- **Why it matters:** Native Google Workspace integration aligns perfectly with our Sheets/Drive/Gmail pipeline. Free tier on Google AI Studio. Could replace or supplement Groq for tasks that touch Google APIs.
- **MCP support:** Confirmed.

**3. xAI Grok 4.1 Fast — EVALUATE**
- **Price:** $0.20/1M input, $0.50/1M output
- **Context:** 2M tokens
- **Why it matters:** Built-in web search eliminates separate tool calls. Ideal for A2 (Wraith) research and market intelligence. Agent Tools API could automate destination research workflows.
- **Weakness:** Smaller ecosystem, less mature dev tooling.

---

### TIER 2 — Monitor Closely

**4. Google Gemini 3.1 Pro (Preview)**
- **Price:** $2/1M input, $12/1M output
- **Context:** 1M tokens
- **Why it matters:** MCP Atlas score of 69.2% — best tool coordination of any model. ARC-AGI-2 score of 77.1% (12% ahead of Opus 4.6). Still in preview — evaluate when GA.
- **MCP support:** Confirmed by Demis Hassabis.

**5. OpenAI GPT-5.4**
- **Price:** $2.50/1M input, $15/1M output
- **Context:** 1M tokens
- **Why it matters:** Native computer use, tool search for dynamic tool discovery, massive ecosystem. ChatGPT desktop supports MCP.
- **Weakness:** Expensive at Pro tier ($30/$180). Less consistent persona voice fidelity.

**6. Meta Llama 4 Maverick (400B MoE)**
- **Price:** $0.50/1M input, $0.77/1M output
- **Context:** Varies by provider
- **Why it matters:** Premium open-source reasoning at fraction of Claude cost. Matches/exceeds GPT-5.3 on code generation. Behemoth (2T params) coming.

---

### TIER 3 — Niche / Watch

**7. DeepSeek V3.2 / R1 (V4 imminent)**
- **Price:** $0.14/1M input, $0.28/1M output (cheapest frontier model)
- **Context:** 164K (V3), 64K (R1), expected 1M (V4)
- **Why it matters:** Unbeatable price for OCR parsing and booking data structuring.
- **CAUTION:** Chinese company — data sovereignty risk. Use for non-PII extraction ONLY.

**8. Mistral Large 3**
- **Price:** $0.50/1M input, $1.50/1M output
- **Context:** 262K tokens
- **Why it matters:** EU-based (GDPR-friendly), strong multilingual, 75% price drop from previous version.

**9. Alibaba Qwen 3.5**
- **Price:** $0.10/1M input, $0.15/1M output
- **Context:** Up to 1M tokens, runs on consumer GPUs
- **Why it matters:** 119 languages, MCP support confirmed, self-hosting eliminates API costs entirely.
- **CAUTION:** Chinese company — same data sovereignty concern.

---

### TIER 4 — Skip for Thunderbird

**10. Cohere Command A** — $2.50/$10, enterprise-focused, no advantage for small travel agency
**11. Amazon Nova 2 Pro** — $0.30/$10, Bedrock lock-in not justified unless on AWS
**12. Microsoft Phi-4** — $0.06/$0.14, too small (14B params) for our use cases
**Bonus: GLM-5 (Zhipu AI)** — Strong reasoning but Chinese-only ecosystem, limited production tooling

---

## MCP Has Gone Industry-Standard

| Platform | MCP Status |
|----------|-----------|
| Claude (Anthropic) | Originator — deepest support |
| OpenAI / ChatGPT | Confirmed (desktop + API) |
| Google Gemini | Confirmed — leads MCP Atlas benchmark |
| Microsoft Copilot | First-class MCP client |
| Amazon Nova 2 | Remote MCP support |
| Qwen (Alibaba) | Confirmed |
| Cursor, Replit, VS Code | Full client support |

**97 million** monthly SDK downloads. **10,000+** active MCP servers. Our 97-tool D2M MCP server is now compatible with most major platforms, not just Claude.

---

## Travel Industry Is Moving Fast

- **Sabre + PayPal + MindTrip** — first end-to-end agentic AI booking system (Q2 2026 launch)
- **Booking.com** — agentic AI customer-facing tools
- **Google** — preparing agentic booking tools
- **McKinsey:** AI travel startup funding spiked from 10% to 45% since 2023
- **IDC:** "Agentic AI will redefine travel and hospitality in 2026"
- **Key insight:** If your data is incomplete or fragmented, AI agents will skip you entirely. Structured, accessible data is now critical infrastructure.

**Thunderbird OS already has structured data** — Booking Master, dossier pipeline, MCP tools, Google Workspace integration. We're ahead of the curve.

---

## Recommended Architecture Evolution

| Layer | Current | Recommended | Cost Impact |
|-------|---------|-------------|-------------|
| Routine persona ops | Groq Llama 3.3-70B (free) | Groq Llama 4 Scout (free/cheap) | Neutral |
| Research & intel | Claude + web search | Grok 4.1 Fast ($0.20/1M) | -90% |
| Google Workspace ops | Claude via MCP | Gemini 2.5 Flash ($0.30/1M) | -90% |
| Creative/strategy/escalation | Claude Sonnet 4 | Claude Sonnet 4.6 (**DONE**) | Neutral |
| Bulk extraction (non-PII) | Groq | DeepSeek V3 ($0.14/1M) | -95% |

---

## Bottom Line

Our Groq + Claude architecture is **directionally correct**. The upgrade path is clear:
1. **Swap Llama 3.3 → Llama 4 Scout** on Groq (immediate, free)
2. **Add Gemini 2.5 Flash** for Google Workspace tasks (evaluate this week)
3. **Add Grok 4.1 Fast** for research with built-in web search (evaluate next week)
4. **Keep Claude Sonnet 4.6** as the judgment/creative/MCP escalation engine
5. **Watch Gemini 3.1 Pro** — could become Claude alternative for tool coordination

Claude is still the best brain. But it doesn't need to do every job. Let the cheap models handle volume. Reserve Claude for when quality and voice matter.

---

*Competitive intelligence gathered and synthesized by Thunderbird OS — March 10, 2026*
*12 models evaluated across pricing, capabilities, MCP support, and travel industry relevance*
