#!/usr/bin/env python3
"""
WF-17 Draft Hygiene Audit — MISSION-232
Audits d2mconcierge Gmail drafts, deletes truly empty ones, reports on client-ready drafts.

Rules:
- EMPTY = no Subject AND no To AND empty body (after full decode, strip HTML+whitespace)
- If ANY of subject/to/body present → KEEP
- Never send, never touch mission_board.json
- Nichols/Kuklinski drafts flagged explicitly
"""

import base64
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


TOKEN_PATH = "/home/john/Thunderbird/config/persona_gmail_token.json"
REPORT_PATH = "/home/john/Thunderbird/output/wf17_draft_audit_20260616.md"
EXPECTED_ACCOUNT = "d2mconcierge"  # partial match
USER = "me"

KUKLINSKI_HOLD_DATE = "2026-07-15"
MCLEOD_HOLD_DATE = "2026-07-07"


def build_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    service = build("gmail", "v1", credentials=creds)
    return service


def verify_account(service):
    profile = service.users().getProfile(userId=USER).execute()
    email = profile.get("emailAddress", "")
    print(f"[ACCOUNT VERIFY] Authenticated as: {email}")
    if EXPECTED_ACCOUNT not in email.lower():
        raise ValueError(
            f"WRONG ACCOUNT: expected d2mconcierge, got {email}. ABORTING — do NOT delete from wrong account."
        )
    return email


