#!/usr/bin/env python3
"""
Offline tests for tcd.sms_gateway — Android SMS gateway client.

No credentials, no network, no real phone: config is monkeypatched to a
tmp_path fixture, the android_sms_gateway client's HTTP layer is never hit
(send_sms/get_status tests use a fake _client() context manager), and
poll_inbox's requests.get is monkeypatched.
    python -m pytest tests/test_tcd_sms_gateway.py -v
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import sms_gateway  # noqa: E402


def _write_config(path, **overrides):
    cfg = {"base_url": "http://100.64.1.2:8080", "username": "gwuser",
          "password": "gwpass", "commander_phone": "+17195551234"}
    cfg.update(overrides)
    path.write_text(json.dumps(cfg))
    return cfg


class TestConfigLoading:
    def test_missing_config_raises_not_configured(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", tmp_path / "missing.json")
        with pytest.raises(sms_gateway.NotConfigured, match="No SMS gateway config"):
            sms_gateway._load_config()

    def test_missing_required_field_raises(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps({"base_url": "http://x:8080"}))  # no username/password
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        with pytest.raises(sms_gateway.NotConfigured, match="username"):
            sms_gateway._load_config()

    def test_valid_config_loads(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        cfg = sms_gateway._load_config()
        assert cfg["base_url"] == "http://100.64.1.2:8080"


class TestSendSms:
    def test_send_sms_calls_client_with_message(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)

        fake_response = MagicMock(id="msg-123", state="Pending")
        fake_client = MagicMock()
        fake_client.__enter__ = MagicMock(return_value=fake_client)
        fake_client.__exit__ = MagicMock(return_value=False)
        fake_client.send = MagicMock(return_value=fake_response)
        monkeypatch.setattr(sms_gateway, "_client", lambda: fake_client)

        result = sms_gateway.send_sms(["+15551234567"], "Test message")
        assert result == {"id": "msg-123", "state": "Pending"}
        fake_client.send.assert_called_once()
        sent_message = fake_client.send.call_args[0][0]
        assert sent_message.phone_numbers == ["+15551234567"]
        assert sent_message.text_message.text == "Test message"

    def test_client_points_at_local_server_not_cloud_default(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path, base_url="http://100.64.1.2:8080/")  # trailing slash
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        captured = {}
        class FakeAPIClient:
            def __init__(self, login, password, base_url):
                captured["login"] = login
                captured["password"] = password
                captured["base_url"] = base_url
        fake_module = type(sys)("android_sms_gateway.client")
        fake_module.APIClient = FakeAPIClient
        monkeypatch.setitem(sys.modules, "android_sms_gateway.client", fake_module)
        # `from android_sms_gateway import client` reads the PARENT package's
        # attribute, not sys.modules directly — patching sys.modules alone
        # leaves the real client module reachable via that attribute.
        import android_sms_gateway
        monkeypatch.setattr(android_sms_gateway, "client", fake_module)
        sms_gateway._client()
        # trailing slash stripped, /3rdparty/v1 appended, NOT the library's
        # cloud default (api.sms-gate.app) — this is the whole point of the
        # override.
        assert captured["base_url"] == "http://100.64.1.2:8080/3rdparty/v1"
        assert "api.sms-gate.app" not in captured["base_url"]

    def test_send_sms_without_config_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", tmp_path / "missing.json")
        with pytest.raises(sms_gateway.NotConfigured):
            sms_gateway.send_sms(["+15551234567"], "hi")


class TestSendAlert:
    def test_send_alert_uses_commander_phone(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path, commander_phone="+17195559999")
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        captured = {}
        monkeypatch.setattr(sms_gateway, "send_sms",
                            lambda numbers, text: captured.update(
                                {"numbers": numbers, "text": text}) or {"id": "x", "state": "Pending"})
        sms_gateway.send_alert("P0: FPD overdue")
        assert captured["numbers"] == ["+17195559999"]
        assert captured["text"] == "P0: FPD overdue"

    def test_send_alert_no_commander_phone_configured_raises(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        cfg = _write_config(cfg_path)
        del cfg["commander_phone"]
        cfg_path.write_text(json.dumps(cfg))
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        with pytest.raises(sms_gateway.NotConfigured, match="commander_phone"):
            sms_gateway.send_alert("test")


class TestGetStatus:
    def test_get_status_returns_state(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        fake_status = MagicMock(state="Delivered")
        fake_client = MagicMock()
        fake_client.__enter__ = MagicMock(return_value=fake_client)
        fake_client.__exit__ = MagicMock(return_value=False)
        fake_client.get_state = MagicMock(return_value=fake_status)
        monkeypatch.setattr(sms_gateway, "_client", lambda: fake_client)
        result = sms_gateway.get_status("msg-123")
        assert result == {"id": "msg-123", "state": "Delivered"}


class TestPollInbox:
    def test_poll_inbox_parses_response(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)

        fake_response = MagicMock()
        fake_response.json.return_value = [
            {"id": "m1", "sender": "+15559990000", "contentPreview": "Hello",
             "createdAt": "2026-07-12T10:00:00Z"},
        ]
        fake_response.raise_for_status = MagicMock()
        monkeypatch.setattr(sms_gateway.requests, "get", lambda *a, **kw: fake_response)

        result = sms_gateway.poll_inbox()
        assert len(result) == 1
        assert result[0] == {"id": "m1", "sender": "+15559990000", "text": "Hello",
                             "receivedAt": "2026-07-12T10:00:00Z"}

    def test_poll_inbox_uses_basic_auth_and_correct_endpoint(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)

        captured = {}
        def fake_get(url, params=None, auth=None, timeout=None):
            captured.update({"url": url, "params": params, "auth": auth})
            resp = MagicMock()
            resp.json.return_value = []
            resp.raise_for_status = MagicMock()
            return resp
        monkeypatch.setattr(sms_gateway.requests, "get", fake_get)

        sms_gateway.poll_inbox(limit=10)
        assert captured["url"] == "http://100.64.1.2:8080/inbox"
        assert captured["auth"] == ("gwuser", "gwpass")
        assert captured["params"]["limit"] == 10
        assert captured["params"]["type"] == "SMS"

    def test_poll_inbox_empty_result(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        fake_response = MagicMock()
        fake_response.json.return_value = []
        fake_response.raise_for_status = MagicMock()
        monkeypatch.setattr(sms_gateway.requests, "get", lambda *a, **kw: fake_response)
        assert sms_gateway.poll_inbox() == []

    def test_poll_inbox_since_iso_passed_as_from_param(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        captured = {}
        def fake_get(url, params=None, auth=None, timeout=None):
            captured["params"] = params
            resp = MagicMock()
            resp.json.return_value = []
            resp.raise_for_status = MagicMock()
            return resp
        monkeypatch.setattr(sms_gateway.requests, "get", fake_get)
        sms_gateway.poll_inbox(since_iso="2026-07-12T00:00:00Z")
        assert captured["params"]["from"] == "2026-07-12T00:00:00Z"

    def test_poll_inbox_http_error_propagates(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        _write_config(cfg_path)
        monkeypatch.setattr(sms_gateway, "CONFIG_PATH", cfg_path)
        fake_response = MagicMock()
        fake_response.raise_for_status.side_effect = sms_gateway.requests.HTTPError("401")
        monkeypatch.setattr(sms_gateway.requests, "get", lambda *a, **kw: fake_response)
        with pytest.raises(sms_gateway.requests.HTTPError):
            sms_gateway.poll_inbox()
