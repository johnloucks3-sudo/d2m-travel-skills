#!/usr/bin/env python3
"""
thunderbird_telegram_gw.py — Thunderbird Telegram Gateway
Dreams2Memories Travel, LLC
Version: 1.0 | 2026-04-04

Three bots. One process. Clean output.

Bot         Token prefix  Engine         Identity     Audience
─────────────────────────────────────────────────────────────
D2MC2C      8754681793    Claude -p      Hale (COS)   Commander only
GooseD2M    8774569956    Goose run      Hale (COS)   Commander only
Dani        8723918695    Claude -p      Dani Moreau  Clients + Commander

Message Flow:
  Commander → Telegram → getUpdates poll (3 tokens, threaded)
      → COMMANDER_ID whitelist check
      → typing... indicator
      → load rolling context (last 10 turns)
      → invoke engine (Claude or Goose headless)
      → Formatter Pipeline (5 stages)
      → send clean chunks (0.5s gap)
      → append exchange to rolling context file

Slash commands (all bots):
    /new     — clear context, fresh session
    /status  — wing health + last activity
    /help    — show available commands
    /brief   — (GooseD2M only) trigger Hale morning brief

Telegram overrides (D2MC2C only):
    OPUS: [task]   → route to claude-opus-4-6
    Sonnet: [task] → route to claude-sonnet-4-6
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

# ── Add Thunderbird root to path ──────────────────────────────────────────────
sys.path.insert(0, '/home/john/Thunderbird')
sys.path.insert(0, '/home/john/Thunderbird/OpsCenter')
sys.path.insert(0, '/home/john/Thunderbird/core/email')

from thunderbird_tg_formatter import process as fmt_process

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger('tg_gw')

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path('/home/john/Thunderbird')
OPS         = THUNDERBIRD / 'OpsCenter'
PERSONAS    = THUNDERBIRD / 'Personas'

HALE_COS    = THUNDERBIRD / 'Personas' / 'hale_cos.md'
HALE_INIT   = THUNDERBIRD / 'hale_init.md'
HALE_MEMORY = THUNDERBIRD / 'hale_memory.md'
HALE_BRIEF  = THUNDERBIRD / 'hale_brief.md'
STAFF_INTRO = PERSONAS / 'D2M_Staff_Introduction.md'

CTX_D2MC2C  = OPS / 'context_d2mc2c.json'
CTX_GOOSE   = OPS / 'context_goose.json'
CTX_DANI    = OPS / 'context_dani.json'

# ── Config from env ───────────────────────────────────────────────────────────
def _load_env_file(path: str) -> None:
    """Load KEY=VALUE pairs from a file into os.environ."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass

_load_env_file('/home/john/Thunderbird/.env')
_load_env_file('/home/john/Thunderbird/config/telegram_gw.env')

TOKEN_D2MC2C  = os.environ.get('TELEGRAM_D2MC2C_TOKEN', '')
TOKEN_GOOSE   = os.environ.get('TELEGRAM_GOOSE_TOKEN', '')
TOKEN_DANI    = os.environ.get('TELEGRAM_DANI_TOKEN', '')
COMMANDER_ID  = int(os.environ.get('TELEGRAM_COMMANDER_ID', '7554895206'))
POLL_INTERVAL = float(os.environ.get('TELEGRAM_GW_POLL_INTERVAL', '2'))
ENGINE_TIMEOUT = int(os.environ.get('TELEGRAM_GW_TIMEOUT', '180'))
CHUNK_SIZE    = int(os.environ.get('TELEGRAM_GW_CHUNK_SIZE', '4000'))
CONTEXT_TURNS = int(os.environ.get('TELEGRAM_GW_CONTEXT_TURNS', '10'))

SONNET_MODEL  = 'claude-sonnet-4-6'
OPUS_MODEL    = 'claude-opus-4-6'
GOOSE_BIN     = Path('/home/john/.local/bin/goose')
MCP_HTTP_URL  = 'http://localhost:8767'

# ── Persona cache (loaded once at startup) ────────────────────────────────────
_PERSONA_CACHE: dict[str, str] = {}
_PERSONA_LOCK = threading.Lock()


