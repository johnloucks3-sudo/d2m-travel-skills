#!/usr/bin/env python3
"""
thunderbird_elevenlabs.py — ElevenLabs voice synthesis adapter for Thunderbird.
Free alpha tier: 10,000 chars/month. Production: $5/mo for 30K chars.

Registration: https://elevenlabs.io — free tier, no credit card.
Key: ELEVENLABS_API_KEY in .env
Docs: https://elevenlabs.io/docs

Use cases:
- Dani voice for client call prep / voice messages
- Wing internal TTS for briefings
- Persona voice evaluation (MISSION-407)

Voices of interest:
- Rachel (21m00Tcm4TlvDq8ikWAM) — warm, professional female
- Adam (pNInz6obpgDQGcFmaJgB) — authoritative male
- Custom Dani voice (if uploaded)

Usage:
    from core.ai_infra.thunderbird_elevenlabs import speak, text_to_file

    # Quick TTS to speaker
    speak("Good morning, Commander. Here is your daily brief.")

    # Save to file
    text_to_file("Mission accomplished.", "output/brief.mp3")
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

_ENV = Path(__file__).parent.parent.parent / ".env"
_BASE_URL = "https://api.elevenlabs.io/v1"

# D2M-appropriate voices (free tier)
VOICES = {
    "dani": "21m00Tcm4TlvDq8ikWAM",       # Rachel — warm professional female (Dani default)
    "hale": "AZnzlk1XvdvUeBnXmlld",        # Domi — authoritative, measured
    "sterling": "ErXwobaYiN019PkySvjV",     # Antoni — calm, deliberate
    "commander": "VR6AewLTigWG4xSOukaG",   # Arnold — commanding male
    "default": "21m00Tcm4TlvDq8ikWAM",
}


def _get_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        try:
            for line in _ENV.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
    return key


def _request_audio(voice_id: str, text: str, model: str = "eleven_turbo_v2") -> bytes:
    key = _get_key()
    if not key:
        raise ValueError("ELEVENLABS_API_KEY not set — register at https://elevenlabs.io")

    payload = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode()

    req = urllib.request.Request(
        f"{_BASE_URL}/text-to-speech/{voice_id}",
        data=payload,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:300]
        raise RuntimeError(f"ElevenLabs API error {e.code}: {error_body}")


def text_to_file(
    text: str,
    output_path: str | Path,
    voice: str = "dani",
    model: str = "eleven_turbo_v2",
) -> Path:
    """Convert text to MP3 and save to file. Returns path."""
    voice_id = VOICES.get(voice, VOICES["default"])
    audio_bytes = _request_audio(voice_id, text, model)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio_bytes)
    return out


def speak(text: str, voice: str = "dani") -> bool:
    """Convert text to speech and play via system audio. Returns True on success."""
    import subprocess, tempfile
    voice_id = VOICES.get(voice, VOICES["default"])
    audio_bytes = _request_audio(voice_id, text)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["mpg123", "-q", tmp_path], capture_output=True, timeout=30
        )
        if result.returncode != 0:
            # Fallback: aplay (after conversion), or paplay
            subprocess.run(["paplay", tmp_path], capture_output=True, timeout=30)
    except FileNotFoundError:
        pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return True


def get_available_voices() -> list[dict]:
    """List all available voices on this account."""
    key = _get_key()
    if not key:
        raise ValueError("ELEVENLABS_API_KEY not set")

    req = urllib.request.Request(
        f"{_BASE_URL}/voices",
        headers={"xi-api-key": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return [
        {"voice_id": v["voice_id"], "name": v["name"], "category": v.get("category", "?")}
        for v in data.get("voices", [])
    ]


def get_usage() -> dict:
    """Check character usage vs monthly limit."""
    key = _get_key()
    if not key:
        raise ValueError("ELEVENLABS_API_KEY not set")

    req = urllib.request.Request(
        f"{_BASE_URL}/user",
        headers={"xi-api-key": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    sub = data.get("subscription", {})
    return {
        "character_count": sub.get("character_count", 0),
        "character_limit": sub.get("character_limit", 10000),
        "tier": sub.get("tier", "free"),
        "remaining": sub.get("character_limit", 10000) - sub.get("character_count", 0),
    }


if __name__ == "__main__":
    import sys
    key = _get_key()
    if not key:
        print("ELEVENLABS_API_KEY not set.")
        print("Register at: https://elevenlabs.io (free: 10K chars/mo)")
        print("Then: echo 'ELEVENLABS_API_KEY=sk_...' >> .env")
        sys.exit(1)

    print(f"ElevenLabs configured: {key[:8]}...")
    try:
        usage = get_usage()
        print(f"Usage: {usage['character_count']}/{usage['character_limit']} chars ({usage['tier']})")
        print(f"Remaining: {usage['remaining']} chars")
    except Exception as e:
        print(f"Usage check error: {e}")
