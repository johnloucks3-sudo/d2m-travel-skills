"""Unit tests for icelandair_session_warm.py's pure logic (auth-marker
parsing, cookie shaping). The live CDP/Xvfb path is exercised manually
(see docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-
engineered.md addendum) — not mocked here, since faking CDP responses
would test the mock, not the real Cloudflare/DOM behavior."""
from __future__ import annotations

import json

import scripts.icelandair_session_warm as warm_module


class _FakeWS:
    def __init__(self, responses):
        self._responses = responses
        self.sent = []

    def send(self, msg):
        self.sent.append(json.loads(msg))

    def settimeout(self, t):
        pass

    def recv(self):
        return json.dumps(self._responses.pop(0))


def test_check_authenticated_true_when_no_login_no_challenge():
    ws = _FakeWS([{"id": 2, "result": {"result": {"value": json.dumps(
        {"title": "Icelandair US", "hasLogin": False, "hasChallenge": False})}}}])
    assert warm_module._check_authenticated(ws) is True


def test_check_authenticated_false_on_login_prompt():
    ws = _FakeWS([{"id": 2, "result": {"result": {"value": json.dumps(
        {"title": "Icelandair US", "hasLogin": True, "hasChallenge": False})}}}])
    assert warm_module._check_authenticated(ws) is False


def test_check_authenticated_false_on_cloudflare_challenge():
    ws = _FakeWS([{"id": 2, "result": {"result": {"value": json.dumps(
        {"title": "Just a moment...", "hasLogin": False, "hasChallenge": True})}}}])
    assert warm_module._check_authenticated(ws) is False


def test_extract_icelandair_cookies_filters_domain_and_shapes_fields():
    ws = _FakeWS([{"id": 3, "result": {"cookies": [
        {"name": "iceAuth", "value": "abc", "domain": ".icelandair.com", "path": "/",
         "secure": True, "httpOnly": True, "expires": 123.0, "sameSite": "Lax"},
        {"name": "_ga", "value": "xyz", "domain": ".google-analytics.com", "path": "/"},
    ]}}])
    out = warm_module._extract_icelandair_cookies(ws)
    assert len(out) == 1
    assert out[0]["name"] == "iceAuth"
    assert out[0]["secure"] is True
    assert out[0]["expires"] == 123.0


def test_warm_returns_2_when_no_cookie_file(tmp_path, monkeypatch):
    monkeypatch.setattr(warm_module, "COOKIE_FILE", tmp_path / "missing.json")
    assert warm_module.warm() == 2