def _load_persona_cache() -> None:
    """Pre-load persona files at startup."""
    global _PERSONA_CACHE
    with _PERSONA_LOCK:
        # Hale COS persona (first 5K chars — the authoritative system prompt)
        hale_cos = ''
        if HALE_COS.exists():
            hale_cos = HALE_COS.read_text(encoding='utf-8')[:5000]
        elif HALE_INIT.exists():
            hale_cos = HALE_INIT.read_text(encoding='utf-8')

        # Hale memory (condensed — Commander prefs, standing orders, clients)
        hale_mem = ''
        if HALE_MEMORY.exists():
            hale_mem = HALE_MEMORY.read_text(encoding='utf-8')[:2000]

        _PERSONA_CACHE['hale_system'] = hale_cos
        _PERSONA_CACHE['hale_memory_snippet'] = hale_mem

        # Dani persona — extract her section from Staff Introduction
        dani_text = _extract_dani_persona()
        _PERSONA_CACHE['dani_system'] = dani_text

        log.info('Persona cache loaded: hale=%d chars, dani=%d chars',
                 len(_PERSONA_CACHE['hale_system']),
                 len(_PERSONA_CACHE['dani_system']))


def _extract_dani_persona() -> str:
    """Extract Dani Moreau's section from D2M_Staff_Introduction.md."""
    try:
        text = STAFF_INTRO.read_text(encoding='utf-8')
        # Find Dani section (starts at A3)
        start = text.find('#### A3')
        if start == -1:
            start = text.find('Dani Moreau')
        end = text.find('#### A5', start + 1)
        if start >= 0 and end > start:
            dani_section = text[start:end].strip()
        elif start >= 0:
            dani_section = text[start:start + 2000].strip()
        else:
            dani_section = ''
    except Exception:
        dani_section = ''

    dani_base = """You are Dani Moreau — A3, D2M Luxury Travel Concierge.
Voice: Warm but operationally crisp. You call clients by name, remember details, run the operation with precision.
Role: Aggregator → Artist → Advocate. You gather intel from specialists, craft communications with voice and tone, present as concierge.
Company: Dreams2Memories Travel, LLC (NEVER "Love Group Travel").
Sign-off: "Thanks" or "Thank you" — NEVER "Best."
You do NOT research. You do NOT brief Commander. You do NOT contact suppliers.
Respond warmly, briefly, and with certainty. Mobile-first: ≤4096 chars, scannable.
"""
    return dani_base + ('\n\n' + dani_section[:1500] if dani_section else '')


# ── Rolling Context Management ────────────────────────────────────────────────
_CTX_LOCKS: dict[Path, threading.Lock] = {
    CTX_D2MC2C: threading.Lock(),
    CTX_GOOSE: threading.Lock(),
    CTX_DANI: threading.Lock(),
}


