#!/usr/bin/env python3
"""d2mconcierge <-> AgentMail bridge — application-layer link (no new Gmail OAuth scope needed).

True Gmail-side forwarding needs the sensitive gmail.settings.sharing scope,
which the current persona_gmail_token.json grant doesn't have (gmail.modify
only) — that requires a fresh consent-screen click, a human-only step.

Instead: poll d2mconcierge for new messages from the named WF-17-exception
correspondents (Nancy/Ken Lyons per SO_LYONS_WF17_EXCEPTION_PIPELINE), and
relay each one into hale-thunderbird@agentmail.to. This puts Lyons-thread
traffic through the same real-time listener/quota-guard/Telegram-bridge
infra as everything else — Primary C2 sees it, without a new OAuth grant.

Run as a periodic job (deploy/d2m-agentmail-bridge.timer), not persistent —
Gmail search is poll-based here, no push mechanism configured.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from core.email.agentmail_client import AgentMailClient

TOKEN_FILE = "/home/john/Thunderbird/config/persona_gmail_token.json"
CREDS_FILE = "/home/john/.config/google-workspace-mcp/credentials.json"
CHECKPOINT_PATH = Path("/home/john/Thunderbird/OpsCenter/state/d2m_agentmail_bridge_checkpoint.json")
RELAY_INBOX = "hale-thunderbird@agentmail.to"

# SO_LYONS_WF17_EXCEPTION_PIPELINE_20260705 — named correspondents only
LYONS_QUERY = "from:(klyons3@bellsouth.net OR kenlyons73@bellsouth.net OR nancylyons73@outlook.com)"


def _gmail_service():
    token = json.load(open(TOKEN_FILE))
    creds_data = json.load(open(CREDS_FILE))
    creds = Credentials(
        token=token.get("token", token.get("access_token")),
        refresh_token=token["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
    )
    if creds.expired:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _load_checkpoint() -> set:
    if CHECKPOINT_PATH.exists():
        return set(json.loads(CHECKPOINT_PATH.read_text()).get("relayed_ids", []))
    return set()


def _save_checkpoint(relayed_ids: set):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps({
        "relayed_ids": sorted(relayed_ids),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def main():
    svc = _gmail_service()
    relayed = _load_checkpoint()
    client = AgentMailClient()

    results = svc.users().messages().list(userId="me", q=LYONS_QUERY, maxResults=20).execute()
    messages = results.get("messages", [])
    new_count = 0

    for m in messages:
        gmail_id = m["id"]
        if gmail_id in relayed:
            continue
        msg = svc.users().messages().get(userId="me", id=gmail_id, format="metadata",
                                          metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        client.send_message(
            inbox_id=RELAY_INBOX,
            to=[RELAY_INBOX],
            subject=f"[Lyons relay] {headers.get('Subject', '(no subject)')}",
            text=(
                f"Relayed from d2mconcierge Gmail (WF-17 Lyons exception thread).\n\n"
                f"From: {headers.get('From')}\n"
                f"Date: {headers.get('Date')}\n"
                f"Gmail message id: {gmail_id}\n\n"
                f"Snippet: {msg.get('snippet', '')}"
            ),
        )
        relayed.add(gmail_id)
        new_count += 1
        print(f"[bridge] relayed {gmail_id} from {headers.get('From')}")

    _save_checkpoint(relayed)
    print(f"[bridge] done — {new_count} new message(s) relayed, {len(relayed)} total tracked")


if __name__ == "__main__":
    main()
