"""
Dreams2Memories TESS API Client
================================

OAuth 2.0 + PKCE client for the Outside Agents TESS CRM API.
Ported from the JavaScript spec in docs/tess_and_tokens_raw.md.

Features:
- OAuth 2.0 Authorization Code + PKCE flow
- Automatic token refresh with 5-minute buffer
- Token persistence to ~/Thunderbird/tess_token.json
- API client with auto-retry on 401
- MCP tool registration for Claude integration
- CLI for setup and testing

Auth endpoints: https://auth.outsideagents.com/oauth2
API base:       https://api.outsideagents.com/tess/v2

Integrates with: travel_mcp_server.py
Dependencies:    requests (already installed)
"""

import base64
import hashlib
import http.server
import json
import logging
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Optional

import requests

from pydantic import Field

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TOKEN_FILE = THUNDERBIRD_DIR / "tess_token.json"
CONFIG_FILE = THUNDERBIRD_DIR / "tess_config.json"

AUTH_BASE_URL = "https://auth.outsideagents.com/oauth2"
API_BASE_URL = "https://api.outsideagents.com/tess/v2"

REDIRECT_URI = "http://localhost:8089/callback"
CALLBACK_PORT = 8089

SCOPES = [
    "agent:read",
    "agent:write",
    "bookings:read",
    "bookings:write",
    "clients:read",
    "clients:write",
    "commissions:read",
    "suppliers:read",
]

USER_AGENT = "D2M-Thunderbird/1.0"


# ============================================================================
# PKCE Helpers
# ============================================================================

def _generate_code_verifier() -> str:
    """Generate a cryptographically random PKCE code verifier (43-128 chars)."""
    return _base64url_encode(secrets.token_bytes(32))


