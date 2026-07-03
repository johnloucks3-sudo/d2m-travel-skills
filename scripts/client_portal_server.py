#!/usr/bin/env python3
"""
client_portal_server.py — ONE server for ALL client portals (multi-tenant).

Routes by Host header against config/client_portals.json:
  "loucks.d2mluxury.quest" -> {slug, dir, user, pw, name, drive_folder}

Per client:
  GET  /...            static from <dir>/html/ (Basic Auth, per-client password)
  GET  /files          dark-navy Documents & Uploads page (portal docs + client uploads + upload form)
  POST /upload         multipart file upload -> <dir>/uploads/ + best-effort push to the
                       client's Google Drive folder (background thread; queued if offline)

Replaces the one-service-one-port-one-ingress-per-client ritual: new client =
one folder + one registry entry. Cloudflare ingress points every client hostname
at this single port (default 8925).

Dreams2Memories Travel, LLC · 2026-07-03 (Loucks Dec 2026 = first tenant)
"""
import base64
import html
import io
import json
import re
import sys
import threading
from datetime import datetime
from email.parser import BytesParser
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config/client_portals.json"
MAX_UPLOAD = 25 * 1024 * 1024  # 25 MB

MIME = {".html": "text/html", ".htm": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        ".svg": "image/svg+xml", ".pdf": "application/pdf", ".json": "application/json",
        ".md": "text/plain", ".txt": "text/plain", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".ico": "image/x-icon"}


def load_registry():
    return json.loads(REGISTRY.read_text())


