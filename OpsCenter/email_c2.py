#!/usr/bin/env python3
"""
email_c2.py — RELAY v2 Email C2 Engine
Thunderbird Wing · Dreams2Memories Travel, LLC · 2026-07-02

Watches d2mconcierge@gmail.com inbox for [WING] emails from Commander.
Parses intent with Haiku, gates through Hale rules, executes, replies in-thread.

REPLACES: gmail_exec_poller.py (raw IMAP, no threading, no gate dispatch)

Usage:
    python3 OpsCenter/email_c2.py --once    # single poll cycle (systemd timer mode)
    python3 OpsCenter/email_c2.py --loop    # continuous loop for dev/testing

Trigger (Commander sends TO d2mconcierge@gmail.com):
    Formal:   Subject: [WING] <what you want done>
    Natural:  Subject: Hale, <task>       (or COO / COS / Vic in subject)
              Body:    Hale — <task>       (persona name in first 200 chars of body)

Chat commands (subject only, no Haiku needed):
    [WING] STATUS <task-id>   — or —  Hale, status RELAY-XXXXXXXX
    [WING] LIST               — or —  Hale, list
    [WING] ABORT <task-id>    — or —  Hale, abort RELAY-XXXXXXXX
    [WING] BLACKBOARD         — or —  Hale, blackboard
    [WING] BRIEF              — or —  Hale, brief
"""

import sys
import os
import re
import json
import time
import logging
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# ── Project root on sys.path ──────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Logging ───────────────────────────────────────────────────────────────
LOG_FILE = _ROOT / "logs" / "email_c2.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("email_c2")

# ── Constants ─────────────────────────────────────────────────────────────
WING_TRIGGER      = "[WING]"
# Natural-language persona triggers — Commander uses these in subject or body
PERSONA_TRIGGERS  = {"COS", "HALE", "COO", "VIC"}
COMMANDER_TO   = "johnloucks3@gmail.com"
BLACKBOARD     = _ROOT / "OpsCenter" / "collaboration" / "blackboard.md"
ASK_WRAPPER    = Path.home() / ".local" / "bin" / "ask"
HAIKU_MODEL    = "claude-haiku-4-5-20251001"
EXEC_TIMEOUT   = 120  # seconds for subprocess tasks

# ── Lazy Gmail import ─────────────────────────────────────────────────────
def _wing_service():
    from core.email.thunderbird_gmail import _get_wing_gmail_service
    return _get_wing_gmail_service()

def _reply_in_thread(thread_id, in_reply_to, subject, body, html_body=None):
    from core.email.thunderbird_gmail import gmail_reply_in_thread
    return gmail_reply_in_thread(
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        subject=subject,
        body=body,
        html_body=html_body,
        persona_id="COS",
        to=COMMANDER_TO,
    )

# ── Task DB helpers ───────────────────────────────────────────────────────
def _db_init():
    from OpsCenter.task_queue import init_db
    init_db()

def _db_submit(content, gmail_thread_id="", gmail_message_id="",
               priority=5, task_type="email_c2", source="email_c2"):
    from OpsCenter.task_queue import get_db
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    task_id = "RELAY-" + hashlib.sha1(
        f"{content}{now}".encode()
    ).hexdigest()[:8].upper()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, created_at, updated_at, priority, task_type, content,
                assigned_to, status, source, gmail_thread_id, gmail_message_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, now, now, priority, task_type, content,
             "hale", "pending", source, gmail_thread_id, gmail_message_id)
        )
    return task_id

def _db_update(task_id, status, result=None):
    from OpsCenter.task_queue import get_db
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        if result is not None:
            conn.execute(
                "UPDATE tasks SET status=?, result=?, updated_at=? WHERE id=?",
                (status, result, now, task_id)
            )
        else:
            conn.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                (status, now, task_id)
            )

def _db_get(task_id):
    from OpsCenter.task_queue import get_db
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

def _db_get_by_message_id(gmail_message_id: str):
    """Dedup check — returns existing task if this Gmail message was already ingested."""
    from OpsCenter.task_queue import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status FROM tasks WHERE gmail_message_id=?", (gmail_message_id,)
        ).fetchone()
        return dict(row) if row else None

def _db_list(limit=10):
    from OpsCenter.task_queue import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, status, task_type, content, created_at FROM tasks "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

# ── Gmail fetch ───────────────────────────────────────────────────────────
def _extract_text_body(payload):
    """Recursively extract plain text from Gmail message payload."""
    import base64
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _extract_text_body(part)
        if text:
            return text
    return ""

