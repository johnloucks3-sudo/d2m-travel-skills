"""
Dreams2Memories Evernote Mirror MCP Module
===========================================
Mirrors content to Evernote via email-in using Gmail OAuth.
"""
import json
import logging
import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from thunderbird_gmail import _get_gmail_service, USER_EMAIL

logger = logging.getLogger(__name__)
EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"


def register_evernote_tools(mcp: FastMCP):

    @mcp.tool(name="mirror_to_evernote", annotations={"title": "Mirror to Evernote", "readOnlyHint": False})
    async def mirror_to_evernote(
        subject: str = Field(..., description="Note title (becomes Evernote note title)"),
        body_text: str = Field("", description="Note content (plain text)"),
        attachment_path: Optional[str] = Field(None, description="Optional file path to attach (e.g. PDF)"),
        notebook: Optional[str] = Field(None, description="Target notebook name (append @NotebookName to subject)"),
    ) -> str:
        """Mirror content to Evernote via email. Subject = note title, body = content."""
        try:
            service = _get_gmail_service()
            title = f"{subject} @{notebook}" if notebook else subject

            if attachment_path:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body_text, "plain"))
                fp = Path(attachment_path)
                if not fp.exists():
                    return json.dumps({"error": f"File not found: {attachment_path}", "type": "file_error"})
                ctype, _ = mimetypes.guess_type(str(fp))
                if ctype is None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                with open(fp, "rb") as f:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=fp.name)
                msg.attach(part)
            else:
                msg = MIMEText(body_text, "plain")

            msg["to"] = EVERNOTE_EMAIL
            msg["from"] = USER_EMAIL
            msg["subject"] = title
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()

            result = {"status": "sent", "to": EVERNOTE_EMAIL, "title": title}
            if attachment_path:
                result["attachment"] = Path(attachment_path).name
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Evernote mirror error: {e}")
            return json.dumps({"error": str(e), "type": "evernote_error"})
