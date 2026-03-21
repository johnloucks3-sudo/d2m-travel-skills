# MULTI-CHANNEL DANI DEPLOYMENT: OpenClaw + Alternatives Evaluation

**Classification:** D2M Internal -- A2 Staff Paper
**Date:** 2026-03-20
**From:** Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
**To:** Commander (Yoda) / COS (Hale)

---

## ISSUE

Dreams2Memories currently operates two custom Telegram bots (client-facing Dani + Commander C2) totaling ~3,400 lines of Python. Clients increasingly expect to reach Dani on WhatsApp, Signal, iMessage, and SMS -- not just Telegram. Evaluate whether OpenClaw or alternatives can serve as a multi-channel gateway routing all messaging platforms to our Dani Engine backend, replacing or augmenting our custom Telegram infrastructure.

---

## DISCUSSION

### 1. OpenClaw -- Primary Candidate

**Repository:** https://github.com/openclaw/openclaw
**Stars:** 327,221 (verified via GitHub API -- exceeds the 210K figure in the tasking)
**Forks:** 63,323 | **Open Issues:** 14,719
**License:** MIT (fully permissive -- commercial use, modification, distribution all clear)
**Language:** TypeScript | **Created:** 2025-11-24
**Last Push:** 2026-03-21 (active daily development)
**Current Version:** v2026.3.7

**What it is:** A self-hosted, open-source AI agent gateway. It decouples the messaging interface layer (where messages arrive) from the assistant runtime (where intelligence lives). One persistent agent, accessible through any messaging app, with conversation state and tool access managed centrally on your hardware.

#### Architecture

OpenClaw uses a hub-and-spoke model:

```
[WhatsApp] ─┐
[Telegram] ─┤
[Signal]   ─┤──→ [OpenClaw Gateway] ──→ [Agent Backend]
[iMessage] ─┤         (Router)          (Dani Engine)
[SMS]      ─┤
[Web Chat] ─┘
```

- **Gateway** = local control plane managing sessions, channels, tools, and events
- **Channels** = messaging platform connectors (50+ supported)
- **Agent Backend** = the LLM/intelligence layer (swappable)
- Messages arrive from any channel, Gateway normalizes them, routes to agent, streams response back

#### Supported Platforms (Verified)

| Platform | Status | Method | Notes |
|----------|--------|--------|-------|
| **Telegram** | Stable | Bot API (grammy) | Groups supported |
| **WhatsApp** | Stable | Baileys (unofficial) | **Ban risk with personal numbers** -- dedicated number required |
| **Signal** | Stable | signal-cli | Privacy-focused, solid |
| **iMessage** | Partial | macOS only | Requires a Mac running the gateway -- **blocker for YOGA (Linux)** |
| **Discord** | Stable | Native | Full support |
| **Slack** | Stable | Native | Full support |
| **SMS** | Via Twilio skill | Plugin | Requires Twilio account + costs |
| **Google Chat** | Stable | Native | Workspace integration |
| **Microsoft Teams** | Stable | Native | Enterprise |
| **Matrix** | Stable | Native | Protocol-level bridge |
| **Web Chat** | Stable | Built-in | Embeddable widget |
| **LINE** | Stable | Native | Asia-Pacific |
| **Mattermost** | Stable | Native | Self-hosted Slack alternative |
| **IRC** | Stable | Native | Legacy |
| **BlueBubbles** | Beta | macOS gateway | iMessage alternative path |
| **Feishu/Lark** | Stable | Native | China enterprise |
| **Others** | Various | Various | Nostr, Twitch, Zalo, Nextcloud Talk, Synology Chat, Tlon |

**Confidence: HIGH** -- platform list verified against official docs and GitHub README.

#### Dani Engine Integration Path

This is the critical question: can we plug our `thunderbird_dani_engine.py` into OpenClaw as the backend brain?

**Answer: Yes.** OpenClaw supports the **OpenResponses API** -- an open HTTP standard aligned with OpenAI's Responses API. The integration model:

1. We build a thin FastAPI adapter (~100-200 lines) that implements `POST /v1/responses`
2. Incoming messages from any channel hit this endpoint
3. Our adapter calls `build_dani_context()` + `cos_review()` + `pre_send_evaluate()` from `thunderbird_dani_engine.py`
4. Response streams back to the Gateway, which routes to the originating channel

This is **framework-agnostic** -- Python, TypeScript, anything. Our existing FastAPI infrastructure (`thunderbird_api.py`) is already the right shape. The adapter would:

- Receive the OpenResponses request (contains message text, session ID, channel metadata)
- Map session ID to client dossier
- Run full Dani pipeline (Aggregate -> Artist -> Advocate)
- Apply COS review gate
- Return formatted response

**Confidence: HIGH** that architectural fit works. **MODERATE** confidence on production stability (see Limitations below).

#### Self-Hosted Setup on YOGA

**Requirements:**
- Docker + Docker Compose v2 (YOGA has both)
- Minimum 2GB RAM for OpenClaw (YOGA has 32GB -- no issue)
- Node.js 20+ (for native install) or Docker image
- Storage: bind-mounted config + workspace directories

**Install path:**
```bash
# Docker (recommended)
git clone https://github.com/openclaw/openclaw
cd openclaw
./docker-setup.sh  # guided onboarding

# Or native
npm install -g openclaw
openclaw setup
```

**Confidence: HIGH** -- YOGA exceeds all requirements. openSUSE Tumbleweed + Docker is a supported configuration.

#### Limitations & Gotchas (Critical)

1. **WhatsApp Ban Risk** -- Baileys is an unofficial reverse-engineered protocol. WhatsApp actively detects automation. Accounts get banned without warning. **Must use a dedicated number, never John's personal number.** No guarantee of long-term stability.

2. **iMessage Requires macOS** -- The iMessage channel needs a Mac running the Gateway or BlueBubbles. YOGA is Linux. **iMessage is NOT available on our infrastructure** without adding a Mac Mini or similar.

3. **14,719 Open Issues** -- High issue count correlates with massive adoption, but also indicates churn. Security CVE-2026-25253 (RCE via WebSocket) was patched, but 30,000+ exposed instances were found. Security hardening is non-optional.

4. **Configuration Fragility** -- Reports of config files being auto-modified or damaged on restart. JSON config is not stable under all conditions. Requires backup discipline.

5. **Over-Autonomy Problem** -- OpenClaw agents can wander through reasoning loops, invoke tools repeatedly, reinterpret objectives. This is mitigated by using our own Dani Engine as the backend (we control the agent logic, OpenClaw only handles routing).

6. **Rapid Version Churn** -- 4 months old, moving fast. Breaking changes between versions. Operational burden to stay current.

7. **Production Criticism** -- Multiple credible sources (Medium, CNBC) flag that OpenClaw "was never ready for production" in its default configuration. Works best in "tightly scoped, well-observed environments" -- which is exactly what we'd build.

**Confidence: HIGH** on the limitation assessment. These are well-documented, not speculative.

---

### 2. Alternatives Evaluated

#### Botpress

**URL:** https://botpress.com | **GitHub:** https://github.com/botpress/botpress
**Stars:** ~13,000 | **License:** AGPL-3.0 (open source) + Cloud (paid)
**Type:** Visual conversational AI platform

**Strengths:**
- Drag-and-drop flow builder for conversation design
- Native channels: WhatsApp, Telegram, Messenger, Slack, Teams, web widget
- Built-in analytics (message volume, drop-off, intent tracking)
- 50+ integrations, LLM support (GPT, Claude)
- Self-hostable via Docker

**Weaknesses for D2M:**
- **Designed for structured chatbot flows, NOT autonomous agents.** Botpress agents cannot write code, browse the web, manage files, or call arbitrary APIs the way our Dani Engine does.
- Flow-based paradigm conflicts with Dani's Aggregate-Artist-Advocate pipeline. We'd be forcing a concierge into a decision-tree framework.
- AGPL license requires open-sourcing modifications if distributed (less concern for internal use)
- Rated 3.9/5 in 2026 reviews -- "good but not great" consensus

**D2M Fit: LOW.** Wrong architecture for our use case. Botpress is for customer service chatbots, not AI concierges with full data access.

**Confidence: HIGH.**

#### Chatwoot

**URL:** https://www.chatwoot.com | **GitHub:** https://github.com/chatwoot/chatwoot
**Stars:** ~22,000 | **License:** MIT
**Type:** Open-source customer engagement / omnichannel inbox

**Strengths:**
- Omnichannel inbox: website chat, Facebook, Instagram, WhatsApp, Telegram, email, SMS
- 50,000+ self-hosted production installations
- Agent assignment, canned responses, satisfaction surveys
- Mature, stable, well-documented
- Docker / one-click deploy (DigitalOcean, Heroku, CapRover)