def _load_context(ctx_file: Path) -> list[dict]:
    """Load context exchanges from JSON file. Returns list of {role, text}."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            if ctx_file.exists():
                return json.loads(ctx_file.read_text(encoding='utf-8'))
        except Exception:
            pass
        return []


def _save_context(ctx_file: Path, exchanges: list[dict]) -> None:
    """Save context exchanges to JSON file."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            ctx_file.write_text(
                json.dumps(exchanges, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as e:
            log.error('Context save failed %s: %s', ctx_file.name, e)


def _append_exchange(ctx_file: Path, user_msg: str, assistant_msg: str,
                     user_label: str = 'Commander', assistant_label: str = 'Hale') -> None:
    """Append a turn to the rolling context, pruning to CONTEXT_TURNS."""
    exchanges = _load_context(ctx_file)
    exchanges.append({'role': user_label, 'text': user_msg})
    exchanges.append({'role': assistant_label, 'text': assistant_msg})
    # Keep last (CONTEXT_TURNS * 2) entries = last N turns
    max_entries = CONTEXT_TURNS * 2
    if len(exchanges) > max_entries:
        exchanges = exchanges[-max_entries:]
    _save_context(ctx_file, exchanges)


def _format_context(ctx_file: Path) -> str:
    """Format context for injection into prompt."""
    exchanges = _load_context(ctx_file)
    if not exchanges:
        return ''
    lines = ['[RECENT CONVERSATION — last turns]']
    for ex in exchanges:
        role = ex.get('role', 'Unknown')
        text = ex.get('text', '').strip()
        if text:
            # Truncate very long entries
            if len(text) > 500:
                text = text[:500] + '...'
            lines.append(f'{role}: {text}')
    lines.append('[END CONTEXT]')
    return '\n'.join(lines)


def _clear_context(ctx_file: Path) -> None:
    """Wipe context file."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            ctx_file.write_text('[]', encoding='utf-8')
        except Exception:
            pass


# ── Telegram API helpers ──────────────────────────────────────────────────────
TG_BASE = 'https://api.telegram.org/bot{token}/{method}'


def tg(token: str, method: str, **kwargs) -> dict:
    """Make a Telegram Bot API call. Returns parsed JSON."""
    url = TG_BASE.format(token=token, method=method)
    try:
        r = requests.post(url, json=kwargs, timeout=35)
        data = r.json()
        if not data.get('ok'):
            log.warning('TG API %s error: %s', method, data.get('description', '?'))
        return data
    except Exception as e:
        log.error('TG API %s exception: %s', method, e)
        return {'ok': False, 'description': str(e)}


def tg_get_updates(token: str, offset: int) -> list[dict]:
    """Short-poll getUpdates (timeout=0). Returns list of update objects immediately."""
    data = tg(token, 'getUpdates', offset=offset, timeout=0, limit=20)
    if data.get('ok'):
        return data.get('result', [])
    return []


def tg_typing(token: str, chat_id: int) -> None:
    """Send typing indicator."""
    tg(token, 'sendChatAction', chat_id=chat_id, action='typing')


def tg_send(token: str, chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
    """Send a single message. Returns True on success."""
    # Telegram hard limit
    if len(text) > 4096:
        text = text[:4090] + '\n…'
    data = tg(token, 'sendMessage', chat_id=chat_id, text=text, parse_mode=parse_mode)
    return bool(data.get('ok'))


def tg_send_chunks(token: str, chat_id: int, chunks: list[str]) -> None:
    """Send multiple chunks with 0.5s delay, plain-text fallback on error."""
    for chunk in chunks:
        success = tg_send(token, chat_id, chunk, parse_mode='HTML')
        if not success:
            # Fallback: strip HTML tags and send plain
            plain = re.sub(r'<[^>]+>', '', chunk)
            tg_send(token, chat_id, plain, parse_mode=None)
        if len(chunks) > 1:
            time.sleep(0.5)


import re  # noqa: E402 — needed for tg_send_chunks fallback above


# ── Engine: Claude headless ───────────────────────────────────────────────────

def _build_hale_claude_prompt(context_text: str, message: str) -> str:
    """Build the full prompt for Claude/Hale engine."""
    persona = _PERSONA_CACHE.get('hale_system', '')
    memory_snip = _PERSONA_CACHE.get('hale_memory_snippet', '')

    parts = []
    if persona:
        parts.append(persona)
    if memory_snip:
        parts.append(f'\n\n---\n## CURRENT MEMORY SNAPSHOT\n{memory_snip}')
    if context_text:
        parts.append(f'\n\n---\n{context_text}')
    parts.append(f'\n\nCommander: {message}\nHale:')

    return ''.join(parts)


def _build_dani_claude_prompt(context_text: str, message: str) -> str:
    """Build the full prompt for Claude/Dani engine."""
    persona = _PERSONA_CACHE.get('dani_system', '')
    parts = []
    if persona:
        parts.append(persona)
    if context_text:
        parts.append(f'\n\n---\n{context_text}')
    parts.append(f'\n\nCommander/Client: {message}\nDani:')
    return ''.join(parts)


def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
    """
    Invoke Claude headless via `claude -p`.
    Uses Max OAuth (no API key needed when ANTHROPIC_API_KEY is empty).
    """
    env = dict(os.environ)
    # Claude CLI uses Max OAuth when no API key is set
    env.pop('ANTHROPIC_API_KEY', None)

    try:
        result = subprocess.run(
            ['claude', '--model', model, '-p', prompt, '--dangerously-skip-permissions'],
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT,
            env=env,
            cwd=str(THUNDERBIRD),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        err = result.stderr.strip()
        log.error('Claude headless rc=%d: %s', result.returncode, err[:300])
        return f'[Engine error — Claude rc={result.returncode}]'
    except subprocess.TimeoutExpired:
        return '[Engine timeout — Claude exceeded limit]'
    except FileNotFoundError:
        return '[Engine error — claude binary not found]'
    except Exception as e:
        return f'[Engine error — {e}]'


# ── Engine: Goose headless ────────────────────────────────────────────────────

def call_goose_engine(system_prompt: str, text_prompt: str, use_mcp: bool = True) -> str:
    """
    Invoke Goose headless via `goose run`.
    system_prompt: persona/identity instructions
    text_prompt:   context + user message
    use_mcp:       if True, connect to Thunderbird MCP via HTTP (port 8767)
    """
    # Write text_prompt to temp file to avoid command-line length limits
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.md', delete=False, encoding='utf-8'
    ) as f:
        f.write(text_prompt)
        instructions_file = f.name

    try:
        cmd = [
            str(GOOSE_BIN), 'run',
            '--instructions', instructions_file,
            '--no-session',
            '--quiet',
            '--max-turns', '15',
        ]

        # Inject persona as system instructions
        if system_prompt:
            # Truncate to avoid arg length issues
            cmd += ['--system', system_prompt[:2000]]

        # MCP access for GooseD2M
        if use_mcp:
            cmd += ['--with-streamable-http-extension', MCP_HTTP_URL]

        env = dict(os.environ)
        env['GOOSE_WORKING_DIR'] = str(THUNDERBIRD)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT,
            cwd=str(THUNDERBIRD),
            env=env,
        )

        output = result.stdout.strip()
        if not output and result.returncode != 0:
            log.error('Goose headless rc=%d: %s', result.returncode, result.stderr[:300])
            return f'[Engine error — Goose rc={result.returncode}]'
        return output or '[Engine returned empty response]'

    except subprocess.TimeoutExpired:
        return '[Engine timeout — Goose exceeded limit]'
    except FileNotFoundError:
        return '[Engine error — goose binary not found]'
    except Exception as e:
        return f'[Engine error — {e}]'
    finally:
        try:
            os.unlink(instructions_file)
        except Exception:
            pass


# ── Slash Command Handlers ────────────────────────────────────────────────────

def handle_new(token: str, chat_id: int, ctx_file: Path) -> None:
    _clear_context(ctx_file)
    tg_send(token, chat_id, '🔄 <b>Context cleared.</b> Fresh session started.')
    log.info('/new — context cleared for %s', ctx_file.name)


def handle_status(token: str, chat_id: int) -> None:
    """Check wing health and report."""
    import socket

    lines = ['<b>⚡ Thunderbird Wing Status</b>', '']

    # MCP HTTP server check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('localhost', 8767))
        s.close()
        lines.append('🟢 MCP Server — ONLINE (port 8767)')
    except Exception:
        lines.append('🔴 MCP Server — OFFLINE (port 8767)')

    # Context activity
    for label, ctx_file in [('D2MC2C', CTX_D2MC2C), ('GooseD2M', CTX_GOOSE), ('Dani', CTX_DANI)]:
        if ctx_file.exists():
            mtime = datetime.fromtimestamp(ctx_file.stat().st_mtime).strftime('%m/%d %H:%M')
            exchanges = _load_context(ctx_file)
            turns = len(exchanges) // 2
            lines.append(f'📋 {label} context — {turns} turns, last: {mtime}')
        else:
            lines.append(f'📋 {label} context — empty')

    # System time
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines.append(f'\n🕐 {now}')

    tg_send(token, chat_id, '\n'.join(lines))


def handle_help(token: str, chat_id: int, bot_name: str) -> None:
    msg = f"""<b>⚡ {bot_name} — Commands</b>

/new — Clear context, fresh session
/status — Wing health + last activity
/help — This menu
/drafts — List pending drafts in d2mconcierge
/approve [id] — Send a draft (first 20 chars of ID)
/reject [id] — Delete a draft
"""
    if bot_name == 'GooseD2M':
        msg += '/brief — Trigger Hale morning brief\n'
    msg += '\n<b>🔄 Both Ways Cross-Bot:</b>\n'
    if bot_name == 'D2MC2C':
        msg += '<code>@goose [msg]</code> — Task Goose\n<code>@dani [msg]</code> — Task Dani\n'
    elif bot_name == 'GooseD2M':
        msg += '<code>@claude [msg]</code> — Task Claude\n<code>@dani [msg]</code> — Task Dani\n'
    elif bot_name == 'Dani':
        msg += '<code>@goose [msg]</code> — Task Goose\n<code>@claude [msg]</code> — Task Claude\n'
    msg += '\n<b>Overrides (D2MC2C only):</b>\n<code>OPUS: [task]</code> — Route to Claude Opus\n<code>Sonnet: [task]</code> — Route to Claude Sonnet'
    tg_send(token, chat_id, msg)


def handle_brief(token: str, chat_id: int) -> None:
    """GooseD2M /brief — trigger morning brief via Goose."""
    tg_typing(token, chat_id)
    tg_send(token, chat_id, '⌛ Pulling brief from Goose/Hale...')

    system = _PERSONA_CACHE.get('hale_system', '')
    brief_path = str(HALE_BRIEF)
    text = f"""Read {brief_path} and give me the current morning brief.
Format: structured, scannable. Highlight CRITICAL items first.
If the brief is stale or missing, summarize what you know about current wing status."""

    raw = call_goose_engine(system, text, use_mcp=True)
    chunks = fmt_process(raw, CHUNK_SIZE)
    tg_send_chunks(token, chat_id, chunks)


# ── Draft Approval Commands ───────────────────────────────────────────────────

def _get_d2m_gmail():
    """Get Gmail service for d2mconcierge (gmail_token.json)."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        token_file = THUNDERBIRD / 'gmail_token.json'
        creds_file = THUNDERBIRD / 'credentials.json'
        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if not creds or not creds.valid:
            return None
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        log.error('Gmail service error: %s', e)
        return None


def handle_drafts(token: str, chat_id: int) -> None:
    """List pending drafts in d2mconcierge — /drafts"""
    tg_typing(token, chat_id)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, '❌ Gmail unavailable — check credentials.')
        return
    try:
        result = svc.users().drafts().list(userId='me', maxResults=8).execute()
        drafts = result.get('drafts', [])
        if not drafts:
            tg_send(token, chat_id, '📭 No pending drafts in d2mconcierge.')
            return
        lines = ['<b>📋 Pending drafts in d2mconcierge:</b>\n']
        for d in drafts:
            try:
                detail = svc.users().drafts().get(userId='me', id=d['id'], format='metadata').execute()
                headers = {h['name'].lower(): h['value']
                           for h in detail.get('message', {}).get('payload', {}).get('headers', [])}
                subject = headers.get('subject', '(no subject)')[:60]
                to = headers.get('to', '?')[:40]
                lines.append(f'<code>{d["id"][:20]}</code>\n  To: {to}\n  Re: {subject}\n')
            except Exception:
                lines.append(f'<code>{d["id"][:20]}</code> (error fetching detail)\n')
        lines.append('\nUse <code>/approve [id]</code> or <code>/reject [id]</code>')
        tg_send(token, chat_id, '\n'.join(lines))
    except Exception as e:
        tg_send(token, chat_id, f'❌ Error listing drafts: {e}')


