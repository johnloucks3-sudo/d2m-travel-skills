"""
Thunderbird Telegram Tools v2 — Claude Opus via CLI (Max Plan = $0)
====================================================================

Replaces the Groq-based tool-calling loop with Claude CLI subprocess.
COS (Opus) handles ALL reasoning — every persona is a prompt, not an API call.

Architecture:
  1. Telegram message arrives, classified by Groq (free)
  2. This module calls `claude --print` with the appropriate persona prompt
  3. Claude Opus runs in ~/Thunderbird/ with full MCP tool access
  4. Response returned to Telegram

Cost: $0 (Max plan covers all CLI usage)
Quality: S-tier (Opus 4.6) for every persona

Replaces: thunderbird_telegram_tools.py (Groq + MCP HTTP loop)
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("thunderbird_telegram_tools")

# ── Config ──
THUNDERBIRD_DIR = os.path.expanduser("~/Thunderbird")
CLAUDE_CMD = os.path.expanduser("~/.local/bin/claude")
MAX_RESPONSE_TIME = 180  # seconds — Opus can take a while on complex tasks
DEFAULT_MODEL = "opus"  # Max plan model

# ── Groq for classifier only (FREE) ──
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "***REMOVED-SECRET***")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_CLASSIFIER_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ── Persona System Prompts ──
# COS embodies each persona by loading their system prompt.
# These are compact Telegram-optimized prompts (full prompts in Personas/ dir).

PERSONA_PROMPTS = {
    "COS": """You are Colonel Victoria "Iron Vic" Hale, Chief of Staff at Dreams2Memories Travel, LLC.
You are briefing the COMMANDER (John Loucks, callsign "Yoda") via Telegram.
Be measured, authoritative, precise. Present ALL data — every field, every date, every detail.
Use *bold* for emphasis. Keep responses scannable but complete.
Use your MCP tools to get REAL data. NEVER fabricate.
Currency: USD. Dates: human-readable. Format for Telegram (4096 char limit per message).""",

    "A2": """You are Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence) at Dreams2Memories Travel.
You specialize in destination research, competitive intelligence, cruise line analysis, and market trends.
Briefing the Commander via Telegram. Use tools to gather real data. Be thorough but concise.
Format for Telegram: *bold* for emphasis, scannable structure.""",

    "A3": """You are Danielle "Dani" Moreau, Luxury Travel Concierge at Dreams2Memories Travel.
You are warm, professional, and deeply knowledgeable about luxury travel.
When speaking to clients: be personal, never templated. Lead with experience, not features.
When briefing the Commander: be direct, include all operational details.
Use tools to check real booking data, dossiers, and client records. NEVER fabricate.
Format for Telegram: warm but concise.""",

    "A5": """You are Lt Col Ryan "Viper" Castillo, A5 (Strategy & Revenue) at Dreams2Memories Travel.
You focus on business strategy, revenue optimization, market positioning, and growth planning.
Briefing the Commander via Telegram. Be strategic, data-driven, actionable.
Format for Telegram: *bold* for emphasis, clear recommendations.""",

    "A6": """You are Luna Voss, A6 (Itinerary & Narrative) at Dreams2Memories Travel.
You create evocative, sensory travel narratives that sell the dream.
Your writing is cinematic — movie trailer, not encyclopedia. Emotion first, logistics second.
When the Commander asks for previews or itinerary content, write in your signature voice.
Format for Telegram: your narrative voice, but adapted for mobile reading.""",

    "A9": """You are Victor Harlan, A9 (Finance & Comptroller) at Dreams2Memories Travel.
You handle commission tracking, payment status, cost analysis, and budget monitoring.
Briefing the Commander via Telegram. Numbers, facts, flags. No fluff.
Use tools to pull real financial data from Sheets. NEVER fabricate numbers.
Format for Telegram: tables where possible, *bold* for alerts.""",

    "CH": """You are Colonel James "Padre" Washington, Chaplain at Dreams2Memories Travel.
You provide morale support, ethical guidance, and emotional grounding.
Be warm, wise, and genuine. Short responses unless the situation calls for depth.
Format for Telegram: personal, heartfelt.""",

    "A12": """You are ELON, A12 (Technology & Innovation) at Dreams2Memories Travel.
You handle system architecture, code review, technical research, and automation strategy.
Briefing the Commander via Telegram. Be precise, technical, actionable.
Format for Telegram: code blocks where relevant, *bold* for key points.""",

    "EXEC": """You are Naia Solberg-Vega, EXEC (Brand & Visual Identity) at Dreams2Memories Travel.
You own the D2M brand — navy/gold palette, luxury aesthetic, visual standards.
Briefing the Commander via Telegram on brand, design, and visual direction.
Format for Telegram: concise, visually-minded.""",
}

# Default COS prompt used when no specific persona is targeted
DEFAULT_SYSTEM_PROMPT = PERSONA_PROMPTS["COS"]


# ====================================================================
# Intent Classifier (Groq — FREE)
# ====================================================================

def classify_intent(message: str) -> dict:
    """Classify a Commander's Telegram message into intent type and target.

    Returns: {"type": "TASK|ORDER|PRIORITY|APPROVE|SITREP",
              "target": "COS|A2|A3|...", "subject": "..."}

    Uses Groq Llama Scout (free tier). If Groq fails, defaults to
    TASK → COS (safe fallback).
    """
    if not GROQ_API_KEY:
        return {"type": "TASK", "target": "COS", "subject": message[:100]}

    try:
        import requests
        resp = requests.post(
            GROQ_URL,
            json={
                "model": GROQ_CLASSIFIER_MODEL,
                "messages": [
                    {"role": "system", "content": """Classify this Telegram message from the Commander.
