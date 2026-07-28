"""
Regression tests for scripts/credentials_health_check.py's Telegram alert path.

REGRESSION (2026-07-16): send_telegram_alerts() builds an alert message by
interpolating raw cookie/reason/reauth-cmd text into a string sent with
parse_mode="Markdown" (OpsCenter/hale_telegram_reporter.py::send_to_commander).
Cookie names and script paths routinely contain literal "_" and "[...]"
(laravel_session, __stripe_sid, [auth-gate], portal_keepalive.py) with no
matching Markdown pair -- Telegram's legacy parser 400s on any one unescaped
occurrence ("can't parse entities"), the send silently fails, and the
credential check -- which correctly detects real Regent/Centrav expiry --
never reaches the Commander's phone. Ground truth: this crashed for hours
because ONE field (reauth_cmd) was still unescaped after an initial partial
fix; this suite exists so that regression can't land silently again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import credentials_health_check as chc  # noqa: E402
from OpsCenter import hale_telegram_reporter  # noqa: E402


def _capture_sent_text(monkeypatch):
    captured = {}

    def fake_send_to_commander(message, message_type="update", urgent=False, also_email=False):
        captured["message"] = message
        captured["formatted"] = f"🚨 ⚠️ **[Hale]** {message}" if urgent else f"⚠️ **[Hale]** {message}"
        return True

    monkeypatch.setattr(hale_telegram_reporter, "send_to_commander", fake_send_to_commander)
    return captured


class TestTelegramAlertEscaping:
    def test_all_dynamic_fields_are_markdown_escaped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chc, "ALERT_DEDUP", tmp_path / "dedup.json")
        captured = _capture_sent_text(monkeypatch)

        results = {
            "client_affecting_alerts": [
                {
                    "name": "centrav_cookies",
                    "status": "expired",
                    "reason": "Expired 5.2h ago (cookie: laravel_session [auth-gate], also __stripe_sid)",
                    "reauth_cmd": "python3 scripts/portal_keepalive.py --portal centrav",
                }
            ]
        }
        chc.send_telegram_alerts(results)

        assert "message" in captured, "send_to_commander was never called -- alert dropped silently"
        msg = captured["message"]
        # every raw "_" and "[" that isn't part of an escape sequence must have been escaped
        for bad in ("laravel_session", "auth-gate]", "__stripe_sid", "portal_keepalive.py"):
            assert bad not in msg, f"unescaped fragment {bad!r} would 400 against Telegram's legacy Markdown parser"
        assert "laravel\\_session" in msg
        assert "\\_\\_stripe\\_sid" in msg
        assert "portal\\_keepalive.py" in msg, "reauth_cmd field must be escaped too -- this was the field missed in the first fix pass"

    def test_dedup_only_commits_after_reported_success(self, tmp_path, monkeypatch):
        dedup_path = tmp_path / "dedup.json"
        monkeypatch.setattr(chc, "ALERT_DEDUP", dedup_path)

        def fake_send_fail(message, message_type="update", urgent=False, also_email=False):
            return False

        monkeypatch.setattr(hale_telegram_reporter, "send_to_commander", fake_send_fail)

        results = {
            "client_affecting_alerts": [
                {"name": "regent_cookies", "status": "expired", "reason": "x", "reauth_cmd": "y"}
            ]
        }
        chc.send_telegram_alerts(results)
        assert not dedup_path.exists() or dedup_path.read_text().strip() in ("", "{}"), \
            "a failed send must not be recorded as delivered -- next run has to retry"
