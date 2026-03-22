"""
Thunderbird Telegram Tools — Phase 2: Claude Agent SDK
=======================================================

Replaces the `claude --print` subprocess approach with the Claude Agent SDK
for streaming, hooks, sessions, and custom tools.

Architecture:
  1. Telegram message arrives, classified by Claude
  2. This module calls the Claude Agent SDK with persona system prompt
  3. Claude runs in ~/Thunderbird/ with full MCP tool access
  4. Streaming progress callbacks sent to Telegram as the agent works
  5. Response returned to Telegram

Billing modes (controlled by ~/Thunderbird/config/poe.env):
  POE_MODE=0 (default) — Max plan OAuth, $0 per call, Opus quality
  POE_MODE=1           — Poe gateway, burns Poe points, Sonnet quality
  Switch:  sed -i 's/POE_MODE=0/POE_MODE=1/' ~/Thunderbird/config/poe.env
  Revert:  sed -i 's/POE_MODE=1/POE_MODE=0/' ~/Thunderbird/config/poe.env

Replaces: thunderbird_telegram_tools_v2.py (subprocess CLI approach)
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

logger = logging.getLogger("thunderbird_telegram_tools_sdk")

# ── Poe / Max plan mode — import BEFORE any SDK import ──────────────────────
# build_api_env() sets or strips ANTHROPIC_API_KEY depending on POE_MODE.
# This must run before any SDK import so the SDK picks up the right credentials.
from thunderbird_poe_config import build_api_env, poe_mode, poe_model, route_model, log_usage, estimate_from_text

# Apply mode to the live process environment so SDK auto-detects credentials
_startup_env = build_api_env()
if poe_mode():
    os.environ["ANTHROPIC_API_KEY"]  = _startup_env.get("ANTHROPIC_API_KEY", "")
    os.environ["ANTHROPIC_BASE_URL"] = _startup_env.get("ANTHROPIC_BASE_URL", "")
    logger.info("Poe gateway mode active — routing via %s", os.environ["ANTHROPIC_BASE_URL"])
else:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("ANTHROPIC_BASE_URL", None)
    logger.info("Max plan mode active — using OAuth credentials")

# ── Config ──
THUNDERBIRD_DIR = os.path.expanduser("~/Thunderbird")
CLAUDE_CMD = os.path.expanduser("~/.local/bin/claude")
MAX_RESPONSE_TIME = 600  # seconds — complex multi-tool requests (research + draft + status) can exceed 180s
# Model routing — Sonnet is default (separate weekly quota, ~0% used).
# Escalate to Opus via route_model("client_proposal") etc. for high-value work.
DEFAULT_MODEL  = poe_model() if poe_mode() else route_model("default")   # claude-sonnet-4-6
FALLBACK_MODEL = route_model("classify")                                   # claude-haiku-4-5-*


# ── Session store — maps Telegram chat IDs to SDK session IDs ──
_sessions: dict[str, str] = {}

# ── Dangerous command patterns for safety hooks ──
BLOCKED_PATTERNS = [
    "rm -rf",
    "shutdown",
    "reboot",
    "DROP TABLE",
    "DROP DATABASE",
    "TRUNCATE TABLE",
    "mkfs",
    "dd if=",
    "> /dev/sd",
]

BLOCKED_PATH_PREFIXES = [
    "/etc/",
    "/usr/lib/systemd/",
    "/lib/systemd/",
]


# ====================================================================
# Persona System Prompts — COS embodies each persona via prompt
# ====================================================================

PERSONA_PROMPTS = {
    "A1": (
        'You are CMSgt (Ret.) Dale "Radar" Crenshaw, A1 (Personnel, Admin & Audit) '
        "at Dreams2Memories Travel.\n"
        "You are COS Hale's eyes and ears — the third pair of eyes in the cockpit. "
        "Observer, auditor, process improver.\n"
        "Your duties: dossier hygiene, Booking Master accuracy, file indexing, "
        "workflow compliance, Trinity sync watchdog, pre-brief prep.\n"
        "You proactively surface what's missing, stale, or wrong — before anyone asks.\n"
        "You suggest world-class best practices when you see room for improvement.\n"
        "Voice: quiet, deliberate, dry wit. When you speak, people listen.\n"
        "Use tools to check real data. NEVER fabricate.\n"
        "Format for Telegram: *bold* for flags, concise, facts-first."
    ),
    "COS": (
        'You are Colonel Victoria "Iron Vic" Hale, Chief of Staff at '
        "Dreams2Memories Travel, LLC.\n"
        'You are briefing the COMMANDER (John Loucks, callsign "Yoda") '
        "via Telegram.\n"
        "Be measured, authoritative, precise. Present ALL data — every "
        "field, every date, every detail.\n"
        "Use *bold* for emphasis. Keep responses scannable but complete.\n"
        "Use your MCP tools to get REAL data. NEVER fabricate.\n"
        "Currency: USD. Dates: human-readable. "
        "Format for Telegram (4096 char limit per message)."
    ),
    "A2": (
        'You are Lt Col Marcus "Wraith" Dembe, A2 (Research & Market '
        "Intelligence) at Dreams2Memories Travel.\n"
        "You specialize in destination research, competitive intelligence, "
        "cruise line analysis, and market trends.\n"
        "Briefing the Commander via Telegram. Use tools to gather real "
        "data. Be thorough but concise.\n"
        "Format for Telegram: *bold* for emphasis, scannable structure."
    ),
    "A3": (
        'You are Danielle "Dani" Moreau, Luxury Travel Concierge at '
        "Dreams2Memories Travel.\n"
        "You are warm, professional, and deeply knowledgeable about "
        "luxury travel.\n"
        "When speaking to clients: be personal, never templated. Lead "
        "with experience, not features.\n"
        "When briefing the Commander: be direct, include all operational "
        "details.\n"
        "Use tools to check real booking data, dossiers, and client "
        "records. NEVER fabricate.\n"
        "Format for Telegram: warm but concise."
    ),
    "A5": (
        'You are Lt Col Ryan "Viper" Castillo, A5 (Strategy & Revenue) '
        "at Dreams2Memories Travel.\n"
        "You focus on business strategy, revenue optimization, market "
        "positioning, and growth planning.\n"
        "Briefing the Commander via Telegram. Be strategic, data-driven, "
        "actionable.\n"
        "Format for Telegram: *bold* for emphasis, clear recommendations."
    ),
    "A6": (
        "You are Luna Voss, A6 (Itinerary & Narrative) at "
        "Dreams2Memories Travel.\n"
        "You create evocative, sensory travel narratives that sell the "
        "dream.\n"
        "Your writing is cinematic — movie trailer, not encyclopedia. "
        "Emotion first, logistics second.\n"
        "When the Commander asks for previews or itinerary content, "
        "write in your signature voice.\n"
        "Format for Telegram: your narrative voice, but adapted for "
        "mobile reading."
    ),
    "A9": (
        "You are Victor Harlan, A9 (Finance & Comptroller) at "
        "Dreams2Memories Travel.\n"
        "You handle commission tracking, payment status, cost analysis, "
        "and budget monitoring.\n"
        "Briefing the Commander via Telegram. Numbers, facts, flags. "
        "No fluff.\n"
        "Use tools to pull real financial data from Sheets. NEVER "
        "fabricate numbers.\n"
        "Format for Telegram: tables where possible, *bold* for alerts."
    ),
    "CH": (
        'You are Colonel James "Padre" Washington, Chaplain at '
        "Dreams2Memories Travel.\n"
        "You provide morale support, ethical guidance, and emotional "
        "grounding.\n"
        "Be warm, wise, and genuine. Short responses unless the "
        "situation calls for depth.\n"
        "Format for Telegram: personal, heartfelt."
    ),
    "A12": (
        "You are ELON, A12 (Technology & Innovation) at "
        "Dreams2Memories Travel.\n"
        "You handle system architecture, code review, technical "
        "research, and automation strategy.\n"
        "Briefing the Commander via Telegram. Be precise, technical, "
        "actionable.\n"
        "Format for Telegram: code blocks where relevant, *bold* for "
        "key points."
    ),
    "EXEC": (
        "You are Naia Solberg-Vega, EXEC (Brand & Visual Identity) at "
        "Dreams2Memories Travel.\n"
        "You own the D2M brand — navy/gold palette, luxury aesthetic, "
        "visual standards.\n"
        "Briefing the Commander via Telegram on brand, design, and "
        "visual direction.\n"
        "Format for Telegram: concise, visually-minded."
    ),
}

DEFAULT_SYSTEM_PROMPT = PERSONA_PROMPTS["COS"]


# ====================================================================
# SDK Import — handle both possible package names
# ====================================================================

_SDK_AVAILABLE = False
_sdk_query = None
_sdk_options_cls = None
_sdk_message_types = {}
_sdk_errors = {}

def _try_import_sdk():
    """Attempt to import the Claude Agent SDK, trying known package names."""
    global _SDK_AVAILABLE, _sdk_query, _sdk_options_cls
    global _sdk_message_types, _sdk_errors

    # Try the known package names in order of likelihood
    for pkg_name in ("claude_agent_sdk", "claude_code_sdk"):
        try:
            mod = __import__(pkg_name)

            _sdk_query = getattr(mod, "query", None)
            _sdk_options_cls = (
                getattr(mod, "ClaudeAgentOptions", None)
                or getattr(mod, "ClaudeCodeOptions", None)
            )

            # Message types
            for name in (
                "AssistantMessage",
                "UserMessage",
                "SystemMessage",
                "ResultMessage",
                "TextBlock",
                "ToolUseBlock",
                "ToolResultBlock",
            ):
                cls = getattr(mod, name, None)
                if cls:
                    _sdk_message_types[name] = cls

            # Error types
            for name in (
                "ClaudeSDKError",
                "CLINotFoundError",
                "CLIConnectionError",
                "ProcessError",
                "CLIJSONDecodeError",
            ):
                cls = getattr(mod, name, None)
                if cls:
                    _sdk_errors[name] = cls

            if _sdk_query and _sdk_options_cls:
                _SDK_AVAILABLE = True
                logger.info(
                    "Claude Agent SDK loaded from '%s' (query=%s, options=%s)",
                    pkg_name,
                    _sdk_query.__name__,
                    _sdk_options_cls.__name__,
                )
                return True
            else:
                logger.warning(
                    "Package '%s' imported but missing query() or options class",
                    pkg_name,
                )
        except ImportError:
            continue
        except Exception as exc:
            logger.warning("Failed to import '%s': %s", pkg_name, exc)
            continue

    logger.warning("Claude Agent SDK not available — will use CLI fallback")
    return False


# Run import on module load
_try_import_sdk()


# ====================================================================
# Safety Hook — PreToolUse blocker
# ====================================================================

async def _safety_hook(input_data: dict, tool_use_id: str = None,
                       context: Any = None) -> dict:
    """PreToolUse hook that blocks dangerous commands.

    Blocks:
      - rm -rf, shutdown, reboot, mkfs, dd
      - DROP TABLE, DROP DATABASE, TRUNCATE TABLE
      - Any Bash command modifying /etc or systemd paths
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only inspect Bash commands and Write/Edit operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        cmd_upper = command.upper()

        # Check blocked command patterns
        for pattern in BLOCKED_PATTERNS:
            if pattern.upper() in cmd_upper:
                reason = f"BLOCKED: dangerous command pattern '{pattern}' detected"
                logger.warning("Safety hook: %s — command: %s", reason, command[:200])
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }

        # Check blocked path prefixes
        for prefix in BLOCKED_PATH_PREFIXES:
            if prefix in command:
                reason = f"BLOCKED: modifying protected path '{prefix}'"
                logger.warning("Safety hook: %s — command: %s", reason, command[:200])
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }

    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        for prefix in BLOCKED_PATH_PREFIXES:
            if file_path.startswith(prefix):
                reason = f"BLOCKED: writing to protected path '{prefix}'"
                logger.warning("Safety hook: %s — path: %s", reason, file_path)
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }

    # Allow everything else
    return {}


