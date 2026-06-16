#!/usr/bin/env python3
"""
Re-auth d2mconcierge ADDING gmail.settings.sharing (needed to create the
concierge@d2mluxury.quest send-as alias via API). One-time interactive consent.
Writes refreshed token to config/persona_gmail_token.json.
Run:  python3 scripts/reauth_d2mconcierge_sharing.py
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

HOME = Path.home()
CLIENT = HOME / ".gmail-mcp" / "d2mconcierge" / "gcp-oauth.keys.json"
OUT = Path("config/persona_gmail_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.settings.sharing",
]

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
# headless box: prints a URL, you open it on YOUR machine, paste the code back
creds = flow.run_local_server(port=0, open_browser=False)
tok = {
    "token": creds.token, "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri, "client_id": creds.client_id,
    "client_secret": creds.client_secret, "scopes": list(creds.scopes),
}
OUT.write_text(json.dumps(tok, indent=2))
print("WROTE", OUT, "scopes:", sorted(creds.scopes))