def _is_wing_email(subject: str, body: str) -> bool:
    """True if email is a Wing task — [WING] in subject OR persona name in subject/body.

    Body matching is anchored to the START of the body (first 50 chars) to prevent
    false-positives on words like 'cos' or 'vic' appearing mid-sentence.
    """
    if WING_TRIGGER.lower() in subject.lower():
        return True
    # Subject: word-boundary match anywhere (Commander intentionally addresses by name)
    subj_up = subject.upper()
    if any(re.search(rf'\b{name}\b', subj_up) for name in PERSONA_TRIGGERS):
        return True
    # Body: persona must appear at the VERY START (Commander addressing the Wing directly)
    body_start = (body or "")[:50].upper()
    return any(re.search(rf'^\s*{name}\b', body_start) for name in PERSONA_TRIGGERS)

def _clean_subject(subject: str) -> str:
    """Strip [WING] / persona prefix from subject for clean intent parsing."""
    s = re.sub(r"^\[WING\]\s*", "", subject, flags=re.IGNORECASE)
    s = re.sub(
        rf"^({'|'.join(PERSONA_TRIGGERS)})[,:\s\u2013\u2014-]+",
        "", s, flags=re.IGNORECASE
    )
    return s.strip()

def fetch_wing_emails():
    """Return list of unread Wing emails from Commander in d2mconcierge inbox.
    Matches [WING] in subject OR persona name (HALE/COS/COO/VIC) in subject/body.
    """
    service = _wing_service()
    # Broad query: [WING] subject OR any persona trigger word in message
    persona_terms = " OR ".join(PERSONA_TRIGGERS)
    query = (
        f'from:{COMMANDER_TO} is:unread '
        f'(subject:"{WING_TRIGGER}" OR {persona_terms})'
    )
    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=20,
    ).execute()

    emails = []
    for meta in result.get("messages", []):
        try:
            msg = service.users().messages().get(
                userId="me", id=meta["id"], format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"]
                       for h in msg["payload"]["headers"]}
            subject       = headers.get("subject", "")
            message_id_hdr = headers.get("message-id", "")
            thread_id     = msg["threadId"]
            body          = _extract_text_body(msg["payload"])

            # Python-level confirm — broad query may pull non-Wing emails
            if not _is_wing_email(subject, body):
                log.debug("Skipping non-Wing email: %s", subject[:60])
                continue

            # Mark read immediately
            service.users().messages().modify(
                userId="me", id=meta["id"],
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            emails.append({
                "gmail_msg_id":     meta["id"],
                "thread_id":        thread_id,
                "message_id_header": message_id_hdr,
                "subject":          subject,
                "body":             body.strip(),
            })
            log.info("Fetched: %s (thread=%s)", subject[:60], thread_id)
        except Exception as e:
            log.warning("Failed to fetch message %s: %s", meta["id"], e)

    return emails

# ── Intent parsing (Haiku) ────────────────────────────────────────────────
def parse_intent(subject: str, body: str) -> dict:
    """Classify task intent with Haiku. Returns {intent, gate, route, summary}."""
    clean_subject = _clean_subject(subject)

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    f"Classify this Wing task. Return JSON only.\n\n"
                    f"Subject: {clean_subject}\n"
                    f"Body: {body[:400]}\n\n"
                    '{"intent":"<one sentence>","gate":"EXEC|WF17|HARLAN|DANI",'
                    '"route":"JET|DANI|COMMANDER","summary":"<5 words max>"}\n\n'
                    "gate=WF17: client-facing content.\n"
                    "gate=HARLAN: dollar amounts, payments, commissions.\n"
                    "gate=DANI: client email/itinerary/proposal draft.\n"
                    "gate=EXEC: everything else (code, research, ops)."
                ),
            }],
        )
        raw = resp.content[0].text.strip()
        # Extract JSON even if wrapped in markdown
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group()) if m else {"intent": clean_subject,
                                                 "gate": "EXEC", "route": "JET",
                                                 "summary": clean_subject[:40]}
    except Exception as e:
        log.warning("Haiku parse failed: %s — defaulting EXEC", e)
        return {"intent": clean_subject, "gate": "EXEC",
                "route": "JET", "summary": clean_subject[:40]}

# ── Chat command handlers ─────────────────────────────────────────────────
def _chat_status(args: str) -> str:
    task_id = args.strip().upper()
    if not task_id:
        return "Usage: [WING] STATUS <RELAY-XXXXXXXX>"
    row = _db_get(task_id)
    if not row:
        return f"No task found: {task_id}"
    result_preview = (row.get("result") or "—")[:500]
    return (
        f"**{row['id']}** — {row['status'].upper()}\n"
        f"Type:    {row['task_type']}\n"
        f"Created: {row['created_at']}\n"
        f"Updated: {row['updated_at']}\n\n"
        f"Result:\n{result_preview}"
    )

def _chat_list(_args: str) -> str:
    rows = _db_list(10)
    if not rows:
        return "No tasks in queue."
    lines = ["Last 10 tasks:\n"]
    for r in rows:
        summary = (r["content"] or "")[:50]
        lines.append(f"  {r['id']}  [{r['status']}]  {summary}")
    return "\n".join(lines)

