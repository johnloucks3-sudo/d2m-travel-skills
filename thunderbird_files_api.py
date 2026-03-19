"""
Thunderbird Files API Registry
================================
Dreams2Memories Travel, LLC

Uploads dossier .md files to Anthropic Files API so they can be referenced
by file_id in Dani/persona calls — charged as input tokens when used,
but eliminates redundant re-upload on every request.

Storage ops (upload, list, delete) are FREE.
Files are charged only as input tokens when included in messages.

API reference:
  client.beta.files.upload(file=(...))  → FileObject with .id
  client.beta.files.list()              → paginated list
  client.beta.files.delete(file_id)     → DeletedFile
  Usage: betas=["files-api-2025-04-14"]

Registry: ~/Thunderbird/config/files_registry.json
  { "dossier_name": { "file_id": "file_abc123", "synced_at": "...", "size_bytes": N } }

CLI:
  python thunderbird_files_api.py --sync-all       # upload all dossiers
  python thunderbird_files_api.py --list            # show registry
  python thunderbird_files_api.py --sync Furlow_Regent_3071222
  python thunderbird_files_api.py --delete Furlow_Regent_3071222
  python thunderbird_files_api.py --purge-orphans  # delete API files not in registry
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("thunderbird_files_api")

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR  = Path.home() / "Thunderbird"
DOSSIERS_DIR     = THUNDERBIRD_DIR / "dossiers"
REGISTRY_FILE    = THUNDERBIRD_DIR / "config" / "files_registry.json"

# ── Registry I/O ──────────────────────────────────────────────────────────────

def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_registry(registry: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

# ── Anthropic client ─────────────────────────────────────────────────────────

def _get_client():
    import anthropic
    return anthropic.Anthropic()

# ── Core operations ───────────────────────────────────────────────────────────

def sync_dossier(dossier_name: str, force: bool = False) -> dict:
    """Upload a single dossier to Files API. Returns registry entry.

    dossier_name: stem of file in dossiers/ (with or without .md)
    force: re-upload even if already synced
    """
    name = dossier_name.replace(".md", "")
    path = DOSSIERS_DIR / f"{name}.md"

    if not path.exists():
        return {"error": f"Dossier not found: {path}"}

    registry = _load_registry()
    existing = registry.get(name, {})
    file_size = path.stat().st_size

    # Skip if already synced (unless forced or size changed)
    if not force and existing.get("file_id") and existing.get("size_bytes") == file_size:
        logger.info("Dossier %s already synced (file_id=%s)", name, existing["file_id"])
        return existing

    client = _get_client()
    content = path.read_bytes()

    try:
        # Delete old version if it exists
        if existing.get("file_id"):
            try:
                client.beta.files.delete(existing["file_id"])
                logger.info("Deleted old file %s for %s", existing["file_id"], name)
            except Exception as e:
                logger.warning("Could not delete old file %s: %s", existing["file_id"], e)

        result = client.beta.files.upload(
            file=(f"{name}.md", content, "text/plain"),
        )
        entry = {
            "file_id":   result.id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": file_size,
            "filename":   f"{name}.md",
        }
        registry[name] = entry
        _save_registry(registry)
        logger.info("Synced %s → %s", name, result.id)
        return entry

    except Exception as e:
        logger.error("Upload failed for %s: %s", name, e)
        return {"error": str(e), "dossier": name}


def sync_all_dossiers(force: bool = False) -> dict:
    """Sync all .md files in dossiers/ to Files API.
    Returns { "synced": [...], "skipped": [...], "errors": [...] }
    """
    results = {"synced": [], "skipped": [], "errors": []}
    registry = _load_registry()

    for path in sorted(DOSSIERS_DIR.glob("*.md")):
        name = path.stem
        existing = registry.get(name, {})
        file_size = path.stat().st_size

        if not force and existing.get("file_id") and existing.get("size_bytes") == file_size:
            results["skipped"].append(name)
            continue

        entry = sync_dossier(name, force=force)
        if "error" in entry:
            results["errors"].append({"dossier": name, "error": entry["error"]})
        else:
            results["synced"].append({"dossier": name, "file_id": entry["file_id"]})

    return results


def get_dossier_block(dossier_name: str) -> dict | None:
    """Return a Files API content block for use in Dani/persona messages.

    Usage in Anthropic SDK:
      block = get_dossier_block("Furlow_Regent_3071222")
      messages = [{"role": "user", "content": [block, {"type": "text", "text": query}]}]
      client.beta.messages.create(..., betas=["files-api-2025-04-14"])

    Returns None if dossier not in registry (sync first).
    """
    name = dossier_name.replace(".md", "")
    registry = _load_registry()
    entry = registry.get(name)
    if not entry or not entry.get("file_id"):
        return None
    return {
        "type": "document",
        "source": {
            "type":    "file",
            "file_id": entry["file_id"],
        },
        "title": name.replace("_", " "),
    }


def get_dossier_block_or_inline(dossier_name: str) -> dict | None:
    """Return Files API block if synced, else fall back to inline text block.

    Safe to use without pre-syncing — gracefully degrades.
    """
    block = get_dossier_block(dossier_name)
    if block:
        return block

    # Fallback: inline text
    name = dossier_name.replace(".md", "")
    path = DOSSIERS_DIR / f"{name}.md"
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    return {
        "type": "text",
        "text": f"[DOSSIER: {name}]\n\n{text}",
    }


def list_registry() -> list[dict]:
    """Return all registry entries as a sorted list."""
    registry = _load_registry()
    entries = []
    for name, entry in sorted(registry.items()):
        entries.append({"dossier": name, **entry})
    return entries


def delete_dossier_file(dossier_name: str) -> dict:
    """Delete a file from Files API and remove from registry."""
    name = dossier_name.replace(".md", "")
    registry = _load_registry()
    entry = registry.get(name)

    if not entry or not entry.get("file_id"):
        return {"error": f"No file_id in registry for {name}"}

    client = _get_client()
    try:
        client.beta.files.delete(entry["file_id"])
        del registry[name]
        _save_registry(registry)
        return {"deleted": name, "file_id": entry["file_id"]}
    except Exception as e:
        return {"error": str(e), "dossier": name}


def purge_orphan_files() -> dict:
    """Delete Files API files that are no longer in the registry."""
    client = _get_client()
    registry = _load_registry()
    known_ids = {v["file_id"] for v in registry.values() if v.get("file_id")}

    deleted = []
    errors  = []
    try:
        page = client.beta.files.list()
        for f in page.data:
            if f.id not in known_ids:
                try:
                    client.beta.files.delete(f.id)
                    deleted.append(f.id)
                except Exception as e:
                    errors.append({"file_id": f.id, "error": str(e)})
    except Exception as e:
        return {"error": str(e)}

    return {"deleted_orphans": deleted, "errors": errors}


# ── MCP tool registration ─────────────────────────────────────────────────────

def register_files_api_tools(mcp) -> None:
    """Register Files API tools with the MCP server."""

    @mcp.tool()
    def upload_dossier_file(dossier_name: str, force: bool = False) -> str:
        """Upload a single client dossier to Anthropic Files API.
        Returns file_id. Skips if already synced (unless force=True)."""
        result = sync_dossier(dossier_name, force=force)
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2)

    @mcp.tool()
    def sync_all_dossier_files(force: bool = False) -> str:
        """Sync all client dossiers to Anthropic Files API.
        Returns counts of synced, skipped, and errored files."""
        result = sync_all_dossiers(force=force)
        synced  = len(result["synced"])
        skipped = len(result["skipped"])
        errors  = len(result["errors"])
        summary = f"Synced: {synced} | Skipped (up to date): {skipped} | Errors: {errors}"
        if result["errors"]:
            summary += "\nErrors:\n" + "\n".join(
                f"  {e['dossier']}: {e['error']}" for e in result["errors"]
            )
        return summary

    @mcp.tool()
    def list_dossier_files() -> str:
        """List all dossiers in the Files API registry with their file_ids."""
        entries = list_registry()
        if not entries:
            return "Registry is empty. Run sync_all_dossier_files first."
        lines = [
            f"{e['dossier']}: {e.get('file_id','—')} ({e.get('size_bytes',0)//1024}KB synced {e.get('synced_at','?')[:10]})"
            for e in entries
        ]
        return "\n".join(lines)

    @mcp.tool()
    def delete_dossier_api_file(dossier_name: str) -> str:
        """Delete a dossier's file from Anthropic Files API and remove from registry."""
        result = delete_dossier_file(dossier_name)
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Deleted: {result['dossier']} (was {result['file_id']})"

    @mcp.tool()
    def purge_orphan_api_files() -> str:
        """Delete Files API files that are no longer in the local registry."""
        result = purge_orphan_files()
        if "error" in result:
            return f"Error: {result['error']}"
        deleted = result.get("deleted_orphans", [])
        errors  = result.get("errors", [])
        return f"Deleted {len(deleted)} orphan(s). Errors: {len(errors)}"


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = sys.argv[1:]

    if "--list" in args:
        entries = list_registry()
        if not entries:
            print("Registry empty — run --sync-all first")
        else:
            print(f"{'Dossier':<45} {'File ID':<30} {'KB':>5}  Synced")
            print("-" * 95)
            for e in entries:
                kb = e.get("size_bytes", 0) // 1024
                print(f"{e['dossier']:<45} {e.get('file_id','—'):<30} {kb:>5}  {e.get('synced_at','?')[:10]}")

    elif "--sync-all" in args:
        force = "--force" in args
        print(f"Syncing all dossiers to Files API{' (forced)' if force else ''}...")
        result = sync_all_dossiers(force=force)
        print(f"  Synced:  {len(result['synced'])}")
        print(f"  Skipped: {len(result['skipped'])} (already up to date)")
        print(f"  Errors:  {len(result['errors'])}")
        for e in result["errors"]:
            print(f"    ERROR {e['dossier']}: {e['error']}")
        for s in result["synced"]:
            print(f"    OK {s['dossier']} → {s['file_id']}")

    elif "--sync" in args:
        idx = args.index("--sync")
        if idx + 1 < len(args):
            name = args[idx + 1]
            force = "--force" in args
            print(f"Syncing {name}...")
            result = sync_dossier(name, force=force)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: --sync <dossier_name>")

    elif "--delete" in args:
        idx = args.index("--delete")
        if idx + 1 < len(args):
            name = args[idx + 1]
            result = delete_dossier_file(name)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: --delete <dossier_name>")

    elif "--purge-orphans" in args:
        print("Purging orphan files from Files API...")
        result = purge_orphan_files()
        print(json.dumps(result, indent=2))

    elif "--test-block" in args:
        idx = args.index("--test-block")
        if idx + 1 < len(args):
            name = args[idx + 1]
            block = get_dossier_block_or_inline(name)
            if block:
                src_type = block.get("source", {}).get("type", block.get("type"))
                print(f"Block type: {src_type}")
                if block.get("source", {}).get("type") == "file":
                    print(f"file_id: {block['source']['file_id']}")
                else:
                    print(f"Inline fallback — {len(block.get('text',''))} chars")
            else:
                print(f"No block available for {name}")

    else:
        print("Usage:")
        print("  python thunderbird_files_api.py --sync-all [--force]")
        print("  python thunderbird_files_api.py --sync <dossier_name> [--force]")
        print("  python thunderbird_files_api.py --list")
        print("  python thunderbird_files_api.py --delete <dossier_name>")
        print("  python thunderbird_files_api.py --purge-orphans")
        print("  python thunderbird_files_api.py --test-block <dossier_name>")
