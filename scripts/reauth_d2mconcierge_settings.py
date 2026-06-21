#!/usr/bin/env python3
"""
Re-authorize d2mconcierge with gmail.settings.basic scope added.
Commander runs this ONE TIME (opens browser, takes ~2 min).
After running: d2mconcierge filter creation will work.

Usage: python3 scripts/reauth_d2mconcierge_settings.py
"""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic',
]

CREDS_RAW   = Path.home() / '.config/google-workspace-mcp/credentials.json'
TOKEN_FILE  = Path('/home/john/Thunderbird/config/persona_gmail_token.json')
TOKEN_FILE2 = Path.home() / '.config/google-workspace-mcp/token.json'

def reauth():
    raw = json.load(open(CREDS_RAW))
    client_config = {
        'installed': {
            'client_id':     raw['client_id'],
            'client_secret': raw['client_secret'],
            'redirect_uris': raw.get('redirect_uris', ['http://localhost']),
            'auth_uri':      raw.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
            'token_uri':     raw.get('token_uri', 'https://oauth2.googleapis.com/token'),
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print('\n[d2mconcierge re-auth — log in as d2mconcierge@gmail.com]\n')
    creds = flow.run_local_server(port=0, open_browser=True)
    
    token_data = {
        'token':         creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri':     creds.token_uri,
        'client_id':     creds.client_id,
        'client_secret': creds.client_secret,
        'scopes':        list(creds.scopes) if creds.scopes else SCOPES,
    }
    
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    TOKEN_FILE2.write_text(json.dumps(token_data, indent=2))
    print(f"\n✅ d2mconcierge re-authorized with gmail.settings.basic scope")
    print(f"   Written: {TOKEN_FILE}")
    print(f"   Written: {TOKEN_FILE2}")
    print(f"\n   Run next: python3 scripts/create_d2mconcierge_filters.py")

if __name__ == '__main__':
    reauth()
