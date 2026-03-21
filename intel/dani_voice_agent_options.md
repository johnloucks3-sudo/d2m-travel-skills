# DANI VOICE AGENT — PLATFORM OPTIONS ASSESSMENT
## Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
## Dreams2Memories Travel, LLC
### Date: 2026-03-20 | Classification: INTERNAL

---

## ISSUE

Select a voice AI platform to put Dani — our luxury travel concierge persona — on the D2M business phone line, providing 24/7 warm, operationally crisp voice answering backed by the existing Thunderbird Dani Engine (`thunderbird_dani_engine.py`) and REST API (`api.d2mluxury.quest`).

---

## DISCUSSION

### Requirements Matrix

| Requirement | Weight | Notes |
|---|---|---|
| Voice quality & warmth | CRITICAL | Luxury brand — callers must feel welcomed, not routed to a robot |
| Backend integration | CRITICAL | Must call Thunderbird REST API for booking data, dossier lookups, client context |
| Latency (sub-1s response) | HIGH | Awkward pauses destroy the luxury illusion |
| Phone number integration | HIGH | Twilio or Google Voice forwarding to AI agent |
| Custom persona/prompt | HIGH | Dani's voice rules, tone, relationship awareness must be injectable |
| Custom voice training | MODERATE | Ideal: a consistent "Dani voice" across every call |
| Cost predictability | MODERATE | Low call volume initially (5-20 calls/day projected) |
| n8n/webhook compatibility | NICE | We already run 16 n8n workflows; native integration is a bonus |

### Current Architecture

The Dani Engine already generates text responses with full context awareness — client detection, specialist routing (A2/A5/A9/COS), dossier lookup, booking data from Google Sheets, and COS review gating. The voice platform needs to serve as a **frontend only**: capture speech, send text to our backend, receive Dani's text response, convert to speech, deliver to caller. The intelligence stays in Thunderbird.

Two integration patterns are viable:

1. **Custom LLM / Webhook Pattern** — Platform calls our API for every response. We control the brain. Platform handles voice I/O only.
2. **Platform-Native LLM + Knowledge Base** — Platform runs its own LLM with our system prompt and knowledge base docs. Less control, simpler setup, but Dani's intelligence is duplicated/degraded.

**Assessment: Pattern 1 is strongly preferred.** We have 120+ MCP tools, live booking data, client dossiers, and a voice ledger. No knowledge base upload can replicate that. The platform must support custom LLM or webhook-based response generation.

---

## OPTIONS

### OPTION 1: RETELL AI (RECOMMENDED)

**Confidence: HIGH** — Most thoroughly documented, strongest integration story for our architecture.

#### Pricing
| Component | Cost |
|---|---|
| Base platform | $0 (pay-as-you-go, no monthly fee) |
| Voice engine (ElevenLabs Flash v2.5) | $0.07-0.08/min |
| Twilio telephony pass-through | $0.015/min |
| LLM agent (Custom LLM mode) | $0.00/min (we provide our own) |
| **Total estimated per minute** | **$0.085-0.095/min** |
| Free credits at signup | $10 |
| Concurrent calls included | 20 free, then $8/seat/mo |

At 20 calls/day averaging 4 minutes each: ~$5-6/day, ~$150-180/month.

Enterprise tier available at $8,000/year for volume discounts (base drops to $0.05/min). Not needed at our scale.

#### Integration Architecture (Custom LLM Mode)

This is the key differentiator. Retell supports a **Custom LLM WebSocket** where:

1. Caller dials Twilio number
2. Twilio routes to Retell via SIP trunk or Elastic SIP
3. Retell transcribes speech to text in real-time
4. Retell opens WebSocket to our backend server
5. Our server receives transcript, calls Dani Engine, returns response text
6. Retell converts response to speech, delivers to caller

We would build a lightweight WebSocket handler (Python/FastAPI) that:
- Receives Retell's live transcript stream
- Calls `thunderbird_dani_engine.py` functions for response generation
- Returns Dani's text response via the same WebSocket
- Retell handles TTS with the selected voice