def push_to_drive(local_path: Path, folder_id: str):
    """Best-effort background push of an uploaded file into the client's Drive folder."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        tok = ROOT / "creds/drive_token.json"
        creds = Credentials.from_authorized_user_file(str(tok), ["https://www.googleapis.com/auth/drive"])
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tok.write_text(creds.to_json())
        svc = build("drive", "v3", credentials=creds)
        media = MediaFileUpload(str(local_path), resumable=True)
        svc.files().create(body={"name": local_path.name, "parents": [folder_id]},
                           media_body=media, fields="id").execute()
        (local_path.parent / ".drive_pushed").open("a").write(f"{local_path.name}\n")
    except Exception as e:  # queued: uploads dir is the queue; a later push can retry
        (local_path.parent / ".drive_push_failed").open("a").write(f"{local_path.name}\t{e}\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "D2MPortal/1.0"

    # --- tenant + auth -------------------------------------------------
    def tenant(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        reg = load_registry()
        return reg.get(host)

    def authed(self, t):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            u, p = base64.b64decode(h[6:]).decode().split(":", 1)
        except Exception:
            return False
        return u == t["user"] and p == t["pw"]

    def deny(self, t):
        # header values are latin-1 — strip anything fancier (em-dashes in client names)
        realm = (t["name"] if t else "D2M").encode("ascii", "ignore").decode() or "D2M"
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{realm}"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Auth required")

    def _send(self, code, body: bytes, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- GET ------------------------------------------------------------
    def do_GET(self):
        t = self.tenant()
        if not t:
            return self._send(404, b"Unknown portal")
        if not self.authed(t):
            return self.deny(t)
        path = self.path.split("?")[0]
        if path == "/files":
            return self._send(200, self.files_page(t).encode())
        base = (ROOT / t["dir"] / "html").resolve()
        rel = path.lstrip("/") or "index.html"
        if path.startswith("/uploads/"):
            base = (ROOT / t["dir"] / "uploads").resolve()
            rel = path[len("/uploads/"):]
        target = (base / rel).resolve()
        if not str(target).startswith(str(base)) or not target.is_file():
            return self._send(404, b"Not found")
        self._send(200, target.read_bytes(), MIME.get(target.suffix.lower(), "application/octet-stream"))

    def do_HEAD(self):
        self.do_GET()

    # --- POST /upload -----------------------------------------------------
    def do_POST(self):
        t = self.tenant()
        if not t:
            return self._send(404, b"Unknown portal")
        if not self.authed(t):
            return self.deny(t)
        if self.path.split("?")[0] != "/upload":
            return self._send(404, b"Not found")
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD:
            return self._send(413, b"File too large (25 MB max)")
        ctype = self.headers.get("Content-Type", "")
        raw = self.rfile.read(length)
        msg = BytesParser(policy=email_default).parsebytes(
            b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw)
        saved = []
        updir = ROOT / t["dir"] / "uploads"
        updir.mkdir(parents=True, exist_ok=True)
        for part in msg.iter_parts():
            fn = part.get_filename()
            if not fn:
                continue
            fn = re.sub(r"[^A-Za-z0-9._ -]", "_", fn)[:120]
            dest = updir / f"{datetime.now():%Y%m%d-%H%M}_{fn}"
            dest.write_bytes(part.get_payload(decode=True))
            saved.append(dest)
        for p in saved:
            if t.get("drive_folder"):
                threading.Thread(target=push_to_drive, args=(p, t["drive_folder"]), daemon=True).start()
        body = ("<script>location='/files?ok=" + str(len(saved)) + "'</script>").encode()
        return self._send(200, body)

    # --- files page --------------------------------------------------------
    def files_page(self, t):
        docs_dir = ROOT / t["dir"] / "html"
        updir = ROOT / t["dir"] / "uploads"
        def rows(d, link_prefix):
            out = []
            if d.is_dir():
                for f in sorted(d.iterdir(), key=lambda x: x.name):
                    if f.name.startswith(".") or f.name == "index.html" or not f.is_file():
                        continue
                    kb = max(1, f.stat().st_size // 1024)
                    ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y")
                    out.append(f'<tr><td><a href="{link_prefix}{html.escape(f.name)}">{html.escape(f.name)}</a></td>'
                               f'<td>{kb:,} KB</td><td>{ts}</td></tr>')
            return "\n".join(out) or '<tr><td colspan="3"><em>None yet</em></td></tr>'
        drive = t.get("drive_link", "")
        drive_html = (f'<p>All working copies also live in your '
                      f'<a href="{drive}">Google Drive folder</a>.</p>') if drive else ""
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(t['name'])} — Documents</title><style>
body{{margin:0;font-family:Georgia,serif;color:#e8f1ff;background:#07076b;
background:radial-gradient(ellipse at 50% -6%,#2428b0 0%,#0e1088 16%,#07076b 44%,#02022e 100%);background-attachment:fixed}}
.wrap{{max-width:760px;margin:0 auto;padding:40px 16px}}
h1{{color:#f0f6ff;font-weight:normal;font-size:26px}} h2{{color:#c8dcff;font-weight:normal;font-size:19px;
border-bottom:1px solid rgba(180,200,255,.35);padding-bottom:8px;margin-top:34px}}
table{{width:100%;border-collapse:collapse;font-size:15px;margin:10px 0 22px}}
th{{background:#0a0a68;text-align:left;font-weight:normal;padding:9px 12px;border:1px solid rgba(180,200,255,.22)}}
td{{padding:9px 12px;border:1px solid rgba(180,200,255,.15);color:#d0e4ff}}
a{{color:#a8c4f0}} .up{{background:rgba(120,150,255,.14);border:1px solid rgba(180,200,255,.4);
border-radius:10px;padding:18px 22px;margin-top:8px}}
input[type=file]{{color:#d0e4ff;font-family:Georgia,serif}}
button{{background:#c8d8ff;color:#07076b;border:0;border-radius:6px;padding:9px 22px;
font-family:Georgia,serif;font-size:15px;cursor:pointer;margin-top:10px}}
.back{{font-size:14px}}</style></head><body><div class="wrap">
<p class="back"><a href="/">&larr; Back to your trip portal</a></p>
<h1>{html.escape(t['name'])} — Documents &amp; Files</h1>
<h2>Your trip documents</h2>
<table><tr><th>Document</th><th>Size</th><th>Updated</th></tr>{rows(docs_dir, '/')}</table>
<h2>Your uploaded files</h2>
<table><tr><th>File</th><th>Size</th><th>Uploaded</th></tr>{rows(updir, '/uploads/')}</table>
<div class="up"><b>Send us a document</b> — passports, preferences, forms, anything trip-related.
It lands with your travel team (and in your shared Drive folder) the moment it uploads.
<form method="POST" action="/upload" enctype="multipart/form-data">
<input type="file" name="file" required> <button type="submit">Upload</button></form></div>
{drive_html}
<p style="color:#8fa8d8;font-size:12px;margin-top:36px">Dreams2Memories Travel, LLC · Private client portal</p>
</div></body></html>"""

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{datetime.now():%H:%M:%S} {self.headers.get('Host','-')} {fmt % args}\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8925
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
