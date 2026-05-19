import logging
import re

log = logging.getLogger("router_classifier")

ALL_TIERS = ("FLAG", "MID", "BULK", "ARB")
DEFAULT_TIER = "MID"

_TIER_KEYWORDS: dict[str, list[str]] = {
    "FLAG": [
        "strategy", "judgment", "voice", "tone", "client", "proposal", "pricing",
        "dani", "hale-cc", "opus", "decision", "approve", "sign-off", "brand",
        "luxury", "voice fidelity",
    ],
    "MID": [
        "structured", "report", "analysis", "review", "brief", "dossier",
        "profile", "inference", "itinerary", "planning",
    ],
    "BULK": [
        "research", "osint", "sweep", "summary", "summarize", "intel",
        "extract", "scan", "list", "bulk", "batch",
    ],
    "ARB": [
        "tie-break", "compare", "vs", "versus", "arbitrate", "decide between",
    ],
}

_TIER_CONTENT_HINTS: dict[str, list[str]] = {
    "FLAG": ["draft email", "client message", "proposal", "quote", "company voice"],
    "MID": ["200-500 words", "structured output", "bullet points", "table"],
    "BULK": ["csv", "list of", "all the", "every", "extract data"],
}

_PERSONA_TIER_MAP: dict[str, str] = {
    "HALE": "FLAG", "HALE-CC": "FLAG", "COS": "FLAG",
    "DANI": "FLAG", "DANIELLE": "FLAG", "A3": "FLAG",
    "DEMBE": "BULK", "A2": "BULK",
    "A12": "MID", "ELON": "MID",
}


def classify_by_persona(persona: str) -> str | None:
    normalized = persona.strip().upper()
    return _PERSONA_TIER_MAP.get(normalized)


def classify_by_content(system: str, user: str) -> str | None:
    combined = f"{system} {user}".lower()

    # Check content hints first (more specific)
    for tier, hints in _TIER_CONTENT_HINTS.items():
        for hint in hints:
            if hint.lower() in combined:
                log.debug("Content hint '%s' → %s", hint, tier)
                return tier

    # Check keywords
    for tier, keywords in _TIER_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', combined):
                log.debug("Keyword '%s' → %s", kw, tier)
                return tier

    return None


def classify(task_system: str, task_user: str, persona: str = "default",
             tier_override: str | None = None) -> str:
    if tier_override and tier_override.upper() in ALL_TIERS:
        return tier_override.upper()

    persona_tier = classify_by_persona(persona)
    if persona_tier:
        return persona_tier

    content_tier = classify_by_content(task_system, task_user)
    if content_tier:
        return content_tier

    return DEFAULT_TIER
