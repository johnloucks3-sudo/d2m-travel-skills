#!/usr/bin/env python3
"""
Thunderbird Directory Server — Basic Auth + File Manager Directory Listing
Port 8900 | Serves /home/john/Thunderbird
"""
import base64
import html
import os
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from io import BytesIO

# Multi-user credentials: username → (password, directory_scope)
USERS = {
    "john": ("OQybVhNgLUEK1Pk%k7#m", "/home/john/Thunderbird"),
    "Bryana": ("f7lieTWcZwcdc6N4EH2c", "/home/john/Thunderbird/Bryana"),
}
PORT = 8900
REALM = "D2M Thunderbird"


class AuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Directory set per-request in do_GET/do_HEAD based on authenticated user
        super().__init__(*args, directory=USERS["john"][1], **kwargs)

    def do_HEAD(self):
        user_dir = self._check_auth()
        if user_dir:
            self.directory = user_dir
            super().do_HEAD()

    def do_GET(self):
        user_dir = self._check_auth()
        if user_dir:
            self.directory = user_dir
            super().do_GET()

    def _check_auth(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                username, password = decoded.split(":", 1)
                if username in USERS and USERS[username][0] == password:
                    return USERS[username][1]  # Return scoped directory
            except Exception:
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Length", "12")
        self.end_headers()
        self.wfile.write(b"Unauthorized")
        return None

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        entries.sort(key=lambda e: (0 if os.path.isdir(os.path.join(path, e)) else 1, e.lower()))

        display_path = urllib.parse.unquote(self.path, errors="surrogatepass")
        display_path = html.escape(display_path, quote=False)

        # Build breadcrumb
        parts = display_path.strip("/").split("/")
        breadcrumb = '<a href="/" style="color:#f7f3ea;">Thunderbird</a>'
        acc = ""
        for part in parts:
            if part:
                acc += "/" + part
                breadcrumb += f' / <a href="{acc}/" style="color:#f7f3ea;">{html.escape(part)}</a>'

        rows = []
        if display_path != "/":
            rows.append(
                '<tr><td class="icon">📁</td>'
                '<td class="name dir"><a href="../">.. (parent)</a></td>'
                '<td class="size">—</td><td class="type">Directory</td></tr>'
            )

        for name in entries:
            fullname = os.path.join(path, name)
            is_dir = os.path.isdir(fullname)
            linkname = urllib.parse.quote(name, errors="surrogatepass")
            display_name = html.escape(name)

            try:
                size = os.path.getsize(fullname)
                size_str = _fmt_size(size) if not is_dir else "—"
            except OSError:
                size_str = "—"

            if is_dir:
                icon = "📁"
                href = f"{linkname}/"
                row_class = "dir-row"
                type_str = "Folder"
                name_html = f'<a href="{href}" class="dir-link">{display_name}</a>'
            else:
                icon = _file_icon(name)
                href = linkname
                row_class = "file-row"
                ext = name.rsplit(".", 1)[-1].upper() if "." in name else "FILE"
                type_str = ext
                name_html = f'<a href="{href}" class="file-link">{display_name}</a>'

            rows.append(
                f'<tr class="{row_class}">'
                f'<td class="icon">{icon}</td>'
                f'<td class="name">{name_html}</td>'
                f'<td class="size">{size_str}</td>'
                f'<td class="type">{type_str}</td>'
                f'</tr>'
            )

        body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thunderbird — {display_path}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f7f3ea;
    color: #1a1a1a;
    font-size: 14px;
  }}
  .topbar {{
    background: #003087;
    color: #f7f3ea;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .topbar .logo {{ font-size: 1.1rem; font-weight: bold; letter-spacing: 0.1em; }}
  .topbar .breadcrumb {{ font-size: 0.82rem; color: #a0b8d8; }}
  .topbar .breadcrumb a {{ color: #c8d8f0; text-decoration: none; }}
  .topbar .breadcrumb a:hover {{ color: #fff; }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  thead tr {{
    background: #e8e2d8;
    border-bottom: 2px solid #ccc6b8;
  }}
  thead th {{
    padding: 8px 14px;
    text-align: left;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #555;
  }}
  tbody tr {{
    border-bottom: 1px solid #e0d8cc;
    transition: background 0.1s;
  }}
  tbody tr:hover {{ background: #eee8da; }}
  .dir-row {{ background: #fff; }}
  .file-row {{ background: #faf8f4; }}
  td {{ padding: 8px 14px; vertical-align: middle; }}
  td.icon {{ width: 36px; font-size: 1.1rem; padding-right: 4px; }}
  td.name {{ max-width: 60vw; word-break: break-all; }}
  td.size {{ width: 80px; text-align: right; color: #888; font-size: 0.82rem; white-space: nowrap; }}
  td.type {{ width: 80px; color: #888; font-size: 0.78rem; text-align: right; padding-right: 16px; }}
  a.dir-link {{
    color: #003087;
    font-weight: 600;
    text-decoration: none;
  }}
  a.dir-link:hover {{ color: #0000ff; text-decoration: underline; }}
  a.file-link {{
    color: #1a1a1a;
    text-decoration: none;
  }}
  a.file-link:hover {{ color: #0000ff; text-decoration: underline; }}
  .parent a {{ color: #888; font-style: italic; }}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo">✈ THUNDERBIRD</div>
  <div class="breadcrumb">{breadcrumb}</div>
</div>
<table>
  <thead>
    <tr>
      <th></th>
      <th>Name</th>
      <th style="text-align:right;">Size</th>
      <th style="text-align:right;padding-right:16px;">Type</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
</body>
</html>"""

        encoded = body.encode("utf-8", "surrogateescape")
        f = BytesIO()
        f.write(encoded)
        f.seek(0)
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


def _file_icon(name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    icons = {
        "html": "🌐", "htm": "🌐",
        "md": "📝", "txt": "📄",
        "py": "🐍", "js": "📜", "sh": "⚙️",
        "json": "📋", "csv": "📊", "xlsx": "📊", "xls": "📊",
        "pdf": "📕",
        "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "gif": "🖼️", "webp": "🖼️",
        "mp4": "🎬", "mp3": "🎵",
        "zip": "🗜️", "gz": "🗜️", "tar": "🗜️",
        "log": "📃", "jsonl": "📃",
        "db": "🗄️", "sqlite": "🗄️",
    }
    return icons.get(ext, "📄")


if __name__ == "__main__":
    root = USERS["john"][1]
    os.chdir(root)
    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("0.0.0.0", PORT), AuthHandler)
    print(f"Serving {root} on :{PORT} — multi-user auth required")
    server.serve_forever()
