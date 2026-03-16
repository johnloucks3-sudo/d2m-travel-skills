# WhatsApp API Production Plan -- Dreams2Memories Travel
## ELON (A12) -- 2026-03-15

---

## TL;DR

**Drop Twilio. Go direct to Meta WhatsApp Cloud API. Use PyWa (Python library). Wire it into the same Dani pipeline as Telegram. McLeod can be texting Dani within 2 weeks. Monthly cost for our volume: effectively $0 in Meta fees + zero platform markup.**

---

## 1. Current State

What we have today is a Twilio sandbox wrapper (`thunderbird_whatsapp.py`) that can only send outbound messages to pre-verified numbers. It is send-only -- no webhook, no inbound processing, no Dani brain. It is a 45-line script with hardcoded credentials (which, by the way, should not be hardcoded -- we will fix that).

What we need: bidirectional WhatsApp where clients message a D2M number, Dani responds with full Opus-powered intelligence, same as Telegram.

---

## 2. Provider Recommendation: Meta Cloud API (Direct)

### Why NOT Twilio

| Factor | Twilio | Meta Direct |
|--------|--------|-------------|
| Per-message markup | $0.005 sent + $0.005 received | $0.00 |
| Monthly platform fee | Pay-as-you-go (no minimum) | $0.00 |
| WhatsApp approval | Still goes through Meta anyway | Cut out the middleman |
| Webhook setup | Twilio proxy layer adds latency | Direct webhook to our server |
| Production approval | Twilio submits to Meta on your behalf | You submit directly, same timeline |
| Python library | twilio SDK (bloated, 500+ modules in venv) | PyWa (lightweight, purpose-built) |

Twilio adds a layer of abstraction and cost for zero added value. We already have our own infrastructure (cloudflared tunnel, FastAPI-capable server, webhook experience from Telegram). We do not need Twilio to hold our hand.

### Why NOT 360dialog / MessageBird / Vonage

- 360dialog: $49-99/month platform fee. Makes sense at 10K+ messages/month. We will send maybe 50-200/month. Overkill.
- MessageBird (Bird): Same $0.005/msg markup as Twilio. No advantage.
- Vonage: Enterprise-oriented, minimum commitments. Wrong fit.

**For a low-volume, high-value concierge service, Meta direct is the only answer that does not waste money.**

---

## 3. Cost Analysis

### Meta WhatsApp Pricing (Post July 2025 Model)

The new model charges per template message delivered, not per conversation.

| Message Type | Cost (US recipients) | Our Use Case |
|-------------|---------------------|--------------|
| Service (free-form within 24h window) | FREE | Client asks question, Dani responds -- this is 90%+ of our traffic |
| Utility template | FREE within 24h window | Booking confirmations, updates |
| Marketing template | ~$0.025/msg (North America) | We will almost never use this |
| Authentication template | ~$0.0135/msg | Not applicable |

**The 24-hour window rule is our best friend.** When McLeod sends a WhatsApp message to Dani, that opens a 24-hour window. Every response Dani sends within that window is FREE. The timer resets every time the client sends a new message. An active conversation stays free indefinitely.

### Estimated Monthly Cost

| Item | Cost |
|------|------|
| Meta message fees | $0-2/month (only outbound templates outside 24h window) |
| Twilio markup | $0 (we are dropping Twilio) |
| 360dialog/BSP fee | $0 (going direct) |
| Phone number | Use existing D2M number or get a new one (free through Meta) |
| Infrastructure | $0 incremental (runs on YOGA alongside Telegram) |
| **Total** | **~$0-2/month** |

Compare to Twilio: even at 100 messages/month, that is $1.00 in Twilio markup alone, plus you still pay Meta fees, plus you are locked into their sandbox until you go through their approval process which... goes through Meta anyway.

---

## 4. WhatsApp Business Compliance Rules

These are non-negotiable. WhatsApp will ban your number if you violate them.

### 4.1 Opt-In Requirement
- Clients MUST explicitly opt in to receive WhatsApp messages from D2M
- Opt-in can be: reply to a message, check a box on portal, verbal/email confirmation
- **For McLeod/McGlasson:** They are already initiating WhatsApp contact. That is implicit opt-in. We just need to document it.

