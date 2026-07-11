#!/usr/bin/env python3
"""
tcd_server.py — Thunderbird Commander Desktop (TCD) v4 backend.

Single-tenant (Commander-only) stdlib HTTP server, same Basic-Auth pattern as
scripts/client_portal_server.py and scripts/thunderbird_dir_server.py (reuses
the Commander's existing site credential — no new password to remember).

Serves the wired TCD frontend (output/tcd_v4_wired.html) and a small JSON API
backed by:
  - scripts/tcd_data.py   — read-only adapter over live Wing state
  - OpsCenter/tcd_state.json        — overlay: comments / folder moves / outbox pushes
  - OpsCenter/tcd_interactions.json — append-only interaction audit log

Every mutating call is logged to tcd_interactions.json AND appended to
hale_decisions.md so the Commander's existing audit trail stays canonical —
this backend does not create a second source of truth for decisions.

Port: 8930 (dev/prod — see systemd unit + cloudflared ingress entry)
"""
import base64
import json
import re
import sys
import threading
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcd_data  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "OpsCenter/tcd_state.json"
LOG_FILE = ROOT / "OpsCenter/tcd_interactions.json"
VOICE_DIR = ROOT / "OpsCenter/tcd_voice_notes"
DECISIONS_MD = ROOT / "hale_decisions.md"
FRONTEND = ROOT / "output/tcd_v4_wired.html"

