"""
drive_mirror — give local-only files a REAL, resolvable Google Drive link.

Without a custom backend (Phase 4 retires the last one), a local file (an
intel report, a tech-scan output) has no web URL of its own. A Drive
*search* link (permalink.drive_search_link) is a graceful fallback for files
that MIGHT already be in Drive, but it's not a guarantee — a query with no
hits is a dead end, exactly what requirement #1 forbids.

This module closes that gap the same way the existing Auto-Dossier Protocol
already does for dossiers ("Mirror to Google Drive — D2M Trip Dossiers/",
dossiers/CLAUDE.md): find-or-create a dedicated Drive folder, find-or-upload
the file into it, and return Drive's own ``webViewLink`` — a link that is
guaranteed to open the exact file, every time.

Folder ids are cached in ``config/tcd_drive_folders.json`` so repeated syncs
don't re-search Drive for the same folder on every run.
"""
import json
from pathlib import Path

from . import _imports

ROOT = _imports.ROOT
FOLDER_CACHE_PATH = ROOT / "config" / "tcd_drive_folders.json"

_folder_cache = None


def _load_folder_cache() -> dict:
    global _folder_cache
    if _folder_cache is None:
        try:
            _folder_cache = json.loads(FOLDER_CACHE_PATH.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            _folder_cache = {}
    return _folder_cache


def _save_folder_cache() -> None:
    FOLDER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FOLDER_CACHE_PATH.write_text(json.dumps(_folder_cache, indent=2))


def find_or_create_folder(drive, folder_name: str) -> str:
    """Drive folder id for ``folder_name`` (top-level, "My Drive"), cached."""
    cache = _load_folder_cache()
    if folder_name in cache:
        return cache[folder_name]

    safe_name = folder_name.replace("'", "\\'")
    res = drive.files().list(
        q=f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
          f"and trashed = false",
        fields="files(id,name)", pageSize=1,
    ).execute()
    files = res.get("files", [])
    if files:
        folder_id = files[0]["id"]
    else:
        created = drive.files().create(
            body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        folder_id = created["id"]

    cache[folder_name] = folder_id
    _save_folder_cache()
    return folder_id


def find_or_upload(drive, local_path: Path, folder_id: str, mime_type: str = "text/plain") -> dict:
    """Find-or-upload ``local_path`` into Drive folder ``folder_id``.

    Returns ``{"id": ..., "webViewLink": ..., "uploaded": bool}``. If a file
    with the same name already exists in the folder, it is left as-is
    (dossiers/intel reports are content-addressed by filename+date, so a
    same-name file is the same report — no need to re-upload every sync).
    """
    name = local_path.name
    safe_name = name.replace("'", "\\'")
    res = drive.files().list(
        q=f"name = '{safe_name}' and '{folder_id}' in parents and trashed = false",
        fields="files(id,webViewLink)", pageSize=1,
    ).execute()
    existing = res.get("files", [])
    if existing:
        return {"id": existing[0]["id"], "webViewLink": existing[0].get("webViewLink", ""),
                "uploaded": False}

    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=False)
    created = drive.files().create(
        body={"name": name, "parents": [folder_id]},
        media_body=media, fields="id,webViewLink",
    ).execute()
    return {"id": created["id"], "webViewLink": created.get("webViewLink", ""), "uploaded": True}


def mirror_file(local_path: Path, folder_name: str, mime_type: str = "text/plain") -> str:
    """One-call convenience: mirror ``local_path`` into ``folder_name``,
    return its real webViewLink (empty string on any failure — callers
    should fall back to drive_search_link rather than crash the sync)."""
    try:
        gauth = _imports.load_google_auth()
        drive = gauth.get_drive()
        folder_id = find_or_create_folder(drive, folder_name)
        result = find_or_upload(drive, local_path, folder_id, mime_type)
        return result.get("webViewLink", "")
    except Exception:
        return ""