### 4.2 The 24-Hour Window
- When a client messages us: 24-hour window opens. We can send free-form responses freely.
- Timer resets with each new client message.
- After 24 hours of client silence: we can ONLY send pre-approved template messages.
- Template messages cost money and require Meta approval.

### 4.3 Template Messages
- Must be pre-approved by Meta (usually approved within minutes to 24 hours)
- Categories: Marketing, Utility, Authentication
- We need 2-3 templates max:
  - **booking_update**: "Hi {{1}}, your booking {{2}} has been updated. {{3}}"
  - **trip_reminder**: "Hi {{1}}, your {{2}} departure is {{3}} days away. Reply to this message if you have any questions -- Dani, D2M Concierge"
  - **welcome**: "Hi {{1}}, this is Dani from Dreams2Memories Travel. You can message me here anytime for trip questions, booking updates, or travel assistance."

### 4.4 Quality Rating
- Meta monitors template quality via customer feedback
- If clients report messages as spam, template quality drops, eventually gets paused
- For a luxury concierge service with known clients, this is zero risk

### 4.5 Frequency Caps (New 2026)
- Meta now enforces per-user daily/weekly caps on marketing messages
- Does not affect service/utility messages
- Not relevant for our use case (we are not doing marketing blasts)

---

## 5. Architecture

### 5.1 The Pattern

This is almost identical to how Telegram works. The message flow:

```
Client WhatsApp msg
        |
        v
  Meta Cloud API webhook
        |
        v
  YOGA: thunderbird_whatsapp_bot.py (FastAPI endpoint)
        |
        v
  Groq classifier (intent detection)
        |
        v
  Dani Engine (build_dani_context)
        |
        v
  COS Review Gate (cos_review)
        |
        v
  Claude Opus via CLI (Agent SDK) -- for complex queries
        OR
  Groq Llama 4 Scout -- for routine queries
        |
        v
  WhatsApp reply via Cloud API
        +
  Commander notification via Telegram DM
```

### 5.2 Shared Pipeline

The key insight: **we do not build a second brain.** We reuse 100% of the existing Dani pipeline.

| Component | Already Built | Reuse? |
|-----------|--------------|--------|
| `thunderbird_dani_engine.py` | Yes | 100% -- same context builder, same data access |
| `thunderbird_personas.py` | Yes | 100% -- same persona system |
| `thunderbird_context.py` | Yes | 100% -- same context engine |
| `thunderbird_telegram_tools_sdk.py` | Yes | 90% -- same COS review, classify_intent, Opus escalation |
| COS review gate | Yes | 100% -- same review before client delivery |
| Commander notification | Yes | 100% -- same Telegram DM to Yoda |

**New code needed:**
- `thunderbird_whatsapp_bot.py` -- ~200 lines. FastAPI webhook handler, PyWa integration, message routing.
- Update `thunderbird_whatsapp.py` -- replace Twilio send with Meta Cloud API send.
- Cloudflared tunnel config -- add route for WhatsApp webhook endpoint.

### 5.3 Module Design

```python
# thunderbird_whatsapp_bot.py (new)

from fastapi import FastAPI
from pywa import WhatsApp
from pywa.types import Message

from thunderbird_dani_engine import build_dani_context, cos_review
from thunderbird_telegram_tools_sdk import classify_intent, call_cos_with_tools

app = FastAPI()

wa = WhatsApp(
    phone_id="YOUR_PHONE_NUMBER_ID",
    token="YOUR_ACCESS_TOKEN",
    server=app,           # PyWa hooks into FastAPI automatically
    callback_url="https://wa.d2mluxury.quest/webhook",
    verify_token="D2M_VERIFY_TOKEN",
    app_id="YOUR_APP_ID",
    app_secret="YOUR_APP_SECRET",
)

# Known clients (expand via registry)
CLIENT_NUMBERS = {
    "+1XXXXXXXXXX": "McLeod",
    "+1XXXXXXXXXX": "McGlasson",
}

@wa.on_message()
async def handle_message(client: WhatsApp, msg: Message):
    sender = msg.from_user.wa_id
    client_name = CLIENT_NUMBERS.get(f"+{sender}", "Unknown")
    text = msg.text

    # 1. Classify intent
    intent = await classify_intent(text, client_name)

    # 2. Build Dani context
    context = await build_dani_context(client_name, text)

    # 3. Generate response (Groq or Opus escalation)
    response = await call_cos_with_tools(text, context, client_name)

    # 4. COS review
    reviewed = await cos_review(response, client_name)

    # 5. Reply on WhatsApp
    msg.reply_text(reviewed)

    # 6. Notify Commander via Telegram
    await notify_commander(client_name, text, reviewed)
```

