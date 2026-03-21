"""
Thunderbird Audio Briefing Generator
=====================================
Converts trip dossiers into audio-friendly scripts, then generates
audio files using text-to-speech.

Two modes:
  A. Script-only: Generate a conversational script from a dossier
     (can be read aloud or sent as text)
  B. TTS: Generate actual audio file using free/low-cost TTS

Uses:
  - Client trip preview: "Here's your trip at a glance"
  - Commander morning brief: Audio version of the morning briefing
  - Pre-departure overview: "Everything you need to know before you go"

Dreams2Memories Travel, LLC
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(__file__).parent
DOSSIER_DIR = Path(os.path.expanduser("~/Thunderbird/dossiers"))
AUDIO_DIR = Path(os.path.expanduser("~/Thunderbird/audio_briefings"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("thunderbird_audio_briefing")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# Files in dossiers/ that are NOT client dossiers
SKIP_FILES = {
    "CLAUDE.md", "DANI_TESTER_BRIEFINGS.md", "DOSSIER_Regent_Tips_Guide.md",
}

# Style templates — system prompts for script generation
STYLE_PROMPTS = {
    "conversational": (
        "You are Dani Moreau, luxury travel concierge at Dreams2Memories Travel. "
        "Write a warm, conversational audio briefing script — as if you are personally "
        "talking to the client on the phone. Use short sentences. Be confident and "
        "specific. Include all key dates, destinations, hotels, flights, and excursions. "
        "Address the client by first name. No bullet points — this will be read aloud. "
        "Open with a warm greeting. Close with genuine excitement for their trip. "
        "Target 3-5 minutes when read aloud (roughly 500-800 words)."
    ),
    "concise": (
        "You are Dani Moreau, luxury travel concierge at Dreams2Memories Travel. "
        "Write a concise audio briefing — key facts only, read in under 2 minutes. "
        "Dates, destinations, hotels, flights, action items. Short declarative sentences. "
        "Address the client by first name. No filler. Every sentence delivers information."
    ),
    "luxury": (
        "You are Dani Moreau, luxury travel concierge at Dreams2Memories Travel. "
        "Write an evocative, luxurious audio briefing that paints a picture of the "
        "experience ahead. Describe the destinations, the ship, the feeling of arrival. "
        "Weave in practical details (dates, hotels, flights) naturally. This should feel "
        "like a personal letter read aloud — warm, literate, never corporate. "
        "Address the client by first name. Target 5-7 minutes (800-1100 words)."
    ),
    "commander": (
        "You are Col Victoria Hale, Chief of Staff at Dreams2Memories Travel. "
        "Write a crisp operational briefing for Commander Loucks. Cover: booking status, "
        "payments due, open action items, upcoming anchor dates, any risks or gaps. "
        "Military brevity — no fluff, no adjectives. Facts, dates, numbers, actions. "
        "This is a morning brief, not a client piece. Under 3 minutes."
    ),
}

# ---------------------------------------------------------------------------
# Dossier Discovery
# ---------------------------------------------------------------------------


def list_dossiers() -> list[dict]:
    """List all available dossier files with metadata."""
    dossiers = []
    if not DOSSIER_DIR.exists():
        return dossiers

    for f in sorted(DOSSIER_DIR.iterdir()):
        if f.suffix not in (".md", ".txt"):
            continue
        if f.name in SKIP_FILES:
            continue
        # Extract a friendly name from the filename
        name = f.stem.replace("DOSSIER_", "").replace("_", " ")
        dossiers.append({
            "filename": f.name,
            "name": name,
            "path": str(f),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return dossiers


def _find_dossier(dossier_name: str) -> Optional[Path]:
    """Resolve a dossier name to a file path. Accepts partial matches."""
    if not DOSSIER_DIR.exists():
        return None

    # Exact match first
    exact = DOSSIER_DIR / dossier_name
    if exact.exists():
        return exact

    # Try with .md extension
    if not dossier_name.endswith(".md"):
        exact_md = DOSSIER_DIR / f"{dossier_name}.md"
        if exact_md.exists():
            return exact_md

    # Try with DOSSIER_ prefix
    prefixed = DOSSIER_DIR / f"DOSSIER_{dossier_name}.md"
    if prefixed.exists():
        return prefixed

    # Fuzzy match — case-insensitive substring
    search = dossier_name.lower().replace(" ", "_").replace("-", "_")
    candidates = []
    for f in DOSSIER_DIR.iterdir():
        if f.suffix not in (".md", ".txt"):
            continue
        if f.name in SKIP_FILES:
            continue
        if search in f.name.lower():
            candidates.append(f)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # Prefer exact stem match
        for c in candidates:
            if c.stem.lower() == search:
                return c
        # Otherwise return the shortest name (most specific)
        return sorted(candidates, key=lambda c: len(c.name))[0]

    return None


# ---------------------------------------------------------------------------
# Dossier Parsing — Extract structured facts for script generation
# ---------------------------------------------------------------------------


def _extract_dossier_facts(content: str) -> dict:
    """Extract key facts from dossier markdown for script generation.

    Returns a structured dict with trip details, dates, flights, hotels, etc.
    This helps Claude produce accurate scripts without hallucinating details.
    """
    facts: dict = {
        "raw_length": len(content),
        "sections": [],
    }

    # Trip name / ship
    ship_match = re.search(r"(?:Ship|Vessel|Cruise):\s*(.+)", content, re.I)
    if ship_match:
        facts["ship"] = ship_match.group(1).strip()

    # Route
    route_match = re.search(r"Route:\s*(.+)", content, re.I)
    if route_match:
        facts["route"] = route_match.group(1).strip()

    # Embarkation
    embark_match = re.search(r"Embarkation:\s*(.+)", content, re.I)
    if embark_match:
        facts["embarkation"] = embark_match.group(1).strip()

    # Disembarkation
    disembark_match = re.search(r"Disembarkation:\s*(.+)", content, re.I)
    if disembark_match:
        facts["disembarkation"] = disembark_match.group(1).strip()

    # Duration
    duration_match = re.search(r"Duration:\s*(.+)", content, re.I)
    if duration_match:
        facts["duration"] = duration_match.group(1).strip()

    # Client names
    client_match = re.search(
        r"(?:CLIENT DOSSIER|CLIENT|GUEST).*?[—–-]\s*(.+)", content, re.I
    )
    if client_match:
        facts["clients"] = client_match.group(1).strip()

    # Payment info
    payment_matches = re.findall(
        r"(?:Balance Due|FINAL PAYMENT|Payment Due).*?(\$[\d,]+(?:\.\d{2})?)"
        r".*?(?:DUE\s+)?(\w+\s+\d+,?\s*\d{4})?",
        content, re.I
    )
    if payment_matches:
        facts["payments"] = [
            {"amount": m[0], "due": m[1].strip() if m[1] else "TBD"}
            for m in payment_matches
        ]

    # Hotels
    hotel_matches = re.findall(
        r"(?:Hotel|Stay|Property):\s*(.+?)(?:\n|$)", content, re.I
    )
    if hotel_matches:
        facts["hotels"] = [h.strip() for h in hotel_matches]

    # Flight table rows (capture route info)
    flight_rows = re.findall(
        r"((?:AA|BA|AY|DL|UA|LH|SK|SQ|EK|QR|CX|NH|JL)\s*\d+[^\n]*)",
        content
    )
    if flight_rows:
        facts["flights"] = flight_rows[:10]  # cap at 10

    # Excursions / shore excursions
    excursion_matches = re.findall(
        r"(?:excursion|shore|activity|tour)[s]?.*?:\s*(.+?)(?:\n|$)",
        content, re.I
    )
    if excursion_matches:
        facts["excursions"] = [e.strip() for e in excursion_matches[:10]]

    # Key dates table
    date_rows = re.findall(
        r"(\d{4}-\d{2}-\d{2})\s+(\w+)\s+\[([^\]]+)\]\s+(.+)",
        content
    )
    if date_rows:
        facts["anchor_dates"] = [
            {"date": d[0], "status": d[1], "category": d[2].strip(),
             "milestone": d[3].strip()}
            for d in date_rows[:20]
        ]

    # Section headers for context
    headers = re.findall(r"^#{1,3}\s+(.+)|^[═─]{5,}\n(.+)", content, re.M)
    facts["sections"] = [
        (h[0] or h[1]).strip() for h in headers if (h[0] or h[1]).strip()
    ]

    return facts


# ---------------------------------------------------------------------------
# Script Generation — Uses Claude via Anthropic SDK
# ---------------------------------------------------------------------------


def generate_briefing_script(
    dossier_path: str,
    style: str = "conversational",
) -> str:
    """Generate a conversational audio briefing script from a dossier.

    Args:
        dossier_path: Path to the dossier file, or dossier name for auto-resolve
        style: One of "conversational", "concise", "luxury", "commander"

    Returns:
        Plain text script ready for TTS or human reading
    """
    # Resolve path
    path = Path(dossier_path)
    if not path.exists():
        resolved = _find_dossier(dossier_path)
        if not resolved:
            available = list_dossiers()
            names = [d["filename"] for d in available]
            return (
                f"Dossier not found: {dossier_path}\n\n"
                f"Available dossiers:\n" + "\n".join(f"  - {n}" for n in names)
            )
        path = resolved

    content = path.read_text(encoding="utf-8")
    facts = _extract_dossier_facts(content)

    # Validate style
    if style not in STYLE_PROMPTS:
        style = "conversational"

    system_prompt = STYLE_PROMPTS[style]

    # Build the user message with extracted facts + full content
    user_message = (
        f"Generate an audio briefing script for this trip dossier.\n\n"
        f"EXTRACTED FACTS (use these for accuracy — do NOT invent details):\n"
        f"{json.dumps(facts, indent=2, default=str)}\n\n"
        f"FULL DOSSIER CONTENT:\n"
        f"{content}\n\n"
        f"RULES:\n"
        f"- Only include facts present in the dossier. Never fabricate.\n"
        f"- Write as flowing prose — no markdown, no bullets, no headers.\n"
        f"- Use pauses naturally (commas, periods) for TTS pacing.\n"
        f"- Spell out abbreviations on first use (e.g., 'AA' → 'American Airlines').\n"
        f"- Dates should be spoken naturally ('August twenty-ninth' not 'Aug 29').\n"
        f"- Dollar amounts spoken naturally ('fifteen thousand, four hundred eighty-six dollars').\n"
        f"- End with something warm and genuine — not a cliche.\n"
    )

    try:
        import anthropic
        client = anthropic.Anthropic()

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        script = resp.content[0].text if resp.content else ""
        if script:
            logger.info(
                "Generated %s-style briefing script for %s (%d words)",
                style, path.name, len(script.split())
            )
            return script

    except Exception as exc:
        logger.error("Claude script generation failed: %s", exc)
        return f"Script generation failed: {exc}"

    return "No script generated — empty response from Claude."


# ---------------------------------------------------------------------------
# TTS Generation — gTTS (free) with pyttsx3 fallback
# ---------------------------------------------------------------------------


def _tts_gtts(script: str, output_path: Path) -> Path:
    """Generate audio using Google Text-to-Speech (free, requires internet)."""
    from gtts import gTTS

    tts = gTTS(text=script, lang="en", slow=False)
    tts.save(str(output_path))
    logger.info("gTTS audio saved: %s (%.1f KB)", output_path.name,
                output_path.stat().st_size / 1024)
    return output_path


def _tts_pyttsx3(script: str, output_path: Path) -> Path:
    """Generate audio using pyttsx3 (offline, no API needed).

    Note: pyttsx3 requires system audio drivers — may not work on headless servers.
    Falls back to gTTS if initialization fails.
    """
    import pyttsx3

    engine = pyttsx3.init()

    # Configure voice — prefer female voice for Dani
    voices = engine.getProperty("voices")
    for voice in voices:
        if "female" in voice.name.lower() or "zira" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break

    engine.setProperty("rate", 160)  # Slightly slower for clarity
    engine.setProperty("volume", 0.95)

    engine.save_to_file(script, str(output_path))
    engine.runAndWait()
    logger.info("pyttsx3 audio saved: %s", output_path.name)
    return output_path


def generate_audio_file(script: str, output_path: Path) -> Path:
    """Generate an audio file from script text. Tries pyttsx3 first, falls back to gTTS."""
    # Try pyttsx3 first (offline, no API)
    try:
        return _tts_pyttsx3(script, output_path)
    except Exception as exc:
        logger.info("pyttsx3 unavailable (%s), falling back to gTTS", exc)

    # Fall back to gTTS (free, needs internet)
    try:
        return _tts_gtts(script, output_path)
    except Exception as exc:
        logger.error("Both TTS engines failed. pyttsx3 and gTTS unavailable: %s", exc)
        raise RuntimeError(
            f"TTS generation failed — neither pyttsx3 nor gTTS could produce audio: {exc}"
        )


# ---------------------------------------------------------------------------
# High-Level API — Generate audio briefing from dossier
# ---------------------------------------------------------------------------


def generate_audio_briefing(
    dossier_path: str,
    style: str = "conversational",
    output_path: Optional[str] = None,
) -> dict:
    """Generate an audio briefing from a trip dossier.

    Full pipeline: dossier → script → audio file.

    Args:
        dossier_path: Path or name of the dossier
        style: Script style ("conversational", "concise", "luxury", "commander")
        output_path: Optional output .mp3 path. Auto-generated if not provided.

    Returns:
        dict with script, audio_path, duration_estimate, and metadata
    """
    # Step 1: Generate script
    script = generate_briefing_script(dossier_path, style=style)

    if script.startswith("Dossier not found:") or script.startswith("Script generation failed:"):
        return {"status": "error", "message": script}

    # Step 2: Determine output path
    if output_path:
        audio_path = Path(output_path)
    else:
        # Auto-name: dossier stem + style + timestamp
        resolved = _find_dossier(dossier_path)
        stem = resolved.stem if resolved else "briefing"
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        audio_path = AUDIO_DIR / f"{stem}_{style}_{ts}.mp3"

    audio_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 3: Generate audio
    try:
        result_path = generate_audio_file(script, audio_path)
    except RuntimeError as exc:
        # Save script as fallback even if TTS fails
        script_path = audio_path.with_suffix(".txt")
        script_path.write_text(script, encoding="utf-8")
        return {
            "status": "partial",
            "message": f"Script generated but TTS failed: {exc}",
            "script": script,
            "script_path": str(script_path),
            "word_count": len(script.split()),
            "duration_estimate_min": round(len(script.split()) / 150, 1),
        }

    # Estimate duration (average speaking pace: ~150 words/min)
    word_count = len(script.split())
    duration_min = round(word_count / 150, 1)

    return {
        "status": "success",
        "audio_path": str(result_path),
        "script": script,
        "word_count": word_count,
        "duration_estimate_min": duration_min,
        "file_size_kb": round(result_path.stat().st_size / 1024, 1),
        "style": style,
        "dossier": dossier_path,
    }


# ---------------------------------------------------------------------------
# Morning Brief Audio Mode
# ---------------------------------------------------------------------------


def generate_morning_brief_audio(output_path: Optional[str] = None) -> dict:
    """Generate an audio version of the morning briefing.

    Reads the latest morning briefing output (HTML preview) and converts
    the key content to an audio briefing in COS voice.

    Returns:
        dict with audio_path and metadata
    """
    # Look for the latest morning briefing preview
    preview_dir = THUNDERBIRD_DIR / "output"
    briefing_content = None

    if preview_dir.exists():
        html_files = sorted(
            preview_dir.glob("briefing_preview*.html"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if html_files:
            try:
                from bs4 import BeautifulSoup
                raw_html = html_files[0].read_text(encoding="utf-8")
                soup = BeautifulSoup(raw_html, "html.parser")
                briefing_content = soup.get_text(separator="\n", strip=True)
                logger.info("Loaded morning briefing from %s", html_files[0].name)
            except ImportError:
                # No bs4 — read raw HTML, Claude can handle it
                briefing_content = html_files[0].read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Failed to parse briefing HTML: %s", exc)

    if not briefing_content:
        # Try to generate a fresh briefing
        try:
            from thunderbird_morning_briefing import run_briefing
            result = run_briefing(preview=True)
            # Re-read the generated preview
            if preview_dir.exists():
                html_files = sorted(
                    preview_dir.glob("briefing_preview*.html"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                if html_files:
                    from bs4 import BeautifulSoup
                    raw_html = html_files[0].read_text(encoding="utf-8")
                    soup = BeautifulSoup(raw_html, "html.parser")
                    briefing_content = soup.get_text(separator="\n", strip=True)
        except Exception as exc:
            return {
                "status": "error",
                "message": f"No morning briefing available and generation failed: {exc}",
            }

    if not briefing_content:
        return {
            "status": "error",
            "message": "No morning briefing content found. Run the briefing first.",
        }

    # Generate script from briefing content using commander style
    system_prompt = STYLE_PROMPTS["commander"]
    user_message = (
        f"Convert this morning briefing into an audio script for Commander Loucks.\n\n"
        f"BRIEFING CONTENT:\n{briefing_content[:8000]}\n\n"
        f"RULES:\n"
        f"- Military brevity. Facts, dates, numbers, actions.\n"
        f"- Open with 'Good morning, Commander. Here is your daily brief.'\n"
        f"- Group by: client actions due, market intelligence, operational items.\n"
        f"- Close with 'End of brief.' — nothing else.\n"
        f"- Spoken naturally — no markdown, no bullets.\n"
    )

    try:
        import anthropic
        client = anthropic.Anthropic()

        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        script = resp.content[0].text if resp.content else ""
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Script generation failed: {exc}",
        }

    if not script:
        return {"status": "error", "message": "Empty script from Claude."}

    # Generate audio
    if output_path:
        audio_path = Path(output_path)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        audio_path = AUDIO_DIR / f"morning_brief_{ts}.mp3"

    audio_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result_path = generate_audio_file(script, audio_path)
    except RuntimeError as exc:
        script_path = audio_path.with_suffix(".txt")
        script_path.write_text(script, encoding="utf-8")
        return {
            "status": "partial",
            "message": f"Script generated but TTS failed: {exc}",
            "script": script,
            "script_path": str(script_path),
        }

    word_count = len(script.split())
    return {
        "status": "success",
        "audio_path": str(result_path),
        "script": script,
        "word_count": word_count,
        "duration_estimate_min": round(word_count / 150, 1),
        "file_size_kb": round(result_path.stat().st_size / 1024, 1),
        "style": "commander",
    }


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------


def register_audio_briefing_tools(server) -> None:
    """Register audio briefing MCP tools with the FastMCP server instance."""

    @server.tool()
    async def generate_briefing_script_tool(
        dossier_name: str,
        style: str = "conversational",
    ) -> str:
        """Generate a conversational audio briefing script from a trip dossier.

        Reads the dossier, extracts key facts (dates, destinations, hotels,
        excursions, flights), and generates a warm script in Dani's voice.

        Args:
            dossier_name: Dossier filename or partial name (e.g., "Furlow",
                "Grandeur_Scandinavia", "SilverNova_Pacific"). Fuzzy matching supported.
            style: Script style:
                - "conversational" (default) — podcast-like, warm, 3-5 min
                - "concise" — bullet summary, under 2 min
                - "luxury" — evocative, paints a picture, 5-7 min
                - "commander" — COS operational brief, no fluff
        """
        script = generate_briefing_script(dossier_name, style=style)
        return json.dumps({
            "status": "success" if not script.startswith(("Dossier not found", "Script generation failed")) else "error",
            "script": script,
            "word_count": len(script.split()),
            "duration_estimate_min": round(len(script.split()) / 150, 1),
            "style": style,
        }, indent=2)

    @server.tool()
    async def generate_audio_briefing_tool(
        dossier_name: str,
        style: str = "conversational",
    ) -> str:
        """Generate an audio briefing (.mp3) from a trip dossier.

        Full pipeline: reads dossier → generates Dani-voice script → converts to audio.
        Audio files saved to ~/Thunderbird/audio_briefings/.

        Args:
            dossier_name: Dossier filename or partial name (e.g., "Furlow",
                "Grandeur_Scandinavia"). Fuzzy matching supported.
            style: Script style — "conversational", "concise", "luxury", or "commander"
        """
        result = generate_audio_briefing(dossier_name, style=style)
        # Don't include full script in MCP response to keep it manageable
        if result.get("script"):
            result["script_preview"] = result["script"][:500] + "..."
            del result["script"]
        return json.dumps(result, indent=2)

    @server.tool()
    async def generate_morning_brief_audio_tool() -> str:
        """Generate an audio version of the morning briefing.

        Reads the latest morning briefing and converts it to an audio file
        in COS operational voice. Saved to ~/Thunderbird/audio_briefings/.
        """
        result = generate_morning_brief_audio()
        if result.get("script"):
            result["script_preview"] = result["script"][:500] + "..."
            del result["script"]
        return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Thunderbird Audio Briefing Generator"
    )
    parser.add_argument(
        "dossier",
        nargs="?",
        help="Dossier name or path (omit to list available dossiers)",
    )
    parser.add_argument(
        "--style", "-s",
        choices=["conversational", "concise", "luxury", "commander"],
        default="conversational",
        help="Script style (default: conversational)",
    )
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Generate script text only, skip TTS audio generation",
    )
    parser.add_argument(
        "--morning-brief",
        action="store_true",
        help="Generate audio from morning briefing instead of dossier",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (auto-generated if omitted)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available dossiers",
    )

    args = parser.parse_args()

    if args.list or (not args.dossier and not args.morning_brief):
        dossiers = list_dossiers()
        if dossiers:
            print(f"\nAvailable dossiers ({len(dossiers)}):\n")
            for d in dossiers:
                print(f"  {d['filename']:<50} {d['size_kb']:>6.1f} KB")
        else:
            print("No dossiers found in", DOSSIER_DIR)
        raise SystemExit(0)

    if args.morning_brief:
        print("Generating morning brief audio...")
        result = generate_morning_brief_audio(output_path=args.output)
        print(json.dumps(result, indent=2))
        raise SystemExit(0)

    if args.script_only:
        script = generate_briefing_script(args.dossier, style=args.style)
        print(script)
    else:
        print(f"Generating {args.style} audio briefing for: {args.dossier}")
        result = generate_audio_briefing(
            args.dossier, style=args.style, output_path=args.output
        )
        if result["status"] == "success":
            print(f"\nAudio saved: {result['audio_path']}")
            print(f"Duration:    ~{result['duration_estimate_min']} min")
            print(f"File size:   {result['file_size_kb']} KB")
            print(f"\nScript:\n{'=' * 60}")
            print(result["script"])
        else:
            print(f"\n{result['status'].upper()}: {result.get('message', '')}")
            if result.get("script"):
                print(f"\nScript (TTS failed):\n{'=' * 60}")
                print(result["script"])