_auth = json.loads((ROOT / "creds/tcd_site_auth.json").read_text())
AUTH_USER = _auth["user"]
AUTH_PASS = _auth["pass"]
REALM = "Thunderbird Commander Desktop"
PORT = 8930
MAX_UPLOAD = 25 * 1024 * 1024

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"comments": {}, "folder_overrides": {}, "outbox_pushes": [], "read_overrides": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log_interaction(action, detail):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        entries = json.loads(LOG_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []
    entries.append({"ts": _now(), "user": AUTH_USER, "action": action, **detail})
    LOG_FILE.write_text(json.dumps(entries, indent=2))


def append_decision_log(text):
    with DECISIONS_MD.open("a") as f:
        f.write(f"\n<!-- TCD:{_now()} -->\n{text}\n")


def merged_data():
    data = tcd_data.build_data()
    state = load_state()
    comments = state.get("comments", {})
    overrides = state.get("folder_overrides", {})
    reads = state.get("read_overrides", {})
    for f in data["files"]:
        if f["id"] in comments:
            f["comments"] = f["comments"] + comments[f["id"]]
        if f["id"] in overrides:
            f["inbox"] = overrides[f["id"]].get("inbox", f["inbox"])
            f["folder"] = overrides[f["id"]].get("folder", f["folder"])
        if f["id"] in reads:
            f["unread"] = False
    pushed = list(reversed(state.get("outbox_pushes", [])))
    data["outbox"] = pushed + data["outbox"]
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = "TCD/1.0"

    def authed(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            u, p = base64.b64decode(h[6:]).decode().split(":", 1)
        except Exception:
            return False
        return u == AUTH_USER and p == AUTH_PASS

    def deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Auth required")

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _body_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    # --- GET -------------------------------------------------------
    def do_GET(self):
        if not self.authed():
            return self.deny()
        path = self.path.split("?")[0]
        if path == "/api/data":
            return self._json(200, merged_data())
        if path == "/" or path == "/index.html":
            if not FRONTEND.is_file():
                return self._send(500, b'{"error":"frontend not built yet"}')
            return self._send(200, FRONTEND.read_bytes(), "text/html; charset=utf-8")
        return self._send(404, b'{"error":"not found"}')

    def do_HEAD(self):
        self.do_GET()

    # --- POST --------------------------------------------------------
    def do_POST(self):
        if not self.authed():
            return self.deny()
        path = self.path.split("?")[0]
        with _lock:
            if path == "/api/comment":
                return self._handle_comment()
            if path == "/api/move":
                return self._handle_move()
            if path == "/api/outbox":
                return self._handle_outbox()
            if path == "/api/read":
                return self._handle_read()
            if path == "/api/voicenote":
                return self._handle_voicenote()
        return self._send(404, b'{"error":"not found"}')

    def _handle_comment(self):
        body = self._body_json()
        file_id, text = body.get("fileId"), (body.get("text") or "").strip()
        if not file_id or not text:
            return self._json(400, {"error": "fileId and text required"})
        state = load_state()
        state["comments"].setdefault(file_id, []).append(
            {"author": "Commander", "ts": datetime.now().strftime("%b %d, %H:%M"), "text": text})
        save_state(state)
        log_interaction("comment", {"fileId": file_id, "text": text})
        append_decision_log(f"**TCD comment** on `{file_id}`: {text}")
        return self._json(200, {"ok": True})

    def _handle_move(self):
        body = self._body_json()
        file_id, to_inbox, to_folder = body.get("fileId"), body.get("toInbox"), body.get("toFolder")
        if not all([file_id, to_inbox, to_folder]):
            return self._json(400, {"error": "fileId, toInbox, toFolder required"})
        state = load_state()
        state["folder_overrides"][file_id] = {"inbox": to_inbox, "folder": to_folder}
        save_state(state)
        log_interaction("move", {"fileId": file_id, "toInbox": to_inbox, "toFolder": to_folder})
        append_decision_log(f"**TCD move** `{file_id}` -> {to_inbox}/{to_folder}")
        return self._json(200, {"ok": True})

    def _handle_read(self):
        body = self._body_json()
        file_id = body.get("fileId")
        if not file_id:
            return self._json(400, {"error": "fileId required"})
        state = load_state()
        state["read_overrides"][file_id] = True
        save_state(state)
        return self._json(200, {"ok": True})

    def _handle_outbox(self):
        body = self._body_json()
        file_id, title = body.get("fileId"), (body.get("title") or "").strip()
        conditions = (body.get("conditions") or "").strip()
        assigned = (body.get("assignedTo") or "").strip()
        deadline = (body.get("deadline") or "").strip()
        if not file_id or not title:
            return self._json(400, {"error": "fileId and title required"})
        state = load_state()
        entry = {
            "id": f"px-{file_id}-{int(datetime.now().timestamp())}", "fileId": file_id,
            "title": title, "executed": False,
            "execDate": datetime.now().strftime("%b %d, %H:%M"),
            "from": "Commander outbox push",
            "stage": "T", "conditions": conditions, "assignedTo": assigned, "deadline": deadline,
        }
        state["outbox_pushes"].append(entry)
        save_state(state)
        log_interaction("outbox_push", entry)
        append_decision_log(
            f"**TCD P-D-T-A-C task opened** `{entry['id']}` from `{file_id}`: {title}\n"
            f"Conditions: {conditions or 'n/a'} | Assigned: {assigned or 'unassigned'} | Deadline: {deadline or 'n/a'}")
        return self._json(200, {"ok": True, "entry": entry})

    def _handle_voicenote(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD:
            return self._json(413, {"error": "file too large"})
        ctype = self.headers.get("Content-Type", "")
        raw = self.rfile.read(length)
        msg = BytesParser(policy=email_default).parsebytes(
            b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw)
        file_id = None
        saved = None
        VOICE_DIR.mkdir(parents=True, exist_ok=True)
        for part in msg.iter_parts():
            name = part.get_param("name", header="Content-Disposition")
            if name == "fileId":
                file_id = part.get_payload(decode=True).decode().strip()
            elif part.get_filename():
                fn = re.sub(r"[^A-Za-z0-9._-]", "_", part.get_filename())[:120]
                dest = VOICE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}_{fn}"
                dest.write_bytes(part.get_payload(decode=True))
                saved = dest.name
        if not file_id or not saved:
            return self._json(400, {"error": "fileId and audio file required"})
        state = load_state()
        state["comments"].setdefault(file_id, []).append(
            {"author": "Commander", "ts": datetime.now().strftime("%b %d, %H:%M"),
             "text": f"[voice note: {saved}]", "voiceNote": f"/voice/{saved}"})
        save_state(state)
        log_interaction("voice_note", {"fileId": file_id, "file": saved})
        append_decision_log(f"**TCD voice note** on `{file_id}`: {saved}")
        return self._json(200, {"ok": True, "file": saved})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{datetime.now():%H:%M:%S} {fmt % args}\n")


def main():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        save_state(load_state())
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"TCD server listening on 127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
