"""
Dani — D2M Public Travel Concierge (Poe Bot)
=============================================
Dreams2Memories Travel, LLC

Dani is Dreams2Memories' luxury travel concierge bot on Poe.
She helps prospective and current clients with:
  - Destination research and inspiration
  - Cruise line comparisons
  - Port and excursion recommendations
  - Hotel and tour guidance
  - Travel advisories and weather outlook
  - General luxury travel advice

IMPORTANT: This bot serves the PUBLIC and prospective clients.
  - NO client-specific data (names, booking IDs, payment amounts)
  - NO itinerary details or confirmation numbers
  - NO financial information
  - Direct transactional requests → "Contact your D2M agent"
  - For booked clients: direct to concierge@d2mluxury.quest

Deployment:
  1. Register bot at poe.com/create_bot
  2. Set server URL: https://api.d2mluxury.quest/dani-poe
  3. Set access key in DANI_POE_ACCESS_KEY env/config
  4. Run: python thunderbird_dani_poe_bot.py

Cloudflare tunnel routes api.d2mluxury.quest → localhost:8788

Run standalone:
  cd ~/Thunderbird && .venv/bin/python thunderbird_dani_poe_bot.py
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import AsyncIterable

import fastapi_poe as fp

logger = logging.getLogger("thunderbird_dani_poe_bot")

THUNDERBIRD_DIR = Path.home() / "Thunderbird"

# ── Config ─────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    cfg = {}
    for env_file in [
        THUNDERBIRD_DIR / "config" / "poe.env",
        THUNDERBIRD_DIR / "config" / "dani_poe.env",
    ]:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip()
    return cfg


_cfg = _load_config()
DANI_POE_ACCESS_KEY = _cfg.get("DANI_POE_ACCESS_KEY", os.environ.get("DANI_POE_ACCESS_KEY", ""))
DANI_BOT_PORT       = int(_cfg.get("DANI_POE_PORT", os.environ.get("DANI_POE_PORT", "8788")))

# ── System prompt ──────────────────────────────────────────────────────────────

DANI_SYSTEM_PROMPT = """You are Dani, the luxury travel concierge for Dreams2Memories Travel, LLC — a boutique travel agency specializing in ultra-luxury cruises and custom journeys.

**Your personality:**
You are warm, knowledgeable, and operationally crisp. You speak like a trusted concierge at a five-star hotel — attentive, unhurried, specific. You love travel and it shows. You never use corporate jargon or filler phrases like "Great question!" or "Absolutely!"

**What you help with:**
- Destination research: ports, cities, regions — what to do, eat, see
- Cruise line profiles: Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways, Ponant
- Ship comparisons and itinerary styles
- Port excursion recommendations (cultural, culinary, adventure)
- Hotel and resort guidance for pre/post cruise stays
- Travel advisories, entry requirements, and safety context
- Best travel seasons, packing advice, dress codes
- General luxury travel planning guidance

**What you do NOT handle (redirect gracefully):**
- Specific booking details, confirmation numbers, or payment amounts → "For booking-specific questions, email us at concierge@d2mluxury.quest"
- Pricing quotes or availability → "We'd love to build a custom quote for you — reach us at concierge@d2mluxury.quest or text John directly at 719-291-0742"
- Visa or legal advice → "We recommend consulting the official embassy website or a visa service"

**D2M contact info (share freely):**
- Email: concierge@d2mluxury.quest
- Website: d2mluxury.quest
- John Loucks, founder — 719-291-0742 (for clients who ask directly)

**Tone:**
- Specific and useful, never vague
- Warm without being saccharine
- Confident without being pushy
- Sign off naturally, not with "Best regards"

You are not a booking system. You are a knowledgeable friend who happens to know luxury travel intimately."""

# ── Dani Bot ───────────────────────────────────────────────────────────────────

class DaniBot(fp.PoeBot):
    """Dani — D2M Luxury Travel Concierge for Poe."""

    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        """Stream a response using Claude Sonnet via Poe's model proxy."""

        # Build message history with system prompt injected
        messages = [
            fp.ProtocolMessage(role="system", content=DANI_SYSTEM_PROMPT)
        ]

        # Add conversation history (limit to last 10 turns to save tokens)
        history = list(request.query)
        if len(history) > 20:
            history = history[-20:]
        messages.extend(history)

        # Use Claude Sonnet via Poe's built-in bot proxy
        async for msg in fp.stream_request(
            request,
            "Claude-3.7-Sonnet",   # Poe bot name for Claude Sonnet
            request.access_key,
            query=messages,
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"Claude-3.7-Sonnet": 1},
            introduction_message=(
                "Hi, I'm Dani — your luxury travel concierge from Dreams2Memories Travel. "
                "I can help with destination inspiration, cruise line comparisons, "
                "port excursions, hotel recommendations, and travel planning. "
                "What are you dreaming about?"
            ),
        )


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not DANI_POE_ACCESS_KEY:
        logger.error(
            "DANI_POE_ACCESS_KEY not set. Add to config/dani_poe.env:\n"
            "  DANI_POE_ACCESS_KEY=<key from poe.com/create_bot>"
        )
        raise SystemExit(1)

    logger.info("Starting Dani Poe bot on port %d", DANI_BOT_PORT)
    fp.run(DaniBot(), access_key=DANI_POE_ACCESS_KEY, port=DANI_BOT_PORT)
