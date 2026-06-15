"""
D2M LLM Proxy — OpenAI-compatible local endpoint
Forwards requests to Groq (free tier) using the GROQ_API_KEY from the environment.
AnythingLLM points to http://localhost:3002/v1 with any dummy key.

Repointed Together AI -> Groq on 2026-06-15 (MISSION-267, Commander-approved):
  - removes the Together dependency (consolidation)
  - removes the hardcoded API key (security H10) -> reads GROQ_API_KEY from env
  - same model class (Llama-3.3-70B), free tier, OpenAI-compatible

Usage: python3 thunderbird_llm_proxy.py
Port: 3002
"""
import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load GROQ_API_KEY from env or .env (no hardcoded secrets)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    try:
        for _line in open(os.path.join(os.path.dirname(__file__), "..", ".env")):
            if _line.startswith("GROQ_API_KEY="):
                GROQ_API_KEY = _line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    except Exception:
        pass

GROQ_BASE = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"   # Groq Llama-3.3-70B (free tier)
_GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
}
PORT = 3002


class ProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}")

    def do_GET(self):
        if self.path in ("/v1/models", "/v1/models/"):
            models = {
                "object": "list",
                "data": [
                    {"id": DEFAULT_MODEL, "object": "model", "owned_by": "groq"},
                    {"id": "llama-3.1-8b-instant", "object": "model", "owned_by": "groq"},
                ]
            }
            self._send_json(200, models)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # Force a valid Groq model (callers may still send Together model names)
        try:
            payload = json.loads(body) if body else {}
            if isinstance(payload, dict):
                if payload.get("model") not in _GROQ_MODELS:
                    payload["model"] = DEFAULT_MODEL
                body = json.dumps(payload).encode()
        except Exception:
            pass  # forward as-is if not JSON

        # Forward to Groq (OpenAI-compatible)
        target = GROQ_BASE + self.path.replace("/v1", "", 1)
        req = urllib.request.Request(
            target,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                # Groq sits behind Cloudflare which 1010-blocks the default urllib UA
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) D2M-LLM-Proxy/1.0",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_body = resp.read()
                self._raw_response(resp.status, resp_body,
                                   resp.headers.get("Content-Type", "application/json"))
        except urllib.error.HTTPError as e:
            self._raw_response(e.code, e.read(), "application/json")
        except Exception as ex:
            self._send_json(502, {"error": str(ex)})

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self._raw_response(code, body, "application/json")

    def _raw_response(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"[D2M LLM Proxy] Listening on http://127.0.0.1:{PORT}/v1")
    print(f"[D2M LLM Proxy] Forwarding to Groq -> {DEFAULT_MODEL} (key {'set' if GROQ_API_KEY else 'MISSING'})")
    server.serve_forever()