def handle_approve(token: str, chat_id: int, args: list) -> None:
    """Send a draft by ID — /approve [draft_id]"""
    if not args:
        tg_send(token, chat_id, 'Usage: <code>/approve [draft_id]</code>\nGet IDs with /drafts')
        return
    draft_id = args[0]
    tg_typing(token, chat_id)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, '❌ Gmail unavailable.')
        return
    try:
        # Preview before sending
        detail = svc.users().drafts().get(userId='me', id=draft_id, format='metadata').execute()
        headers = {h['name'].lower(): h['value']
                   for h in detail.get('message', {}).get('payload', {}).get('headers', [])}
        subject = headers.get('subject', '?')
        to = headers.get('to', '?')
        # Send it
        svc.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        tg_send(token, chat_id,
                f'✅ <b>SENT</b>\nTo: {to}\nSubject: {subject}\n\n<i>Draft {draft_id[:16]}… delivered.</i>')
        log.info('[APPROVE] Sent draft %s to %s — %s', draft_id[:16], to, subject)
    except Exception as e:
        tg_send(token, chat_id, f'❌ Send failed: {e}')


def handle_reject(token: str, chat_id: int, args: list) -> None:
    """Delete a draft by ID — /reject [draft_id]"""
    if not args:
        tg_send(token, chat_id, 'Usage: <code>/reject [draft_id]</code>\nGet IDs with /drafts')
        return
    draft_id = args[0]
    tg_typing(token, chat_id)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, '❌ Gmail unavailable.')
        return
    try:
        detail = svc.users().drafts().get(userId='me', id=draft_id, format='metadata').execute()
        headers = {h['name'].lower(): h['value']
                   for h in detail.get('message', {}).get('payload', {}).get('headers', [])}
        subject = headers.get('subject', '?')
        svc.users().drafts().delete(userId='me', id=draft_id).execute()
        tg_send(token, chat_id, f'🗑️ <b>REJECTED</b>: {subject[:60]}')
        log.info('[REJECT] Deleted draft %s — %s', draft_id[:16], subject)
    except Exception as e:
        tg_send(token, chat_id, f'❌ Reject failed: {e}')


