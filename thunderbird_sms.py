"""
Dreams2Memories SMS Notification MCP Module
============================================
Sends SMS via T-Mobile email-to-SMS gateway using Gmail OAuth.
"""
import json
import logging
import base64
import asyncio
from email.mime.text import MIMEText

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from thunderbird_gmail import _get_gmail_service, USER_EMAIL

logger = logging.getLogger(__name__)
SMS_GATEWAY = "17192910742@tmomail.net"
SMS_MAX_LEN = 160

def _sync_send(message: str, subject: str) -> dict:
    service = _get_gmail_service()
    truncated = len(message) > SMS_MAX_LEN
    msg_text = message[:SMS_MAX_LEN] if truncated else message
    
    msg = MIMEText(msg_text, 'plain')
    msg["to"] = SMS_GATEWAY
    msg["from"] = USER_EMAIL
    if subject:
        msg["subject"] = subject
        
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    
    return {
        "status": "sent",
        "to": SMS_GATEWAY,
        "chars": len(msg_text),
        "truncated": truncated
    }

def register_sms_tools(mcp: FastMCP):

    @mcp.tool(name="send_sms_notification", annotations={"title": "Send SMS Notification", "readOnlyHint": False})
    async def send_sms_notification(
        message: str = Field(..., description="SMS message text (160 char max recommended)"),
        subject: str = Field("D2M Alert", description="SMS subject/header"),
    ) -> str:
        """Send an SMS notification to John's phone via T-Mobile email gateway."""
        try:
            # Run the blocking Google API call in a separate thread so it doesn't crash the Starlette event loop
            result = await asyncio.to_thread(_sync_send, message, subject)
            return json.dumps(result)
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return json.dumps({"error": str(e), "type": "sms_error"})
