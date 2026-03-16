"""
Thunderbird Google Keep Module
===============================

Integrates Google Keep for quick-reference notes and checklists.
Uses gkeepapi (unofficial reverse-engineered library).

Auth: Google email + App Password (generate at myaccount.google.com/apppasswords)
Token cached at ~/Thunderbird/keep_token.json after first login.

Tools:
  - keep_create_note: Create a text note or checklist
  - keep_search_notes: Search notes by text
  - keep_list_notes: List recent notes
  - keep_update_note: Update an existing note
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional, List

import gkeepapi

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
KEEP_TOKEN_FILE = THUNDERBIRD_DIR / "keep_token.json"
KEEP_CREDS_FILE = THUNDERBIRD_DIR / "keep_credentials.json"

# Cached Keep instance
_keep_instance = None


def _get_keep() -> gkeepapi.Keep:
    """Get authenticated Keep instance. Uses cached token if available."""
    global _keep_instance
    if _keep_instance is not None:
        return _keep_instance

    keep = gkeepapi.Keep()

    if not KEEP_CREDS_FILE.exists():
        raise RuntimeError(
            f"Keep credentials not found: {KEEP_CREDS_FILE}\n"
            f"Run the EmbeddedSetup flow — see thunderbird_keep.py docstring."
        )

    creds = json.loads(KEEP_CREDS_FILE.read_text())
    email = creds["email"]
    master_token = creds["master_token"]

    try:
        keep.authenticate(email, master_token)
        logger.info(f"Keep: authenticated as {email}")
    except Exception as e:
        raise RuntimeError(f"Keep auth failed: {e}")

    _keep_instance = keep
    return keep


def create_note(title: str, body: str = "", labels: Optional[List[str]] = None,
                pinned: bool = False, color: str = "WHITE") -> dict:
    """Create a text note in Google Keep."""
    keep = _get_keep()

    note = keep.createNote(title, body)

    if pinned:
        note.pinned = True

    # Set color
    color_map = {
        "WHITE": gkeepapi.node.ColorValue.White,
        "RED": gkeepapi.node.ColorValue.Red,
        "ORANGE": gkeepapi.node.ColorValue.Orange,
        "YELLOW": gkeepapi.node.ColorValue.Yellow,
        "GREEN": gkeepapi.node.ColorValue.Green,
        "TEAL": gkeepapi.node.ColorValue.Teal,
        "BLUE": gkeepapi.node.ColorValue.Blue,
        "PURPLE": gkeepapi.node.ColorValue.Purple,
        "PINK": gkeepapi.node.ColorValue.Pink,
        "BROWN": gkeepapi.node.ColorValue.Brown,
        "GRAY": gkeepapi.node.ColorValue.Gray,
    }
    if color.upper() in color_map:
        note.color = color_map[color.upper()]

    # Apply labels
    if labels:
        keep_labels = keep.labels()
        for label_name in labels:
            label = next((l for l in keep_labels if l.name.lower() == label_name.lower()), None)
            if label is None:
                label = keep.createLabel(label_name)
            note.labels.add(label)

    keep.sync()

    return {
        "status": "success",
        "action": "note_created",
        "id": note.id,
        "title": title,
        "pinned": pinned,
        "color": color,
    }


def create_checklist(title: str, items: List[str], labels: Optional[List[str]] = None,
                     pinned: bool = False, color: str = "WHITE") -> dict:
    """Create a checklist note in Google Keep."""
    keep = _get_keep()

    note = keep.createList(title, [(item, False) for item in items])

    if pinned:
        note.pinned = True

    color_map = {
        "WHITE": gkeepapi.node.ColorValue.White,
        "RED": gkeepapi.node.ColorValue.Red,
        "ORANGE": gkeepapi.node.ColorValue.Orange,
        "YELLOW": gkeepapi.node.ColorValue.Yellow,
        "GREEN": gkeepapi.node.ColorValue.Green,
        "TEAL": gkeepapi.node.ColorValue.Teal,
        "BLUE": gkeepapi.node.ColorValue.Blue,
        "PURPLE": gkeepapi.node.ColorValue.Purple,
        "PINK": gkeepapi.node.ColorValue.Pink,
        "BROWN": gkeepapi.node.ColorValue.Brown,
        "GRAY": gkeepapi.node.ColorValue.Gray,
    }
    if color.upper() in color_map:
        note.color = color_map[color.upper()]

    if labels:
        keep_labels = keep.labels()
        for label_name in labels:
            label = next((l for l in keep_labels if l.name.lower() == label_name.lower()), None)
            if label is None:
                label = keep.createLabel(label_name)
            note.labels.add(label)

    keep.sync()

    return {
        "status": "success",
        "action": "checklist_created",
        "id": note.id,
        "title": title,
        "items": len(items),
        "pinned": pinned,
        "color": color,
    }


def search_notes(query: str, max_results: int = 10) -> dict:
    """Search Keep notes by text content."""
    keep = _get_keep()
    keep.sync()

    results = []
    for note in keep.find(query=query):
        if note.trashed:
            continue
        results.append({
            "id": note.id,
            "title": note.title,
            "text": note.text[:500] if hasattr(note, 'text') else "",
            "pinned": note.pinned,
            "color": str(note.color) if note.color else "WHITE",
            "type": "list" if isinstance(note, gkeepapi.node.List) else "note",
        })
        if len(results) >= max_results:
            break

    return {"status": "success", "query": query, "count": len(results), "notes": results}


def list_notes(max_results: int = 15, pinned_only: bool = False) -> dict:
    """List recent Keep notes."""
    keep = _get_keep()
    keep.sync()

    results = []
    for note in keep.all():
        if note.trashed:
            continue
        if pinned_only and not note.pinned:
            continue
        results.append({
            "id": note.id,
            "title": note.title,
            "text": note.text[:300] if hasattr(note, 'text') else "",
            "pinned": note.pinned,
            "color": str(note.color) if note.color else "WHITE",
            "type": "list" if isinstance(note, gkeepapi.node.List) else "note",
        })
        if len(results) >= max_results:
            break

    return {"status": "success", "count": len(results), "notes": results}


def update_note(note_id: str, title: Optional[str] = None, body: Optional[str] = None,
                pinned: Optional[bool] = None, color: Optional[str] = None) -> dict:
    """Update an existing Keep note."""
    keep = _get_keep()
    keep.sync()

    note = keep.get(note_id)
    if note is None:
        return {"status": "error", "message": f"Note not found: {note_id}"}

    if title is not None:
        note.title = title
    if body is not None:
        note.text = body
    if pinned is not None:
        note.pinned = pinned
    if color is not None:
        color_map = {
            "WHITE": gkeepapi.node.ColorValue.White,
            "RED": gkeepapi.node.ColorValue.Red,
            "ORANGE": gkeepapi.node.ColorValue.Orange,
            "YELLOW": gkeepapi.node.ColorValue.Yellow,
            "GREEN": gkeepapi.node.ColorValue.Green,
            "TEAL": gkeepapi.node.ColorValue.Teal,
            "BLUE": gkeepapi.node.ColorValue.Blue,
            "PURPLE": gkeepapi.node.ColorValue.Purple,
            "PINK": gkeepapi.node.ColorValue.Pink,
            "BROWN": gkeepapi.node.ColorValue.Brown,
            "GRAY": gkeepapi.node.ColorValue.Gray,
        }
        if color.upper() in color_map:
            note.color = color_map[color.upper()]

    keep.sync()

    return {
        "status": "success",
        "action": "note_updated",
        "id": note_id,
        "title": note.title,
    }


def register_keep_tools(mcp_server):
    """Register Google Keep MCP tools."""
    from pydantic import Field

    @mcp_server.tool(
        name="keep_create_note",
        annotations={"title": "Create Google Keep Note", "readOnlyHint": False},
    )
    async def keep_create_note_tool(
        title: str = Field(..., description="Note title"),
        body: str = Field("", description="Note body text"),
        labels: Optional[str] = Field(None, description="Comma-separated label names (created if missing)"),
        pinned: bool = Field(False, description="Pin the note to top"),
        color: str = Field("WHITE", description="Note color: WHITE, RED, ORANGE, YELLOW, GREEN, TEAL, BLUE, PURPLE, PINK, BROWN, GRAY"),
    ) -> str:
        """Create a text note in Google Keep."""
        try:
            label_list = [l.strip() for l in labels.split(",")] if labels else None
            result = create_note(title, body, label_list, pinned, color)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "keep_error"})

    @mcp_server.tool(
        name="keep_create_checklist",
        annotations={"title": "Create Google Keep Checklist", "readOnlyHint": False},
    )
    async def keep_create_checklist_tool(
        title: str = Field(..., description="Checklist title"),
        items: str = Field(..., description="Checklist items, one per line (newline-separated)"),
        labels: Optional[str] = Field(None, description="Comma-separated label names"),
        pinned: bool = Field(False, description="Pin to top"),
        color: str = Field("WHITE", description="Note color"),
    ) -> str:
        """Create a checklist in Google Keep."""
        try:
            item_list = [i.strip() for i in items.strip().split("\n") if i.strip()]
            label_list = [l.strip() for l in labels.split(",")] if labels else None
            result = create_checklist(title, item_list, label_list, pinned, color)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "keep_error"})

    @mcp_server.tool(
        name="keep_search_notes",
        annotations={"title": "Search Google Keep Notes", "readOnlyHint": True},
    )
    async def keep_search_notes_tool(
        query: str = Field(..., description="Search text"),
        max_results: int = Field(10, description="Max notes to return"),
    ) -> str:
        """Search Google Keep notes by text content."""
        try:
            result = search_notes(query, max_results)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "keep_error"})

    @mcp_server.tool(
        name="keep_list_notes",
        annotations={"title": "List Google Keep Notes", "readOnlyHint": True},
    )
    async def keep_list_notes_tool(
        max_results: int = Field(15, description="Max notes to return"),
        pinned_only: bool = Field(False, description="Only show pinned notes"),
    ) -> str:
        """List recent Google Keep notes."""
        try:
            result = list_notes(max_results, pinned_only)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "keep_error"})

    @mcp_server.tool(
        name="keep_update_note",
        annotations={"title": "Update Google Keep Note", "readOnlyHint": False},
    )
    async def keep_update_note_tool(
        note_id: str = Field(..., description="Keep note ID (from search/list results)"),
        title: Optional[str] = Field(None, description="New title (or omit to keep current)"),
        body: Optional[str] = Field(None, description="New body text (or omit to keep current)"),
        pinned: Optional[bool] = Field(None, description="Pin/unpin"),
        color: Optional[str] = Field(None, description="New color"),
    ) -> str:
        """Update an existing Google Keep note."""
        try:
            result = update_note(note_id, title, body, pinned, color)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "keep_error"})

    logger.info("Google Keep tools registered (create_note, create_checklist, search, list, update)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if "--test" in sys.argv:
        print("Testing Keep connection...")
        try:
            keep = _get_keep()
            print(f"Authenticated. Syncing...")
            keep.sync()
            notes = list(keep.all())
            print(f"Found {len(notes)} notes in Keep.")
            for n in notes[:5]:
                print(f"  - {n.title[:50]}")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("Usage:")
        print("  python3 thunderbird_keep.py --test    # Test Keep connection")
        print()
        print("Setup:")
        print(f"  1. Generate App Password: https://myaccount.google.com/apppasswords")
        print(f"  2. Create {KEEP_CREDS_FILE} with:")
        print(f'     {{"email": "yourmail@gmail.com", "app_password": "xxxx xxxx xxxx xxxx"}}')
