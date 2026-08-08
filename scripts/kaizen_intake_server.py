#!/usr/bin/env python3
"""
kaizen_intake_server.py — Commander-facing ticket intake form.

KAIZEN item #1 extension (2026-08-08, Commander directive): a web form so
the Commander can draft a prompt with HIS OWN Gemini (web/Chrome, separate
from AG) or Grok (Super Grok — MCP access when logged in, but it does not
persist, so never assume either tool can write the ticket file directly),
paste the finished text here, and have it land as a real KAIZEN ticket
(OpsCenter/tickets/<id>.json) without a live CC chat session.

Single-user (Commander only), Basic Auth, stdlib http.server — matches this
repo's existing scripts/client_portal_server.py pattern, no new dependency.

GET  /            intake form (origin, seat, spec, verify_step, gates)
POST /submit      builds + writes the ticket via core.relay.task_templates,
                   redirects to a confirmation page showing the ticket_id

Origin tag (commander_gemini / commander_grok / commander_other) is
recorded on the ticket for audit — these are drafting aids only, never an
elevated-authority source. Gates default to empty (no Weapons Free scope)
unless the Commander explicitly types one in — gates are never inferred.
"""
import base64
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PORT = int(os.environ.get("KAIZEN_INTAKE_PORT", "8930"))
AUTH_USER = os.environ.get("KAIZEN_INTAKE_USER", "commander")
AUTH_PASS = os.environ.get("KAIZEN_INTAKE_PASS", "")  # set via EnvironmentFile, never hardcoded

FORM_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>KAIZEN Ticket Intake</title>
<style>
 body{font-family:Georgia,serif;background:#f7f3ea;color:#1a1a1a;max-width:720px;margin:40px auto;padding:0 20px}
 h1{color:#07076b;border-bottom:3px solid #07076b;padding-bottom:8px}
 label{display:block;margin-top:16px;font-weight:bold;color:#07076b}
 textarea,input,select{width:100%;box-sizing:border-box;padding:8px;margin-top:4px;font-family:Georgia,serif;font-size:14px}
 textarea{height:180px}
 button{margin-top:20px;background:#07076b;color:#f7f3ea;border:none;padding:10px 24px;font-size:15px;cursor:pointer}
 .hint{font-size:12px;color:#555;margin-top:2px}
</style></head><body>
<h1>KAIZEN Ticket Intake</h1>
<p class="hint">Draft with your own Gemini (web/Chrome) or Grok/Super Grok, paste the finished prompt below. This never runs anything automatically — it just writes a ticket file CC/OC will pick up.</p>
<form method="POST" action="/submit">
<label>Origin</label>
<select name="origin">
<option value="commander_gemini">My Gemini (web)</option>
<option value="commander_grok">My Grok / Super Grok</option>
<option value="commander_other">Other</option>
</select>
<label>Who should execute this? (seat)</label>
<select name="seat">
<option value="CC">CC (Claude)</option>
<option value="OC">OC (DeepSeek, $0)</option>
<option value="AG">AG (Gemini, Google-billed)</option>
</select>
<label>Task / prompt (pasted from Gemini or Grok)</label>
<textarea name="spec" required placeholder="Paste the drafted prompt here..."></textarea>
<label>Done means exactly... (checkable — a count, path, ref, or artifact)</label>
<input name="verify_step" required placeholder="e.g. scripts/foo.py exists and py_compile passes">
<label>Elevated gates (leave blank unless you explicitly want Weapons Free scope on this ticket)</label>
<input name="gates" placeholder="blank = routine work only, no elevated authority">
<button type="submit">Create Ticket</button>
</form>
</body></html>"""


def _check_auth(header: str) -> bool:
    if not AUTH_PASS:
        return False
    if not header or not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
        user, pw = decoded.split(":", 1)
    except Exception:
        return False
    return user == AUTH_USER and pw == AUTH_PASS


class Handler(BaseHTTPRequestHandler):
    def _unauthorized(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="KAIZEN Intake"')
        self.end_headers()

    def do_GET(self):
        if not _check_auth(self.headers.get("Authorization")):
            return self._unauthorized()
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = FORM_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not _check_auth(self.headers.get("Authorization")):
            return self._unauthorized()
        if self.path != "/submit":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()
        fields = urllib.parse.parse_qs(raw)
        origin = fields.get("origin", ["commander_other"])[0]
        seat = fields.get("seat", ["CC"])[0]
        spec = fields.get("spec", [""])[0].strip()
        verify_step = fields.get("verify_step", [""])[0].strip()
        gates_raw = fields.get("gates", [""])[0].strip()
        gates = [g.strip() for g in gates_raw.split(",") if g.strip()]

        from core.relay.task_templates import build_cc_task, write_ticket

        try:
            ticket = build_cc_task(
                spec, seat=seat, verify_step=verify_step, gates=gates,
                require_checkable=False,  # this form is Basic-Auth gated to the
                # Commander himself — his direct tasking never needed machine
                # checkability anywhere else in this system; the checkable gate
                # exists to stop OC/AG writing themselves vague tickets, not to
                # block the Commander's own.
            )
            ticket["origin"] = origin
            path = write_ticket(ticket)
            msg = f"Ticket created: {ticket['ticket_id']} -> {path}"
        except ValueError as e:
            msg = f"REJECTED: {e}"

        body = (
            f"<!doctype html><html><body style='font-family:Georgia,serif;max-width:600px;"
            f"margin:60px auto'><h2>{html.escape(msg)}</h2>"
            f"<a href='/'>&larr; new ticket</a></body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quiet — avoid noisy stdout under systemd


def main():
    if not AUTH_PASS:
        print("KAIZEN_INTAKE_PASS not set — refusing to start unauthenticated.", file=sys.stderr)
        sys.exit(1)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"KAIZEN intake listening on 127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
