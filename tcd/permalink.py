"""
permalink — build real source deep-links for every TCD item.

Requirement #1 (the Commander's loudest complaint): every row on the board must
link to where the item actually lives. These are pure functions — no creds, no
network — so they unit-test offline and can be verified before any live sync.

Link precedence by source (see ``derive_link``):
  Gmail    → web permalink built from the RFC822 Message-ID header
             (the Gmail API message.id is NOT the id in the web URL — using it
             gives dead links, so we search by rfc822msgid instead).
  Calendar → the event's htmlLink (Google already returns a canonical URL).
  Drive    → the file's webViewLink.
  On-disk  → a Drive search deep-link on the item's name/client, so a dossier /
  (SO,      standing-order / alert / task resolves to its file(s) in the owner's
   dossier, Drive. Always constructible without creds and never 404s to a blank
   alert…)  page the way a guessed file id would.
"""
import re
from urllib.parse import quote

GMAIL_BASE = "https://mail.google.com/mail/u/0/#search/"
DRIVE_SEARCH_BASE = "https://drive.google.com/drive/search?q="


def _is_degenerate(text: str) -> bool:
    """True if ``text`` has no alphanumerics to search on (e.g. a '---' title)."""
    return not re.search(r"[A-Za-z0-9]", text or "")


def _humanize_stem(stem: str) -> str:
    """Turn a filename stem into a readable Drive query.

    'DOSSIER_DoorCounty_SisterBay_Sep2026' → 'DoorCounty SisterBay Sep2026'.
    """
    s = re.sub(r"^(DOSSIER_|SO_)", "", stem or "")
    s = re.sub(r"[_-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def gmail_permalink(message_id_header: str) -> str:
    """Web permalink to a specific Gmail message via its RFC822 Message-ID.

    ``message_id_header`` is the value of the message's ``Message-ID`` header
    (e.g. ``<abc123@mail.example.com>``). Angle brackets are stripped; the id is
    URL-quoted. Returns "" if no usable id is given (caller falls back).
    """
    mid = (message_id_header or "").strip().strip("<>").strip()
    if not mid:
        return ""
    return f"{GMAIL_BASE}rfc822msgid:{quote(mid, safe='')}"


def gmail_search_link(query: str) -> str:
    """Fallback Gmail deep-link: a search (e.g. by subject) when no Message-ID."""
    q = (query or "").strip()
    if not q:
        return ""
    return f"{GMAIL_BASE}{quote(q, safe='')}"


def drive_search_link(query: str) -> str:
    """Deep-link into the owner's Drive, filtered to ``query`` (name/client)."""
    q = (query or "").strip()
    if not q:
        return ""
    return f"{DRIVE_SEARCH_BASE}{quote(q, safe='')}"


def first_nonempty(*candidates: str) -> str:
    """First non-empty, stripped string from ``candidates`` (else "")."""
    for c in candidates:
        if c and c.strip():
            return c.strip()
    return ""


def derive_link(item: dict) -> str:
    """Best source deep-link for a legacy tcd_data item dict.

    Guarantees a non-empty link for any item that has at least a title, so every
    board row is clickable. Precedence follows the module docstring; on-disk and
    internal (hale_state) items resolve to a Drive search on their most specific
    identifier.
    """
    fid = item.get("id", "") or ""

    # Google-native sources already carry canonical URLs / ids.
    if fid.startswith("gmail-"):
        permalink = gmail_permalink(item.get("message_id_header", ""))
        return first_nonempty(permalink, gmail_search_link(item.get("title", "")))
    if item.get("htmlLink"):
        return item["htmlLink"]                 # Calendar
    if item.get("webViewLink"):
        return item["webViewLink"]              # Drive

    # On-disk / internal items → Drive search on their most specific name.
    client = ""
    for tag in item.get("tags", []) or []:
        if tag and tag not in ("standing-order", "dossier", "deferred-alert",
                               "gmail", "ELON", "verification"):
            client = tag
            break
    # Titles can be degenerate (e.g. a dossier whose first line is the YAML
    # '---' delimiter), so drop those and fall back to the humanized filename
    # stem — which is always meaningful — before the raw id.
    title = item.get("title", "")
    if _is_degenerate(title):
        title = ""
    stem = fid.split("-", 1)[1] if "-" in fid else fid
    query = first_nonempty(client, title, _humanize_stem(stem), fid)
    return drive_search_link(query)


def derive_source_path(item: dict) -> str:
    """Human-readable pointer to the item's foundation record (for the Sheet).

    Mirrors the mapping in scripts/tcd_data.py:delete_item so the board shows
    where a row really comes from and Phase 2 write-back knows what to act on.
    """
    fid = item.get("id", "") or ""
    if fid.startswith("gmail-"):
        return f"gmail:{fid[len('gmail-'):]}"
    if fid.startswith("so-"):
        return f"standing_orders/{fid[len('so-'):]}.md"
    if fid.startswith("dossier-"):
        return f"dossiers/{fid[len('dossier-'):]}.md"
    if fid.startswith("alert-"):
        return "hale_state.json:deferred_alerts"
    if fid.startswith("task-"):
        return "hale_state.json:open_tasks"
    if fid.startswith("proj-"):
        return "hale_state.json:project_tracking.active_projects"
    if fid.startswith("elon-"):
        return "hale_state.json:elon_proposals"
    return ""
