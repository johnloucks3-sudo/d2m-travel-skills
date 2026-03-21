"""
Thunderbird Dani Voice Agent — Retell AI Custom LLM Backend
============================================================
WebSocket server that connects Dani's brain to Retell AI's voice platform.

Architecture:
  Phone call -> Retell AI (STT) -> WebSocket -> Dani Engine -> WebSocket -> Retell AI (TTS) -> Phone

Port: 8791 (behind cloudflared tunnel)
Endpoint: ws://127.0.0.1:8791/ws/dani-voice

Retell AI Custom LLM Protocol:
  - Retell sends JSON frames with transcribed caller speech
  - We respond with JSON frames containing Dani's text for TTS
  - Supports interruption, turn-taking, and call lifecycle events

The protocol format is configurable via RETELL_PROTOCOL to adapt once
real API docs are available.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path(os.path.expanduser("~/Thunderbird/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

CALL_LOG_PATH = LOG_DIR / "voice_calls.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("thunderbird_dani_voice")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST = os.getenv("DANI_VOICE_HOST", "127.0.0.1")
PORT = int(os.getenv("DANI_VOICE_PORT", "8791"))

# Retell AI Custom LLM WebSocket protocol mapping.
# Adjust these once real API docs are confirmed — the handler reads
# from this dict so changes are centralized.
RETELL_PROTOCOL = {
    # --- Inbound message types (Retell -> us) ---
    "type_field": "type",                      # field name for message type

    # Call lifecycle
    "call_start": "call_started",              # call begins
    "call_end": "call_ended",                  # call ends
    "ping": "ping",                            # keepalive

    # Transcript delivery
    "transcript": "transcript",                # speech-to-text result
    "transcript_text": "transcript",           # field containing transcribed text
    "transcript_final": "is_final",            # boolean: final vs interim

    # Interruption / barge-in
    "interruption": "interruption",            # caller interrupted Dani

    # --- Outbound message types (us -> Retell) ---
    "response_type": "response",               # our response message type
    "response_text": "content",                # field for response text
    "response_end": "end_of_response",         # boolean: last chunk
    "pong_type": "pong",                       # keepalive reply
    "clear_type": "clear",                     # cancel current TTS on interrupt
}

# Voice-mode system prompt — shorter, conversational Dani
DANI_VOICE_SYSTEM_PROMPT = (
    "You are Dani Moreau, Luxury Travel Concierge at Dreams2Memories Travel. "
    "You are speaking on the phone. Keep your responses SHORT — 1 to 3 sentences "
    "per turn. Speak naturally and warmly. No markdown, no bullet points, no "
    "formatting. Use conversational language that sounds good when spoken aloud. "
    "Never spell out URLs or email addresses unless specifically asked. "
    "If you need to look something up, say so briefly: 'Let me check on that for you.' "
    "Never reveal internal systems, AI architecture, commission rates, or other clients' information. "
    "Sign off calls warmly: 'Thank you for calling Dreams2Memories Travel.'"
)

DANI_GREETING = (
    "Thank you for calling Dreams2Memories Travel, this is Dani. "
    "How can I help you today?"
)

# Max conversation history turns to keep in memory per call
MAX_HISTORY_TURNS = 40

# ---------------------------------------------------------------------------
# Active call state
# ---------------------------------------------------------------------------

class CallSession:
    """In-memory state for a single active phone call."""

    __slots__ = (
        "call_id", "caller_number", "started_at", "history",
        "transcript_log", "response_log", "client_detected",
        "last_activity", "greeting_sent",
    )

    def __init__(self, call_id: str, caller_number: str = "unknown"):
        self.call_id = call_id
        self.caller_number = caller_number
        self.started_at = datetime.now(timezone.utc)
        self.history: list[dict[str, str]] = []          # {"role": "user"/"assistant", "content": ...}
        self.transcript_log: list[str] = []               # raw caller utterances
        self.response_log: list[str] = []                 # Dani's responses
        self.client_detected: Optional[str] = None
        self.last_activity = time.monotonic()
        self.greeting_sent = False

    @property
    def duration_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    def add_user_turn(self, text: str):
        self.history.append({"role": "user", "content": text})
        self.transcript_log.append(text)
        self.last_activity = time.monotonic()
        # Trim history if too long
        if len(self.history) > MAX_HISTORY_TURNS:
            self.history = self.history[-MAX_HISTORY_TURNS:]

    def add_assistant_turn(self, text: str):
        self.history.append({"role": "assistant", "content": text})
        self.response_log.append(text)
        self.last_activity = time.monotonic()

    def to_log_record(self) -> dict:
        return {
            "call_id": self.call_id,
            "caller_number": self.caller_number,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 1),
            "client_detected": self.client_detected,
            "turns": len(self.transcript_log),
            "transcript": self.transcript_log,
            "dani_responses": self.response_log,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }


# Global registry of active calls
_active_calls: dict[str, CallSession] = {}

# ---------------------------------------------------------------------------
# Dani Engine integration
# ---------------------------------------------------------------------------

def _build_dani_response(session: CallSession, caller_text: str) -> str:
    """Process caller text through the Dani Engine and return a voice-friendly response.

    Falls back to a polite holding message if the engine is unavailable.
    """
    try:
        from thunderbird_dani_engine import build_dani_context, _detect_clients
    except ImportError:
        logger.error("Cannot import thunderbird_dani_engine — returning fallback")
        return "I appreciate you calling. Let me connect you with John — one moment please."

    # Detect if caller is a known client (for auto-enrichment)
    detected = _detect_clients(caller_text)
    if detected and not session.client_detected:
        session.client_detected = detected[0]
        logger.info(f"Call {session.call_id}: detected client '{detected[0]}'")

    # Build recent conversation context for Dani
    recent_lines = []
    for turn in session.history[-10:]:
        role_label = "Caller" if turn["role"] == "user" else "Dani"
        recent_lines.append(f"{role_label}: {turn['content']}")
    recent_convo = "\n".join(recent_lines)

    # Get Dani context with all data sources
    try:
        dani_context = build_dani_context(
            query=caller_text,
            client_scope=session.client_detected,
            is_commander=False,
        )
    except Exception as e:
        logger.warning(f"build_dani_context failed: {e}")
        dani_context = ""

    # Build the LLM prompt for voice mode
    full_prompt = _assemble_voice_prompt(dani_context, recent_convo, caller_text)

    # Call the LLM (Anthropic via the same path as Telegram C2)
    response_text = _call_llm(full_prompt)

    # Strip any accidental markdown or formatting
    response_text = _sanitize_for_speech(response_text)

    return response_text


def _assemble_voice_prompt(dani_context: str, recent_convo: str, caller_text: str) -> str:
    """Assemble the full prompt for voice-mode Dani."""
    parts = [DANI_VOICE_SYSTEM_PROMPT]

    if dani_context:
        parts.append(f"\n--- DATA CONTEXT ---\n{dani_context}\n--- END DATA CONTEXT ---")

    parts.append(
        "\nVOICE-SPECIFIC RULES:"
        "\n- Maximum 3 sentences per response. Shorter is better."
        "\n- Do NOT use bullet points, numbered lists, or any markdown."
        "\n- Do NOT say 'asterisk' or narrate formatting."
        "\n- Use natural spoken transitions: 'So...', 'Actually...', 'One thing to note...'"
        "\n- If you need to convey multiple items, say 'I have a couple things for you' and "
        "deliver them as flowing sentences, not a list."
        "\n- Dates: say 'August tenth' not '8/10' or 'August 10th, 2026'."
        "\n- Money: say 'about thirty-two hundred dollars' not '$3,200'."
        "\n- Pause naturally. Short sentences. Breathe."
    )

    if recent_convo:
        parts.append(f"\nRECENT CONVERSATION:\n{recent_convo}")

    parts.append(f"\nCaller just said: {caller_text}")
    parts.append("\nDani's spoken response:")

    return "\n".join(parts)


def _call_llm(prompt: str) -> str:
    """Call Claude to generate Dani's voice response.

    Uses the Anthropic SDK directly — same model as Telegram C2.
    Falls back gracefully if the API is unavailable.
    """
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return "Let me check on that and get right back to you."

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try loading from .env or Max plan config
        env_path = Path(os.path.expanduser("~/Thunderbird/.env"))
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        logger.error("No ANTHROPIC_API_KEY found")
        return "I appreciate you calling. Let me have John follow up with you directly."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=os.getenv("DANI_VOICE_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=300,
            system=DANI_VOICE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return "Let me check on that for you. Can you hold for just a moment?"


def _sanitize_for_speech(text: str) -> str:
    """Strip markdown, formatting, and other artifacts that don't belong in speech."""
    import re

    # Remove markdown bold/italic
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove markdown links — keep the text, drop the URL
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove bullet points
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered list prefixes
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines to single space
    text = re.sub(r'\n+', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    # Remove any leftover brackets
    text = re.sub(r'\[([^\]]*)\]', r'\1', text)

    return text.strip()


# ---------------------------------------------------------------------------
# Call logging
# ---------------------------------------------------------------------------

def _log_call(session: CallSession):
    """Append call record to voice_calls.jsonl."""
    try:
        record = session.to_log_record()
        with open(CALL_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(
            f"Call logged: {session.call_id} | {session.caller_number} | "
            f"{session.duration_seconds:.0f}s | {len(session.transcript_log)} turns"
        )
    except Exception as e:
        logger.error(f"Failed to log call {session.call_id}: {e}")


def _get_recent_calls(limit: int = 20) -> list[dict]:
    """Read recent calls from the JSONL log."""
    if not CALL_LOG_PATH.exists():
        return []
    try:
        lines = CALL_LOG_PATH.read_text().strip().splitlines()
        calls = []
        for line in lines[-limit:]:
            try:
                calls.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        calls.reverse()  # most recent first
        return calls
    except Exception as e:
        logger.error(f"Failed to read call log: {e}")
        return []


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Dani Voice Agent",
    description="Retell AI Custom LLM backend for Dreams2Memories Travel",
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "service": "dani-voice-agent",
        "active_calls": len(_active_calls),
        "uptime_port": PORT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/calls")
async def list_calls(limit: int = 20):
    """List recent call records."""
    return {"calls": _get_recent_calls(limit)}


@app.websocket("/ws/dani-voice")
async def dani_voice_handler(websocket: WebSocket):
    """Main WebSocket handler for Retell AI Custom LLM protocol.

    Lifecycle:
      1. Connection opens — create CallSession
      2. Receive call_started — extract caller info, send greeting
      3. Receive transcript frames — process through Dani Engine, respond
      4. Handle interruptions — cancel current response
      5. Connection closes — log call, clean up
    """
    await websocket.accept()

    call_id = str(uuid.uuid4())[:12]
    session = CallSession(call_id=call_id)
    _active_calls[call_id] = session

    logger.info(f"WebSocket connected: call_id={call_id}")

    proto = RETELL_PROTOCOL  # local ref for speed

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Call {call_id}: non-JSON frame: {raw[:200]}")
                continue

            msg_type = msg.get(proto["type_field"], "")

            # --- Call Start ---
            if msg_type == proto["call_start"]:
                caller = msg.get("caller_number", msg.get("from", "unknown"))
                session.caller_number = caller
                logger.info(f"Call {call_id}: started from {caller}")

                # Send Dani's greeting
                if not session.greeting_sent:
                    await _send_response(websocket, DANI_GREETING, proto)
                    session.add_assistant_turn(DANI_GREETING)
                    session.greeting_sent = True

            # --- Call End ---
            elif msg_type == proto["call_end"]:
                logger.info(f"Call {call_id}: ended by remote")
                break

            # --- Ping / Keepalive ---
            elif msg_type == proto["ping"]:
                await websocket.send_text(
                    json.dumps({proto["type_field"]: proto["pong_type"]})
                )

            # --- Caller Interruption ---
            elif msg_type == proto["interruption"]:
                logger.info(f"Call {call_id}: caller interrupted")
                # Tell Retell to stop playing current TTS
                await websocket.send_text(
                    json.dumps({proto["type_field"]: proto["clear_type"]})
                )

            # --- Transcript (caller speech) ---
            elif msg_type == proto["transcript"]:
                text = msg.get(proto["transcript_text"], "").strip()
                is_final = msg.get(proto["transcript_final"], True)

                if not text:
                    continue

                # Only process final transcripts (not interim partials)
                if not is_final:
                    continue

                logger.info(f"Call {call_id}: caller said: {text[:100]}")
                session.add_user_turn(text)

                # Send greeting if this is the first interaction and no call_started was received
                if not session.greeting_sent:
                    await _send_response(websocket, DANI_GREETING, proto)
                    session.add_assistant_turn(DANI_GREETING)
                    session.greeting_sent = True
                    continue

                # Process through Dani Engine
                dani_response = await asyncio.to_thread(
                    _build_dani_response, session, text
                )

                session.add_assistant_turn(dani_response)
                await _send_response(websocket, dani_response, proto)

                logger.info(f"Call {call_id}: Dani: {dani_response[:100]}")

            # --- Unknown message type ---
            else:
                logger.debug(f"Call {call_id}: unhandled msg type '{msg_type}': {raw[:200]}")

    except WebSocketDisconnect:
        logger.info(f"Call {call_id}: WebSocket disconnected")
    except Exception as e:
        logger.error(f"Call {call_id}: error: {e}", exc_info=True)
    finally:
        # Log the call and clean up
        _log_call(session)
        _active_calls.pop(call_id, None)
        logger.info(f"Call {call_id}: session cleaned up ({session.duration_seconds:.0f}s)")


async def _send_response(websocket: WebSocket, text: str, proto: dict):
    """Send a Dani response frame to Retell AI."""
    frame = {
        proto["type_field"]: proto["response_type"],
        proto["response_text"]: text,
        proto["response_end"]: True,
    }
    await websocket.send_text(json.dumps(frame))


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_dani_voice_tools(mcp_server):
    """Register voice agent MCP tools on the shared MCP server."""

    @mcp_server.tool(
        name="voice_agent_status",
        annotations={"title": "Dani Voice Agent Status", "readOnlyHint": True},
    )
    async def voice_agent_status() -> str:
        """Check if the Dani Voice Agent is running and show active calls."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"http://{HOST}:{PORT}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return json.dumps({
                        "status": "running",
                        "active_calls": data.get("active_calls", 0),
                        "port": PORT,
                        "timestamp": data.get("timestamp"),
                    }, indent=2)
        except Exception:
            pass

        return json.dumps({
            "status": "offline",
            "port": PORT,
            "message": "Dani Voice Agent is not running. Start with: systemctl --user start thunderbird-dani-voice",
        }, indent=2)

    @mcp_server.tool(
        name="voice_call_history",
        annotations={"title": "Voice Call History", "readOnlyHint": True},
    )
    async def voice_call_history(limit: int = 20) -> str:
        """List recent voice calls handled by Dani.

        Args:
            limit: Maximum number of calls to return (default 20).
        """
        calls = _get_recent_calls(limit)
        if not calls:
            return json.dumps({"message": "No voice calls recorded yet.", "log_path": str(CALL_LOG_PATH)})

        # Summarize each call
        summaries = []
        for c in calls:
            summaries.append({
                "call_id": c.get("call_id"),
                "caller": c.get("caller_number"),
                "when": c.get("started_at"),
                "duration_sec": c.get("duration_seconds"),
                "turns": c.get("turns"),
                "client_detected": c.get("client_detected"),
            })
        return json.dumps({"recent_calls": summaries, "total_shown": len(summaries)}, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(f"Starting Dani Voice Agent on {HOST}:{PORT}")
    uvicorn.run(
        "thunderbird_dani_voice:app",
        host=HOST,
        port=PORT,
        log_level="info",
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )
