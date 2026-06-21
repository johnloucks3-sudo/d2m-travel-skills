#!/usr/bin/env python3
"""
Create d2mconcierge Gmail filters — run after reauth_d2mconcierge_settings.py
"""
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = '/home/john/Thunderbird/config/persona_gmail_token.json'

def main():
    token = json.load(open(TOKEN_FILE))
    creds_data = json.load(open('/home/john/.config/google-workspace-mcp/credentials.json'))
    creds = Credentials(token=token.get('token', token.get('access_token')),
        refresh_token=token['refresh_token'], token_uri='https://oauth2.googleapis.com/token',
        client_id=creds_data['client_id'], client_secret=creds_data['client_secret'])
    if creds.expired: creds.refresh(Request())
    svc = build('gmail', 'v1', credentials=creds)
    labels = {l['name']: l['id'] for l in svc.users().labels().list(userId='me').execute().get('labels',[])}
    
    CLIENT_ACTIVE  = labels.get('CLIENTS/Active', '')
    WING_INTERNAL  = labels.get('WING-INTERNAL', '')
    BOOK_CONFIRM   = labels.get('BOOKINGS/Confirmations', '')
    
    FILTERS = [
        {
            'name': 'Client replies → CLIENTS/Active',
            'criteria': {'from': 'kyle.kuklinski@gmail.com OR bkspencer381@gmail.com OR '
                'nancylyons73@outlook.com OR klyons3@bellsouth.net OR missy.furlow@gmail.com OR '
                'larry.nichols4811@gmail.com OR rwestbrook3@gmail.com OR iamheer@outlook.com OR bryanajarboe@gmail.com'},
            'action': {'addLabelIds': [CLIENT_ACTIVE]}
        },
        {
            'name': 'Booking confirmations → BOOKINGS/Confirmations',
            'criteria': {'from': 'rssc.com OR silversea.com OR viking.com OR oceaniacruises.com'},
            'action': {'addLabelIds': [BOOK_CONFIRM]}
        },
        {
            'name': 'Wing reports → WING-INTERNAL, skip inbox',
            'criteria': {'subject': '"EOD Brief" OR "Wing Status" OR "D2M Weekly" OR "[WF-17]" OR "A10:" OR "A2 Intel"'},
            'action': {'addLabelIds': [WING_INTERNAL], 'removeLabelIds': ['INBOX', 'UNREAD']}
        },
    ]
    
    for f in FILTERS:
        if not all(v for v in f['action'].get('addLabelIds', [None]) if v):
            print(f"⚠️  Skipped (missing label): {f['name']}")
            continue
        try:
            svc.users().settings().filters().create(userId='me', body={'criteria': f['criteria'], 'action': f['action']}).execute()
            print(f"✅ {f['name']}")
        except Exception as e:
            print(f"⚠️  {e}")

if __name__ == '__main__':
    main()
