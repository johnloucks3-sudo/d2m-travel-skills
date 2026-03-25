#!/usr/bin/env python3
"""
Thunderbird Inbox Cleanup — Daily Label-Only Hygiene
24 MAR 2026

Scans d2mconcierge@gmail.com AND johnloucks3@gmail.com.
Identifies deletion candidates, applies 'For Deletion' label (RED).
NO ACTUAL DELETES — Commander reviews and clears at his discretion.

Run: python3 thunderbird_inbox_cleanup_daily.py
Arg: --dry-run to skip labeling
"""

import os
import sys
import json
import logging
import argparse
import datetime
from pathlib import Path
from typing import Optional

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ─── Config ────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TOKEN_CONCIERGE = THUNDERBIRD_DIR / "gmail_token.json"
TOKEN_COMMANDER = THUNDERBIRD_DIR / "gmail_token_commander.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

LABEL_NAME = "For Deletion"
# Gmail API red color
LABEL_BG_COLOR = "#fb4c2f"
LABEL_TEXT_COLOR = "#ffffff"

TELEGRAM_BOT = os.getenv("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_COMMANDER_ID", "")

logging.basicConfig(level=logging.WARNING, format="%(message)s")

# ─── Gmail helpers ──────────────────────────────────────────────────────────────

def build_service(token_path: Path) -> Optional[object]:
    """Return Gmail service or None if token missing/invalid."""
    if not token_path.exists():
        print(f"  ⚠️  Token not found: {token_path.name} — skipping account")
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"  ⚠️  Could not authenticate {token_path.name}: {e}")
        return None


def get_or_create_label(service) -> str:
    """Return label ID for 'For Deletion', creating and coloring it if needed."""
    results = service.users().labels().list(userId="me").execute()
    for lbl in results.get("labels", []):
        if lbl["name"] == LABEL_NAME:
            label_id = lbl["id"]
            # Ensure color is set correctly (idempotent patch)
            try:
                service.users().labels().patch(
                    userId="me", id=label_id,
                    body={"color": {"backgroundColor": LABEL_BG_COLOR,
                                    "textColor": LABEL_TEXT_COLOR}}
                ).execute()
            except Exception:
                pass
            return label_id
    # Create fresh
    body = {
        "name": LABEL_NAME,
        "messageListVisibility": "show",
        "labelListVisibility": "labelShow",
        "color": {"backgroundColor": LABEL_BG_COLOR, "textColor": LABEL_TEXT_COLOR},
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    return created["id"]


def search_messages(service, query: str, max_results=200) -> list:
    msgs = []
    result = service.users().messages().list(
        userId="me", q=query, maxResults=min(max_results, 500)
    ).execute()
    msgs.extend(result.get("messages", []))
    while "nextPageToken" in result and len(msgs) < max_results:
        result = service.users().messages().list(
            userId="me", q=query, maxResults=min(max_results - len(msgs), 500),
            pageToken=result["nextPageToken"]
        ).execute()
        msgs.extend(result.get("messages", []))
    return msgs


def get_headers(service, msg_id: str) -> dict:
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["Subject", "From", "To", "Date"]
    ).execute()
    h = {}
    for hdr in msg.get("payload", {}).get("headers", []):
        h[hdr["name"]] = hdr["value"]
    h["snippet"] = msg.get("snippet", "")
    h["labelIds"] = msg.get("labelIds", [])
    h["id"] = msg_id
    return h


def already_labeled(h: dict, label_id: str) -> bool:
    return label_id in h.get("labelIds", [])


def apply_label(service, msg_id: str, label_id: str, dry_run: bool):
    if not dry_run:
        service.users().messages().modify(
            userId="me", id=msg_id,
            body={"addLabelIds": [label_id]}
        ).execute()


def remove_label(service, msg_id: str, label_id: str, dry_run: bool):
    if not dry_run:
        service.users().messages().modify(
            userId="me", id=msg_id,
            body={"removeLabelIds": [label_id]}
        ).execute()


def list_drafts(service) -> list:
    result = service.users().drafts().list(userId="me").execute()
    return result.get("drafts", [])


# ─── Candidate Rules ───────────────────────────────────────────────────────────