# ── Both Ways Router ──────────────────────────────────────────────────────────

def _detect_forward(msg: str, bot_name: str) -> str | None:
    """Return 'goose', 'claude', or 'dani' if msg targets them. Works with typed @ or voice 'at'."""
    lower = msg.lower().strip()
    
    # Regex catches:
    # 1. Typed: "@goose do this" 
    # 2. Voice: "at goose do this" 
    # 3. Short: "goose, do this" (Name as imperative)
    
    p_goose = re.compile(r'^(@|at\s+)?goose[,\s:].*')
    p_claude = re.compile(r'^(@|at\s+)?(claude|hale)[,\s:].*')
    p_dani = re.compile(r'^(@|at\s+)?dani[,\s:].*')

    if bot_name == 'D2MC2C':
        # Currently talking to Claude. Forward others.
        if p_goose.match(lower): return 'goose'
        if p_dani.match(lower): return 'dani'
    elif bot_name == 'GooseD2M':
        # Currently talking to Goose. Forward others.
        if p_claude.match(lower): return 'claude'
        if p_dani.match(lower): return 'dani'
    elif bot_name == 'Dani':
        # Currently talking to Dani. Forward others.
        if p_goose.match(lower): return 'goose'
        if p_claude.match(lower): return 'claude'
        
    return None


