"""
Thunderbird Voice Profile Module
=================================

Analyzes John's writing style from sent emails and Commander Review drafts,
then generates a "voice profile" that can be injected into persona system
prompts (especially EXEC and A6) to make them write in John's voice.

Usage:
    from thunderbird_my_voice import build_voice_profile, get_voice_prompt_fragment

    # Build/refresh the profile (hits Gmail API + Groq)
    profile = build_voice_profile()

    # Get the prompt fragment for persona injection
    fragment = get_voice_prompt_fragment()

Outputs:
    ~/Thunderbird/my_voice_profile.json  — machine-readable profile
    ~/Thunderbird/my_voice_profile.md    — human-readable summary
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIG
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
COMMANDER_REVIEW_DIR = THUNDERBIRD_DIR / "Commander_Review"
PROFILE_JSON = THUNDERBIRD_DIR / "my_voice_profile.json"
PROFILE_MD = THUNDERBIRD_DIR / "my_voice_profile.md"

CLAUDE_MODEL = "claude-sonnet-4-20250514"

USER_EMAIL = "d2mconcierge@gmail.com"  # D2M operational Gmail per standing order
SAMPLE_MONTHS = 3
MAX_GMAIL_SAMPLES = 30
MAX_BODY_CHARS = 8000  # per email — Claude's 200K context handles this easily


# ============================================================================
# SAMPLE COLLECTION
# ============================================================================

def _collect_gmail_samples(months: int = SAMPLE_MONTHS, max_results: int = MAX_GMAIL_SAMPLES) -> List[Dict[str, str]]:
    """Fetch sent emails from the last N months via Gmail API.

    Returns list of dicts with 'subject', 'to', 'date', 'body'.
    """
    service = _get_gmail_service()

    cutoff = datetime.now() - timedelta(days=months * 30)
    after_str = cutoff.strftime("%Y/%m/%d")
    query = f"from:me in:sent after:{after_str}"

    logger.info(f"Searching Gmail: {query} (max {max_results})")

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=min(max_results, 50))
            .execute()
        )
    except Exception as e:
        logger.error(f"Gmail search failed: {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        logger.warning("No sent emails found in the specified window.")
        return []

    samples = []
    for msg_ref in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            headers = _extract_headers(
                payload.get("headers", []),
                keys={"From", "To", "Subject", "Date"},
            )
            body = _decode_body(payload)

            # Skip auto-generated / very short emails
            if not body or len(body.strip()) < 50:
                continue

            # Truncate long emails
            if len(body) > MAX_BODY_CHARS:
                body = body[:MAX_BODY_CHARS] + "\n[...truncated...]"

            samples.append({
                "subject": headers.get("Subject", "(no subject)"),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "body": body.strip(),
            })
        except Exception as e:
            logger.warning(f"Failed to read message {msg_ref['id']}: {e}")
            continue

    logger.info(f"Collected {len(samples)} Gmail sent samples.")
    return samples


def _collect_draft_samples() -> List[Dict[str, str]]:
    """Read .md files in Commander_Review that contain 'Email' or 'DRAFT' in filename.

    Returns list of dicts with 'filename', 'body'.
    """
    samples = []

    if not COMMANDER_REVIEW_DIR.exists():
        logger.warning(f"Commander_Review directory not found: {COMMANDER_REVIEW_DIR}")
        return samples

    for md_file in sorted(COMMANDER_REVIEW_DIR.glob("*.md")):
        name_upper = md_file.name.upper()
        if "EMAIL" not in name_upper and "DRAFT" not in name_upper:
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")

            # Extract just the email body — between the second "---" and the staff notes
            # The drafts follow a pattern: header block, ---, email body, ---, staff notes
            sections = re.split(r"\n---\n", content)
            # The email body is typically section index 2 (after metadata + header)
            email_body = ""
            for i, section in enumerate(sections):
                # Find sections that look like email content (start with a name salutation)
                stripped = section.strip()
                if re.match(r"^(Hi |Hey |Dear |[A-Z][a-z]+,|[A-Z][a-z]+ and )", stripped):
                    email_body = stripped
                    break

            if not email_body:
                # Fallback: grab the largest section that isn't metadata or staff notes
                candidates = [
                    s.strip() for s in sections
                    if "STAFF NOTES" not in s
                    and "COMMANDER REVIEW" not in s
                    and "Status:" not in s[:50]
                    and len(s.strip()) > 100
                ]
                if candidates:
                    email_body = max(candidates, key=len)

            if email_body and len(email_body) > 50:
                # Truncate if needed
                if len(email_body) > MAX_BODY_CHARS:
                    email_body = email_body[:MAX_BODY_CHARS] + "\n[...truncated...]"

                samples.append({
                    "filename": md_file.name,
                    "body": email_body,
                })
        except Exception as e:
            logger.warning(f"Failed to read {md_file.name}: {e}")
            continue

    logger.info(f"Collected {len(samples)} Commander Review draft samples.")
    return samples


# ============================================================================
# CLAUDE ANALYSIS (replaced Groq — standing order: eliminate all Groq)
# ============================================================================

def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Call Claude Sonnet via Anthropic SDK. Max plan = $0 cost."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text


def _analyze_writing_style(gmail_samples: List[Dict], draft_samples: List[Dict]) -> Dict[str, Any]:
    """Send writing samples to Groq for voice analysis.

    Returns structured JSON profile.
    """
    # Build the samples block for the prompt
    sample_texts = []

    for i, s in enumerate(gmail_samples[:20], 1):
        sample_texts.append(
            f"=== SENT EMAIL {i} ===\n"
            f"To: {s['to']}\n"
            f"Subject: {s['subject']}\n"
            f"Date: {s['date']}\n\n"
            f"{s['body']}\n"
        )

    for i, s in enumerate(draft_samples, 1):
        sample_texts.append(
            f"=== EDITED DRAFT {i} ({s['filename']}) ===\n\n"
            f"{s['body']}\n"
        )

    all_samples = "\n\n".join(sample_texts)

    system_prompt = (
        "You are a linguistics and communications analyst. You specialize in "
        "analyzing an individual's writing style to create a precise, actionable "
        "voice profile. You focus on concrete patterns, not vague generalizations. "
        "You must return ONLY valid JSON — no markdown fences, no commentary."
    )

    user_prompt = f"""Analyze the following emails written by John Loucks, owner of a luxury travel agency.
