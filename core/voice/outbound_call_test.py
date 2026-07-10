#!/usr/bin/env python3
"""
outbound_call_test.py — minimal outbound Twilio voice call test.

Places a one-way TTS announcement call to a target number, then polls the
Call resource's own status (queued -> ringing -> in-progress -> completed/
no-answer/busy/failed) rather than trusting calls.create()'s response alone
(that call only confirms the request was queued, not that it connected).

Usage:
  .venv/bin/python3 core/voice/outbound_call_test.py [--to +17192910742]
"""
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent.parent
ENV_FILE = THUNDERBIRD / ".env"

TEST_MESSAGE = (
    "This is a test call from the Thunderbird Wing voice capability. "
    "If you can hear this clearly, outbound calling is confirmed. "
    "This call will now end."
)


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


def place_call(to: str) -> str:
    env = _load_env()
    sid = env["TWILIO_ACCOUNT_SID"]
    token = env["TWILIO_AUTH_TOKEN"]
    from_number = env["TWILIO_SMS_NUMBER"]

    twiml = f"<Response><Say voice=\"Polly.Joanna\">{TEST_MESSAGE}</Say></Response>"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    body = urllib.parse.urlencode({"To": to, "From": from_number, "Twiml": twiml}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", _auth_header(sid, token))
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    call_sid = data["sid"]
    print(f"call queued: sid={call_sid} status={data['status']} to={to} from={from_number}")
    return call_sid


def poll_status(call_sid: str, max_wait_s: int = 60) -> dict:
    env = _load_env()
    sid = env["TWILIO_ACCOUNT_SID"]
    token = env["TWILIO_AUTH_TOKEN"]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json"

    terminal = {"completed", "no-answer", "busy", "failed", "canceled"}
    elapsed = 0
    last = {}
    while elapsed < max_wait_s:
        req = urllib.request.Request(url)
        req.add_header("Authorization", _auth_header(sid, token))
        with urllib.request.urlopen(req, timeout=15) as r:
            last = json.loads(r.read())
        status = last.get("status")
        print(f"  t+{elapsed}s: status={status}")
        if status in terminal:
            break
        time.sleep(5)
        elapsed += 5
    return last


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="+17192910742")
    args = parser.parse_args()

    call_sid = place_call(args.to)
    result = poll_status(call_sid)

    print("\n--- FINAL STATUS (independently verified via Twilio Call resource) ---")
    print(f"sid: {result.get('sid')}")
    print(f"status: {result.get('status')}")
    print(f"duration: {result.get('duration')}s")
    print(f"answered_by: {result.get('answered_by')}")


if __name__ == "__main__":
    main()
