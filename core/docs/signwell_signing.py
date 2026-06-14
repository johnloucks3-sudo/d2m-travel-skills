#!/usr/bin/env python3
"""
signwell_signing.py — SignWell document signing for D2M client agreements.

STATUS: STUB — API key required.
  1. Create SignWell account: https://www.signwell.com/signup/
  2. Go to Settings → API → copy API key
  3. Set SIGNWELL_API_KEY in .env or creds/signwell_credentials.json
  4. This wrapper is ready to activate.

Free tier: 3 documents/month. API Plan: $8/month for unlimited.
D2M use cases:
  - Client service agreements / Terms of Service (before booking)
  - Group booking authorization (12-pax Spencer Grand Tour)
  - Deposit authorization confirmations

Authority: SO-2026-05-04 §XII.
"""

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/signwell_credentials.json"
API_BASE = "https://www.signwell.com/api/v1"


def _get_key() -> str:
    key = os.environ.get("SIGNWELL_API_KEY", "")
    if not key and CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text())
        key = data.get("SIGNWELL_API_KEY", "")
    if not key:
        raise RuntimeError(
            "SIGNWELL_API_KEY not set.\n"
            "1. Create account: https://www.signwell.com/signup/\n"
            "2. Settings → API → copy key\n"
            "3. Set in creds/signwell_credentials.json or .env"
        )
    return key


def _headers() -> dict:
    return {
        "X-Api-Key": _get_key(),
        "Content-Type": "application/json",
    }


def send_document(
    template_id: str,
    recipients: list[dict],
    fields: Optional[dict] = None,
    subject: str = "D2M Travel — Document for Signature",
    message: str = "Please review and sign the attached document.",
    test_mode: bool = True,
) -> dict:
    """Send a document for signature from a template.

    Args:
        template_id: SignWell template ID (from your SignWell account)
        recipients: List of {name, email, role} dicts
        fields: Pre-fill template fields {field_name: value}
        subject: Email subject line
        message: Email message body
        test_mode: True = no real signature, no billing. Set False for production.

    Returns:
        SignWell document creation response with document ID, signing URL
    """
    payload = {
        "template_id": template_id,
        "subject": subject,
        "message": message,
        "test_mode": test_mode,
        "recipients": recipients,
    }
    if fields:
        payload["fields"] = [[{"api_id": k, "value": v} for k, v in fields.items()]]

    resp = requests.post(f"{API_BASE}/documents", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_document_status(document_id: str) -> dict:
    """Check status of a sent document (pending / signed / declined)."""
    resp = requests.get(f"{API_BASE}/documents/{document_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def list_templates() -> list[dict]:
    """List all templates in the D2M SignWell account."""
    resp = requests.get(f"{API_BASE}/templates", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def download_signed_pdf(document_id: str, output_path: str) -> str:
    """Download the signed PDF for a completed document."""
    resp = requests.get(f"{API_BASE}/documents/{document_id}/download_pdf", headers=_headers(), timeout=30)
    resp.raise_for_status()
    Path(output_path).write_bytes(resp.content)
    return output_path


# ── Optional type annotation fix ────────────────────────────────────────────
try:
    from typing import Optional
except ImportError:
    pass

if __name__ == "__main__":
    print("SignWell stub — API key required.")
    print("Create account and API plan at: https://www.signwell.com/signup/")