### 5.4 Webhook Routing

We already have cloudflared tunnel running. Options:

**Option A (recommended):** Add a subdomain route.
- `wa.d2mluxury.quest` -> YOGA port 8780 (or new port)
- Add to cloudflared tunnel config, restart tunnel service

**Option B:** Add a path on the existing API.
- `api.d2mluxury.quest/whatsapp/webhook`
- Mount the FastAPI app as a sub-application of the REST API

Option A is cleaner. Separate service, separate logs, separate restart capability.

---

## 6. Implementation Steps

### Phase 1: Meta Business Setup (Days 1-3)

1. **Create Meta Business Account** (if not already done for D2M)
   - Go to business.facebook.com
   - Register Dreams2Memories Travel, LLC
   - This may already exist from any Facebook/Instagram presence

2. **Business Verification**
   - Upload: business license/articles of incorporation, tax ID, utility bill or bank statement
   - Timeline: 3-7 business days (often faster for US businesses)
   - Without verification: limited to 250 conversations/24h (more than enough to start)

3. **Create WhatsApp Business App**
   - Go to developers.facebook.com
   - Create app -> select "Business" type
   - Add WhatsApp product
   - Get: Phone Number ID, Business Account ID, Permanent Access Token

4. **Register Phone Number**
   - Option A: Register 719-291-0742 (Yoda's number -- probably not ideal)
   - Option B: Get a new number for D2M WhatsApp (recommended)
   - Option C: Use the Meta-provided test number to start, migrate later
   - The number cannot simultaneously be used with WhatsApp personal app

### Phase 2: Build the Bot (Days 3-7)

1. **Install PyWa**
   ```bash
   pip install "pywa[fastapi]"
   ```

2. **Write `thunderbird_whatsapp_bot.py`**
   - FastAPI app with PyWa integration
   - Reuse Dani engine, COS review, Commander notification
   - Handle: text messages, media (photos of documents), location sharing
   - ~200-250 lines of new code

3. **Configure webhook**
   - Add `wa.d2mluxury.quest` to cloudflared tunnel config
   - Set Meta webhook URL to `https://wa.d2mluxury.quest/webhook`
   - Verify webhook with Meta's challenge request

4. **Create template messages**
   - Submit 2-3 templates for Meta approval
   - `welcome`, `booking_update`, `trip_reminder`

5. **Create systemd service**
   - `d2m-whatsapp.service` -- same pattern as other services
   - Auto-restart, user-level, survives logout

### Phase 3: Test and Launch (Days 7-14)

1. **Test with Commander's number** -- send/receive, verify Dani responds, COS review works
2. **Test template messages** -- verify outbound templates deliver
3. **Onboard McLeod/McGlasson** -- send welcome template, they reply, 24h window opens
4. **Monitor first week** -- watch for errors, response quality, latency

---

## 7. Timeline Summary

| Day | Milestone |
|-----|-----------|
| 1 | Meta Business account created, verification submitted |
| 2-3 | While waiting for verification: write the bot code, test with Meta test number |
| 3-7 | Verification approved, real number registered |
| 7-10 | Bot deployed on YOGA, webhook live, templates approved |
| 10-14 | McLeod/McGlasson onboarded and chatting with Dani |

**Fastest path:** If Meta approves verification quickly (some US businesses get approved same-day), McLeod could be talking to Dani on WhatsApp within a week.

---

## 8. Cleanup Actions

### Kill the Twilio Dependency
1. Remove hardcoded credentials from `thunderbird_whatsapp.py` (security issue regardless)
2. Replace Twilio send function with Meta Cloud API send
3. Eventually: `pip uninstall twilio` -- that package is massive (500+ modules in venv)
4. Update CLAUDE.md known issues section

### Phone Number Decision
The current Twilio sandbox uses `+14155238886` (Twilio's shared sandbox number). That goes away. We need a real number. Options:

| Option | Pros | Cons |
|--------|------|------|
| New dedicated number | Clean separation, professional | One more number to manage |
| Existing toll-free +18776118189 | Already have it | Was not WhatsApp-enabled per known issues |
| Meta test number | Free, instant | Not production-grade, cannot be client-facing |

**Recommendation:** Get a new dedicated number for D2M WhatsApp. Meta provides numbers or you can port an existing one. Keep it separate from Yoda's personal number.

---

## 9. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Meta verification takes >2 weeks | Low (US business, clean docs) | Start with test number, 250 conversation limit is fine |
| WhatsApp bans number for policy violation | Very low (we are concierge, not spam) | Follow template rules, document opt-ins |
| Client sends message outside 24h, we cannot reply free-form | Medium | Have template messages ready for re-engagement |
| PyWa library has breaking changes | Low | Pin version, it is actively maintained (v3.9) |
| Latency from Opus/Groq processing | Medium | Same as Telegram -- async processing, "typing" indicator |

---

## 10. What I Would NOT Do

1. **Do not use the WhatsApp Business App** (the free phone app). No API access, no webhooks, no automation. It is a dead end for what we need.

2. **Do not use Twilio for this.** We are paying a middleman to talk to Meta for us. We can talk to Meta directly. The Twilio SDK is 500+ files of bloat we do not need.

3. **Do not build a separate "WhatsApp brain."** Dani is Dani regardless of channel. One engine, multiple transports. That is the whole point.

4. **Do not wait for WhatsApp Business approval to start coding.** Build against the test number, swap to production when approved.

5. **Do not overthink compliance.** We are a luxury travel concierge responding to clients who want to talk to us. We are not sending marketing blasts to strangers. The rules are designed to stop spam, not stop us.

---

## 11. Final Architecture Diagram

```
                    CLIENTS
                   /       \
            Telegram      WhatsApp
               |              |
    python-telegram-bot    PyWa (FastAPI)
               |              |
               v              v
        +---------------------------+
        |    Unified Dani Pipeline   |
        |                           |
        |  classify_intent (Groq)   |
        |  build_dani_context       |
        |  call_cos_with_tools      |
        |  cos_review               |
        +---------------------------+
               |
               v
        Claude Opus (complex)
           or Groq (routine)
               |
               v
        +---------------------------+
        |   Response Router         |
        |   - Telegram reply        |
        |   - WhatsApp reply        |
        |   - Commander notify      |
        +---------------------------+
```

Two transports, one brain. Build it once, benefit forever.

---

## Sources

- [Meta WhatsApp Cloud API - Get Started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started)
- [WhatsApp Business Platform Pricing](https://business.whatsapp.com/products/platform-pricing)
- [Meta WhatsApp Pricing Documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- [Twilio WhatsApp Pricing](https://www.twilio.com/en-us/whatsapp/pricing)
- [Twilio WhatsApp API: Pricing, Setup & Alternatives 2026](https://chatarmin.com/en/blog/twilio-whats-app-api)
- [WhatsApp API Pricing: What Businesses Need to Know in 2026](https://respond.io/blog/whatsapp-business-api-pricing)
- [360dialog Pricing](https://360dialog.com/pricing)
- [WhatsApp Business API Compliance 2026](https://gmcsco.com/your-simple-guide-to-whatsapp-api-compliance-2026/)
- [PyWa Documentation (v3.9)](https://pywa.readthedocs.io/en/latest/)
- [Building WhatsApp Business Bots - Architecture and Webhooks](https://dev.to/achiya-automation/building-whatsapp-business-bots-with-the-official-api-architecture-webhooks-and-automation-1ce4)
- [WhatsApp Business Bot Development 2026](https://www.groovyweb.co/blog/whatsapp-business-bot-development-2026)
- [WhatsApp Cloud API Setup Guide 2026](https://chatarmin.com/en/blog/how-to-set-up-the-whats-app-api)