These are real sent emails and edited drafts. Extract his specific writing patterns.

Return a JSON object with EXACTLY this structure:

{{
  "greeting_patterns": [list of specific greeting styles he uses, e.g. "Kyle," or "Larry and Heidi,"],
  "signoff_patterns": [list of specific sign-off styles],
  "sentence_style": {{
    "avg_length": "short/medium/long",
    "complexity": "simple/moderate/complex",
    "structure_notes": "specific observations about sentence construction"
  }},
  "tone_markers": {{
    "primary_tone": "one or two word descriptor",
    "secondary_tones": [list of secondary tone qualities],
    "formality_level": "casual/semi-formal/formal/adaptive",
    "warmth_level": "low/medium/high",
    "directness_level": "low/medium/high"
  }},
  "favorite_phrases": [list of actual phrases or constructions he repeats],
  "verbal_tics": [list of habitual word choices or patterns],
  "punctuation_habits": {{
    "em_dashes": "frequency and usage pattern",
    "ellipses": "frequency and usage pattern",
    "exclamation_points": "frequency and usage pattern",
    "bold_text": "how and when he uses bold",
    "other": "any other notable punctuation patterns"
  }},
  "good_news_style": "how he delivers good news",
  "bad_news_style": "how he delivers bad news or corrections",
  "urgent_matters_style": "how he handles urgent items",
  "humor_style": "how he uses humor, if at all",
  "persuasion_style": "how he persuades or recommends",
  "structural_patterns": {{
    "email_structure": "how he typically structures an email",
    "list_usage": "how he uses bullets/numbered lists",
    "paragraph_length": "typical paragraph length",
    "transition_style": "how he moves between topics"
  }},
  "things_he_never_does": [list of things notably absent from his writing],
  "signature_moves": [list of distinctive stylistic choices that make his writing recognizable]
}}

WRITING SAMPLES:

{all_samples}"""

    raw = _call_claude(system_prompt, user_prompt, max_tokens=3000)

    # Parse JSON — strip any markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        profile = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude JSON response: {e}")
        logger.error(f"Raw response: {raw[:500]}")
        raise ValueError(f"Claude returned invalid JSON: {e}")

    return profile


def _generate_voice_summary(profile: Dict[str, Any]) -> str:
    """Generate a human-readable markdown summary of the voice profile."""
    system_prompt = (
        "You are a writing coach summarizing a voice analysis for the subject himself. "
        "Write in second person ('you'). Be specific and concrete — cite actual phrases "
        "and patterns. Keep it under 600 words. Use markdown formatting."
    )

    user_prompt = f"""Based on this voice analysis, write a readable summary of John Loucks's
writing style. He's the owner of Dreams2Memories Travel, a luxury travel agency.
He's a retired USAF Colonel. The summary should help an AI write in his voice.

Voice analysis data:
{json.dumps(profile, indent=2)}

