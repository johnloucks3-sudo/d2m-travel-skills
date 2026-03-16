"""
Dreams2Memories Gmail MCP Module
================================

Extends the travel MCP server with Gmail operations:
- Search messages by query
- Read individual messages
- Read full threads
- List drafts
- Create drafts (never auto-send for safety)

Uses OAuth 2.0 Desktop flow for personal Gmail (johnloucks3@gmail.com).
First run requires browser authorization; refresh token is saved for
all subsequent runs.

Integrates with: travel_mcp_server.py
Dependencies: google-api-python-client, google-auth, google-auth-oauthlib
"""

import json
import logging
import time
import functools
import base64
import mimetypes
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
EMAIL_SENT_LOG = THUNDERBIRD_DIR / "logs" / "email_sent.log"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
USER_EMAIL = "johnloucks3@gmail.com"
D2M_FROM_ADDRESS = "concierge@d2mluxury.quest"
COMMANDER_D2M_EMAIL = "john@d2mluxury.quest"
COMMANDER_EMAIL = "johnloucks3@gmail.com"

# Persona display names for Send As support
PERSONA_DISPLAY_NAMES = {
    "COS": "Victoria Hale, D2M Travel",
    "EXEC": "Naia Solberg-Vega, D2M Travel",
    "A2": "Marcus Dembe, D2M Travel",
    "A3": "Dani Moreau, D2M Travel",
    "A5": "Ryan Castillo, D2M Travel",
    "A6": "Luna Voss, D2M Travel",
    "A9": "Vic Harlan, D2M Travel",
    "A10": "Tomoko Ikeda, D2M Travel",
    "CH": "James Washington, D2M Travel",
    "A12": "ELON, D2M Travel",
    "D2M": "Dreams2Memories Travel",
    "CONCIERGE": "D2M Concierge",
    "COMMANDER": "John Loucks, Dreams2Memories Travel",
}

logger = logging.getLogger(__name__)

# Cached service instance
_gmail_service = None


def _get_gmail_service():
    """Authenticate and return a cached Gmail API service instance.

    Uses OAuth 2.0 Desktop flow:
    - If gmail_token.json exists, loads and auto-refreshes the token
    - If no token exists, raises a clear error pointing to --authorize
    """
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service

    creds = None

    # Load existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            TOKEN_FILE.write_text(creds.to_json())
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            creds = None

    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail not authorized. Run:  python3 thunderbird_gmail.py --authorize\n"
            f"OAuth credentials file needed: {OAUTH_CREDENTIALS_FILE}"
        )

    _gmail_service = build("gmail", "v1", credentials=creds)
    return _gmail_service


def authorize_gmail():
    """Run the one-time OAuth 2.0 authorization flow.

    Opens a browser for user consent, saves the refresh token to gmail_token.json.
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: OAuth credentials file not found: {OAUTH_CREDENTIALS_FILE}")
        print()
        print("To create it:")
        print("  1. Go to console.cloud.google.com > project d2m-python-pipeline")
        print("  2. APIs & Services > Credentials > Create Credentials > OAuth client ID")
        print("  3. Application type: Desktop app")
        print("  4. Download JSON and save as:")
        print(f"     {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"Authorization successful! Token saved to {TOKEN_FILE}")
    print(f"Email: {USER_EMAIL}")
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
                    logger.warning(f"Gmail API {e.resp.status}, retry {attempt+1}/{retries} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
    return wrapper


def _decode_body(payload):
    """Extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Walk multipart parts
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # Nested multipart
        if part.get("parts"):
            result = _decode_body(part)
            if result:
                return result
    return ""


def _extract_headers(headers, keys=None):
    """Extract specific headers from a Gmail message header list."""
    if keys is None:
        keys = {"From", "To", "Subject", "Date", "Cc", "Bcc"}
    return {h["name"]: h["value"] for h in headers if h["name"] in keys}


