"""
D2M LLM Proxy — OpenAI-compatible local endpoint
Forwards requests to Together AI using the configured API key.
AnythingLLM points to http://localhost:3002/v1 with any dummy key.

Usage: python3 thunderbird_llm_proxy.py
Port: 3002
"""
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

TOGETHER_API_KEY = "***REMOVED-SECRET***"
TOGETHER_BASE = "https://api.together.xyz/v1"
DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
PORT = 3002


class ProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}")

    def do_GET(self):
        if self.path in ("/v1/models", "/v1/models/"):
            models = {
                "object": "list",
                "data": [
                    {"id": DEFAULT_MODEL, "object": "model", "owned_by": "together"},
                    {"id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "object": "model", "owned_by": "together"},
                    {"id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "object": "model", "owned_by": "together"},
                ]
            }
            self._send_json(200, models)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # Forward to Together
        target = TOGETHER_BASE + self.path.replace("/v1", "", 1)
        req = urllib.request.Request(
            target,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json",
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
    print(f"[D2M LLM Proxy] Forwarding to Together AI → {DEFAULT_MODEL}")
    server.serve_forever()