**Weaknesses for D2M:**
- **Customer support platform, not an AI agent gateway.** Chatwoot routes messages to human agents, not AI backends.
- Bot integration exists but is primitive -- webhook-based, no streaming, no session state
- No concept of agent autonomy, tool calling, or LLM-driven responses
- Would require significant custom development to wire Dani in
- Overhead: full Ruby on Rails app, PostgreSQL, Redis, Sidekiq -- heavy stack for what we need

**D2M Fit: LOW-MODERATE.** Could serve as a message aggregation layer in front of Dani, but adds massive infrastructure complexity for minimal gain over OpenClaw.

**Confidence: HIGH.**

#### Matrix/Element Bridges (mautrix)

**URL:** https://matrix.org/ecosystem/bridges/ | **mautrix:** https://docs.mau.fi
**Type:** Protocol-level messaging bridges via Matrix protocol

**Strengths:**
- Bridges exist for WhatsApp (mautrix-whatsapp), Signal (mautrix-signal), Telegram (mautrix-telegram), iMessage (mautrix-imessage), Discord, Slack, Teams
- True protocol bridging -- messages appear native on each platform
- Element (Matrix client) provides unified inbox
- Decentralized, privacy-focused architecture
- Self-hosted (Synapse server + bridge processes)

**Weaknesses for D2M:**
- **Designed for human-to-human bridging, not AI agent routing.** No built-in concept of "route this message to an AI backend."
- Each bridge is a separate process with its own dependencies (Python, Go, etc.)
- mautrix-whatsapp also uses unofficial protocol (same ban risk as OpenClaw)
- mautrix-imessage requires macOS (same limitation)
- Significant ops burden: Synapse server + N bridge processes + configuration per bridge
- No agent framework, no session management, no tool calling

**D2M Fit: LOW.** Maximum infrastructure complexity for minimum agent capability. Would require building everything OpenClaw already provides.

**Confidence: HIGH.**

---

### 3. Comparison to Current Infrastructure

| Capability | Current (Custom Telegram) | OpenClaw |
|------------|--------------------------|----------|
| Channels | 1 (Telegram only) | 50+ |
| Lines of code we maintain | ~3,400 | ~200 (adapter only) |
| Dani Engine integration | Direct import | HTTP adapter (OpenResponses API) |
| COS review gate | Built-in | Must implement in adapter |
| Commander C2 | Separate bot | Could be separate agent or skill |
| Session persistence | In-memory / Telegram state | Built-in (Markdown files) |
| WhatsApp | Not available | Available (with caveats) |
| Signal | Not available | Available |
| iMessage | Not available | macOS only (not on YOGA) |
| SMS | Not available | Via Twilio skill |
| Web chat | Not available | Built-in widget |
| Deployment complexity | systemd services | Docker Compose |
| Security model | Telegram auth only | Requires hardening |
| Maturity | 6+ months stable | 4 months, fast-moving |

---

### 4. Information Gaps

- **I do not have** hands-on testing data for OpenClaw + custom Python backend latency. The adapter pattern is documented but production benchmarks under our specific load are unknown.
- **I do not have** verified data on WhatsApp ban rates for travel-industry use cases specifically. General automation ban rates are high, but low-volume concierge use may differ.
- **I do not have** a clear answer on whether OpenClaw's session management can map cleanly to our per-client dossier system. This requires a proof-of-concept.
- **Insufficient data** on OpenClaw's behavior when the backend (Dani) takes 15-30 seconds to respond (our typical response time with COS review). Gateway timeout behavior is undocumented for custom backends.

---

## OPTIONS

### Option 1: Deploy OpenClaw as Multi-Channel Gateway (Recommended)

- Run OpenClaw in Docker on YOGA alongside existing services
- Build thin FastAPI adapter mapping OpenResponses API to Dani Engine
- Enable Telegram + WhatsApp + Signal + Web Chat channels
- Keep Commander C2 bot as-is (separate concern)
- Phase: POC first (2-3 days), then staged rollout

**Risk:** Medium. New dependency, WhatsApp ban risk, security hardening required.
**Reward:** High. 4+ new client channels, unified session management, reduced custom code.

### Option 2: Incremental -- Add WhatsApp via Standalone Bridge

- Deploy mautrix-whatsapp or a standalone Baileys bot
- Keep existing Telegram infrastructure intact
- Add one channel at a time, custom code per channel

**Risk:** Low initial, high long-term (code multiplication per channel).
**Reward:** Low. Solves WhatsApp only, same ban risk, more code to maintain.

### Option 3: Hold -- Stay Telegram-Only