# ====================================================================
# Intent Classifier (Claude Haiku — Max plan, $0)
# ====================================================================

def classify_intent(message: str) -> dict:
    """Classify a Commander's Telegram message into intent type and target.

    Returns: {"type": "TASK|ORDER|PRIORITY|APPROVE|SITREP",
              "target": "COS|A2|A3|...", "subject": "..."}

    Uses Claude Haiku via CLI subprocess (Max plan, $0). If it fails,
    defaults to TASK -> COS (safe fallback).
    """
    import subprocess

    prompt = (
        "Classify this Telegram message from the Commander.\n"
        "Return JSON only, no other text:\n"
        '{"type": "TASK|ORDER|PRIORITY|APPROVE|SITREP", '
        '"target": "A1|COS|A2|A3|A5|A6|A9|CH|A12|EXEC", '
        '"subject": "brief description"}\n\n'
        "TASK = specific action for a persona\n"
        "ORDER = standing directive / SOP change\n"
        "PRIORITY = urgent, drop everything\n"
        "APPROVE = approving/denying a pending item\n"
        "SITREP = status request\n\n"
        "If unclear, default to: "
        '{"type": "TASK", "target": "COS", "subject": "..."}\n'
        "Target mapping: radar/crenshaw=A1, hale/cos=COS, dembe=A2, dani=A3, "
        "castillo=A5, voss/luna=A6, harlan=A9, "
        "washington=CH, elon=A12, naia=EXEC\n\n"
        f"MESSAGE: {message}"
    )

    # Build mode-aware env (Max plan: strip key | Poe: set key+base_url)
    clean_env = build_api_env()

    cmd = [
        os.path.expanduser("~/.local/bin/claude"),
        "--print",
        "--model", "haiku",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",  # read prompt from stdin to avoid ARG_MAX
    ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30,
            env=clean_env,
        )

        if result.returncode != 0:
            logger.warning("Haiku classifier CLI failed (exit %d), defaulting to COS TASK", result.returncode)
            return {"type": "TASK", "target": "COS", "subject": message[:100]}

        content = result.stdout.strip()

        # Parse JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        parsed = json.loads(content)

        # Validate required fields
        if "type" not in parsed:
            parsed["type"] = "TASK"
        if "target" not in parsed:
            parsed["target"] = "COS"
        if "subject" not in parsed:
            parsed["subject"] = message[:100]

        return parsed

    except Exception as e:
        logger.warning("Haiku classifier failed (%s), defaulting to COS TASK", e)
        return {"type": "TASK", "target": "COS", "subject": message[:100]}


