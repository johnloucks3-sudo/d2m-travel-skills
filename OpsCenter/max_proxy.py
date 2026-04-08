#!/usr/bin/env python3
"""
max_proxy.py — Claude MAX OAuth proxy for OpenCode
Sits on localhost:5099, speaks Anthropic API format.
Every request is routed through 'claude -p' (Max OAuth — free).
OpenCode talks to this instead of api.anthropic.com.
"""
import json
import os
import subprocess
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT     = 5099
TIMEOUT  = 180
CWD      = '/home/john/Thunderbird'
# Fallback model name for the claude CLI
# Default when OpenCode sends an unrecognized model ID
CLAUDE_MODEL = 'claude-sonnet-4-6'

# Maps OpenCode model IDs → claude CLI names (add new ones here as they release)
MODEL_MAP = {
    'claude-sonnet-4-5':  'claude-sonnet-4-6',
    'claude-sonnet-4-6':  'claude-sonnet-4-6',
    'claude-opus-4':      'claude-opus-4',
    'claude-opus-4-5':    'claude-opus-4-5',
    'claude-haiku-3-5':   'claude-haiku-3-5',
    'claude-haiku-3':     'claude-haiku-3-5',
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _clean_env():
    """Return env with Anthropic proxy vars stripped so Max OAuth kicks in."""
    env = dict(os.environ)
    env.pop('ANTHROPIC_API_KEY', None)
    env.pop('ANTHROPIC_BASE_URL', None)
    return env


def _build_prompt(messages: list, system) -> str:
    parts = []
    if system:
        if isinstance(system, list):
            system = ' '.join(
                s.get('text', '') for s in system if s.get('type') == 'text'
            )
        parts.append(f"System: {system}")
    for msg in messages:
        role    = msg.get('role', 'user').capitalize()
        content = msg.get('content', '')
        if isinstance(content, list):
            content = ' '.join(
                c.get('text', '') for c in content if c.get('type') == 'text'
            )
        parts.append(f"{role}: {content}")
    return '\n\n'.join(parts)


def _call_max(prompt: str, model: str) -> str:
    """Dispatch to claude -p with Max OAuth. Returns response text."""
    # Honor the model OpenCode requests; fall back to default
    cli_model = MODEL_MAP.get(model, CLAUDE_MODEL)
    result = subprocess.run(
        ['claude', '--model', cli_model, '-p', prompt,
         '--dangerously-skip-permissions'],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env=_clean_env(),
        cwd=CWD,
    )
    return result.stdout.strip() or result.stderr.strip() or '[max_proxy: empty response]'


# ── request handler ───────────────────────────────────────────────────────────

class MaxProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Minimal logging — errors only
        if args and isinstance(args[0], int) and args[0] >= 400:
            super().log_message(fmt, *args)

    # ── Health check ─────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path == '/health':
            body = b'{"status":"ok","proxy":"claude-max"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    # ── Main API surface ──────────────────────────────────────────────────────
    def do_POST(self):
        if self.path != '/v1/messages':
            self.send_error(404)
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, 'Bad JSON')
            return

        model  = data.get('model', CLAUDE_MODEL)
        stream = data.get('stream', False)
        prompt = _build_prompt(data.get('messages', []), data.get('system', ''))

        text   = _call_max(prompt, model)
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"

        if stream:
            self._send_stream(text, msg_id, model)
        else:
            self._send_json(text, msg_id, model)

    # ── Response formats ──────────────────────────────────────────────────────
    def _send_json(self, text: str, msg_id: str, model: str):
        body = json.dumps({
            "id": msg_id, "type": "message", "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "model": model, "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": len(text) // 4},
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, event: dict):
        line = f"data: {json.dumps(event)}\n\n".encode()
        self.wfile.write(line)

    def _send_stream(self, text: str, msg_id: str, model: str):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

        self._sse({"type": "message_start", "message": {
            "id": msg_id, "type": "message", "role": "assistant",
            "content": [], "model": model, "stop_reason": None,
            "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0},
        }})
        self._sse({"type": "content_block_start", "index": 0,
                   "content_block": {"type": "text", "text": ""}})

        # Stream in 80-char chunks so the TUI shows progressive output
        for i in range(0, len(text), 80):
            self._sse({"type": "content_block_delta", "index": 0,
                       "delta": {"type": "text_delta", "text": text[i:i+80]}})

        self._sse({"type": "content_block_stop", "index": 0})
        self._sse({"type": "message_delta",
                   "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                   "usage": {"output_tokens": len(text) // 4}})
        self._sse({"type": "message_stop"})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), MaxProxyHandler)
    print(f'[max_proxy] Claude MAX proxy — http://127.0.0.1:{PORT}', flush=True)
    server.serve_forever()