def _chat_abort(args: str) -> str:
    task_id = args.strip().upper()
    if not task_id:
        return "Usage: [WING] ABORT <RELAY-XXXXXXXX>"
    row = _db_get(task_id)
    if not row:
        return f"No task found: {task_id}"
    if row["status"] in ("completed", "failed", "aborted"):
        return f"{task_id} already in terminal state: {row['status']}"
    _db_update(task_id, "aborted", result="Aborted by Commander via Email C2")
    return f"✅ {task_id} aborted."

def _chat_blackboard(_args: str) -> str:
    if BLACKBOARD.exists():
        lines = BLACKBOARD.read_text().splitlines()
        return "\n".join(lines[-25:])
    return "Blackboard not found."

def _chat_brief(_args: str) -> str:
    brief = _ROOT / "hale_brief.md"
    if brief.exists():
        content = brief.read_text()
        return content[:3000]
    return "hale_brief.md not found. Run morning brief generation first."

CHAT_HANDLERS = {
    "STATUS":     _chat_status,
    "LIST":       _chat_list,
    "ABORT":      _chat_abort,
    "BLACKBOARD": _chat_blackboard,
    "BRIEF":      _chat_brief,
}

def detect_chat_command(subject: str):
    """If subject is a chat command, return (cmd, args) else None.
    Handles both [WING] STATUS and natural 'Hale, status RELAY-...' forms.
    """
    clean = _clean_subject(subject)
    for cmd in CHAT_HANDLERS:
        if clean.upper().startswith(cmd):
            args = clean[len(cmd):].strip()
            return cmd, args
    return None

# ── Task execution ────────────────────────────────────────────────────────
def execute_exec_task(intent: str, body: str) -> str:
    """Execute EXEC-gate task via CC headless (ask wrapper)."""
    if not ASK_WRAPPER.exists():
        # Fallback: try mission_board_sync
        log.warning("ask wrapper not found at %s — using mission_board_sync fallback", ASK_WRAPPER)
        mb = _ROOT / "OpsCenter" / "mission_board_sync.py"
        try:
            r = subprocess.run(
                [sys.executable, str(mb), "add", intent, intent, "P2"],
                capture_output=True, text=True, timeout=30, cwd=str(_ROOT)
            )
            return f"Queued to mission board (ask not available):\n{r.stdout.strip()}"
        except Exception as e:
            return f"❌ Fallback failed: {e}"

    task_prompt = f"{intent}"
    if body:
        task_prompt += f"\n\nContext:\n{body[:600]}"

    try:
        r = subprocess.run(
            [str(ASK_WRAPPER), task_prompt],
            capture_output=True, text=True,
            timeout=EXEC_TIMEOUT, cwd=str(_ROOT),
        )
        output = (r.stdout + r.stderr).strip()
        return output[:3000] if output else "✅ Task executed (no output captured)"
    except subprocess.TimeoutExpired:
        return f"⏱ Task timed out ({EXEC_TIMEOUT}s). Check mission board for async completion."
    except Exception as e:
        return f"❌ Execution error: {e}"

def build_reply_html(task_id: str, gate: str, summary: str, result_text: str, elapsed: float) -> str:
    now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    safe_result = result_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<div style="font-family:Georgia,serif;background:#f0f4ff;padding:20px;border-radius:6px">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="background:#07076b;padding:12px 16px;border-radius:4px 4px 0 0">
      <span style="color:#ffffff;font-size:14px;font-weight:bold">
        ✅ {task_id} — {summary}
      </span>
    </td></tr>
    <tr><td style="background:#ffffff;padding:16px;border-radius:0 0 4px 4px">
      <pre style="background:#f7f7f7;padding:12px;border-radius:4px;
                  white-space:pre-wrap;font-size:12px;color:#222;
                  max-height:400px;overflow-y:auto">{safe_result[:2500]}</pre>
      <p style="color:#666;font-size:11px;margin:8px 0 0">
        Gate: <b>{gate}</b> &nbsp;·&nbsp; Elapsed: {elapsed:.1f}s
        &nbsp;·&nbsp; {now_str}
        &nbsp;·&nbsp; Victory Hale, D2M Travel
      </p>
    </td></tr>
  </table>