# ====================================================================
# MCP Configuration Loader
# ====================================================================

def _load_mcp_config() -> Optional[dict]:
    """Load MCP server config from ~/.claude/mcp.json if it exists.

    Returns dict suitable for passing as mcp_servers to the SDK,
    or None if no config found.
    """
    mcp_paths = [
        os.path.expanduser("~/.claude/mcp.json"),
        os.path.join(THUNDERBIRD_DIR, "mcp.json"),
    ]

    for path in mcp_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info("Loaded MCP config from %s", path)
                return config
            except Exception as e:
                logger.warning("Failed to load MCP config from %s: %s", path, e)

    return None


# ====================================================================
# Option 1 helper — probe SDK options class for thinking support
# ====================================================================

def _sdk_supports_thinking() -> bool:
    """Return True if the SDK options class accepts a 'thinking' parameter."""
    if not _sdk_options_cls:
        return False
    try:
        import dataclasses
        if dataclasses.is_dataclass(_sdk_options_cls):
            return "thinking" in {f.name for f in dataclasses.fields(_sdk_options_cls)}
        # Fallback: inspect __init__ signature
        import inspect
        sig = inspect.signature(_sdk_options_cls.__init__)
        return "thinking" in sig.parameters
    except Exception:
        return False

_SDK_HAS_THINKING: Optional[bool] = None  # cached after first probe


# ====================================================================
# Options 2+3 — Direct Anthropic client: caching + Files API + thinking
# ====================================================================

# Drafting keywords — if message contains any, activate draft_mode
_DRAFT_KEYWORDS = frozenset({
    "draft", "write", "email", "compose", "proposal", "letter",
    "message", "reply", "respond", "itinerary", "document", "memo",
    "subject", "dear", "hi ", "hello ", "warm regards",
})


def _is_draft_request(text: str) -> bool:
    """Return True if the message is a drafting request."""
    low = text.lower()
    return any(kw in low for kw in _DRAFT_KEYWORDS)


def _get_direct_client():
    """Get a direct Anthropic Python client using the global API key.

    Works in Max plan mode because ANTHROPIC_API_KEY is in the global env
    even though it's stripped from subprocess env for the claude CLI.
    Returns None if no API key is available.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        return anthropic.Anthropic()
    except Exception as e:
        logger.warning("Direct Anthropic client init failed: %s", e)
        return None


def _load_voice_card() -> str:
    """Load d2m_brand_voice.json as a formatted system-prompt block.

    Returns a compact but complete voice guide string, or "" on failure.
    Cached in memory after first load — file rarely changes.
    """
    if hasattr(_load_voice_card, "_cached"):
        return _load_voice_card._cached  # type: ignore[attr-defined]
    try:
        import json as _json
        voice_path = Path(os.path.dirname(os.path.abspath(__file__))) / "d2m_brand_voice.json"
        if not voice_path.exists():
            _load_voice_card._cached = ""
            return ""
        vc = _json.loads(voice_path.read_text())

        lines = ["# Commander Voice Card — John Loucks, Dreams2Memories Travel", ""]

        lines.append(f"**Opening:** {vc.get('opening_register', '')}")
        lines.append("")

        tr = vc.get("tense_rules", {})
        lines.append("**Tense rules:**")
        for k, v in tr.items():
            if k != "prohibition":
                lines.append(f"- {v}")
        if tr.get("prohibition"):
            lines.append(f"- NEVER: {tr['prohibition']}")
        lines.append("")

        lines.append(f"**Specificity:** {vc.get('specificity_standard', '')}")
        lines.append("")

        closers = vc.get("closing_variants", [])
        if closers:
            lines.append("**Closings:** " + " | ".join(c["text"] for c in closers))
        if vc.get("closing_prohibition"):
            lines.append(f"**Never close with:** {vc['closing_prohibition']}")
        lines.append("")

        forbidden = vc.get("forbidden_words", [])
        if forbidden:
            lines.append(f"**Forbidden words:** {', '.join(forbidden)}")
        lines.append("")

        lr = vc.get("length_rules", {})
        lines.append("**Length rules:**")
        for k, v in lr.items():
            lines.append(f"- {k.replace('_', ' ')}: {v}")
        lines.append("")

        rq = vc.get("required_qualities", [])
        if rq:
            lines.append("**Required qualities:**")
            for q in rq:
                lines.append(f"- {q}")
        lines.append("")

        vp = vc.get("voice_principles", {})
        if vp:
            lines.append("**Voice principles:**")
            for k, v in vp.items():
                lines.append(f"- {v}")
        lines.append("")

        lines.append(f"**Screenshot test:** {vc.get('screenshot_test', '')}")
        lines.append(f"**Human thread:** {vc.get('human_thread', '')}")

        result = "\n".join(lines)
        _load_voice_card._cached = result
        return result
    except Exception as e:
        logger.warning("Voice card load failed: %s", e)
        _load_voice_card._cached = ""
        return ""


_FORBIDDEN_VOICE_WORDS = [
    "automated", "system", "alert", "update", "platform", "portal",
    "algorithm", "AI", "bot", "notification", "generate", "process",
    "template", "workflow", "pipeline", "optimize", "leverage",
    "utilize", "facilitate", "stakeholder", "scalable", "synergy",
    "I hope this email finds you", "please don't hesitate",
    "as per", "please be advised", "kindly", "circling back",
]

_JUDGE_CRITERIA = """You are a strict voice editor for John Loucks, owner of Dreams2Memories Travel.

