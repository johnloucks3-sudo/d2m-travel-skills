#!/usr/bin/env python3
"""
Thunderbird Draft Polish Engine
================================
Two-backend LLM layer that actively rewrites D2M email drafts for voice, tone,
and format BEFORE the TALON+JET quality gate (creative chain step 4.5).

Backend A — Gemini 2.5 Flash   (cloud, free 1500 RPD, instant)
Backend B — Ollama local        (on-device, zero cost, zero rate limit, privacy-safe)
Auto mode — Gemini first, Ollama fallback on any failure.

Usage:
    from core.email.draft_polish import polish_draft

    polished = polish_draft(
        body=draft_body,
        email_type="welcome",   # "welcome" | "lifecycle" | "validation" | "general"
        client_name="Kyle",
        backend="auto",         # "gemini" | "ollama" | "auto"
    )

Integration point: after Dani (step 4), before TALON+JET (step 5).
Caller is responsible for swapping body in the draft record before evaluation.
"""

import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger("thunderbird.draft_polish")

THUNDERBIRD_DIR = Path.home() / "Thunderbird"

# Ollama model preference — first available in this list wins
OLLAMA_MODEL_PREFERENCE = [
    "qwen2.5:7b",
    "llama3.1:8b",
    "llama3.2:3b",   # installed — guaranteed fallback
    "phi3:mini",
]

# Sanity check: polished result must be >= this fraction of original length
# Guards against truncated/empty responses slipping through
_MIN_LENGTH_RATIO = 0.25


# ---------------------------------------------------------------------------
# D2M Voice System Prompt
# ---------------------------------------------------------------------------

_BASE_SYSTEM_PROMPT = """You are a luxury travel correspondence editor for Dreams2Memories Travel, LLC.
Your task: rewrite the email draft below to match John Loucks' exact communication style.

VOICE RULES — apply every one without exception:
1. Opening: "Hi [FirstName]," — first name only; never Mr./Mrs./Dr./Miss
2. Lead sentence: the single most important fact — not a pleasantry
3. Length: 3-5 sentences for routine emails; longer only if genuinely multi-point
4. Specificity: at least one concrete anchor — date, ship name, dollar figure, or city
5. Tone: warm-but-certain — client may be uncertain; John is steady and expert
6. Delete all filler: "I hope this finds you well" · "please don't hesitate" · "feel free to reach out" · "just wanted to" · "as always" · "excited to share"
7. Sign-off: EXACTLY "Thanks,\\nJohn" or "Thank you,\\nJohn" — never Best · Cheers · Warm regards · Sincerely
8. Screenshot test: a stranger reading this must know it was written for THIS specific person
9. Never mention AI, automation, or internal system names

FORBIDDEN WORDS — remove or replace each one found:
journey · curated (as experience adjective) · seamless · nestled · delight (as verb) ·
bespoke · luxurious (redundant for this audience) · unparalleled · tailor-made ·
personalized · boutique (unless a venue name) · immersive · transformative ·
elevated (as experience adjective) · wanderlust · sojourn

OUTPUT FORMAT:
Return ONLY the revised email body. No preamble. No "Here is the revision:". No markdown fences.
Preserve any HTML formatting tags present in the input.
If the draft already meets all rules, return it verbatim."""

_TYPE_HINTS: dict[str, str] = {
    "welcome": (
        "\n\nEMAIL TYPE — WELCOME:"
        " Confirm what is booked. State the single most exciting fact about their voyage."
        " End with what John is actively doing for them next."
    ),
    "lifecycle": (
        "\n\nEMAIL TYPE — LIFECYCLE:"
        " One focused topic only. Build anticipation without vague superlatives."
        " Always close with John's concrete next action on their behalf."
    ),
    "validation": (
        "\n\nEMAIL TYPE — PAYMENT VALIDATION:"
        " Lead with confirmation of payment received."
        " State exact amount and date. Include the next milestone date."
    ),
    "general": "",
}


