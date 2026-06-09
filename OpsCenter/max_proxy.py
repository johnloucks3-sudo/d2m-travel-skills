#!/usr/bin/env python3
"""
max_proxy.py — Claude MAX OAuth proxy for OpenCode  v2.0
Sits on localhost:5099, speaks Anthropic API format.
Routes via 'claude -p' (Max OAuth — $0).

v2: True streaming via Popen + --output-format stream-json.
Tokens forward to the client as the subprocess emits them.
Handles both per-token content_block_delta events AND complete
assistant message events (fallback for older CLI versions).
"""
import json, os, subprocess, uuid, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT      = 5099
TIMEOUT   = 600
PROXY_LOG = Path("/home/john/Thunderbird/logs/max_proxy_requests.jsonl")
CWD       = '/tmp'
CLAUDE_MODEL = 'claude-sonnet-4-6'

MODEL_MAP = {
    'claude-sonnet-4-5':  'claude-sonnet-4-6',
    'claude-sonnet-4-6':  'claude-sonnet-4-6',
    # Opus: generic + all older aliases resolve to the current latest (4-8).
    # Previously these pinned to 4-7 — stale; opus work never reached 4-8.
    'claude-opus-4':      'claude-opus-4-8',
    'claude-opus-4-5':    'claude-opus-4-8',
    'claude-opus-4-6':    'claude-opus-4-8',
    'claude-opus-4-7':    'claude-opus-4-7',   # explicit 4-7 request honored
    'claude-opus-4-8':    'claude-opus-4-8',
    # Haiku targets use the dated canonical ID (matches HAIKU_FALLBACK).
    'claude-haiku-3-5':   'claude-haiku-4-5-20251001',
    'claude-haiku-3':     'claude-haiku-4-5-20251001',
    'claude-haiku-4-5':   'claude-haiku-4-5-20251001',
}


def _clean_env():
    """Strip Anthropic proxy vars so Max OAuth is used."""
    env = dict(os.environ)
    env.pop('ANTHROPIC_API_KEY', None)
    env.pop('ANTHROPIC_BASE_URL', None)
    return env


THINKING_INSTRUCTION = (
    "Before answering, think through this carefully. "
    "Show your reasoning explicitly — walk through your logic step by step, "
    "consider alternatives, and explain your conclusions. "
    "Open with a **Thinking:** section, then give your answer."
)


def _inject_thinking(system, thinking_cfg: dict) -> str:
    """Prepend visible-reasoning instruction when extended thinking is requested."""
    if not thinking_cfg or thinking_cfg.get('type') != 'enabled':
        return system
    if isinstance(system, list):
        # Already a content list — prepend as a text block
        return [{'type': 'text', 'text': THINKING_INSTRUCTION}] + system
    return (THINKING_INSTRUCTION + "\n\n" + system).strip() if system else THINKING_INSTRUCTION


def _build_prompt(messages: list, system) -> str:
    parts = []
    if system:
        if isinstance(system, list):
            system = ' '.join(s.get('text', '') for s in system if s.get('type') == 'text')
        parts.append(f"System: {system}")
    for msg in messages:
        role    = msg.get('role', 'user').capitalize()
        content = msg.get('content', '')
        if isinstance(content, list):
            content = ' '.join(c.get('text', '') for c in content if c.get('type') == 'text')
        parts.append(f"{role}: {content}")
    return '\n\n'.join(parts)


def _log(model, cli_model, prompt, response):
    try:
        PROXY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PROXY_LOG, 'a') as f:
            f.write(json.dumps({
                'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'model': model, 'cli_model': cli_model,
                'prompt_chars': len(prompt), 'resp_chars': len(response),
            }) + '\n')
    except Exception:
        pass


# ── blocking call (non-streaming requests) ───────────────────────────────────

