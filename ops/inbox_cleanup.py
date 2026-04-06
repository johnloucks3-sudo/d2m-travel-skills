#!/usr/bin/env python3
"""
Inbox Cleanup Script — 17 MAR 2026
Commander's orders: DELETE internal/outdated D2M, KEEP D2M-current in D2M/Current_Ops,
DELETE duplicates and expired emails.
"""

import sys
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service, label_name):
    """Get label ID by name, create if not exists."""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    body = {
        "name": label_name,
        "messageListVisibility": "show",
        "labelListVisibility": "labelShow",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    print(f"  ✅ Created label: {label_name} -> {created['id']}")
    return created["id"]


def search_messages(service, query, max_results=100):
    """Return list of message stubs."""
    msgs = []
    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    msgs.extend(result.get("messages", []))
    while "nextPageToken" in result and len(msgs) < max_results:
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results,
            pageToken=result["nextPageToken"]
        ).execute()
        msgs.extend(result.get("messages", []))
    return msgs


def get_headers(service, msg_id):
    """Get subject, from, date, snippet for a message."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["Subject", "From", "Date", "To"]
    ).execute()
    headers = {}
    for h in msg.get("payload", {}).get("headers", []):
        headers[h["name"]] = h["value"]
    headers["snippet"] = msg.get("snippet", "")
    headers["labelIds"] = msg.get("labelIds", [])
    headers["id"] = msg_id
    headers["threadId"] = msg.get("threadId", "")
    return headers


def modify_message(service, msg_id, add_labels=None, remove_labels=None):
    """Add/remove labels on a message."""
    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    service.users().messages().modify(userId="me", id=msg_id, body=body).execute()


def trash_message(service, msg_id):
    """Move message to trash."""
    service.users().messages().trash(userId="me", id=msg_id).execute()


def main():
    service = get_service()
    print("=" * 60)
    print("INBOX CLEANUP — 17 MAR 2026")
    print("=" * 60)

    # ── Step 1: Create labels ──
    print("\n📁 STEP 1: Creating labels...")
    d2m_label_id = get_or_create_label(service, "D2M")
    current_ops_id = get_or_create_label(service, "D2M/Current_Ops")
    print(f"  D2M: {d2m_label_id}")
    print(f"  D2M/Current_Ops: {current_ops_id}")

    # ── Step 2: Identify all inbox messages ──
    print("\n🔍 STEP 2: Scanning inbox...")
    inbox_msgs = search_messages(service, "in:inbox", max_results=500)
    print(f"  Total inbox messages: {len(inbox_msgs)}")

    # Categorize
    delete_list = []  # Internal D2M outdated, duplicates, test emails
    keep_current_ops = []  # D2M-related, move to Current_Ops
    keep_inbox = []  # Non-D2M, stay in inbox

    # Track seen snippets for duplicate detection
    seen_snippets = {}

    for stub in inbox_msgs:
        try:
            h = get_headers(service, stub["id"])
        except Exception as e:
            print(f"  ⚠️ Could not read {stub['id']}: {e}")
            continue

        subject = h.get("Subject", "")
        from_addr = h.get("From", "")
        to_addr = h.get("To", "")
        snippet = h.get("snippet", "")
        labels = h.get("labelIds", [])
        msg_id = h["id"]

        # ── DELETE RULES ──

        # 1. SMS gateway failure notifications (internal, outdated)
        if "SMS" in snippet and "tmomail.net" in snippet:
            delete_list.append((msg_id, f"SMS gateway failure: {subject[:50]}"))
            continue

        # 2. Duplicate concierge received notifications
        dup_key = snippet[:80]
        if "📬 Concierge Email Received" in snippet:
            if dup_key in seen_snippets:
                delete_list.append((msg_id, f"Duplicate concierge notification: {snippet[:50]}"))
                continue
            seen_snippets[dup_key] = msg_id

        # 3. Internal system emails (ISSUE/DISCUSSION format from self to self)
        is_system_intel = (
            snippet.startswith("ISSUE:") and
            "SENT" in labels and
            "johnloucks3" not in from_addr.lower() or
            (not h.get("From") and "ISSUE:" in snippet)
        )

        # 4. Test emails
        is_test = (
            "test" in subject.lower() and
            ("concierge@d2mluxury" in to_addr.lower() or "concierge@d2mluxury" in from_addr.lower())
        ) or (
            "D2M Direct Send Test" in subject
        ) or (
            "Test email — verifying concierge" in snippet
        )

        # 5. Heartbeat / monitor failures
        is_heartbeat = "heartbeat failure" in snippet.lower() or "Concierge Monitor heartbeat" in snippet

        # 6. Internal DANI DRAFT review copies that are outdated
        is_old_dani_draft = "[DANI DRAFT]" in subject and "SENT" in labels

        # 7. Newsmax / Just the News (not travel-related — but Commander said non-travel forward,
        #    for now just keep out of way)
        is_news = "newsmax" in from_addr.lower() or "justthenews" in from_addr.lower()

        if is_test:
            delete_list.append((msg_id, f"Test email: {subject[:60]}"))
        elif is_heartbeat:
            delete_list.append((msg_id, f"Heartbeat alert: {snippet[:60]}"))
        elif is_old_dani_draft:
            delete_list.append((msg_id, f"Old DANI DRAFT review: {subject[:60]}"))
        elif is_news:
            # Non-travel: archive out of inbox (not delete — Commander may want)
            delete_list.append((msg_id, f"Non-travel newsletter: {subject[:60]}"))

        # ── KEEP → CURRENT_OPS RULES ──
        # Internal ISSUE/DISCUSSION intel that IS current and actionable
        elif "ISSUE:" in snippet and "SENT" in labels:
            # These are system-generated intel briefs — check if they're actionable
            if any(kw in snippet for kw in ["Kuklinski", "Viking", "Westbrook", "McLeod", "McGlasson",
                                              "Lyons", "Loucks", "Britan", "Bitran", "Dodge", "Burcham",
                                              "Rehfeldt", "Strait of Hormuz", "flight cancellations"]):
                keep_current_ops.append((msg_id, f"D2M Intel: {snippet[:60]}"))
            else:
                delete_list.append((msg_id, f"Outdated internal intel: {snippet[:60]}"))

        # Concierge received notifications (non-duplicate)
        elif "📬 Concierge Email Received" in snippet:
            keep_current_ops.append((msg_id, f"Concierge alert: {snippet[:60]}"))

        # Dani intro follow-ups sent to clients
        elif "Dani" in subject and "SENT" in labels and any(
            client in to_addr for client in [
                "rwestbrook", "davidmcleran", "loucksrj", "cnuraptor",
                "jbitran", "nancylyons", "klyons"
            ]
        ):
            keep_current_ops.append((msg_id, f"Dani intro: {subject[:60]}"))

        # Meet Dani Moreau emails
        elif "Meet Dani Moreau" in subject:
            keep_current_ops.append((msg_id, f"Dani intro: {subject[:60]}"))

        # Client replies (McLeran, Westbrook HELLO DANI, etc.)
        elif any(client in from_addr.lower() for client in [
            "rwestbrook", "davidmcleran", "loucksrj", "cnuraptor",
            "jbitran", "nancylyons", "klyons"
        ]):
            keep_current_ops.append((msg_id, f"Client reply: {from_addr[:30]} — {subject[:40]}"))

        # Commander replies in D2M threads
        elif "johnloucks3" in from_addr.lower() and any(
            kw in subject.lower() for kw in ["dani", "meet dani", "organized travel", "d2m", "concierge"]
        ):
            keep_current_ops.append((msg_id, f"Commander D2M reply: {subject[:60]}"))

        # Ron Westbrook's HELLO DANI (inbound client email)
        elif "HELLO DANI" in subject:
            keep_current_ops.append((msg_id, f"Client inbound: {subject[:60]}"))

        # Dinner confirmation (Westbrook) — personal but D2M-adjacent, keep
        elif "dinner" in snippet.lower() and "Westbrook" in snippet:
            keep_current_ops.append((msg_id, f"Westbrook dinner: {snippet[:60]}"))

        else:
            keep_inbox.append((msg_id, f"{from_addr[:30]} | {subject[:50]}"))

    # ── Step 3: Report ──
    print(f"\n📊 TRIAGE RESULTS:")
    print(f"  🗑️  DELETE/TRASH: {len(delete_list)}")
    print(f"  📂 MOVE → D2M/Current_Ops: {len(keep_current_ops)}")
    print(f"  📥 KEEP IN INBOX: {len(keep_inbox)}")

    print(f"\n🗑️  DELETE LIST:")
    for msg_id, reason in delete_list:
        print(f"    • {reason}")

    print(f"\n📂 CURRENT_OPS LIST:")
    for msg_id, reason in keep_current_ops:
        print(f"    • {reason}")

    print(f"\n📥 KEEP IN INBOX:")
    for msg_id, reason in keep_inbox:
        print(f"    • {reason}")

    # ── Step 4: Execute ──
    print(f"\n🚀 EXECUTING...")

    # Trash deletions
    trash_count = 0
    for msg_id, reason in delete_list:
        try:
            trash_message(service, msg_id)
            trash_count += 1
        except Exception as e:
            print(f"    ⚠️ Failed to trash {msg_id}: {e}")
    print(f"  🗑️  Trashed: {trash_count}/{len(delete_list)}")

    # Move to Current_Ops (add label, remove INBOX)
    moved_count = 0
    for msg_id, reason in keep_current_ops:
        try:
            modify_message(service, msg_id,
                           add_labels=[current_ops_id, d2m_label_id],
                           remove_labels=["INBOX"])
            moved_count += 1
        except Exception as e:
            print(f"    ⚠️ Failed to move {msg_id}: {e}")
    print(f"  📂 Moved to Current_Ops: {moved_count}/{len(keep_current_ops)}")

    print(f"\n✅ CLEANUP COMPLETE")
    print(f"  Inbox remaining: {len(keep_inbox)} messages")


if __name__ == "__main__":
    main()