def _build_system_prompt(email_type: str) -> str:
    return _BASE_SYSTEM_PROMPT + _TYPE_HINTS.get(email_type, "")


# ---------------------------------------------------------------------------
# Sanity check — guards against truncated LLM responses
# ---------------------------------------------------------------------------

def _is_plausible_output(original: str, result: str) -> bool:
    """Return False if result looks truncated or empty."""
    if not result or not result.strip():
        return False
    orig_len = len(original.strip())
    res_len = len(result.strip())
    if orig_len > 0 and (res_len / orig_len) < _MIN_LENGTH_RATIO:
        logger.warning(
            "draft_polish: result length %.0f%% of original — treating as truncated",
            100 * res_len / orig_len,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------

def _get_available_ollama_model() -> Optional[str]:
    """Return the best available Ollama model or None."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return None
        installed = {m["name"] for m in resp.json().get("models", [])}
        for candidate in OLLAMA_MODEL_PREFERENCE:
            if candidate in installed:
                return candidate
        return None
    except Exception as exc:
        logger.debug("Ollama model check failed: %s", exc)
        return None


def _polish_with_ollama(
    body: str,
    email_type: str,
    client_name: Optional[str],
    model: str,
) -> str:
    """Call Ollama chat API to polish draft. Raises on failure."""
    import requests

    system_prompt = _build_system_prompt(email_type)
    user_content = (
        f"CLIENT FIRST NAME: {client_name or 'unknown'}\n\n"
        f"DRAFT TO POLISH:\n---\n{body}\n---\n\n"
        "Return only the polished email body."
    )

    # Prefer /api/chat (better instruction following on instruct models)
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {"num_predict": 1024, "temperature": 0.4, "top_p": 0.9},
    }

    resp = requests.post(
        "http://localhost:11434/api/chat",
        json=chat_payload,
        timeout=90,
    )
    resp.raise_for_status()
    text = resp.json().get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Ollama returned empty message content")
    return text


# ---------------------------------------------------------------------------
# Gemini backend
# ---------------------------------------------------------------------------

def _polish_with_gemini(
    body: str,
    email_type: str,
    client_name: Optional[str],
) -> str:
    """Call Gemini 2.5 Flash to polish draft. Raises on failure."""
    sys.path.insert(0, str(THUNDERBIRD_DIR))

    try:
        from dotenv import load_dotenv
        load_dotenv(str(THUNDERBIRD_DIR / ".env"))
    except ImportError:
        pass

    from core.ai_infra.gemini_client import call_gemini  # type: ignore

    system_prompt = _build_system_prompt(email_type)
    user_prompt = (
        f"CLIENT FIRST NAME: {client_name or 'unknown'}\n\n"
        f"DRAFT TO POLISH:\n---\n{body}\n---\n\n"
        "Return only the polished email body."
    )

    return call_gemini(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=1024,
        temperature=0.4,
        caller="draft_polish",
        task_hint=f"email_polish/{email_type}",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def polish_draft(
    body: str,
    email_type: str = "general",
    client_name: Optional[str] = None,
    backend: Literal["auto", "gemini", "ollama"] = "auto",
) -> str:
    """
    Polish a D2M email draft for voice, tone, and format compliance.

    Args:
        body:        Draft body (plain text or HTML)
        email_type:  "welcome" | "lifecycle" | "validation" | "general"
        client_name: Client first name — improves personalization prompting
        backend:     "gemini" | "ollama" | "auto" (Gemini → Ollama fallback)

    Returns:
        Polished body string. Returns original unchanged on total backend failure
        so the pipeline never breaks.
    """
    if not body or not body.strip():
        return body

    start = time.time()
    used_backend: Optional[str] = None
    result: Optional[str] = None

    # --- Path A: Gemini ---
    if backend in ("gemini", "auto"):
        try:
            candidate = _polish_with_gemini(body, email_type, client_name)
            if _is_plausible_output(body, candidate):
                result = candidate
                used_backend = "gemini/gemini-2.5-flash"
            else:
                logger.warning("draft_polish: Gemini output failed sanity check")
        except Exception as exc:
            if backend == "gemini":
                logger.error("draft_polish: Gemini failed: %s", exc)
                return body
            logger.warning("draft_polish: Gemini failed (%s) — trying Ollama", exc)

    # --- Path B: Ollama ---
    if result is None and backend in ("ollama", "auto"):
        model = _get_available_ollama_model()
        if model is None:
            logger.warning("draft_polish: no Ollama models available")
            if backend == "ollama":
                return body
        else:
            try:
                candidate = _polish_with_ollama(body, email_type, client_name, model)
                if _is_plausible_output(body, candidate):
                    result = candidate
                    used_backend = f"ollama/{model}"
                else:
                    logger.warning("draft_polish: Ollama output failed sanity check")
            except Exception as exc:
                logger.error("draft_polish: Ollama failed: %s", exc)

    if not result:
        logger.warning("draft_polish: all backends failed — returning original draft")
        return body

    logger.info(
        "draft_polish: polished via %s in %.1fs [type=%s client=%s]",
        used_backend, time.time() - start, email_type, client_name or "?",
    )
    return result


def polish_draft_gemini(
    body: str, email_type: str = "general", client_name: Optional[str] = None
) -> str:
    """Gemini-only polish. No Ollama fallback."""
    return polish_draft(body, email_type, client_name, backend="gemini")


def polish_draft_ollama(
    body: str, email_type: str = "general", client_name: Optional[str] = None
) -> str:
    """Ollama-only polish. No Gemini fallback."""
    return polish_draft(body, email_type, client_name, backend="ollama")


def ensure_polish_model(preferred: str = "qwen2.5:7b") -> str:
    """
    Ensure the preferred Ollama polish model is available. Pulls it in the
    background (non-blocking) if not installed. Returns model that will be used.
    """
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            installed = {m["name"] for m in resp.json().get("models", [])}
            if preferred in installed:
                logger.info("draft_polish: %s already installed", preferred)
                return preferred
    except Exception:
        pass

    logger.info("draft_polish: pulling %s in background (non-blocking)", preferred)
    try:
        subprocess.Popen(
            ["ollama", "pull", preferred],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("draft_polish: %s pull started — available in ~2-3 min on this disk", preferred)
    except Exception as exc:
        logger.warning("draft_polish: could not start pull for %s: %s", preferred, exc)

    return _get_available_ollama_model() or "llama3.2:3b"


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

_SMOKE_DRAFT = """Dear Mr. and Mrs. Kuklinski,

I hope this email finds you well! I am very excited to share that your booking
has been successfully processed. Your journey on the Viking Mars is confirmed and we
are so delighted for you to embark on this curated, immersive voyage experience.

Please don't hesitate to reach out if you have any questions whatsoever.

Best regards,
John"""

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        from dotenv import load_dotenv
        load_dotenv(str(THUNDERBIRD_DIR / ".env"))
    except ImportError:
        pass

    backend_arg = sys.argv[1] if len(sys.argv) > 1 else "auto"

    print(f"draft_polish smoke test — backend: {backend_arg}")
    print("=" * 60)
    print("ORIGINAL:")
    print(_SMOKE_DRAFT)
    print("=" * 60)

    polished = polish_draft(
        _SMOKE_DRAFT,
        email_type="welcome",
        client_name="Kyle",
        backend=backend_arg,
    )

    print("POLISHED:")
    print(polished)
    print("=" * 60)

    changed = polished.strip() != _SMOKE_DRAFT.strip()
    forbidden_still_present = any(
        w in polished.lower()
        for w in ["journey", "curated", "seamless", "delighted", "immersive", "best regards"]
    )

    if changed and not forbidden_still_present:
        print("[PASS] Draft modified and forbidden words removed")
        sys.exit(0)
    elif changed:
        print("[PARTIAL] Draft modified but some forbidden words remain — check prompt adherence")
        sys.exit(0)
    else:
        print("[WARN] Draft returned unchanged — check backend connectivity")
        sys.exit(1)
