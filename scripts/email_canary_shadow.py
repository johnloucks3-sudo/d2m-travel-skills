#!/usr/bin/env python3
"""
email_canary_shadow.py — Phase B email-canary shadow classifier

Pulls the last N emails from the same inbox the custom sweep watches (read-only).
For each email, runs TWO shadow classifiers:
  - inbox-zero-style  (rules + LLM; DIRECTIVE / QUESTION / CC-FYI / OTHER)
  - n8n-style         (minimal single-shot LLM prompt; same 4 categories)

Records each classification to the audit DB via record().
NEVER sends, labels, creates missions, or modifies any email.
Fails SOFT: per-email errors are logged and skipped.

Usage:
  python3 scripts/email_canary_shadow.py
  python3 scripts/email_canary_shadow.py --limit 25
  python3 scripts/email_canary_shadow.py --dry-run --limit 5
  python3 scripts/email_canary_shadow.py --source-account johnloucks3
  python3 scripts/email_canary_shadow.py --n8n-ingest          # alias: normal pass, called from n8n
"""

import argparse
import base64
import os
import re
import sqlite3
import sys
import traceback
from pathlib import Path

# ── Repo root on path ──────────────────────────────────────────────────────────
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

# ── Constants ──────────────────────────────────────────────────────────────────
DB_PATH = REPO / "core" / "email" / "email_audit.db"
VALID_CATEGORIES = {"DIRECTIVE", "QUESTION", "CC-FYI", "OTHER"}

# ── Source strings (must match exactly what scoreboard queries) ─────────────
SOURCE_INBOX_ZERO = "inbox-zero-style"
SOURCE_N8N = "n8n-style"

# ── LLM model for canary (cheap, fast) ────────────────────────────────────────
HAIKU_MODEL = "haiku"


# ════════════════════════════════════════════════════════════════════════════════
# Gmail helpers
# ════════════════════════════════════════════════════════════════════════════════