def _generate_code_challenge(verifier: str) -> str:
    """Generate S256 PKCE code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _base64url_encode(digest)


def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding (RFC 7636)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ============================================================================
# TESSAuth — OAuth 2.0 + PKCE Authentication
# ============================================================================

class TESSAuth:
    """OAuth 2.0 + PKCE authentication for the TESS API."""

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id or os.environ.get("TESS_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("TESS_CLIENT_SECRET", "")
        self._tokens: dict | None = None

        # Try loading config file if env vars not set
        if not self.client_id and CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.client_id = cfg.get("client_id", "")
                self.client_secret = cfg.get("client_secret", "")
            except Exception:
                pass

        # Load existing tokens
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from disk."""
        if TOKEN_FILE.exists():
            try:
                self._tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load TESS tokens: {e}")
                self._tokens = None

    def _save_tokens(self):
        """Persist tokens to disk."""
        if self._tokens:
            TOKEN_FILE.write_text(
                json.dumps(self._tokens, indent=2),
                encoding="utf-8",
            )

    @property
    def is_configured(self) -> bool:
        """True if client credentials are available."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_authenticated(self) -> bool:
        """True if we have stored tokens (may be expired)."""
        return self._tokens is not None and "access_token" in self._tokens

    def authorize(self) -> bool:
        """Run the full OAuth 2.0 + PKCE authorization flow.

        Opens a browser for user consent, runs a localhost callback server
        to catch the redirect, exchanges the code for tokens, and saves them.
        Returns True on success.
        """
        if not self.is_configured:
            print("ERROR: TESS client credentials not configured.")
            print()
            print("Set environment variables:")
            print("  export TESS_CLIENT_ID='your-client-id'")
            print("  export TESS_CLIENT_SECRET='your-client-secret'")
            print()
            print("Or create ~/Thunderbird/tess_config.json:")
            print('  {"client_id": "...", "client_secret": "..."}')
            return False

        # Generate PKCE values
        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        auth_url = f"{AUTH_BASE_URL}/authorize?{urllib.parse.urlencode(params)}"

        # Start callback server
        result = {"code": None, "error": None}
        server_ready = threading.Event()

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)

                # Validate state
                received_state = qs.get("state", [None])[0]
                if received_state != state:
                    result["error"] = "State mismatch — possible CSRF attack"
                    self._respond("Authorization failed: state mismatch. Close this tab.")
                    return

                if "error" in qs:
                    result["error"] = qs.get("error_description", qs["error"])[0]
                    self._respond(f"Authorization failed: {result['error']}. Close this tab.")
                    return

                code = qs.get("code", [None])[0]
                if not code:
                    result["error"] = "No authorization code received"
                    self._respond("Authorization failed: no code received. Close this tab.")
                    return

                result["code"] = code
                self._respond(
                    "Authorization successful! You can close this tab and return to the terminal."
                )

            def _respond(self, message: str):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;
                    text-align:center;padding:60px;background:#0d1b2e;color:#c9a84c">
                    <h1>TESS OAuth</h1><p>{message}</p></body></html>"""
                self.wfile.write(html.encode())

            def log_message(self, format, *args):
                pass  # Suppress server logs

        server = http.server.HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
        server.timeout = 120  # 2 minute timeout

        def serve():
            server_ready.set()
            server.handle_request()  # Handle exactly one request

        server_thread = threading.Thread(target=serve, daemon=True)
        server_thread.start()
        server_ready.wait()

        # Open browser
        print(f"Opening browser for TESS authorization...")
        print(f"  URL: {auth_url[:80]}...")
        print()
        print("If the browser doesn't open, visit this URL manually:")
        print(auth_url)
        print()
        print("Waiting for authorization (2 minute timeout)...")

        webbrowser.open(auth_url)

        # Wait for callback
        server_thread.join(timeout=130)

        if result["error"]:
            print(f"\nAuthorization failed: {result['error']}")
            return False

        if not result["code"]:
            print("\nAuthorization timed out. Try again.")
            return False

        # Exchange code for tokens
        print("Exchanging authorization code for tokens...")
        success = self._exchange_code(result["code"], code_verifier)

        if success:
            print(f"\nAuthorization successful! Tokens saved to {TOKEN_FILE}")
            return True
        else:
            print("\nToken exchange failed.")
            return False

    def _exchange_code(self, code: str, code_verifier: str) -> bool:
        """Exchange authorization code for access + refresh tokens."""
        try:
            resp = requests.post(
                f"{AUTH_BASE_URL}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code_verifier": code_verifier,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=30,
            )

            if not resp.ok:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                logger.error(f"Token exchange failed: {resp.status_code} — {data}")
                print(f"Token exchange failed: {resp.status_code}")
                if data.get("error_description"):
                    print(f"  {data['error_description']}")
                return False

            data = resp.json()

            # Validate required fields
            for field in ("access_token", "token_type", "expires_in"):
                if field not in data:
                    logger.error(f"Token response missing required field: {field}")
                    return False

            self._tokens = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "token_type": data["token_type"],
                "expires_in": data["expires_in"],
                "scope": data.get("scope", ""),
                "issued_at": time.time(),
            }
            self._save_tokens()
            return True

        except requests.RequestException as e:
            logger.error(f"Token exchange network error: {e}")
            print(f"Network error during token exchange: {e}")
            return False

    def refresh_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self._tokens or not self._tokens.get("refresh_token"):
            logger.error("No refresh token available — re-authorization required")
            return False

        try:
            resp = requests.post(
                f"{AUTH_BASE_URL}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._tokens["refresh_token"],
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=30,
            )

            if not resp.ok:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if data.get("error") == "invalid_grant":
                    logger.error("Refresh token expired — re-authorization required")
                    self._tokens = None
                    if TOKEN_FILE.exists():
                        TOKEN_FILE.unlink()
                    return False
                logger.error(f"Token refresh failed: {resp.status_code} — {data}")
                return False

            data = resp.json()
            self._tokens = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", self._tokens.get("refresh_token", "")),
                "token_type": data["token_type"],
                "expires_in": data["expires_in"],
                "scope": data.get("scope", self._tokens.get("scope", "")),
                "issued_at": time.time(),
            }
            self._save_tokens()
            logger.info("TESS access token refreshed successfully")
            return True

        except requests.RequestException as e:
            logger.error(f"Token refresh network error: {e}")
            return False

    def get_valid_token(self) -> str | None:
        """Return a valid access token, refreshing if needed.

        Returns None if not authenticated or refresh fails.
        """
        if not self._tokens:
            return None

        # Check expiry with 5-minute buffer
        issued_at = self._tokens.get("issued_at", 0)
        expires_in = self._tokens.get("expires_in", 0)
        expires_at = issued_at + expires_in
        buffer = 5 * 60  # 5 minutes

        if time.time() >= expires_at - buffer:
            if not self.refresh_token():
                return None

        return self._tokens.get("access_token")

    def revoke(self) -> bool:
        """Revoke tokens and delete stored credentials."""
        if self._tokens and self._tokens.get("access_token"):
            try:
                requests.post(
                    f"{AUTH_BASE_URL}/revoke",
                    data={
                        "token": self._tokens["access_token"],
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=15,
                )
            except Exception as e:
                logger.warning(f"Token revocation request failed: {e}")

        self._tokens = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            logger.info("TESS tokens revoked and deleted")
        return True


# ============================================================================
# TESSClient — Authenticated API Client
# ============================================================================

class TESSClient:
    """Authenticated client for the TESS API."""

    def __init__(self, auth: TESSAuth | None = None):
        self.auth = auth or TESSAuth()
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        })

    def _api_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_body: dict | None = None,
        retry_on_401: bool = True,
    ) -> dict[str, Any]:
        """Make an authenticated API request.

        Handles token injection, 401 auto-refresh retry, and JSON parsing.
        Returns the parsed JSON response or an error dict.
        """
        token = self.auth.get_valid_token()
        if not token:
            return {
                "error": "Not authenticated. Run: python3 thunderbird_tess.py --authorize",
                "type": "auth_required",
            }

        url = f"{API_BASE_URL}{endpoint}"
        self._session.headers["Authorization"] = f"Bearer {token}"

        try:
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                timeout=30,
            )

            # Handle 401 — try refresh and retry once
            if resp.status_code == 401 and retry_on_401:
                logger.info("TESS API 401 — attempting token refresh")
                if self.auth.refresh_token():
                    return self._api_request(
                        method, endpoint, params, json_body, retry_on_401=False
                    )
                return {
                    "error": "Authentication expired. Re-authorize with: python3 thunderbird_tess.py --authorize",
                    "type": "auth_expired",
                }

            # Parse response
            if resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
            else:
                data = {"raw_response": resp.text[:2000]}

            if not resp.ok:
                return {
                    "error": data.get("error", f"HTTP {resp.status_code}"),
                    "error_description": data.get("error_description", resp.reason),
                    "status_code": resp.status_code,
                    "type": "api_error",
                }

            return data

        except requests.RequestException as e:
            logger.error(f"TESS API request error: {e}")
            return {"error": str(e), "type": "network_error"}

    # ------------------------------------------------------------------
    # Agent / Profile
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        """Get the authenticated agent's profile."""
        return self._api_request("GET", "/agents/profile")

    # ------------------------------------------------------------------
    # Trips
    # ------------------------------------------------------------------

    def list_trips(self, status: str = "", limit: int = 50, offset: int = 0) -> dict:
        """List trips with optional status filter."""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._api_request("GET", "/trips", params=params)

    def get_trip(self, trip_id: str) -> dict:
        """Get a specific trip by ID."""
        return self._api_request("GET", f"/trips/{trip_id}")

    def create_trip(self, trip_data: dict) -> dict:
        """Create a new trip."""
        return self._api_request("POST", "/trips", json_body=trip_data)

    def update_trip(self, trip_id: str, trip_data: dict) -> dict:
        """Update an existing trip."""
        return self._api_request("PUT", f"/trips/{trip_id}", json_body=trip_data)

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------

    def list_bookings(self, limit: int = 50, offset: int = 0) -> dict:
        """List all bookings."""
        return self._api_request("GET", "/bookings", params={"limit": limit, "offset": offset})

    def get_booking(self, booking_id: str) -> dict:
        """Get a specific booking by ID."""
        return self._api_request("GET", f"/bookings/{booking_id}")

    def search_bookings(self, filters: dict) -> dict:
        """Search bookings with filters (status, client, date range, etc.)."""
        return self._api_request("POST", "/bookings/search", json_body=filters)

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def list_clients(self, limit: int = 50, offset: int = 0) -> dict:
        """List all clients."""
        return self._api_request("GET", "/clients", params={"limit": limit, "offset": offset})

    def get_client(self, client_id: str) -> dict:
        """Get a specific client by ID."""
        return self._api_request("GET", f"/clients/{client_id}")

    def update_client(self, client_id: str, client_data: dict) -> dict:
        """Update client information."""
        return self._api_request("PUT", f"/clients/{client_id}", json_body=client_data)

    # ------------------------------------------------------------------
    # Commissions
    # ------------------------------------------------------------------

    def get_commissions(self, limit: int = 50, offset: int = 0) -> dict:
        """Get commission records."""
        return self._api_request("GET", "/commissions", params={"limit": limit, "offset": offset})

    def get_commission_summary(self) -> dict:
        """Get commission summary (totals, pending, paid)."""
        return self._api_request("GET", "/commissions/summary")

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def list_documents(self, trip_id: str) -> dict:
        """List documents for a trip."""
        return self._api_request("GET", f"/trips/{trip_id}/documents")

    def upload_document(self, trip_id: str, file_path: str, doc_type: str = "general") -> dict:
        """Upload a document to a trip.

        Uses multipart form upload — bypasses the JSON content-type.
        """
        token = self.auth.get_valid_token()
        if not token:
            return {"error": "Not authenticated", "type": "auth_required"}

        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}", "type": "file_error"}

        url = f"{API_BASE_URL}/trips/{trip_id}/documents"
        try:
            with open(path, "rb") as f:
                resp = requests.post(
                    url,
                    files={"file": (path.name, f)},
                    data={"type": doc_type},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": USER_AGENT,
                    },
                    timeout=60,
                )

            if resp.ok:
                return resp.json()
            return {
                "error": f"Upload failed: HTTP {resp.status_code}",
                "type": "api_error",
                "status_code": resp.status_code,
            }
        except requests.RequestException as e:
            return {"error": str(e), "type": "network_error"}

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------

    def list_suppliers(self, limit: int = 50) -> dict:
        """List available suppliers."""
        return self._api_request("GET", "/suppliers", params={"limit": limit})

    # ------------------------------------------------------------------
    # Client Tasks (Portal)
    # ------------------------------------------------------------------

    def get_client_tasks(self, client_id: str) -> dict:
        """Get task completion status for a client."""
        return self._api_request("GET", f"/clients/{client_id}/tasks")