VOICE CRITERIA — every draft must pass all of these:
1. Opens with client's first name: "Hi [Name]," — never "Dear", "Hello there", or unnamed
2. 3–5 sentences for routine emails; earns more length only when combining payment + portal + relationship
3. At least one specific detail unique to THIS client (their name, a date, an amount, a place, a trip detail)
4. Closes with "Thanks, John" or "Thank you, John" — never "Best", "Warm regards", "Cheers", or "Sincerely"
5. Zero forbidden words/phrases: automated, system, alert, platform, portal, algorithm, AI, bot,
   notification, generate, process, template, workflow, optimize, leverage, utilize, facilitate,
   stakeholder, scalable, synergy, "I hope this email finds you", "please don't hesitate",
   "as per", "please be advised", "kindly", "circling back"
6. Warm and certain — NOT corporate, NOT verbose, NOT gushing

TASK:
Review the draft below. List each failing criterion (if any). Then rewrite the email fixing ONLY
the failures — keep all correct content intact. Return the rewritten email only, no explanation,
no preamble."""


_VALE_INI = Path(os.path.dirname(os.path.abspath(__file__))) / "config" / "vale" / ".vale.ini"
_VALE_BIN = Path.home() / ".local" / "bin" / "vale"


def _run_vale(draft: str) -> list[str]:
    """Run vale linter on draft text, return list of violation strings.

    Uses D2M style package (Tongue & Quill + Turabian rules).
    Returns [] if vale not installed or config missing — graceful degradation.
    """
    if not _VALE_BIN.exists() or not _VALE_INI.exists():
        return []
    try:
        import subprocess, tempfile, json as _json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(draft)
            tmp_path = f.name
        result = subprocess.run(
            [str(_VALE_BIN), "--config", str(_VALE_INI), "--output", "JSON", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
        Path(tmp_path).unlink(missing_ok=True)
        if result.stdout:
            data = _json.loads(result.stdout)
            violations = []
            for file_violations in data.values():
                for v in file_violations:
                    msg = v.get("Message", "")
                    line = v.get("Line", "?")
                    sev = v.get("Severity", "warning").upper()
                    violations.append(f"[{sev}] Line {line}: {msg}")
            return violations
    except Exception as e:
        logger.debug("vale lint failed: %s", e)
    return []


def _quick_voice_check(draft: str) -> list[str]:
    """Fast heuristic + vale lint check — returns list of failure strings, empty if passes."""
    failures = []
    stripped = draft.strip()

    if not re.match(r"^Hi \w", stripped, re.IGNORECASE):
        failures.append("Does not open with 'Hi [Name],'")

    word_count = len(stripped.split())
    if word_count > 150:
        failures.append(f"Too long ({word_count} words — target 3-5 sentences)")

    has_close = bool(re.search(r"\b(Thanks|Thank you),?\s*John\b", stripped, re.IGNORECASE))
    if not has_close:
        failures.append("Missing 'Thanks, John' or 'Thank you, John' close")

    draft_lower = stripped.lower()
    for word in _FORBIDDEN_VOICE_WORDS:
        if word.lower() in draft_lower:
            failures.append(f"Forbidden word/phrase: '{word}'")

    # Vale lint — Tongue & Quill + Turabian rules (line-level violations)
    vale_violations = _run_vale(draft)
    failures.extend(vale_violations)

    return failures


def _judge_revise_draft(draft: str, client: object) -> str:
    """Run judge-revisor pass on a draft. Returns revised draft if it fails voice check.

    1. Quick heuristic check — if passes, return draft unchanged (no API call)
    2. If fails, call direct Anthropic client with specific failure list + revision request
    3. Returns revised draft, or original if revision call fails
    """
    failures = _quick_voice_check(draft)
    if not failures:
        logger.debug("Voice check passed — no revision needed")
        return draft

    logger.info("Voice check failed (%d issues) — running revisor: %s", len(failures), failures)

    direct = _get_direct_client()
    if not direct:
        logger.debug("No direct client for revisor — returning original draft")
        return draft

    failure_list = "\n".join(f"- {f}" for f in failures)
    prompt = (
        f"{_JUDGE_CRITERIA}\n\n"
        f"ISSUES FOUND:\n{failure_list}\n\n"
        f"DRAFT TO REVISE:\n{draft}"
    )

    def _sync_revise() -> str:
        import anthropic
        try:
            resp = direct.messages.create(
                model="claude-haiku-4-5-20251001",  # Haiku — fast + cheap for revision
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip() if resp.content else draft
        except Exception:
            # Fall back to main model if Haiku unavailable
            try:
                resp = direct.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text.strip() if resp.content else draft
            except Exception as e2:
                logger.warning("Revisor call failed: %s", e2)
                return draft

    import asyncio
    loop = asyncio.get_event_loop()
    try:
        revised = loop.run_in_executor(None, _sync_revise)
        # run_in_executor returns a future — we need to run it synchronously here
        # since this is called from within an already-async context
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_sync_revise)
            revised = future.result(timeout=30)
        logger.info("Revisor complete — %d chars → %d chars", len(draft), len(revised))
        return revised
    except Exception as e:
        logger.warning("Revisor execution failed: %s", e)
        return draft


def _build_voice_examples_block(context: str, persona: str) -> str:
    """Return a few-shot system block with 5 real John emails matched to context.

    Pulls from config/voice_examples.json (built by thunderbird_voice_harvest.py).
    Returns "" if the library doesn't exist yet — graceful degradation.
    """
    try:
        from thunderbird_voice_harvest import get_voice_examples, format_few_shot_block
        # Client-facing personas use client tier; internal use internal
        tier = "client" if persona in ("A3", "EXEC", "A6", "CONCIERGE") else "internal"
        examples = get_voice_examples(context, tier=tier, n=5)
        if not examples:
            return ""
        return format_few_shot_block(examples)
    except Exception as e:
        logger.debug("Voice examples unavailable: %s", e)
        return ""


def _detect_client_dossiers(text: str) -> list[str]:
    """Detect client dossier names referenced in a message.

    Scans the Files API registry for dossiers whose names partially
    match words in the text. Returns list of dossier stems.
    """
    try:
        from thunderbird_files_api import list_registry
        registry = list_registry()
        text_lower = text.lower()
        found = []
        for entry in registry:
            dossier_name = entry.get("dossier", "")
            # Each word segment of the dossier name (e.g. "Furlow", "Westbrook")
            segments = [s for s in dossier_name.replace("_", " ").split() if len(s) > 3]
            if any(seg.lower() in text_lower for seg in segments):
                if dossier_name not in found:
                    found.append(dossier_name)
        return found
    except Exception as e:
        logger.debug("Dossier detection failed: %s", e)
        return []


def _build_dossier_blocks(dossier_names: list[str]) -> list[dict]:
    """Return Files API document blocks for a list of dossier names.

    Falls back to inline text if a dossier hasn't been synced to Files API.
    """
    try:
        from thunderbird_files_api import get_dossier_block_or_inline
        blocks = []
        for name in dossier_names:
            block = get_dossier_block_or_inline(name)
            if block:
                blocks.append(block)
                logger.info("Dossier injected for direct call: %s", name)
        return blocks
    except Exception as e:
        logger.debug("Dossier block build failed: %s", e)
        return []


async def _call_via_anthropic_direct(
    prompt: str,
    system_prompt: str,
    persona: str,
    client_context: str = "",
    on_progress: Optional[Callable] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Direct Anthropic client call: adaptive thinking + prompt caching + Files API.

    Used for drafting tasks (email, proposals, documents) where deep comprehension
    matters more than live MCP tool calls.

    Features activated:
    - Option 1: Adaptive thinking (effort=high) — reasons before drafting
    - Option 2: Cache_control on system prompt (1h TTL) — ~90% savings on repeats
    - Option 3: Files API dossier injection for detected clients

    Falls back to _call_via_sdk on any failure.
    """
    client = _get_direct_client()
    if not client:
        logger.info("No direct client available — SDK path")
        return await _call_via_sdk(prompt, system_prompt, persona,
                                   on_progress=on_progress, model=model)

    if on_progress:
        await on_progress("Analyzing context for drafting...")

    # Option 3: detect and inject client dossiers
    full_context = f"{client_context} {prompt}"
    dossier_names = _detect_client_dossiers(full_context)
    dossier_blocks = _build_dossier_blocks(dossier_names)
    if dossier_blocks and on_progress:
        n = len(dossier_blocks)
        await on_progress(f"Loading {n} client dossier{'s' if n > 1 else ''}...")

    # Option 2: cached system prompt (1h TTL — persona prompts are stable)
    system = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }
    ]

    # Voice card — inject Commander's writing style for all drafting tasks
    voice_card = _load_voice_card()
    if voice_card:
        system.append({
            "type": "text",
            "text": voice_card,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        })

    # Few-shot voice examples — 5 real John emails matched to this context
    voice_block = _build_voice_examples_block(full_context, persona)
    if voice_block:
        system.append({
            "type": "text",
            "text": voice_block,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        })

    # User message: dossier blocks first (context), then the request
    user_content: list[dict] = []
    user_content.extend(dossier_blocks)
    user_content.append({"type": "text", "text": prompt})

    if on_progress:
        await on_progress("Drafting with extended reasoning...")

    def _sync_call() -> str:
        import anthropic

        # Option 1: adaptive thinking + Option 3: Files API beta
        try:
            response = client.beta.messages.create(
                model=model,
                max_tokens=8192,
                thinking={"type": "adaptive", "effort": "high"},
                system=system,
                messages=[{"role": "user", "content": user_content}],
                betas=["files-api-2025-04-14"],
            )
        except anthropic.BadRequestError as e:
            # Thinking not supported for this model — retry without it
            logger.warning("Thinking not supported (%s), retrying without", e)
            response = client.beta.messages.create(
                model=model,
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                betas=["files-api-2025-04-14"],
            )

        # Log cache usage for diagnostics
        usage = getattr(response, "usage", None)
        if usage:
            logger.info(
                "Direct client cache — write: %s, read: %s, input: %s, output: %s",
                getattr(usage, "cache_creation_input_tokens", 0),
                getattr(usage, "cache_read_input_tokens", 0),
                getattr(usage, "input_tokens", 0),
                getattr(usage, "output_tokens", 0),
            )

        parts = [
            getattr(block, "text", "")
            for block in response.content
            if hasattr(block, "text")
        ]
        return "\n".join(parts).strip()

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_call),
            timeout=MAX_RESPONSE_TIME,
        )
        result = result or "No response generated."

        # Judge-revisor: check voice criteria, auto-revise if needed (Haiku, fast)
        if on_progress:
            await on_progress("Reviewing voice alignment...")
        result = _judge_revise_draft(result, client=None)

        return result
    except asyncio.TimeoutError:
        raise
    except Exception as e:
        logger.warning("Direct client failed (%s) — falling back to SDK", e)
        return await _call_via_sdk(prompt, system_prompt, persona,
                                   on_progress=on_progress, model=model)


