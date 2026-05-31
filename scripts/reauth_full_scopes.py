"""
Headless OAuth re-auth — single process, preserves PKCE code verifier.
Run once. Paste the redirect URL when prompted.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/contacts",
]

flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
flow.redirect_uri = "http://localhost:8087/"

auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

print("\n" + "="*60)
print("Open this URL in Chrome or Firefox:")
print("="*60)
print(auth_url)
print("="*60)
print("\nApprove all permissions. Browser will land on an error page.")
print("Copy the FULL URL from the address bar and paste it below.\n")

redirect_url = input("Paste redirect URL here: ").strip()

parsed = urlparse(redirect_url)
params = parse_qs(parsed.query)
code = params.get("code", [None])[0]
if not code:
    print("ERROR: No 'code' in URL. Copy the full address bar URL.")
    sys.exit(1)

flow.fetch_token(code=code)
creds = flow.credentials
TOKEN_FILE.write_text(creds.to_json())
print(f"\n✅ Token saved to {TOKEN_FILE}")
print(f"   Scopes: {sorted(creds.scopes)}")