# ============================================================================
# Singleton instance (lazy)
# ============================================================================

_tess_client: TESSClient | None = None


def _get_client() -> TESSClient:
    """Get or create the singleton TESSClient."""
    global _tess_client
    if _tess_client is None:
        _tess_client = TESSClient()
    return _tess_client


# ============================================================================
# MCP Tool Registration
# ============================================================================

def register_tess_tools(mcp):
    """Register TESS API tools with the MCP server."""

    @mcp.tool(
        name="tess_authorize",
        annotations={"title": "TESS OAuth Authorization", "readOnlyHint": False},
    )
    async def tess_authorize() -> str:
        """Run the TESS OAuth 2.0 + PKCE authorization flow.

        Opens a browser for user consent. One-time setup — tokens are saved
        and auto-refreshed for subsequent calls.
        """
        try:
            auth = TESSAuth()
            if not auth.is_configured:
                return json.dumps({
                    "error": "TESS client credentials not configured",
                    "type": "config_error",
                    "help": "Set TESS_CLIENT_ID and TESS_CLIENT_SECRET env vars, "
                            "or create ~/Thunderbird/tess_config.json with client_id and client_secret",
                }, indent=2)

            success = auth.authorize()
            if success:
                # Reset singleton to pick up new tokens
                global _tess_client
                _tess_client = None
                return json.dumps({
                    "status": "success",
                    "message": "TESS authorization successful. Tokens saved.",
                    "token_file": str(TOKEN_FILE),
                }, indent=2)
            return json.dumps({
                "error": "Authorization failed or timed out",
                "type": "auth_error",
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "auth_error"}, indent=2)

    @mcp.tool(
        name="tess_list_trips",
        annotations={"title": "List TESS Trips", "readOnlyHint": True},
    )
    async def tess_list_trips(
        status: str = Field("", description="Filter by status (e.g. 'active', 'completed', 'cancelled'). Empty = all."),
        limit: int = Field(50, description="Max trips to return (1-100)"),
    ) -> str:
        """List trips from the TESS CRM."""
        client = _get_client()
        result = client.list_trips(status=status, limit=min(limit, 100))
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_get_trip",
        annotations={"title": "Get TESS Trip Details", "readOnlyHint": True},
    )
    async def tess_get_trip(
        trip_id: str = Field(..., description="TESS trip ID"),
    ) -> str:
        """Get detailed information for a specific TESS trip."""
        client = _get_client()
        result = client.get_trip(trip_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_get_booking",
        annotations={"title": "Get TESS Booking Details", "readOnlyHint": True},
    )
    async def tess_get_booking(
        booking_id: str = Field(..., description="TESS booking ID"),
    ) -> str:
        """Get detailed information for a specific TESS booking."""
        client = _get_client()
        result = client.get_booking(booking_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_search_bookings",
        annotations={"title": "Search TESS Bookings", "readOnlyHint": True},
    )
    async def tess_search_bookings(
        status: str = Field("", description="Booking status filter (e.g. 'confirmed', 'pending', 'cancelled')"),
        client_name: str = Field("", description="Client name to search for"),
        date_from: str = Field("", description="Start date filter (YYYY-MM-DD)"),
        date_to: str = Field("", description="End date filter (YYYY-MM-DD)"),
    ) -> str:
        """Search TESS bookings by status, client, or date range."""
        filters = {}
        if status:
            filters["status"] = status
        if client_name:
            filters["client_name"] = client_name
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to

        client = _get_client()
        result = client.search_bookings(filters)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_get_commissions",
        annotations={"title": "Get TESS Commission Summary", "readOnlyHint": True},
    )
    async def tess_get_commissions(
        summary: bool = Field(True, description="True for summary totals, False for individual records"),
        limit: int = Field(50, description="Max records if not summary (1-100)"),
    ) -> str:
        """Get commission data from TESS — summary totals or individual records."""
        client = _get_client()
        if summary:
            result = client.get_commission_summary()
        else:
            result = client.get_commissions(limit=min(limit, 100))
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_list_clients",
        annotations={"title": "List TESS Clients", "readOnlyHint": True},
    )
    async def tess_list_clients(
        limit: int = Field(50, description="Max clients to return (1-100)"),
    ) -> str:
        """List clients from the TESS CRM."""
        client = _get_client()
        result = client.list_clients(limit=min(limit, 100))
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_get_client",
        annotations={"title": "Get TESS Client Details", "readOnlyHint": True},
    )
    async def tess_get_client(
        client_id: str = Field(..., description="TESS client ID"),
    ) -> str:
        """Get detailed client information from TESS."""
        client = _get_client()
        result = client.get_client(client_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_upload_document",
        annotations={"title": "Upload Document to TESS Trip", "readOnlyHint": False},
    )
    async def tess_upload_document(
        trip_id: str = Field(..., description="TESS trip ID to attach document to"),
        file_path: str = Field(..., description="Absolute path to the file to upload"),
        doc_type: str = Field("general", description="Document type (e.g. 'general', 'invoice', 'itinerary', 'insurance')"),
    ) -> str:
        """Upload a document (PDF, image, etc.) to a TESS trip."""
        client = _get_client()
        result = client.upload_document(trip_id, file_path, doc_type)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_get_client_tasks",
        annotations={"title": "Get Client Portal Tasks", "readOnlyHint": True},
    )
    async def tess_get_client_tasks(
        client_id: str = Field(..., description="TESS client ID"),
    ) -> str:
        """Get task completion status for a client (portal tasks, document uploads, etc.)."""
        client = _get_client()
        result = client.get_client_tasks(client_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_test_connection",
        annotations={"title": "Test TESS API Connection", "readOnlyHint": True},
    )
    async def tess_test_connection() -> str:
        """Test the TESS API connection by fetching the agent profile."""
        client = _get_client()
        if not client.auth.is_configured:
            return json.dumps({
                "status": "not_configured",
                "message": "TESS client credentials not set. Set TESS_CLIENT_ID/TESS_CLIENT_SECRET or create tess_config.json.",
            }, indent=2)
        if not client.auth.is_authenticated:
            return json.dumps({
                "status": "not_authenticated",
                "message": "No TESS tokens found. Run tess_authorize first.",
            }, indent=2)

        result = client.get_profile()
        if "error" in result:
            return json.dumps({"status": "error", **result}, indent=2)
        return json.dumps({"status": "connected", "profile": result}, indent=2)

    logger.info("TESS API tools registered (11 tools)")


