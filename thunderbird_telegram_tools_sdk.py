"""
Thunderbird Telegram Tools — Phase 2: Claude Agent SDK
=======================================================

Replaces the `claude --print` subprocess approach with the Claude Agent SDK
for streaming, hooks, sessions, and custom tools.

Architecture:
  1. Telegram message arrives, classified by Claude (Max plan, $0)
  2. This module calls the Claude Agent SDK with persona system prompt
  3. Claude Opus runs in ~/Thunderbird/ with full MCP tool access
  4. Streaming progress callbacks sent to Telegram as the agent works
  5. Response returned to Telegram

Cost: $0 (Max plan OAuth — ANTHROPIC_API_KEY stripped from env)
Quality: S-tier (Opus 4.6) for every persona, Sonnet fallback on timeout

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

# ── Strip ANTHROPIC_API_KEY so SDK uses Max plan OAuth ($0) ──
# This MUST happen before any SDK import to prevent the SDK from
# picking up a pay-per-token API key.
if "ANTHROPIC_API_KEY" in os.environ:
    logger.info("Stripping ANTHROPIC_API_KEY from env — using Max plan OAuth")
    del os.environ["ANTHROPIC_API_KEY"]

# ── Config ──
THUNDERBIRD_DIR = os.path.expanduser("~/Thunderbird")
CLAUDE_CMD = os.path.expanduser("~/.local/bin/claude")
MAX_RESPONSE_TIME = 180  # seconds
DEFAULT_MODEL = "opus"
FALLBACK_MODEL = "sonnet"


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

    # Strip ANTHROPIC_API_KEY so CLI uses Max plan OAuth ($0)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    cmd = [
        os.path.expanduser("~/.local/bin/claude"),
        "--print",
        "--model", "haiku",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
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
# Core: SDK-based Agent Call
# ====================================================================

async def call_cos_via_sdk(
    message: str,
    persona: str = "COS",
    intent_type: str = "TASK",
    conversation_history: Optional[list[dict]] = None,
    session_id: Optional[str] = None,
    on_progress: Optional[Callable] = None,
) -> dict:
    """Call Claude Opus via the Agent SDK. Cost: $0 (Max plan).

    This is the primary entry point for all Telegram -> Claude communication
    in Phase 2. Supports streaming progress, safety hooks, and session
    persistence.

    Args:
        message: Commander's raw message
        persona: Target persona ID (COS, A2, A3, etc.)
        intent_type: Classified intent (TASK, ORDER, PRIORITY, APPROVE, SITREP)
        conversation_history: Recent conversation for context
        session_id: Session ID for multi-turn conversations (None = new)
        on_progress: Async callback for streaming progress to Telegram.
                     Called with (str) progress messages as the agent works.

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

    # Try SDK first, fall back to CLI subprocess
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
                # Fall through to CLI fallback

        except Exception as e:
            logger.error("SDK call failed: %s", e)
            if on_progress:
                await on_progress("SDK error, falling back to CLI...")
            # Fall through to CLI fallback

    # CLI fallback — always available
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

    # Ensure ANTHROPIC_API_KEY is NOT passed to the SDK subprocess
    options_kwargs["env"] = {
        k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"
    }

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
        # MCP tool — extract the tool name part
        parts = tool_name.split("__")
        short_name = parts[-1] if len(parts) > 1 else tool_name
        return f"MCP tool: {short_name}"
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
        "-p", prompt,
    ]

    # Build clean env without ANTHROPIC_API_KEY
    clean_env = {
        k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"
    }
    clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    logger.info(
        "CLI fallback: calling Claude as %s (%s): %s",
        persona, model, prompt[:80],
    )

    try:
        result = subprocess.run(
            cmd,
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