def _handle_forward(
    token: str, chat_id: int, msg: str,
    bot_name: str, ctx_file: Path, target: str,
) -> None:
    """Strip @prefix, call the other engine, return response to source chat."""
    parts = msg.split(None, 1)
    stripped = parts[1].strip() if len(parts) > 1 else ''
    if not stripped:
        tg_send(token, chat_id, 'Both Ways: no message after @prefix.')
        return

    tg_typing(token, chat_id)
    if target == 'goose':
        engine_fn = hale_goose_engine
        engine_label = 'GooseD2M'
    elif target == 'dani':
        engine_fn = dani_claude_engine
        engine_label = 'Dani'
    else:
        engine_fn = hale_claude_engine
        engine_label = 'Sonnet'

    log.info('[%s] Both Ways → %s: %s...', bot_name, engine_label, stripped[:80])
    try:
        raw_response = engine_fn('', stripped, None)
    except Exception as e:
        log.error('[%s] Both Ways engine error: %s', bot_name, e)
        raw_response = f'[Both Ways error: {e}]'

    chunks = fmt_process(f'🔄 <b>Both Ways via {engine_label}</b>\n\n{raw_response}', CHUNK_SIZE)
    tg_send_chunks(token, chat_id, chunks)

    _append_exchange(
        ctx_file,
        user_msg=stripped,
        assistant_msg=raw_response[:800],
        user_label='Commander',
        assistant_label=f'{engine_label} (via Both Ways)',
    )


# ── Message Handler ───────────────────────────────────────────────────────────