</div>"""

# ── Gate dispatch ─────────────────────────────────────────────────────────
def dispatch(email: dict, parsed: dict, task_id: str) -> None:
    """Route task through gate, execute, reply in thread."""
    gate    = parsed.get("gate", "EXEC")
    intent  = parsed.get("intent", email["subject"])
    summary = parsed.get("summary", intent[:40])
    subject = email["subject"]
    thread_id  = email["thread_id"]
    msg_id_hdr = email["message_id_header"]

    t_start = time.time()

    if gate == "WF17":
        result = (
            "🔒 WF-17 gate — client-facing content detected.\n"
            "This task requires Commander review before any send.\n"
            "Staged for your action — no email sent to any client.\n\n"
            f"Task: {intent}"
        )
        _db_update(task_id, "gated_wf17", result=result)

    elif gate == "HARLAN":
        result = (
            "💰 HARLAN gate — financial content detected.\n"
            "Flagged for Harlan (A9) sign-off.\n"
            "Reply APPROVE to this thread to release execution.\n\n"
            f"Task: {intent}"
        )
        _db_update(task_id, "gated_harlan", result=result)

    elif gate == "DANI":
        # Route to Dani via ask wrapper with Dani framing
        dani_prompt = (
            f"You are Dani (A3) — D2M client communications specialist.\n"
            f"Task: {intent}\n"
            f"Context: {email['body'][:400]}"
        )
        result = execute_exec_task(dani_prompt, "")
        _db_update(task_id, "completed", result=result)

    else:  # EXEC
        result = execute_exec_task(intent, email["body"])
        _db_update(task_id, "completed", result=result)

    elapsed = time.time() - t_start
    plain = f"{task_id} [{gate}]\n\n{result}\n\nElapsed: {elapsed:.1f}s"
    html  = build_reply_html(task_id, gate, summary, result, elapsed)

    try:
        _reply_in_thread(thread_id, msg_id_hdr, subject, plain, html)
        log.info("Replied in thread %s for task %s", thread_id, task_id)
    except Exception as e:
        log.error("Thread reply failed for %s: %s", task_id, e)

# ── Main poll cycle ───────────────────────────────────────────────────────
def run_once():
    log.info("── Email C2 poll cycle ──")
    _db_init()

    try:
        emails = fetch_wing_emails()
    except Exception as e:
        log.error("Gmail fetch failed: %s", e)
        return

    if not emails:
        log.info("No [WING] emails found")
        return

    log.info("Found %d [WING] email(s)", len(emails))

    for email in emails:
        subject    = email["subject"]
        thread_id  = email["thread_id"]
        msg_id_hdr = email["message_id_header"]

        log.info("Processing: %s", subject[:80])

        # ── Chat command? Handle immediately, no Haiku needed ──
        cmd_result = detect_chat_command(subject)
        if cmd_result:
            cmd, args = cmd_result
            log.info("Chat command: %s %s", cmd, args)
            handler = CHAT_HANDLERS[cmd]
            try:
                reply_text = handler(args)
            except Exception as e:
                reply_text = f"❌ {cmd} failed: {e}"
            plain = f"[WING] {cmd}\n\n{reply_text}"
            try:
                _reply_in_thread(thread_id, msg_id_hdr, subject, plain)
            except Exception as e:
                log.error("Chat reply failed: %s", e)
            continue

        # ── Task email — parse with Haiku, then dispatch ──

        # Dedup: skip if this Gmail message was already ingested (handles mark-read
        # before DB insert crash-recovery — email stays read, task already exists)
        if msg_id_hdr:
            existing = _db_get_by_message_id(msg_id_hdr)
            if existing:
                log.info("Skipping duplicate message %s (task %s already exists)",
                         msg_id_hdr, existing["id"])
                continue

        task_id = _db_submit(
            content          = f"{subject}\n{email['body'][:800]}",
            gmail_thread_id  = thread_id,
            gmail_message_id = msg_id_hdr,
            task_type        = "email_c2",
            source           = "email_c2",
        )
        log.info("Task %s submitted", task_id)

        # Send immediate ack in thread
        try:
            _reply_in_thread(
                thread_id, msg_id_hdr, subject,
                f"⚡ {task_id} — received. Parsing and routing now…",
            )
        except Exception as e:
            log.warning("Ack reply failed: %s", e)

        parsed = parse_intent(subject, email["body"])
        log.info("Parsed: gate=%s route=%s intent=%s",
                 parsed.get("gate"), parsed.get("route"), parsed.get("intent", "")[:60])

        _db_update(task_id, "active")
        dispatch(email, parsed, task_id)

    log.info("── Cycle complete ──")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="RELAY v2 Email C2 Engine")
    ap.add_argument("--once", action="store_true", default=True,
                    help="Run one poll cycle and exit (default; for systemd timer)")
    ap.add_argument("--loop", action="store_true",
                    help="Continuous loop (for development/testing)")
    ap.add_argument("--interval", type=int, default=120,
                    help="Loop interval in seconds (default 120)")
    args = ap.parse_args()

    if args.loop:
        log.info("Starting Email C2 in loop mode (interval=%ds)", args.interval)
        while True:
            try:
                run_once()
            except Exception as e:
                log.error("Poll error: %s", e)
            time.sleep(args.interval)
    else:
        run_once()
