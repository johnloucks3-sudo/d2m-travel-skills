"""
core/email/dani_ag_email_bridge.py — Email Hale Antigravity CLI Integration

Equips Email Hale with full Antigravity CLI capabilities (Gemini 3.6 Flash / 3.1 Pro 1M context)
to analyze complex multi-year client email threads and draft high-fidelity responses
governed by the inviolable WF-17 Commander Review Queue.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from core.relay.contact_ag import contact_ag

logger = logging.getLogger("thunderbird.email_ag")

REVIEW_QUEUE_DIR = Path("/home/john/Thunderbird/review")


def process_client_email_thread_with_ag(
    sender: str,
    subject: str,
    body: str,
    thread_id: str,
    client_dossier_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invokes Antigravity CLI (contact_ag) to process complex client email threads.
    Generates a draft response into /home/john/Thunderbird/review/ under WF-17 gate.
    """
    REVIEW_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    deliverable_path = str(REVIEW_QUEUE_DIR / f"email_draft_{thread_id}.md")

    task_prompt = f"""
    YOU ARE HALE-AG / TALON OPERATING IN EMAIL HALE MODE.
    Analyze incoming client email thread from {sender}:
    Subject: {subject}
    Body:
    {body}

    Instructions:
    1. Inspect client dossier context if available: {client_dossier_path or 'Search data/dossiers/'}.
    2. Extract travel preferences, dates, or booking inquiries.
    3. Draft a complete, warm, executive response conforming to USAF Point Paper / Dani Brand Voice.
    4. Save candidate response to {deliverable_path}.
    5. Ensure the draft is flagged for COMMANDER WF-17 Review.
    """

    res = contact_ag(
        task=task_prompt,
        deliverable_path=deliverable_path,
        from_seat="EmailHale",
        verdict_tag="AG-EMAIL-DRAFT",
        model="gemini-3.6-flash-high"
    )

    is_ok = res.get("ok", False) and Path(deliverable_path).exists()
    return {
        "ok": is_ok,
        "status": "DRAFTED_FOR_WF17_REVIEW" if is_ok else "AG_INVOCATION_FAILED",
        "deliverable_path": deliverable_path,
        "raw_response": res
    }


if __name__ == "__main__":
    print("Email Hale AG CLI Bridge initialized and ready.")
