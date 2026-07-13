"""
item_model — the row schema for the Google Sheet data plane.

One ``Item`` == one row on the AppSheet board. Column order/types are chosen so
AppSheet's "create app from existing data" auto-generates a clean app:
  - ``id`` is first (AppSheet uses the first column as the key by default).
  - ``link`` is a URL column (AppSheet renders URL-typed columns as clickable).
  - ``stage`` drives the P-D-T-A-C pills; ``status`` drives dispose/write-back.
"""
from dataclasses import dataclass, field
import json

# Exact header row written to the Sheet, in order. Keep in sync with Item.to_row.
SHEET_COLUMNS = [
    "id",         # key (stable across syncs)
    "inbox",      # strategic | operational | reference
    "type",       # decision | paper | brief | email
    "priority",   # p0 | p1 | p2 | routine
    "stage",      # P | D | T | A | C | REF  (P-D-T-A-C pill)
    "title",
    "from",       # sender / origin
    "date",
    "snippet",
    "body",
    "link",       # URL column — deep-link to source (requirement #1)
    "sourcePath", # human-readable foundation pointer
    "comments",   # serialized; write-back appends here (Phase 2)
    "status",     # Open | Reference | Closed | Delete (Commander-facing plain English)
    "owner",      # staff seat (Hale/Dani/Sterling/Dembe/Harlan) — set on D -> T auto-task
]


def _flatten_comments(comments) -> str:
    """Legacy items carry comments as a list; the Sheet stores a compact string."""
    if not comments:
        return ""
    if isinstance(comments, str):
        return comments
    try:
        return json.dumps(comments, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(comments)


@dataclass
class Item:
    id: str
    inbox: str
    type: str
    priority: str
    stage: str
    title: str
    source: str          # maps to the "from" column ("from" is a py keyword)
    date: str
    snippet: str
    body: str
    link: str
    sourcePath: str
    comments: str = ""
    status: str = "Open"
    owner: str = ""

    @classmethod
    def from_legacy(cls, item: dict, *, link: str, source_path: str,
                    stage: str, status: str, owner: str = "") -> "Item":
        """Build from a scripts/tcd_data.py item dict plus the enrichment fields."""
        return cls(
            id=item.get("id", ""),
            inbox=item.get("inbox", ""),
            type=item.get("type", ""),
            priority=item.get("priority", ""),
            stage=stage,
            title=item.get("title", ""),
            source=item.get("from", ""),
            date=item.get("date", ""),
            snippet=item.get("snippet", ""),
            body=item.get("body", ""),
            link=link,
            sourcePath=source_path,
            comments=_flatten_comments(item.get("comments")),
            status=status,
            owner=owner,
        )

    def to_row(self) -> list:
        """Values aligned to SHEET_COLUMNS (order-locked)."""
        return [
            self.id, self.inbox, self.type, self.priority, self.stage,
            self.title, self.source, self.date, self.snippet, self.body,
            self.link, self.sourcePath, self.comments, self.status, self.owner,
        ]

    def to_dict(self) -> dict:
        """SHEET_COLUMNS-keyed dict (used by --dry-run JSON output)."""
        return dict(zip(SHEET_COLUMNS, self.to_row()))
