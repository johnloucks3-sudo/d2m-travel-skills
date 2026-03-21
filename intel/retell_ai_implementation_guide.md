# RETELL AI — DANI VOICE AGENT IMPLEMENTATION GUIDE
## Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
## Dreams2Memories Travel, LLC
### Date: 2026-03-20 | Classification: INTERNAL

---

## D2M RELEVANCE SUMMARY

1. **Retell AI is confirmed viable for Dani Voice Agent** — Custom LLM WebSocket integration lets us keep all intelligence in the Dani Engine while Retell handles voice I/O. High confidence.
2. **Cost projection: $0.085-0.125/minute all-in** — at 20 calls/day averaging 3 minutes each, roughly $150-225/month. Falls within the $150-180 budget window with modest call volumes.
3. **Latency floor is 600ms** — Retell claims "as low as 600ms" end-to-end. Achievable with streaming responses, fast TTS provider, and YOGA server proximity. Our Dani Engine must stream, not batch.
4. **Voice cloning available across 5 providers** — We can create a consistent "Dani voice" using ElevenLabs (best quality, up to 25 training files) or Cartesia/MiniMax (lower cost, 1 file each).
5. **Twilio SIP trunk integration is documented and straightforward** — Import existing Twilio numbers or buy through Retell directly at $2/month per number.

---

## TABLE OF CONTENTS

