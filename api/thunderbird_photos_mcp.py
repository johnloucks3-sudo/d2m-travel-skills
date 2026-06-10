"""
Dreams2Memories Google Photos MCP Module
=========================================

Extends the travel MCP server with Google Photos Library operations:
- List albums
- Search and read media items
- Get album and media item details

Auth: Unified OAuth via thunderbird_google_auth (gmail_token.json).
Requires scope: https://www.googleapis.com/auth/photoslibrary.readonly

Run re-auth to grant the Photos scope:
    python3 api/thunderbird_google_auth.py --authorize

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import functools
import time
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Photos service builder (with graceful fallback)
# ---------------------------------------------------------------------------

_photos_service = None


def _get_photos_service():
    """Return cached Google Photos Library API service instance.

    Falls back to registering stub tools if the Photos scope has not
    been authorised yet (user needs to run --authorize again).
    """
    global _photos_service
    if _photos_service is not None:
        return _photos_service
    try:
        from api.thunderbird_google_auth import get_photos

        _photos_service = get_photos()
        logger.info("Photos: Using unified OAuth credentials")
        return _photos_service
    except Exception as exc:
        logger.warning(f"Photos: Cannot build service — {exc}")
        return None


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


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
                    logger.warning(
                        f"Photos API {e.resp.status}, retry {attempt + 1}/{retries} in {wait}s"
                    )
                    time.sleep(wait)
                    continue
                raise
    return wrapper


# ---------------------------------------------------------------------------
# Fallback tools (when Photos API is unavailable)
# ---------------------------------------------------------------------------

_FALLBACK = json.dumps(
    {"error": "Google Photos API not available. Run: python3 api/thunderbird_google_auth.py --authorize"}
)


def _register_fallback_tools(mcp: FastMCP):
    """Register dummy tools that tell the user to re-authorise."""

    @mcp.tool(
        name="photos_list_albums",
        annotations={"title": "List Google Photos Albums", "readOnlyHint": True},
    )
    async def photos_list_albums(page_size: int = 50) -> str:
        """List all Google Photos albums (fallback — API unavailable)."""
        return _FALLBACK

    @mcp.tool(
        name="photos_search_media",
        annotations={"title": "Search Google Photos Media", "readOnlyHint": True},
    )
    async def photos_search_media(
        album_id: str = "",
        query: str = "",
        page_size: int = 25,
    ) -> str:
        """Search photos in Google Photos (fallback — API unavailable)."""
        return _FALLBACK

    @mcp.tool(
        name="photos_get_media_item",
        annotations={"title": "Get Google Photos Media Item", "readOnlyHint": True},
    )
    async def photos_get_media_item(media_item_id: str) -> str:
        """Get a single media item's details (fallback — API unavailable)."""
        return _FALLBACK

    @mcp.tool(
        name="photos_get_album",
        annotations={"title": "Get Google Photos Album", "readOnlyHint": True},
    )
    async def photos_get_album(album_id: str) -> str:
        """Get album details (fallback — API unavailable)."""
        return _FALLBACK

    @mcp.tool(
        name="photos_list_media_items",
        annotations={"title": "List Recent Media Items", "readOnlyHint": True},
    )
    async def photos_list_media_items(page_size: int = 25) -> str:
        """List recent media items (fallback — API unavailable)."""
        return _FALLBACK

    logger.info("Google Photos fallback tools registered (API unavailable)")


# ---------------------------------------------------------------------------
# Main registration
# ---------------------------------------------------------------------------


def register_photos_mcp_tools(mcp: FastMCP):
    """Register all Google Photos Library tools with the MCP server.

    If the Photos API service cannot be built (missing scope or token),
    registers fallback tools that guide the user to re-authorise.
    """
    service = _get_photos_service()
    if service is None:
        _register_fallback_tools(mcp)
        return

    # ------------------------------------------------------------------
    # 1. photos_list_albums
    # ------------------------------------------------------------------
    @mcp.tool(
        name="photos_list_albums",
        annotations={"title": "List Google Photos Albums", "readOnlyHint": True},
    )
    @_retry_on_error
    async def photos_list_albums(
        page_size: int = Field(50, description="Number of albums to return (max 50)"),
    ) -> str:
        """List all Google Photos albums."""
        try:
            page_size = min(page_size, 50)
            albums = []
            page_token = None

            while len(albums) < page_size:
                results = (
                    service.albums()
                    .list(
                        pageSize=min(page_size - len(albums), 50),
                        pageToken=page_token,
                    )
                    .execute()
                )
                for a in results.get("albums", []):
                    albums.append(
                        {
                            "id": a.get("id"),
                            "title": a.get("title"),
                            "media_items_count": a.get("mediaItemsCount"),
                            "cover_photo_base_url": a.get("coverPhotoBaseUrl"),
                            "product_url": a.get("productUrl"),
                            "is_writeable": a.get("isWriteable"),
                        }
                    )
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            return json.dumps(
                {"status": "success", "count": len(albums), "albums": albums},
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Photos list albums error: {e}")
            return json.dumps(
                {"error": str(e), "status_code": e.resp.status, "type": "photos_error"}
            )
        except Exception as e:
            logger.error(f"Photos list albums error: {e}")
            return json.dumps({"error": str(e), "type": "photos_error"})

    # ------------------------------------------------------------------
    # 2. photos_search_media
    # ------------------------------------------------------------------
    @mcp.tool(
        name="photos_search_media",
        annotations={"title": "Search Google Photos Media", "readOnlyHint": True},
    )
    @_retry_on_error
    async def photos_search_media(
        album_id: str = Field("", description="Album ID to search within (omit for all)"),
        query: str = Field("", description="Content category filter (e.g. 'LANDSCAPES', 'SUNSET')"),
        page_size: int = Field(25, description="Number of media items to return (max 100)"),
    ) -> str:
        """Search photos in Google Photos by album or content category."""
        try:
            page_size = min(page_size, 100)
            body = {"pageSize": page_size}

            if album_id:
                body["albumId"] = album_id
            if query:
                body["filters"] = {
                    "contentFilter": {
                        "includedContentCategories": [query.upper()]
                    }
                }

            results = service.mediaItems().search(body=body).execute()

            items = []
            for m in results.get("mediaItems", []):
                items.append(
                    {
                        "id": m.get("id"),
                        "filename": m.get("filename"),
                        "mime_type": m.get("mimeType"),
                        "base_url": m.get("baseUrl"),
                        "product_url": m.get("productUrl"),
                        "creation_time": m.get("mediaMetadata", {}).get("creationTime"),
                        "width": m.get("mediaMetadata", {}).get("width"),
                        "height": m.get("mediaMetadata", {}).get("height"),
                    }
                )

            return json.dumps(
                {
                    "status": "success",
                    "count": len(items),
                    "media_items": items,
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Photos search media error: {e}")
            return json.dumps(
                {"error": str(e), "status_code": e.resp.status, "type": "photos_error"}
            )
        except Exception as e:
            logger.error(f"Photos search media error: {e}")
            return json.dumps({"error": str(e), "type": "photos_error"})

    # ------------------------------------------------------------------
    # 3. photos_get_media_item
    # ------------------------------------------------------------------
    @mcp.tool(
        name="photos_get_media_item",
        annotations={"title": "Get Google Photos Media Item", "readOnlyHint": True},
    )
    @_retry_on_error
    async def photos_get_media_item(
        media_item_id: str = Field(..., description="Media item ID to retrieve"),
    ) -> str:
        """Get a single media item's details and download URL."""
        try:
            result = service.mediaItems().get(mediaItemId=media_item_id).execute()

            item = {
                "id": result.get("id"),
                "filename": result.get("filename"),
                "mime_type": result.get("mimeType"),
                "base_url": result.get("baseUrl"),
                "product_url": result.get("productUrl"),
                "download_url": f"{result.get('baseUrl')}=d",
                "creation_time": result.get("mediaMetadata", {}).get("creationTime"),
                "width": result.get("mediaMetadata", {}).get("width"),
                "height": result.get("mediaMetadata", {}).get("height"),
                "orientation": result.get("mediaMetadata", {}).get("orientation"),
                "photo": result.get("mediaMetadata", {}).get("photo"),
                "video": result.get("mediaMetadata", {}).get("video"),
            }

            return json.dumps({"status": "success", "media_item": item}, indent=2)
        except HttpError as e:
            logger.error(f"Photos get media item error: {e}")
            return json.dumps(
                {"error": str(e), "status_code": e.resp.status, "type": "photos_error"}
            )
        except Exception as e:
            logger.error(f"Photos get media item error: {e}")
            return json.dumps({"error": str(e), "type": "photos_error"})

    # ------------------------------------------------------------------
    # 4. photos_get_album
    # ------------------------------------------------------------------
    @mcp.tool(
        name="photos_get_album",
        annotations={"title": "Get Google Photos Album", "readOnlyHint": True},
    )
    @_retry_on_error
    async def photos_get_album(
        album_id: str = Field(..., description="Album ID to retrieve"),
    ) -> str:
        """Get album details: title, count, cover photo, url, share info."""
        try:
            result = service.albums().get(albumId=album_id).execute()

            album = {
                "id": result.get("id"),
                "title": result.get("title"),
                "media_items_count": result.get("mediaItemsCount"),
                "cover_photo_base_url": result.get("coverPhotoBaseUrl"),
                "cover_photo_media_item_id": result.get("coverPhotoMediaItemId"),
                "product_url": result.get("productUrl"),
                "is_writeable": result.get("isWriteable"),
                "share_info": result.get("shareInfo"),
            }

            return json.dumps({"status": "success", "album": album}, indent=2)
        except HttpError as e:
            logger.error(f"Photos get album error: {e}")
            return json.dumps(
                {"error": str(e), "status_code": e.resp.status, "type": "photos_error"}
            )
        except Exception as e:
            logger.error(f"Photos get album error: {e}")
            return json.dumps({"error": str(e), "type": "photos_error"})

    # ------------------------------------------------------------------
    # 5. photos_list_media_items
    # ------------------------------------------------------------------
    @mcp.tool(
        name="photos_list_media_items",
        annotations={"title": "List Recent Media Items", "readOnlyHint": True},
    )
    @_retry_on_error
    async def photos_list_media_items(
        page_size: int = Field(25, description="Number of media items to return (max 100)"),
    ) -> str:
        """List recent media items (most recent first)."""
        try:
            page_size = min(page_size, 100)
            items = []
            page_token = None

            while len(items) < page_size:
                results = (
                    service.mediaItems()
                    .list(
                        pageSize=min(page_size - len(items), 100),
                        pageToken=page_token,
                    )
                    .execute()
                )
                for m in results.get("mediaItems", []):
                    items.append(
                        {
                            "id": m.get("id"),
                            "filename": m.get("filename"),
                            "mime_type": m.get("mimeType"),
                            "base_url": m.get("baseUrl"),
                            "product_url": m.get("productUrl"),
                            "creation_time": m.get("mediaMetadata", {}).get("creationTime"),
                            "download_url": f"{m.get('baseUrl')}=d",
                        }
                    )
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            return json.dumps(
                {
                    "status": "success",
                    "count": len(items),
                    "media_items": items,
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Photos list media items error: {e}")
            return json.dumps(
                {"error": str(e), "status_code": e.resp.status, "type": "photos_error"}
            )
        except Exception as e:
            logger.error(f"Photos list media items error: {e}")
            return json.dumps({"error": str(e), "type": "photos_error"})

    logger.info("Google Photos tools registered successfully")
