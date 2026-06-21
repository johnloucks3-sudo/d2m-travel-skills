#!/usr/bin/env python3
"""
Gmail Label Reorganization — 17 MAR 2026
Commander-authorized full label restructure.

Phase 1: Create new label hierarchy
Phase 2: Migrate threads from old labels to new
Phase 3: Report results (old labels NOT deleted until Commander confirms)
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
            return label["id"], False  # existed
    body = {
        "name": label_name,
        "messageListVisibility": "show",
        "labelListVisibility": "labelShow",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    return created["id"], True  # newly created


def get_label_id(service, label_name):
    """Get label ID by name, return None if not found."""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    return None


def get_threads_by_label(service, label_id, max_results=500):
    """Get all thread IDs with a given label."""
    threads = []
    result = service.users().threads().list(
        userId="me", labelIds=[label_id], maxResults=min(max_results, 500)
    ).execute()
    threads.extend(result.get("threads", []))
    while "nextPageToken" in result and len(threads) < max_results:
        result = service.users().threads().list(
            userId="me", labelIds=[label_id], maxResults=500,
            pageToken=result["nextPageToken"]
        ).execute()
        threads.extend(result.get("threads", []))
    return threads


def modify_thread(service, thread_id, add_labels=None, remove_labels=None):
    """Add/remove labels on an entire thread."""
    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    service.users().threads().modify(userId="me", id=thread_id, body=body).execute()


def delete_label(service, label_id):
    """Delete a label (does not delete messages)."""
    service.users().labels().delete(userId="me", id=label_id).execute()


# ── MIGRATION MAP ──
# Format: (old_label_name, new_label_name)
# Threads get new label applied, old label removed.

MIGRATION_MAP = [
    # AI Screening → AI/
    ("AI Screening - Urgent",  "AI/Screening-Urgent"),
    ("AI Screening - Review",  "AI/Screening-Review"),
    ("AI Screening - Hold",    "AI/Screening-Hold"),
    ("AI Screening - Routine", "AI/Screening-Routine"),

    # THUNDERBIRD → PIPELINE/
    ("THUNDERBIRD-Process",           "PIPELINE/Inbound"),
    ("THUNDERBIRD-Processed",         "PIPELINE/Processed"),
    ("THUNDERBIRD-Commander-Review",  "PIPELINE/Commander-Review"),
    ("THUNDERBIRD-SMS-Processed",     "PIPELINE/Processed"),

    # DANI → PIPELINE/
    ("DANI-Processed",  "PIPELINE/Processed"),

    # TITAN sub-labels → PIPELINE/ (collapse legacy)
    ("TITAN/Urgent",       "PIPELINE/Inbound"),
    ("TITAN/Command",      "PIPELINE/Commander-Review"),
    ("TITAN/Analyze",      "AI/Screening-Review"),
    ("TITAN/Draft-Reply",  "PIPELINE/Commander-Review"),
    ("TITAN/Intel",        "AI/Screening-Review"),
    ("TITAN/Log-Supplier", "D2M/Suppliers"),
    ("TITAN/Processed",    "PIPELINE/Processed"),

    # Cruise labels → D2M/Bookings/Active
    ("Spring 2026 Cruise", "D2M/Bookings/Active"),
    ("Summer 2027 cruise", "D2M/Bookings/Active"),

    # D2M/Current_Ops → D2M/Bookings/Active
    ("D2M/Current_Ops", "D2M/Bookings/Active"),

    # Personal
    ("USAFA 75 CS-24",             "PERSONAL/USAFA"),
    ("jbzsolutionsllc@gmail.com",  "PERSONAL/JBZ"),
]

# New labels to create even if no migration targets them
NEW_LABELS = [
    "D2M",
    "D2M/Clients",
    "D2M/Bookings/Active",
    "D2M/Bookings/Archive",
    "D2M/Suppliers",
    "D2M/Financial",
    "PIPELINE/Inbound",
    "PIPELINE/Commander-Review",
    "PIPELINE/Dani-Queue",
    "PIPELINE/Processed",
    "AI/Screening-Urgent",
    "AI/Screening-Review",
    "AI/Screening-Hold",
    "AI/Screening-Routine",
    "PERSONAL/USAFA",
    "PERSONAL/JBZ",
    "PERSONAL/Family",
]

# Old labels to delete AFTER migration (Phase 3 — requires --delete flag)
OLD_LABELS_TO_DELETE = [
    "AI Screening - Urgent",
    "AI Screening - Review",
    "AI Screening - Hold",
    "AI Screening - Routine",
    "THUNDERBIRD-Process",
    "THUNDERBIRD-Processed",
    "THUNDERBIRD-Commander-Review",
    "THUNDERBIRD-SMS-Processed",
    "DANI-Processed",
    "TITAN/Urgent",
    "TITAN/Command",
    "TITAN/Analyze",
    "TITAN/Draft-Reply",
    "TITAN/Intel",
    "TITAN/Log-Supplier",
    "TITAN/Processed",
    "TITAN",  # parent — delete last
    "Spring 2026 Cruise",
    "Summer 2027 cruise",
    "D2M/Current_Ops",
    # NOTE: "D2M" parent stays — it's the new parent too
    # NOTE: "USAFA 75 CS-24" and "jbzsolutionsllc@gmail.com" deleted after migration
    "USAFA 75 CS-24",
    "jbzsolutionsllc@gmail.com",
]


def main():
    delete_mode = "--delete" in sys.argv
    dry_run = "--dry-run" in sys.argv

    service = get_service()
    print("=" * 60)
    print("GMAIL LABEL REORGANIZATION — 17 MAR 2026")
    if dry_run:
        print("  *** DRY RUN — no changes will be made ***")
    print("=" * 60)

    # ── PHASE 1: Create new labels ──
    print("\n📁 PHASE 1: Creating new label hierarchy...")
    new_label_ids = {}
    for label_name in NEW_LABELS:
        if dry_run:
            print(f"  [DRY] Would create: {label_name}")
            continue
        label_id, created = get_or_create_label(service, label_name)
        new_label_ids[label_name] = label_id
        status = "✅ Created" if created else "  Exists"
        print(f"  {status}: {label_name} → {label_id}")

    if dry_run:
        print("\n  [DRY RUN] Skipping migration and deletion.")
        return

    # ── PHASE 2: Migrate threads ──
    print("\n🔄 PHASE 2: Migrating threads...")
    total_migrated = 0
    migration_report = []

    for old_name, new_name in MIGRATION_MAP:
        old_id = get_label_id(service, old_name)
        if old_id is None:
            print(f"  ⏭️  {old_name} — label not found, skipping")
            migration_report.append((old_name, new_name, 0, "not found"))
            continue

        new_id = new_label_ids.get(new_name)
        if new_id is None:
            # Might already exist from Phase 1 cache miss
            new_id = get_label_id(service, new_name)
        if new_id is None:
            print(f"  ⚠️  {new_name} — target label not found!")
            migration_report.append((old_name, new_name, 0, "target missing"))
            continue

        threads = get_threads_by_label(service, old_id)
        count = len(threads)
        if count == 0:
            print(f"  📭 {old_name} → {new_name}: 0 threads (empty)")
            migration_report.append((old_name, new_name, 0, "empty"))
            continue

        migrated = 0
        for thread in threads:
            try:
                modify_thread(service, thread["id"],
                              add_labels=[new_id],
                              remove_labels=[old_id])
                migrated += 1
            except Exception as e:
                print(f"    ⚠️ Thread {thread['id']}: {e}")

        total_migrated += migrated
        print(f"  ✅ {old_name} → {new_name}: {migrated}/{count} threads")
        migration_report.append((old_name, new_name, migrated, "done"))

    # ── PHASE 3: Delete old labels (only with --delete flag) ──
    if delete_mode:
        print("\n🗑️  PHASE 3: Deleting old labels...")
        deleted = 0
        for label_name in OLD_LABELS_TO_DELETE:
            label_id = get_label_id(service, label_name)
            if label_id is None:
                print(f"  ⏭️  {label_name} — already gone")
                continue
            # Safety check: any threads still on this label?
            remaining = get_threads_by_label(service, label_id, max_results=1)
            if remaining:
                print(f"  ⚠️  {label_name} — still has threads, skipping delete")
                continue
            try:
                delete_label(service, label_id)
                deleted += 1
                print(f"  ✅ Deleted: {label_name}")
            except Exception as e:
                print(f"  ⚠️  {label_name}: {e}")
        print(f"\n  Deleted {deleted} old labels.")
    else:
        print("\n📋 PHASE 3: Old label deletion SKIPPED")
        print("  Run with --delete flag after confirming migration is correct.")

    # ── REPORT ──
    print("\n" + "=" * 60)
    print("MIGRATION REPORT")
    print("=" * 60)
    print(f"{'Old Label':<35} {'New Label':<30} {'Threads':>8} {'Status'}")
    print("-" * 85)
    for old, new, count, status in migration_report:
        print(f"{old:<35} {new:<30} {count:>8} {status}")
    print("-" * 85)
    print(f"{'TOTAL':>65} {total_migrated:>8}")
    print(f"\nNew labels created: {sum(1 for _, created in [get_or_create_label(service, n) for n in []] if created)}")
    print(f"Old labels pending delete: {len(OLD_LABELS_TO_DELETE)}")
    print(f"\n✅ Done. Review in Gmail, then run with --delete to clean up old labels.")


if __name__ == "__main__":
    main()