# ====================================================================
# Core: SDK-based Agent Call
# ====================================================================

async def call_cos_via_sdk(
    message: str,
    persona: str = "COS",
    intent_type: str = "TASK",
    conversation_history: Optional[list[dict]] = None,
    session_id: Optional[str] = None,
    on_progress: Optional[Callable] = None,
    draft_mode: bool = False,
) -> dict:
    """Call Claude via Agent SDK (tool use) or direct client (drafting).

    draft_mode=True activates the direct Anthropic client path with:
      - Adaptive thinking (Option 1)
      - Prompt caching on system prompt (Option 2)
      - Files API dossier injection for detected clients (Option 3)

    draft_mode=False (default) uses the Agent SDK path with full MCP tool
    access — appropriate for research, sitrep, and agentic tasks.

    Args:
        message: Commander's raw message
        persona: Target persona ID (COS, A2, A3, etc.)
        intent_type: Classified intent (TASK, ORDER, PRIORITY, APPROVE, SITREP)
        conversation_history: Recent conversation for context
        session_id: Session ID for multi-turn conversations (None = new)
        on_progress: Async callback for streaming progress to Telegram.
        draft_mode: Use direct client with thinking+caching+Files API.

    Returns:
        {"response": str, "session_id": str}
    """
    # Resolve persona prompt
    system_prompt = PERSONA_PROMPTS.get(persona, DEFAULT_SYSTEM_PROMPT)

    # Build the full prompt with context
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"CURRENT DATE/TIME: {now}",
        f"COMMAND TYPE: {intent_type}",
        f"TARGET PERSONA: {persona}",
    ]

    if conversation_history:
        parts.append("\nRECENT CONVERSATION:")
        for msg in conversation_history[-6:]:
            speaker = "Commander" if msg.get("role") == "user" else "COS"
            text = msg.get("text", msg.get("content", ""))
            parts.append(f"  {speaker}: {text[:300]}")

    parts.append(f"\nCOMMANDER'S MESSAGE: {message}")
    full_prompt = "\n".join(parts)

    # Generate or reuse session ID
    if not session_id:
        session_id = str(uuid.uuid4())

    # ── Draft mode: direct Anthropic client with thinking+caching+Files API ──
    # Activated when draft_mode=True and an API key is available.
    # Falls back to SDK path automatically on any failure.
    if draft_mode and os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Draft mode: using direct Anthropic client (thinking+caching+Files API)")
        try:
            result = await _call_via_anthropic_direct(
                full_prompt, system_prompt, persona,
                client_context=message,
                on_progress=on_progress,
                model=DEFAULT_MODEL,
            )
            return {"response": result, "session_id": session_id}
        except asyncio.TimeoutError:
            logger.warning("Direct client timed out — falling through to SDK")
        except Exception as e:
            logger.warning("Direct client error (%s) — falling through to SDK", e)

    # ── Standard SDK path — full MCP tool access ──
    if _SDK_AVAILABLE:
        try:
            result = await _call_via_sdk(
                full_prompt, system_prompt, persona,
                on_progress=on_progress, model=DEFAULT_MODEL,
            )
            return {"response": result, "session_id": session_id}
        except asyncio.TimeoutError:
            logger.warning(
                "SDK call timed out on %s, retrying with %s",
                DEFAULT_MODEL, FALLBACK_MODEL,
            )
            if on_progress:
                await on_progress(
                    f"Opus timed out, switching to {FALLBACK_MODEL}..."
                )
            try:
                result = await _call_via_sdk(
                    full_prompt, system_prompt, persona,
                    on_progress=on_progress, model=FALLBACK_MODEL,
                )
                return {"response": result, "session_id": session_id}
            except Exception as e:
                logger.error("SDK fallback also failed: %s", e)

        except Exception as e:
            logger.error("SDK call failed: %s", e)
            if on_progress:
                await on_progress("SDK error, falling back to CLI...")

    # ── CLI fallback — always available ──
    logger.info("Using CLI subprocess fallback")
    result = await _call_via_cli_async(
        full_prompt, system_prompt, persona, model=DEFAULT_MODEL
    )
    return {"response": result, "session_id": session_id}


