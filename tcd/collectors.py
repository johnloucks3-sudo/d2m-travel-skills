"""
collectors — gather the current TCD dataset and enrich every item into an Item.

Non-Gmail sources reuse the local, offline builders already in
scripts/tcd_data.py (strategic alerts / ELON proposals, operational tasks /
projects / alerts, reference standing-orders / dossiers) — the "repurpose, don't
rewrite" part of the plan.

Gmail is collected here (not via tcd_data.build_gmail) because the board needs
the RFC822 **Message-ID header** to build a working web permalink, which the
existing builder doesn't capture. This keeps the live tcd_server untouched.

Everything degrades gracefully with no credentials: the local builders read
on-disk Wing files, and the Gmail collector returns [] if auth/creds are
missing — so ``--dry-run`` works offline and still links every row.
"""
import sys
from email.utils import parsedate_to_datetime

from . import _imports
from .item_model import Item
from .permalink import derive_link, derive_source_path
from .staging import derive_stage, derive_status

# Two Gmail accounts, mirroring scripts/tcd_data.GMAIL_ACCOUNTS.
GMAIL_ACCOUNTS = [
    ("johnloucks3", "get_commander_gmail"),
    ("d2mconcierge", "get_persona_gmail"),
]


def _enrich(item: dict) -> Item:
    """Legacy tcd_data dict → fully-populated Item (link + stage + status)."""
    stage = derive_stage(item)
    return Item.from_legacy(
        item,
        link=derive_link(item),
        source_path=derive_source_path(item),
        stage=stage,
        status=derive_status(item, stage),
    )


def collect_local() -> list:
    """Strategic + operational + reference items from on-disk Wing state.

    Offline and credential-free. Returns a list of legacy item dicts.
    """
    td = _imports.load_tcd_data()
    state = td._load_json(td.HALE_STATE, {})
    return (
        td.build_strategic(state)
        + td.build_operational(state)
        + td.build_reference()
    )


def _header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def collect_gmail(max_per_account: int = 12) -> list:
    """Recent inbox messages from both Gmail accounts, WITH Message-ID headers.

    Returns legacy item dicts (same shape as tcd_data.build_gmail) plus a
    ``message_id_header`` field so a real permalink can be built. Any failure
    (missing module, missing/expired creds, API error) yields [] for that
    account — the sync still succeeds with the other sources.
    """
    try:
        gauth = _imports.load_google_auth()
    except Exception as e:
        print(f"tcd.collectors: google auth unavailable: {e}", file=sys.stderr)
        return []

    items = []
    for account, getter_name in GMAIL_ACCOUNTS:
        try:
            svc = getattr(gauth, getter_name)()
            listing = svc.users().messages().list(
                userId="me", labelIds=["INBOX"],
                maxResults=max_per_account, q="newer_than:14d",
            ).execute()
            for meta in listing.get("messages", []):
                msg = svc.users().messages().get(
                    userId="me", id=meta["id"], format="full").execute()
                headers = msg.get("payload", {}).get("headers", [])
                subject = _header(headers, "Subject") or "(no subject)"
                sender = _header(headers, "From")
                message_id_header = _header(headers, "Message-ID")
                try:
                    date_iso = parsedate_to_datetime(
                        _header(headers, "Date")).date().isoformat()
                except Exception:
                    date_iso = ""
                snippet = msg.get("snippet", "")
                unread = "UNREAD" in (msg.get("labelIds") or [])
                items.append({
                    "id": f"gmail-{account}-{meta['id']}",
                    "inbox": "operational", "folder": "o-inbox", "type": "email",
                    "priority": "p2" if unread else "routine", "unread": unread,
                    "title": subject, "from": f"{sender} → {account}",
                    "date": date_iso, "snippet": snippet, "body": snippet,
                    "tags": ["gmail", account], "comments": [],
                    "message_id_header": message_id_header,
                })
        except Exception as e:
            print(f"tcd.collectors: gmail fetch failed for {account}: {e}",
                  file=sys.stderr)
    return items


def collect_all(include_gmail: bool = True) -> list:
    """All sources → list[Item], each with a non-empty source deep-link."""
    raw = list(collect_local())
    if include_gmail:
        raw = collect_gmail() + raw
    return [_enrich(item) for item in raw]
