TIER_CHAINS: dict[str, list[str]] = {
    "FLAG": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_opus",
        "deepseek_v4",
    ],
    "FLAG_OPUS": [
        "claude_max_oauth_opus",
        "claude_max_oauth_sonnet",
        "deepseek_v4",
    ],
    "FLAG_SONNET": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_opus",
        "deepseek_v4",
    ],
    "MID": [
        "claude_max_oauth_sonnet",
        "claude_max_oauth_haiku",
        "deepseek_v4",
    ],
    "BULK": [
        "claude_max_oauth_haiku",
        "claude_max_oauth_sonnet",
        "deepseek_v4",
    ],
    "ARB": [
        "claude_max_oauth_haiku",
        "claude_max_oauth_sonnet",
        "deepseek_v4",
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
