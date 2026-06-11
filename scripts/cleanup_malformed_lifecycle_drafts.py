#!/usr/bin/env python3
"""
cleanup_malformed_lifecycle_drafts.py — staged 2026-06-10 (Sterling/A7).

The d2m-lifecycle-scheduler duplicate-draft loop (fixed this session: it read the
wrong result key, never recorded sent, and re-created a draft every run) left a pile
of MALFORMED drafts in d2mconcierge — no Subject AND no To header. As of the audit:
  320 total drafts | 27 legit (subject+recipient) | 293 malformed junk.

This tool deletes ONLY malformed drafts (missing BOTH subject and recipient). Legit
WF-17 drafts (have a subject and a To) are never touched.

DESTRUCTIVE — default is DRY-RUN. Requires --execute to actually delete.
Run:
  python3 scripts/cleanup_malformed_lifecycle_drafts.py            # dry-run, lists count
  python3 scripts/cleanup_malformed_lifecycle_drafts.py --execute  # delete malformed
"""
import sys
import argparse

sys.path.insert(0, "/home/john/Thunderbird")
from core.email.thunderbird_gmail import _get_wing_gmail_service


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="actually delete (default: dry-run)")
    args = ap.parse_args()

    svc = _get_wing_gmail_service()
    drafts = svc.users().drafts().list(userId="me", maxResults=500).execute().get("drafts", [])

    malformed = []
    for d in drafts:
        dd = svc.users().drafts().get(userId="me", id=d["id"], format="metadata").execute()
        hdrs = dd.get("message", {}).get("payload", {}).get("headers", [])
        sub = next((h["value"] for h in hdrs if h["name"] == "Subject"), "")
        to = next((h["value"] for h in hdrs if h["name"] == "To"), "")
        if not sub and not to:
            malformed.append(d["id"])

    print(f"Total drafts: {len(drafts)} | malformed (no subject AND no recipient): {len(malformed)}")
    if not args.execute:
        print("DRY-RUN — no drafts deleted. Re-run with --execute to delete the malformed pile.")
        return 0

    deleted = 0
    for did in malformed:
        try:
            svc.users().drafts().delete(userId="me", id=did).execute()
            deleted += 1
        except Exception as e:
            print(f"  failed to delete {did}: {e}")
    print(f"Deleted {deleted} malformed drafts. Legit WF-17 drafts untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
