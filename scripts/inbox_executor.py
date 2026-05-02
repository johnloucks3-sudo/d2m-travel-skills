#!/usr/bin/env python3
"""
inbox_executor.py
D2M Thunderbird Wing — Lifecycle Inbox Executor

Runs sequentially after d2m_lifecycle_scheduler.py (same systemd service).
Reads claude_inbox.md, processes each pending task, clears processed items.

Task routing:
  OVERDUE / ALERT / SEARCH_CLOSING  → Telegram page to Commander
  TRIGGER_EMAIL (pre-written TP)    → extract from drafts doc → Gmail draft → Telegram
  TRIGGER_EMAIL (no pre-written)    → DeepSeek V3.1 compose → Gmail draft → Telegram
  RESEARCH / WEEKLY_REPORT          → wing_comms.md task + Telegram flag

No Claude. No OpenCode. Pure Python + DeepSeek API + Gmail API + Telegram.
"""

import json
import logging
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import requests

BASE = Path("/home/john/Thunderbird")
INBOX_FILE      = BASE / "OpsCenter" / "claude_inbox.md"
WING_COMMS      = BASE / "OpsCenter" / "collaboration" / "wing_comms.md"
DRAFTS_DOC      = BASE / "output" / "Drafts_for_Client_Lifecycle_Engagement.md"
LOG_FILE        = BASE / "logs" / "inbox_executor.log"
STATE_FILE      = BASE / "state" / "inbox_executor_state.json"

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
COMMANDER_ID   = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206").strip()
TELEGRAM_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ── DeepSeek via OpenRouter ───────────────────────────────────────────────────
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek/deepseek-v4-pro"

# ── Gmail ─────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE))
from core.email.thunderbird_gmail import gmail_create_draft_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("inbox_executor")

