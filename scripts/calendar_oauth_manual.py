#!/usr/bin/env python3
"""
Calendar OAuth — opens URL for user to authorize in their real Chrome browser.
1. Starts a local server to catch the OAuth redirect
2. Prints the authorization URL for the user to open in Chrome
3. Waits for the redirect and exchanges for a token
"""
import logging
import socket
import sys
import threading
import time
from pathlib import Path
from wsgiref.simple_server import make_server

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.scheduling.thunderbird_calendar_sync import (
    OAUTH_CREDENTIALS_FILE, CALENDAR_TOKEN_FILE, CALENDAR_SCOPES
)
from google_auth_oauthlib.flow import InstalledAppFlow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    if CALENDAR_TOKEN_FILE.exists():
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
        if creds and creds.valid:
            logger.info("Calendar token already exists and is valid.")
            return True
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired — refreshing...")
            creds.refresh(Request())
            CALENDAR_TOKEN_FILE.write_text(creds.to_json())
            logger.info("Refreshed and saved.")
            return True

    if not OAUTH_CREDENTIALS_FILE.exists():
        logger.error(f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}")
        return False

    # Find a free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    redirect_uri = f"http://localhost:{port}/"
    logger.info(f"Local server port: {port}")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES,
        redirect_uri=redirect_uri
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Start local server to catch OAuth redirect
    auth_response = [None]
    server_shutdown = [False]

    def wsgi_app(environ, start_response):
        query = environ.get('QUERY_STRING', '')
        if 'code=' in query or 'error=' in query:
            scheme = environ['wsgi.url_scheme']
            host = environ['HTTP_HOST']
            path = environ['PATH_INFO']
            auth_response[0] = f"{scheme}://{host}{path}?{query}"
            start_response('200 OK', [('Content-Type', 'text/html')])
            return [b"<html><body><h1>Authorization received!</h1><p>You can close this window.</p></body></html>"]
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b"Not Found"]

    server = make_server('localhost', port, wsgi_app)
    server.timeout = 180

    def serve():
        while not server_shutdown[0] and auth_response[0] is None:
            server.handle_request()

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    print("\n" + "=" * 70)
    print("  GOOGLE CALENDAR OAUTH AUTHORIZATION")
    print("=" * 70)
    print()
    print("  Step 1: Open this URL in your Chrome browser (already running):")
    print()
    print(f"  {auth_url}")
    print()
    print("  Step 2: Sign in with johnloucks3@gmail.com if prompted")
    print()
    print("  Step 3: Click 'Continue' to grant Calendar access")
    print()
    print("  The server will catch the redirect automatically.")
    print("  Waiting up to 3 minutes...")
    print("=" * 70)
    print()

    # Wait for the auth response
    server_thread.join(timeout=180)
    server_shutdown[0] = True

    if not auth_response[0]:
        logger.error("No authorization response received within 3 minutes.")
        return False

    logger.info("Authorization received! Exchanging for token...")
    flow.fetch_token(authorization_response=auth_response[0])

    if flow.credentials:
        CALENDAR_TOKEN_FILE.write_text(flow.credentials.to_json())
        logger.info(f"Calendar OAuth token saved to {CALENDAR_TOKEN_FILE}")
        return True
    else:
        logger.error("Failed to obtain credentials.")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