def list_all_drafts(service):
    """List all draft IDs, paginating to get all."""
    drafts = []
    page_token = None
    while True:
        params = {"userId": USER, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        result = service.users().drafts().list(**params).execute()
        batch = result.get("drafts", [])
        drafts.extend(batch)
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    print(f"[LIST] Found {len(drafts)} total drafts")
    return drafts


def get_draft_metadata(service, draft_id):
    """Get draft with metadata format (cheap - for To/Subject/snippet)."""
    try:
        draft = service.users().drafts().get(
            userId=USER, id=draft_id, format="metadata"
        ).execute()
        return draft
    except HttpError as e:
        print(f"  [ERROR] Failed to get metadata for draft {draft_id}: {e}")
        return None


def extract_headers(message):
    """Extract To, Subject from message headers."""
    headers = {}
    payload = message.get("payload", {})
    for h in payload.get("headers", []):
        name = h.get("name", "").lower()
        if name in ("to", "subject", "from", "date"):
            headers[name] = h.get("value", "").strip()
    return headers


def get_draft_full(service, draft_id):
    """Get draft with full format for body decode."""
    try:
        draft = service.users().drafts().get(
            userId=USER, id=draft_id, format="full"
        ).execute()
        return draft
    except HttpError as e:
        print(f"  [ERROR] Failed to get full draft {draft_id}: {e}")
        return None


def decode_b64(data):
    """Decode base64url-encoded Gmail body data."""
    if not data:
        return ""
    try:
        padded = data + "=" * (4 - len(data) % 4) if len(data) % 4 else data
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_body_text(payload):
    """Recursively extract all text from MIME payload."""
    texts = []

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        if data:
            decoded = decode_b64(data)
            texts.append(decoded)
        for subpart in part.get("parts", []):
            walk(subpart)

    walk(payload)
    return "".join(texts)


def strip_html(text):
    """Strip HTML tags, decode entities, collapse whitespace."""
    # Remove HTML tags
    no_tags = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    no_tags = no_tags.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    # Collapse whitespace
    stripped = re.sub(r"\s+", " ", no_tags).strip()
    return stripped


def is_body_empty(payload, snippet=""):
    """Return True only if the full decoded body is empty/whitespace-only."""
    # First check snippet as a quick hint
    if snippet and snippet.strip():
        return False  # snippet has content, definitely not empty

    # Full body decode
    raw_body = extract_body_text(payload)
    stripped = strip_html(raw_body).strip()
    return len(stripped) == 0


def classify_draft(subject, to_addr, snippet, payload):
    """
    Returns (is_truly_empty, body_stripped)
    truly_empty = no subject AND no to AND no body
    """
    has_subject = bool(subject and subject.strip())
    has_to = bool(to_addr and to_addr.strip())
    body_empty = is_body_empty(payload, snippet)

    is_empty = (not has_subject) and (not has_to) and body_empty
    return is_empty


def is_nichols_or_kuklinski(subject, to_addr, snippet):
    """Check if draft relates to Nichols or Kuklinski."""
    text = " ".join([subject or "", to_addr or "", snippet or ""]).lower()
    keywords = ["nichols", "kuklinski", "kyle", "amy", "roger", "carla", "josh"]
    for kw in keywords:
        if kw in text:
            return True
    return False


def delete_draft(service, draft_id, dry_run=False):
    """Delete a draft. dry_run=True just logs."""
    if dry_run:
        print(f"  [DRY RUN] Would delete draft {draft_id}")
        return True
    try:
        service.users().drafts().delete(userId=USER, id=draft_id).execute()
        print(f"  [DELETED] Draft {draft_id}")
        return True
    except HttpError as e:
        print(f"  [ERROR] Failed to delete draft {draft_id}: {e}")
        return False


def main():
    print("=" * 60)
    print("WF-17 DRAFT HYGIENE AUDIT — MISSION-232")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    service = build_service()
    account_email = verify_account(service)

    all_draft_refs = list_all_drafts(service)

    if not all_draft_refs:
        print("[INFO] No drafts found.")
        write_report(account_email, [], [], [], 0)
        return

    # Collect all draft details
    all_drafts = []
    truly_empty_candidates = []
    real_drafts = []
    nichols_kuklinski_drafts = []

    print(f"\n[PHASE 1] Fetching metadata for {len(all_draft_refs)} drafts...")
    for ref in all_draft_refs:
        draft_id = ref["id"]
        meta = get_draft_metadata(service, draft_id)
        if not meta:
            continue

        message = meta.get("message", {})
        headers = extract_headers(message)
        snippet = message.get("snippet", "")

        subject = headers.get("subject", "")
        to_addr = headers.get("to", "")
        from_addr = headers.get("from", "")
        date_hdr = headers.get("date", "")

        draft_info = {
            "id": draft_id,
            "subject": subject,
            "to": to_addr,
            "from": from_addr,
            "date": date_hdr,
            "snippet": snippet,
        }

        # Quick check: if subject or to is present, it's definitely NOT empty
        has_subject = bool(subject and subject.strip())
        has_to = bool(to_addr and to_addr.strip())

        if has_subject or has_to or (snippet and snippet.strip()):
            # Definitely a real draft — no need to fetch full
            real_drafts.append(draft_info)
            if is_nichols_or_kuklinski(subject, to_addr, snippet):
                nichols_kuklinski_drafts.append(draft_info)
        else:
            # Ambiguous — need full body decode
            truly_empty_candidates.append(draft_info)

    print(f"\n[PHASE 2] Deep-checking {len(truly_empty_candidates)} ambiguous drafts (no subject/to/snippet)...")

    deleted_ids = []
    kept_from_ambiguous = []

    for draft_info in truly_empty_candidates:
        draft_id = draft_info["id"]
        print(f"  Fetching full body for draft {draft_id}...")
        full_draft = get_draft_full(service, draft_id)
        if not full_draft:
            # Can't verify — keep it
            print(f"    → Cannot fetch full — KEEPING draft {draft_id}")
            kept_from_ambiguous.append(draft_info)
            continue

        message = full_draft.get("message", {})
        payload = message.get("payload", {})
        snippet = message.get("snippet", "")

        is_empty = classify_draft(
            draft_info["subject"],
            draft_info["to"],
            snippet,
            payload
        )

        if is_empty:
            print(f"    → TRULY EMPTY — will delete draft {draft_id}")
            deleted_ids.append(draft_id)
        else:
            # Has body content
            raw_body = extract_body_text(payload)
            body_preview = strip_html(raw_body)[:80]
            draft_info["body_preview"] = body_preview
            print(f"    → Has body content: '{body_preview[:60]}...' — KEEPING")
            kept_from_ambiguous.append(draft_info)
            if is_nichols_or_kuklinski(draft_info["subject"], draft_info["to"], snippet):
                nichols_kuklinski_drafts.append(draft_info)

    # Log candidates before deleting
    print(f"\n[PHASE 3] About to delete {len(deleted_ids)} truly empty drafts:")
    for did in deleted_ids:
        print(f"  - {did}")

    # Execute deletions
    actual_deleted = 0
    delete_errors = []
    for did in deleted_ids:
        success = delete_draft(service, did)
        if success:
            actual_deleted += 1
        else:
            delete_errors.append(did)

    # Combine real drafts + kept ambiguous
    all_real = real_drafts + kept_from_ambiguous
    all_drafts_combined = all_real  # for report

    # Write report
    write_report(
        account_email,
        all_drafts_combined,
        nichols_kuklinski_drafts,
        deleted_ids,
        actual_deleted,
        delete_errors
    )

    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Total drafts found: {len(all_draft_refs)}")
    print(f"  Truly empty deleted: {actual_deleted}")
    print(f"  Real drafts remaining: {len(all_drafts_combined)}")
    print(f"  Nichols/Kuklinski drafts: {len(nichols_kuklinski_drafts)}")
    print(f"  Delete errors: {len(delete_errors)}")
    print(f"  Report written: {REPORT_PATH}")
    print("=" * 60)

    return actual_deleted, len(all_drafts_combined), nichols_kuklinski_drafts


def write_report(account_email, real_drafts, nk_drafts, deleted_ids, actual_deleted, delete_errors=None):
    """Write the audit report to output/wf17_draft_audit_20260616.md"""
    if delete_errors is None:
        delete_errors = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    lines = []
    lines.append(f"# WF-17 Draft Audit — d2mconcierge")
    lines.append(f"**Date:** {now}  ")
    lines.append(f"**Account:** {account_email}  ")
    lines.append(f"**Mission:** MISSION-232 WF-17 Draft Hygiene  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total drafts before audit | {len(deleted_ids) + len(real_drafts)} |")
    lines.append(f"| Truly empty drafts deleted | {actual_deleted} |")
    lines.append(f"| Delete errors (kept) | {len(delete_errors)} |")
    lines.append(f"| Real drafts remaining | {len(real_drafts)} |")
    lines.append(f"| Nichols/Kuklinski drafts found | {len(nk_drafts)} |")
    lines.append("")

    if deleted_ids:
        lines.append("## Deleted Empty Drafts")
        lines.append("")
        lines.append("These had NO subject, NO To address, and NO body content:")
        lines.append("")
        for did in deleted_ids:
            status = "DELETED" if did not in delete_errors else "ERROR — kept"
            lines.append(f"- `{did}` — {status}")
        lines.append("")

    # Nichols/Kuklinski section
    lines.append("## Nichols / Kuklinski Drafts (WF-17 Queue)")
    lines.append("")
    if nk_drafts:
        lines.append("⚠️ **DO NOT SEND** — These require Commander send authority (WF-17 gate).  ")
        lines.append("Kuklinski emails on HOLD until **2026-07-15** (Commander directive).  ")
        lines.append("")
        lines.append("| Draft ID | Subject | To | Status |")
        lines.append("|----------|---------|-----|--------|")
        for d in nk_drafts:
            subject = d.get("subject") or "*(no subject)*"
            to_addr = d.get("to") or "*(no to)*"
            draft_id = d.get("id", "")
            # Determine hold status
            subject_lower = subject.lower()
            to_lower = to_addr.lower()
            combined = subject_lower + " " + to_lower + " " + d.get("snippet","").lower()
            if "kuklinski" in combined or "kyle" in combined or "roger" in combined or "josh" in combined:
                status = f"HOLD until {KUKLINSKI_HOLD_DATE}"
            elif "nichols" in combined:
                status = "AWAITING COMMANDER SEND"
            else:
                status = "REVIEW"
            lines.append(f"| `{draft_id}` | {subject} | {to_addr} | {status} |")
        lines.append("")
    else:
        lines.append("*No Nichols or Kuklinski drafts found in d2mconcierge.*")
        lines.append("")

    # All remaining real drafts table
    lines.append("## All Remaining Drafts")
    lines.append("")
    if real_drafts:
        lines.append("| Draft ID | Subject | To | Snippet |")
        lines.append("|----------|---------|-----|---------|")
        for d in sorted(real_drafts, key=lambda x: x.get("subject") or ""):
            draft_id = d.get("id", "")
            subject = (d.get("subject") or "*(no subject)*").replace("|", "\\|")
            to_addr = (d.get("to") or "*(no to)*").replace("|", "\\|")
            snippet = (d.get("snippet") or d.get("body_preview") or "").strip()[:80].replace("|", "\\|")
            lines.append(f"| `{draft_id}` | {subject} | {to_addr} | {snippet} |")
        lines.append("")
    else:
        lines.append("*No real drafts remaining.*")
        lines.append("")

    # WF-17 send-ready assessment
    lines.append("## WF-17 Send-Ready Assessment")
    lines.append("")
    lines.append("Drafts assessed as client-send-ready (has Subject + To + non-empty body):")
    lines.append("")
    send_ready = [
        d for d in real_drafts
        if d.get("subject") and d.get("to") and (d.get("snippet") or d.get("body_preview"))
    ]
    if send_ready:
        lines.append("| Subject | To | Action |")
        lines.append("|---------|-----|--------|")
        for d in send_ready:
            subject = (d.get("subject") or "").replace("|", "\\|")
            to_addr = (d.get("to") or "").replace("|", "\\|")
            combined = (subject + " " + to_addr).lower()
            if "kuklinski" in combined or "kyle" in combined:
                action = f"HOLD — Jul 15"
            elif "nichols" in combined:
                action = "AWAITING COMMANDER SEND"
            elif "mcleod" in combined or "mcglasson" in combined:
                action = "HOLD — Jul 7 (McLeod aboard ship)"
            else:
                action = "Review for Commander send"
            lines.append(f"| {subject} | {to_addr} | {action} |")
    else:
        lines.append("*No drafts assessed as fully send-ready at this time.*")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by scripts/wf17_draft_audit.py · {now}*")

    report_text = "\n".join(lines)
    Path(REPORT_PATH).write_text(report_text)
    print(f"\n[REPORT] Written to {REPORT_PATH}")


if __name__ == "__main__":
    result = main()
