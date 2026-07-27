#!/usr/bin/env python3
"""HTTP Basic-Auth static file server with query parameter bypass support."""
import base64, functools, http.server, os, sys
from http.server import SimpleHTTPRequestHandler

USER = os.environ.get("PORTAL_USER", "spencer")
PW = os.environ.get("PORTAL_PW", "spencer-12pax-grand2026")

class H(SimpleHTTPRequestHandler):
    def do_AUTH(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Spencer Grand Tour"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Authentication required for Spencer Portal")

    def check(self):
        # 1. Allow query token bypass
        if "token=d2m-spencer-12pax-secure" in self.path:
            return True
        # 2. Check Basic Auth header
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            u, p = base64.b64decode(h[6:]).decode().split(":", 1)
        except Exception:
            return False
        return u == USER and p == PW

    def do_GET(self):
        if not self.check():
            return self.do_AUTH()
        # Clean path for SimpleHTTPRequestHandler
        if "?" in self.path:
            self.path = self.path.split("?", 1)[0]
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_HEAD(self):
        if not self.check():
            return self.do_AUTH()
        if "?" in self.path:
            self.path = self.path.split("?", 1)[0]
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return super().do_HEAD()

if __name__ == "__main__":
    port = int(sys.argv[1])
    directory = sys.argv[2]
    handler = functools.partial(H, directory=directory)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