# ============================================================================
# CLI Interface
# ============================================================================

def _cli():
    """CLI for TESS setup and testing."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Dreams2Memories TESS API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 thunderbird_tess.py --authorize       # Run OAuth flow
  python3 thunderbird_tess.py --test            # Test connection
  python3 thunderbird_tess.py --bookings        # List bookings
  python3 thunderbird_tess.py --commissions     # Commission summary
  python3 thunderbird_tess.py --clients         # List clients
  python3 thunderbird_tess.py --trips           # List trips
  python3 thunderbird_tess.py --revoke          # Revoke tokens
""",
    )
    parser.add_argument("--authorize", action="store_true", help="Run OAuth 2.0 + PKCE authorization flow")
    parser.add_argument("--test", action="store_true", help="Test API connection (fetch agent profile)")
    parser.add_argument("--bookings", action="store_true", help="List bookings")
    parser.add_argument("--commissions", action="store_true", help="Get commission summary")
    parser.add_argument("--clients", action="store_true", help="List clients")
    parser.add_argument("--trips", action="store_true", help="List trips")
    parser.add_argument("--revoke", action="store_true", help="Revoke tokens and delete credentials")

    args = parser.parse_args()

    if args.authorize:
        auth = TESSAuth()
        auth.authorize()
        return

    if args.revoke:
        auth = TESSAuth()
        auth.revoke()
        print("TESS tokens revoked.")
        return

    client = TESSClient()

    if not client.auth.is_configured:
        print("TESS not configured. Set TESS_CLIENT_ID/TESS_CLIENT_SECRET or create tess_config.json.")
        print("Run: python3 thunderbird_tess.py --authorize")
        sys.exit(1)

    if args.test:
        result = client.get_profile()
        print(json.dumps(result, indent=2, default=str))
        return

    if args.bookings:
        result = client.list_bookings()
        print(json.dumps(result, indent=2, default=str))
        return

    if args.commissions:
        result = client.get_commission_summary()
        print(json.dumps(result, indent=2, default=str))
        return

    if args.clients:
        result = client.list_clients()
        print(json.dumps(result, indent=2, default=str))
        return

    if args.trips:
        result = client.list_trips()
        print(json.dumps(result, indent=2, default=str))
        return

    parser.print_help()


if __name__ == "__main__":
    _cli()
