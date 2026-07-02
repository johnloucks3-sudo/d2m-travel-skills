# Sector H — Voice AI | 2026-07-02
**Scanned by:** ELON (A12) | **Posture:** Adopt-first

---

## Top 3 Findings

1. **Deepgram Nova-3 / Flux — real-time STT at $0.0048/min is table stakes now.** Speech-to-text is no longer expensive or difficult. Deepgram's Flux model (launched April 29, 2026) is the first conversational STT with integrated end-of-turn detection — built for voice agents, ~100ms latency. $200 free credit on signup. The barrier to building "Commander speaks, Wing executes" is engineering hours, not cost.

2. **Voice-to-Wing is a one-weekend build.** The architecture exists: Commander speaks → Deepgram/Whisper transcribes → Claude processes intent → Thunderbird MCP executes. No vendor dependency required. We own every layer except the STT API. Leaping AI and Neural Voice are doing exactly this for enterprise travel call centers — we can build the same loop in-house for $0.29/hour of audio.

3. **AI voice for inbound client calls is a real product.** Narvika (EU), Neural Voice (UK), and Leaping AI (US) are deploying AI voicebots for travel agency hotlines — auto-transcribe, summarize, sentiment-tag every call, then hand off to a human with a full brief. These run $200-800/month for small agencies. The inbound call problem at D2M is currently zero — we don't have a call center. But the outbound use case (voice memo → draft client email) is immediate and costs almost nothing.

---

## Adoption Recommendations

| Tool/Move | Priority | Rationale | Estimated effort |
|---|---|---|---|
| **Deepgram Nova-3 API** — Commander voice memos → Wing task intake | P0 | $200 free credit, $0.29/hr after. Commander records a voice note, it lands in claude_inbox.md as text. Eliminates the typing bottleneck entirely. | 1 day — Python wrapper + Telegram bot hook |
| **Whisper (local, openai-whisper)** — local fallback, zero API cost | P1 | Free, runs on YOGA. Slower (not real-time) but zero ongoing cost. Use for batch: "transcribe today's notes." | 2 hours — pip install, script wrapper |
| **Voice memo → dossier update pipeline** | P1 | Commander speaks client update on phone → transcribed → appended to dossier. Eliminates the "I need to update the Kuklinski file" manual step entirely. | 1 day |
| **Watch Neural Voice / Retell AI** for inbound client call AI | WATCH | Not needed now (no call center volume) but relevant if D2M scales. Retell AI runs $0.05-0.07/min per call with full CRM integration hooks. | 0 — monitor quarterly |

---

## Kill Audit — What to Replace

| Current approach | Candidate replacement | Confidence |
|---|---|---|
| Commander types tasks into Claude Code / Telegram | Voice memo → Deepgram → claude_inbox.md | HIGH — straightforward pipe |
| Manual dossier updates (typing) | Voice note → transcribe → append to dossier | HIGH — same pipe, different destination |
| No client call logging | Not applicable yet (no call volume) | N/A |
| No transcription in stack | Deepgram (real-time) or local Whisper (batch) | HIGH |

**Current stack has ZERO voice/transcription tooling.** This is a pure greenfield adoption — no replacement friction.

---

## Watch List (not adopt yet)

- **ElevenLabs voice cloning** — synthetic voice for outbound calls to clients. Technically impressive. Ethically complex. D2M's differentiator is the human relationship. Putting a synthetic voice on client calls could destroy that. Watch, do not adopt without Commander directive.
- **Twilio Voice + AI** — full outbound dialing with AI script. Enterprise price. Not the right scale for D2M yet.
- **Retell AI / Bland AI** — inbound call center automation. Relevant when D2M has volume. Currently overkill.
- **Cruise line AI voice programs** — Regent, Silversea, Viking have NO publicly announced AI voice deployments as of July 2026. This is a market gap, not a threat.

---

## ZEN Counter-Voice

The "Commander speaks, Wing executes" vision is seductive but the failure mode is worth naming: voice-to-action loops create accidental execution. Commander says something half-formed in a phone call, it gets transcribed and executed as a Wing directive. The transcription layer has to be staging-only — nothing goes to execution without Commander confirming the transcript first. Build the pipe with a mandatory confirmation gate before any action fires. Also: Deepgram is a third-party API receiving audio that may contain client names and booking details — that's PII on a vendor pipe. Use local Whisper for any transcription that touches client information. Deepgram for Commander task intake only (no client data in that channel).

---

*Sources: [Deepgram Pricing](https://deepgram.com/pricing) · [Deepgram Flux model](https://deepgram.com/learn/best-speech-to-text-apis-2026) · [Leaping AI travel](https://leapingai.com/industries/voice-ai-travel-companies) · [Neural Voice travel](https://www.neural-voice.ai/travel) · [Narvika voicebot](https://www.narvika.com/en/ai-voicebot-travel-agency) · [Retell AI](https://www.retellai.com/blog/best-ai-voice-agent-services-businesses) · [STT benchmark 2026](https://futureagi.com/blog/speech-to-text-apis-in-2026-benchmarks-pricing-developer-s-decision-guide/)*
