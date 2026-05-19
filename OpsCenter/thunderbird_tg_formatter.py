#!/usr/bin/env python3
"""
thunderbird_tg_formatter.py — 5-Stage Output Formatter Pipeline
Thunderbird Wing / Dreams2Memories Travel, LLC

Stage 1: STRIP   — Remove ANSI codes, tool XML, noise lines, excess blank lines
Stage 2: EXTRACT — Pull final-answer section if tool use was detected
Stage 3: FORMAT  — Markdown → Telegram HTML (parse_mode='HTML')
Stage 4: CHUNK   — Split into ≤4000-char pieces at paragraph boundaries
Output:  list[str] of HTML strings, each ≤4000 chars, ready to send

Unit-testable: import and call process(raw_string) → [chunks]
"""

import re
from typing import List

# ── Stage 1: STRIP ───────────────────────────────────────────────────────────

# ANSI escape sequences (color codes, cursor moves, etc.)
_ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)')

# Claude tool call XML blocks — full block with content
_TOOL_BLOCKS = re.compile(
    r'\[(?:use_mcp_tool|bash|result|thinking|tool_use|tool_result|'
    r'function_call|invoke|parameters|artifact|antml:thinking|antThinking)\]'
    r'.*?'
    r'\[/(?:use_mcp_tool|bash|result|thinking|tool_use|tool_result|'
    r'function_call|invoke|parameters|artifact|antml:thinking|antThinking)\]',
    re.DOTALL | re.IGNORECASE,
)

# Orphaned open/close tags left after block removal
_TOOL_TAGS = re.compile(
    r'\[/?(?:use_mcp_tool|bash|result|thinking|tool_use|tool_result|'
    r'function_call|invoke|parameters|artifact|antml:\w+)\]',
    re.IGNORECASE,
)

# Noise line patterns (matched line by line after split)
_NOISE_LINES = [
    re.compile(r'^(?:INFO|DEBUG|WARNING|TRACE|ERROR):\s+', re.IGNORECASE),
    re.compile(r'[█░▓▒]{4,}'),                        # progress bars
    re.compile(r'^\s*\d+%\s*[\|█▊▋▌▍▎▏]'),            # percentage bars
    re.compile(r'^\s*\[[\d.]+s\]\s'),                  # [0.23s] timer lines
    re.compile(r'^✓\s+.*(?:tool|calling|result|done)', re.IGNORECASE),  # agent tool announce
    re.compile(r'^Using tool:\s'),
    re.compile(r'^Tool result:\s'),
    re.compile(r'^─{10,}$'),                            # pure divider lines
    re.compile(r'^={10,}$'),
]


def _stage1_strip(text: str) -> str:
    """Remove ANSI, tool XML blocks, noise lines, collapse blank lines."""
    # ANSI codes
    text = _ANSI.sub('', text)

    # Tool XML blocks (multi-line)
    text = _TOOL_BLOCKS.sub('', text)
    text = _TOOL_TAGS.sub('', text)

    # Noise lines — filter line by line
    lines = []
    for line in text.split('\n'):
        noisy = False
        for pat in _NOISE_LINES:
            if pat.search(line):
                noisy = True
                break
        if not noisy:
            lines.append(line)
    text = '\n'.join(lines)

    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ── Stage 2: EXTRACT ─────────────────────────────────────────────────────────

def _stage2_extract(text: str) -> str:
    """
    If output clearly has a preamble (tool use) followed by final answer,
    extract just the final answer. Otherwise return text unchanged.
    """
    lines = text.split('\n')
    total = len(lines)

    # Only attempt extraction if output is substantial (>8 lines)
    if total < 8:
        return text

    # Look for strong dividers or final-answer headers in the latter 70%
    for i, line in enumerate(lines):
        s = line.strip()
        if i < int(total * 0.30):
            continue  # Skip first 30%

        # Strong separator line (---, ===, ***) followed by content
        if s in ('---', '===', '***', '────────────────────', '━━━━━━━━━━━━━━━━━━━━'):
            after = '\n'.join(lines[i + 1:]).strip()
            if len(after) > 80:
                return after

        # Explicit final-answer header
        if re.match(r'^#+\s*(?:Final Answer|Response|Summary|Result|Output)\s*$', s, re.IGNORECASE):
            after = '\n'.join(lines[i + 1:]).strip()
            if len(after) > 50:
                return after

    return text


# ── Stage 3: FORMAT (Markdown → Telegram HTML) ───────────────────────────────