def handle_message(
    token: str,
    chat_id: int,
    user_id: int,
    text: str,
    bot_name: str,
    ctx_file: Path,
    engine_fn: Callable,
    assistant_label: str,
) -> None:
    """Process one incoming message and send formatted response."""

    # Security: Commander-only for D2MC2C and GooseD2M
    # For Dani, still only accept Commander ID (clients use a separate flow later)
    if user_id != COMMANDER_ID:
        log.warning('Rejected message from non-Commander user_id=%d', user_id)
        return

    msg = text.strip()

    # ── Slash commands ────────────────────────────────────────────────────────
    if msg.startswith('/'):
        cmd = msg.split()[0].lower()
        if cmd == '/new':
            handle_new(token, chat_id, ctx_file)
            return
        elif cmd == '/status':
            handle_status(token, chat_id)
            return
        elif cmd == '/help':
            handle_help(token, chat_id, bot_name)
            return
        elif cmd == '/brief' and bot_name == 'GooseD2M':
            handle_brief(token, chat_id)
            return
        elif cmd == '/drafts':
            handle_drafts(token, chat_id)
            return
        elif cmd == '/approve':
            args = msg.split()[1:]
            handle_approve(token, chat_id, args)
            return
        elif cmd == '/reject':
            args = msg.split()[1:]
            handle_reject(token, chat_id, args)
            return
        elif cmd == '/start':
            tg_send(token, chat_id, f'<b>{bot_name} online.</b> Type /help for commands.')
            return
        else:
            tg_send(token, chat_id, f'Unknown command. Type /help.')
            return

    # ── Model override detection (D2MC2C / Claude only) ──────────────────────
    model_override = None
    msg_upper = msg.upper()
    if msg_upper.startswith('OPUS:'):
        model_override = OPUS_MODEL
        msg = msg[5:].strip()
        log.info('OPUS override activated')
    elif msg_upper.startswith('SONNET:'):
        model_override = SONNET_MODEL
        msg = msg[7:].strip()
        log.info('Sonnet override activated')

    if not msg:
        return

    # ── Both Ways forward check ────────────────────────────────────────────────
    forward_target = _detect_forward(msg, bot_name)
    if forward_target:
        _handle_forward(token, chat_id, msg, bot_name, ctx_file, forward_target)
        return

    # ── Typing indicator ──────────────────────────────────────────────────────
    tg_typing(token, chat_id)

    # ── Load context ──────────────────────────────────────────────────────────
    context_text = _format_context(ctx_file)

    # ── Invoke engine ─────────────────────────────────────────────────────────
    log.info('[%s] Invoking engine for: %s...', bot_name, msg[:80])
    start_t = time.time()

    try:
        raw_response = engine_fn(context_text, msg, model_override)
    except Exception as e:
        log.error('[%s] Engine exception: %s', bot_name, e)
        raw_response = f'[Internal error: {e}]'

    elapsed = time.time() - start_t
    log.info('[%s] Engine returned %d chars in %.1fs', bot_name, len(raw_response), elapsed)

    # ── Format and send ───────────────────────────────────────────────────────
    chunks = fmt_process(raw_response, CHUNK_SIZE)
    tg_send_chunks(token, chat_id, chunks)

    # ── Save to rolling context ───────────────────────────────────────────────
    # Use first 800 chars of response to keep context compact
    response_snippet = raw_response[:800].strip()
    _append_exchange(
        ctx_file,
        user_msg=msg,
        assistant_msg=response_snippet,
        user_label='Commander',
        assistant_label=assistant_label,
    )


# ── Engine function wrappers (match handle_message signature) ─────────────────

def hale_claude_engine(context_text: str, message: str, model_override: str | None) -> str:
    prompt = _build_hale_claude_prompt(context_text, message)
    model = model_override or SONNET_MODEL
    return call_claude_engine(prompt, model=model)


def hale_goose_engine(context_text: str, message: str, model_override: str | None) -> str:
    system = _PERSONA_CACHE.get('hale_system', '')
    text = (
        (f'{context_text}\n\n' if context_text else '')
        + f'Commander: {message}\n\n'
        + 'Respond as Hale. Brief-first. No preamble. No trailing summary.'
    )
    return call_goose_engine(system, text, use_mcp=True)


