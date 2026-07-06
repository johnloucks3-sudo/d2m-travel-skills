"""AgentMail wrapper — Thunderbird's agent-native email channel.

Scope: internal/monitoring/agent-identity mail only (Hale's own inbox, wing-to-wing
comms). NOT for client-facing sends — default inboxes are @agentmail.to, a cold
domain; client mail stays on d2mconcierge/johnloucks3 Gmail + WF-17 per
standing orders in CLAUDE.md.

Uses the official `agentmail` SDK (pip install agentmail). API key resolution
order: AGENTMAIL_API_KEY env var, then config/agentmail_credentials.json
{"api_key": "..."}.
"""
import json
import os
from pathlib import Path

from agentmail import AgentMail

from core.email.agentmail_quota import check_and_record

CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / "config" / "agentmail_credentials.json"

# Commander directive 2026-07-06: CC johnloucks3 on ALL AgentMail correspondence
# (both CONDOR and WIND inboxes) until he's satisfied free-tier quota is safe
# and can assess the nature of traffic. Standing default, not per-call-site —
# enforced here so it can't be forgotten by a caller. Remove when he lifts it.
STANDING_MONITOR_CC = "johnloucks3@gmail.com"


def _with_standing_cc(cc: list | None) -> list:
    cc = list(cc) if cc else []
    if STANDING_MONITOR_CC.lower() not in {a.lower() for a in cc}:
        cc.append(STANDING_MONITOR_CC)
    return cc


class AgentMailError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("AGENTMAIL_API_KEY")
    if key:
        return key
    if CREDENTIALS_PATH.exists():
        key = json.loads(CREDENTIALS_PATH.read_text()).get("api_key")
        if key:
            return key
    raise AgentMailError(
        f"No AgentMail API key found (checked $AGENTMAIL_API_KEY and {CREDENTIALS_PATH}). "
        "Sign up at https://console.agentmail.to/sign-up, then Console -> API Keys, "
        "and drop it into config/agentmail_credentials.json as {\"api_key\": \"...\"}."
    )


def get_client() -> AgentMail:
    return AgentMail(api_key=_api_key())


class AgentMailClient:
    """Thin, opinionated wrapper over the official SDK for Thunderbird's call sites."""

    def __init__(self, api_key: str | None = None):
        self.client = AgentMail(api_key=api_key or _api_key())

    def list_inboxes(self):
        return self.client.inboxes.list()

    def create_inbox(self, username: str, display_name: str, client_id: str | None = None):
        # client_id makes this idempotent — safe to retry without creating duplicate inboxes.
        return self.client.inboxes.create(
            request={
                "username": username,
                "display_name": display_name,
                "client_id": client_id or f"inbox-{username}",
            }
        )

    def send_message(self, inbox_id: str, to, subject: str, text: str,
                      html: str | None = None, cc=None, bcc=None, attachments=None):
        check_and_record()  # raises QuotaExceeded before we spend a send on the free tier cap
        return self.client.inboxes.messages.send(
            inbox_id,
            to=to,
            subject=subject,
            text=text,
            html=html,
            cc=_with_standing_cc(cc),
            bcc=bcc,
            attachments=attachments,
        )

    def list_messages(self, inbox_id: str, limit: int = 20, labels=None):
        return self.client.inboxes.messages.list(inbox_id, limit=limit, labels=labels)

    def get_message(self, inbox_id: str, message_id: str):
        return self.client.inboxes.messages.get(inbox_id, message_id)

    def reply_to_message(self, inbox_id: str, message_id: str, text: str, html: str | None = None,
                          attachments=None, to=None, cc=None, bcc=None):
        # NOTE: replying to a message YOUR OWN inbox sent (not one it received) does not
        # auto-fill `to` from the original recipient — it silently loops back to yourself.
        # Always pass `to=` explicitly when continuing an outbound thread you started.
        check_and_record()
        return self.client.inboxes.messages.reply(
            inbox_id, message_id, text=text, html=html, attachments=attachments,
            to=to, cc=_with_standing_cc(cc), bcc=bcc,
        )

    def create_webhook(self, url: str, event_types: list[str]):
        return self.client.webhooks.create(url=url, event_types=event_types)

    def list_webhooks(self):
        return self.client.webhooks.list()
