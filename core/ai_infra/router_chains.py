TIER_CHAINS: dict[str, list[str]] = {
    "FLAG": [
        "claude_max_oauth_sonnet",
        "deepseek_r1",
    ],
    "FLAG_OPUS": [
        "claude_max_oauth_opus",
        "deepseek_r1",
    ],
    "FLAG_SONNET": [
        "claude_max_oauth_sonnet",
        "deepseek_r1",
    ],
    "MID": [
        "claude_max_oauth_sonnet",
        "opencode_bigpickle",
        "poe_kimi_k2",
        "opencode_nemotron",
    ],
    "BULK": [
        "opencode_bigpickle",
        "google_gemini_flash",
        "poe_gemini_flash",
        "opencode_nemotron",
    ],
    "ARB": [
        "deepseek_r1",
        "poe_kimi_k2",
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