def dani_claude_engine(context_text: str, message: str, model_override: str | None) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    # Dani always uses Sonnet (warm copy, client-facing)
    return call_claude_engine(prompt, model=SONNET_MODEL)


# ── Bot Poll Loop ─────────────────────────────────────────────────────────────

def bot_poll_loop(
    token: str,
    bot_name: str,
    ctx_file: Path,
    engine_fn: Callable,
    assistant_label: str,
) -> None:
    """
    Long-poll loop for one bot. Runs in its own thread.
    Processes messages only from COMMANDER_ID.
    """
    log.info('[%s] Poll loop starting', bot_name)
    offset = 0

    # Initialize context file if missing
    if not ctx_file.exists():
        _save_context(ctx_file, [])

    while True:
        try:
            updates = tg_get_updates(token, offset=offset)
        except Exception as e:
            log.error('[%s] getUpdates exception: %s', bot_name, e)
            time.sleep(5)
            continue

        for update in updates:
            offset = update['update_id'] + 1

            msg_obj = update.get('message')
            if not msg_obj:
                continue  # Skip non-message updates (callbacks, etc.)

            chat_id = msg_obj.get('chat', {}).get('id')
            user_id = msg_obj.get('from', {}).get('id')
            text    = msg_obj.get('text', '')

            if not chat_id or not text:
                continue

            # Dispatch in a thread so we don't block the poll loop
            t = threading.Thread(
                target=handle_message,
                args=(token, chat_id, user_id, text, bot_name, ctx_file,
                      engine_fn, assistant_label),
                daemon=True,
            )
            t.start()

        # Brief sleep between polls to avoid hammering Telegram
        time.sleep(POLL_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info('═══════════════════════════════════════')
    log.info('Thunderbird Telegram Gateway v1.5 — Both Ways Enabled')
    log.info('Three bots. One process. Clean output.')
    log.info('═══════════════════════════════════════')

    # Validate tokens
    missing = []
    if not TOKEN_D2MC2C:
        missing.append('TELEGRAM_D2MC2C_TOKEN')
    if not TOKEN_GOOSE:
        missing.append('TELEGRAM_GOOSE_TOKEN')
    if not TOKEN_DANI:
        missing.append('TELEGRAM_DANI_TOKEN')
    if missing:
        log.error('Missing required tokens: %s', ', '.join(missing))
        sys.exit(1)

    # Load persona cache
    _load_persona_cache()

    # Verify commander ID is set
    log.info('Commander ID: %d', COMMANDER_ID)
    log.info('Engine timeout: %ds | Chunk size: %d | Context turns: %d',
             ENGINE_TIMEOUT, CHUNK_SIZE, CONTEXT_TURNS)

    # Define bots
    bot_configs = [
        {
            'token':           TOKEN_D2MC2C,
            'bot_name':        'D2MC2C',
            'ctx_file':        CTX_D2MC2C,
            'engine_fn':       hale_claude_engine,
            'assistant_label': 'Hale',
        },
        {
            'token':           TOKEN_GOOSE,
            'bot_name':        'GooseD2M',
            'ctx_file':        CTX_GOOSE,
            'engine_fn':       hale_goose_engine,
            'assistant_label': 'Hale',
        },
        {
            'token':           TOKEN_DANI,
            'bot_name':        'Dani',
            'ctx_file':        CTX_DANI,
            'engine_fn':       dani_claude_engine,
            'assistant_label': 'Dani',
        },
    ]

    # Start a poll thread per bot
    threads = []
    for cfg in bot_configs:
        t = threading.Thread(
            target=bot_poll_loop,
            kwargs=cfg,
            name=f"poll_{cfg['bot_name']}",
            daemon=True,
        )
        t.start()
        threads.append(t)
        log.info('[%s] Poll thread started', cfg['bot_name'])

    log.info('All 3 bot threads running. Gateway is LIVE.')

    # Keep main thread alive — monitor worker threads
    try:
        while True:
            dead = [t for t in threads if not t.is_alive()]
            if dead:
                for d in dead:
                    log.error('Thread %s died — gateway may be degraded', d.name)
            time.sleep(30)
    except KeyboardInterrupt:
        log.info('Gateway shutting down (KeyboardInterrupt)')


if __name__ == '__main__':
    main()
