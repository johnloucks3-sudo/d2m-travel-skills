"""
Regression tests for the TESS OAuth refresh_token() client-selection hardening
(2026-07-16, Block 2).

Root cause: tess_config.json carried client_id="johnloucks3@gmail.com" (the
Commander's email — not a real OAuth client) plus a bogus client_secret. The
live TESS token is minted by the public Angular SPA client "ngAuthApp" (PKCE,
no secret), so presenting that email client_id / a secret made the token
endpoint reject the refresh grant with invalid_client every ~90min — silently
absorbed by a Playwright credential fallback.

These tests pin the fixed behaviour by capturing the POST body sent to the
token endpoint (requests.post is mocked — no network, no disk writes).
"""
import sys

sys.path.insert(0, "/home/john/Thunderbird")

import core.booking.thunderbird_tess as tess_mod
from core.booking.thunderbird_tess import TESSAuth, DEFAULT_CLIENT_ID


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self.ok = status < 400
        self._p = payload
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._p


def _auth_with(monkeypatch, client_id, client_secret, token_client_id=None):
    """Build a TESSAuth with controlled creds and a mocked token endpoint.

    Returns (auth, captured) where captured['data'] is the POST body.
    """
    auth = TESSAuth()
    auth.client_id = client_id
    auth.client_secret = client_secret
    auth._tokens = {
        "refresh_token": "RT-abc",
        "access_token": "old-access",
        "token_type": "bearer",
        "expires_in": 3600,
        "issued_at": 0,
    }
    if token_client_id is not None:
        auth._tokens["client_id"] = token_client_id
    # never touch the real token file
    monkeypatch.setattr(auth, "_save_tokens", lambda: None)

    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _Resp(200, {
            "access_token": "new-access",
            "token_type": "bearer",
            "expires_in": 3600,
        })

    monkeypatch.setattr(tess_mod.requests, "post", fake_post)
    return auth, captured


def test_email_clientid_is_replaced_with_public_client_and_secret_dropped(monkeypatch):
    # Reproduces the exact production misconfiguration.
    auth, captured = _auth_with(monkeypatch, "johnloucks3@gmail.com", "bogus16charsecre")
    assert auth.refresh_token() is True
    assert captured["data"]["client_id"] == DEFAULT_CLIENT_ID  # ngAuthApp
    assert "client_secret" not in captured["data"]             # public client → no secret


def test_public_client_never_sends_secret(monkeypatch):
    # Even with ngAuthApp explicitly + a secret present, no secret is sent —
    # sending one is itself rejected (invalid_grant) by the public client.
    auth, captured = _auth_with(monkeypatch, DEFAULT_CLIENT_ID, "some-secret")
    assert auth.refresh_token() is True
    assert captured["data"]["client_id"] == DEFAULT_CLIENT_ID
    assert "client_secret" not in captured["data"]


def test_empty_clientid_falls_back_to_default(monkeypatch):
    auth, captured = _auth_with(monkeypatch, "", "")
    assert auth.refresh_token() is True
    assert captured["data"]["client_id"] == DEFAULT_CLIENT_ID


def test_genuine_confidential_client_keeps_its_secret(monkeypatch):
    # A real (non-public, non-email) confidential client must still authenticate
    # with its secret — the guard only strips the public-client / email cases.
    auth, captured = _auth_with(monkeypatch, "realConfidentialClient", "s3cr3t")
    assert auth.refresh_token() is True
    assert captured["data"]["client_id"] == "realConfidentialClient"
    assert captured["data"]["client_secret"] == "s3cr3t"


def test_refresh_grant_shape(monkeypatch):
    auth, captured = _auth_with(monkeypatch, "johnloucks3@gmail.com", "bogus16charsecre")
    auth.refresh_token()
    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "RT-abc"
    assert captured["url"].endswith("/token")
