#!/usr/bin/env python3
"""
Get Calendar OAuth token using Playwright Firefox.
Starts a local server, generates auth URL, opens in Firefox via Playwright,
waits for redirect, exchanges for token.
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
    server.timeout = 180  # 3 minute timeout

    def serve():
        while auth_response[0] is None:
            server.handle_request()

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    logger.info(f"Local server running on {redirect_uri}")
    logger.info(f"Opening auth URL in Firefox via Playwright...")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page()
            page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)

            logger.info("=== Firefox OAuth window open ===")
            logger.info("Waiting for authorization (up to 3 min)...")
            page.screenshot(path="/tmp/oauth_ff_start.png")

            # Wait for the auth response (the local server catches the redirect)
            server_thread.join(timeout=180)

            page.screenshot(path="/tmp/oauth_ff_end.png")
            browser.close()
    except Exception as e:
        logger.error(f"Playwright error: {e}")
        # Fallback: wait for manual authorization
        logger.info(f"If the browser didn't open, visit: {auth_url}")
        logger.info(f"Waiting up to 3 minutes for manual authorization...")
        server_thread.join(timeout=180)

    if not auth_response[0]:
        logger.error("No authorization response received.")
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