def _get_gmail_service(account: str):
    """Return a Gmail API service object for the requested account.

    account='d2mconcierge'  → gmail_token.json (wing account — matches sweep)
    account='johnloucks3'   → gmail_token_commander.json (commander inbox)
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    if account == "johnloucks3":
        token_paths = [
            REPO / "gmail_token_commander.json",
            REPO / "creds" / "johnloucks3_token.json",
        ]
    else:
        # d2mconcierge — default; matches what the live sweep watches
        token_paths = [
            REPO / "creds" / "gmail_token.json",
            REPO / "gmail_token.json",
        ]

    token_path = None
    for p in token_paths:
        if p.exists():
            token_path = p
            break

    if not token_path:
        raise FileNotFoundError(
            f"No Gmail token found for account={account}. "
            f"Searched: {[str(p) for p in token_paths]}"
        )

    import json
    data = json.loads(token_path.read_text())
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
    )
    return build("gmail", "v1", credentials=creds)


def _fetch_emails(service, limit: int) -> list[dict]:
    """Fetch up to `limit` recent inbox messages. Returns list of email dicts."""
    result = service.users().messages().list(
        userId="me",
        q="in:inbox",
        maxResults=limit,
    ).execute()

    messages = result.get("messages", [])
    emails = []
    for msg_stub in messages:
        msg_id = msg_stub["id"]
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full",
            ).execute()

            headers = {h["name"].lower(): h["value"]
                       for h in msg.get("payload", {}).get("headers", [])}

            subject = headers.get("subject", "(no subject)")
            sender = headers.get("from", "(unknown sender)")
            thread_id = msg.get("threadId", "")

            body = _extract_body(msg)

            emails.append({
                "message_id": msg_id,
                "thread_id": thread_id,
                "subject": subject,
                "sender": sender,
                "body_preview": body[:500],
            })
        except Exception as e:
            print(f"  [WARN] Could not fetch message {msg_id}: {e}", file=sys.stderr)

    return emails


def _extract_body(msg: dict) -> str:
    """Extract plain-text body from a Gmail message."""
    payload = msg.get("payload", {})

    def _decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""

    # Single-part
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        return _decode(body_data)

    # Multi-part — find text/plain
    for part in payload.get("parts", []):
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            return _decode(part.get("body", {}).get("data", ""))

    # Fallback: first part with data
    for part in payload.get("parts", []):
        d = part.get("body", {}).get("data", "")
        if d:
            return _decode(d)

    return ""


# ════════════════════════════════════════════════════════════════════════════════
# LLM helper — reuses thunderbird_personas._call_claude (Claude Max OAuth, $0)
# ════════════════════════════════════════════════════════════════════════════════

def _call_llm(system: str, prompt: str, max_tokens: int = 30) -> str:
    """Call Claude Haiku via CLI subprocess (Max plan OAuth, no API key needed)."""
    from core.ai_infra.thunderbird_personas import _call_claude
    return _call_claude(system, prompt, max_tokens=max_tokens, model=HAIKU_MODEL)


def _parse_category(raw: str) -> str:
    """Extract a valid category from LLM output; fall back to OTHER."""
    raw = raw.strip().upper()
    for cat in VALID_CATEGORIES:
        if cat in raw:
            return cat
    return "OTHER"


# ════════════════════════════════════════════════════════════════════════════════
# Classifier A — inbox-zero-style
# Rules pass first (cheap, zero LLM); LLM only for ambiguous messages.
# ════════════════════════════════════════════════════════════════════════════════

_DIRECTIVE_PATTERNS = [
    r"\bplease\s+(do|send|fix|update|check|confirm|call|book|cancel|add|remove)\b",
    r"\bcan you\s+(please\s+)?(do|send|fix|update|check|confirm|call|book|cancel|add|remove)\b",
    r"\b(action required|urgent|asap|follow up|follow-up|needs\s+attention)\b",
    r"\b(do this|handle this|take care of|please handle)\b",
]
_QUESTION_PATTERNS = [
    r"\?\s*$",
    r"\b(what|when|where|who|how|which|why|is there|are there|can you tell)\b",
    r"\b(wondering|wanted to know|do you know|any update|any news)\b",
]
_CCFYI_PATTERNS = [
    r"\b(fyi|for your (info|information|awareness)|heads up|just wanted to (let you know|share|inform))\b",
    r"\b(confirmation|confirmed|booked|receipt|invoice|statement|itinerary)\b",
    r"\b(newsletter|unsubscribe|promotion|offer|deal|discount)\b",
]

def _rules_classify(subject: str, sender: str, body: str) -> str | None:
    """Fast rules-based pre-classification. Returns category or None (→ use LLM)."""
    text = f"{subject} {body}".lower()

    for pat in _DIRECTIVE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "DIRECTIVE"

    for pat in _CCFYI_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "CC-FYI"

    for pat in _QUESTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "QUESTION"

    return None  # ambiguous — hand off to LLM


_INBOX_ZERO_SYSTEM = (
    "You are an email classifier for a luxury travel agency. "
    "Classify the email into exactly one category:\n"
    "  DIRECTIVE — the sender wants you to DO something (action required)\n"
    "  QUESTION  — the sender is asking for information\n"
    "  CC-FYI    — informational only, no action needed (receipts, newsletters, FYI)\n"
    "  OTHER     — none of the above\n"
    "Reply with ONLY the category word. No explanation."
)

def classify_inbox_zero(subject: str, sender: str, body_preview: str) -> str:
    """inbox-zero-style classifier: rules → LLM if ambiguous."""
    rules_result = _rules_classify(subject, sender, body_preview)
    if rules_result:
        return rules_result

    prompt = f"Subject: {subject}\nFrom: {sender}\nBody preview:\n{body_preview}"
    try:
        raw = _call_llm(_INBOX_ZERO_SYSTEM, prompt, max_tokens=10)
        return _parse_category(raw)
    except Exception as e:
        print(f"  [WARN] inbox-zero LLM call failed: {e}", file=sys.stderr)
        return "OTHER"


# ════════════════════════════════════════════════════════════════════════════════
# Classifier B — n8n-style
# Minimal DAG-style single-shot LLM prompt (simulates what an n8n workflow sends).
# ════════════════════════════════════════════════════════════════════════════════

_N8N_SYSTEM = (
    "Email classifier. Reply with one word only: DIRECTIVE, QUESTION, CC-FYI, or OTHER."
)

def classify_n8n_style(subject: str, sender: str, body_preview: str) -> str:
    """n8n-style classifier: minimal single-shot LLM prompt, no rules pre-pass."""
    prompt = (
        f"Classify this email.\n"
        f"Subject: {subject}\n"
        f"From: {sender}\n"
        f"Body: {body_preview[:300]}"
    )
    try:
        raw = _call_llm(_N8N_SYSTEM, prompt, max_tokens=10)
        return _parse_category(raw)
    except Exception as e:
        print(f"  [WARN] n8n-style LLM call failed: {e}", file=sys.stderr)
        return "OTHER"


# ════════════════════════════════════════════════════════════════════════════════
# Audit DB helpers — idempotency keyed on (message_id, source)
# ════════════════════════════════════════════════════════════════════════════════

def _already_classified(con: sqlite3.Connection, message_id: str, source: str) -> bool:
    """Return True if this (message_id, source) pair already has a 'classified' row."""
    row = con.execute(
        "SELECT id FROM email_events "
        "WHERE message_id = ? AND source = ? AND action_taken = 'classified' "
        "LIMIT 1",
        (message_id, source),
    ).fetchone()
    return row is not None


def _record(
    con: sqlite3.Connection,
    message_id: str,
    source: str,
    thread_id: str,
    classified_as: str,
    detail: str = "",
) -> None:
    """Insert a classified audit row directly (bypasses record() to use our connection)."""
    con.execute(
        """
        INSERT INTO email_events
            (message_id, thread_id, source, action_taken, classified_as, outcome, detail)
        VALUES (?, ?, ?, 'classified', ?, 'shadow', ?)
        """,
        (message_id, thread_id, source, classified_as, detail),
    )
    con.commit()


# ════════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════════

def run(limit: int, dry_run: bool, source_account: str) -> None:
    print(f"⚡ email_canary_shadow  limit={limit}  dry_run={dry_run}  account={source_account}")

    # ── Connect to audit DB ──────────────────────────────────────────────────
    if not dry_run:
        if not DB_PATH.exists():
            print(f"  [ERROR] Audit DB not found at {DB_PATH}", file=sys.stderr)
            sys.exit(1)
        con = sqlite3.connect(str(DB_PATH))
        con.execute("PRAGMA journal_mode=WAL")
    else:
        con = None

    # ── Fetch emails ─────────────────────────────────────────────────────────
    print(f"  Connecting to Gmail ({source_account})…")
    try:
        svc = _get_gmail_service(source_account)
        emails = _fetch_emails(svc, limit)
    except Exception as e:
        print(f"  [ERROR] Gmail fetch failed: {e}", file=sys.stderr)
        if con:
            con.close()
        sys.exit(1)

    print(f"  Fetched {len(emails)} emails. Running classifiers…\n")

    classified_count = 0
    skipped_idempotent = 0
    error_count = 0

    for email in emails:
        msg_id = email["message_id"]
        thread_id = email["thread_id"]
        subject = email["subject"]
        sender = email["sender"]
        body = email["body_preview"]

        print(f"  [{msg_id[:12]}] {subject[:60]!r}  from {sender[:40]!r}")

        # ── Run both classifiers (fail soft per classifier) ─────────────────
        for source, classify_fn in [
            (SOURCE_INBOX_ZERO, lambda: classify_inbox_zero(subject, sender, body)),
            (SOURCE_N8N, lambda: classify_n8n_style(subject, sender, body)),
        ]:
            try:
                # ── Idempotency check ────────────────────────────────────────
                if con and _already_classified(con, msg_id, source):
                    print(f"    {source}: [SKIP — already recorded]")
                    skipped_idempotent += 1
                    continue

                category = classify_fn()
                print(f"    {source}: {category}")

                if dry_run:
                    print(f"      [dry-run] would record → classified_as={category}")
                else:
                    _record(
                        con,
                        msg_id,
                        source,
                        thread_id,
                        category,
                        detail=f"subject={subject[:80]}",
                    )
                    classified_count += 1

            except Exception as e:
                # Fail soft: log and continue
                print(f"    {source}: [ERROR] {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                error_count += 1

        print()

    # ── Summary ──────────────────────────────────────────────────────────────
    if dry_run:
        print(f"DRY-RUN complete. Would have classified {len(emails)} emails × 2 sources.")
        print("No DB writes performed.")
    else:
        print(f"Done. Recorded {classified_count} new rows. "
              f"Skipped {skipped_idempotent} (idempotent). "
              f"Errors: {error_count}.")
        con.close()


def main():
    parser = argparse.ArgumentParser(description="Email canary shadow classifier")
    parser.add_argument("--limit", type=int, default=25,
                        help="Number of recent inbox emails to classify (default: 25)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify and print; no DB writes")
    parser.add_argument("--source-account", default="d2mconcierge",
                        choices=["d2mconcierge", "johnloucks3"],
                        help="Gmail account to read (default: d2mconcierge, same as sweep)")
    parser.add_argument("--n8n-ingest", action="store_true",
                        help="Alias for normal pass; called from the staged n8n workflow")
    args = parser.parse_args()

    run(
        limit=args.limit,
        dry_run=args.dry_run,
        source_account=args.source_account,
    )


if __name__ == "__main__":
    main()