Format with these sections:
# Your Voice — John "Yoda" Loucks
## The Big Picture
(2-3 sentences capturing the overall feel)
## How You Open
## How You Close
## Sentence DNA
## Tone & Temperature
## Your Go-To Moves
## What You Never Do
## The Signature
(1-2 sentences that nail the essence)
"""

    return _call_claude(system_prompt, user_prompt, max_tokens=1500)


def _generate_prompt_fragment(profile: Dict[str, Any]) -> str:
    """Generate a system prompt fragment for persona injection."""
    system_prompt = (
        "You are an AI prompt engineer. Generate a concise system prompt fragment "
        "(under 400 words) that instructs an AI persona to write in a specific person's voice. "
        "Be extremely specific — include actual phrases, patterns, and anti-patterns. "
        "Return ONLY the prompt fragment text, no markdown fences or labels."
    )

    user_prompt = f"""Based on this voice analysis of John Loucks (owner of Dreams2Memories Travel,
retired USAF Colonel, goes by "Yoda"), generate a system prompt fragment that can be
injected into AI persona prompts to make them write client-facing emails in John's voice.

The fragment should cover:
- Greeting and sign-off patterns
- Sentence structure and length
- Tone calibration
- Specific phrases to use and avoid
- How to handle good/bad/urgent news
- Structural patterns (bullets, bold, paragraphs)
- Anti-patterns (things John NEVER does)

Voice analysis:
{json.dumps(profile, indent=2)}

Write the fragment as direct instructions starting with "COMMANDER'S VOICE PROFILE —" """

    return _call_claude(system_prompt, user_prompt, max_tokens=1200)


# ============================================================================
# PUBLIC API
# ============================================================================

def build_voice_profile(
    gmail_months: int = SAMPLE_MONTHS,
    gmail_max: int = MAX_GMAIL_SAMPLES,
    skip_gmail: bool = False,
) -> Dict[str, Any]:
    """Build (or rebuild) John's voice profile from writing samples.

    Args:
        gmail_months: How many months back to search sent emails.
        gmail_max: Max Gmail samples to fetch.
        skip_gmail: If True, only use Commander Review drafts (offline mode).

    Returns:
        The full profile dict (also saved to disk).
    """
    logger.info("Building voice profile...")

    # 1. Collect samples
    gmail_samples = []
    if not skip_gmail:
        try:
            gmail_samples = _collect_gmail_samples(months=gmail_months, max_results=gmail_max)
        except Exception as e:
            logger.warning(f"Gmail collection failed (continuing with drafts only): {e}")

    draft_samples = _collect_draft_samples()

    total = len(gmail_samples) + len(draft_samples)
    if total == 0:
        raise ValueError(
            "No writing samples found. Check Gmail auth and Commander_Review directory."
        )

    logger.info(f"Total samples: {len(gmail_samples)} Gmail + {len(draft_samples)} drafts = {total}")

    # 2. Analyze with Groq
    logger.info("Analyzing writing patterns with Claude...")
    analysis = _analyze_writing_style(gmail_samples, draft_samples)

    # 3. Generate readable summary
    logger.info("Generating voice summary...")
    summary_md = _generate_voice_summary(analysis)

    # 4. Generate prompt fragment
    logger.info("Generating persona prompt fragment...")
    prompt_fragment = _generate_prompt_fragment(analysis)

    # 5. Assemble full profile
    profile = {
        "meta": {
            "generated": datetime.now().isoformat(),
            "gmail_samples": len(gmail_samples),
            "draft_samples": len(draft_samples),
            "model": CLAUDE_MODEL,
            "email": USER_EMAIL,
        },
        "analysis": analysis,
        "prompt_fragment": prompt_fragment,
    }

    # 6. Save outputs
    PROFILE_JSON.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"Saved: {PROFILE_JSON}")

    # Build the markdown file
    md_content = f"""{summary_md}

---

## Prompt Fragment (for persona injection)