async def _call_via_sdk(
    prompt: str,
    system_prompt: str,
    persona: str,
    on_progress: Optional[Callable] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Internal: execute query via Claude Agent SDK with streaming.

    Returns the assembled text response.
    Raises asyncio.TimeoutError on timeout.
    """
    # Build options — the SDK handles tool routing, MCP, etc.
    options_kwargs: dict[str, Any] = {
        "system_prompt": system_prompt,
        "cwd": THUNDERBIRD_DIR,
        "permission_mode": "bypassPermissions",
    }

    # Set model and fallback
    options_kwargs["model"] = model
    if model == DEFAULT_MODEL:
        options_kwargs["fallback_model"] = FALLBACK_MODEL

    # Build mode-aware env for SDK subprocess
    options_kwargs["env"] = build_api_env()

    # Option 1: Adaptive thinking — probe SDK support once, then apply
    global _SDK_HAS_THINKING
    if _SDK_HAS_THINKING is None:
        _SDK_HAS_THINKING = _sdk_supports_thinking()
        logger.info("SDK thinking support: %s", _SDK_HAS_THINKING)
    if _SDK_HAS_THINKING:
        options_kwargs["thinking"] = {"type": "adaptive", "effort": "high"}

    # MCP config — let the SDK pick up from mcp.json automatically
    # The SDK inherits the user's ~/.claude/mcp.json when running
    # in the Thunderbird working directory.

    # Safety hooks
    try:
        # Try to import HookMatcher if available
        sdk_mod = sys.modules.get("claude_agent_sdk") or sys.modules.get("claude_code_sdk")
        HookMatcher = getattr(sdk_mod, "HookMatcher", None) if sdk_mod else None

        if HookMatcher:
            options_kwargs["hooks"] = {
                "PreToolUse": [
                    HookMatcher(matcher="Bash", hooks=[_safety_hook]),
                    HookMatcher(matcher="Write", hooks=[_safety_hook]),
                    HookMatcher(matcher="Edit", hooks=[_safety_hook]),
                ]
            }
        else:
            logger.debug("HookMatcher not available — safety hooks skipped")
    except Exception as e:
        logger.debug("Could not configure safety hooks: %s", e)

    options = _sdk_options_cls(**options_kwargs)

    # Collect response text from the streaming generator
    # ECHO PREVENTION: Track seen text to prevent duplicate blocks
    response_parts: list[str] = []
    _seen_text_hashes: set[int] = set()  # hash of each text block to dedup
    tool_notifications_sent: set[str] = set()
    _got_assistant_text = False  # True once we get text from AssistantMessage

    TextBlock = _sdk_message_types.get("TextBlock")
    ToolUseBlock = _sdk_message_types.get("ToolUseBlock")
    AssistantMessage = _sdk_message_types.get("AssistantMessage")
    ResultMessage = _sdk_message_types.get("ResultMessage")

    try:
        async with asyncio.timeout(MAX_RESPONSE_TIME):
            async for msg in _sdk_query(prompt=prompt, options=options):
                # Process AssistantMessage — contains text and tool use blocks
                if AssistantMessage and isinstance(msg, AssistantMessage):
                    content_list = getattr(msg, "content", [])
                    if not isinstance(content_list, (list, tuple)):
                        content_list = [content_list]

                    for block in content_list:
                        # Text content — accumulate for final response
                        if TextBlock and isinstance(block, TextBlock):
                            text = getattr(block, "text", str(block))
                            if text:
                                # ECHO GUARD: skip duplicate text blocks
                                text_hash = hash(text.strip())
                                if text_hash not in _seen_text_hashes:
                                    _seen_text_hashes.add(text_hash)
                                    response_parts.append(text)
                                    _got_assistant_text = True
                                else:
                                    logger.debug("Echo suppressed: duplicate text block (hash=%d)", text_hash)

                        # Tool use — send progress notification
                        elif ToolUseBlock and isinstance(block, ToolUseBlock):
                            tool_name = getattr(block, "name", "unknown")
                            tool_id = getattr(block, "id", tool_name)

                            if on_progress and tool_id not in tool_notifications_sent:
                                tool_notifications_sent.add(tool_id)
                                # Format a user-friendly progress message
                                tool_input = getattr(block, "input", {})
                                detail = _format_tool_progress(tool_name, tool_input)
                                try:
                                    await on_progress(detail)
                                except Exception as pe:
                                    logger.debug("Progress callback error: %s", pe)

                # ResultMessage — ONLY use if AssistantMessage yielded NO text.
                # The SDK's ResultMessage contains the full assembled text, which
                # is a superset of what AssistantMessage blocks already gave us.
                # Appending both causes the "echo" — so this is the fallback ONLY.
                elif ResultMessage and isinstance(msg, ResultMessage):
                    if not _got_assistant_text:
                        result_text = getattr(msg, "text", None)
                        if result_text:
                            text_hash = hash(result_text.strip())
                            if text_hash not in _seen_text_hashes:
                                _seen_text_hashes.add(text_hash)
                                response_parts.append(result_text)
                                logger.debug("Using ResultMessage text (no AssistantMessage text received)")
                    else:
                        logger.debug("Skipping ResultMessage — already have AssistantMessage text (echo prevention)")

    except asyncio.TimeoutError:
        raise
    except Exception as e:
        # Check for known SDK errors
        ProcessError = _sdk_errors.get("ProcessError")
        if ProcessError and isinstance(e, ProcessError):
            logger.error("SDK process error (exit %s): %s",
                         getattr(e, "exit_code", "?"), e)
        raise

    response = "\n".join(response_parts).strip()

    # CLEAN VERBOSE OUTPUT — strip internal narration that leaks from CLI
    # The SDK streams text blocks that include Claude's "thinking out loud"
    # lines meant for terminal display, not Telegram delivery.
    _narration_prefixes = (
        "Let me ", "Good,", "Good.", "Now let me ", "I see ", "I'll ",
        "Got it", "Got the ", "Found it", "Searching ", "Reading ",
        "Let me check", "Let me pull", "Let me read", "Let me search",
        "Let me find", "Now I", "Now fetching", "Now searching",
        "Thread fully read", "I have all", "Full picture",
        "INTEL CONSOLIDATED", "Draft already exists",
    )
    if response_parts and len(response_parts) > 1:
        # Keep only the LAST substantial text block — that's the actual answer.
        # Earlier blocks are typically narration ("Let me read...", "Searching...")
        cleaned_parts = []
        for part in response_parts:
            lines = part.strip().split("\n")
            # Skip blocks that are ONLY narration (no structured content)
            first_line = lines[0].strip() if lines else ""
            is_narration = (
                first_line.startswith(_narration_prefixes) and
                len(lines) < 4 and
                not any(c in part for c in ["**", "##", "| ", "✅", "📋", "---"])
            )
            if not is_narration:
                cleaned_parts.append(part)
        if cleaned_parts:
            response = "\n".join(cleaned_parts).strip()
        # else keep original response — don't return empty

    if not response:
        response = (
            "COS reporting: Agent completed but returned no text. "
            "The task may have been executed via tools — check results."
        )

    # Truncate for Telegram pipeline
    if len(response) > 16000:
        response = response[:16000] + "\n\n[Response truncated for Telegram]"

    return response


_MCP_TOOL_LABELS: dict[str, str] = {
    # Gmail
    "gmail_search_messages": "Searching Gmail",
    "gmail_read_message": "Reading email",
    "gmail_read_thread": "Reading email thread",
    "gmail_create_draft": "Drafting email",
    "gmail_update_draft": "Updating draft",
    "gmail_list_drafts": "Loading drafts",
    "gmail_list_labels": "Loading labels",
    "run_dani_email_sweep": "Running email sweep",
    "run_commander_inbox_sweep_tool": "Sweeping Commander inbox",
    "scan_commander_inbox_tool": "Scanning Commander inbox",
    "draft_client_email": "Drafting client email",
    # Drive
    "drive_list_files": "Scanning Drive",
    "drive_search": "Searching Drive",
    "drive_read_document": "Reading document",
    "drive_upload_file": "Uploading to Drive",
    "drive_create_folder": "Creating Drive folder",
    # Dossiers & booking
    "list_trip_dossiers": "Loading dossiers",
    "scan_dossiers": "Scanning dossiers",
    "list_dossier_files": "Loading dossier files",
    "extract_booking_from_pdf": "Reading booking PDF",
    "extract_pdf_booking_details": "Parsing booking PDF",
    "extract_master_booking_data": "Extracting booking data",
    "reconcile_booking_tool": "Reconciling booking",
    "reconcile_all_bookings_tool": "Reconciling all bookings",
    "sync_booking_to_excel": "Syncing to Booking Master",
    "compute_booking_anchors": "Computing booking anchors",
    "sync_anchors_to_calendar": "Syncing to calendar",
    # TESS
    "tess_get_booking": "Fetching booking from TESS",
    "tess_search_bookings": "Searching TESS bookings",
    "tess_list_clients": "Loading TESS client list",
    "tess_get_client": "Fetching client from TESS",
    "tess_get_trip": "Fetching trip from TESS",
    "tess_get_commissions": "Fetching commissions",
    "tess_list_trips": "Loading trips from TESS",
    # Travel search
    "search_flights": "Searching flights",
    "search_hotels": "Searching hotels",
    "search_tours": "Searching tours",
    "search_shore_excursions_group": "Searching excursions",
    "search_live_cruise_voyages": "Searching cruise voyages",
    "check_hotel_rates": "Checking hotel rates",
    "check_departure_prices": "Checking departure prices",
    "compare_flights": "Comparing flights",
    "compare_hotels": "Comparing hotels",
    # Intel & research
    "get_innovation_digest": "Loading innovation digest",
    "run_innovation_scan": "Running innovation scan",
    "innovation_daily_scan": "Running daily intel scan",
    "get_tech_news": "Fetching tech news",
    "academic_scan": "Running academic scan",
    "get_country_intel": "Gathering country intel",
    "get_port_city_intel": "Gathering port intel",
    "run_world_intelligence_sweep": "Running world intel sweep",
    "run_ship_intelligence_sweep": "Running ship intel sweep",
    "run_competitive_surveillance": "Running competitive scan",
    "run_intel_crew": "Running intel crew",
    # Keep / calendar
    "keep_list_notes": "Checking Keep notes",
    "keep_create_note": "Writing Keep note",
    "keep_search_notes": "Searching Keep",
    "gcal_list_events": "Checking calendar",
    "gcal_create_event": "Creating calendar event",
    # Learning / voice
    "learning_capture_diff": "Capturing learning diff",
    "learning_extract": "Extracting principles",
    "voice_ledger_get": "Loading voice ledger",
    "recall_persona_memory": "Recalling persona memory",
    # Misc
    "session_checkpoint": "Writing session checkpoint",
    "system_health_check": "Running health check",
    "mcp_connector_status": "Checking MCP status",
    "generate_weekly_report": "Generating weekly report",
    "run_staff_meeting": "Convening staff meeting",
    "consult_persona": "Consulting persona",
}


def _format_tool_progress(tool_name: str, tool_input: dict) -> str:
    """Format a tool use event into a human-readable progress string."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        return f"Running: {cmd}"
    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        return f"Reading: {os.path.basename(path)}"
    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        return f"Writing: {os.path.basename(path)}"
    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        return f"Editing: {os.path.basename(path)}"
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"Searching: {pattern[:40]}"
    elif tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        short_name = parts[-1] if len(parts) > 1 else tool_name
        return _MCP_TOOL_LABELS.get(short_name, f"MCP: {short_name}")
    else:
        return f"Using tool: {tool_name}"


# ====================================================================
# CLI Subprocess Fallback — async wrapper
# ====================================================================

async def _call_via_cli_async(
    prompt: str,
    system_prompt: str,
    persona: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Async wrapper around the CLI subprocess fallback.

    Used when the SDK is not available or fails.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _call_via_cli_sync,
        prompt, system_prompt, persona, model,
    )


def _call_via_cli_sync(
    prompt: str,
    system_prompt: str,
    persona: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Synchronous CLI subprocess call — the original v2 approach."""
    import subprocess

    cmd = [
        CLAUDE_CMD,
        "--print",
        "--system-prompt", system_prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",  # read prompt from stdin to avoid ARG_MAX on large emails
    ]

    # Build mode-aware env (Max plan: strip key | Poe: set key+base_url)
    clean_env = build_api_env()
    clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    logger.info(
        "CLI fallback: calling Claude as %s (%s): %s",
        persona, model, prompt[:80],
    )

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=MAX_RESPONSE_TIME,
            cwd=THUNDERBIRD_DIR,
            env=clean_env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "No stderr"
            logger.error(
                "CLI failed (exit %d): %s", result.returncode, stderr
            )
            if model == DEFAULT_MODEL:
                logger.info("Retrying CLI with %s...", FALLBACK_MODEL)
                return _call_via_cli_sync(
                    prompt, system_prompt, persona, model=FALLBACK_MODEL
                )
            return f"COS reporting: CLI execution failed. Error: {stderr[:200]}"

        response = result.stdout.strip()
        if not response:
            return "COS reporting: Claude returned empty response. Retrying may help."

        if len(response) > 16000:
            response = response[:16000] + "\n\n[Response truncated for Telegram]"

        # Log Poe point consumption (estimated from char count when no token data)
        log_usage(
            persona=persona,
            model=model,
            input_tokens=estimate_from_text(prompt),
            output_tokens=estimate_from_text(response),
            source="telegram_cli",
        )

        return response

    except subprocess.TimeoutExpired:
        logger.error("CLI timed out after %ds", MAX_RESPONSE_TIME)
        return (
            f"COS reporting: Request timed out after {MAX_RESPONSE_TIME}s. "
            "Consider breaking into smaller requests."
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found at %s", CLAUDE_CMD)
        return "COS reporting: Claude CLI not found on this system."
    except Exception as e:
        logger.error("CLI call failed: %s", e)
        return f"COS reporting: Unexpected error — {str(e)[:200]}"


# ====================================================================
# Legacy Compatibility — synchronous wrapper
# ====================================================================

def call_cos_with_tools(
    query: str,
    conversation_history: Optional[list[dict]] = None,
) -> str:
    """Legacy entry point — synchronous wrapper for backward compatibility.

    This matches the function signature from thunderbird_telegram_tools_v2.py
    so thunderbird_telegram.py doesn't need to change its import.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (e.g., called from Telegram handler).
        # Create a new thread to run the async function.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                call_cos_via_sdk(
                    message=query,
                    persona="COS",
                    intent_type="TASK",
                    conversation_history=conversation_history,
                ),
            )
            result = future.result(timeout=MAX_RESPONSE_TIME + 30)
        return result.get("response", "COS reporting: No response generated.")
    else:
        # No event loop running — safe to use asyncio.run
        result = asyncio.run(
            call_cos_via_sdk(
                message=query,
                persona="COS",
                intent_type="TASK",
                conversation_history=conversation_history,
            )
        )
        return result.get("response", "COS reporting: No response generated.")


