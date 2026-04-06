from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/calendar']
flow = InstalledAppFlow.from_client_secrets_file('/home/john/Thunderbird/credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
with open('/home/john/Thunderbird/gmail_token.json', 'w') as token:
    token.write(creds.to_json())
print("✅ TOKEN SUCCESSFULLY GENERATED AND SAVED!")