Retell provides Python and Node.js demo repos for Custom LLM integration: [retell-custom-llm-python-demo](https://github.com/RetellAI/retell-custom-llm-python-demo).

#### n8n Integration
Native. Retell sends webhooks to n8n on `call_started`, `call_ended`, and `call_analyzed` events. Custom Functions during calls can trigger n8n workflows — e.g., "let me check your booking" triggers a webhook to n8n, which calls our API, and returns data to the voice agent mid-call. This maps directly to our existing n8n infrastructure (16 workflows in `deploy/n8n/`).

#### Voice Options
- 100+ community voices
- ElevenLabs Flash v2.5 (multilingual), PlayHT, Cartesia Sonic-3
- **Custom voice cloning** via API (`clone-voice` endpoint) — upload audio samples
- Emotion control: Happy, Surprised, Sympathetic, Calm
- Fallback voice configuration (if primary provider has an outage)

#### Latency
~600-800ms reported. Industry-leading for the price tier. Adequate for natural conversation.

#### Phone Number Setup
- Import existing Twilio number via Elastic SIP Trunking (recommended)
- Or use Retell's built-in number provisioning
- Google Voice: would need to forward to a Twilio number first, then SIP trunk to Retell
- IP whitelist: 18.98.16.120/30, 143.223.88.0/21, 161.115.160.0/19

#### Gaps Identified
- Voice cloning quality reports are mixed — some reviews say it's limited. Would need to test with Dani voice samples.
- No HIPAA compliance mentioned (not relevant for us, but noted).
- Community forum suggests some users hit issues with native Twilio inbound (SIP only visible, not traditional Twilio webhook).

---

### OPTION 2: OPENAI REALTIME API (SIP)

**Confidence: HIGH on capability, MODERATE on cost predictability.**

#### Pricing
| Component | Cost |
|---|---|
| Audio input (gpt-realtime) | $0.06/min (~$32/1M tokens) |
| Audio output (gpt-realtime) | $0.24/min (~$64/1M tokens) |
| Cached audio input | $0.004/min (~$0.40/1M tokens) |
| Text input (system prompt) | $5/1M tokens |
| Text output | $20/1M tokens |
| **Total estimated per minute** | **$0.30-0.50/min** |
| Twilio telephony (separate) | ~$0.015/min + number fee |

At 20 calls/day averaging 4 minutes: ~$24-40/day, ~$720-1,200/month.

A gpt-realtime-mini model exists at lower token prices but details on per-minute equivalents are less documented. Rough estimate: 40-60% cheaper than full model.

**Cost is 3-5x higher than Retell** at equivalent usage. Token-based billing makes costs variable and harder to predict. The system prompt itself consumes tokens on every call.

#### Integration Architecture

Two approaches:

**A. SIP Connector (Simpler)**
1. Configure webhook in OpenAI Console for `realtime.call.incoming`
2. Set up Twilio Elastic SIP Trunk pointing to `sip:$PROJECT_ID@sip.api.openai.com;transport=tls`
3. When call arrives, OpenAI hits your webhook; you respond with instructions (system prompt, voice, tools)
4. OpenAI's model handles the conversation directly
5. Function calls (tools) execute on your server via "sideband" WebSocket connection

**B. WebSocket + Twilio Media Streams (More Control)**
1. Twilio webhook hits your server
2. Your server opens WebSocket to OpenAI Realtime API
3. Audio streams bidirectionally
4. You inject system prompt and handle function calls server-side

**Key limitation: OpenAI IS the LLM.** You cannot swap in your own model. You inject Dani's persona via system prompt and define tools that call your API, but the response generation is OpenAI's, not our Dani Engine. This means:
- Dani's voice ledger rules, specialist routing, and COS review gating would need to be replicated as tool definitions and system prompt instructions
- Response quality depends on how well the system prompt captures Dani's behavior
- No guarantee of consistency with the text-based Dani responses clients already receive via Telegram

#### Voice Options
Seven voices: Ash, Ballad, Coral, Sage, Verse, Cedar, Marin. All are OpenAI-native. **No custom voice cloning.** You pick from the list. The voices are reportedly very natural and expressive, with emotion/accent tuning via prompt.

#### Latency
Sub-1-second. Speech-to-speech (S2S) architecture eliminates the STT-to-LLM-to-TTS pipeline. This is the lowest latency option.

#### Function Calling
Supports function calling / tool use during conversation. Your server handles tool execution via sideband WebSocket. This is how you'd connect to Thunderbird API — define tools like `lookup_booking`, `check_itinerary`, `get_client_info` that call `api.d2mluxury.quest`.

#### Gaps Identified
- **No custom voice.** Seven preset voices only. Cannot create a "Dani" voice.
- **Cost unpredictability.** System prompt token consumption on every call adds up. A rich Dani persona prompt could cost $0.02-0.05 per call just for the prompt.
- **LLM lock-in.** Cannot use our Dani Engine as the brain — must rely on OpenAI's model with prompt engineering.
- **Reliability concerns.** OpenAI community reports some SIP reliability issues (dropped calls, connection instability).
- **No native n8n integration.** Would require custom webhook plumbing.

---

### OPTION 3: ELEVENLABS CONVERSATIONAL AI

**Confidence: MODERATE** — Strong voice quality, weaker on custom backend integration.

#### Pricing
| Component | Cost |
|---|---|
| Plan required | Scale ($330/mo) or Business ($1,320/mo) |
| Per-minute call cost (Scale) | $0.10/min |
| Per-minute call cost (Business, annual) | $0.08/min |
| LLM costs | Currently absorbed by ElevenLabs, will be passed through eventually |
| Silence discount | 95% off for silence >10 seconds |
| Setup/test calls | 50% discount |
| **Total estimated per minute** | **$0.08-0.10/min + plan fee** |

At 20 calls/day averaging 4 minutes on Business plan: ~$6.40-8/day in per-minute + $1,320/mo plan = ~$1,500-1,560/month.

**Significantly more expensive than Retell** due to the mandatory plan subscription.

#### Integration Architecture

ElevenLabs agents can use:
1. **Built-in LLM** with custom system prompt and knowledge base (RAG)
2. **Custom LLM** integration (less documented than Retell's)
3. **Webhook actions** for mid-call API calls

The knowledge base feature supports document uploads and RAG, but this is the "Pattern 2" approach — duplicating Dani's intelligence rather than calling our backend. Custom LLM integration documentation is thinner than Retell's.

#### Voice Quality & Cloning
This is ElevenLabs' crown jewel.

- **Instant Voice Cloning:** Upload a short sample, get a clone in minutes. Quality is good but not perfect.
- **Professional Voice Cloning:** Upload 30 min to 3 hours of audio. Results are exceptional — nearly indistinguishable from the real voice. Requires Creator plan ($11/mo) or higher.
- Emotion control, pacing adjustment, accent tuning
- 29+ languages supported natively

**If we want a custom "Dani" voice that sounds like a specific person, ElevenLabs is the gold standard.** No other platform matches their cloning quality.

#### Phone Integration
- Native Twilio integration (paste Account SID + Auth Token, auto-configures webhooks)
- SIP trunking support (Twilio, Vonage, Telnyx, RingCentral, Plivo, others)
- Built-in DTMF, voicemail detection, automatic language detection
- Google Voice: forward to Twilio number, then native integration to ElevenLabs

#### Latency
Not explicitly benchmarked in their docs. Industry estimates suggest 800ms-1.2s depending on LLM backend. Slightly slower than Retell or OpenAI Realtime.

#### Gaps Identified
- **Mandatory monthly plan** even at low volume. $330-1,320/mo before any calls.
- **Custom LLM integration less mature** than Retell. Documentation is thinner.
- **LLM costs "currently absorbed"** — this is a ticking time bomb. When they pass through LLM costs, per-minute pricing could jump significantly.
- **Primarily a voice/TTS company** adding agent capabilities, vs. Retell/Bland which are agent-first.

---

### OPTION 4: BLAND AI

**Confidence: MODERATE** — Phone-first platform, but latency concerns and enterprise pricing model.

#### Pricing
| Component | Cost |
|---|---|
| Build plan (minimum viable) | $299/mo |
| Scale plan | $499/mo |
| Per-minute voice calls | $0.09/min (billed per second) |
| Minimum charge per call | $0.015 |
| SMS | $0.02/message |
| Voice cloning | Included (5 clones on Build, 15 on Scale) |
| **Total estimated per minute** | **$0.09/min + plan fee** |

At 20 calls/day averaging 4 minutes on Build plan: ~$7.20/day in per-minute + $299/mo = ~$515/month.

#### Integration Architecture

Bland is API-first:
1. Configure agent via API with system prompt, voice, and tools
2. Define webhooks for external API calls during conversation
3. Agent makes/receives calls via Bland's infrastructure
4. Post-call webhook delivers transcript and analysis

Bland supports custom pathways (conversation flow design), memory stores, and webhook-triggered actions during calls. Travel/hospitality is an explicitly supported vertical — they demo airline bag-tracking as a use case.

**However:** Like OpenAI, Bland runs its own LLM. You inject a system prompt and define tools, but you cannot swap in the Dani Engine as the response generator. Custom LLM integration (bring-your-own-brain) is not a documented capability.

#### Voice Options
- Voice library selection
- Voice cloning from short MP3 samples (5-15 clones depending on plan)
- Dynamic emotion/style control via markers ("excited", "calm")

#### Latency
**This is the concern.** Bland claims <2 seconds, but third-party reviews consistently report:
- Average: ~800ms
- Worst case: 2.5 seconds
- Creates awkward pauses in dynamic conversation

For a luxury concierge, 2.5-second pauses are unacceptable. This is a deal-breaker risk.

#### Capacity
- Build: 2,000 daily calls, 50 concurrent (far exceeds our needs)
- Scale: 5,000 daily, 100 concurrent
- Enterprise: 20,000/hour

#### Phone Integration
- Bland provides phone numbers directly
- Bring-your-own via SIP trunk or forwarding
- Google Voice: forward to Bland number

#### Gaps Identified
- **Latency is the critical weakness.** 800ms average with 2.5s spikes is not luxury-grade.
- **No custom LLM mode.** Cannot plug in our Dani Engine directly.
- **Mandatory monthly plan** ($299-499) even at low volume.
- **Enterprise-focused.** Built for 20,000 calls/hour, not 20 calls/day. We're paying for infrastructure we don't need.
- **SOC 2/HIPAA/GDPR compliance** — nice, but adds cost we're not leveraging.

---

## COMPARATIVE MATRIX

| Factor | Retell AI | OpenAI Realtime | ElevenLabs | Bland AI |
|---|---|---|---|---|
| **Est. Monthly Cost (80 calls/day, 4 min avg)** | $150-180 | $720-1,200 | $1,500-1,560 | $515 |
| **Custom LLM / Backend** | YES (WebSocket) | NO (tools only) | Partial | NO (tools only) |
| **Voice Cloning** | Yes (API) | No | Best in class | Yes (limited) |
| **Latency** | 600-800ms | <500ms (best) | 800-1,200ms | 800-2,500ms (worst) |
| **Twilio/SIP** | Native | Native (SIP) | Native | SIP/forwarding |
| **n8n Integration** | Native | None | None | Zapier/webhook |
| **Monthly Minimum** | $0 | $0 | $330 | $299 |
| **Voice Quality** | Good (multi-provider) | Excellent | Excellent (best) | Good |
| **Dani Engine Integration** | Full (Custom LLM) | Partial (tools) | Partial | Partial (tools) |
| **Setup Complexity** | Moderate | High | Moderate | Low |

---

## RECOMMENDED ARCHITECTURE (Retell AI + Thunderbird)

```
Caller → Twilio Number → SIP Trunk → Retell AI
                                         ↓
                                    [Speech-to-Text]
                                         ↓
                              [WebSocket to our server]
                                         ↓
                          thunderbird_voice_ws.py (new)
                                         ↓
                          thunderbird_dani_engine.py
                              ↓              ↓
                    [Booking Data]    [Client Dossiers]
                    [Google Sheets]   [Voice Ledger]
                              ↓
                    [Dani's text response]
                              ↓
                         [Back to Retell]
                              ↓
                         [Text-to-Speech]
                              ↓
                         Caller hears Dani
```

New components needed:
1. `thunderbird_voice_ws.py` — WebSocket handler (~200 lines, based on Retell's Python demo)
2. Twilio account + phone number ($1/mo + usage)
3. SIP trunk configuration (Retell docs cover this)
4. Voice selection/cloning in Retell dashboard
5. Systemd service for the WebSocket server on YOGA

Estimated build time: 2-3 days for MVP, 1 week for production-grade with error handling, call logging, and COS notification.

---

## ACTIONS I RECOMMEND TAKING

1. **Select Retell AI** as the voice platform. It is the only option that supports full Custom LLM integration (our Dani Engine as the brain), has no monthly minimum, and costs ~$150-180/mo at projected volume. High confidence this is the right call.

2. **Provision a Twilio phone number** for D2M. Cost: $1/month + $0.015/min usage. This becomes the business line that Dani answers. Google Voice can forward to this number if we want to keep the existing GV number as the public-facing number.

3. **Do NOT use the Google Voice number directly.** GV does not support SIP trunking. Forward GV to the Twilio number, or publish the Twilio number as the new D2M line.

4. **Build `thunderbird_voice_ws.py`** — a WebSocket handler based on Retell's [Python demo](https://github.com/RetellAI/retell-custom-llm-python-demo). This server receives Retell's transcript stream, calls the Dani Engine, and returns text responses. Deploy on YOGA alongside the existing REST API.

5. **Start with a stock Retell voice** (warm, female, American English). Test for 2 weeks. If the Commander wants a custom "Dani" voice, we can either:
   - Clone a voice via Retell's API (moderate quality, fast), or
   - Use ElevenLabs Professional Voice Cloning (excellent quality, requires 30+ min audio samples) and configure Retell to use the ElevenLabs voice engine (Retell supports ElevenLabs as a voice provider).

6. **Add n8n workflow** for post-call processing: transcript logging, COS notification via Telegram, dossier updates from call content.

7. **Phase 2 consideration:** If voice quality becomes the top priority and we're willing to pay the premium, ElevenLabs Conversational AI with Professional Voice Cloning would deliver the most "luxury" caller experience. But at $1,500+/mo vs. $150/mo, this is a 10x cost increase for incremental voice quality. Retell can use ElevenLabs voices anyway, giving us 80% of the benefit at 10% of the cost.

8. **Do NOT pursue Bland AI.** The latency profile (up to 2.5s) is incompatible with luxury concierge expectations, and the $299/mo minimum is unjustified for our volume.

9. **Do NOT pursue OpenAI Realtime API as primary.** Cost is 4-6x Retell, no custom voice, and no ability to use our Dani Engine as the brain. The sub-500ms latency is appealing but not worth the trade-offs. If OpenAI adds custom LLM support or drops pricing significantly, reassess.

---

## INFORMATION GAPS

| Gap | Impact | Mitigation |
|---|---|---|
| Retell voice cloning quality for a specific "Dani" voice | MODERATE — affects brand consistency | Test with sample audio; fall back to ElevenLabs provider within Retell |
| Actual latency under load on YOGA→Retell→Twilio chain | MODERATE — could add 200-400ms from our backend | Load test during build phase; YOGA is local, low-latency to US endpoints |
| Google Voice → Twilio forwarding reliability | LOW — GV forwarding is well-established | Test before publishing the number |
| Retell's stability/uptime SLA | MODERATE — no public SLA on free tier | Monitor; escalate to paid tier if issues arise |
| Long-term ElevenLabs cost pass-through for LLM | LOW for us (we use Custom LLM) | Only affects us if we use ElevenLabs Conversational AI directly |

---

## SOURCES

- [Retell AI Pricing](https://www.retellai.com/pricing)
- [Retell AI Custom LLM Docs](https://docs.retellai.com/integrate-llm/overview)
- [Retell AI Custom Telephony](https://docs.retellai.com/deploy/custom-telephony)
- [Retell AI Voice Options](https://docs.retellai.com/build/voice)
- [Retell AI + n8n Custom Functions](https://n8n.io/workflows/3805-connect-retell-voice-agents-to-custom-functions/)
- [Retell AI Python Custom LLM Demo](https://github.com/RetellAI/retell-custom-llm-python-demo)
- [OpenAI Realtime API Pricing](https://developers.openai.com/api/docs/pricing)
- [OpenAI Realtime SIP Guide](https://developers.openai.com/api/docs/guides/realtime-sip)
- [OpenAI + Twilio SIP Tutorial](https://www.twilio.com/en-us/blog/developers/tutorials/product/openai-realtime-api-elastic-sip-trunking)
- [OpenAI Voice Agents Guide](https://developers.openai.com/api/docs/guides/voice-agents)
- [ElevenLabs Conversational AI](https://elevenlabs.io/conversational-ai)
- [ElevenLabs Pricing](https://elevenlabs.io/pricing)
- [ElevenLabs Professional Voice Cloning](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning)
- [ElevenLabs Twilio Integration](https://elevenlabs.io/agents/integrations/twilio)
- [ElevenLabs Pricing Cut Announcement (March 2026)](https://elevenlabs.io/blog/we-cut-our-pricing-for-conversational-ai)
- [Bland AI Platform](https://www.bland.ai/)
- [Bland AI Billing Docs](https://docs.bland.ai/platform/billing)
- [Bland AI Review — Latency Issues (Retell)](https://www.retellai.com/blog/bland-ai-reviews)
- [Building a Voice AI Travel Agent with Retell AI and n8n](https://medium.com/@aimastermind/building-a-voice-ai-travel-agent-with-retell-ai-and-n8n-cc556058b160)

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 Research & Market Intelligence, Dreams2Memories Travel, LLC*
