# Sector D — Agentic Apps · Incubator Research
*ELON (A12 — Technology Vanguard) · W7 · 2026-07-02*

## Bottom Line Up Front
Multi-agent orchestration consolidated in 2026 to ~4 mature frameworks. Thunderbird's architecture (Claude Code + subagents + headless dispatch) is already a de-facto orchestration layer — the gap is not a framework, it's making our **email AI loop** hybrid (deterministic + judgment escalation) and getting **cc-fleet** to route non-critical agent work to cheap/free models. Both are adopt-now candidates that map directly to open missions (MISSION-814, email-effort diagnosis 2026-07-01).

---

## 1. Framework Landscape (mid-2026)

The 2024–25 proliferation consolidated. Four survivors, each with a clear niche:

| Framework | Owner | Architecture | Best for | Model-agnostic |
|---|---|---|---|---|
| **LangGraph** | LangChain | Directed graph, conditional edges, built-in checkpointing + time-travel state | Enterprise production at scale (largest footprint) | Yes |
| **CrewAI** | CrewAI | Role-based "crews" w/ process types; ~20-line DSL, lowest learning curve | Rapid prototyping / demos (weak on prod observability) | Yes |
| **AutoGen** | Microsoft | Conversational GroupChat; mature debate/verification patterns | Research / academic | Yes |
| **OpenAI Agents SDK** (ex-Swarm) | OpenAI | Explicit handoffs | Narrow handoff flows | **No — OpenAI only** |

**So-what for Thunderbird:** We are not going to rip out Claude Code to adopt a Python framework. Our subagent + `Agent` tool + headless-dispatch stack *is* our orchestration layer, and it's Claude-native (right where our token discipline and personas live). The frameworks matter as **pattern sources**, not adoptions:
- **LangGraph's checkpointing / time-travel** → validates our OODA "checkpoint every cycle" + hale_bus state handoff design. We already do this; the pattern is industry-standard now.
- **AutoGen's debate/verification** → this is exactly our ZEN counter-voice + Sterling red-team. Confirmed sound.
- **CrewAI's role DSL** → our persona roster (Hale/Dani/Sterling/Dembe/Harlan) is the same idea, richer.

*Confidence: HIGH. Consistent across 7 comparison sources.*

## 2. Email-Based AI Agent Patterns (connects to our email AI loop)

The 2026 email-agent market split into 5 segments; the one that matters to us is **agentic infrastructure that acts on email autonomously**. The consensus winning pattern:

> **Hybrid is the 2026 playbook: deterministic automation handles predictable events; AI agents handle judgment-heavy exceptions; uncertain decisions hand back to a human with full context + confidence score + *why it escalated*.**

Core mechanics observed across platforms (Fini, Fin/Intercom, Freddy AI, Nylas, Robylon):
- Read body + subject + **sender history**, classify to intent with a **confidence score**, apply one/more labels.
- **High-confidence → route autonomously. Low-confidence → pause for human**, with an explainability panel ("here's why").
- Relationship/reply-pattern graphs to surface what matters and deprioritize the rest.

**So-what — this is a direct hit on our open wound.** Our email-effort diagnosis (memory 2026-07-01) found three stacked faults: LLM-per-email fragility, a classify gate that tagged ALL inbound as `client_inquiry` (326 junk missions), and an executor that auto-drafted junk. The 2026 industry pattern is the fix:
1. **Rules-first / deterministic tier** for predictable mail (we already shipped this — commit `1eb2b7e93` "zero-model rules-first classifier"). Keep it as tier 1.
2. **Confidence-scored classification** — never a flat `client_inquiry` default (the exact bug in commit `27801906e`). Anything below threshold → do NOT auto-draft; surface to Hale/Commander with reasoning.
3. **Sender-history / relationship signal** — Kim Westbrook (crnakim@yahoo, active pro-bono) got buried because we had no relationship weighting. A relationship graph would have floated her to the top.
4. **Human-in-loop = the WF-17 gate** we already have. The industry pattern *validates* our client-send prohibition — we just need the confidence tier feeding it.

## 3. CC-Fleet (cc-fleet npm package) — What it is, does it work?

**What:** `@ethanhq/cc-fleet` (repo `ethanhq/cc-fleet`) runs Claude Code's Dynamic Workflows, Agent Teams, and Subagents **on any third-party model** — DeepSeek, GLM, Kimi, Qwen, Groq, Together, Fireworks, local vLLM, OpenAI, or a Codex subscription — with **no Anthropic subscription required for the workers**. Every third-party worker is a real `claude` process with its LLM backend swapped, so Claude Code drives it like a native agent.

**How it works (from README, verified):**
- Drives the official `claude` CLI. Install script adds `ccf` CLI + a Claude Code plugin (skill + session hook) via marketplace. `ccf doctor` = health check for deps/providers/plugin.
- **Broad compatibility**: any Anthropic- *or* OpenAI-compatible endpoint. Vendors ship as presets (endpoint + protocol auto-filled); "Custom" for anything else.
- **Model tiers per provider**: default / strong / fast slots, each taggable with 1M-context + reasoning effort. Claude just asks for "the strong model" — no hardcoded IDs.
- **Multi-key rotation** per provider.
- **Security**: main session's own auth untouched; provider keys never enter env, argv, or shell history.

**Does it work? — YES, and it directly addresses MISSION-814.** Our mission board has MISSION-814 (P0) *stuck* precisely on this: "cc-fleet 0.2.9 installed + plugin active; Groq/Cerebras providers registered but rejecting model requests." The README's `ccf doctor` health check + preset-vs-custom endpoint model is the diagnostic path. The rejection is almost certainly a **model-ID / endpoint-protocol mismatch or a bad free-tier key**, not a cc-fleet defect — the tool explicitly supports Groq via OpenAI-compatible endpoint. This is a config fix, not a tool kill.

*Confidence: HIGH on what/how (primary-source README). MEDIUM on root cause of our Groq/Cerebras rejection — needs `ccf doctor` run to confirm.*

---

## Sources
- [Presenc AI — Multi-Agent Orchestration Frameworks 2026](https://presenc.ai/research/multi-agent-orchestration-frameworks-2026)
- [Turing — Top 6 AI Agent Frameworks 2026](https://www.turing.com/resources/ai-agent-frameworks)
- [cc-fleet — GitHub (ethanhq/cc-fleet) README](https://github.com/ethanhq/cc-fleet/blob/main/README.md)
- [Fini Labs — 9 AI Email Triage Platforms 2026](https://www.usefini.com/guides/ai-email-triage-gmail-billing-technical-cancellation-categories)
- [Windows News — 2026 AI Email Assistant Guide (Agentic Mail)](https://windowsnews.ai/article/2026-ai-email-assistant-guide-5-segments-privacy-and-agentic-mail.425662)
- [Nylas — Build an AI Email Triage Agent](https://cli.nylas.com/guides/build-ai-email-triage-agent)
