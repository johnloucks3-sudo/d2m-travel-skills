"""
Dreams2Memories WhatsApp MCP Module
====================================
Send WhatsApp messages via Twilio API.
Trial account -- verified numbers only.
"""
import json
import logging

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from twilio.rest import Client

logger = logging.getLogger(__name__)

ACCOUNT_SID = "ACdc4e7b2beacb84b18c8b49ab8c8369cb"
AUTH_TOKEN = "***REMOVED-SECRET***"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio sandbox number


def register_whatsapp_tools(mcp: FastMCP):

    @mcp.tool(name="send_whatsapp", annotations={"title": "Send WhatsApp Message", "readOnlyHint": False})
    async def send_whatsapp(
        to_number: str = Field(..., description="Recipient phone (E.164 format, e.g. '+17192910742')"),
        message: str = Field(..., description="Message text to send"),
    ) -> str:
        """Send a WhatsApp message via Twilio. Trial: verified numbers only."""
        try:
            client = Client(ACCOUNT_SID, AUTH_TOKEN)
            msg = client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=message,
                to=f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number,
            )
            return json.dumps({
                "status": "sent",
                "sid": msg.sid,
                "to": to_number,
                "body_preview": message[:100],
            }, indent=2)
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return json.dumps({"error": str(e), "type": "whatsapp_error"})
