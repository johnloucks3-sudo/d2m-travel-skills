"""
/concierge — Dani AI Concierge chat page
GET  /concierge    → chat UI
POST /api/concierge → {message, history[]} → {reply}

Auth: Claude Max OAuth via ~/.claude/.credentials.json
Model: claude-haiku-4-5-20251001
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

CLAUDE_BIN = "/home/john/.local/bin/claude"
CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
LEADS_PATH = Path(__file__).parent.parent / "concierge_leads.jsonl"
MODEL = "claude-haiku-4-5-20251001"
HISTORY_TURNS = 6  # keep last N turns (user+assistant pairs)
TIMEOUT_SECONDS = 30

def _build_system_prompt() -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return f"""You are Dani, the personal travel concierge for Dreams2Memories Travel, LLC — a luxury cruise specialty agency owned by John A. Loucks III in Colorado Springs, Colorado.

Today's date: {today}. You are aware of sailings and availability through 2027 and beyond.

Your role: Help website visitors discover the perfect cruise vacation. You are warm, knowledgeable, and direct. You speak with confidence, not flair.

EXPERTISE: You know these cruise lines deeply — Silversea, Regent Seven Seas, Seabourn, Viking, Oceania, Cunard, AmaWaterways, Ponant. You understand ship personalities, cabin categories, itinerary differences, dining, and expedition sailing. You can speak to sailings in 2025, 2026, 2027, and early 2028.

SAILING KNOWLEDGE: You know current and upcoming sailings. When a visitor asks about availability, suggest specific itineraries with realistic date ranges (e.g., "Silversea has a Japan to Alaska crossing in April–May 2026, and similar Pacific crossings in 2027"). If you don't know exact inventory, say so honestly and offer to research it — "I'd want to check live availability on that one. John can get you exact pricing within the hour."

VOICE RULES:
- Use contractions naturally (I'm, don't, it's, you'll)
- Average sentence length: 12-15 words
- Lead with the answer, not context
- Be specific: name the ship, the port, the price range
- Never flowery or salesy
- Never say "I'm thrilled to" or "I'm excited to" or "Please don't hesitate"
- Say: "Here's what I found", "I was thinking", "Let me know if I can help"

FORBIDDEN WORDS (never use these): automated, system, alert, update, platform, portal, algorithm, AI, bot, notification, generate, process, template, workflow, pipeline, optimize, leverage, utilize, facilitate, stakeholder, scalable, synergy

EVERY REPLY must:
1. Contain at least one specific detail — a ship name, port, price range, or sailing date
2. End with a question that moves toward booking intent (e.g., "What dates are you thinking?" or "Is this a couple's trip or a group?")
3. Sign off: — Dani, Dreams2Memories Travel

JOHN LOUCKS: If a visitor wants to speak directly with someone, connect them with John A. Loucks III personally. Phone: 719-291-0742. Email: concierge@d2mluxury.quest. He is the owner and a seasoned cruise specialist — not a call center.

LENGTH: Keep replies to 3-5 sentences unless a comparison or itinerary genuinely requires more. Trust the visitor to follow."""


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ConciergeRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


def _load_oauth_token() -> str | None:
    """Load Max OAuth access token from credentials file."""
    try:
        if not CREDS_PATH.exists():
            return None
        creds = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
        return creds.get("claudeAiOauth", {}).get("accessToken")
    except Exception as exc:
        logger.warning("Could not read OAuth credentials: %s", exc)
        return None


def _build_prompt(message: str, history: list[ChatMessage]) -> str:
    """
    Build a single prompt string for claude -p.
    Includes system prompt, last HISTORY_TURNS turns, and the new user message.
    """
    # Trim history to last HISTORY_TURNS pairs
    turns = list(history)
    # Each turn is one message (user or assistant); HISTORY_TURNS*2 messages max
    if len(turns) > HISTORY_TURNS * 2:
        turns = turns[-(HISTORY_TURNS * 2):]

    parts: list[str] = [_build_system_prompt(), ""]

    for turn in turns:
        role_label = "Visitor" if turn.role == "user" else "Dani"
        parts.append(f"{role_label}: {turn.content}")

    parts.append(f"Visitor: {message}")
    parts.append("Dani:")

    return "\n".join(parts)


def _call_claude(prompt: str) -> str:
    """
    Call claude binary synchronously and return stdout.
    Raises RuntimeError on non-zero exit or timeout.
    """
    token = _load_oauth_token()
    env = dict(os.environ)

    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        # Remove API key to force OAuth path
        env.pop("ANTHROPIC_API_KEY", None)

    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--model", MODEL, "--output-format", "text"],
            capture_output=True,
            text=True,
            env=env,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude response timed out. Please try again.")
    except FileNotFoundError:
        raise RuntimeError("Claude binary not found at expected path.")

    if result.returncode != 0:
        stderr_excerpt = (result.stderr or "")[:200]
        raise RuntimeError(f"Claude returned exit code {result.returncode}: {stderr_excerpt}")

    reply = result.stdout.strip()
    if not reply:
        raise RuntimeError("Empty response from Claude.")

    return reply


def _extract_lead(message: str) -> dict[str, str]:
    """
    Attempt to extract name and/or email from a user message.
    Returns a dict with any found fields (may be empty).
    """
    lead: dict[str, str] = {}

    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", message)
    if email_match:
        lead["email"] = email_match.group(0)

    name_match = re.search(
        r"\bI(?:'m| am) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b", message
    )
    if name_match:
        lead["name"] = name_match.group(1)

    return lead


def _log_lead(lead: dict[str, str], message: str) -> None:
    """Append lead data to JSONL file."""
    try:
        LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "message": message,
            **lead,
        }
        with LEADS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("Failed to log lead: %s", exc)


@router.get("/concierge", response_class=HTMLResponse)
async def concierge_page(request: Request) -> Any:
    return templates.TemplateResponse("concierge.html", {"request": request})


@router.post("/api/concierge")
def concierge_api(payload: ConciergeRequest) -> JSONResponse:
    message = (payload.message or "").strip()
    if not message:
        return JSONResponse({"reply": "I didn't catch that — what destination are you thinking about?"})

    # Lead capture from user message
    lead = _extract_lead(message)
    if lead:
        _log_lead(lead, message)

    try:
        prompt = _build_prompt(message, payload.history)
        reply = _call_claude(prompt)
    except RuntimeError as exc:
        logger.error("Concierge API error: %s", exc)
        reply = (
            "Something went sideways on my end — sorry about that. "
            "You can reach John directly at concierge@d2mluxury.quest or 719-291-0742. "
            "He'll get back to you same day.\n\n— Dani, Dreams2Memories Travel"
        )
    except Exception as exc:
        logger.exception("Unexpected concierge error: %s", exc)
        reply = (
            "I ran into a technical issue. "
            "John is always reachable at concierge@d2mluxury.quest or 719-291-0742.\n\n"
            "— Dani, Dreams2Memories Travel"
        )

    return JSONResponse({"reply": reply})
