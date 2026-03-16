"""
Dreams2Memories SMS Notification MCP Module
============================================
Sends SMS via T-Mobile email-to-SMS gateway using Gmail OAuth.
"""
import json
import logging
import base64
from email.mime.text import MIMEText

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from thunderbird_gmail import _get_gmail_service, USER_EMAIL

logger = logging.getLogger(__name__)
SMS_GATEWAY = "7192910742@tmomail.net"
SMS_MAX_LEN = 160


def register_sms_tools(mcp: FastMCP):

    @mcp.tool(name="send_sms_notification", annotations={"title": "Send SMS Notification", "readOnlyHint": False})
    async def send_sms_notification(
        message: str = Field(..., description="SMS message text (160 char max recommended)"),
        subject: str = Field("D2M Alert", description="SMS subject/header"),
    ) -> str:
        """Send an SMS notification to John's phone via T-Mobile email gateway."""
        try:
            service = _get_gmail_service()
            truncated = len(message) > SMS_MAX_LEN
            msg = MIMEText(message[:SMS_MAX_LEN] if truncated else message)
            msg["to"] = SMS_GATEWAY
            msg["from"] = USER_EMAIL
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return json.dumps({
                "status": "sent",
                "to": SMS_GATEWAY,
                "subject": subject,
                "chars": len(message),
                "truncated": truncated,
            }, indent=2)
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return json.dumps({"error": str(e), "type": "sms_error"})
