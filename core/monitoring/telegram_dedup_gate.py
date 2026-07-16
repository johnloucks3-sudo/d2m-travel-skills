"""
core/monitoring/telegram_dedup_gate.py — fleet-wide Telegram flood suppression.

ROOT CAUSE (2026-07-16): 90+ separate scripts each POST directly to
`api.telegram.org` with their own `requests.post()` call. There is no
shared client and no central place to rate-limit or mute anything, so a
single crash-looping service (or a per-cycle alert like a fare watch or
credential check) pages the Commander every run, forever, with no memory
of what it already said. Commander, 2026-07-16: "hundreds of notices
about system outages... just fix it immediately and dedupe/silence."

Fixing 90+ call sites individually is exactly the kind of scoped, brittle
patch this session's triage kept finding and re-finding. This installs
ONE gate at the network layer instead, using the same zero-touch
sitecustomize pattern as core/monitoring/crash_reporter.py (see
core/monitoring/sitecustomize.py) -- every Python process on this
machine's PYTHONPATH picks it up with no per-script edits.

Two independent suppression mechanisms:
  1. MUTE LIST (OpsCenter/state/telegram_muted_topics.json) -- substring
     match against outgoing message text. Anything matching a muted
     phrase is dropped silently, permanently, until removed from the
     file. Seeded 2026-07-16 with "Lyons" per direct Commander order (a
     topic he says he already told the Wing to stop paging him about).
  2. COOLDOWN DEDUP (OpsCenter/state/telegram_dedup_state.json) -- any
     other message is hashed (after stripping obviously-volatile tokens
     like timestamps, attempt counters, and PIDs so near-identical repeat
     alerts still collide) and suppressed if an identical signature was
     already sent within TELEGRAM_DEDUP_COOLDOWN_SECONDS (default 4h).

Every suppression is logged to OpsCenter/telegram_suppressed.log so
nothing vanishes without a trace -- this gate silences noise, it does
not hide real signal from an auditor who goes looking.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent.parent
STATE_DIR = THUNDERBIRD_DIR / "OpsCenter" / "state"
MUTED_TOPICS_FILE = STATE_DIR / "telegram_muted_topics.json"
DEDUP_STATE_FILE = STATE_DIR / "telegram_dedup_state.json"
SUPPRESSED_LOG = THUNDERBIRD_DIR / "OpsCenter" / "telegram_suppressed.log"

DEFAULT_COOLDOWN_SECONDS = int(os.environ.get("TELEGRAM_DEDUP_COOLDOWN_SECONDS", 4 * 3600))

_VOLATILE_TOKEN_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?|"  # ISO-ish timestamps
    r"\battempt #?\d+\b|\bpid \d+\b|\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b",
    re.IGNORECASE,
)

_installed = False


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _ensure_seed_mute_list() -> None:
    if MUTED_TOPICS_FILE.exists():
        return
    _save_json(MUTED_TOPICS_FILE, {
        "muted_substrings": ["Lyons"],
        "_note": (
            "Substring match (case-insensitive) against outgoing Telegram "
            "text. Matches are dropped silently and logged to "
            "telegram_suppressed.log. Seeded 2026-07-16 per Commander "
            "direct order re: repeated Lyons notices."
        ),
    })


def _normalize_for_hash(text: str) -> str:
    return _VOLATILE_TOKEN_RE.sub("", text or "").strip().lower()


def _log_suppressed(reason: str, chat_id: str, text: str) -> None:
    try:
        SUPPRESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(SUPPRESSED_LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{reason}] chat={chat_id} :: {text[:200]!r}\n")
    except Exception:
        pass


def should_suppress(chat_id: str, text: str) -> Optional[str]:
    """Return a suppression reason string if this send should be dropped, else None."""
    muted = _load_json(MUTED_TOPICS_FILE, {"muted_substrings": []})
    for phrase in muted.get("muted_substrings", []):
        if phrase and phrase.lower() in (text or "").lower():
            return f"muted:{phrase}"

    key = hashlib.sha256(f"{chat_id}:{_normalize_for_hash(text)}".encode()).hexdigest()
    state = _load_json(DEDUP_STATE_FILE, {})
    now = time.time()
    last = state.get(key)
    state[key] = now
    # opportunistic cleanup so this file doesn't grow forever
    if len(state) > 2000:
        cutoff = now - DEFAULT_COOLDOWN_SECONDS
        state = {k: v for k, v in state.items() if v >= cutoff}
        state[key] = now
    _save_json(DEDUP_STATE_FILE, state)

    if last is not None and (now - last) < DEFAULT_COOLDOWN_SECONDS:
        return "cooldown"
    return None


def _extract_chat_and_text(url: str, args, kwargs):
    if "api.telegram.org" not in url or "sendmessage" not in url.lower():
        return None, None
    payload = kwargs.get("json") or kwargs.get("data") or (args[0] if args else None) or {}
    if not isinstance(payload, dict):
        return None, None
    return str(payload.get("chat_id", "")), payload.get("text", "")


def install() -> None:
    global _installed
    if _installed:
        return
    _installed = True
    try:
        _ensure_seed_mute_list()
        import requests

        _orig_post = requests.post
        _orig_session_post = requests.Session.post

        class _SuppressedResponse:
            status_code = 200
            text = '{"ok": true, "result": {"suppressed_by_dedup_gate": true}}'

            def json(self):
                return {"ok": True, "result": {"suppressed_by_dedup_gate": True}}

        def _guarded_post(url, *args, **kwargs):
            chat_id, text = _extract_chat_and_text(url, args, kwargs)
            if chat_id is not None:
                reason = should_suppress(chat_id, text)
                if reason:
                    _log_suppressed(reason, chat_id, text)
                    return _SuppressedResponse()
            return _orig_post(url, *args, **kwargs)

        def _guarded_session_post(self, url, *args, **kwargs):
            chat_id, text = _extract_chat_and_text(url, args, kwargs)
            if chat_id is not None:
                reason = should_suppress(chat_id, text)
                if reason:
                    _log_suppressed(reason, chat_id, text)
                    return _SuppressedResponse()
            return _orig_session_post(self, url, *args, **kwargs)

        requests.post = _guarded_post
        requests.Session.post = _guarded_session_post
    except Exception:
        # Never let this gate be the reason a script fails to start or send.
        pass