```
{prompt_fragment}
```

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} |
{len(gmail_samples)} sent emails + {len(draft_samples)} edited drafts |
Model: {CLAUDE_MODEL}*
"""

    PROFILE_MD.write_text(md_content, encoding="utf-8")
    logger.info(f"Saved: {PROFILE_MD}")

    return profile


def get_voice_prompt_fragment() -> str:
    """Return the voice prompt fragment for persona injection.

    Loads from the saved profile. If no profile exists, raises FileNotFoundError
    with instructions to run build_voice_profile() first.
    """
    if not PROFILE_JSON.exists():
        raise FileNotFoundError(
            f"Voice profile not found at {PROFILE_JSON}. "
            "Run build_voice_profile() first."
        )

    profile = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
    fragment = profile.get("prompt_fragment", "")

    if not fragment:
        raise ValueError("Profile exists but prompt_fragment is empty. Rebuild with build_voice_profile().")

    return fragment


def get_voice_profile() -> Dict[str, Any]:
    """Load and return the full voice profile dict from disk."""
    if not PROFILE_JSON.exists():
        raise FileNotFoundError(
            f"Voice profile not found at {PROFILE_JSON}. "
            "Run build_voice_profile() first."
        )
    return json.loads(PROFILE_JSON.read_text(encoding="utf-8"))


def inject_voice_into_persona(persona_system_prompt: str) -> str:
    """Append the voice prompt fragment to an existing persona system prompt.

    Use this to augment EXEC (Naia) or A6 (Luna) prompts so they write
    in John's voice when drafting client-facing communications.
    """
    try:
        fragment = get_voice_prompt_fragment()
    except (FileNotFoundError, ValueError) as e:
        logger.warning(f"Cannot inject voice profile: {e}")
        return persona_system_prompt

    return f"{persona_system_prompt}\n\n{fragment}"


# ============================================================================
# LEARNING COMPILER INTEGRATION (Layer 2: Passive Observation)
# ============================================================================

def feed_learning_compiler(profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Feed voice profile analysis into the learning compiler as passive observations.

    This bridges Layer 2 (passive observation from sent emails) into Layer 1
    (the learning compiler's corrections/principles pipeline).

    Extracts voice patterns from the profile and stores them as 'passive_voice'
    source corrections, which the learning compiler can then extract principles from.
    """
    from thunderbird_learning import capture_email_diff, extract_principles

    if profile is None:
        profile = get_voice_profile()

    analysis = profile.get("analysis", {})
    if not analysis:
        return {"status": "error", "message": "No analysis data in profile"}

    captured = 0

    # Feed signature moves as directives (things Commander DOES)
    for move in analysis.get("signature_moves", []):
        capture_email_diff(
            original_body="",
            sent_body=f"VOICE PATTERN (positive): {move}",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    # Feed anti-patterns (things Commander NEVER does)
    for anti in analysis.get("things_he_never_does", []):
        capture_email_diff(
            original_body=f"ANTI-PATTERN: {anti}",
            sent_body="",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    # Feed favorite phrases as positive patterns
    for phrase in analysis.get("favorite_phrases", []):
        capture_email_diff(
            original_body="",
            sent_body=f"PREFERRED PHRASE: {phrase}",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    # Feed tone markers as contextual rules
    tone = analysis.get("tone_markers", {})
    if tone:
        tone_summary = (
            f"Primary tone: {tone.get('primary_tone', 'unknown')}. "
            f"Formality: {tone.get('formality_level', 'unknown')}. "
            f"Warmth: {tone.get('warmth_level', 'unknown')}. "
            f"Directness: {tone.get('directness_level', 'unknown')}."
        )
        capture_email_diff(
            original_body="",
            sent_body=f"VOICE TONE PROFILE: {tone_summary}",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    # Feed greeting and signoff patterns
    for greeting in analysis.get("greeting_patterns", []):
        capture_email_diff(
            original_body="",
            sent_body=f"GREETING PATTERN: {greeting}",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    for signoff in analysis.get("signoff_patterns", []):
        capture_email_diff(
            original_body="",
            sent_body=f"SIGNOFF PATTERN: {signoff}",
            context="passive_voice_observation",
            source="voice_profile",
        )
        captured += 1

    logger.info(f"Fed {captured} voice observations into learning compiler")

    # Extract principles from the newly captured observations
    principles = []
    if captured > 0:
        try:
            principles = extract_principles(limit=captured)
            logger.info(f"Extracted {len(principles)} principles from voice observations")
        except Exception as e:
            logger.warning(f"Principle extraction failed (will retry later): {e}")

    return {
        "status": "ok",
        "observations_captured": captured,
        "principles_extracted": len(principles),
        "principles": principles,
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--skip-gmail" in sys.argv:
        print("Building voice profile (drafts only, skipping Gmail)...")
        profile = build_voice_profile(skip_gmail=True)
    else:
        print("Building voice profile (Gmail + Commander Review drafts)...")
        print(f"Searching last {SAMPLE_MONTHS} months of sent emails from {USER_EMAIL}")
        profile = build_voice_profile()

    print(f"\nProfile saved to:")
    print(f"  JSON: {PROFILE_JSON}")
    print(f"  MD:   {PROFILE_MD}")
    print(f"\nSamples analyzed: {profile['meta']['gmail_samples']} emails + {profile['meta']['draft_samples']} drafts")
    print(f"\nTo get the prompt fragment in code:")
    print(f"  from thunderbird_my_voice import get_voice_prompt_fragment")
    print(f"  fragment = get_voice_prompt_fragment()")