def call_cos_via_cli(
    message: str,
    persona: str = "COS",
    intent_type: str = "TASK",
    conversation_history: Optional[list[dict]] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Legacy compatibility: wraps call_cos_via_sdk synchronously.

    Matches the v2 function signature used in thunderbird_telegram.py.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                call_cos_via_sdk(
                    message=message,
                    persona=persona,
                    intent_type=intent_type,
                    conversation_history=conversation_history,
                ),
            )
            result = future.result(timeout=MAX_RESPONSE_TIME + 30)
        return result.get("response", "COS reporting: No response generated.")
    else:
        result = asyncio.run(
            call_cos_via_sdk(
                message=message,
                persona=persona,
                intent_type=intent_type,
                conversation_history=conversation_history,
            )
        )
        return result.get("response", "COS reporting: No response generated.")


# ====================================================================
# Quick test
# ====================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    test_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "What bookings do we have active?"
    )

    print(f"\n{'=' * 60}")
    print(f"Thunderbird Telegram Tools — Phase 2 (Agent SDK)")
    print(f"{'=' * 60}")
    print(f"SDK available: {_SDK_AVAILABLE}")
    print(f"Query: {test_query}")
    print(f"{'=' * 60}")

    # Test classifier
    intent = classify_intent(test_query)
    print(f"\nIntent classification: {json.dumps(intent, indent=2)}")

    # Test SDK call
    async def _test():
        async def progress_cb(msg: str):
            print(f"  [progress] {msg}")

        result = await call_cos_via_sdk(
            message=test_query,
            persona=intent.get("target", "COS"),
            intent_type=intent.get("type", "TASK"),
            on_progress=progress_cb,
        )
        return result

    print(f"\nCalling Claude as {intent.get('target', 'COS')}...\n")
    result = asyncio.run(_test())
    print(f"\nSession ID: {result['session_id']}")
    print(f"\n{result['response']}")
