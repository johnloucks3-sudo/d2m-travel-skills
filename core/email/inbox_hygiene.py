"""
Thunderbird Inbox Hygiene
=========================
Keeps both johnloucks3 and d2mconcierge inboxes clean.

Protocol (per Commander directive 2026-05-30):
  1. Find Label_102 (ForDeletion) items → trash them
  2. Find known clutter patterns → label + trash
  3. Auto-delete handled by Gmail 30-day trash policy

Run via timer: inbox-hygiene.timer (every 30 min)
"""

import logging
import socket
import sys
from datetime import datetime
from pathlib import Path

socket.setdefaulttimeout(10)  # 30s × 3 simultaneous timeouts > 120s TimeoutStartSec; 10s is still generous for Gmail API

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
LOG_FILE = THUNDERBIRD / "logs" / "inbox_hygiene.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

JOHNLOUCKS3_TOKEN = THUNDERBIRD / "gmail_token.json"
D2MCONCIERGE_TOKEN = THUNDERBIRD / "config" / "persona_gmail_token.json"

# FIXED 2026-07-16 (hot-window triage, same root cause as
# scripts/d2m_inbox_triage.py): "Label_102" is a stale/deleted label ID --
# confirmed gone via a live labels().list() call. This constant was also
# used directly inside a `label:` SEARCH query, which matches Gmail's
# visible label NAME, not its internal ID string, so this was doubly wrong:
# even before the label was deleted, `label:Label_102` likely never matched
# the intended "ForDeletion" label by name. Fixed to search by name.
LABEL_FOR_DELETION = "ForDeletion"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HYGIENE] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Clutter rules per account ─────────────────────────────────────────────────
# Each rule: (label, gmail_query)
# Query matches messages to trash. 'in:inbox' appended automatically.

JOHNLOUCKS3_CLUTTER = [
    # Wing auto-generated system noise
    ("Wing preflight checks",       'subject:"D2M YELLOW" subject:"Preflight"'),
    ("Wing preflight checks",       'subject:"D2M GREEN" subject:"Preflight"'),
    ("Wing preflight checks",       'subject:"D2M RED" subject:"Preflight"'),
    ("Duplicate daily briefs",      'subject:"Thunderbird Brief" older_than:1d'),
    ("Duplicate daily briefs",      'subject:"THUNDERBIRD BRIEFING" older_than:1d'),
    ("Duplicate daily briefs",      'subject:"HALE — DAILY BRIEF" older_than:1d'),
    ("Duplicate daily briefs",      'subject:"THUNDERBIRD MORNING BRIEFING" older_than:1d'),
    # REMOVED 2026-06-08 (Commander directive): "Own reply loop guard" rule was
    # auto-trashing every legitimate "Task completed by Hale" reply. The original
    # Padre loop is now blocked at the source in run_commander_directive_sweep.py
    # (sweep no longer re-fires on its own receipts), so this rule is unnecessary
    # and was causing the Wing's actual responses to disappear into trash.
]

D2MCONCIERGE_CLUTTER = [
    # Sent replies older than 7 days that are just notification echoes
    ("Old task-complete replies",   'from:d2mconcierge@gmail.com "Task completed by Ms. Victoria" older_than:7d'),
    # System preflight noise landing in d2mconcierge
    ("Preflight noise",             'subject:"D2M YELLOW" subject:"Preflight"'),
    ("Preflight noise",             'subject:"D2M GREEN" subject:"Preflight"'),
]


# ── Gmail helpers ─────────────────────────────────────────────────────────────

def _get_service(token_path: Path):
    if not token_path.exists():
        log.warning(f"Token not found: {token_path}")
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        log.error(f"Auth failed for {token_path.name}: {e}")
        return None


def _find_messages(svc, query: str, max_results: int = 200) -> list:
    ids = []
    page_token = None
    while True:
        kwargs = dict(userId="me", q=query, maxResults=max_results)
        if page_token:
            kwargs["pageToken"] = page_token
        try:
            resp = svc.users().messages().list(**kwargs).execute()
        except Exception as e:
            log.error(f"List failed for query '{query[:60]}': {e}")
            break
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token or len(ids) >= max_results:
            break
    return ids


def _trash_messages(svc, msg_ids: list, account_label: str) -> int:
    trashed = 0
    for msg_id in msg_ids:
        try:
            svc.users().messages().trash(userId="me", id=msg_id).execute()
            trashed += 1
        except Exception as e:
            log.warning(f"  [{account_label}] trash failed {msg_id}: {e}")
    return trashed


def _sweep_label_102(svc, account_label: str) -> int:
    """Move all Label_102 (ForDeletion) messages to trash."""
    ids = _find_messages(svc, f"label:{LABEL_FOR_DELETION} -in:trash")
    if not ids:
        return 0
    log.info(f"[{account_label}] Label_102: {len(ids)} messages → trash")
    return _trash_messages(svc, ids, account_label)


def _sweep_clutter(svc, rules: list, account_label: str) -> int:
    """Apply clutter rules: find → trash."""
    total = 0
    for label, query in rules:
        # Always restrict to inbox (not already trashed/archived)
        full_query = f"{query} in:inbox"
        ids = _find_messages(svc, full_query)
        if not ids:
            continue
        log.info(f"[{account_label}] {label}: {len(ids)} → trash")
        total += _trash_messages(svc, ids, account_label)
    return total


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    log.info(f"=== Inbox Hygiene Run — {datetime.now().strftime('%Y-%m-%d %H:%M MT')} ===")
    total = 0

    # johnloucks3
    svc_jl = _get_service(JOHNLOUCKS3_TOKEN)
    if svc_jl:
        total += _sweep_label_102(svc_jl, "johnloucks3")
        total += _sweep_clutter(svc_jl, JOHNLOUCKS3_CLUTTER, "johnloucks3")
    else:
        log.warning("johnloucks3 service unavailable — skipping")

    # d2mconcierge
    svc_d2m = _get_service(D2MCONCIERGE_TOKEN)
    if svc_d2m:
        total += _sweep_label_102(svc_d2m, "d2mconcierge")
        total += _sweep_clutter(svc_d2m, D2MCONCIERGE_CLUTTER, "d2mconcierge")
    else:
        log.warning("d2mconcierge service unavailable — skipping")

    log.info(f"=== Done. {total} messages trashed. ===")
    return svc_jl, svc_d2m, total


if __name__ == "__main__":
    _jl, _d2m, _total = run()
    if _jl is None and _d2m is None:
        log.error("Both accounts unavailable — exiting 1")
        sys.exit(1)
    sys.exit(0)