1. [Signup & Account Setup](#1-signup--account-setup)
2. [Pricing Deep Dive](#2-pricing-deep-dive)
3. [Architecture: How It All Connects](#3-architecture-how-it-all-connects)
4. [Custom LLM WebSocket Protocol](#4-custom-llm-websocket-protocol)
5. [Dani WebSocket Server Implementation](#5-dani-websocket-server-implementation)
6. [Twilio SIP Trunk Setup](#6-twilio-sip-trunk-setup)
7. [Voice Configuration & Cloning](#7-voice-configuration--cloning)
8. [Latency Optimization](#8-latency-optimization)
9. [Python SDK Reference](#9-python-sdk-reference)
10. [Deployment Architecture for YOGA](#10-deployment-architecture-for-yoga)
11. [Information Gaps](#11-information-gaps)

---

## 1. SIGNUP & ACCOUNT SETUP

### Registration

- **Dashboard URL:** https://dashboard.retellai.com
- **Pricing page:** https://www.retellai.com/pricing
- **Free credits:** $10 in credits on signup — no credit card required initially
- **No annual contracts, no minimum commitment**

### Steps

1. Register at dashboard.retellai.com (email + password)
2. Navigate to Agents > Create an agent
3. Test via built-in web calling interface (no phone number needed)
4. Add payment method via Billing tab before purchasing phone numbers
5. Generate API key from Dashboard > Settings > API Keys

### API Key

```
Authorization: Bearer YOUR_RETELL_API_KEY
```

All REST API calls and SDK initialization use this single key. Guard it like a TS//SCI access badge.

---

## 2. PRICING DEEP DIVE

### Pay-As-You-Go (Our Tier)

No monthly subscription. You pay per minute of voice agent usage.

#### Per-Minute Cost Breakdown

| Component | Cost/Min | Notes |
|---|---|---|
| Retell Voice Infrastructure | $0.055 | Fixed, all plans |
| Telephony (PSTN) | $0.015 | US domestic; varies by country |
| TTS — Platform/Minimax/Fish/Cartesia/OpenAI | $0.015 | Lowest tier |
| TTS — ElevenLabs | $0.040 | Premium quality |
| LLM — Custom LLM (ours) | $0.000 | We host it; no Retell LLM charge |

#### Total Per-Minute Estimates for D2M

| Configuration | Cost/Min | Monthly (60 min/day) |
|---|---|---|
| Custom LLM + Platform TTS | $0.085 | ~$155 |
| Custom LLM + ElevenLabs TTS | $0.110 | ~$200 |
| Custom LLM + Cartesia TTS | $0.085 | ~$155 |

**Key insight:** Because we use Custom LLM (our Dani Engine), we pay $0.00 for the LLM component. The Retell-hosted LLM costs ($0.027-$0.080/min) do not apply.

#### Add-On Costs

| Feature | Cost |
|---|---|
| Phone Number (Retell-managed) | $2/month |
| Verified Phone Number (caller ID) | $10/month |
| Additional concurrent calls (beyond 20 free) | $8/concurrent call/month |
| Knowledge Base (beyond 10 free) | $8/month |
| SMS capability | $20/month |

#### Enterprise Tier

Custom pricing, dedicated support, SSO, RBAC, no concurrency cap, 24/7 support. Contact sales. Not needed at our volume.

### D2M Cost Projection

Assumptions: 10-20 calls/day, average 3 minutes each, 30 days/month.

| Scenario | Calls/Day | Min/Day | Monthly Cost |
|---|---|---|---|
| Conservative | 10 | 30 | $78-102 |
| Moderate | 20 | 60 | $155-200 |
| Growth | 40 | 120 | $310-400 |

Plus $2/month per phone number, $10/month for verified caller ID.

---

## 3. ARCHITECTURE: HOW IT ALL CONNECTS

### Data Flow

```
Caller (Phone/Web)
    |
    v
[Retell Platform] -- STT --> text transcript
    |
    v
[WebSocket Connection to YOGA]
    |
    v
[Dani WebSocket Server (FastAPI on YOGA)]
    |
    v
[Dani Engine / Thunderbird REST API]
    |-- client dossier lookup
    |-- booking data from Google Sheets
    |-- MCP tool calls (120+ tools)
    |-- COS review gate (if needed)
    |-- voice ledger rules
    v
[Streamed text response back via WebSocket]
    |
    v
[Retell Platform] -- TTS --> audio
    |
    v
Caller hears Dani's voice
```

### Key Architecture Decisions

1. **Custom LLM mode** — Retell sends us transcripts via WebSocket, we send back response text. All intelligence stays on YOGA.
2. **No Retell-hosted LLM** — We do not use their GPT/Claude/Gemini. Our Dani Engine IS the LLM layer.
3. **WebSocket, not REST** — The Custom LLM protocol is WebSocket-based, enabling streaming responses (critical for latency).
4. **Retell handles:** STT (speech-to-text), TTS (text-to-speech), telephony, interruption detection, turn-taking, backchannel sounds.
5. **We handle:** Conversation logic, client context, booking lookups, persona voice rules, response generation.

---

## 4. CUSTOM LLM WEBSOCKET PROTOCOL

### Connection

Retell connects to your WebSocket server when a call starts:

```
wss://your-domain.com/llm-websocket/{call_id}
```

For D2M on YOGA via cloudflared:
```
wss://api.d2mluxury.quest/llm-websocket/{call_id}
```

**Retell's IP for allowlisting:** `100.20.5.228`

### Message Protocol

All messages are JSON-stringified text frames. Two directions:

#### RETELL --> YOUR SERVER (Inbound Events)

**1. Ping Pong** (every 2 seconds when auto_reconnect is true)
```json
{
  "interaction_type": "ping_pong",
  "timestamp": 1703302428000
}
```

**2. Call Details** (sent once at connection start when call_details is true)
```json
{
  "interaction_type": "call_details",
  "call": {
    "call_id": "...",
    "agent_id": "...",
    "call_type": "phone_call",
    "direction": "inbound",
    "from_number": "+17192910742",
    "to_number": "+17195551234",
    "metadata": {},
    "retell_llm_dynamic_variables": {}
  }
}
```

**3. Update Only** (transcript changed, no response needed)
```json
{
  "interaction_type": "update_only",
  "transcript": [
    {"role": "agent", "content": "Hello, this is Dani..."},
    {"role": "user", "content": "Hi, I have a question about my cruise"}
  ],
  "turntaking": "agent_turn"
}
```

**4. Response Required** (user stopped speaking, agent must respond)
```json
{
  "interaction_type": "response_required",
  "response_id": 1,
  "timestamp": 1703302428000,
  "transcript": [
    {"role": "agent", "content": "Hello, this is Dani..."},
    {"role": "user", "content": "Hi, I have a question about my cruise"}
  ]
}
```

**5. Reminder Required** (user has been silent for reminder_trigger_ms)
```json
{
  "interaction_type": "reminder_required",
  "response_id": 2,
  "transcript": [...]
}
```

#### YOUR SERVER --> RETELL (Outbound Events)

**1. Config** (send immediately on connection)
```json
{
  "response_type": "config",
  "config": {
    "auto_reconnect": true,
    "call_details": true,
    "transcript_with_tool_calls": true
  }
}
```

**2. Ping Pong Response** (reply within 5 seconds or reconnect triggers)
```json
{
  "response_type": "ping_pong",
  "timestamp": 1703302428000
}
```

**3. Response** (streamed text chunks)
```json
{
  "response_type": "response",
  "response_id": 1,
  "content": "Of course! Let me pull up your ",
  "content_complete": false,
  "end_call": false
}
```

Final chunk:
```json
{
  "response_type": "response",
  "response_id": 1,
  "content": "",
  "content_complete": true,
  "end_call": false
}
```

**4. Response with Call Control**
```json
{
  "response_type": "response",
  "response_id": 3,
  "content": "Let me transfer you to John now.",
  "content_complete": true,
  "end_call": false,
  "transfer_number": "+17192910742",
  "show_transferee_as_caller": false
}
```

**5. Agent Interrupt** (agent speaks without being asked)
```json
{
  "response_type": "agent_interrupt",
  "interrupt_id": 1,
  "content": "Oh, I just found something interesting about your booking.",
  "content_complete": true,
  "no_interruption_allowed": false
}
```

**6. Update Agent** (change behavior mid-call)
```json
{
  "response_type": "update_agent",
  "agent_config": {
    "responsiveness": 0.8,
    "interruption_sensitivity": 0.5,
    "reminder_trigger_ms": 15000,
    "reminder_max_count": 2
  }
}
```

**7. Tool Call Invocation** (log function calls in transcript)
```json
{
  "response_type": "tool_call_invocation",
  "tool_call_id": "tc_abc123",
  "name": "lookup_booking",
  "arguments": "{\"client_name\": \"Lyons\"}"
}
```

**8. Tool Call Result**
```json
{
  "response_type": "tool_call_result",
  "tool_call_id": "tc_abc123",
  "content": "{\"booking\": \"RSSC Splendor\", \"dates\": \"Aug 2026\"}"
}
```

**9. Metadata** (forward data to frontend — web calls only)
```json
{
  "response_type": "metadata",
  "metadata": {"client_tier": "Friend Service", "dossier_id": "lyons_nancy_ken"}
}
```

### Critical Protocol Behaviors

- **response_id tracking:** When Retell sends a new `response_required` with a higher `response_id`, stop generating for the old one. The user interrupted or the conversation moved on.
- **Streaming:** Send multiple response events with `content_complete: false`, then a final one with `content_complete: true`. TTS starts rendering as soon as first chunk arrives.
- **5-second ping deadline:** If you don't respond to ping_pong within 5 seconds, Retell disconnects and reconnects (if auto_reconnect is true).

---

## 5. DANI WEBSOCKET SERVER IMPLEMENTATION

### Core Types (custom_types.py)

```python
from typing import List, Optional, Literal, Union, Dict
from pydantic import BaseModel


# === RETELL --> OUR SERVER ===

class Utterance(BaseModel):
    role: Literal["agent", "user", "system"]
    content: str


class PingPongRequest(BaseModel):
    interaction_type: Literal["ping_pong"]
    timestamp: int


class CallDetailsRequest(BaseModel):
    interaction_type: Literal["call_details"]
    call: dict


class UpdateOnlyRequest(BaseModel):
    interaction_type: Literal["update_only"]
    transcript: List[Utterance]


class ResponseRequiredRequest(BaseModel):
    interaction_type: Literal["reminder_required", "response_required"]
    response_id: int
    transcript: List[Utterance]


CustomLlmRequest = Union[
    ResponseRequiredRequest, UpdateOnlyRequest, CallDetailsRequest, PingPongRequest
]


# === OUR SERVER --> RETELL ===

class ConfigResponse(BaseModel):
    response_type: Literal["config"] = "config"
    config: Dict[str, bool]


class PingPongResponse(BaseModel):
    response_type: Literal["ping_pong"] = "ping_pong"
    timestamp: int


class ResponseResponse(BaseModel):
    response_type: Literal["response"] = "response"
    response_id: int
    content: str
    content_complete: bool
    end_call: Optional[bool] = False
    transfer_number: Optional[str] = None
    no_interruption_allowed: Optional[bool] = False


CustomLlmResponse = Union[ConfigResponse, PingPongResponse, ResponseResponse]
```

### WebSocket Server (dani_retell_server.py)

```python
"""
Dani Voice Agent — Retell AI Custom LLM WebSocket Server
Dreams2Memories Travel, LLC

Connects Retell's voice I/O to the Thunderbird Dani Engine.
All intelligence stays on YOGA. Retell handles STT/TTS/telephony.
"""

import json
import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from concurrent.futures import TimeoutError as ConnectionTimeoutError
from retell import Retell
from custom_types import (
    ConfigResponse,
    ResponseRequiredRequest,
    ResponseResponse,
)
from dani_llm import DaniLlmClient

load_dotenv(override=True)

app = FastAPI(title="Dani Voice Agent — Retell WebSocket Server")
retell = Retell(api_key=os.environ["RETELL_API_KEY"])


# === WEBHOOK HANDLER ===
# Retell sends call lifecycle events here

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        post_data = await request.json()
        valid_signature = retell.verify(
            json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
            api_key=str(os.environ["RETELL_API_KEY"]),
            signature=str(request.headers.get("X-Retell-Signature")),
        )
        if not valid_signature:
            print(f"Unauthorized webhook: {post_data['event']} "
                  f"call_id={post_data['data']['call_id']}")
            return JSONResponse(status_code=401,
                                content={"message": "Unauthorized"})

        event = post_data["event"]
        call_id = post_data["data"]["call_id"]

        if event == "call_started":
            print(f"[DANI VOICE] Call started: {call_id}")
            # TODO: Log to Telegram C2, create call record
        elif event == "call_ended":
            print(f"[DANI VOICE] Call ended: {call_id}")
            # TODO: Log duration, save transcript, notify Commander
        elif event == "call_analyzed":
            print(f"[DANI VOICE] Call analyzed: {call_id}")
            # TODO: Extract post-call analysis, store in dossier
        else:
            print(f"[DANI VOICE] Unknown event: {event}")

        return JSONResponse(status_code=200, content={"received": True})

    except Exception as err:
        print(f"[DANI VOICE] Webhook error: {err}")
        return JSONResponse(status_code=500,
                            content={"message": "Internal Server Error"})


# === WEBSOCKET HANDLER ===
# The core: Retell connects here for every call

@app.websocket("/llm-websocket/{call_id}")
async def websocket_handler(websocket: WebSocket, call_id: str):
    try:
        await websocket.accept()
        llm_client = DaniLlmClient()

        # Step 1: Send config
        config = ConfigResponse(
            response_type="config",
            config={
                "auto_reconnect": True,
                "call_details": True,
            },
        )
        await websocket.send_json(config.model_dump())

        # Step 2: Send Dani's greeting
        response_id = 0
        first_event = llm_client.draft_begin_message()
        await websocket.send_json(first_event.model_dump())

        # Step 3: Handle incoming messages
        async def handle_message(request_json):
            nonlocal response_id

            # Ping/pong keepalive
            if request_json["interaction_type"] == "ping_pong":
                await websocket.send_json({
                    "response_type": "ping_pong",
                    "timestamp": request_json["timestamp"],
                })
                return

            # Call details — log for context
            if request_json["interaction_type"] == "call_details":
                call_data = request_json.get("call", {})
                caller = call_data.get("from_number", "unknown")
                print(f"[DANI VOICE] Call details: caller={caller}")
                # TODO: Look up caller in client dossiers by phone number
                # TODO: Inject client context into DaniLlmClient
                llm_client.set_caller_context(call_data)
                return

            # Update only — no response needed
            if request_json["interaction_type"] == "update_only":
                return

            # Response required or reminder required
            if request_json["interaction_type"] in (
                "response_required", "reminder_required"
            ):
                response_id = request_json["response_id"]
                request = ResponseRequiredRequest(
                    interaction_type=request_json["interaction_type"],
                    response_id=response_id,
                    transcript=request_json["transcript"],
                )

                last_msg = request_json["transcript"][-1]["content"]
                print(f"[DANI VOICE] {request_json['interaction_type']} "
                      f"id={response_id} last='{last_msg[:80]}'")

                async for event in llm_client.draft_response(request):
                    await websocket.send_json(event.model_dump())
                    # Stop if a newer response_id arrived (user interrupted)
                    if request.response_id < response_id:
                        break

        async for data in websocket.iter_json():
            asyncio.create_task(handle_message(data))

    except WebSocketDisconnect:
        print(f"[DANI VOICE] WebSocket disconnected: {call_id}")
    except ConnectionTimeoutError:
        print(f"[DANI VOICE] Connection timeout: {call_id}")
    except Exception as e:
        print(f"[DANI VOICE] WebSocket error: {e} call_id={call_id}")
        await websocket.close(1011, "Server error")
    finally:
        print(f"[DANI VOICE] Connection closed: {call_id}")
```

### Dani LLM Client (dani_llm.py)

This is where we connect to the existing Thunderbird Dani Engine.

```python
"""
Dani LLM Client — bridges Retell WebSocket protocol to Thunderbird Dani Engine.

Instead of calling OpenAI directly, this calls our own Dani Engine
which has full access to client dossiers, booking data, voice ledger,
and 120+ MCP tools.
"""

import os
import httpx
from typing import List, AsyncGenerator, Optional, Dict, Any
from custom_types import (
    ResponseRequiredRequest,
    ResponseResponse,
    Utterance,
)

# Thunderbird API on YOGA
THUNDERBIRD_API = os.environ.get(
    "THUNDERBIRD_API_URL", "http://localhost:8766"
)

DANI_GREETING = (
    "Hello, this is Dani with Dreams2Memories Travel. "
    "How can I help you today?"
)

DANI_REMINDER = (
    "I'm still here whenever you're ready. "
    "Is there anything I can help you with?"
)

DANI_SYSTEM_PROMPT = """You are Dani Moreau, the luxury travel concierge for Dreams2Memories Travel, LLC.

## Voice & Personality
- Warm but operationally crisp. Civilian concierge, not military.
- Conversational, not corporate. Use everyday language.
- Keep responses SHORT for voice — 1-3 sentences max per turn.
- Never say "I'm an AI" or "I'm a virtual assistant."
- You ARE Dani. Own it.

## Style for Voice
- Be concise. One thought per utterance.
- Use filler words sparingly for naturalness ("Let me check on that...", "Oh, great question...")
- Address one question at a time. Don't pack everything into one response.
- End with a question or next step to keep the conversation flowing.

## Capabilities
- Look up client bookings and trip details
- Answer questions about upcoming cruises, hotels, excursions
- Take notes and messages for John (the owner)
- Provide destination information
- Schedule callbacks

## Boundaries
- Never quote prices without checking (say "Let me have John get back to you with exact pricing")
- Never make booking changes on the phone (say "I'll make a note and have John confirm that change with you")
- If unsure, say "Let me check on that and have someone get back to you"
- For urgent matters, offer to transfer to John: "Let me connect you with John directly"

## Transfer Protocol
- Commander's cell: +17192910742 (only for existing clients or urgent matters)
"""


class DaniLlmClient:
    def __init__(self):
        self.caller_context: Optional[Dict[str, Any]] = None
        self.client_info: Optional[Dict[str, Any]] = None

    def set_caller_context(self, call_data: dict):
        """Store call metadata for client lookup."""
        self.caller_context = call_data
        caller_number = call_data.get("from_number", "")
        # TODO: Async lookup of client by phone number via Thunderbird API
        # self.client_info = await self._lookup_client(caller_number)

    def draft_begin_message(self) -> ResponseResponse:
        """The first thing Dani says when answering the phone."""
        return ResponseResponse(
            response_id=0,
            content=DANI_GREETING,
            content_complete=True,
            end_call=False,
        )

    def _build_messages(self, request: ResponseRequiredRequest) -> list:
        """Convert Retell transcript to chat completion messages."""
        messages = [{"role": "system", "content": DANI_SYSTEM_PROMPT}]

        # Inject client context if available
        if self.client_info:
            context = (
                f"CALLER CONTEXT: This is {self.client_info.get('name', 'unknown')}. "
                f"Tier: {self.client_info.get('tier', 'unknown')}. "
                f"Active bookings: {self.client_info.get('bookings', 'none')}."
            )
            messages.append({"role": "system", "content": context})

        # Convert transcript
        for utterance in request.transcript:
            if utterance.role == "agent":
                messages.append({
                    "role": "assistant",
                    "content": utterance.content
                })
            else:
                messages.append({
                    "role": "user",
                    "content": utterance.content
                })

        # Handle reminder (user silent)
        if request.interaction_type == "reminder_required":
            messages.append({
                "role": "user",
                "content": "(The caller has been silent. Gently check in.)"
            })

        return messages

    async def draft_response(
        self, request: ResponseRequiredRequest
    ) -> AsyncGenerator[ResponseResponse, None]:
        """
        Generate Dani's response by calling the Thunderbird API.

        OPTION A (MVP): Call Anthropic/OpenAI directly with Dani's prompt.
        OPTION B (Full): Call Thunderbird REST API /dani/voice endpoint
                         which runs the full Dani Engine pipeline.

        Both options stream the response token-by-token back to Retell.
        """
        messages = self._build_messages(request)

        # --- OPTION A: Direct Anthropic API (MVP) ---
        # Uses Claude to generate Dani's voice responses directly.
        # Faster to implement, less context than full Dani Engine.

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )

            async with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=200,  # Short for voice
                messages=[m for m in messages if m["role"] != "system"],
                system=DANI_SYSTEM_PROMPT,
            ) as stream:
                async for text in stream.text_stream:
                    yield ResponseResponse(
                        response_id=request.response_id,
                        content=text,
                        content_complete=False,
                        end_call=False,
                    )

            # Signal completion
            yield ResponseResponse(
                response_id=request.response_id,
                content="",
                content_complete=True,
                end_call=False,
            )

        except Exception as e:
            print(f"[DANI LLM] Error generating response: {e}")
            yield ResponseResponse(
                response_id=request.response_id,
                content="I'm sorry, I'm having a little trouble right now. "
                        "Can I have John call you back?",
                content_complete=True,
                end_call=False,
            )

        # --- OPTION B: Full Thunderbird API (Production) ---
        # Uncomment when /dani/voice endpoint is built
        #
        # async with httpx.AsyncClient() as http:
        #     async with http.stream(
        #         "POST",
        #         f"{THUNDERBIRD_API}/dani/voice",
        #         json={
        #             "transcript": [u.model_dump() for u in request.transcript],
        #             "interaction_type": request.interaction_type,
        #             "caller_number": self.caller_context.get("from_number"),
        #             "call_id": self.caller_context.get("call_id"),
        #         },
        #         timeout=10.0,
        #     ) as resp:
        #         async for chunk in resp.aiter_text():
        #             yield ResponseResponse(
        #                 response_id=request.response_id,
        #                 content=chunk,
        #                 content_complete=False,
        #                 end_call=False,
        #             )
        #
        #     yield ResponseResponse(
        #         response_id=request.response_id,
        #         content="",
        #         content_complete=True,
        #         end_call=False,
        #     )
```

### Requirements (requirements.txt for Dani Voice)

```
retell-sdk>=5.22.0
fastapi>=0.100.0
uvicorn>=0.21.0
python-dotenv>=1.0.0
pydantic>=2.6.0
anthropic>=0.40.0
httpx>=0.26.0
python-multipart>=0.0.9
```

### Environment Variables (.env)

```bash
RETELL_API_KEY=your_retell_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
THUNDERBIRD_API_URL=http://localhost:8766
```

---

## 6. TWILIO SIP TRUNK SETUP

### Overview

Two paths to get a phone number connected to Retell:

| Method | Pros | Cons |
|---|---|---|
| **Retell-managed number** | One-click, $2/month | Limited area codes, less control |
| **Twilio SIP trunk** | Full control, existing numbers, caller ID masking | More setup, Twilio costs extra |

### Path A: Retell-Managed Number (Fastest)

```python
from retell import Retell

client = Retell(api_key="YOUR_RETELL_API_KEY")

# Buy a number with 719 area code (Colorado Springs)
response = client.phone_number.create(
    area_code=719,
    inbound_agents=[{
        "agent_id": "your_dani_agent_id",
        "weight": 1.0,
    }],
    nickname="D2M Dani Voice Line",
)
print(f"Number: {response.phone_number}")
# Cost: $2/month + per-minute usage
```

### Path B: Twilio SIP Trunk (Full Control)

#### Step 1: Create Elastic SIP Trunk in Twilio

1. Log into Twilio Console > Elastic SIP Trunking
2. Create new trunk, name it "D2M-Retell"
3. **Termination (outbound):** Set SIP URI for your region
4. **Security:** Choose IP Whitelisting, add Retell CIDR: `18.98.16.120/30`
   - OR create username/password credentials
5. **Origination (inbound):** Set origination URI to `sip:sip.retellai.com`

#### Step 2: Move/Buy Phone Number in Twilio

Assign your D2M business number to the elastic SIP trunk in Twilio's phone numbers section.

#### Step 3: Import Number into Retell

```python
from retell import Retell

client = Retell(api_key="YOUR_RETELL_API_KEY")

response = client.phone_number.import_(
    phone_number="+17195551234",  # Your Twilio number, E.164 format
    termination_uri="your-trunk.pstn.twilio.com",
    # If using auth instead of IP whitelisting:
    # sip_trunk_auth_username="your_username",
    # sip_trunk_auth_password="your_password",
    inbound_agents=[{
        "agent_id": "your_dani_agent_id",
        "weight": 1.0,
    }],
    nickname="D2M Main Line",
)
print(f"Imported: {response.phone_number}")
```

### Retell SIP Server Details

| Parameter | Value |
|---|---|
| SIP URI | `sip:sip.retellai.com` |
| IP Blocks | `18.98.16.120/30`, `143.223.88.0/21`, `161.115.160.0/19` |
| Transports | TCP (recommended), UDP, TLS |
| TLS syntax | `sip:sip.retellai.com;transport=tls` |
| SRTP | Supported (requires TLS transport) |

### Caller ID Masking (Twilio)

To show your D2M number as caller ID on outbound calls:

1. Twilio > Verified Caller IDs > verify your D2M number via OTP
2. Create SIP header manipulation policy: set "From number" to your verified number in E.164 format
3. Apply policy to trunk termination settings

---

## 7. VOICE CONFIGURATION & CLONING

### Available Voice Providers

| Provider | TTS Cost/Min | Quality | Cloning | Max Clone Files |
|---|---|---|---|---|
| Platform (Retell) | $0.015 | Good, optimized for phone | Yes | Via dashboard |
| Cartesia | $0.015 | Good, strong spelling | Yes | 1 file |
| MiniMax | $0.015 | Good, best Asian langs | Yes | 1 file |
| Fish Audio | $0.015 | Good | Yes | Via dashboard |
| OpenAI | $0.015 | Good | No | N/A |
| ElevenLabs | $0.040 | Best naturalness | Yes | Up to 25 files |

### Recommended Voice Strategy for Dani

**Phase 1 (MVP):** Use a Retell Platform voice. These are "fine-tuned specifically for conversational AI over the phone" with optimized fillers, pacing, and conversational rhythm. Browse and preview in the dashboard.

**Phase 2 (Custom Dani):** Clone a voice via ElevenLabs (best quality, up to 25 training audio files) to create a consistent, recognizable "Dani" voice. This becomes her signature.

### Voice Cloning via API

```python
from retell import Retell

client = Retell(api_key="YOUR_RETELL_API_KEY")

# Clone a voice using ElevenLabs (highest quality, up to 25 files)
with open("dani_voice_sample_1.wav", "rb") as f1, \
     open("dani_voice_sample_2.wav", "rb") as f2:
    voice = client.voice.clone(
        voice_name="Dani Moreau",
        voice_provider="elevenlabs",
        files=[f1, f2],
    )
print(f"Voice ID: {voice.voice_id}")
```

**Cloning constraints:**
- ElevenLabs: up to 25 audio files
- Cartesia, MiniMax: 1 file only
- Account limit: 100 custom voices total
- No documented minimum duration or format requirements (information gap)

### Agent Voice Configuration

```python
# Create agent with voice settings
agent = client.agent.create(
    response_engine={
        "type": "custom-llm",
        "llm_websocket_url": "wss://api.d2mluxury.quest/llm-websocket",
    },
    voice_id="your-cloned-dani-voice-id",
    voice_speed=1.0,           # 0.5 to 2.0
    voice_temperature=0.8,     # 0.0 to 2.0 (lower = more stable)
    volume=1.0,                # 0.0 to 2.0
    enable_backchannel=True,   # "yeah", "uh-huh" during user speech
    backchannel_frequency=0.6, # 0.0 to 1.0
    language="en-US",
    agent_name="Dani Moreau - D2M Concierge",
    # Interaction tuning
    responsiveness=0.9,              # 0-1, how fast to respond
    interruption_sensitivity=0.7,    # 0-1, how easily user can interrupt
    enable_dynamic_voice_speed=True, # Match user's speech rate
    enable_dynamic_responsiveness=True,
    # Silence handling
    reminder_trigger_ms=12000,       # 12s silence before reminder
    reminder_max_count=2,
    end_call_after_silence_ms=120000, # 2 min silence = end call
    max_call_duration_ms=1800000,     # 30 min max
    # Speech recognition
    boosted_keywords=["Dreams2Memories", "Dani", "Silversea", "Regent",
                       "Cunard", "Oceania", "Seabourn", "Viking",
                       "AmaWaterways", "Ponant", "Loucks", "concierge"],
    stt_mode="accurate",             # "fast" or "accurate"
    denoising_mode="noise-cancellation",
    normalize_for_speech=True,
    # Voicemail handling
    voicemail_message="Hi, this is Dani from Dreams2Memories Travel. "
                      "I'm sorry I missed you. Please leave a message "
                      "and we'll get back to you shortly.",
    # Post-call analysis
    post_call_analysis_data=[
        {
            "type": "string",
            "name": "caller_intent",
            "description": "What the caller wanted (booking inquiry, "
                          "trip question, complaint, general info)",
        },
        {
            "type": "string",
            "name": "client_name",
            "description": "The caller's name if mentioned",
        },
        {
            "type": "boolean",
            "name": "needs_followup",
            "description": "Whether the caller needs a callback from John",
        },
        {
            "type": "string",
            "name": "summary",
            "description": "Brief summary of the call in 1-2 sentences",
        },
    ],
    # Webhook
    webhook_url="https://api.d2mluxury.quest/webhook",
    webhook_events=["call_started", "call_ended", "call_analyzed"],
)
print(f"Agent ID: {agent.agent_id}")
```

---

## 8. LATENCY OPTIMIZATION

### Retell's Latency Claim

"As low as 600ms, measured from when the user stops speaking to when the AI agent begins responding."

### Latency Budget Breakdown (estimated)

| Component | Typical | Optimized | Notes |
|---|---|---|---|
| STT (speech-to-text) | 100-200ms | 80-150ms | `stt_mode: "fast"` helps |
| Network (Retell --> YOGA) | 30-80ms | 20-50ms | Cloudflare tunnel adds ~10ms |
| LLM (our Dani Engine) | 300-900ms | 200-500ms | Time to first token matters |
| Network (YOGA --> Retell) | 30-80ms | 20-50ms | Same path back |
| TTS (text-to-speech) | 100-200ms | 80-150ms | Platform/Cartesia fastest |
| **Total** | **560-1460ms** | **400-900ms** | |

### Optimization Strategies (Priority Order)

**1. Stream responses — never batch**
This is the single most important optimization. Retell starts TTS as soon as the first text chunk arrives. If you wait to generate the complete response before sending, you add the full LLM generation time to latency.

```python
# GOOD: Stream each token as it arrives
async for text in stream.text_stream:
    yield ResponseResponse(
        response_id=request.response_id,
        content=text,
        content_complete=False,
        end_call=False,
    )

# BAD: Wait for complete response
full_response = await generate_complete_response()
yield ResponseResponse(content=full_response, content_complete=True)
```

**2. Use a fast LLM**
Time to first token is what matters, not total generation time. Recommended models for voice:
- Claude 3.5 Haiku (fastest Anthropic)
- Claude Sonnet (good balance)
- GPT-4.1-mini (fastest OpenAI)
Avoid Opus-class models for voice — the quality difference is inaudible but latency cost is real.

**3. Keep prompts short**
Longer system prompts = longer time to first token. The voice Dani prompt should be under 500 tokens. Move knowledge base content to RAG, not the system prompt.

**4. Choose fast TTS**
Platform voices ($0.015/min) are optimized for conversational latency. ElevenLabs ($0.040/min) is higher quality but may add 50-100ms. Test both.

**5. Use `stt_mode: "fast"`**
Trades marginal transcription accuracy for lower latency. For conversational voice, "fast" is almost always correct enough.

**6. Set `responsiveness` high (0.8-1.0)**
Higher values make the agent respond sooner after the user pauses. Lower values wait longer (reduces interruption, increases perceived latency).

**7. Server proximity**
YOGA is in Colorado Springs. Retell's infrastructure is AWS-based. The ~30ms round-trip should be acceptable. If latency becomes an issue, consider deploying the WebSocket handler to a cloud instance closer to Retell's servers.

**8. Don't chain LLM calls**
A single LLM call per response. Never do: "Call LLM to classify intent, then call LLM to generate response." That doubles your LLM latency.

**9. Use `boosted_keywords`**
Pre-loading cruise line names, client names, and travel terms into STT improves accuracy and reduces correction loops.

### Latency Monitoring

Check actual latency in the Retell dashboard under agent details > "Estimated Latency." Features marked with a turtle icon add latency. The P90 target should be under 3 seconds.

---

## 9. PYTHON SDK REFERENCE

### Installation

```bash
pip install retell-sdk
# Or with async support:
pip install retell-sdk[aiohttp]
```

**Current version:** 5.22.1 (as of March 2026)
**Python requirement:** 3.9+
**License:** Apache-2.0

### Client Initialization

```python
from retell import Retell, AsyncRetell

# Synchronous
client = Retell(api_key="YOUR_API_KEY")

# Asynchronous
async_client = AsyncRetell(api_key="YOUR_API_KEY")

# With custom timeout/retries
client = Retell(
    api_key="YOUR_API_KEY",
    max_retries=2,    # Default: 2
    timeout=20.0,     # Default: 60s
)
```

### Core SDK Methods

#### Agent Management
```python
# Create agent
agent = client.agent.create(
    response_engine={"type": "custom-llm",
                     "llm_websocket_url": "wss://..."},
    voice_id="retell-Cimo",
)

# List agents
agents = client.agent.list()

# Get agent
agent = client.agent.retrieve(agent_id="...")

# Update agent
client.agent.update(agent_id="...", agent_name="Dani v2")

# Delete agent
client.agent.delete(agent_id="...")
```

#### Phone Number Management
```python
# Buy Retell number
number = client.phone_number.create(area_code=719)

# Import Twilio number
number = client.phone_number.import_(
    phone_number="+17195551234",
    termination_uri="trunk.pstn.twilio.com",
)

# List numbers
numbers = client.phone_number.list()

# Update number
client.phone_number.update(
    phone_number="+17195551234",
    inbound_agents=[{"agent_id": "...", "weight": 1.0}],
)

# Delete number
client.phone_number.delete(phone_number="+17195551234")
```

#### Call Operations
```python
# Make outbound phone call
call = client.call.create_phone_call(
    from_number="+17195551234",
    to_number="+17192910742",
    metadata={"purpose": "test_call"},
    retell_llm_dynamic_variables={
        "client_name": "John Loucks",
        "booking_ref": "SN-2026-001",
    },
)

# Create web call (for testing/portal)
web_call = client.call.create_web_call(
    agent_id="your_agent_id",
    metadata={"source": "d2m_portal"},
)
access_token = web_call.access_token  # For frontend connection

# Get call details
call = client.call.retrieve(call_id="...")

# List calls
calls = client.call.list()
```

#### Voice Management
```python
# List all available voices
voices = client.voice.list()
for v in voices:
    print(f"{v.voice_id}: {v.voice_name} ({v.provider}, {v.gender})")

# Clone a voice
voice = client.voice.clone(
    voice_name="Dani",
    voice_provider="elevenlabs",
    files=[open("sample.wav", "rb")],
)

# Get voice details
voice = client.voice.retrieve(voice_id="...")
```

### Webhook Signature Verification

```python
from retell import Retell

retell = Retell(api_key="YOUR_API_KEY")

is_valid = retell.verify(
    json.dumps(post_data, separators=(",", ":"), ensure_ascii=False),
    api_key="YOUR_API_KEY",
    signature=request.headers.get("X-Retell-Signature"),
)
```

### Error Handling

```python
from retell import Retell, BadRequestError, AuthenticationError, RateLimitError

client = Retell(api_key="YOUR_API_KEY")

try:
    agent = client.agent.create(...)
except AuthenticationError:
    print("Invalid API key")
except BadRequestError as e:
    print(f"Bad request: {e}")
except RateLimitError:
    print("Rate limited — back off")
except Exception as e:
    print(f"Unexpected: {e}")
```

### Response Objects

All responses are Pydantic models:
```python
agent = client.agent.create(...)
agent.agent_id          # string
agent.to_json()         # JSON string
agent.to_dict()         # Python dict
agent.model_fields_set  # Which fields were explicitly set
```

---

## 10. DEPLOYMENT ARCHITECTURE FOR YOGA

### Service Stack

```
YOGA (10.0.0.53)
├── thunderbird_api.py          :8766  (existing REST API)
├── dani_retell_server.py       :8780  (NEW — Retell WebSocket handler)
├── travel_mcp_server.py        :8765  (existing MCP server)
└── cloudflared tunnel
    ├── api.d2mluxury.quest  --> :8766
    ├── mcp.d2mluxury.quest  --> :8765
    └── voice.d2mluxury.quest --> :8780  (NEW tunnel route)
```

### Systemd Service File

```ini
# /etc/systemd/system/dani-retell.service
[Unit]
Description=Dani Voice Agent — Retell WebSocket Server
After=network.target thunderbird-api.service

[Service]
Type=exec
User=john
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/.venv/bin/uvicorn \
    dani_retell_server:app \
    --host 0.0.0.0 \
    --port 8780 \
    --workers 2
EnvironmentFile=/home/john/Thunderbird/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Cloudflare Tunnel Config Addition

Add to existing cloudflared config:

```yaml
# In existing tunnel config, add:
- hostname: voice.d2mluxury.quest
  service: http://localhost:8780
```

### Retell Agent Configuration

After deploying, set the Custom LLM WebSocket URL in Retell dashboard or via API:

```
wss://voice.d2mluxury.quest/llm-websocket
```

### Implementation Phases

| Phase | Scope | Timeline |
|---|---|---|
| **Phase 1: MVP** | Signup, buy number, platform voice, direct Anthropic LLM, basic greeting/conversation | 1-2 days |
| **Phase 2: Integration** | Connect to Thunderbird API, client lookup by phone, dossier context injection | 3-5 days |
| **Phase 3: Voice** | Clone custom Dani voice, tune voice settings, latency optimization | 2-3 days |
| **Phase 4: Production** | Webhook logging, Telegram C2 notifications, post-call analysis to dossiers, call recording | 3-5 days |
| **Phase 5: Intelligence** | Full Dani Engine integration (Aggregate/Artist/Advocate), voice ledger rules, COS review gate for sensitive calls | 5-7 days |

---

## 11. INFORMATION GAPS

Items I could not verify from available documentation. Confidence level noted.

| Gap | Impact | Confidence in Gap |
|---|---|---|
| Voice cloning audio requirements (format, duration, quality) | Need to know before recording voice samples | HIGH — docs don't specify |
| Exact voice IDs for platform voices | Must browse dashboard to find right Dani voice | MODERATE — catalog is in dashboard, not docs |
| Latency by component (STT/TTS breakdown) | My budget breakdown is estimated, not measured | HIGH — docs give total only |
| Retell IP allowlist completeness | `100.20.5.228` is documented but may be incomplete | MODERATE — need to verify |
| WebSocket connection auth | No API key or token on the WS connection itself | HIGH — may rely on URL obscurity |
| Concurrent WebSocket connections limit | 20 free concurrent calls, but WS connection behavior at scale unclear | LOW — not relevant at our volume |
| ElevenLabs voice quality vs Platform for phone | Subjective, need A/B testing | HIGH — must test ourselves |
| Retell data retention defaults | Docs say "forever" default, unclear GDPR implications | MODERATE — review before production |
| Custom LLM response timeout | How long Retell waits before dropping WS if we're slow | HIGH — not documented |
| Twilio per-minute cost on SIP trunk | Twilio charges separately; need to add to our cost model | MODERATE — depends on Twilio plan |

### Recommended Next Actions

1. **Sign up at dashboard.retellai.com** — use the $10 free credit to test immediately
2. **Browse platform voices** — find a warm, female, American-accented voice for Dani Phase 1
3. **Deploy the MVP WebSocket server** on YOGA and expose via cloudflared
4. **Test with web call first** — no phone number needed, faster iteration
5. **Record voice samples** for cloning once we're happy with the conversation quality

---

## SOURCES

- Retell AI Pricing: https://www.retellai.com/pricing (fetched 2026-03-20)
- Retell API Reference — Create Agent: https://docs.retellai.com/api-references/create-agent
- Retell API Reference — LLM WebSocket: https://docs.retellai.com/api-references/llm-websocket
- Retell API Reference — Import Phone Number: https://docs.retellai.com/api-references/import-phone-number
- Retell API Reference — Create Phone Number: https://docs.retellai.com/api-references/create-phone-number
- Retell API Reference — Create Phone Call: https://docs.retellai.com/api-references/create-phone-call
- Retell API Reference — Create Web Call: https://docs.retellai.com/api-references/create-web-call
- Retell API Reference — Clone Voice: https://docs.retellai.com/api-references/clone-voice
- Retell API Reference — List Voices: https://docs.retellai.com/api-references/list-voices
- Retell Custom LLM Overview: https://docs.retellai.com/integrate-llm/overview
- Retell Custom LLM Integration: https://docs.retellai.com/integrate-llm/integrate-llm
- Retell Custom LLM Best Practices: https://docs.retellai.com/integrate-llm/llm-best-practice
- Retell WebSocket Server Setup: https://docs.retellai.com/integrate-llm/setup-websocket-server
- Retell Custom Telephony: https://docs.retellai.com/deploy/custom-telephony
- Retell Twilio Setup: https://docs.retellai.com/deploy/twilio
- Retell Latency Troubleshooting: https://docs.retellai.com/reliability/troubleshoot-latency
- Retell Estimated Latency: https://docs.retellai.com/reliability/check-estimated-latency
- Retell TTS Provider Comparison: https://docs.retellai.com/build/tts-provider-comparison
- Retell Platform Voices: https://docs.retellai.com/build/platform-voices
- Retell Python SDK: https://pypi.org/project/retell-sdk/ (v5.22.1)
- GitHub Demo: https://github.com/RetellAI/retell-custom-llm-python-demo
- Retell Full Docs Index: https://docs.retellai.com/llms.txt (346 pages)

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)*
*Dreams2Memories Travel, LLC*
