#!/usr/bin/env python3
"""
emergency_voice_notify.py — backup emergency notification channel: places a
real outbound phone call reading a short TTS message, for P0/client-affecting
escalations where Telegram/SMS/email may not get seen fast enough.

Proven live 2026-07-10: test call to Commander's phone confirmed clear audio,
Twilio status independently verified as 'completed' (not just trusted from
the create-call response). Generalizes core/voice/outbound_call_test.py into
a reusable function other Wing code can call.

Usage:
    from core.voice.emergency_voice_notify import emergency_call
    result = emergency_call("Regent portal session dead, client-affecting, needs your login.")
"""
from __future__ import annotations

import base64
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent.parent
ENV_FILE = THUNDERBIRD / ".env"
CALL_LOG = THUNDERBIRD / "logs" / "emergency_voice_notify.log"

COMMANDER_PHONE = "+17192910742"
TERMINAL_STATUSES = {"completed", "no-answer", "busy", "failed", "canceled"}


def _load_env() -> dict:
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


def _auth_header(sid: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CALL_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def emergency_call(message: str, to: str = COMMANDER_PHONE, max_wait_s: int = 45) -> dict:
    """Place a real outbound call reading `message`, poll Twilio's own Call
    resource for the true terminal status (never trust the create-call
    response alone -- it only confirms the call was queued). Returns a dict
    with sid/status/duration/answered_by. Never raises on a failed call --
    a failed emergency call must not itself crash the caller; the returned
    status is the signal to fall back to another channel."""
    env = _load_env()
    sid = env["TWILIO_ACCOUNT_SID"]
    token = env["TWILIO_AUTH_TOKEN"]
    from_number = env["TWILIO_SMS_NUMBER"]

    twiml = f"<Response><Say voice=\"Polly.Joanna\">{message}</Say></Response>"

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
        body = urllib.parse.urlencode({"To": to, "From": from_number, "Twiml": twiml}).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", _auth_header(sid, token))
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        call_sid = data["sid"]
        _log(f"queued sid={call_sid} to={to} message={message[:80]!r}")
    except Exception as e:
        _log(f"FAILED to queue call to {to}: {e}")
        return {"sid": None, "status": "queue_failed", "error": str(e)}

    status_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json"
    elapsed = 0
    result = {"sid": call_sid, "status": "unknown"}
    while elapsed < max_wait_s:
        try:
            req = urllib.request.Request(status_url)
            req.add_header("Authorization", _auth_header(sid, token))
            with urllib.request.urlopen(req, timeout=15) as r:
                result = json.loads(r.read())
        except Exception as e:
            _log(f"status poll failed for {call_sid}: {e}")
            break
        if result.get("status") in TERMINAL_STATUSES:
            break
        time.sleep(5)
        elapsed += 5

    _log(f"final sid={call_sid} status={result.get('status')} duration={result.get('duration')}s")
    return {
        "sid": call_sid,
        "status": result.get("status"),
        "duration": result.get("duration"),
        "answered_by": result.get("answered_by"),
    }


if __name__ == "__main__":
    import sys
    msg = sys.argv[1] if len(sys.argv) > 1 else "This is a Thunderbird Wing emergency notification test."
    print(emergency_call(msg))
