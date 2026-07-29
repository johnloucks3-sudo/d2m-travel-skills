"""
collectors — gather the current TCD dataset and enrich every item into an Item.

Non-Gmail sources reuse the local, offline builders already in
scripts/tcd_data.py (strategic alerts / ELON proposals, operational tasks /
projects / alerts, reference standing-orders / dossiers) — the "repurpose, don't
rewrite" part of the plan.

Gmail is collected here (not via tcd_data.build_gmail) because the board needs
the RFC822 **Message-ID header** to build a working web permalink, which the
existing builder doesn't capture. This keeps the data-plane builders untouched.

Everything degrades gracefully with no credentials: the local builders read
on-disk Wing files, and the Gmail collector returns [] if auth/creds are
missing — so ``--dry-run`` works offline and still links every row.
"""
import sys
from email.utils import parsedate_to_datetime

from . import _imports
from . import overrides as _overrides
from . import watchdog
from .item_model import Item
from .permalink import derive_link, derive_source_path
from .staging import derive_stage, derive_status

# Two Gmail accounts, mirroring scripts/tcd_data.GMAIL_ACCOUNTS.
GMAIL_ACCOUNTS = [
    ("johnloucks3", "get_commander_gmail"),
    ("d2mconcierge", "get_persona_gmail"),
]


def _enrich(item: dict, overrides: dict = None) -> Item:
    """Legacy tcd_data dict → fully-populated Item (link + stage + status).

    ``overrides`` (id -> {"stage", "owner"}) is applied on top of the freshly
    derived stage so a Commander's Approve or a manual stage move survives
    the next full sync instead of being silently recomputed back to "P" —
    see tcd/overrides.py for why this exists.
    """
    overrides = overrides if overrides is not None else {}
    item_id = item.get("id", "")
    stage = _overrides.apply_override(item_id, derive_stage(item), overrides)
    status = _overrides.apply_status(item_id, derive_status(item, stage), overrides)
    return Item.from_legacy(
        item,
        link=derive_link(item),
        source_path=derive_source_path(item),
        stage=stage,
        status=status,
        owner=_overrides.apply_owner(item_id, overrides),
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
        + td.build_missions(state)
        + td.build_reference()
        + watchdog.collect_watchdog()
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


def collect_gmail_drafts(max_per_account: int = 100) -> list:
    """Recent drafts from both Gmail accounts, paginated via pageToken."""
    try:
        gauth = _imports.load_google_auth()
    except Exception as e:
        print(f"tcd.collectors: google auth unavailable: {e}", file=sys.stderr)
        return []

    items = []
    for account, getter_name in GMAIL_ACCOUNTS:
        try:
            svc = getattr(gauth, getter_name)()
            drafts = []
            page_token = None
            while True:
                res = svc.users().drafts().list(
                    userId="me", pageToken=page_token
                ).execute()
                drafts.extend(res.get("drafts", []))
                page_token = res.get("nextPageToken")
                if not page_token or len(drafts) >= max_per_account:
                    break
            
            for d in drafts[:max_per_account]:
                try:
                    full_d = svc.users().drafts().get(userId="me", id=d["id"], format="full").execute()
                    msg = full_d.get("message", {})
                    headers = msg.get("payload", {}).get("headers", [])
                    subject = _header(headers, "Subject") or "(no subject)"
                    to = _header(headers, "To") or "unknown recipient"
                    message_id = _header(headers, "Message-ID")
                    try:
                        date_iso = parsedate_to_datetime(_header(headers, "Date")).date().isoformat()
                    except Exception:
                        date_iso = ""
                    snippet = msg.get("snippet", "")
                    items.append({
                        "id": f"draft-{account}-{d['id']}",
                        "inbox": "operational", "folder": "o-inbox", "type": "decision",
                        "priority": "p1", "unread": True,
                        "title": subject, "from": to,
                        "date": date_iso, "snippet": snippet, "body": snippet,
                        "tags": ["draft", account], "comments": [],
                        "message_id_header": message_id,
                    })
                except Exception as e:
                    print(f"Failed to fetch draft {d['id']}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"tcd.collectors: gmail drafts fetch failed for {account}: {e}", file=sys.stderr)
    return items


def collect_keep(max_results: int = 30) -> list:
    """Recent Google Keep notes as legacy item dicts, feeding Reference.

    Reuses the existing gkeepapi/master-token integration in
    api/thunderbird_keep.py (Commander decision: no Workspace/service-account
    needed — the consumer-account path already wired is sufficient). Returns
    [] on any auth/connectivity failure so the sync still succeeds with the
    other sources.

    SECURITY: title-only, NEVER the note body/text. The Commander uses Keep
    to store credentials (API keys, SSH private keys, access tokens) — a
    live incident on 2026-07-12 confirmed raw secrets were being copied into
    the Sheet via this collector before this fix. A per-title keyword filter
    is NOT sufficient (a secret can sit in a note with an innocuous title);
    the only safe rule is "never duplicate Keep's freeform content into a
    less-protected store, period." The link (keep_permalink) already gets
    you to the real note in Keep itself, where it belongs.
    """
    try:
        keep_mod = _imports.load_keep()
        result = keep_mod.list_notes(max_results=max_results)
    except Exception as e:
        print(f"tcd.collectors: keep unavailable: {e}", file=sys.stderr)
        return []

    items = []
    for note in result.get("notes", []):
        note_id = note.get("id", "")
        if not note_id:
            continue
        title = note.get("title") or "(untitled note)"
        placeholder = "(Keep note — open via link to view content; not mirrored here for security)"
        items.append({
            "id": f"keep-{note_id}", "inbox": "reference", "folder": "r-inbox",
            "type": "note", "priority": "p2" if note.get("pinned") else "routine",
            "unread": False, "title": title, "from": "Google Keep", "date": "",
            "snippet": placeholder, "body": placeholder,
            "tags": ["keep"] + (["pinned"] if note.get("pinned") else []),
            "comments": [],
        })
    return items


def collect_sms(limit: int = 30) -> list:
    """Recent inbound SMS (Android gateway) as legacy item dicts, feeding
    Operational. Soft-fails to [] if the gateway isn't configured yet
    (docs/TCD_ANDROID_SMS_SETUP.md) or unreachable — same fail-soft contract
    as Gmail/Keep so a missing/offline phone never breaks the sync."""
    try:
        sms_mod = _imports.load_sms_gateway()
        messages = sms_mod.poll_inbox(limit=limit)
    except Exception as e:
        print(f"tcd.collectors: sms gateway unavailable: {e}", file=sys.stderr)
        return []

    items = []
    for m in messages:
        msg_id = m.get("id", "")
        if not msg_id:
            continue
        text = m.get("text", "")
        sender = m.get("sender", "unknown")
        items.append({
            "id": f"sms-{msg_id}", "inbox": "operational", "folder": "o-inbox",
            "type": "email", "priority": "p2", "unread": True,
            "title": f"SMS from {sender}", "from": sender,
            "date": (m.get("receivedAt", "") or "")[:10],
            "snippet": text[:220], "body": text,
            "tags": ["sms", sender], "comments": [],
        })
    return items


def collect_all(include_gmail: bool = True, include_keep: bool = True,
                include_sms: bool = True) -> list:
    """All sources → list[Item], each with a non-empty source deep-link."""
    raw = list(collect_local())
    if include_gmail:
        raw = collect_gmail() + collect_gmail_drafts() + raw
    if include_keep:
        raw = raw + collect_keep()
    if include_sms:
        raw = raw + collect_sms()
    overrides = _overrides.load_overrides()
    return [_enrich(item, overrides) for item in raw]
