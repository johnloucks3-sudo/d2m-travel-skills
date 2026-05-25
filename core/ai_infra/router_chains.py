TIER_CHAINS: dict[str, list[str]] = {
    "FLAG": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_opus",
    ],
    "FLAG_OPUS": [
        "claude_max_oauth_opus",
        "claude_max_oauth_sonnet",
    ],
    "FLAG_SONNET": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_opus",
    ],
    "MID": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_haiku",
    ],
    "BULK": [
        "claude_max_oauth_haiku",
        "claude_max_oauth_sonnet",
    ],
    "ARB": [
        "claude_max_oauth_haiku",
        "claude_max_oauth_sonnet",
    ],
}

PERSONA_TIER_OVERRIDES: dict[str, str] = {
    "DANI": "FLAG",
    "DANIELLE": "FLAG",
    "A3": "FLAG",
    "HALE": "FLAG",
    "HALE-OPUS": "FLAG_OPUS",
    "HALE-SONNET": "FLAG_SONNET",
    "HALE-CC": "FLAG",
    "COS": "FLAG",
    "DEMBE": "BULK",
    "A2": "BULK",
    "ELON": "MID",
    "A12": "MID",
}

ALL_TIERS = list(TIER_CHAINS.keys())

DEFAULT_TIER = "MID"


def resolve_persona_tier(persona: str) -> str | None:
    normalized = persona.strip().upper()
    if normalized in PERSONA_TIER_OVERRIDES:
        return PERSONA_TIER_OVERRIDES[normalized]
    return None
