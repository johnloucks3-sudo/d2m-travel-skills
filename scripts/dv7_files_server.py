#!/usr/bin/env python3
"""
dv7_files_server.py — always-on file browser for files.d2mluxury.quest.

Runs ON dv7. Serves ONLY ~/thunderbird_files (the curated, secret-free set pushed
from YOGA by scripts/yoga_dv7_files_sync.sh) so the Commander can reach session
output from any device when YOGA is off.

Two auth layers:
  1. Cloudflare Access at the edge (real gate — see deploy/FILES_DV7_RUNBOOK.md).
  2. HTTP Basic Auth here (defense in depth). Password from env DV7_FILES_PW.

Binds 127.0.0.1 only — cloudflared connects locally; nothing is exposed on the LAN.
"""
import base64
import html
import os
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from io import BytesIO
from pathlib import Path

SERVE_DIR = str(Path(os.environ.get("DV7_FILES_DIR", str(Path.home() / "thunderbird_files"))))
PORT = int(os.environ.get("DV7_FILES_PORT", "8930"))
USER = os.environ.get("DV7_FILES_USER", "john")
PASSWORD = os.environ.get("DV7_FILES_PW", "change-me-set-DV7_FILES_PW")
REALM = "D2M Files"


class AuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def do_HEAD(self):
        if self._authed():
            super().do_HEAD()

    def do_GET(self):
        if self._authed():
            super().do_GET()

    def _authed(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                user, pw = base64.b64decode(auth[6:]).decode().split(":", 1)
                if user == USER and pw == PASSWORD:
                    return True
            except Exception:
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Length", "12")
        self.end_headers()
        self.wfile.write(b"Unauthorized")
        return False

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        entries.sort(key=lambda e: (0 if os.path.isdir(os.path.join(path, e)) else 1, e.lower()))

        display_path = html.escape(urllib.parse.unquote(self.path, errors="surrogatepass"), quote=False)
        parts = [p for p in display_path.strip("/").split("/") if p]
        breadcrumb = '<a href="/" style="color:#c8d8f0;">Files</a>'
        acc = ""
        for part in parts:
            acc += "/" + part
            breadcrumb += f' / <a href="{acc}/" style="color:#c8d8f0;">{html.escape(part)}</a>'

        rows = []
        if display_path != "/":
            rows.append('<tr><td>📁</td><td><a href="../">.. (parent)</a></td><td>—</td></tr>')
        for name in entries:
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            link = urllib.parse.quote(name, errors="surrogatepass") + ("/" if is_dir else "")
            try:
                size = "—" if is_dir else _fmt_size(os.path.getsize(full))
            except OSError:
                size = "—"
            icon = "📁" if is_dir else "📄"
            rows.append(
                f'<tr><td>{icon}</td>'
                f'<td><a href="{link}">{html.escape(name)}</a></td>'
                f'<td class="size">{size}</td></tr>'
            )

        body = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D2M Files — {display_path}</title><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f7f3ea;color:#1a1a1a;font-size:14px}}
.topbar{{background:#003087;color:#f7f3ea;padding:12px 20px;display:flex;align-items:center;gap:12px}}
.logo{{font-size:1.1rem;font-weight:bold;letter-spacing:.1em}}
.breadcrumb{{font-size:.82rem;color:#a0b8d8}}
table{{width:100%;border-collapse:collapse}}
td{{padding:8px 14px;border-bottom:1px solid #e0d8cc}}
td:first-child{{width:36px;font-size:1.1rem}}
.size{{width:90px;text-align:right;color:#888;font-size:.82rem;white-space:nowrap}}
a{{color:#003087;text-decoration:none;font-weight:600}}
a:hover{{color:#0000ff;text-decoration:underline}}
tr:hover{{background:#eee8da}}
</style></head><body>
<div class="topbar"><div class="logo">✈ THUNDERBIRD FILES</div><div class="breadcrumb">{breadcrumb}</div></div>
<table><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
        encoded = body.encode("utf-8", "surrogateescape")
        f = BytesIO(encoded)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def log_message(self, fmt, *args):
        pass


def _fmt_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


if __name__ == "__main__":
    os.makedirs(SERVE_DIR, exist_ok=True)
    os.chdir(SERVE_DIR)
    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("127.0.0.1", PORT), AuthHandler)
    print(f"Serving {SERVE_DIR} on 127.0.0.1:{PORT} — Basic Auth + Cloudflare Access")
    server.serve_forever()
