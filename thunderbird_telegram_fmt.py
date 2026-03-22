"""
Thunderbird Telegram Formatting Utilities
==========================================
Dreams2Memories Travel, LLC

Centralizes all Telegram message formatting:
  - MarkdownV2 conversion via telegramify-markdown
  - Safe escape for plain text strings
  - Smart message splitting (newline-aware, not mid-word)
  - Structured output Pydantic schemas for Claude API
  - Table rendering via monospace blocks (Telegram has no native tables)

Both telegram bots import from here.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("thunderbird_telegram_fmt")

# ── MarkdownV2 conversion ─────────────────────────────────────────────────────

def md_to_telegram(text: str) -> str:
    """Convert Claude's natural markdown output to Telegram MarkdownV2.

    Uses telegramify-markdown to handle escaping, bold/italic/code conversion,
    and character safety. Falls back to plain-text strip on any error.

    Claude produces ## headers, **bold**, _italic_, bullet lists, `code` —
    this converts all of it to safe MarkdownV2.
    """
    try:
        from telegramify_markdown import markdownify
        return markdownify(text)
    except ImportError:
        logger.warning("telegramify-markdown not installed — falling back to escape_md2")
        return escape_md2(text)
    except Exception as e:
        logger.warning("md_to_telegram failed (%s) — stripping formatting", e)
        return strip_markdown(text)


def escape_md2(text: str) -> str:
    """Escape a plain-text string for safe use inside MarkdownV2 messages.

    Use this for dynamic values (prices, names, dates) being inserted into
    a manually-constructed MarkdownV2 template. Do NOT use on already-formatted
    markdown — use md_to_telegram() for that.

    MarkdownV2 requires escaping these 18 chars outside formatting blocks:
      _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    special = r'\_*[]()~`>#+-=|{}.!'
    result = []
    for char in text:
        if char in special:
            result.append('\\')
        result.append(char)
    return ''.join(result)


def strip_markdown(text: str) -> str:
    """Strip all markdown formatting, return plain text (safe Telegram fallback)."""
    # Remove common markdown markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    return text


# ── Message splitting ─────────────────────────────────────────────────────────

MAX_TELEGRAM_LENGTH = 4096