- No new infrastructure
- Wait for OpenClaw to mature (6-12 months)
- Focus engineering effort elsewhere

**Risk:** Low technical, moderate business (clients expect WhatsApp).
**Reward:** Zero new capability. Preserves stability.

### Option 4: Chatwoot + Custom Bot Layer

- Deploy Chatwoot as omnichannel inbox
- Build custom bot integration for Dani
- Heavy lift, high infrastructure overhead

**Risk:** High (complexity, maintenance burden).
**Reward:** Moderate (good inbox UI, but wrong tool for AI agents).

---

## ACTIONS I RECOMMEND TAKING

1. **Proceed with Option 1 -- OpenClaw POC.** The architecture is sound, the integration path (OpenResponses API) aligns with our existing FastAPI stack, and the reward-to-risk ratio is the best of all options.

2. **POC scope (2-3 days):**
   - Install OpenClaw via Docker on YOGA
   - Build the FastAPI adapter (`thunderbird_openclaw_adapter.py`) implementing `POST /v1/responses` -> Dani Engine pipeline
   - Enable Telegram channel first (validate parity with existing bot)
   - Enable WhatsApp channel with a **dedicated prepaid number** (not John's personal cell)
   - Test COS review gate through the adapter
   - Measure response latency end-to-end

3. **Security hardening before any client traffic:**
   - Firewall rules (YOGA UFW)
   - WebSocket origin validation (CVE-2026-25253 patch verified)
   - Disable unused channels
   - Gateway authentication enabled
   - Config backup cron

4. **Do NOT attempt iMessage** until we have a Mac in the infrastructure. Not worth the workaround complexity.

5. **Keep Commander C2 bot (`thunderbird_telegram_c2.py`) independent.** It serves a different function (staff commands, ops briefings) and should not route through OpenClaw. Commander's C2 channel stays Telegram-only.

6. **Establish rollback criteria:** If WhatsApp ban occurs within 30 days, or if OpenClaw Gateway uptime drops below 95%, revert to Telegram-only and revisit in Q3.

---

**Assessment Confidence:** HIGH on architecture fit, MODERATE on production stability, INSUFFICIENT DATA on long-term WhatsApp viability.

The 210K star count in the tasking was conservative -- it's actually 327K. The ecosystem is massive, the MIT license is clean, and the OpenResponses API is purpose-built for exactly our use case: bring your own agent brain, let the gateway handle the plumbing. The risks are real but manageable with proper scoping.

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2, D2M Travel*

---

## Sources

- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
- [OpenClaw Official Documentation](https://docs.openclaw.ai/channels)
- [OpenClaw Docker Setup](https://docs.openclaw.ai/install/docker)
- [OpenResponses API -- Custom Agent Integration (HuggingFace)](https://huggingface.co/blog/darielnoel/an-agentic-backend-openclaw-integration)
- [OpenClaw Architecture Overview (Substack)](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)
- [OpenClaw WhatsApp Baileys Ban Risk (GitHub Issue #4376)](https://github.com/openclaw/openclaw/issues/4376)
- [OpenClaw Security Challenges 2026 (DigitalOcean)](https://www.digitalocean.com/resources/articles/openclaw-security-challenges)
- [OpenClaw Production Criticism (Medium)](https://agentnativedev.medium.com/openclaw-was-never-ready-for-production-nvidias-nemoclaw-changes-that-268ce03ded95)
- [OpenClaw 2.26 Stability Fixes (UCStrategies)](https://ucstrategies.com/news/openclaw-2-26-update-major-stability-security-and-automation-fixes-explained/)
- [Botpress AI Platform](https://botpress.com/)
- [Botpress Review 2026 (Chatimize)](https://chatimize.com/reviews/botpress/)
- [Chatwoot Open Source Platform](https://www.chatwoot.com/)
- [Chatwoot GitHub](https://github.com/chatwoot/chatwoot)
- [Matrix.org Bridges](https://matrix.org/ecosystem/bridges/)
- [mautrix Bridge Documentation](https://docs.mau.fi/bridges/general/troubleshooting.html)
- [Multi-Channel AI Assistant with OpenClaw (APIDog)](https://apidog.com/blog/multi-channel-ai-assistant-openclaw/)
- [OpenClaw Custom LLM Provider (haimaker.ai)](https://haimaker.ai/blog/integrating-custom-llm-providers-with-clawdbot/)
- [OpenClaw + LiteLLM Integration](https://docs.litellm.ai/docs/tutorials/openclaw_integration)
- [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [OpenClaw CNBC Coverage](https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbook.html)
