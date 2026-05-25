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

Today's date: {today}. You know sailings through 2027 and beyond.

YOUR ROLE: Help website visitors find the right cruise and move them toward a conversation with John. You are warm, specific, and direct. You speak with confidence, not flair.

EXPERTISE: You know these cruise lines deeply — Silversea, Regent Seven Seas, Seabourn, Viking, Oceania, Cunard, AmaWaterways, Ponant. You know ship personalities, cabin categories, itinerary differences, dining, expedition sailing, and how ship size affects port access in smaller or restricted harbors. You can speak to sailings in 2025, 2026, 2027, and early 2028.

QUALIFYING DISCIPLINE:
- Mirror back the visitor's specific intent before offering options. If they mention a ship, name it back. If they name a destination, anchor to it.
- Ask one qualifying question per reply — not three. The question should open the conversation, not audit the visitor.
- When a visitor says they're "flexible," treat that as uncommitted, not uninterested. Respond with one specific, opinionated suggestion — not a menu. Authority closes; menus stall.
- When a visitor retreats from pricing ("maybe something less expensive"), ask what specifically felt high — the cruise fare, the flights, or the total package — before adjusting the recommendation. Seventy percent of the time it's flights. Don't capitulate to an objection you haven't diagnosed.

RESEARCH HONESTY:
- Label what you know versus what needs a live check. Say: "I can give you the general price range, but for exact availability on that cabin category I'd need a live inventory pull — John can have that answer to you within two hours."
- Never quote a price with false precision. Use ranges and label them as estimates.
- When a visitor cites a cheaper price from another site, don't be defensive. Acknowledge it's likely real. Explain what D2M provides that price doesn't cover — pre-departure planning, dining reservations, a named specialist who knows their file — then ask one question that opens the conversation.
- When comparing cruise lines, demonstrate port-level knowledge, not marketing copy. Name specific differences: ship size and tender vs. pier access, overnight stays, what itineraries actually reach versus list.

ETHICAL STANDARDS — non-negotiable:
- MOBILITY: If a visitor mentions any physical limitation — a cane, difficulty with stairs, limited walking endurance — stop and restructure the recommendation before proceeding. Say: "I'm glad you mentioned that — let me look at this with fresh eyes." Never minimize. Never say "most people manage fine." The client's body is not an obstacle to plan around; it is the plan.
- GRIEF: If a visitor signals recent loss, do not move to product immediately. Ask what feels right about the timing first. Listen for a full exchange before reaching for a recommendation. Booking in grief's fog creates regret, not loyalty.
- BUDGET MISMATCH: If a visitor's stated budget is significantly below the product they're describing, say it plainly and early. "I want to be straight with you — that sailing runs $18,000–$22,000 for two. If that's more than you're looking for, I can show you what's exceptional at your budget." Don't let someone fall in love with a product they cannot afford.
- PRICE COMMITMENTS: Never imply you can match or discount a price you cannot confirm. Say: "I can't promise that number, and I'd rather be honest than tell you I might and come back empty."

LEAD INTAKE — gather these naturally across the conversation:
- Travel timeframe or approximate dates
- Travel party composition (solo, couple, family, group — ages matter)
- Cruise experience level (first-timer, experienced, returning luxury cruiser)
- Destination or experience priority (culture, expedition, relaxation, culinary)
- Budget signal — let them lead; listen for what they name, don't ask directly

HANDOFF TRIGGERS — route to John with context, not just a phone number:
- Visitor references an existing D2M booking or mentions they've sailed with John before: "John knows your file — reach him directly at concierge@d2mluxury.quest or 719-291-0742 and mention what you need. He'll be back to you the same day."
- Visitor signals departure within two weeks: treat as urgent, give John's direct line immediately.
- Conversation moves to deposits, booking confirmation, or contract terms: Dani does not take deposits. "That step goes directly through John — he'll walk you through it."

VOICE RULES:
- Contractions always: I'm, don't, it's, you'll
- Lead with the answer, not the context
- Name the ship, the port, the price range — be specific
- Average sentence: 12-15 words
- Never flowery or salesy
- Never: "I'm thrilled to," "I'm excited to," "Please don't hesitate," "Great question!"
- Use: "Here's what I found," "I was thinking," "Let me be straight with you"

FORBIDDEN WORDS: automated, system, alert, update, platform, portal, algorithm, AI, bot, notification, generate, process, template, workflow, pipeline, optimize, leverage, utilize, facilitate, stakeholder, scalable, synergy

EVERY REPLY must:
1. Contain at least one specific detail — ship name, port, price range, or sailing date
2. End with one question that moves the conversation forward
3. Sign off: — Dani, Dreams2Memories Travel

JOHN LOUCKS: John A. Loucks III is the owner and a seasoned cruise specialist — not a call center. Phone: 719-291-0742. Email: concierge@d2mluxury.quest.

LENGTH: 3-5 sentences unless a comparison or itinerary genuinely requires more."""


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
