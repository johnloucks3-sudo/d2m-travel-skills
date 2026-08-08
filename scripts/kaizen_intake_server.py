#!/usr/bin/env python3
"""
kaizen_intake_server.py — shared ticket intake form, password-gated.

KAIZEN item #1 extension (2026-08-08, Commander directive; opened to staff
2026-08-08): a web form to draft a prompt with an outside tool (the
Commander's own Gemini web/Chrome, separate from AG; Grok/Super Grok — MCP
access when logged in doesn't persist, so never assume either tool can write
the ticket file directly) or type one directly, paste it here, and have it
land as a real KAIZEN ticket (OpsCenter/tickets/<id>.json) without a live CC
chat session.

Shared Basic-Auth (Commander directive 2026-08-08): anyone who authenticates
with the shared password is authorized — the password IS the authorization
check, no per-user allowlist. Stdlib http.server — matches this repo's
existing scripts/client_portal_server.py pattern, no new dependency.

GET  /            intake form (submitted_by, email, phone, origin, seat, spec, verify_step, gates)
POST /submit      builds + writes the ticket via core.relay.task_templates,
                   redirects to a confirmation page showing the ticket_id

`submitted_by`/email/phone (all required) record WHO typed the ticket now
that the login is shared — separate from `origin`, which tags which
drafting tool (if any) produced the prompt text, never an elevated-authority
source. Gates default to empty (no Weapons Free scope) unless explicitly
typed in — gates are never inferred.

Commander-visibility alert (2026-08-08 directive): if the submitted email
AND phone both fail to match the Commander's own on file, a NOW-urgency
Telegram breaks through immediately (not the WINDOW batch) — "someone else
is using this" per his own words. Matching either field is enough to count
as the Commander himself; blank fields never match, so an unfilled
submission always alerts.
"""
import base64
import html
import os
import re
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

COMMANDER_EMAIL = os.environ.get("KAIZEN_COMMANDER_EMAIL", "johnloucks3@gmail.com").strip().lower()
COMMANDER_PHONE = re.sub(r"\D", "", os.environ.get("KAIZEN_COMMANDER_PHONE", "719-291-0742"))[-10:]


def _looks_like_commander(email: str, phone: str) -> bool:
    email_norm = (email or "").strip().lower()
    phone_norm = re.sub(r"\D", "", phone or "")[-10:]
    if email_norm and email_norm == COMMANDER_EMAIL:
        return True
    if phone_norm and phone_norm == COMMANDER_PHONE:
        return True
    return False

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
<div style="background:#fff;border-left:4px solid #07076b;padding:14px 18px;margin:16px 0;font-size:14px;line-height:1.5">
<p style="margin:0 0 8px"><b>You've got three consultants on call — and they're all yours.</b></p>
<p style="margin:0 0 8px">Every ticket here lands with three seats you get to pick from, depending on the job:</p>
<ul style="margin:0 0 8px;padding-left:20px">
<li><b>CC (Claude)</b> — the judgment seat. Big builds, careful reasoning, writing that needs a real voice behind it.</li>
<li><b>OC (DeepSeek)</b> — the $0 workhorse. Ops, scripts, the routine work that keeps this Wing turning.</li>
<li><b>AG (Gemini)</b> — the second pair of eyes. Deep research, massive documents, the independent look.</li>
</ul>
<p style="margin:0">Not sure who should do it? Leave it to us — send the ticket, and one of us picks it up. <i>(Not sure what "elevated gates" means? Leave it blank — that's exactly what we'd hope you'd do.)</i> — Dani</p>
</div>
<p class="hint">Draft with an outside tool (Gemini web, Grok/Super Grok) or type it directly, paste the finished prompt below. This never runs anything automatically — it just writes a ticket file CC/OC will pick up.</p>
<form method="POST" action="/submit">
<label>Your name (for the record)</label>
<input name="submitted_by" required placeholder="e.g. John, Dani, Sterling">
<label>Your delivery email</label>
<input name="email" type="email" required placeholder="you@example.com">
<label>Your phone number</label>
<input name="phone" type="tel" required placeholder="e.g. 719-291-0742">
<label>Origin (which tool drafted the prompt, if any)</label>
<select name="origin">
<option value="my_gemini">My Gemini (web)</option>
<option value="my_grok">My Grok / Super Grok</option>
<option value="other">Other / typed directly</option>
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
        submitted_by = fields.get("submitted_by", [""])[0].strip() or "unknown"
        email = fields.get("email", [""])[0].strip()
        phone = fields.get("phone", [""])[0].strip()
        origin = fields.get("origin", ["other"])[0]
        seat = fields.get("seat", ["CC"])[0]
        spec = fields.get("spec", [""])[0].strip()
        verify_step = fields.get("verify_step", [""])[0].strip()
        gates_raw = fields.get("gates", [""])[0].strip()
        gates = [g.strip() for g in gates_raw.split(",") if g.strip()]

        from core.relay.task_templates import build_cc_task, write_ticket

        try:
            ticket = build_cc_task(
                spec, seat=seat, verify_step=verify_step, gates=gates,
                require_checkable=False,  # this form is Basic-Auth gated to
                # holders of the shared password (Commander directive
                # 2026-08-08: anyone who logs in is authorized) — direct human
                # tasking never needed machine checkability anywhere else in
                # this system; the checkable gate exists to stop OC/AG writing
                # themselves vague tickets, not to block a human submitter's.
            )
            ticket["origin"] = origin
            ticket["submitted_by"] = submitted_by
            ticket["submitted_email"] = email
            ticket["submitted_phone"] = phone
            path = write_ticket(ticket)
            msg = f"Ticket created: {ticket['ticket_id']} -> {path}"

            if not _looks_like_commander(email, phone):
                try:
                    from core.comms.commander_channel import notify
                    notify(
                        "ops",
                        f"KAIZEN ticket from {submitted_by} — not your own email/phone",
                        (
                            f"Someone submitted a KAIZEN ticket whose email/phone didn't "
                            f"match your own on file.\n\n"
                            f"- **Name:** {submitted_by}\n- **Email:** {email or '(blank)'}\n"
                            f"- **Phone:** {phone or '(blank)'}\n- **Seat tasked:** {seat}\n"
                            f"- **Ticket:** {ticket['ticket_id']}\n- **Task:** {spec[:200]}"
                        ),
                        urgency="NOW",
                        reason="Commander visibility directive 2026-08-08 — shared-password "
                               "intake form, alert immediately when the submitter isn't him.",
                        dedup_key=f"kaizen-other-submitter-{ticket['ticket_id']}",
                    )
                except Exception:
                    pass  # never let an alert failure block ticket creation
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