def _escape_html(text: str) -> str:
    """Escape the three HTML special chars for Telegram HTML mode."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _stage3_format(text: str) -> str:
    """
    Convert markdown formatting to Telegram HTML.
    Preserves code blocks and tables in <pre> blocks.
    Converts **bold**, # headers, `inline code`, bullet points.
    """
    # ── Protected zones: extract first, restore after escaping ───────────────
    protected: dict[str, str] = {}
    counter = [0]

    def protect(html_val: str) -> str:
        key = f'\x00P{counter[0]}\x00'
        protected[key] = html_val
        counter[0] += 1
        return key

    # Fenced code blocks  ```lang\ncode\n```
    def _replace_code_block(m: re.Match) -> str:
        lang = (m.group(1) or '').strip()
        code = _escape_html(m.group(2) if m.group(2) else '')
        if lang:
            return protect(f'<pre><code class="language-{lang}">{code}</code></pre>')
        return protect(f'<pre>{code}</pre>')

    text = re.sub(r'```(\w*)\n?(.*?)```', _replace_code_block, text, flags=re.DOTALL)

    # Inline code  `code`
    def _replace_inline_code(m: re.Match) -> str:
        return protect(f'<code>{_escape_html(m.group(1))}</code>')

    text = re.sub(r'`([^`\n]+)`', _replace_inline_code, text)

    # Markdown tables — detect blocks of lines that look like tables
    table_buf: list[str] = []
    result_lines: list[str] = []

    for line in text.split('\n'):
        if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
            table_buf.append(line)
        else:
            if table_buf:
                raw_table = '\n'.join(table_buf)
                result_lines.append(protect(f'<pre>{_escape_html(raw_table)}</pre>'))
                table_buf = []
            result_lines.append(line)

    if table_buf:
        raw_table = '\n'.join(table_buf)
        result_lines.append(protect(f'<pre>{_escape_html(raw_table)}</pre>'))

    text = '\n'.join(result_lines)

    # ── Escape remaining plain text ───────────────────────────────────────────
    # Only escape if not inside a protected zone
    # Split on protected keys, escape segments between them
    parts = re.split(r'(\x00P\d+\x00)', text)
    escaped_parts = []
    for part in parts:
        if part.startswith('\x00P') and part.endswith('\x00'):
            escaped_parts.append(part)  # placeholder, don't escape
        else:
            escaped_parts.append(_escape_html(part))
    text = ''.join(escaped_parts)

    # ── Markdown formatting on the escaped text ───────────────────────────────

    # ### Headers → bold (must come before bold so ## doesn't double-process)
    text = re.sub(r'^#{1,3}\s+(.+)$', lambda m: f'<b>{m.group(1)}</b>', text, flags=re.MULTILINE)

    # **bold**  (must handle escaped & chars inside — already escaped above so fine)
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<b>{m.group(1)}</b>', text)

    # *text* (single, not part of **) → bold (Telegram HTML lacks italic emphasis by default)
    text = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', lambda m: f'<b>{m.group(1)}</b>', text)

    # __bold__
    text = re.sub(r'__(.+?)__', lambda m: f'<b>{m.group(1)}</b>', text)

    # ── Restore protected zones ───────────────────────────────────────────────
    for key, val in protected.items():
        text = text.replace(key, val)

    # ── Final cleanup ─────────────────────────────────────────────────────────
    # Trim trailing spaces on each line
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    # Collapse 3+ blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ── Stage 4: CHUNK ───────────────────────────────────────────────────────────

def _stage4_chunk(text: str, max_size: int = 4000) -> List[str]:
    """
    Split text into chunks of ≤max_size characters.
    Splits at paragraph boundaries (blank lines), then sentence boundaries.
    Never splits inside HTML tags.
    Prepends [1/N] [2/N] labels if multiple chunks.
    """
    if len(text) <= max_size:
        return [text]

    paragraphs = text.split('\n\n')
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush():
        if current_parts:
            chunks.append('\n\n'.join(current_parts))
            current_parts.clear()

    for para in paragraphs:
        para_with_sep = len(para) + 2  # +2 for \n\n separator

        if para_with_sep > max_size:
            # Large paragraph: split at sentence boundaries
            flush()
            sentences = re.split(r'(?<=[.!?])\s+', para)
            seg_parts: list[str] = []
            seg_len = 0
            for sent in sentences:
                sent_len = len(sent) + 1
                if seg_len + sent_len > max_size and seg_parts:
                    chunks.append(' '.join(seg_parts))
                    seg_parts = [sent]
                    seg_len = sent_len
                else:
                    seg_parts.append(sent)
                    seg_len += sent_len
            if seg_parts:
                remaining = ' '.join(seg_parts)
                current_parts.append(remaining)
                current_len = len(remaining) + 2
        elif current_len + para_with_sep > max_size:
            flush()
            current_parts.append(para)
            current_len = para_with_sep
        else:
            current_parts.append(para)
            current_len += para_with_sep

    flush()

    # Label multi-part messages
    if len(chunks) > 1:
        total = len(chunks)
        chunks = [f'<b>[{i + 1}/{total}]</b>\n\n{c}' for i, c in enumerate(chunks)]

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def process(raw_text: str, max_chunk: int = 4000) -> List[str]:
    """
    Run full 5-stage pipeline on raw engine output.

    Returns list of HTML strings, each ≤max_chunk chars,
    ready for Telegram sendMessage with parse_mode='HTML'.

    Stage 5 (SEND) is handled by the caller.
    """
    if not raw_text or not raw_text.strip():
        return ['<i>(no response)</i>']

    text = _stage1_strip(raw_text)
    if not text:
        return ['<i>(empty after strip)</i>']

    text = _stage2_extract(text)
    text = _stage3_format(text)
    chunks = _stage4_chunk(text, max_chunk)

    return [c for c in chunks if c.strip()] or ['<i>(empty)</i>']


# ── CLI test harness ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        TEST_INPUT = """
\x1b[32mINFO: Starting tool call\x1b[0m
[use_mcp_tool]
{"tool": "gmail_search_messages", "args": {"query": "subject:invoice"}}
[/use_mcp_tool]
[result]
{"messages": [{"id": "abc123", "subject": "Invoice #2024-03"}]}
[/result]

---

## Summary

**Furlow booking** is fully paid as of March 25. Final payment of `$15,486` cleared.

Key dates:
| Event | Date |
|-------|------|
| Departure | Aug 29, 2026 |
| Return | Sep 8, 2026 |

Flight PNR: `BB4X94` (Finnair)

Next action: Confirm hotel vouchers for Bergen.
"""
        chunks = process(TEST_INPUT)
        print(f"=== {len(chunks)} chunk(s) ===")
        for i, c in enumerate(chunks):
            print(f"\n--- Chunk {i+1} ({len(c)} chars) ---")
            print(c)
    else:
        # Read from stdin
        raw = sys.stdin.read()
        for chunk in process(raw):
            print(chunk)
            print('---')