RATE_LIMIT_SIGNALS = (
    "There's an issue with the selected model",
    "rate_limit", "rate limit", "overloaded",
    "API Error 429", "429 Too Many Requests",
    "Request rate limit reached",
)
HAIKU_FALLBACK = 'claude-haiku-4-5-20251001'


def _is_rate_limited(text: str) -> bool:
    tl = text.lower()
    return any(s.lower() in tl for s in RATE_LIMIT_SIGNALS)


def _call_max(prompt: str, model: str) -> str:
    cli_model = MODEL_MAP.get(model, CLAUDE_MODEL)
    # Use -p - (stdin) to avoid OSError: Argument list too long on large prompts
    r = subprocess.run(
        ['claude', '--model', cli_model, '-p', '-',
         '--output-format', 'text', '--dangerously-skip-permissions'],
        input=prompt, capture_output=True, text=True, timeout=TIMEOUT,
        env=_clean_env(), cwd=CWD,
    )
    text = r.stdout.strip() or r.stderr.strip() or ''
    if not text:
        text = f'[max_proxy FALLBACK — claude -p rc={r.returncode}; no output]'

    # ── Rate-limit / wrong-model fallback to Haiku ──
    # The claude CLI surfaces 429 rate-limits as "There's an issue with the
    # selected model" — misleading. Detect and retry on Haiku automatically.
    if _is_rate_limited(text) and cli_model != HAIKU_FALLBACK:
        r2 = subprocess.run(
            ['claude', '--model', HAIKU_FALLBACK, '-p', '-',
             '--output-format', 'text', '--dangerously-skip-permissions'],
            input=prompt, capture_output=True, text=True, timeout=TIMEOUT,
            env=_clean_env(), cwd=CWD,
        )
        fallback_text = r2.stdout.strip() or r2.stderr.strip() or ''
        if fallback_text and not _is_rate_limited(fallback_text):
            text = f'[⚡ Haiku fallback — {cli_model} rate-limited]\n\n{fallback_text}'
        # else return original error so caller knows both failed

    _log(model, cli_model, prompt, text)
    return text


# ── streaming call ────────────────────────────────────────────────────────────

