#!/usr/bin/env python3
"""Minimal AgentMail integration test — create inbox, send to johnloucks3, confirm receipt, pull inbound.

Run once a valid API key is in config/agentmail_credentials.json or $AGENTMAIL_API_KEY.
"""
import sys
import time

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient, AgentMailError

INBOX_USERNAME = "hale-thunderbird"
INBOX_DISPLAY = "Hale — Thunderbird Wing"
TEST_RECIPIENT = "johnloucks3@gmail.com"  # within-wing, no send gate


def main():
    client = AgentMailClient()

    print("1. Listing existing inboxes...")
    inboxes = client.list_inboxes()
    print(f"   {inboxes}")

    inbox_id = f"{INBOX_USERNAME}@agentmail.to"
    existing = [i for i in inboxes.get("inboxes", inboxes if isinstance(inboxes, list) else [])
                if i.get("inbox_id") == inbox_id or i.get("email") == inbox_id]
    if not existing:
        print(f"2. Creating inbox {INBOX_USERNAME}...")
        created = client.create_inbox(INBOX_USERNAME, INBOX_DISPLAY)
        print(f"   {created}")
        inbox_id = created.get("inbox_id") or created.get("inboxId") or inbox_id
    else:
        print(f"2. Inbox already exists: {inbox_id}")

    print(f"3. Sending test email to {TEST_RECIPIENT}...")
    sent = client.send_message(
        inbox_id=inbox_id,
        to=[TEST_RECIPIENT],
        subject="AgentMail integration test — Thunderbird Wing",
        text="This is a round-trip test from Hale's new AgentMail inbox. If you can read this, send worked.",
    )
    print(f"   {sent}")

    print("4. Waiting 5s, then pulling messages back from the inbox...")
    time.sleep(5)
    messages = client.list_messages(inbox_id)
    print(f"   {messages}")

    print("\nDONE — round-trip proof: create -> send -> list. Reply to this address to test inbound.")


if __name__ == "__main__":
    try:
        main()
    except AgentMailError as e:
        print(f"BLOCKED: {e}")
        sys.exit(1)
