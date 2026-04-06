"""
Dreams2Memories Google Drive MCP Module
=======================================

Extends the travel MCP server with Google Drive operations:
- List files and folders
- Search files by name or content
- Read file metadata and content
- Create folders
- Upload and download files
- Move/rename files

Auth: OAuth 2.0 Desktop flow (preferred) with service account fallback.
OAuth operates as John's personal Drive — full move/delete permissions.
Service account has limited permissions (no reparenting).

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import io
import mimetypes
import time
import functools
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Configuration
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
SERVICE_ACCOUNT_FILE = THUNDERBIRD_DIR / "credentials.json"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"  # Reuse same client ID
DRIVE_TOKEN_FILE = THUNDERBIRD_DIR / "drive_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

logger = logging.getLogger(__name__)

# Cached service instance
_drive_service = None


def _get_oauth_creds():
    """Load OAuth credentials if available, with auto-refresh."""
    if not DRIVE_TOKEN_FILE.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(DRIVE_TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            DRIVE_TOKEN_FILE.write_text(creds.to_json())
        except Exception as e:
            logger.warning(f"Drive OAuth token refresh failed: {e}")
            return None

    if creds and creds.valid:
        return creds
    return None


def _get_drive_service():
    """Authenticate and return a cached Google Drive API service instance.

    Prefers OAuth (full permissions as John) with service account fallback.
    """
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    # Try OAuth first
    creds = _get_oauth_creds()
    if creds:
        logger.info("Drive: Using OAuth credentials (full permissions)")
        _drive_service = build("drive", "v3", credentials=creds)
        return _drive_service

    # Fallback to service account
    logger.info("Drive: Using service account (limited move permissions)")
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


def authorize_drive():
    """Run the one-time OAuth 2.0 authorization flow for Google Drive.

    Opens a browser for user consent, saves the refresh token to drive_token.json.
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: OAuth credentials file not found: {OAUTH_CREDENTIALS_FILE}")
        print()
        print("This reuses the same OAuth client ID as Gmail.")
        print(f"Expected at: {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)
    DRIVE_TOKEN_FILE.write_text(creds.to_json())
    print(f"Drive authorization successful! Token saved to: {DRIVE_TOKEN_FILE}")
    return True


def _retry_on_error(func):
    """Retry wrapper for transient Google API errors (429, 500, 503)."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        retries = 3
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status in (429, 500, 503) and attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Drive API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _escape_query(value: str) -> str:
    """Escape single quotes for Drive API query strings."""
    return value.replace("\\", "\\\\").replace("'", "\\'")



def register_drive_tools(mcp: FastMCP):
    """Register all Google Drive tools with the MCP server."""

    @mcp.tool(
        name="drive_list_files",
        annotations={"title": "List Google Drive Files", "readOnlyHint": True},
    )
    @_retry_on_error
    async def drive_list_files(
        folder_id: Optional[str] = Field(
            None, description="Folder ID to list (omit for root)"
        ),
        max_results: int = Field(25, description="Max files to return (1-500)"),
        file_type: Optional[str] = Field(
            None,
            description="Filter by type: 'folder', 'document', 'spreadsheet', 'pdf', 'image'",
        ),
    ) -> str:
        """List files and folders in Google Drive."""
        try:
            service = _get_drive_service()

            query_parts = ["trashed = false"]
            if folder_id:
                safe_id = _escape_query(folder_id)
                query_parts.append(f"'{safe_id}' in parents")

            mime_map = {
                "folder": "application/vnd.google-apps.folder",
                "document": "application/vnd.google-apps.document",
                "spreadsheet": "application/vnd.google-apps.spreadsheet",
                "pdf": "application/pdf",
                "image": None,
            }
            if file_type and file_type in mime_map:
                if file_type == "image":
                    query_parts.append("mimeType contains 'image/'")
                else:
                    query_parts.append(f"mimeType = '{mime_map[file_type]}'")

            query = " and ".join(query_parts)
            page_size = min(max_results, 100)
            all_files = []
            page_token = None

            while len(all_files) < max_results:
                results = (
                    service.files()
                    .list(
                        q=query,
                        pageSize=page_size,
                        pageToken=page_token,
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents, webViewLink)",
                        orderBy="modifiedTime desc",
                    )
                    .execute()
                )
                all_files.extend(results.get("files", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            all_files = all_files[:max_results]
            return json.dumps(
                {"status": "success", "count": len(all_files), "files": all_files}, indent=2
            )
        except HttpError as e:
            logger.error(f"Drive list error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "drive_error"})
        except Exception as e:
            logger.error(f"Drive list error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_search",
        annotations={"title": "Search Google Drive", "readOnlyHint": True},
    )
    @_retry_on_error
    async def drive_search(
        query: str = Field(..., description="Search query (file name or content)"),
        search_type: str = Field("fullText", description="Search mode: 'fullText' (name+content) or 'name' (name only)"),
        max_results: int = Field(10, description="Max results to return"),
    ) -> str:
        """Search Google Drive by file name or content."""
        try:
            service = _get_drive_service()
            safe_query = _escape_query(query)
            if search_type == "name":
                q = f"name contains '{safe_query}' and trashed = false"
            else:
                q = f"fullText contains '{safe_query}' and trashed = false"
            results = (
                service.files()
                .list(
                    q=q,
                    pageSize=min(max_results, 50),
                    fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )

            files = results.get("files", [])
            return json.dumps(
                {"status": "success", "query": query, "count": len(files), "files": files},
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Drive search error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "drive_error"})
        except Exception as e:
            logger.error(f"Drive search error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_get_file_info",
        annotations={"title": "Get Drive File Info", "readOnlyHint": True},
    )
    @_retry_on_error
    async def drive_get_file_info(
        file_id: str = Field(..., description="Google Drive file ID"),
    ) -> str:
        """Get detailed metadata for a specific file."""
        try:
            service = _get_drive_service()
            file_meta = (
                service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, modifiedTime, createdTime, size, parents, webViewLink, description, owners, permissions",
                )
                .execute()
            )
            return json.dumps({"status": "success", "file": file_meta}, indent=2)
        except Exception as e:
            logger.error(f"Drive get file error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_read_document",
        annotations={"title": "Read Google Doc Content", "readOnlyHint": True},
    )
    @_retry_on_error
    async def drive_read_document(
        file_id: str = Field(..., description="Google Doc or Sheet file ID"),
        export_format: str = Field(
            "text", description="Export as: 'text', 'html', 'csv' (sheets only)"
        ),
    ) -> str:
        """Read the content of a Google Doc or Sheet."""
        try:
            service = _get_drive_service()

            mime_export = {
                "text": "text/plain",
                "html": "text/html",
                "csv": "text/csv",
            }
            mime = mime_export.get(export_format, "text/plain")

            content = (
                service.files().export(fileId=file_id, mimeType=mime).execute()
            )

            text = content.decode("utf-8") if isinstance(content, bytes) else str(content)

            # Truncate very large files
            if len(text) > 50000:
                text = text[:50000] + "\n\n... [TRUNCATED — file exceeds 50K chars]"

            return json.dumps(
                {"status": "success", "file_id": file_id, "format": export_format, "content": text},
                indent=2,
            )
        except Exception as e:
            logger.error(f"Drive read error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_create_folder",
        annotations={"title": "Create Drive Folder", "readOnlyHint": False},
    )
    @_retry_on_error
    async def drive_create_folder(
        name: str = Field(..., description="Folder name"),
        parent_id: Optional[str] = Field(
            None, description="Parent folder ID (omit for root)"
        ),
    ) -> str:
        """Create a new folder in Google Drive."""
        try:
            service = _get_drive_service()
            metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                metadata["parents"] = [parent_id]

            folder = service.files().create(body=metadata, fields="id, name, webViewLink").execute()
            return json.dumps({"status": "success", "folder": folder}, indent=2)
        except Exception as e:
            logger.error(f"Drive create folder error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_upload_file",
        annotations={"title": "Upload File to Drive", "readOnlyHint": False},
    )
    @_retry_on_error
    async def drive_upload_file(
        local_path: str = Field(..., description="Local file path to upload"),
        folder_id: Optional[str] = Field(
            None, description="Target folder ID (omit for root)"
        ),
        name: Optional[str] = Field(
            None, description="File name in Drive (defaults to local filename)"
        ),
    ) -> str:
        """Upload a local file to Google Drive."""
        try:
            service = _get_drive_service()
            file_path = Path(local_path)

            if not file_path.exists():
                return json.dumps({"error": f"File not found: {local_path}"})

            file_name = name or file_path.name
            mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

            metadata = {"name": file_name}
            if folder_id:
                metadata["parents"] = [folder_id]

            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
            uploaded = (
                service.files()
                .create(body=metadata, media_body=media, fields="id, name, webViewLink, size")
                .execute()
            )

            return json.dumps({"status": "success", "uploaded": uploaded}, indent=2)
        except Exception as e:
            logger.error(f"Drive upload error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_download_file",
        annotations={"title": "Download File from Drive", "readOnlyHint": True},
    )
    @_retry_on_error
    async def drive_download_file(
        file_id: str = Field(..., description="Google Drive file ID"),
        local_path: str = Field(..., description="Local path to save the file"),
    ) -> str:
        """Download a file from Google Drive to local filesystem."""
        try:
            service = _get_drive_service()

            # Get file metadata to check type
            meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
            mime = meta.get("mimeType", "")

            # Google Docs types need export
            export_map = {
                "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
                "application/vnd.google-apps.spreadsheet": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".xlsx",
                ),
                "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
            }

            output_path = Path(local_path)

            if mime in export_map:
                export_mime, ext = export_map[mime]
                if not output_path.suffix:
                    output_path = output_path.with_suffix(ext)
                request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                request = service.files().get_media(fileId=file_id)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(fh.getvalue())

            return json.dumps(
                {
                    "status": "success",
                    "file_name": meta["name"],
                    "saved_to": str(output_path),
                    "size_bytes": len(fh.getvalue()),
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Drive download error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_move_file",
        annotations={"title": "Move/Rename File in Drive", "readOnlyHint": False},
    )
    @_retry_on_error
    async def drive_move_file(
        file_id: str = Field(..., description="File ID to move/rename"),
        new_name: Optional[str] = Field(None, description="New file name"),
        new_parent_id: Optional[str] = Field(None, description="New parent folder ID"),
    ) -> str:
        """Move or rename a file in Google Drive."""
        try:
            service = _get_drive_service()
            body = {}
            if new_name:
                body["name"] = new_name

            kwargs = {"fileId": file_id, "fields": "id, name, parents, webViewLink"}
            if body:
                kwargs["body"] = body

            if new_parent_id:
                # Get current parents
                current = service.files().get(fileId=file_id, fields="parents").execute()
                old_parents = ",".join(current.get("parents", []))
                kwargs["addParents"] = new_parent_id
                kwargs["removeParents"] = old_parents

            updated = service.files().update(**kwargs).execute()
            return json.dumps({"status": "success", "file": updated}, indent=2)
        except Exception as e:
            logger.error(f"Drive move error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    @mcp.tool(
        name="drive_delete_file",
        annotations={"title": "Delete File/Folder in Drive", "readOnlyHint": False},
    )
    @_retry_on_error
    async def drive_delete_file(
        file_id: str = Field(..., description="File or folder ID to delete (moves to trash)"),
    ) -> str:
        """Move a file or folder to trash in Google Drive. Does NOT permanently delete."""
        try:
            service = _get_drive_service()
            # Use trash (recoverable) rather than permanent delete
            service.files().update(fileId=file_id, body={"trashed": True}).execute()
            return json.dumps({"status": "success", "action": "trashed", "file_id": file_id}, indent=2)
        except Exception as e:
            logger.error(f"Drive delete error: {e}")
            return json.dumps({"error": str(e), "type": "drive_error"})

    logger.info("Google Drive tools registered successfully")


if __name__ == "__main__":
    import sys
    if "--authorize" in sys.argv:
        authorize_drive()
    else:
        print("Usage: python3 thunderbird_drive.py --authorize")
        print("  Runs the one-time OAuth 2.0 browser authorization flow for Drive.")
        print(f"  Saves token to: {DRIVE_TOKEN_FILE}")