def split_message(text: str, max_length: int = MAX_TELEGRAM_LENGTH) -> list[str]:
    """Split a message into Telegram-safe chunks without breaking mid-word or mid-format.

    Strategy:
    1. Try to split on paragraph breaks (double newline)
    2. Fall back to single newlines
    3. Fall back to word boundaries
    4. Hard-cut as last resort

    Returns list of strings each <= max_length.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_length:
        # Try double-newline paragraph split
        split_pos = remaining.rfind('\n\n', 0, max_length)
        if split_pos == -1 or split_pos < max_length // 2:
            # Try single newline
            split_pos = remaining.rfind('\n', 0, max_length)
        if split_pos == -1 or split_pos < max_length // 3:
            # Try space (word boundary)
            split_pos = remaining.rfind(' ', 0, max_length)
        if split_pos == -1:
            # Hard cut
            split_pos = max_length

        chunks.append(remaining[:split_pos].strip())
        remaining = remaining[split_pos:].lstrip()

    if remaining.strip():
        chunks.append(remaining.strip())

    return [c for c in chunks if c]


# ── Table rendering ───────────────────────────────────────────────────────────

def render_table(headers: list[str], rows: list[list[str]],
                 col_sep: str = " │ ") -> str:
    """Render a table as a MarkdownV2 monospace code block.

    Telegram has no native table support. This produces a code block with
    aligned columns using Unicode box-drawing characters.

    Returns a MarkdownV2-safe ```code block``` string.
    """
    if not headers or not rows:
        return ""

    # Compute column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            width = col_widths[i] if i < len(col_widths) else 0
            parts.append(str(cell).ljust(width))
        return col_sep.join(parts)

    separator = "─" * (sum(col_widths) + len(col_sep) * (len(headers) - 1))

    lines = [fmt_row(headers), separator]
    for row in rows:
        lines.append(fmt_row(row))

    inner = "\n".join(lines)
    return f"```\n{inner}\n```"


# ── Pydantic schemas for Claude structured output ─────────────────────────────

try:
    from pydantic import BaseModel

    class PersonaSection(BaseModel):
        """A single section in a persona response."""
        header: str
        content: str
        bullets: list[str] = []

    class PersonaResponse(BaseModel):
        """Structured response from any Wing persona.

        Used with client.messages.parse() for consistent Telegram formatting.
        Guarantees valid structure; no markdown parsing errors.
        """
        persona: str                   # e.g. "COS", "A3", "A9"
        summary: str                   # One-sentence bottom line
        sections: list[PersonaSection] # Detailed sections
        action_items: list[str] = []   # Numbered action items if applicable
        flags: list[str] = []          # CRITICAL/WARNING flags (shown in red equivalent)

    class SitrepBrief(BaseModel):
        """Structured SITREP for Commander consumption via Telegram."""
        status: str                     # GREEN / AMBER / RED
        active_bookings: list[str]      # One line per booking
        pending_actions: list[str]      # Deadlines and tasks
        flags: list[str] = []           # Issues needing Commander attention
        system_health: str = "NOMINAL"  # System status line

    class DraftEmail(BaseModel):
        """Structured email draft for Commander review before send."""
        to: str
        subject: str
        body: str                       # Full email body in plain text
        tone_notes: str = ""            # Notes on tone/relationship adjustments
        send_ready: bool = False        # True only if Dani considers it send-ready

    _PYDANTIC_AVAILABLE = True

except ImportError:
    _PYDANTIC_AVAILABLE = False
    PersonaResponse = None
    SitrepBrief = None
    DraftEmail = None
    logger.warning("Pydantic not installed — structured output schemas unavailable")


# ── Formatting helpers for structured output → Telegram ──────────────────────

def sitrep_to_telegram(brief) -> str:
    """Convert a SitrepBrief to a Telegram MarkdownV2 string."""
    status_icon = {"GREEN": "✅", "AMBER": "⚠️", "RED": "🔴"}.get(
        getattr(brief, "status", "GREEN"), "📊"
    )
    lines = [f"{status_icon} *SITREP — {escape_md2(brief.status)}*", ""]

    if brief.active_bookings:
        lines.append("*Active Bookings*")
        for b in brief.active_bookings:
            lines.append(f"• {escape_md2(b)}")
        lines.append("")

    if brief.pending_actions:
        lines.append("*Pending Actions*")
        for a in brief.pending_actions:
            lines.append(f"• {escape_md2(a)}")
        lines.append("")

    if brief.flags:
        lines.append("*⚑ Flags*")
        for f in brief.flags:
            lines.append(f"• {escape_md2(f)}")
        lines.append("")

    lines.append(f"_System: {escape_md2(brief.system_health)}_")
    return "\n".join(lines)


def persona_response_to_telegram(resp) -> str:
    """Convert a PersonaResponse to a Telegram MarkdownV2 string."""
    lines = [f"*{escape_md2(resp.summary)}*", ""]

    for section in resp.sections:
        lines.append(f"*{escape_md2(section.header)}*")
        if section.content:
            lines.append(escape_md2(section.content))
        for bullet in section.bullets:
            lines.append(f"• {escape_md2(bullet)}")
        lines.append("")

    if resp.action_items:
        lines.append("*Action Items*")
        for i, item in enumerate(resp.action_items, 1):
            lines.append(f"{i}\\. {escape_md2(item)}")
        lines.append("")

    if resp.flags:
        lines.append("*⚑ Flags*")
        for flag in resp.flags:
            lines.append(f"• {escape_md2(flag)}")

    return "\n".join(lines).strip()


def draft_email_to_telegram(draft) -> str:
    """Convert a DraftEmail to a Telegram MarkdownV2 preview for Commander review."""
    ready = "✅ Send\\-ready" if draft.send_ready else "⚠️ Needs review"
    lines = [
        f"*Draft Email* — {ready}",
        "",
        f"*To:* {escape_md2(draft.to)}",
        f"*Subject:* {escape_md2(draft.subject)}",
        "",
        "```",
        draft.body[:2000],  # Truncate body in preview
        "```",
    ]
    if draft.tone_notes:
        lines.extend(["", f"_Tone notes: {escape_md2(draft.tone_notes)}_"])
    return "\n".join(lines)


# ── Async send helper (use in bot handlers) ───────────────────────────────────

async def send_telegram(update, text: str, use_md2: bool = True,
                        fallback_plain: bool = True) -> None:
    """Send a message to Telegram with MarkdownV2 and intelligent fallback.

    1. Try MarkdownV2 (best formatting)
    2. Fall back to HTML if MarkdownV2 fails
    3. Fall back to plain text if HTML fails

    Splits long messages automatically.
    """
    from telegram.constants import ParseMode

    chunks = split_message(text)

    for chunk in chunks:
        if not chunk:
            continue

        if use_md2:
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
                continue
            except Exception as e:
                logger.debug("MarkdownV2 send failed (%s) — trying HTML", e)

        # HTML fallback
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            continue
        except Exception as e:
            logger.debug("HTML send failed (%s) — plain text", e)

        if fallback_plain:
            await update.message.reply_text(strip_markdown(chunk))


async def send_claude_response(update, text: str) -> None:
    """Send Claude's markdown response to Telegram, auto-converted to MarkdownV2.

    This is the standard path for all persona/COS responses.
    Converts Claude's natural ## **bold** _italic_ markdown → Telegram MarkdownV2.
    """
    converted = md_to_telegram(text)
    await send_telegram(update, converted, use_md2=True)
