"""
Dreams2Memories Google Docs MCP Module
=======================================

Extends the travel MCP server with Google Docs operations:
- Create new documents with optional initial content
- Read document content as plain text
- Append or replace document content
- Get document metadata (title, url, timestamps, author)
- List/search documents in Drive
- Insert images at specific positions

Auth: OAuth 2.0 via thunderbird_google_auth (unified token).
Uses both Docs API v1 and Drive API v3.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import time
import functools
from pathlib import Path
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from api.thunderbird_google_auth import get_docs, get_drive

logger = logging.getLogger(__name__)


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
                    logger.warning(f"Docs API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _escape_query(value: str) -> str:
    """Escape single quotes for Drive API query strings."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _extract_text_from_doc(doc_data: dict) -> str:
    """Walk the document body and extract plain text from all text runs."""
    body = doc_data.get("body", {})
    content = body.get("content", [])
    texts = []

    def _walk(items):
        for item in items:
            paragraph = item.get("paragraph")
            if paragraph:
                for elem in paragraph.get("elements", []):
                    text_run = elem.get("textRun")
                    if text_run and "content" in text_run:
                        texts.append(text_run["content"])
            table = item.get("table")
            if table:
                for row in table.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        _walk(cell.get("content", []))
            # Recurse into nested structural elements
            for key in ("sectionBreak", "tableOfContents"):
                if key in item:
                    child = item[key]
                    if isinstance(child, dict):
                        _walk(child.get("content", []))

    _walk(content)
    return "".join(texts)


def _get_end_index(doc_data: dict) -> int:
    """Get the total end index of the document body for appending."""
    body = doc_data.get("body", {})
    content = body.get("content", [])
    if content:
        last_item = content[-1]
        seg_end = last_item.get("endIndex", 1)
        return seg_end
    return 1


