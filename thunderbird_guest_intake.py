"""
Thunderbird Guest Intake Engine
================================

AI-driven client intake that replaces the manual guest profile form chase.

Inspired by financial planning AI onboarding (PreciseFP / Holistiplan model):
  "57% of RIAs now use AI for onboarding. Cuts 4–6 hrs to < 1 hr."
  D2M analog: guest profile collection is manual. This solves it.

Two modes:
  1. PROSPECT MODE — unknown sender contacts Dani. We send a warm Dani
     intro + 3 qualifying questions to start the relationship.

  2. CLIENT MODE — known client missing key dossier fields. Dani
     conversationally fills in the gaps over 1-3 exchanges.

Usage:
  from thunderbird_guest_intake import (
      is_intake_candidate,
      build_prospect_intake_draft,
      parse_intake_response,
      save_intake_data,
  )
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("thunderbird_guest_intake")

INTAKE_LOG = Path.home() / "Thunderbird" / "logs" / "guest_intake.jsonl"
PROSPECTS_DIR = Path.home() / "Thunderbird" / "dossiers" / "prospects"
INTAKE_LOG.parent.mkdir(exist_ok=True)
PROSPECTS_DIR.mkdir(parents=True, exist_ok=True)

# Signals that an email is a genuine travel inquiry vs. spam/bounce/vendor
_TRAVEL_SIGNALS = [
    "cruise", "travel", "trip", "vacation", "holiday", "sailing", "voyage",
    "book", "reserve", "inquiry", "interested", "question", "quote",
    "europe", "caribbean", "alaska", "mediterranean", "pacific",
    "silversea", "regent", "viking", "oceania", "cunard", "ponant",
    "recommend", "looking for", "planning", "honeymoon", "anniversary",
    "group", "family", "couple", "retirement",
]

_SPAM_SIGNALS = [
    "unsubscribe", "click here", "limited time", "act now", "free offer",
    "mailer-daemon", "delivery failed", "out of office", "auto-reply",
    "no-reply", "noreply", "bounce", "postmaster",
]

# The three qualifying questions Dani asks prospects
_INTAKE_QUESTIONS = [
    (
        "What kind of travel experience are you dreaming of? "
        "(A river cruise through Europe? An expedition to Antarctica? "
        "A classic ocean voyage?)"
    ),
    (
        "When are you thinking of traveling, and how many people would be joining you?"
    ),
    (
        "Have you cruised or traveled with a luxury line before? "
        "Any lines or ships you've loved — or ones that didn't quite fit?"
    ),
]

# Fields we try to parse from intake responses
_INTAKE_FIELDS = {
    "destination": [
        r"\b(europe|caribbean|alaska|mediterranean|pacific|norway|iceland|japan|"
        r"south america|africa|australia|new zealand|africa|israel|israel|greece|italy|"
        r"scandinavia|baltic|canary|transatlantic|world cruise)\b"
    ],
    "travel_date": [
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b",
        r"\b\d{4}\b",
        r"\b(spring|summer|fall|winter|autumn)\s+\d{4}\b",
        r"\b(next year|this year|next summer|next winter|next spring|next fall)\b",
    ],
    "group_size": [
        r"\b(\d+)\s*(people|guests|passengers|travelers|of us|in our group|pax)\b",
        r"\bjust\s+(the\s+two|two|2)\b",
        r"\bsolo\b",
        r"\bcouple\b",
        r"\bfamily of\s+(\d+)\b",
    ],
    "cruise_experience": [
        r"\b(silversea|regent|viking|oceania|cunard|seabourn|ponant|crystal|azamara|"
        r"celebrity|princess|royal caribbean|carnival|disney|ncl|norwegian)\b",
    ],
    "budget_signal": [
        r"\b(budget|affordable|cost|price|expensive|luxury|ultra-luxury|value)\b",
    ],
    "occasion": [
        r"\b(anniversary|honeymoon|birthday|retirement|celebration|milestone|special occasion|"
        r"bucket list|graduation)\b",
    ],
}


def is_intake_candidate(classification: dict) -> bool:
    """Return True if this email looks like a genuine new prospect inquiry."""
    if classification.get("is_known", False):
        return False  # Existing client — not a prospect intake

    body = (
        classification.get("body_full", "") + " " + classification.get("subject", "")
    ).lower()
    sender = classification.get("sender_email", "").lower()

    # Block obvious spam/system emails
    if any(sig in body or sig in sender for sig in _SPAM_SIGNALS):
        return False

    # Must have at least one travel signal
    return any(sig in body for sig in _TRAVEL_SIGNALS)


def build_prospect_intake_draft(classification: dict) -> str:
    """Build a warm Dani intro email with 3 qualifying questions for a new prospect.

    Returns the email body text (not the HTML-wrapped version — that's the
    stationery layer's job).
    """
    sender_name = classification.get("sender_name", "there")
    first_name = sender_name.split()[0] if sender_name and sender_name != "there" else "there"
    subject = classification.get("subject", "")
    body_preview = classification.get("body_preview", "")

    # Reference their specific question if we can detect it
    specific_ref = ""
    body_lower = body_preview.lower()
    for dest_kw in ["cruise", "voyage", "sailing", "trip", "travel"]:
        if dest_kw in body_lower:
            specific_ref = f"Your note about {dest_kw} planning caught my attention. "
            break

    questions_block = "\n\n".join(
        f"{i+1}. {q}" for i, q in enumerate(_INTAKE_QUESTIONS)
    )

    draft = (
        f"Hi {first_name},\n\n"
        f"I'm Dani — concierge at Dreams2Memories Travel. {specific_ref}"
        f"I'd love to help you start planning something extraordinary.\n\n"
        f"To make sure I point you toward the right experiences, "
        f"I have three quick questions:\n\n"
        f"{questions_block}\n\n"
        f"No pressure, no pitch — just want to understand what you're dreaming of "
        f"before I start pulling options together.\n\n"
        f"Thanks,\n"
        f"Dani Moreau\n"
        f"Concierge Intelligence — Dreams2Memories Travel"
    )
    return draft


def parse_intake_response(email_body: str) -> dict:
    """Parse a client's intake response for structured data fields.

    Returns a dict of detected fields. All values are raw strings
    from the email — caller is responsible for validation.
    """
    parsed = {}
    body_lower = email_body.lower()

    for field, patterns in _INTAKE_FIELDS.items():
        for pattern in patterns:
            match = re.search(pattern, body_lower)
            if match:
                parsed[field] = match.group(0).strip()
                break

    return parsed


def save_intake_data(
    sender_email: str,
    sender_name: str,
    raw_body: str,
    parsed_fields: dict,
    intake_type: str = "prospect",
) -> str:
    """Save intake data to guest_intake.jsonl and create a prospect stub file.

    Returns the path to the stub file created (or '' on failure).
    """
    ts = datetime.now().isoformat()
    entry = {
        "ts": ts,
        "intake_type": intake_type,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "raw_excerpt": raw_body[:500],
        "parsed": parsed_fields,
    }

    try:
        with open(INTAKE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.error(f"Intake log write failed: {e}")

    # Create a minimal dossier stub for the prospect
    stub_name = re.sub(r"[^\w\-]", "_", sender_name.lower())[:30]
    stub_path = PROSPECTS_DIR / f"PROSPECT_{stub_name}_{datetime.now().strftime('%Y%m%d')}.md"
    try:
        lines = [
            f"---",
            f"type: prospect",
            f"name: {sender_name}",
            f"email: {sender_email}",
            f"intake_date: {ts[:10]}",
            f"status: intake_sent",
        ]
        for k, v in parsed_fields.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append(f"\n# Prospect: {sender_name}\n")
        lines.append(f"**Email:** {sender_email}  ")
        lines.append(f"**First contact:** {ts[:10]}  ")
        lines.append(f"**Status:** Intake questions sent\n")
        if parsed_fields:
            lines.append("## Detected Preferences\n")
            for k, v in parsed_fields.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        lines.append(f"\n## Notes\n\n_Intake draft sent. Awaiting response._\n")

        stub_path.write_text("\n".join(lines), encoding="utf-8")
        log.info(f"Prospect stub created: {stub_path.name}")
        return str(stub_path)
    except Exception as e:
        log.error(f"Prospect stub creation failed: {e}")
        return ""
