"""AgentMail REST client — Thunderbird's own agent-native email channel.

Scope: internal/monitoring/agent-identity mail only (Hale's own inbox, wing-to-wing
comms). NOT for client-facing sends — default inboxes are @agentmail.to, a cold
domain; client mail stays on d2mconcierge/johnloucks3 Gmail + WF-17 per
standing orders. See standing_orders/SO_TALON_JET... and CLAUDE.md email rules.

API key resolution order: AGENTMAIL_API_KEY env var, then
config/agentmail_credentials.json {"api_key": "..."}.
"""
import json
import os
from pathlib import Path

import requests

BASE_URL = "https://api.agentmail.to/v0"
CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / "config" / "agentmail_credentials.json"


class AgentMailError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("AGENTMAIL_API_KEY")
    if key:
        return key
    if CREDENTIALS_PATH.exists():
        data = json.loads(CREDENTIALS_PATH.read_text())
        key = data.get("api_key")
        if key:
            return key
    raise AgentMailError(
        f"No AgentMail API key found (checked $AGENTMAIL_API_KEY and {CREDENTIALS_PATH}). "
        "Sign up at https://console.agentmail.to/sign-up and paste the key into "
        "config/agentmail_credentials.json as {\"api_key\": \"...\"}."
    )


class AgentMailClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or _api_key()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs):
        resp = self.session.request(method, f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise AgentMailError(f"{method} {path} -> {resp.status_code}: {resp.text[:500]}")
        return resp.json() if resp.content else {}

    def list_inboxes(self):
        return self._request("GET", "/inboxes")

    def create_inbox(self, username: str, display_name: str):
        return self._request("POST", "/inboxes", json={
            "username": username,
            "display_name": display_name,
        })

    def send_message(self, inbox_id: str, to: list[str], subject: str, text: str,
                      html: str | None = None, cc: list[str] | None = None):
        body = {"to": to, "subject": subject, "text": text}
        if html:
            body["html"] = html
        if cc:
            body["cc"] = cc
        return self._request("POST", f"/inboxes/{inbox_id}/messages/send", json=body)

    def list_messages(self, inbox_id: str, limit: int = 20):
        return self._request("GET", f"/inboxes/{inbox_id}/messages", params={"limit": limit})

    def get_message(self, inbox_id: str, message_id: str):
        return self._request("GET", f"/inboxes/{inbox_id}/messages/{message_id}")

    def reply_to_message(self, inbox_id: str, message_id: str, text: str):
        return self._request("POST", f"/inboxes/{inbox_id}/messages/{message_id}/reply", json={"text": text})

    def create_webhook(self, url: str, event_types: list[str]):
        return self._request("POST", "/webhooks", json={"url": url, "event_types": event_types})

    def list_webhooks(self):
        return self._request("GET", "/webhooks")