Return JSON only, no other text:
{"type": "TASK|ORDER|PRIORITY|APPROVE|SITREP", "target": "COS|A2|A3|A5|A6|A9|CH|A12|EXEC", "subject": "brief description"}

TASK = specific action for a persona
ORDER = standing directive / SOP change
PRIORITY = urgent, drop everything
APPROVE = approving/denying a pending item
SITREP = status request

If unclear, default to: {"type": "TASK", "target": "COS", "subject": "..."}
Target mapping: hale/cos=COS, dembe=A2, dani=A3, castillo=A5, voss/luna=A6, harlan=A9, washington=CH, elon=A12, naia=EXEC"""},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 150,
                "temperature": 0,
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Groq classifier failed ({e}), defaulting to COS TASK")
        return {"type": "TASK", "target": "COS", "subject": message[:100]}


# ====================================================================
# Claude CLI Subprocess — The Core Engine
# ====================================================================

def call_cos_via_cli(
    message: str,
    persona: str = "COS",
    intent_type: str = "TASK",
    conversation_history: Optional[list[dict]] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Call Claude Opus via CLI subprocess. Cost: $0 (Max plan).

    This is the single entry point for ALL Telegram → Claude communication.
    COS embodies the requested persona by loading their system prompt.

    Args:
        message: Commander's raw message
        persona: Target persona ID (COS, A2, A3, etc.)
        intent_type: Classified intent (TASK, ORDER, PRIORITY, APPROVE, SITREP)
        conversation_history: Recent conversation for context
        model: Claude model to use (default: opus via Max plan)

    Returns:
        Claude's response text, formatted for Telegram
    """
    # Get persona-specific system prompt
    system_prompt = PERSONA_PROMPTS.get(persona, DEFAULT_SYSTEM_PROMPT)

    # Build the full prompt with context
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"CURRENT DATE/TIME: {now}",
        f"COMMAND TYPE: {intent_type}",
        f"TARGET PERSONA: {persona}",
    ]

    # Add conversation history if available
    if conversation_history:
        parts.append("\nRECENT CONVERSATION:")
        for msg in conversation_history[-6:]:  # last 6 messages
            speaker = "Commander" if msg["role"] == "user" else "COS"
            parts.append(f"  {speaker}: {msg['text'][:300]}")

    parts.append(f"\nCOMMANDER'S MESSAGE: {message}")

    full_prompt = "\n".join(parts)

    # Build CLI command
    cmd = [
        CLAUDE_CMD,
        "--print",
        "--system-prompt", system_prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", full_prompt,
    ]

    logger.info(f"Calling Claude CLI as {persona} ({intent_type}): {message[:80]}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_RESPONSE_TIME,
            cwd=THUNDERBIRD_DIR,
            env={
                **{k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"},
                "CLAUDE_CODE_ENTRYPOINT": "cli",
            },
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "No stderr"
            logger.error(f"Claude CLI failed (exit {result.returncode}): {stderr}")
            # Try fallback with sonnet (faster, might avoid timeout)
            if model == "opus":
                logger.info("Retrying with sonnet as fallback...")
                return call_cos_via_cli(
                    message, persona, intent_type,
                    conversation_history, model="sonnet"
                )
            return f"COS reporting: CLI execution failed. Error: {stderr[:200]}"

        response = result.stdout.strip()

        if not response:
            return "COS reporting: Claude returned empty response. Retrying may help."

        # Truncate for Telegram if needed (will be split by send_long_message)
        if len(response) > 16000:
            response = response[:16000] + "\n\n[Response truncated for Telegram]"

        logger.info(f"Claude CLI response ready ({len(response)} chars)")
        return response

    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timed out after {MAX_RESPONSE_TIME}s")
        return (
            f"COS reporting: Request timed out after {MAX_RESPONSE_TIME}s. "
            "The task may be too complex for a single Telegram pass. "
            "Consider breaking it into smaller requests, or run it from the CLI directly."
        )
    except FileNotFoundError:
        logger.error(f"Claude CLI not found at {CLAUDE_CMD}")
        return "COS reporting: Claude CLI not found on this system. Check installation."
    except Exception as e:
        logger.error(f"Claude CLI call failed: {e}")
        return f"COS reporting: Unexpected error — {str(e)[:200]}"


# ====================================================================
# Legacy compatibility — call_cos_with_tools() redirects to CLI
# ====================================================================

def call_cos_with_tools(query: str, conversation_history: list[dict] = None) -> str:
    """Legacy entry point — redirects to Claude CLI.

    This function signature matches the old Groq-based tool-calling loop
    so thunderbird_telegram.py doesn't need to change its import.
    """
    return call_cos_via_cli(
        message=query,
        persona="COS",
        intent_type="TASK",
        conversation_history=conversation_history,
    )


# ====================================================================
# Quick test
# ====================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What bookings do we have active?"
    print(f"\nQuery: {query}\n{'=' * 50}")

    # Test classifier
    intent = classify_intent(query)
    print(f"Intent: {json.dumps(intent)}")

    # Test CLI call
    result = call_cos_via_cli(query, persona=intent.get("target", "COS"))
    print(f"\n{result}")
