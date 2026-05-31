#!/usr/bin/env python3
"""
Thunderbird Directory Server — Basic Auth + Directory Listing
Replaces python3 -m http.server with password protection.
Port 8900 | Serves /home/john/Thunderbird
"""
import base64
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

USERNAME = "john"
PASSWORD = "5277"
DIRECTORY = "/home/john/Thunderbird"
PORT = 8900
REALM = "D2M Thunderbird"

_CREDS = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()


class AuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_HEAD(self):
        if self._check_auth():
            super().do_HEAD()

    def do_GET(self):
        if self._check_auth():
            super().do_GET()

    def _check_auth(self):
        auth = self.headers.get("Authorization", "")
        if auth == f"Basic {_CREDS}":
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Length", "12")
        self.end_headers()
        self.wfile.write(b"Unauthorized")
        return False

    def log_message(self, fmt, *args):
        pass  # silence access log noise


if __name__ == "__main__":
    os.chdir(DIRECTORY)
    server = HTTPServer(("0.0.0.0", PORT), AuthHandler)
    print(f"Serving {DIRECTORY} on :{PORT} — auth required")
    server.serve_forever()