TODAY = datetime.now().strftime("%Y-%m-%d %H:%M")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def page_commander(msg: str) -> bool:
    """Send Telegram message to Commander via D2MC2C bot."""
    if not BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram page")
        return False
    try:
        payload = json.dumps({
            "chat_id": COMMANDER_ID,
            "text": msg,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            TELEGRAM_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=15)
        log.info("  [telegram] Page sent to Commander")
        return True
    except Exception as e:
        log.error(f"  [telegram] Failed: {e}")
        return False


def call_deepseek(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
    """Call DeepSeek V4 Pro via OpenRouter. Returns text or empty string on failure."""
    if not OPENROUTER_KEY:
        log.warning("OPENROUTER_API_KEY not set — DeepSeek unavailable")
        return ""
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.4,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error(f"  [deepseek] API call failed: {e}")
        return ""


def extract_tp_email(tp_id: str) -> dict | None:
    """
    Extract pre-written email from Drafts_for_Client_Lifecycle_Engagement.md
    by TP ID (e.g. '0.5', '1.1', '3.1').

    Returns dict with keys: to, subject, body — or None if not found.
    """
    if not DRAFTS_DOC.exists():
        log.warning(f"  [drafts] Drafts doc not found: {DRAFTS_DOC}")
        return None

    content = DRAFTS_DOC.read_text()

    # Normalize: "TP-0.5" → "0.5", "TP 0.5" → "0.5"
    normalized = re.sub(r"^[Tt][Pp][-\s]?", "", tp_id.strip())

    # Find section header: "### TP 0.5 —" or "### TP 0.5 —"
    pattern = rf"###\s+TP\s+{re.escape(normalized)}\s*[—\-]"
    match = re.search(pattern, content)
    if not match:
        log.info(f"  [drafts] No pre-written email found for TP {normalized}")
        return None

    # Extract section: from match to next ### or ## header
    start = match.start()
    rest = content[start:]
    next_section = re.search(r"\n#{2,3}\s", rest[5:])
    section = rest[:next_section.start() + 5] if next_section else rest

    # Extract To
    to_match = re.search(r"\*\*To:\*\*\s*(.+)", section)
    to_addr = to_match.group(1).strip() if to_match else ""

    # Extract Subject
    subj_match = re.search(r"\*\*Subject:\*\*\s*(.+)", section)
    subject = subj_match.group(1).strip() if subj_match else f"TP {normalized} — Kuklinski Group"

    # Extract body: everything after the Subject line to end of section
    if subj_match:
        body_start = section.find("\n", section.find(subj_match.group(0))) + 1
        body = section[body_start:].strip()
        # Strip any trailing Send Date / metadata lines
        body = re.sub(r"\*\*Send Date:\*\*.*\n?", "", body).strip()
    else:
        body = section.strip()

    if not body:
        return None

    return {"to": to_addr, "subject": subject, "body": body}


def post_to_wing_comms(msg: str):
    """Append a task to wing_comms.md."""
    try:
        with open(WING_COMMS, "a") as f:
            f.write(f"\n---\n**[INBOX EXECUTOR — {TODAY}]**\n{msg}\n")
        log.info("  [wing_comms] Task posted")
    except Exception as e:
        log.error(f"  [wing_comms] Write failed: {e}")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_hashes": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_blocks(content: str) -> list[dict]:
    """
    Split claude_inbox.md into task blocks.
    Each block is separated by '---' and contains key-value pairs.
    Returns list of dicts with 'raw', 'type', 'client', 'tp_id', 'subject', etc.
    """
    blocks = []
    raw_blocks = re.split(r"\n---\n", content)

    for raw in raw_blocks:
        raw = raw.strip()
        if not raw or len(raw) < 20:
            continue

        block: dict = {"raw": raw}

        # Determine type from ## header
        type_match = re.search(r"##\s+(.+)", raw)
        block["type_line"] = type_match.group(1).strip() if type_match else ""

        if "OVERDUE TOUCHPOINT" in block["type_line"]:
            block["type"] = "OVERDUE"
        elif "SEARCH WINDOW CLOSING" in block["type_line"] or "SEARCH CLOSING" in block["type_line"]:
            block["type"] = "SEARCH_CLOSING"
        elif "LIFECYCLE — TP EMAIL DUE" in block["type_line"]:
            block["type"] = "TRIGGER_EMAIL"
        elif "WEEKLY INTEL REPORT DUE" in block["type_line"]:
            block["type"] = "WEEKLY_REPORT"
        elif "RESEARCH TASK" in block["type_line"]:
            block["type"] = "RESEARCH"
        elif "PORTAL OPENING" in block["type_line"]:
            block["type"] = "PORTAL"
        elif "PAYMENT CRITICAL" in block["type_line"]:
            block["type"] = "PAYMENT_CRITICAL"
        else:
            block["type"] = "UNKNOWN"

        # Extract common fields
        for field, pattern in [
            ("client",   r"\*\*Client:\*\*\s*(.+)"),
            ("tp_id",    r"\*\*TP:\*\*\s*([\w\.\-]+)"),
            ("tp_label", r"\*\*TP:\*\*\s*[\w\.\-]+\s*[—\-]\s*(.+)"),
            ("subject",  r"\*\*Subject:\*\*\s*(.+)"),
            ("staff",    r"\*\*Staff(?:\s+Lead)?:\*\*\s*(.+)"),
            ("channel",  r"\*\*Channel:\*\*\s*(.+)"),
            ("action",   r"\*\*Action:\*\*\s*(.+)"),
            ("closes",   r"\*\*Closes:\*\*\s*(.+)"),
        ]:
            m = re.search(pattern, raw)
            block[field] = m.group(1).strip() if m else ""

        # Hash for dedup
        import hashlib
        block["hash"] = hashlib.md5(raw.encode()).hexdigest()[:12]

        blocks.append(block)

    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def handle_overdue(block: dict):
    """Alert Commander via Telegram for overdue / closing items."""
    emoji = "🔴" if block["type"] == "OVERDUE" else "⏰"
    client = block.get("client", "Unknown")
    tp = block.get("tp_id", "") + " " + block.get("tp_label", "")
    staff = block.get("staff", "")
    closes = block.get("closes", "")

    lines = [f"{emoji} *{block['type_line']}*", f"*Client:* {client}", f"*TP:* {tp.strip()}"]
    if staff:
        lines.append(f"*Staff:* {staff}")
    if closes:
        lines.append(f"*Closes:* {closes}")
    lines.append(f"_Lifecycle Executor — {TODAY}_")

    page_commander("\n".join(lines))
    log.info(f"  [{block['type']}] Paged Commander — {client} {tp.strip()}")


def handle_trigger_email(block: dict):
    """
    Draft a lifecycle touchpoint email:
    1. Try pre-written email from Drafts doc by TP ID
    2. Fall back to DeepSeek V3.1 composition
    3. Create Gmail draft in d2mconcierge
    4. Page Commander with draft notification
    """
    client  = block.get("client", "Unknown client")
    tp_id   = block.get("tp_id", "")
    tp_lbl  = block.get("tp_label", "")
    subject = block.get("subject", f"TP {tp_id} — {client}")
    channel = block.get("channel", "DRAFT in d2mconcierge@gmail.com")
    action  = block.get("action", "")

    log.info(f"  [TRIGGER_EMAIL] {client} — {tp_id} {tp_lbl}")

    # ── Try pre-written email ──────────────────────────────────────────────
    email_data = extract_tp_email(tp_id)

    if email_data:
        to_addr = email_data["to"]
        subj    = email_data["subject"] or subject
        body    = email_data["body"]
        source  = "pre-written"
        log.info(f"    Pre-written email found for TP {tp_id}")
    else:
        # ── DeepSeek V4 Pro fallback ──────────────────────────────────────
        log.info(f"    No pre-written email — calling DeepSeek V4 Pro for TP {tp_id}")
        system_prompt = (
            "You are Danielle 'Dani' Moreau, D2M Luxury Travel Concierge for Dreams2Memories Travel, LLC. "
            "Write warm, crisp, certain client emails. Short sentences. No hedging. No filler. "
            "Sign off with 'Thanks' — never 'Best'. Use the client's first names."
        )
        user_prompt = (
            f"Write a lifecycle touchpoint email for this client:\n"
            f"Client: {client}\n"
            f"TP: {tp_id} — {tp_lbl}\n"
            f"Subject: {subject}\n"
            f"Context: {action}\n\n"
            f"Output: subject line on first line, then blank line, then email body only. "
            f"No metadata, no brackets, no placeholders."
        )
        composed = call_deepseek(system_prompt, user_prompt, max_tokens=600)
        if not composed:
            # Last resort: wing_comms task for manual handling
            post_to_wing_comms(
                f"## EMAIL COMPOSITION NEEDED — {tp_id} {tp_lbl}\n"
                f"**Client:** {client}\n"
                f"**Subject:** {subject}\n"
                f"**Reason:** DeepSeek V4 Pro unavailable. Manual composition required.\n"
                f"**Staff:** {block.get('staff', 'Hale')}"
            )
            page_commander(
                f"⚠️ *EMAIL NEEDED — Manual*\n"
                f"*{client}* — {tp_id} {tp_lbl}\n"
                f"DeepSeek V4 Pro unavailable. Task in wing\\_comms.\n"
                f"_{TODAY}_"
            )
            return

        lines = composed.split("\n", 2)
        subj  = lines[0].strip() if lines else subject
        body  = lines[2].strip() if len(lines) > 2 else composed
        to_addr = ""  # DeepSeek doesn't know recipients — leave blank for Commander
        source  = "DeepSeek V4 Pro"

    # ── Create Gmail draft ─────────────────────────────────────────────────
    # If channel says SEND (owner client / intel) — still draft for WF-17 safety
    # Commander approves all client-facing sends
    draft_to = to_addr if to_addr else "concierge@d2mluxury.quest"

    try:
        result = gmail_create_draft_sync(
            to=draft_to,
            subject=subj,
            body=body,
            from_address="concierge@d2mluxury.quest",
            label_review=True,
        )
        draft_id = result.get("draft_id", "")
        log.info(f"    Gmail draft created — id={draft_id} source={source}")

        page_commander(
            f"📧 *DRAFT READY — {tp_id}*\n"
            f"*Client:* {client}\n"
            f"*Subject:* {subj}\n"
            f"*To:* {draft_to or '(set recipients)'}\n"
            f"*Source:* {source}\n"
            f"Check d2mconcierge drafts → approve to send\n"
            f"_{TODAY}_"
        )
    except Exception as e:
        log.error(f"    Gmail draft failed: {e}")
        post_to_wing_comms(
            f"## DRAFT FAILED — {tp_id} {tp_lbl}\n"
            f"**Client:** {client}\n"
            f"**Error:** {e}\n"
            f"**Action:** Manual draft required."
        )
        page_commander(
            f"🔴 *DRAFT FAILED — {tp_id}*\n"
            f"*Client:* {client}\n"
            f"Gmail error: {str(e)[:80]}\n"
            f"Task in wing\\_comms.\n_{TODAY}_"
        )


def handle_research(block: dict):
    """Post research/weekly report tasks to wing_comms and page Commander."""
    client  = block.get("client", "Unknown")
    tp_id   = block.get("tp_id", "")
    tp_lbl  = block.get("tp_label", "")
    staff   = block.get("staff", "A2 Dembe")
    action  = block.get("action", "")

    post_to_wing_comms(
        f"## {block['type_line']}\n"
        f"**Client:** {client}\n"
        f"**TP:** {tp_id} {tp_lbl}\n"
        f"**Assigned to:** {staff}\n"
        f"**Action:** {action}\n"
        f"**Authority:** COS Hale (COO SO 2026-04-17)"
    )

    emoji = "📊" if block["type"] == "WEEKLY_REPORT" else "🔍"
    page_commander(
        f"{emoji} *{block['type_line']}*\n"
        f"*Client:* {client}\n"
        f"*TP:* {tp_id} {tp_lbl}\n"
        f"*Staff:* {staff}\n"
        f"Task posted to wing\\_comms.\n_{TODAY}_"
    )
    log.info(f"  [{block['type']}] wing_comms task posted — {client} {tp_id}")


def handle_portal(block: dict):
    """Portal opening / payment critical — page Commander."""
    page_commander(
        f"🔔 *{block['type_line']}*\n"
        f"*Client:* {block.get('client','')}\n"
        f"*TP:* {block.get('tp_id','')} {block.get('tp_label','')}\n"
        f"*Action:* {block.get('action','See inbox for details')}\n"
        f"_{TODAY}_"
    )
    log.info(f"  [PORTAL/PAYMENT] Paged Commander — {block.get('client','')}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info(f"\n{'='*56}")
    log.info(f"  D2M Inbox Executor — {TODAY}")
    log.info(f"{'='*56}\n")

    if not INBOX_FILE.exists():
        log.info("  claude_inbox.md not found — nothing to process")
        return

    content = INBOX_FILE.read_text().strip()
    if not content:
        log.info("  claude_inbox.md is empty — nothing to process")
        return

    state  = load_state()
    done   = set(state.get("processed_hashes", []))
    blocks = parse_blocks(content)

    if not blocks:
        log.info("  No task blocks found in inbox")
        return

    log.info(f"  Found {len(blocks)} task block(s)")
    processed = []
    skipped   = 0

    for block in blocks:
        h = block["hash"]
        if h in done:
            skipped += 1
            continue

        btype = block["type"]
        log.info(f"\n  → [{btype}] {block.get('client','')} {block.get('tp_id','')} {block.get('tp_label','')[:40]}")

        if btype in ("OVERDUE", "SEARCH_CLOSING"):
            handle_overdue(block)
        elif btype == "TRIGGER_EMAIL":
            handle_trigger_email(block)
        elif btype in ("RESEARCH", "WEEKLY_REPORT"):
            handle_research(block)
        elif btype in ("PORTAL", "PAYMENT_CRITICAL"):
            handle_portal(block)
        else:
            log.warning(f"    Unknown block type '{btype}' — paging Commander with raw text")
            page_commander(
                f"⚠️ *INBOX TASK — UNKNOWN TYPE*\n"
                f"```\n{block['raw'][:400]}\n```\n_{TODAY}_"
            )

        processed.append(h)
        done.add(h)

    # ── Clear processed blocks from inbox ─────────────────────────────────
    if processed:
        remaining_blocks = [b for b in blocks if b["hash"] not in set(processed)]
        if remaining_blocks:
            new_content = "\n---\n".join(b["raw"] for b in remaining_blocks)
        else:
            new_content = ""
        INBOX_FILE.write_text(new_content)
        log.info(f"\n  Processed: {len(processed)} | Skipped (already done): {skipped} | Remaining: {len(remaining_blocks)}")
    else:
        log.info(f"\n  All {skipped} blocks already processed — inbox unchanged")

    # ── Persist state ──────────────────────────────────────────────────────
    state["processed_hashes"] = list(done)[-500:]  # keep last 500
    state["last_run"] = TODAY
    save_state(state)

    log.info(f"\n{'='*56}\n")


if __name__ == "__main__":
    main()