def _stream_max(prompt: str, model: str, on_chunk, on_flush) -> str:
    """
    Spawn claude with --output-format stream-json and stream tokens live.

    Handles two event shapes:
      1. content_block_delta  — per-token (stream-json mirrors Anthropic SSE)
      2. assistant            — complete message (fallback for older CLI builds)

    Calls on_chunk(str) for each text delta; on_flush() to push bytes to client.
    Returns full accumulated response text.
    """
    cli_model = MODEL_MAP.get(model, CLAUDE_MODEL)
    # Use -p - (stdin) to avoid OSError: Argument list too long on large prompts
    proc = subprocess.Popen(
        ['claude', '--model', cli_model, '-p', '-',
         '--output-format', 'stream-json', '--dangerously-skip-permissions'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
        env=_clean_env(), cwd=CWD,
    )
    # Write prompt via stdin then close to signal EOF
    proc.stdin.write(prompt)
    proc.stdin.close()

    parts = []
    try:
        for raw in iter(proc.stdout.readline, ''):
            line = raw.strip()
            if not line:
                continue
            try:
                evt   = json.loads(line)
                etype = evt.get('type', '')

                # Per-token streaming (stream-json mirrors Anthropic SSE format)
                if etype == 'content_block_delta':
                    delta = evt.get('delta', {})
                    if delta.get('type') == 'text_delta':
                        chunk = delta.get('text', '')
                        if chunk:
                            parts.append(chunk)
                            on_chunk(chunk)
                            on_flush()

                # Complete assistant turn (fallback if CLI doesn't emit per-token deltas)
                elif etype == 'assistant':
                    for block in evt.get('message', {}).get('content', []):
                        if block.get('type') == 'text':
                            chunk = block['text']
                            if chunk:
                                parts.append(chunk)
                                on_chunk(chunk)
                                on_flush()

                # system / result / tool_use / thinking — skip silently

            except json.JSONDecodeError:
                # Plain text fallback (shouldn't happen with stream-json)
                if raw.strip():
                    parts.append(raw)
                    on_chunk(raw)
                    on_flush()
    finally:
        proc.stdout.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    full_text = ''.join(parts).strip() or '[max_proxy: no response]'

    # ── Rate-limit fallback (streaming path) ──
    if _is_rate_limited(full_text) and cli_model != HAIKU_FALLBACK:
        fallback_text = _call_max(prompt, HAIKU_FALLBACK)
        if fallback_text and not _is_rate_limited(fallback_text):
            full_text = f'[⚡ Haiku fallback — {cli_model} rate-limited]\n\n{fallback_text}'
            on_chunk(full_text)
            on_flush()

    _log(model, cli_model, prompt, full_text)
    return full_text


# ── HTTP handler ──────────────────────────────────────────────────────────────

class MaxProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Only log errors — keep stdout clean
        if args and isinstance(args[0], int) and int(str(args[0])) >= 400:
            super().log_message(fmt, *args)

    def do_GET(self):
        if self.path == '/health':
            body = b'{"status":"ok","proxy":"claude-max","version":"2.0","streaming":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path not in ('/v1/messages', '/messages'):
            self.send_error(404)
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, 'Bad JSON')
            return

        model   = data.get('model', CLAUDE_MODEL)
        stream  = data.get('stream', False)
        system  = _inject_thinking(data.get('system', ''), data.get('thinking', {}))
        prompt  = _build_prompt(data.get('messages', []), system)
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"

        if stream:
            self._handle_stream(prompt, model, msg_id)
        else:
            self._send_json(_call_max(prompt, model), msg_id, model)

    # ── response helpers ──────────────────────────────────────────────────────

    def _sse(self, event: dict):
        try:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
        except BrokenPipeError:
            pass

    def _sse_text(self, text: str):
        self._sse({
            'type': 'content_block_delta', 'index': 0,
            'delta': {'type': 'text_delta', 'text': text},
        })

    def _safe_flush(self):
        try:
            self.wfile.flush()
        except BrokenPipeError:
            pass

    def _send_json(self, text: str, msg_id: str, model: str):
        body = json.dumps({
            'id': msg_id, 'type': 'message', 'role': 'assistant',
            'content': [{'type': 'text', 'text': text}],
            'model': model, 'stop_reason': 'end_turn', 'stop_sequence': None,
            'usage': {'input_tokens': 0, 'output_tokens': len(text) // 4},
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _handle_stream(self, prompt: str, model: str, msg_id: str):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        # Preamble — sent immediately so the client sees activity right away
        self._sse({'type': 'message_start', 'message': {
            'id': msg_id, 'type': 'message', 'role': 'assistant',
            'content': [], 'model': model, 'stop_reason': None,
            'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0},
        }})
        self._sse({'type': 'content_block_start', 'index': 0,
                   'content_block': {'type': 'text', 'text': ''}})
        self._safe_flush()

        # Stream tokens as they arrive from the subprocess
        full_text = _stream_max(
            prompt, model,
            on_chunk=self._sse_text,
            on_flush=self._safe_flush,
        )

        # Closing events
        self._sse({'type': 'content_block_stop', 'index': 0})
        self._sse({'type': 'message_delta',
                   'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
                   'usage': {'output_tokens': len(full_text) // 4}})
        self._sse({'type': 'message_stop'})
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except BrokenPipeError:
            pass


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), MaxProxyHandler)
    print(
        f'[max_proxy v2.0] Claude MAX proxy — http://127.0.0.1:{PORT}\n'
        f'  streaming : Popen + stream-json (per-token deltas)\n'
        f'  auth      : Max OAuth (no API key needed)\n'
        f'  model     : {CLAUDE_MODEL} (default)',
        flush=True,
    )
    server.serve_forever()