CONCIERGE_RULES = [
    # (description, gmail_query, max_results)
    # Automated morning briefings — read + old
    ("Morning briefs >7d (read)",
     "from:d2mconcierge@gmail.com subject:(Morning Brief OR Intel OR Briefing OR Digest) is:read older_than:7d",
     100),
    # Automated batch run logs — read + old
    ("Batch run logs >7d (read)",
     "from:d2mconcierge@gmail.com subject:(Batch OR batch OR BATCH OR log OR LOG) is:read older_than:7d",
     50),
    # Test emails — any age
    ("Test emails",
     "subject:(test OR Test OR TEST) from:d2mconcierge@gmail.com",
     50),
    # Heartbeat / monitor pings — read + old
    ("Heartbeat alerts >3d (read)",
     "subject:(heartbeat OR monitor OR health OR alive) is:read older_than:3d",
     50),
    # Old system/auth notifications — read + old
    ("System notifications >30d (read)",
     "from:(noreply@google.com OR no-reply@accounts.google.com OR security@google.com) is:read older_than:30d",
     50),
    # Old DANI DRAFT review copies — read + old
    ("Old DANI drafts >14d (read)",
     "subject:(DANI DRAFT OR THUNDERBIRD-Commander-Review) is:read older_than:14d",
     50),
    # Incubator / intel review emails — read + old
    ("Incubator reports >7d (read)",
     "from:d2mconcierge@gmail.com subject:(Incubator OR Night OR Review OR Scrape) is:read older_than:7d",
     50),
    # Old sent confirmations back to self
    ("Old self-confirmations >14d (read)",
     "to:johnloucks3@gmail.com from:d2mconcierge@gmail.com is:read older_than:14d",
     100),
]

COMMANDER_RULES = [
    # D2M reports received from concierge — read + old
    ("D2M reports >14d (read)",
     "from:d2mconcierge@gmail.com is:read older_than:14d",
     100),
    # Newsletters / promotional — read + old
    ("Newsletters >14d (read)",
     "category:promotions is:read older_than:14d",
     50),
    ("Newsletters >14d (read, updates)",
     "category:updates is:read older_than:14d",
     50),
    # Google system — read + old
    ("Google system >30d (read)",
     "from:(noreply@google.com OR no-reply@accounts.google.com) is:read older_than:30d",
     30),
    # Social notifications — read + old
    ("Social notifications >7d (read)",
     "category:social is:read older_than:7d",
     50),
    # Old delivery/receipt notifications
    ("Delivery confirmations >7d (read)",
     "subject:(delivered OR undeliverable OR delivery status) is:read older_than:7d",
     30),
    # Old Telegram session logs
    ("Telegram session logs >14d (read)",
     "subject:(Telegram Session OR Session Log OR session log) is:read older_than:14d",
     30),
]


# ─── Duplicate draft detection ─────────────────────────────────────────────────

SYSTEM_BRIEF_MARKERS = [
    "THUNDERBIRD COMMAND BRIEF",
    "COS-EXEC Briefing",
    "COS-EXEC Action Items",
    "MORNING INTEL",
    "NIGHT 1 REVIEW",
    "Incubator Review",
]

CLIENT_DRAFT_MARKERS = [
    # Name-like opening patterns — these are real client drafts
    "Hi ", "Hello ", "Dear ", "Good morning", "Good afternoon",
    "Larry", "Heidi", "Al,", "John and Missy", "Missy", "Kyle,",
    "Greg,", "Roger,", "Nick,", "Rosalie,", "Josh,", "Erica,",
    "Brent,", "Kim,", "Ron,", "Dave,", "Tammy,",
]


def find_duplicate_drafts(service) -> list:
    """
    Return message IDs of older duplicate system-generated drafts.
    ONLY flags:
      - Drafts with no subject AND no To address AND system-brief content
      - Named-subject drafts with exact duplicates (e.g. same template sent twice)
    Does NOT flag client email drafts (even if no subject).
    """
    try:
        drafts = list_drafts(service)
    except Exception:
        return []
    if len(drafts) < 2:
        return []

    subject_map: dict[str, list] = {}
    for d in drafts:
        draft_id = d.get("id", "")
        msg_id = d.get("message", {}).get("id", "")
        if not msg_id:
            continue
        try:
            h = get_headers(service, msg_id)
        except Exception:
            continue

        subj = h.get("Subject", "").strip()
        to_addr = h.get("To", "").strip()
        snippet = h.get("snippet", "")

        # No subject + no To address: check if it's a system brief vs client draft
        if not subj and not to_addr:
            is_system = any(marker in snippet for marker in SYSTEM_BRIEF_MARKERS)
            is_client = any(snippet.startswith(m) or (len(snippet) > 2 and snippet[1:3] in (", ", "! "))
                            for m in CLIENT_DRAFT_MARKERS)
            if is_client:
                continue  # Skip — real client draft, don't flag
            if not is_system:
                continue  # Unknown blank draft — leave alone

        # Key: normalize subject for grouping
        norm = subj.lower().lstrip("re: ").lstrip("fwd: ").strip() if subj else f"_nosub_{snippet[:60]}"
        if norm not in subject_map:
            subject_map[norm] = []
        subject_map[norm].append({
            "draft_id": draft_id,
            "msg_id": msg_id,
            "subject": subj,
            "date": h.get("Date", ""),
        })

    duplicates = []
    for norm, items in subject_map.items():
        if len(items) > 1:
            sorted_items = sorted(items, key=lambda x: x["date"], reverse=True)
            for item in sorted_items[1:]:  # keep newest, flag older
                duplicates.append(item["msg_id"])
    return duplicates


