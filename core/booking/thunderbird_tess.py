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

AUTH_BASE_URL = "https://crm.myagentgenie.com/api"
API_BASE_URL = "https://crm.myagentgenie.com/api/api/"
DEFAULT_CLIENT_ID = "ngAuthApp"

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
                # Normalize issued_at to numeric Unix timestamp.
                # The OAuth ".issued" field is an HTTP-date string; the rest of
                # this module expects a number for expiry math.
                if self._tokens:
                    issued = self._tokens.get("issued_at")
                    if not isinstance(issued, (int, float)):
                        if "expires_at" in self._tokens and "expires_in" in self._tokens:
                            self._tokens["issued_at"] = (
                                self._tokens["expires_at"] - self._tokens["expires_in"]
                            )
                        else:
                            self._tokens["issued_at"] = time.time()
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
        """True if usable token is on disk OR full client credentials are available.

        TESS uses two paths now: (a) JWT bearer tokens extracted from browser
        localStorage (no client_secret needed), (b) full OAuth PKCE with
        client_id + client_secret. Either qualifies as configured.
        """
        if self._tokens and "refresh_token" in self._tokens:
            return True
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
            # The live token is minted by the public Angular SPA client
            # (ngAuthApp): a PKCE client that takes NO client_secret. Its
            # refresh_token must be redeemed against that same client. A
            # client_id that is not a real OAuth client (e.g. an email address
            # left in tess_config.json) or an accompanying secret makes the
            # token endpoint reject the grant with invalid_client — which the
            # Playwright credential fallback then silently absorbs every ~90min.
            # Guard against both so a misconfigured tess_config.json can't
            # re-poison the refresh path. (Root-caused 2026-07-16, Block 2.)
            effective_client_id = self.client_id or self._tokens.get("client_id") or DEFAULT_CLIENT_ID
            if not effective_client_id or "@" in effective_client_id:
                effective_client_id = DEFAULT_CLIENT_ID

            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": self._tokens["refresh_token"],
                "client_id": effective_client_id,
            }
            # A secret is valid ONLY for a genuine confidential OAuth client —
            # never for the public ngAuthApp SPA client. Sending one to the
            # public client is itself rejected (invalid_grant), so omit it.
            if self.client_secret and effective_client_id != DEFAULT_CLIENT_ID:
                refresh_data["client_secret"] = self.client_secret

            resp = requests.post(
                f"{AUTH_BASE_URL}/token",
                data=refresh_data,
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
            now = time.time()
            self._tokens = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", self._tokens.get("refresh_token", "")),
                "token_type": data["token_type"],
                "expires_in": data["expires_in"],
                "expires_at": int(now) + int(data["expires_in"]),
                "scope": data.get("scope", self._tokens.get("scope", "")),
                "issued_at": now,
                "userID": data.get("userID", self._tokens.get("userID", "")),
                "client_id": data.get("as:client_id", self._tokens.get("client_id", DEFAULT_CLIENT_ID)),
                "auth_type": "jwt_bearer",
                "api_base": API_BASE_URL,
                "token_endpoint": f"{AUTH_BASE_URL}/token",
                "company_id": self._tokens.get("company_id", ""),
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
            "X-Requested-With": "XMLHttpRequest",
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
    # Generic action caller — the catch-all for the 344 ?action=X endpoints
    # ------------------------------------------------------------------

    def call_action(
        self,
        resource: str,
        action: str | None = None,
        method: str = "POST",
        body: dict | None = None,
        **params,
    ) -> dict:
        """Invoke any TESS action endpoint.

        myAgentGenie's AngularJS frontend uses URL pattern
        `api/{Resource}/:id/:action`. When `:action` is set but `:id` is empty,
        Angular emits the action as a query param (?action=Name). When both
        are empty, the call collapses to bare `api/{Resource}`.

        Most actions are GET (data fetches) or POST (mutations). PUT is
        declared by some factories but the server returns 405 — use POST.

        Examples:
            client.call_action("Trip", "TripAccessGetListForDashboard",
                               method="GET", pageNumber=1, pageSize=10)
            client.call_action("Trip", "PostTripNote",
                               tripID=123, noteContent="Confirmed dates")
            client.call_action("Booking", "GetUnclaimedBookings", method="GET")

        Full action catalog: output/tess_map/08_action_catalog.md (344 actions
        across 30 resources).
        """
        path = resource
        clean_params = {k: v for k, v in params.items() if v not in (None, "")}
        if action:
            clean_params = {"action": action, **clean_params}
        return self._api_request(method, path, params=clean_params, json_body=body)

    def add_note(self, target: str, target_id: str | int, note: str) -> dict:
        """Add a note to a Trip, Booking, or Client.

        target: 'Trip' | 'Booking' | 'Client' (the resource name).
        Body MUST be null per the JS pattern; content goes in query params.
        """
        target = target.capitalize()
        action_map = {
            "Trip": ("PostTripNote", "tripID", "noteContent"),
            "Booking": ("PostBookingNote", "bookingID", "noteContent"),
            "Client": ("PostClientNote", "clientID", "noteContent"),
        }
        if target not in action_map:
            return {"error": f"Unsupported note target '{target}'", "type": "validation_error"}
        action, id_param, content_param = action_map[target]
        return self.call_action(
            target, action, body=None, **{id_param: target_id, content_param: note}
        )

    # ------------------------------------------------------------------
    # Agent / Profile (myAgentGenie)
    # ------------------------------------------------------------------
    #
    # NOTE: Endpoints below use myAgentGenie's actual API surface, discovered
    # by reverse-engineering the AngularJS bundle on 2026-05-05. URL pattern
    # `api/{Resource}/:id/:action` collapses to bare `api/{Resource}` when
    # both id and action are unset. List endpoints REQUIRE pageNumber +
    # pageSize query params — without them the server returns 405. Responses
    # are paginated as `{Items, CountFiltered, CountUnfiltered, PageNumber, PageSize}`.

    def get_profile(self) -> dict:
        """Get the authenticated user's TESS profile (full record + Company + Permissions)."""
        user_id = (self.auth._tokens or {}).get("userID", "")
        if not user_id:
            return {"error": "No userID in token; re-extract from localStorage", "type": "auth_required"}
        return self._api_request("GET", f"User?userID={user_id}")

    def get_company(self, company_id: str | int = "") -> dict:
        """Get a company record. Defaults to the agent's own company."""
        cid = company_id or (self.auth._tokens or {}).get("company_id") or ""
        return self._api_request("GET", f"Company/{cid}")

    # ------------------------------------------------------------------
    # Trips
    # ------------------------------------------------------------------

    def list_trips(
        self,
        page_number: int = 1,
        page_size: int = 50,
        sort_by: str = "CreatedDateTimeUTC",
        sort_ascending: bool = False,
        **filters,
    ) -> dict:
        """List trips. Returns paginated {Items, CountFiltered, CountUnfiltered}.

        Optional filters: tripDescription, tripMainTypeIds, tripTypeID,
        tripCarrierTypeID, supplierID, userID, tripStatusIDs, startDate,
        startDateEnd, endDate, endDateEnd, clientID.
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "sortBy": sort_by,
            "sortAscending": str(sort_ascending).lower(),
            **{k: v for k, v in filters.items() if v not in (None, "")},
        }
        return self._api_request("GET", "Trip", params=params)

    def get_trip(self, trip_id: str | int) -> dict:
        """Get a specific trip by ID."""
        return self._api_request("GET", f"Trip/{trip_id}")

    def update_trip(self, trip_id: str | int, **action_params) -> dict:
        """Update a trip via POST + action.

        NOTE: Direct PUT /api/Trip/{id} returns 405 despite what the AngularJS
        factory declares. Trip mutations happen via POST with an action override.
        Pass the action name as `action="..."` plus any extra query params.
        Example: client.update_trip(123, action="ReservationUpdate", parentTripID=99)
        """
        return self.call_action("Trip", trip_id=trip_id, **action_params)

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------

    def list_bookings(
        self,
        page_number: int = 1,
        page_size: int = 50,
        sort_by: str = "BookingDate",
        sort_ascending: bool = False,
        **filters,
    ) -> dict:
        """List bookings. Returns paginated {Items, CountFiltered, CountUnfiltered}.

        Each Item carries a full Commission object — this is the financial pulse.
        Optional filters: bookingNumber, bookingCategoryTypeID, tripDescription,
        tourOperatorID, userID, bookingStatus, tripID, tripGroupNumber,
        bookingDateStart, bookingDateEnd, startDate, startDateEnd,
        endDate, endDateEnd, paymentDateStart, paymentDateEnd, personalTravel.
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "sortBy": sort_by,
            "sortAscending": str(sort_ascending).lower(),
            **{k: v for k, v in filters.items() if v not in (None, "")},
        }
        return self._api_request("GET", "Booking", params=params)

    def get_booking(self, booking_id: str | int) -> dict:
        """Get a specific booking by ID."""
        return self._api_request("GET", f"Booking/{booking_id}")

    def search_bookings(self, filters: dict | None = None, **kwargs) -> dict:
        """Compatibility shim — delegates to list_bookings with filters."""
        return self.list_bookings(**(filters or {}), **kwargs)

    def update_booking(self, booking_id: str | int, **action_params) -> dict:
        """Update a booking via POST + action.

        NOTE: Direct PUT /api/Booking/{id} returns 405. Booking mutations use
        POST with an action override. Common actions:
          - BookingPaymentUpdate
          - BookingStatusUpdate
        """
        return self.call_action("Booking", booking_id=booking_id, **action_params)

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def list_clients(
        self,
        page_number: int = 1,
        page_size: int = 50,
        **filters,
    ) -> dict:
        """List clients. Returns paginated {Items, CountFiltered, CountUnfiltered}.

        Optional filters: clientFirstName, clientLastName, userID, marketable,
        telephoneNumber, emailAddress, contactReferralGroupID, minBirthDate,
        maxBirthDate, minAnniversaryDate, maxAnniversaryDate, isMarketing.
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            **{k: v for k, v in filters.items() if v not in (None, "")},
        }
        return self._api_request("GET", "Client", params=params)

    def get_client(self, client_id: str | int) -> dict:
        """Get a specific client by ID."""
        return self._api_request("GET", f"Client/{client_id}")

    def update_client(self, client_id: str | int, **action_params) -> dict:
        """Update a client via POST + action.

        NOTE: Direct PUT /api/Client/{id} is unverified — the factory declares
        PUT but live tests on Trip/Booking PUTs returned 405. Use the action
        pattern to be safe; extend to PUT if a specific action is verified.
        """
        return self.call_action("Client", client_id=client_id, **action_params)

    # ------------------------------------------------------------------
    # Commissions — checks received and paid
    # ------------------------------------------------------------------
    #
    # In TESS terms:
    #   - CheckReceived = D2M received commission from a tour operator/supplier.
    #     This is what Commander cares about — money in.
    #   - CheckPaid = D2M paid out a sub-agent (D2M is org level 2, no sub-agents,
    #     so this list is normally empty).

    def list_checks_received(
        self,
        page_number: int = 1,
        page_size: int = 50,
        **filters,
    ) -> dict:
        """List commission checks received. Returns paginated result.

        Optional filters: checkNumber, tourOperatorID, checkStatusID.
        Each Item includes Commission breakdown (Received, Earned, Paid, Due).
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            **{k: v for k, v in filters.items() if v not in (None, "")},
        }
        return self._api_request("GET", "CheckReceived", params=params)

    def get_check_received(self, check_id: str | int) -> dict:
        """Get a single CheckReceived record by ID."""
        return self._api_request("GET", f"CheckReceived/{check_id}")

    def list_checks_paid(
        self,
        page_number: int = 1,
        page_size: int = 50,
        **filters,
    ) -> dict:
        """List commission checks paid out (sub-agent payments).

        Optional filters: checkNumber, checkGroupNumber, checkStatusID.
        D2M typically has none of these (org level 2, no downline).
        """
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            **{k: v for k, v in filters.items() if v not in (None, "")},
        }
        return self._api_request("GET", "CheckPaid", params=params)

    def get_commissions(self, limit: int = 50, offset: int = 0) -> dict:
        """Compatibility shim — returns CheckReceived list (most relevant for D2M).

        For full financial pulse, prefer list_checks_received() directly.
        """
        page = (offset // max(limit, 1)) + 1
        return self.list_checks_received(page_number=page, page_size=limit)

    def get_commission_summary(self) -> dict:
        """Aggregate commission rollup from all CheckReceived records.

        myAgentGenie has no dedicated summary endpoint — we aggregate locally
        from the Commission object on each check.
        """
        result = self.list_checks_received(page_size=200)
        if "error" in result:
            return result
        items = result.get("Items", [])
        totals = {
            "checks_received_count": result.get("CountUnfiltered", len(items)),
            "total_received": 0.0,
            "total_earned": 0.0,
            "total_paid": 0.0,
            "total_due": 0.0,
            "booking_count": 0,
        }
        for it in items:
            c = it.get("Commission") or {}
            totals["total_received"] += c.get("Received", 0) or 0
            totals["total_earned"] += c.get("Earned", 0) or 0
            totals["total_paid"] += c.get("Paid", 0) or 0
            totals["total_due"] += c.get("Due", 0) or 0
            totals["booking_count"] += c.get("BookingCount", 0) or 0
        return totals

    # ------------------------------------------------------------------
    # Reports — Telerik PDF/Excel binaries (single-check or filtered exports)
    # ------------------------------------------------------------------

    def download_check_received_report(
        self, check_id: str | int, fmt: str = "PDF"
    ) -> bytes | dict:
        """Download a per-check CheckReceived Telerik report.

        Returns raw bytes on success; error dict on failure.
        Format: 'PDF' or 'Excel'.
        """
        return self._download_report(
            "Reporting/CheckReceived", {"checkID": check_id, "format": fmt}
        )

    def download_check_paid_report(
        self, check_id: str | int, fmt: str = "PDF"
    ) -> bytes | dict:
        """Download a per-check CheckPaid Telerik report."""
        return self._download_report(
            "Reporting/CheckPaid", {"checkID": check_id, "format": fmt}
        )

    def download_client_export(self) -> bytes | dict:
        """Download all-clients XLSX export. Prefer list_clients() for JSON."""
        return self._download_report("Export/ClientExport", {})

    def _download_report(self, path: str, params: dict) -> bytes | dict:
        """Internal: GET a Telerik/Export report, return raw bytes."""
        token = self.auth.get_valid_token()
        if not token:
            return {"error": "Not authenticated", "type": "auth_required"}
        url = f"{API_BASE_URL}{path}"
        try:
            resp = requests.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
                timeout=60,
            )
            if resp.ok:
                return resp.content
            return {
                "error": f"Report download failed: HTTP {resp.status_code}",
                "type": "api_error",
                "status_code": resp.status_code,
                "preview": resp.text[:300],
            }
        except requests.RequestException as e:
            return {"error": str(e), "type": "network_error"}

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
    # Notes
    # ------------------------------------------------------------------

    def add_note(self, entity_type: str, entity_id: str, note_text: str) -> dict:
        """Add a note to an entity (trip, booking, or client).

        Args:
            entity_type: One of 'trips', 'bookings', or 'clients'.
            entity_id: The entity's TESS ID.
            note_text: The note content.
        """
        valid_types = ("trips", "bookings", "clients")
        if entity_type not in valid_types:
            return {
                "error": f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(valid_types)}",
                "type": "validation_error",
            }
        return self._api_request(
            "POST",
            f"/{entity_type}/{entity_id}/notes",
            json_body={"text": note_text},
        )

    # ------------------------------------------------------------------
    # Entity Documents (generic)
    # ------------------------------------------------------------------

    def upload_entity_document(
        self,
        entity_type: str,
        entity_id: str,
        file_path: str,
        doc_type: str = "general",
    ) -> dict:
        """Upload a document to any entity (trip, booking, or client).

        Uses multipart form upload — bypasses the JSON content-type.

        Args:
            entity_type: One of 'trips', 'bookings', or 'clients'.
            entity_id: The entity's TESS ID.
            file_path: Absolute path to the file to upload.
            doc_type: Document category (e.g. 'general', 'invoice', 'itinerary',
                      'insurance', 'passport', 'visa').
        """
        valid_types = ("trips", "bookings", "clients")
        if entity_type not in valid_types:
            return {
                "error": f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(valid_types)}",
                "type": "validation_error",
            }

        token = self.auth.get_valid_token()
        if not token:
            return {"error": "Not authenticated", "type": "auth_required"}

        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}", "type": "file_error"}

        url = f"{API_BASE_URL}/{entity_type}/{entity_id}/documents"
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

            if resp.status_code == 401:
                # Try refresh and retry once
                logger.info("TESS document upload 401 — attempting token refresh")
                if self.auth.refresh_token():
                    return self.upload_entity_document(
                        entity_type, entity_id, file_path, doc_type
                    )
                return {
                    "error": "Authentication expired. Re-authorize.",
                    "type": "auth_expired",
                }

            if resp.ok:
                if resp.headers.get("content-type", "").startswith("application/json"):
                    return resp.json()
                return {"status": "uploaded", "raw_response": resp.text[:2000]}
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

    # ------------------------------------------------------------------
    # Write Tools
    # ------------------------------------------------------------------

    @mcp.tool(
        name="tess_create_booking",
        annotations={"title": "Create TESS Booking", "readOnlyHint": False},
    )
    async def tess_create_booking(
        trip_id: str = Field(..., description="TESS trip ID to attach the booking to"),
        supplier: str = Field("", description="Supplier/vendor name (e.g. 'Silversea', 'Marriott')"),
        confirmation_number: str = Field("", description="Supplier confirmation/PNR number"),
        booking_type: str = Field("", description="Booking type (e.g. 'cruise', 'hotel', 'air', 'transfer', 'excursion')"),
        start_date: str = Field("", description="Start date (YYYY-MM-DD)"),
        end_date: str = Field("", description="End date (YYYY-MM-DD)"),
        total_cost: float = Field(0, description="Total cost in USD"),
        notes: str = Field("", description="Additional notes for the booking"),
        extra_fields: str = Field("{}", description="JSON string of additional booking fields"),
    ) -> str:
        """Create a new booking in TESS under a specific trip.

        Provide the trip_id and booking details. Use extra_fields (JSON string)
        for any fields not covered by the named parameters.
        """
        booking_data: dict[str, Any] = {}
        if supplier:
            booking_data["supplier"] = supplier
        if confirmation_number:
            booking_data["confirmation_number"] = confirmation_number
        if booking_type:
            booking_data["booking_type"] = booking_type
        if start_date:
            booking_data["start_date"] = start_date
        if end_date:
            booking_data["end_date"] = end_date
        if total_cost:
            booking_data["total_cost"] = total_cost
        if notes:
            booking_data["notes"] = notes

        # Merge any extra fields
        try:
            extra = json.loads(extra_fields)
            if isinstance(extra, dict):
                booking_data.update(extra)
        except json.JSONDecodeError:
            pass

        client = _get_client()
        result = client.create_booking(trip_id, booking_data)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_update_booking",
        annotations={"title": "Update TESS Booking", "readOnlyHint": False},
    )
    async def tess_update_booking(
        booking_id: str = Field(..., description="TESS booking ID to update"),
        status: str = Field("", description="New booking status (e.g. 'confirmed', 'cancelled', 'pending')"),
        confirmation_number: str = Field("", description="Updated confirmation/PNR number"),
        start_date: str = Field("", description="Updated start date (YYYY-MM-DD)"),
        end_date: str = Field("", description="Updated end date (YYYY-MM-DD)"),
        total_cost: float = Field(0, description="Updated total cost in USD"),
        notes: str = Field("", description="Updated notes"),
        extra_fields: str = Field("{}", description="JSON string of additional fields to update"),
    ) -> str:
        """Update an existing TESS booking.

        Only provided (non-empty) fields are included in the update payload.
        Use extra_fields (JSON string) for fields not covered by named parameters.
        """
        updates: dict[str, Any] = {}
        if status:
            updates["status"] = status
        if confirmation_number:
            updates["confirmation_number"] = confirmation_number
        if start_date:
            updates["start_date"] = start_date
        if end_date:
            updates["end_date"] = end_date
        if total_cost:
            updates["total_cost"] = total_cost
        if notes:
            updates["notes"] = notes

        try:
            extra = json.loads(extra_fields)
            if isinstance(extra, dict):
                updates.update(extra)
        except json.JSONDecodeError:
            pass

        if not updates:
            return json.dumps({"error": "No update fields provided", "type": "validation_error"}, indent=2)

        client = _get_client()
        result = client.update_booking(booking_id, **updates)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_create_client",
        annotations={"title": "Create TESS Client", "readOnlyHint": False},
    )
    async def tess_create_client(
        first_name: str = Field(..., description="Client first name"),
        last_name: str = Field(..., description="Client last name"),
        email: str = Field("", description="Client email address"),
        phone: str = Field("", description="Client phone number"),
        date_of_birth: str = Field("", description="Date of birth (YYYY-MM-DD)"),
        address: str = Field("", description="Mailing address"),
        notes: str = Field("", description="Agent notes about the client"),
        extra_fields: str = Field("{}", description="JSON string of additional client fields (passport, preferences, etc.)"),
    ) -> str:
        """Create a new client in TESS CRM.

        Provide at minimum first_name and last_name. Use extra_fields (JSON string)
        for passport details, travel preferences, loyalty programs, etc.
        """
        client_data: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
        }
        if email:
            client_data["email"] = email
        if phone:
            client_data["phone"] = phone
        if date_of_birth:
            client_data["date_of_birth"] = date_of_birth
        if address:
            client_data["address"] = address
        if notes:
            client_data["notes"] = notes

        try:
            extra = json.loads(extra_fields)
            if isinstance(extra, dict):
                client_data.update(extra)
        except json.JSONDecodeError:
            pass

        client = _get_client()
        result = client.create_client(client_data)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_update_client",
        annotations={"title": "Update TESS Client", "readOnlyHint": False},
    )
    async def tess_update_client(
        client_id: str = Field(..., description="TESS client ID to update"),
        first_name: str = Field("", description="Updated first name"),
        last_name: str = Field("", description="Updated last name"),
        email: str = Field("", description="Updated email address"),
        phone: str = Field("", description="Updated phone number"),
        notes: str = Field("", description="Updated agent notes"),
        extra_fields: str = Field("{}", description="JSON string of additional fields to update"),
    ) -> str:
        """Update an existing client in TESS CRM.

        Only provided (non-empty) fields are included in the update payload.
        """
        updates: dict[str, Any] = {}
        if first_name:
            updates["first_name"] = first_name
        if last_name:
            updates["last_name"] = last_name
        if email:
            updates["email"] = email
        if phone:
            updates["phone"] = phone
        if notes:
            updates["notes"] = notes

        try:
            extra = json.loads(extra_fields)
            if isinstance(extra, dict):
                updates.update(extra)
        except json.JSONDecodeError:
            pass

        if not updates:
            return json.dumps({"error": "No update fields provided", "type": "validation_error"}, indent=2)

        client = _get_client()
        result = client.update_client(client_id, updates)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_add_note",
        annotations={"title": "Add Note to TESS Entity", "readOnlyHint": False},
    )
    async def tess_add_note(
        entity_type: str = Field(..., description="Entity type: 'trips', 'bookings', or 'clients'"),
        entity_id: str = Field(..., description="TESS entity ID"),
        note_text: str = Field(..., description="Note content to add"),
    ) -> str:
        """Add a note to a TESS trip, booking, or client.

        Notes are appended to the entity's note history — useful for tracking
        communications, special requests, internal memos, etc.
        """
        client = _get_client()
        result = client.add_note(entity_type, entity_id, note_text)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="tess_upload_entity_document",
        annotations={"title": "Upload Document to TESS Entity", "readOnlyHint": False},
    )
    async def tess_upload_entity_document(
        entity_type: str = Field(..., description="Entity type: 'trips', 'bookings', or 'clients'"),
        entity_id: str = Field(..., description="TESS entity ID"),
        file_path: str = Field(..., description="Absolute path to the file to upload"),
        doc_type: str = Field("general", description="Document type (e.g. 'general', 'invoice', 'itinerary', 'insurance', 'passport', 'visa')"),
    ) -> str:
        """Upload a document to any TESS entity (trip, booking, or client).

        Supports PDF, images, and other file types. Documents are attached to the
        entity record for reference and client portal access.
        """
        client = _get_client()
        result = client.upload_entity_document(entity_type, entity_id, file_path, doc_type)
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

    @mcp.tool(
        name="tess_fpd_sweep",
        annotations={"title": "TESS Final Payment Date Sweep", "readOnlyHint": True},
    )
    async def tess_fpd_sweep(
        days_ahead: int = Field(60, description="Look-ahead window in days (bookings with FPD within this many days)"),
        include_no_fpd: bool = Field(False, description="Include bookings with no FinalPaymentDate set"),
    ) -> str:
        """Sweep all TESS bookings and return final payment date (FPD) status.

        Returns all active bookings with FPD alerts:
          RED    — FPD within 30 days (urgent)
          YELLOW — FPD 31-45 days out
          ORANGE — FPD 46-60 days out
          GREEN  — FPD > 60 days out
          PAST   — FPD already passed (overdue)

        Used by Harlan (A9) for commission/payment tracking and by Hale's
        proactive dossier sweep (SO-PIPELINE-INTEGRITY-20260528, Rule 4 & 5).
        """
        from datetime import date, datetime, timezone

        client = _get_client()
        raw = client.search_bookings({})

        items = raw.get("Items", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return json.dumps({"error": "Unexpected TESS response shape", "raw_keys": list(raw.keys()) if isinstance(raw, dict) else "not_dict"}, indent=2)

        today = date.today()
        alerts: list[dict] = []
        no_fpd_bookings: list[dict] = []
        skipped_cancelled = 0

        for b in items:
            bs = b.get("BookingStatus") or {}
            status_name = (bs.get("StatusName") if isinstance(bs, dict) else str(bs)).lower()
            if status_name in ("cancelled", "canceled", "void"):
                skipped_cancelled += 1
                continue

            fpd_raw = b.get("FinalPaymentDate")
            if not fpd_raw:
                if include_no_fpd:
                    no_fpd_bookings.append({
                        "booking_id": b.get("BookingID"),
                        "booking_number": b.get("BookingNumber") or b.get("Number"),
                        "trip_description": b.get("TripDescription"),
                        "tour_operator": b.get("TourOperator"),
                        "status": bs.get("StatusName") if isinstance(bs, dict) else str(bs),
                        "start_date": b.get("StartDate"),
                        "package_price": b.get("PackagePrice"),
                    })
                continue

            # Parse FPD — TESS returns ISO 8601 strings
            try:
                if "T" in str(fpd_raw):
                    fpd_dt = datetime.fromisoformat(str(fpd_raw).replace("Z", "+00:00"))
                    fpd = fpd_dt.date()
                else:
                    fpd = date.fromisoformat(str(fpd_raw)[:10])
            except (ValueError, TypeError):
                fpd = None

            if fpd is None:
                continue

            days_until = (fpd - today).days

            if days_until < 0:
                alert_level = "PAST"
            elif days_until <= 30:
                alert_level = "RED"
            elif days_until <= 45:
                alert_level = "YELLOW"
            elif days_until <= 60:
                alert_level = "ORANGE"
            else:
                alert_level = "GREEN"

            if alert_level == "GREEN" and days_until > days_ahead:
                continue

            commission = b.get("Commission") or {}
            alerts.append({
                "alert_level": alert_level,
                "days_until_fpd": days_until,
                "fpd": str(fpd),
                "booking_id": b.get("BookingID"),
                "booking_number": b.get("BookingNumber") or b.get("Number"),
                "trip_description": b.get("TripDescription"),
                "tour_operator": b.get("TourOperator"),
                "booking_status": bs.get("StatusName") if isinstance(bs, dict) else str(bs),
                "start_date": b.get("StartDate"),
                "end_date": b.get("EndDate"),
                "package_price": b.get("PackagePrice"),
                "commission_expected": (commission.get("AgencyCommission") or commission.get("CommissionAmount")) if isinstance(commission, dict) else None,
            })

        alerts.sort(key=lambda x: x["days_until_fpd"])

        summary = {
            "sweep_date": str(today),
            "days_ahead_window": days_ahead,
            "total_bookings_checked": len(items),
            "cancelled_skipped": skipped_cancelled,
            "alerts_found": len(alerts),
            "by_level": {
                "PAST": sum(1 for a in alerts if a["alert_level"] == "PAST"),
                "RED": sum(1 for a in alerts if a["alert_level"] == "RED"),
                "YELLOW": sum(1 for a in alerts if a["alert_level"] == "YELLOW"),
                "ORANGE": sum(1 for a in alerts if a["alert_level"] == "ORANGE"),
                "GREEN": sum(1 for a in alerts if a["alert_level"] == "GREEN"),
            },
            "alerts": alerts,
        }
        if include_no_fpd and no_fpd_bookings:
            summary["no_fpd_bookings"] = no_fpd_bookings

        return json.dumps(summary, indent=2, default=str)

    logger.info("TESS API tools registered (18 tools)")


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
  python3 thunderbird_tess.py --authorize       # Run OAuth flow (needs local browser)
  python3 thunderbird_tess.py --inject-token '{"token":"eyJ...","refreshToken":"..."}' # Inject from browser localStorage
  python3 thunderbird_tess.py --keepalive       # Proactively refresh (called by systemd timer)
  python3 thunderbird_tess.py --test            # Test connection
  python3 thunderbird_tess.py --bookings        # List bookings
  python3 thunderbird_tess.py --commissions     # Commission summary
  python3 thunderbird_tess.py --clients         # List clients
  python3 thunderbird_tess.py --trips           # List trips
  python3 thunderbird_tess.py --revoke          # Revoke tokens

Token injection (from Chromebook or any remote browser):
  1. Log in at https://crm.myagentgenie.com
  2. DevTools (F12) → Application → Local Storage → crm.myagentgenie.com
  3. Copy value of "authenticationData"
  4. python3 thunderbird_tess.py --inject-token '<paste here>'
""",
    )
    parser.add_argument("--authorize", action="store_true", help="Run OAuth 2.0 + PKCE authorization flow")
    parser.add_argument(
        "--inject-token",
        metavar="JSON",
        help='Inject token from browser localStorage. Pass the raw JSON value of the '
             '"authenticationData" key, e.g.: \'{"token":"eyJ...","refreshToken":"abc..."}\''
    )
    parser.add_argument("--keepalive", action="store_true",
                        help="Proactively refresh token if within 30 min of expiry — for use by systemd timer")
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

    if args.inject_token:
        _inject_token_from_localstorage(args.inject_token)
        return

    if args.keepalive:
        _keepalive()
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


def _inject_token_from_localstorage(raw_json: str) -> None:
    """Write tess_token.json from the browser localStorage authenticationData blob.

    Usage:
        python3 thunderbird_tess.py --inject-token '{"token":"eyJ...","refreshToken":"..."}'

    Gets the value from DevTools → Application → Local Storage →
    https://crm.myagentgenie.com → authenticationData.
    """
    import base64

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse JSON — {e}")
        print("Wrap the value in single quotes and paste the full JSON object.")
        sys.exit(1)

    jwt_token = data.get("token") or data.get("access_token")
    refresh_tok = data.get("refreshToken") or data.get("refresh_token")

    if not jwt_token:
        print("ERROR: No 'token' or 'access_token' field found in JSON.")
        sys.exit(1)

    # Decode JWT payload (no signature verification — we trust the browser source)
    try:
        payload_b64 = jwt_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        print(f"ERROR: Could not decode JWT payload — {e}")
        sys.exit(1)

    nbf = payload.get("nbf", int(time.time()))
    exp = payload.get("exp", nbf + 7200)
    user_id = str(payload.get("UserID") or payload.get("userID") or "")
    company_id = str(payload.get("CompanyID") or payload.get("companyID") or "")

    token_data = {
        "access_token": jwt_token,
        "refresh_token": refresh_tok or "",
        "token_type": "Bearer",
        "userID": user_id,
        "company_id": company_id,
        "issued_at": nbf,
        "expires_in": exp - nbf,
        "expires_at": exp,
        "source": "localStorage_inject",
        "injected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")

    remaining = int(exp - time.time())
    print(f"✅ Token injected — UserID={user_id} CompanyID={company_id}")
    print(f"   Expires: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(exp))} "
          f"({remaining // 60}m {remaining % 60}s remaining)")

    # Verify immediately
    client = TESSClient()
    profile = client.get_profile()
    if "error" in profile:
        print(f"⚠️  Connection test failed: {profile['error']}")
    else:
        print(f"✅ Connection verified — API responding")


def _keepalive() -> None:
    """Proactively refresh TESS token if within 30 minutes of expiry.

    Called by systemd timer every 90 minutes. Keeps the refresh chain alive
    so the token never lapses between sessions.
    """
    auth = TESSAuth()
    if not auth._tokens:
        print("TESS keepalive: no token on disk — nothing to refresh")
        sys.exit(0)

    expires_at = auth._tokens.get("expires_at", 0)
    remaining = expires_at - time.time()

    if remaining > 30 * 60:
        print(f"TESS keepalive: token healthy ({int(remaining // 60)}m remaining) — no refresh needed")
        sys.exit(0)

    print(f"TESS keepalive: token expires in {int(remaining // 60)}m — refreshing now")
    ok = auth.refresh_token()
    if ok:
        new_exp = auth._tokens.get("expires_at", 0)
        print(f"✅ Token refreshed — new expiry {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(new_exp))}")
    else:
        print("❌ Refresh failed — manual re-injection required")
        print("   DevTools → Application → Local Storage → crm.myagentgenie.com → authenticationData")
        print("   Then: python3 thunderbird_tess.py --inject-token '<paste JSON>'")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