def register_gmail_tools(mcp):
    """Register all Gmail tools with the MCP server."""
    from mcp.server.fastmcp import FastMCP  # deferred — not needed by standalone importers

    @mcp.tool(
        name="gmail_search_messages",
        annotations={"title": "Search Gmail Messages", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_search_messages(
        query: str = Field(..., description="Gmail search query (same syntax as Gmail search bar, e.g. 'from:silversea subject:confirmation')"),
        max_results: int = Field(10, description="Max messages to return (1-50)"),
    ) -> str:
        """Search Gmail messages using standard Gmail query syntax."""
        try:
            service = _get_gmail_service()
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=min(max_results, 50))
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return json.dumps({"status": "success", "query": query, "count": 0, "messages": []}, indent=2)

            # Fetch summary metadata for each message
            summaries = []
            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"])
                    .execute()
                )
                headers = _extract_headers(msg.get("payload", {}).get("headers", []))
                summaries.append({
                    "id": msg["id"],
                    "threadId": msg["threadId"],
                    "snippet": msg.get("snippet", ""),
                    "labels": msg.get("labelIds", []),
                    **headers,
                })

            return json.dumps({"status": "success", "query": query, "count": len(summaries), "messages": summaries}, indent=2)

        except HttpError as e:
            logger.error(f"Gmail search error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except RuntimeError as e:
            return json.dumps({"error": str(e), "type": "auth_error"})
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_read_message",
        annotations={"title": "Read Gmail Message", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_read_message(
        message_id: str = Field(..., description="Gmail message ID (from search results)"),
    ) -> str:
        """Read the full content of a specific Gmail message."""
        try:
            service = _get_gmail_service()
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = _extract_headers(payload.get("headers", []))
            body = _decode_body(payload)

            # Truncate very long emails
            if len(body) > 30000:
                body = body[:30000] + "\n\n... [TRUNCATED — email exceeds 30K chars]"

            # Extract attachment info (don't download, just list)
            attachments = []
            for part in payload.get("parts", []):
                if part.get("filename"):
                    attachments.append({
                        "filename": part["filename"],
                        "mimeType": part.get("mimeType", "unknown"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": part.get("body", {}).get("attachmentId", ""),
                    })

            return json.dumps({
                "status": "success",
                "id": msg["id"],
                "threadId": msg["threadId"],
                "labels": msg.get("labelIds", []),
                **headers,
                "body": body,
                "attachments": attachments,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail read error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail read error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_read_thread",
        annotations={"title": "Read Gmail Thread", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_read_thread(
        thread_id: str = Field(..., description="Gmail thread ID"),
    ) -> str:
        """Read all messages in a Gmail thread."""
        try:
            service = _get_gmail_service()
            thread = (
                service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )

            messages = []
            for msg in thread.get("messages", []):
                payload = msg.get("payload", {})
                headers = _extract_headers(payload.get("headers", []))
                body = _decode_body(payload)
                if len(body) > 15000:
                    body = body[:15000] + "\n\n... [TRUNCATED]"
                messages.append({
                    "id": msg["id"],
                    **headers,
                    "snippet": msg.get("snippet", ""),
                    "body": body,
                })

            return json.dumps({
                "status": "success",
                "threadId": thread_id,
                "message_count": len(messages),
                "messages": messages,
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail thread error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail thread error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_list_drafts",
        annotations={"title": "List Gmail Drafts", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_list_drafts(
        max_results: int = Field(10, description="Max drafts to return (1-25)"),
    ) -> str:
        """List existing Gmail drafts."""
        try:
            service = _get_gmail_service()
            results = (
                service.users()
                .drafts()
                .list(userId="me", maxResults=min(max_results, 25))
                .execute()
            )

            drafts = results.get("drafts", [])
            if not drafts:
                return json.dumps({"status": "success", "count": 0, "drafts": []}, indent=2)

            draft_summaries = []
            for draft_ref in drafts:
                draft = (
                    service.users()
                    .drafts()
                    .get(userId="me", id=draft_ref["id"], format="metadata")
                    .execute()
                )
                msg = draft.get("message", {})
                headers = _extract_headers(msg.get("payload", {}).get("headers", []))
                draft_summaries.append({
                    "draft_id": draft["id"],
                    "message_id": msg.get("id", ""),
                    "snippet": msg.get("snippet", ""),
                    **headers,
                })

            return json.dumps({"status": "success", "count": len(draft_summaries), "drafts": draft_summaries}, indent=2)

        except HttpError as e:
            logger.error(f"Gmail drafts error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail drafts error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_create_draft",
        annotations={"title": "Create Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_create_draft(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
        bcc: Optional[str] = Field(None, description="BCC recipients (comma-separated)"),
        reply_to_message_id: Optional[str] = Field(None, description="Message ID to reply to (creates reply draft)"),
        attachment_paths: Optional[List[str]] = Field(None, description="List of absolute file paths to attach (e.g. PDFs, images)"),
        from_persona: Optional[str] = Field(None, description="Persona ID (e.g. 'A3', 'CONCIERGE') — sets From to persona display name via concierge@d2mluxury.quest"),
    ) -> str:
        """Create a Gmail draft with optional file attachments. Does NOT send — saves as draft for review.

        This is intentionally draft-only for safety. John reviews and sends manually.
        Supports multiple attachments — pass a list of absolute file paths.
        When from_persona is set, uses the D2M persona display name with concierge@d2mluxury.quest as the From address.
        """
        try:
            service = _get_gmail_service()

            message = MIMEMultipart()
            message["to"] = to

            # Set From based on persona
            if from_persona and from_persona.upper() in PERSONA_DISPLAY_NAMES:
                pid = from_persona.upper()
                display_name = PERSONA_DISPLAY_NAMES[pid]
                from_addr = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS
                message["from"] = f'"{display_name}" <{from_addr}>'
                message["reply-to"] = COMMANDER_EMAIL
            else:
                message["from"] = USER_EMAIL

            message["subject"] = subject
            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            message.attach(MIMEText(body, "plain"))

            # Attach files if provided
            attached_files = []
            if attachment_paths:
                for file_path_str in attachment_paths:
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        return json.dumps({"error": f"Attachment not found: {file_path}", "type": "file_error"})
                    if not file_path.is_file():
                        return json.dumps({"error": f"Not a file: {file_path}", "type": "file_error"})

                    content_type, _ = mimetypes.guess_type(str(file_path))
                    if content_type is None:
                        content_type = "application/octet-stream"
                    main_type, sub_type = content_type.split("/", 1)

                    with open(file_path, "rb") as f:
                        part = MIMEBase(main_type, sub_type)
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=file_path.name)
                    message.attach(part)
                    attached_files.append(file_path.name)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            draft_body = {"message": {"raw": raw}}

            if reply_to_message_id:
                # Get the thread ID from the original message
                orig = (
                    service.users()
                    .messages()
                    .get(userId="me", id=reply_to_message_id, format="minimal")
                    .execute()
                )
                draft_body["message"]["threadId"] = orig.get("threadId", "")

            draft = (
                service.users()
                .drafts()
                .create(userId="me", body=draft_body)
                .execute()
            )

            result = {
                "status": "success",
                "action": "draft_created",
                "draft_id": draft["id"],
                "to": to,
                "subject": subject,
                "note": "Draft saved — NOT sent. Review in Gmail before sending.",
            }
            if attached_files:
                result["attachments"] = attached_files
                result["attachment_count"] = len(attached_files)

            return json.dumps(result, indent=2)

        except HttpError as e:
            logger.error(f"Gmail draft create error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail draft create error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_get_profile",
        annotations={"title": "Get Gmail Profile", "readOnlyHint": True},
    )
    @_retry_on_error
    async def gmail_get_profile() -> str:
        """Get Gmail profile info. Useful as a connectivity test."""
        try:
            service = _get_gmail_service()
            profile = service.users().getProfile(userId="me").execute()
            return json.dumps({
                "status": "success",
                "email": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal"),
                "threads_total": profile.get("threadsTotal"),
                "history_id": profile.get("historyId"),
            }, indent=2)
        except HttpError as e:
            logger.error(f"Gmail profile error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except RuntimeError as e:
            return json.dumps({"error": str(e), "type": "auth_error"})
        except Exception as e:
            logger.error(f"Gmail profile error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    # ------------------------------------------------------------------
    # DRAFT APPROVAL — promote draft to sent, or update draft content
    # ------------------------------------------------------------------

    @mcp.tool(
        name="gmail_send_draft",
        annotations={"title": "Send Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_send_draft(
        draft_id: str = Field(..., description="Gmail draft ID (from gmail_list_drafts or draft creation)"),
    ) -> str:
        """Send an existing Gmail draft. Promotes a draft to a sent message.

        Used by the Commander approval flow: Dani creates draft → Commander approves → COS sends.
        WARNING: This SENDS the email. Use only after Commander approval.
        """
        try:
            service = _get_gmail_service()
            sent = (
                service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            # Log the send action
            msg_id = sent.get("id", "unknown")
            _log_email_action(
                to="(from draft)", subject="(from draft)",
                persona_id="APPROVED", auto_send=True, ref_id=msg_id,
            )

            return json.dumps({
                "status": "success",
                "action": "draft_sent",
                "message_id": msg_id,
                "draft_id": draft_id,
                "labels": sent.get("labelIds", []),
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail send draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail send draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_update_draft",
        annotations={"title": "Update Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_update_draft(
        draft_id: str = Field(..., description="Gmail draft ID to update"),
        body: Optional[str] = Field(None, description="New email body text (replaces existing body)"),
        subject: Optional[str] = Field(None, description="New subject line (replaces existing)"),
    ) -> str:
        """Update an existing Gmail draft's body or subject.

        Used when Commander edits a Dani draft before approving.
        Preserves all other fields (to, from, cc, attachments).
        """
        try:
            service = _get_gmail_service()

            # Fetch the existing draft to preserve fields
            existing = (
                service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="full")
                .execute()
            )
            msg = existing.get("message", {})
            payload = msg.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            # Build updated message preserving original fields
            updated = MIMEMultipart()
            updated["to"] = headers.get("To", "")
            updated["from"] = headers.get("From", USER_EMAIL)
            if headers.get("Cc"):
                updated["cc"] = headers["Cc"]
            if headers.get("Bcc"):
                updated["bcc"] = headers["Bcc"]
            if headers.get("Reply-To"):
                updated["reply-to"] = headers["Reply-To"]
            if headers.get("In-Reply-To"):
                updated["In-Reply-To"] = headers["In-Reply-To"]
            if headers.get("References"):
                updated["References"] = headers["References"]

            updated["subject"] = subject if subject else headers.get("Subject", "")

            # Use new body if provided, otherwise keep existing
            if body:
                updated.attach(MIMEText(body, "plain"))
            else:
                existing_body = _decode_body(payload)
                updated.attach(MIMEText(existing_body, "plain"))

            raw = base64.urlsafe_b64encode(updated.as_bytes()).decode("utf-8")
            draft_body = {"message": {"raw": raw}}

            # Preserve thread ID if it was a reply
            thread_id = msg.get("threadId")
            if thread_id:
                draft_body["message"]["threadId"] = thread_id

            result = (
                service.users()
                .drafts()
                .update(userId="me", id=draft_id, body=draft_body)
                .execute()
            )

            return json.dumps({
                "status": "success",
                "action": "draft_updated",
                "draft_id": result.get("id", draft_id),
                "subject": updated["subject"],
                "to": updated["to"],
            }, indent=2)

        except HttpError as e:
            logger.error(f"Gmail update draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail update draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    @mcp.tool(
        name="gmail_delete_draft",
        annotations={"title": "Delete Gmail Draft", "readOnlyHint": False},
    )
    @_retry_on_error
    async def gmail_delete_draft(
        draft_id: str = Field(..., description="Gmail draft ID to delete"),
    ) -> str:
        """Delete a Gmail draft. Used for draft hygiene — removing superseded or stale drafts."""
        try:
            service = _get_gmail_service()
            service.users().drafts().delete(userId="me", id=draft_id).execute()
            return json.dumps({
                "status": "success",
                "action": "draft_deleted",
                "draft_id": draft_id,
            }, indent=2)
        except HttpError as e:
            logger.error(f"Gmail delete draft error: {e}")
            return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
        except Exception as e:
            logger.error(f"Gmail delete draft error: {e}")
            return json.dumps({"error": str(e), "type": "gmail_error"})

    # ------------------------------------------------------------------
    # SEND AS PERSONA — sends email directly via Gmail API
    # ------------------------------------------------------------------

    @mcp.tool(
        name="send_client_email",
        annotations={"title": "Send Email as D2M Persona", "readOnlyHint": False},
    )
    @_retry_on_error
    async def send_client_email(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        persona_id: str = Field("CONCIERGE", description="Persona ID: COS, EXEC, A2, A3, A5, A6, A9, A10, CH, A12, D2M, CONCIERGE"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
    ) -> str:
        """Send an email as a D2M persona via concierge@d2mluxury.quest.

        Uses Gmail Send As to send from the persona display name.
        Reply-To is set to johnloucks3@gmail.com so all replies go to the Commander.
        WARNING: This SENDS immediately — use draft_client_email for Commander review.
        """
        return await _send_or_draft_as_persona(
            service=_get_gmail_service(),
            to=to, subject=subject, body=body,
            persona_id=persona_id, cc=cc,
            auto_send=True,
        )

    @mcp.tool(
        name="draft_client_email",
        annotations={"title": "Draft Email as D2M Persona", "readOnlyHint": False},
    )
    @_retry_on_error
    async def draft_client_email(
        to: str = Field(..., description="Recipient email address"),
        subject: str = Field(..., description="Email subject line"),
        body: str = Field(..., description="Email body (plain text)"),
        persona_id: str = Field("CONCIERGE", description="Persona ID: COS, EXEC, A2, A3, A5, A6, A9, A10, CH, A12, D2M, CONCIERGE"),
        cc: Optional[str] = Field(None, description="CC recipients (comma-separated)"),
    ) -> str:
        """Create a draft email as a D2M persona for Commander review before sending.

        Uses Gmail Send As with the persona display name via concierge@d2mluxury.quest.
        Reply-To is set to johnloucks3@gmail.com. Draft is NOT sent — Commander reviews in Gmail.
        """
        return await _send_or_draft_as_persona(
            service=_get_gmail_service(),
            to=to, subject=subject, body=body,
            persona_id=persona_id, cc=cc,
            auto_send=False,
        )

    logger.info("Gmail tools registered successfully (including Send As persona tools)")


async def _send_or_draft_as_persona(
    service, to: str, subject: str, body: str,
    persona_id: str = "CONCIERGE", cc: Optional[str] = None,
    auto_send: bool = False,
) -> str:
    """Internal helper: build a persona email and either send or save as draft.

    Args:
        service: Gmail API service instance
        to: Recipient email
        subject: Subject line
        body: Plain text body
        persona_id: Key into PERSONA_DISPLAY_NAMES
        cc: Optional CC addresses
        auto_send: True = send immediately, False = create draft for review
    """
    try:
        pid = persona_id.upper()
        display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
        from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

        message = MIMEMultipart()
        message["to"] = to
        message["from"] = f'"{display_name}" <{from_address}>'
        message["reply-to"] = COMMANDER_EMAIL
        message["subject"] = subject
        if cc:
            message["cc"] = cc

        message.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        if auto_send:
            sent = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            action = "sent"
            ref_id = sent.get("id", "unknown")
        else:
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            action = "draft_created"
            ref_id = draft.get("id", "unknown")

            # Tag draft with THUNDERBIRD-Commander-Review for /drafts approval flow
            try:
                draft_msg_id = draft.get("message", {}).get("id")
                if draft_msg_id:
                    _tag_commander_review(service, draft_msg_id)
            except Exception as e:
                logger.warning(f"Failed to tag draft with review label: {e}")

        # Log the action
        _log_email_action(
            to=to, subject=subject, persona_id=pid,
            auto_send=auto_send, ref_id=ref_id,
        )

        result = {
            "status": "success",
            "action": action,
            "id": ref_id,
            "from_persona": pid,
            "from_display": display_name,
            "from_address": from_address,
            "reply_to": COMMANDER_EMAIL,
            "to": to,
            "subject": subject,
        }
        if not auto_send:
            result["note"] = "Draft saved — NOT sent. Review in Gmail before sending."

        return json.dumps(result, indent=2)

    except HttpError as e:
        logger.error(f"Gmail persona email error: {e}")
        return json.dumps({"error": str(e), "status_code": e.resp.status, "type": "gmail_error"})
    except Exception as e:
        logger.error(f"Gmail persona email error: {e}")
        return json.dumps({"error": str(e), "type": "gmail_error"})


COMMANDER_REVIEW_LABEL = "THUNDERBIRD-Commander-Review"
_review_label_id_cache: str = ""


def _tag_commander_review(service, message_id: str):
    """Add the THUNDERBIRD-Commander-Review label to a draft message."""
    global _review_label_id_cache
    if not _review_label_id_cache:
        results = service.users().labels().list(userId="me").execute()
        for lbl in results.get("labels", []):
            if lbl["name"] == COMMANDER_REVIEW_LABEL:
                _review_label_id_cache = lbl["id"]
                break
        if not _review_label_id_cache:
            body = {
                "name": COMMANDER_REVIEW_LABEL,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=body).execute()
            _review_label_id_cache = created["id"]
            logger.info(f"Created Gmail label: {COMMANDER_REVIEW_LABEL}")

    service.users().messages().modify(
        userId="me", id=message_id,
        body={"addLabelIds": [_review_label_id_cache]},
    ).execute()


def _log_email_action(to: str, subject: str, persona_id: str, auto_send: bool, ref_id: str):
    """Append a line to ~/Thunderbird/logs/email_sent.log."""
    try:
        EMAIL_SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        mode = "SENT" if auto_send else "DRAFT"
        line = f"[{ts}] {mode} | persona={persona_id} | to={to} | subject={subject} | id={ref_id}\n"
        with open(EMAIL_SENT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Failed to write email log: {e}")


# ============================================================================
# Standalone convenience functions (importable without MCP)
# ============================================================================

def gmail_send_as_persona(to: str, subject: str, body: str, persona_id: str = "CONCIERGE", cc: Optional[str] = None) -> dict:
    """Synchronous wrapper: send an email as a D2M persona.

    Builds the email with the persona display name as From,
    uses concierge@d2mluxury.quest (or john@d2mluxury.quest for COMMANDER),
    sets Reply-To to johnloucks3@gmail.com,
    and SENDS via Gmail API. Returns dict with message ID and confirmation.
    """
    service = _get_gmail_service()
    pid = persona_id.upper()
    display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
    from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

    message = MIMEMultipart()
    message["to"] = to
    message["from"] = f'"{display_name}" <{from_address}>'
    message["reply-to"] = COMMANDER_EMAIL
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    message.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    _log_email_action(to=to, subject=subject, persona_id=pid, auto_send=True, ref_id=sent.get("id", "unknown"))

    return {
        "status": "success",
        "action": "sent",
        "message_id": sent.get("id"),
        "from_persona": pid,
        "from_display": display_name,
        "from_address": from_address,
        "reply_to": COMMANDER_EMAIL,
        "to": to,
        "subject": subject,
    }


def gmail_send_with_approval(
    to: str, subject: str, body: str,
    persona_id: str = "CONCIERGE", auto_send: bool = False,
    cc: Optional[str] = None,
) -> dict:
    """Safety gate: send or draft based on auto_send flag.

    - auto_send=True: sends directly (for automated payment reminders, follow-ups, confirmations)
    - auto_send=False (default): creates a draft for Commander review
    - Always logs to ~/Thunderbird/logs/email_sent.log
    """
    service = _get_gmail_service()
    pid = persona_id.upper()
    display_name = PERSONA_DISPLAY_NAMES.get(pid, PERSONA_DISPLAY_NAMES["CONCIERGE"])
    from_address = COMMANDER_D2M_EMAIL if pid == "COMMANDER" else D2M_FROM_ADDRESS

    message = MIMEMultipart()
    message["to"] = to
    message["from"] = f'"{display_name}" <{from_address}>'
    message["reply-to"] = COMMANDER_EMAIL
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    message.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    if auto_send:
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        action = "sent"
        ref_id = result.get("id", "unknown")
    else:
        result = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        action = "draft_created"
        ref_id = result.get("id", "unknown")

    _log_email_action(to=to, subject=subject, persona_id=pid, auto_send=auto_send, ref_id=ref_id)

    return {
        "status": "success",
        "action": action,
        "id": ref_id,
        "from_persona": pid,
        "from_display": display_name,
        "from_address": from_address,
        "reply_to": COMMANDER_EMAIL,
        "to": to,
        "subject": subject,
        "auto_send": auto_send,
    }


def gmail_send_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: send (promote) an existing Gmail draft.

    Used by the Telegram approval flow: Commander approves → COS calls this → draft sent.
    Returns dict with message ID and confirmation.
    """
    service = _get_gmail_service()
    sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()

    msg_id = sent.get("id", "unknown")
    _log_email_action(
        to="(from draft)", subject="(from draft)",
        persona_id="APPROVED", auto_send=True, ref_id=msg_id,
    )
    return {
        "status": "success",
        "action": "draft_sent",
        "message_id": msg_id,
        "draft_id": draft_id,
    }


def gmail_get_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: fetch a draft's metadata and body preview.

    Returns dict with to, subject, body_preview, from fields.
    """
    service = _get_gmail_service()
    draft = service.users().drafts().get(userId="me", id=draft_id, format="full").execute()
    msg = draft.get("message", {})
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
    body = _decode_body(payload)

    return {
        "draft_id": draft_id,
        "to": headers.get("To", ""),
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "body_preview": body[:500],
        "body_full": body,
    }


def gmail_delete_draft_sync(draft_id: str) -> dict:
    """Synchronous wrapper: delete a draft."""
    service = _get_gmail_service()
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    return {"status": "success", "action": "draft_deleted", "draft_id": draft_id}


def gmail_list_drafts_sync(max_results: int = 10) -> list[dict]:
    """Synchronous wrapper: list drafts with metadata. Returns list of draft summaries."""
    service = _get_gmail_service()
    results = service.users().drafts().list(userId="me", maxResults=min(max_results, 50)).execute()
    drafts = results.get("drafts", [])
    if not drafts:
        return []

    summaries = []
    for draft_ref in drafts:
        draft = service.users().drafts().get(userId="me", id=draft_ref["id"], format="metadata").execute()
        msg = draft.get("message", {})
        headers = _extract_headers(msg.get("payload", {}).get("headers", []))
        summaries.append({
            "draft_id": draft["id"],
            "message_id": msg.get("id", ""),
            "snippet": msg.get("snippet", ""),
            **headers,
        })
    return summaries


if __name__ == "__main__":
    import sys
    if "--authorize" in sys.argv:
        authorize_gmail()
    else:
        print("Usage: python3 thunderbird_gmail.py --authorize")
        print("  Runs the one-time OAuth 2.0 browser authorization flow.")
        print(f"  Saves token to: {TOKEN_FILE}")
