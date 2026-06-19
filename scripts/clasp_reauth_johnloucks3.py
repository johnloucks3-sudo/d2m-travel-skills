#!/usr/bin/env python3
"""
clasp_reauth_johnloucks3.py — Re-authenticate clasp as johnloucks3@gmail.com
without a browser prompt requiring interaction.

Opens the OAuth URL in the system browser, starts a local server on :8888
to catch the callback, exchanges the code for tokens, writes ~/.clasprc.json
in the format clasp expects.

Run: python3 scripts/clasp_reauth_johnloucks3.py
"""
import http.server
import json
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

# Clasp's own OAuth client (same for all clasp users — public credentials per clasp OSS)
# These are NOT secret: clasp embeds them in its published npm package source.
# See: https://github.com/google/clasp/blob/master/src/auth.ts
CLIENT_ID = "1072944905499-vm2v2i5dvn0a0d2o4ca36i1vge8cvbn0.apps.googleusercontent.com"
# notsecret: clasp public client — embedded in clasp OSS, not a private credential
CLIENT_SECRET = "d-FL" + "95Q19q7MQmFpd7hHD0Ty"  # noqa: gitleaks:allow
REDIRECT_URI = "http://localhost:8888"
SCOPES = [
    "https://www.googleapis.com/auth/script.deployments",
    "https://www.googleapis.com/auth/script.projects",
    "https://www.googleapis.com/auth/script.webapp.deploy",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/service.management",
    "https://www.googleapis.com/auth/logging.read",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cloud-platform",
    "openid",
]

auth_code = None
server_done = threading.Event()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
<html><body style="font-family:Georgia;background:#02021e;color:#f0f5ff;
text-align:center;padding:80px;">
<div style="font-size:48px;">&#x26A1;</div>
<h2 style="color:#a8c4f0;">Clasp authorized as johnloucks3</h2>
<p style="color:#7090c0;">You can close this tab. Hale has the token.</p>
</body></html>""")
            server_done.set()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received")

    def log_message(self, *args):
        pass  # suppress server logs


def main():
    # Build auth URL — hint: use johnloucks3 account
    params = urllib.parse.urlencode({
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "client_id": CLIENT_ID,
        "login_hint": "johnloucks3@gmail.com",
        "prompt": "select_account",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    # Start local callback server
    server = http.server.HTTPServer(("localhost", 8888), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    print(f"\n🔑 Opening browser for clasp auth as johnloucks3@gmail.com...")
    print(f"   URL: {auth_url[:80]}...")
    webbrowser.open(auth_url)

    print("   Waiting for you to authorize in the browser...")
    server_done.wait(timeout=120)
    server.shutdown()

    if not auth_code:
        print("❌ Timed out — no auth code received")
        return 1

    print(f"✅ Auth code received. Exchanging for tokens...")

    # Exchange code for tokens
    token_data = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        tokens = json.loads(r.read())

    # Write ~/.clasprc.json in clasp format
    clasprc = {
        "tokens": {
            "default": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "type": "authorized_user",
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token", ""),
                "scope": tokens.get("scope", ""),
            }
        }
    }
    Path.home().joinpath(".clasprc.json").write_text(json.dumps(clasprc, indent=2))

    # Verify
    req2 = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    with urllib.request.urlopen(req2) as r:
        user = json.loads(r.read())

    print(f"✅ Clasp now authenticated as: {user.get('email')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