def register_docs_mcp_tools(mcp: FastMCP):
    """Register all Google Docs tools with the MCP server."""

    @mcp.tool(
        name="docs_create_document",
        annotations={"title": "Create Google Doc", "readOnlyHint": False},
    )
    @_retry_on_error
    async def docs_create_document(
        title: str = Field(..., description="Title for the new document"),
        body_json: str = Field("", description="Optional JSON string of initial content to write as the document body"),
    ) -> str:
        """Create a new Google Doc with optional initial content."""
        try:
            docs = get_docs()

            # Create blank document
            doc = docs.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")
            doc_url = doc.get("documentUrl", f"https://docs.google.com/document/d/{doc_id}/edit")

            # Write initial content if provided
            if body_json:
                try:
                    content_text = json.loads(body_json)
                    if not isinstance(content_text, str):
                        content_text = json.dumps(content_text)
                except (json.JSONDecodeError, TypeError):
                    content_text = body_json

                # Build insert request at the start of the document body
                write_requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content_text,
                        }
                    }
                ]
                docs.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": write_requests},
                ).execute()

            return json.dumps(
                {"status": "success", "document_id": doc_id, "url": doc_url, "title": title},
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs create error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs create error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    @mcp.tool(
        name="docs_read_content",
        annotations={"title": "Read Google Doc Content", "readOnlyHint": True},
    )
    @_retry_on_error
    async def docs_read_content(
        document_id: str = Field(..., description="Google Docs document ID"),
    ) -> str:
        """Read document content as plain text."""
        try:
            docs = get_docs()
            doc = docs.documents().get(documentId=document_id).execute()
            text = _extract_text_from_doc(doc)

            # Truncate very large documents
            if len(text) > 100000:
                text = text[:100000] + "\n\n... [TRUNCATED — document exceeds 100K chars]"

            return json.dumps(
                {
                    "status": "success",
                    "document_id": document_id,
                    "title": doc.get("title", ""),
                    "content_length": len(text),
                    "content": text,
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs read error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs read error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    @mcp.tool(
        name="docs_update_content",
        annotations={"title": "Update Google Doc Content", "readOnlyHint": False},
    )
    @_retry_on_error
    async def docs_update_content(
        document_id: str = Field(..., description="Google Docs document ID"),
        text: str = Field(..., description="Text content to write"),
        append: bool = Field(True, description="If True, append to end. If False, replace all content."),
    ) -> str:
        """Append or replace text content in a Google Doc."""
        try:
            docs = get_docs()

            if append:
                # Get the current end index and append
                doc = docs.documents().get(documentId=document_id).execute()
                end_index = _get_end_index(doc)

                # Insert a newline before appending if doc is not empty
                prefix = "\n" if end_index > 1 else ""

                requests = [
                    {
                        "insertText": {
                            "location": {"index": end_index},
                            "text": prefix + text,
                        }
                    }
                ]
            else:
                # Replace all content: delete everything then insert
                doc = docs.documents().get(documentId=document_id).execute()
                end_index = _get_end_index(doc)

                if end_index > 1:
                    # Delete all existing content (index 1 to endIndex-1)
                    requests = [
                        {
                            "deleteContentRange": {
                                "range": {
                                    "startIndex": 1,
                                    "endIndex": end_index - 1,
                                }
                            }
                        },
                        {
                            "insertText": {
                                "location": {"index": 1},
                                "text": text,
                            }
                        },
                    ]
                else:
                    requests = [
                        {
                            "insertText": {
                                "location": {"index": 1},
                                "text": text,
                            }
                        }
                    ]

            docs.documents().batchUpdate(
                documentId=document_id,
                body={"requests": requests},
            ).execute()

            return json.dumps(
                {
                    "status": "success",
                    "document_id": document_id,
                    "action": "append" if append else "replace",
                    "chars_written": len(text),
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs update error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs update error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    @mcp.tool(
        name="docs_get_document_info",
        annotations={"title": "Get Google Doc Info", "readOnlyHint": True},
    )
    @_retry_on_error
    async def docs_get_document_info(
        document_id: str = Field(..., description="Google Docs document ID"),
    ) -> str:
        """Get document metadata: title, url, created/modified time, author."""
        try:
            docs = get_docs()
            drive = get_drive()

            # Get document structure from Docs API
            doc = docs.documents().get(documentId=document_id).execute()

            # Get richer metadata from Drive API
            drive_meta = (
                drive.files()
                .get(
                    fileId=document_id,
                    fields="id, name, createdTime, modifiedTime, owners, size, webViewLink",
                )
                .execute()
            )

            owners = drive_meta.get("owners", [])
            author = owners[0].get("displayName", "Unknown") if owners else "Unknown"

            return json.dumps(
                {
                    "status": "success",
                    "document_id": document_id,
                    "title": doc.get("title", drive_meta.get("name", "")),
                    "url": drive_meta.get("webViewLink", f"https://docs.google.com/document/d/{document_id}/edit"),
                    "created_time": drive_meta.get("createdTime", ""),
                    "modified_time": drive_meta.get("modifiedTime", ""),
                    "author": author,
                    "size_bytes": drive_meta.get("size", 0),
                    "revision_id": doc.get("revisionId", ""),
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs info error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs info error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    @mcp.tool(
        name="docs_list_documents",
        annotations={"title": "List Google Docs in Drive", "readOnlyHint": True},
    )
    @_retry_on_error
    async def docs_list_documents(
        query: str = Field("", description="Optional name search query to filter documents"),
    ) -> str:
        """List Google Docs in Drive with optional name filter."""
        try:
            drive = get_drive()

            query_parts = ["mimeType = 'application/vnd.google-apps.document'", "trashed = false"]
            if query:
                safe_query = _escape_query(query)
                query_parts.append(f"name contains '{safe_query}'")

            q = " and ".join(query_parts)

            results = (
                drive.files()
                .list(
                    q=q,
                    pageSize=50,
                    fields="files(id, name, modifiedTime, size, webViewLink, owners, createdTime)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )

            files = results.get("files", [])
            doc_list = []
            for f in files:
                owners = f.get("owners", [])
                author = owners[0].get("displayName", "Unknown") if owners else "Unknown"
                doc_list.append(
                    {
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "url": f.get("webViewLink"),
                        "modified_time": f.get("modifiedTime"),
                        "created_time": f.get("createdTime"),
                        "author": author,
                        "size_bytes": f.get("size", 0),
                    }
                )

            return json.dumps(
                {"status": "success", "query": query, "count": len(doc_list), "documents": doc_list},
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs list error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs list error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    @mcp.tool(
        name="docs_insert_image",
        annotations={"title": "Insert Image into Google Doc", "readOnlyHint": False},
    )
    @_retry_on_error
    async def docs_insert_image(
        document_id: str = Field(..., description="Google Docs document ID"),
        image_url: str = Field(..., description="Publicly accessible URL of the image to insert"),
        position_index: int = Field(0, description="Position index in the document body to insert the image (default: 0 = end of document)"),
    ) -> str:
        """Insert an image at a specific position in the document.

        Uses batchUpdate with insertInlineImage. The image must be publicly
        accessible via URL (Google Docs fetches it server-side).
        If position_index is 0, inserts at the end of the document body.
        """
        try:
            docs = get_docs()

            # Determine insert location
            insert_index = position_index
            if insert_index <= 0:
                doc = docs.documents().get(documentId=document_id).execute()
                insert_index = _get_end_index(doc) - 1  # Insert before final newline

            requests = [
                {
                    "insertInlineImage": {
                        "location": {"index": insert_index},
                        "uri": image_url,
                        "objectSize": {
                            "height": {"magnitude": 300, "unit": "PT"},
                            "width": {"magnitude": 0, "unit": "PT"},
                        },
                    }
                }
            ]

            result = docs.documents().batchUpdate(
                documentId=document_id,
                body={"requests": requests},
            ).execute()

            replies = result.get("replies", [{}])
            image_props = None
            if replies and "insertInlineImage" in replies[0]:
                image_props = replies[0]["insertInlineImage"].get("objectId")

            return json.dumps(
                {
                    "status": "success",
                    "document_id": document_id,
                    "image_object_id": image_props,
                    "image_url": image_url,
                    "position_index": insert_index,
                },
                indent=2,
            )
        except HttpError as e:
            logger.error(f"Docs insert image error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "docs_error"})
        except Exception as e:
            logger.error(f"Docs insert image error: {e}")
            return json.dumps({"error": str(e), "type": "docs_error"})

    logger.info("Google Docs MCP tools registered successfully")