# ─── Scan one account ─────────────────────────────────────────────────────────

def scan_account(service, account_label: str, rules: list, dry_run: bool) -> dict:
    """Run all rules, apply 'For Deletion' label to candidates. Return summary."""
    label_id = get_or_create_label(service)
    print(f"\n  📁 'For Deletion' label ID: {label_id} (color: red)")

    total_new = 0
    total_already = 0
    total_cleared = 0
    rule_results = []

    for rule_name, query, max_r in rules:
        try:
            msgs = search_messages(service, query, max_results=max_r)
        except Exception as e:
            print(f"    ⚠️  Query failed [{rule_name}]: {e}")
            rule_results.append((rule_name, 0, 0))
            continue

        new_count = 0
        already_count = 0
        for stub in msgs:
            try:
                h = get_headers(service, stub["id"])
            except Exception:
                continue
            if already_labeled(h, label_id):
                already_count += 1
            else:
                apply_label(service, stub["id"], label_id, dry_run)
                new_count += 1

        total_new += new_count
        total_already += already_count
        rule_results.append((rule_name, new_count, already_count))
        if new_count > 0:
            print(f"    ✅ [{rule_name}] → {new_count} newly labeled, {already_count} already labeled")

    # Duplicate draft scan
    dupe_msg_ids = find_duplicate_drafts(service)
    if dupe_msg_ids:
        print(f"    📄 Duplicate drafts: {len(dupe_msg_ids)} older copies flagged")
        for msg_id in dupe_msg_ids:
            try:
                h = get_headers(service, msg_id)
                if not already_labeled(h, label_id):
                    apply_label(service, msg_id, label_id, dry_run)
                    total_new += 1
                else:
                    total_already += 1
            except Exception:
                pass
        rule_results.append(("Duplicate drafts", len(dupe_msg_ids), 0))

    # Count total messages carrying the label (exact from label metadata)
    try:
        label_info = service.users().labels().get(userId="me", id=label_id).execute()
        total_labeled_count = label_info.get("messagesTotal", total_new + total_already)
    except Exception:
        total_labeled_count = total_new + total_already

    return {
        "account": account_label,
        "new_labeled": total_new,
        "already_labeled": total_already,
        "total_in_queue": total_labeled_count,
        "rules": rule_results,
    }


# ─── Telegram report ──────────────────────────────────────────────────────────

def send_telegram(message: str):
    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def build_report(results: list, dry_run: bool) -> str:
    now = datetime.datetime.now().strftime("%d %b %Y %H:%M")
    lines = [
        f"<b>📬 Inbox Cleanup Report — {now}</b>",
        f"{'[DRY RUN] ' if dry_run else ''}No messages deleted — labeled only.",
        "",
    ]
    for r in results:
        lines.append(f"<b>{r['account']}</b>")
        lines.append(f"  • Newly flagged: {r['new_labeled']}")
        lines.append(f"  • Already in queue: {r['already_labeled']}")
        lines.append(f"  • Total 'For Deletion' queue: {r['total_in_queue']}")
        lines.append("")

    lines.append("Review 'For Deletion' label in Gmail → delete what you want, ignore the rest.")
    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Thunderbird inbox cleanup — label only")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't apply labels")
    args = parser.parse_args()

    dry_run = args.dry_run
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{'='*60}")
    print(f"{prefix}THUNDERBIRD INBOX CLEANUP — {datetime.date.today()}")
    print(f"{'='*60}")
    print("Mode: label-only, NO deletes")

    results = []

    # ── d2mconcierge ──
    print(f"\n🔵 d2mconcierge@gmail.com")
    svc_concierge = build_service(TOKEN_CONCIERGE)
    if svc_concierge:
        r = scan_account(svc_concierge, "d2mconcierge@gmail.com", CONCIERGE_RULES, dry_run)
        results.append(r)
        print(f"\n  Summary: {r['new_labeled']} newly flagged, {r['total_in_queue']} total in queue")

    # ── johnloucks3 ──
    print(f"\n🟡 johnloucks3@gmail.com")
    svc_commander = build_service(TOKEN_COMMANDER)
    if svc_commander:
        r = scan_account(svc_commander, "johnloucks3@gmail.com", COMMANDER_RULES, dry_run)
        results.append(r)
        print(f"\n  Summary: {r['new_labeled']} newly flagged, {r['total_in_queue']} total in queue")

    # ── Report ──
    print(f"\n{'='*60}")
    print("CLEANUP COMPLETE")
    for r in results:
        print(f"  {r['account']}: {r['new_labeled']} newly flagged / {r['total_in_queue']} total in queue")

    if results:
        report = build_report(results, dry_run)
        send_telegram(report)
        print("\n📱 Telegram report sent to Commander.")
    else:
        print("\n  ⚠️  No accounts scanned.")


if __name__ == "__main__":
    main()
