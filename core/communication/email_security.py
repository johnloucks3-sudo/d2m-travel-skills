"""
email_security.py — Strict origin filtering for Thunderbird OS.
Only Commander (johnloucks3@gmail.com) is permitted to issue commands.
All other traffic is rejected or treated as non-command ingestion.
"""

from typing import Optional

# Authorized Commander
COMMANDER_EMAIL = "johnloucks3@gmail.com"

def verify_sender(sender_email: str) -> bool:
    """
    Verifies if the sender is authorized to issue commands to Thunderbird OS.
    
    Returns:
        bool: True if authorized (Commander), False otherwise.
    """
    # Simple, strict equality check for sender origin
    # In future, add SPF/DKIM verification if needed
    if sender_email.strip().lower() == COMMANDER_EMAIL.lower():
        return True
    return False

def get_sender_status(sender_email: str) -> str:
    """
    Categorizes the sender status for logging/audit purposes.
    """
    if verify_sender(sender_email):
        return "COMMANDER"
    return "UNAUTHORIZED"
