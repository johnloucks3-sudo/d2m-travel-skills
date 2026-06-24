#!/usr/bin/env python3
"""
whatsapp_webhook.py — WhatsApp C2 channel for Thunderbird Wing
Commander directive 2026-06-22: WhatsApp replaces Telegram as primary C2.

Listens on port 8769. Exposed via Cloudflare tunnel: https://wa.d2mluxury.quest
Twilio WhatsApp sandbox webhook: https://wa.d2mluxury.quest/whatsapp

Architecture (async — Twilio 15s timeout bypassed):
  Commander texts WhatsApp → Twilio POSTs webhook → 200 in <1s → background thread
  → command router OR hale_claude_engine → outbound Twilio API reply → Commander

Commands:
  /agent <task>    — Hale inline (Haiku engine, full context)
  /relay <msg>     — Broadcast to Wing via Telegram (D2MC2C bot → Commander chat)
  /brief           — Daily Hale brief from hale_brief.md
  /status          — Wing health
  /missions [n]    — P0/P1 active missions (default 20)
  /drafts          — List pending drafts (d2mconcierge)
  /approve <id>    — Send a draft
  /reject <id>     — Delete a draft
  /tpb [cmd]       — Target Prosecution Board
  /help            — Command list

Auto-relay trigger: natural language containing "notify the wing", "telegram relay",
  "broadcast to wing", "tell the wing" → relays to Telegram automatically.

Model overrides (prefix your message):
  OPUS: ...     SONNET: ...   GROK: ...   DEEPSEEK: ...   HAIKU: ...

Natural language (no slash): routed to hale_claude_engine.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from base64 import b64encode
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "OpsCenter"))

# Load .env
_env_file = THUNDERBIRD / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("wa_c2")

# ── Constants ────────────────────────────────────────────────────────────────
COMMANDER_WA    = "whatsapp:+17192910742"
WHATSAPP_FROM   = "+14155238886"
PORT            = 8769
CHUNK_SIZE      = 4000    # WhatsApp max is 4096; leave margin
ENGINE_TIMEOUT  = 90      # seconds for claude -p calls

HALE_BRIEF      = THUNDERBIRD / "hale_brief.md"
MISSION_BOARD   = THUNDERBIRD / "OpsCenter" / "mission_board.json"
CTX_D2MC2C      = THUNDERBIRD / "OpsCenter" / "context_d2mc2c.json"
TPB_SCRIPT      = THUNDERBIRD / "OpsCenter" / "tpb.py"

# ── Hale engine ──────────────────────────────────────────────────────────────
try:
    from thunderbird_telegram_gw import hale_claude_engine
    _ENGINE_SOURCE = "telegram_gw"
except Exception as _e:
    log.warning("telegram_gw import failed (%s) — using fallback engine", _e)

    def hale_claude_engine(ctx: str, msg: str, model_override) -> str:
        creds_path = Path.home() / ".claude" / ".credentials.json"
        env = dict(os.environ)
        if creds_path.exists():
            try:
                creds = json.loads(creds_path.read_text())
                env["CLAUDE_CODE_OAUTH_TOKEN"] = creds["claudeAiOauth"]["accessToken"]
            except Exception:
                pass
        model = model_override or "claude-haiku-4-5-20251001"
        prompt = (
            "You are Hale, Chief of Staff, Thunderbird Wing / D2M Travel.\n"
            f"Context: {ctx[:3000]}\n\n"
            f"Commander (WhatsApp): {msg}\n\n"
            "Reply concisely. Lead with ⚡."
        )
        try:
            r = subprocess.run(
                ["/home/john/.local/bin/claude", "-p", prompt,
                 "--model", model],
                capture_output=True, text=True, timeout=ENGINE_TIMEOUT, env=env
            )
            return r.stdout.strip() or "[No response]"
        except Exception as exc:
            return f"[Engine error: {exc}]"

    _ENGINE_SOURCE = "fallback"

log.info("Hale engine: %s", _ENGINE_SOURCE)


# ── Twilio outbound ──────────────────────────────────────────────────────────
def _twilio_send(to_wa: str, body: str) -> bool:
    sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        log.error("Twilio credentials missing")
        return False
    url  = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({
        "From": f"whatsapp:{WHATSAPP_FROM}",
        "To":   to_wa,
        "Body": body,
    }).encode()
    auth = b64encode(f"{sid}:{token}".encode()).decode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        log.info("WA sent → %s (%s)", result.get("sid"), result.get("status"))
        return True
    except urllib.error.HTTPError as e:
        log.error("Twilio HTTP %d: %s", e.code, e.read(200).decode())
        return False
    except Exception as e:
        log.error("Twilio error: %s", e)
        return False


def _wa_send_chunks(to_wa: str, text: str) -> None:
    """Send long text as multiple WhatsApp messages."""
    text = text.strip()
    if not text:
        return
    chunks = []
    while len(text) > CHUNK_SIZE:
        split = text.rfind("\n", 0, CHUNK_SIZE)
        if split < CHUNK_SIZE // 2:
            split = CHUNK_SIZE
        chunks.append(text[:split].strip())
        text = text[split:].strip()
    if text:
        chunks.append(text)
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if total > 1:
            chunk = f"[{i+1}/{total}]\n{chunk}"
        _twilio_send(to_wa, chunk)
        if i < total - 1:
            time.sleep(0.5)


def _strip_html(text: str) -> str:
    """Strip HTML tags for WhatsApp plain text."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return text


# ── Telegram relay ───────────────────────────────────────────────────────────
def _tg_relay(msg: str, label: str = "WA→RELAY") -> bool:
    """Send a message to Telegram via D2MC2C bot → Commander chat.
    This is the real Telegram relay — not LLM-generated text about relay."""
    try:
        from thunderbird_telegram_gw import tg_send as _tg_send
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        commander_chat = "7554895206"
        if not bot_token:
            log.error("TELEGRAM_BOT_TOKEN not set — relay failed")
            return False
        prefixed = f"⚡ [{label}] {msg}"
        ok = _tg_send(bot_token, commander_chat, prefixed)
        if ok:
            log.info("TG relay sent: %s chars", len(prefixed))
        else:
            log.error("TG relay: tg_send returned False")
        return ok
    except Exception as e:
        log.error("TG relay error: %s", e)
        # Fallback: wing_relay.py subprocess
        try:
            r = subprocess.run(
                [sys.executable,
                 str(THUNDERBIRD / "core/relay/wing_relay.py"),
                 "send", "OC", msg],
                capture_output=True, text=True, timeout=10, cwd=str(THUNDERBIRD)
            )
            return r.returncode == 0
        except Exception as e2:
            log.error("TG relay fallback error: %s", e2)
            return False


# Keywords that trigger auto-relay to Telegram (no /relay command required)
_RELAY_TRIGGERS = (
    "notify the wing",
    "tell the wing",
    "telegram relay",
    "broadcast to wing",
    "relay to telegram",
    "wing relay",
    "let the wing know",
)


# ── Command handlers ─────────────────────────────────────────────────────────

def cmd_help(from_wa: str) -> None:
    msg = (
        "⚡ *Thunderbird Wing — WhatsApp C2*\n\n"
        "*Commands:*\n"
        "/agent <task> — Hale inline (ask anything)\n"
        "/relay <msg> — Broadcast to Wing via Telegram\n"
        "/brief — Daily brief\n"
        "/status — Wing health\n"
        "/missions — Active P0/P1 missions\n"
        "/drafts — Pending drafts (Commander + Wing)\n"
        "/approve <id> — Send a draft (WF-17 gate active)\n"
        "/reject <id> — Delete a draft\n"
        "/inbox [query] — Search Commander inbox (johnloucks3)\n"
        "/tpb [cmd] — Target Prosecution Board\n"
        "/help — This menu\n\n"
        "*Model overrides (prefix):*\n"
        "OPUS: / SONNET: / GROK: / DEEPSEEK: / HAIKU:\n\n"
        "*Natural language:* just type — Hale responds."
    )
    _twilio_send(from_wa, msg)


def cmd_status(from_wa: str) -> None:
    lines = ["⚡ *Thunderbird Wing Status*\n"]

    # MCP
    for port, label in [(8765, "MCP Server"), (8769, "WA Webhook")]:
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect(("localhost", port))
            s.close()
            lines.append(f"🟢 {label} (:{port})")
        except Exception:
            lines.append(f"🔴 {label} (:{port})")

    # Supertimer bots
    health_file = THUNDERBIRD / "OpsCenter" / "supertimer_health.json"
    if health_file.exists():
        try:
            bots = json.loads(health_file.read_text())
            lines.append("")
            for name, data in bots.items():
                status = data.get("status", "?")
                cf = data.get("consecutive_failures", 0)
                icon = "🟢" if status in ("GREEN", "IDLE") else ("🔴" if status == "RED" else "🟡")
                suffix = f" (x{cf} fails)" if cf > 0 else ""
                lines.append(f"{icon} {name}: {status}{suffix}")
        except Exception:
            pass

    # Brief freshness
    if HALE_BRIEF.exists():
        age_h = (time.time() - HALE_BRIEF.stat().st_mtime) / 3600
        lines.append(f"\n📋 Brief: {age_h:.1f}h ago")

    lines.append(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M MT')}")
    _wa_send_chunks(from_wa, "\n".join(lines))


def cmd_brief(from_wa: str) -> None:
    _twilio_send(from_wa, "⏳ Pulling brief…")
    if HALE_BRIEF.exists():
        text = HALE_BRIEF.read_text()
        # Trim markdown to essentials for WhatsApp
        text = _strip_html(text)
        # Send first 8000 chars (2 chunks)
        _wa_send_chunks(from_wa, "⚡ *HALE BRIEF*\n\n" + text[:8000])
    else:
        _twilio_send(from_wa, "⚠️ hale_brief.md not found — run morning brief generator.")


def cmd_missions(from_wa: str, limit: int = 20) -> None:
    try:
        mb = json.loads(MISSION_BOARD.read_text())
        missions = mb.get("missions", mb) if isinstance(mb, dict) else mb
        if isinstance(missions, dict):
            all_m = list(missions.values())
        else:
            all_m = missions
        active = [m for m in all_m
                  if m.get("priority") in ("P0", "P1")
                  and m.get("status") not in ("complete", "cancelled", "retired")]
        active.sort(key=lambda m: (m.get("priority", "P9"), m.get("id", "")))
        lines = [f"⚡ *Active P0/P1 Missions* ({len(active)} total)\n"]
        for m in active[:limit]:
            p   = m.get("priority", "??")
            mid = m.get("id", "")
            title = m.get("title", "")[:70]
            status = m.get("status", "")
            lines.append(f"[{p}] {mid} — {title} ({status})")
        if len(active) > limit:
            lines.append(f"\n…and {len(active)-limit} more. /missions {limit+20} for more.")
        _wa_send_chunks(from_wa, "\n".join(lines))
    except Exception as e:
        _twilio_send(from_wa, f"❌ Mission board error: {e}")


def cmd_tpb(from_wa: str, args: str) -> None:
    sub = args.strip() if args.strip() else "status"
    # Allowlist: only permit known subcommands
    ALLOWED_SUBS = {"status", "list", "add", "update", "close"}
    if sub not in ALLOWED_SUBS or sub.startswith("-"):
        _twilio_send(from_wa, f"❌ Unknown TPB command: {sub}\nAllowed: {', '.join(ALLOWED_SUBS)}")
        return
    try:
        r = subprocess.run(
            [sys.executable, str(TPB_SCRIPT), "--", sub],
            capture_output=True, text=True, timeout=30, cwd=str(THUNDERBIRD)
        )
        out = (r.stdout or r.stderr or "(no output)").strip()
        _wa_send_chunks(from_wa, f"⚡ *TPB — {sub}*\n\n{out}")
    except Exception as e:
        _twilio_send(from_wa, f"❌ TPB error: {e}")


_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _get_gmail_svc():
    """Gmail service for d2mconcierge."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        token_file = THUNDERBIRD / "gmail_token.json"
        SCOPES = _GMAIL_SCOPES
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if not creds or not creds.valid:
            return None
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        log.error("Gmail svc error: %s", e)
        return None


def _get_jl3_svc():
    """Gmail service for Commander's inbox (johnloucks3@gmail.com).

    Full read/write per Commander directive 2026-06-23.
    Client-send gate (WF-17) still applies — WA /approve only sends to internal addresses.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        token_file = THUNDERBIRD / "creds" / "johnloucks3_token.json"
        SCOPES = _GMAIL_SCOPES
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if not creds or not creds.valid:
            log.warning("JL3 Gmail: no valid credentials")
            return None
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        log.error("JL3 Gmail svc error: %s", e)
        return None


# ── Internal addresses — Wing may send directly (WF-17 applies to all others) ──
_WING_INTERNAL_ADDRESSES = {
    "johnloucks3@gmail.com",
    "d2mconcierge@gmail.com",
    "susanna.loucks@gmail.com",
}

def _is_internal_address(to_header: str) -> bool:
    from email.utils import getaddresses
    parsed = [addr.lower().strip() for _, addr in getaddresses([to_header]) if addr]
    if not parsed:
        return False
    return all(addr in _WING_INTERNAL_ADDRESSES for addr in parsed)


def _list_account_drafts(svc, label: str, lines: list) -> int:
    """Fetch drafts from one Gmail account and append formatted entries to lines. Returns count."""
    count = 0
    try:
        result = svc.users().drafts().list(userId="me", maxResults=8).execute()
        drafts = result.get("drafts", [])
        for d in drafts:
            try:
                detail  = svc.users().drafts().get(userId="me", id=d["id"], format="metadata").execute()
                headers = {h["name"].lower(): h["value"]
                           for h in detail.get("message", {}).get("payload", {}).get("headers", [])}
                subject = headers.get("subject", "(no subject)")[:50]
                to      = headers.get("to", "?")[:40]
                lines.append(f"[{label}] `{d['id'][:20]}`\n  To: {to}\n  Re: {subject}\n")
            except Exception:
                lines.append(f"[{label}] `{d['id'][:20]}` (error)\n")
            count += 1
    except Exception as e:
        lines.append(f"[{label}] error: {e}\n")
    return count


def cmd_drafts(from_wa: str) -> None:
    _twilio_send(from_wa, "⏳ Fetching drafts (Commander + Wing)…")
    lines = ["⚡ *Pending drafts:*\n"]
    total = 0

    # Commander's inbox (johnloucks3) — where Commander reviews and sends
    svc_jl3 = _get_jl3_svc()
    if svc_jl3:
        total += _list_account_drafts(svc_jl3, "Commander", lines)
    else:
        lines.append("[Commander] ❌ unavailable\n")

    # Wing outbox (d2mconcierge)
    svc_d2m = _get_gmail_svc()
    if svc_d2m:
        total += _list_account_drafts(svc_d2m, "Wing", lines)
    else:
        lines.append("[Wing] ❌ unavailable\n")

    if total == 0:
        _twilio_send(from_wa, "📭 No pending drafts in either account.")
        return
    lines.append("\n/approve <id>  or  /reject <id>")
    _wa_send_chunks(from_wa, "\n".join(lines))


def _find_draft_in_accounts(draft_id: str):
    """Search d2mconcierge then johnloucks3 for a draft. Returns (svc, account_label) or (None, None)."""
    for svc, label in [(_get_gmail_svc(), "Wing"), (_get_jl3_svc(), "Commander")]:
        if not svc:
            continue
        try:
            svc.users().drafts().get(userId="me", id=draft_id, format="metadata").execute()
            return svc, label
        except Exception:
            continue
    return None, None


def cmd_approve(from_wa: str, args: list) -> None:
    if not args:
        _twilio_send(from_wa, "Usage: /approve <draft_id>  — get IDs with /drafts")
        return
    draft_id = args[0]

    # Try two-lane publish path (d2mconcierge registry)
    try:
        sys.path.insert(0, str(THUNDERBIRD / "core" / "email"))
        from thunderbird_gmail import publish_draft, _get_draft_metadata
        meta = _get_draft_metadata(draft_id)
        if meta:
            result = publish_draft(draft_id)
            if result.get("status") == "success":
                _twilio_send(from_wa,
                    f"✅ *SENT*\nTo: {result.get('to','?')}\n"
                    f"Re: {result.get('subject','?')}\n"
                    f"Persona: {result.get('persona_id','?')} · Stationery applied.")
            else:
                _twilio_send(from_wa, f"❌ Publish failed: {result}")
            return
    except Exception:
        pass

    # Fallback: find draft in either account and send raw
    svc, acct = _find_draft_in_accounts(draft_id)
    if not svc:
        _twilio_send(from_wa, "❌ Draft not found in Wing or Commander accounts.")
        return
    try:
        detail  = svc.users().drafts().get(userId="me", id=draft_id, format="metadata").execute()
        headers = {h["name"].lower(): h["value"]
                   for h in detail.get("message", {}).get("payload", {}).get("headers", [])}
        to      = headers.get("to", "?")
        subject = headers.get("subject", "?")
        # WF-17: block client sends
        if not _is_internal_address(to):
            _twilio_send(from_wa,
                f"🚫 *WF-17 GATE*\nTo: {to}\n"
                "Client-facing send blocked. Commander must send from Gmail directly.")
            return
        svc.users().drafts().send(userId="me", body={"id": draft_id}).execute()
        _twilio_send(from_wa, f"✅ *SENT* [{acct}]\nTo: {to}\nRe: {subject}")
    except Exception as e:
        _twilio_send(from_wa, f"❌ Send failed: {e}")


def cmd_reject(from_wa: str, args: list) -> None:
    if not args:
        _twilio_send(from_wa, "Usage: /reject <draft_id>  — get IDs with /drafts")
        return
    draft_id = args[0]
    svc, acct = _find_draft_in_accounts(draft_id)
    if not svc:
        _twilio_send(from_wa, "❌ Draft not found in Wing or Commander accounts.")
        return
    try:
        svc.users().drafts().delete(userId="me", id=draft_id).execute()
        _twilio_send(from_wa, f"🗑️ Draft `{draft_id[:20]}` deleted [{acct}].")
    except Exception as e:
        _twilio_send(from_wa, f"❌ Delete failed: {e}")


def cmd_inbox(from_wa: str, args: list) -> None:
    """Search or list Commander's johnloucks3 inbox. /inbox [query]"""
    query = " ".join(args).strip() if args else ""
    _twilio_send(from_wa, f"⏳ Searching Commander inbox{': ' + query if query else ''}…")
    svc = _get_jl3_svc()
    if not svc:
        _twilio_send(from_wa, "❌ Commander inbox unavailable — check johnloucks3 token.")
        return
    try:
        q = query if query else "in:inbox"
        result = svc.users().messages().list(userId="me", q=q, maxResults=8).execute()
        msgs = result.get("messages", [])
        if not msgs:
            _twilio_send(from_wa, f"📭 No messages found{' for: ' + query if query else ' in inbox'}.")
            return
        lines = [f"⚡ *Commander inbox{' — ' + query if query else ''}:*\n"]
        for m in msgs:
            try:
                detail  = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]
                ).execute()
                headers = {h["name"].lower(): h["value"]
                           for h in detail.get("payload", {}).get("headers", [])}
                subject = headers.get("subject", "(no subject)")[:55]
                sender  = headers.get("from", "?")[:40]
                date    = headers.get("date", "")[:20]
                snippet = detail.get("snippet", "")[:80]
                lines.append(f"`{m['id'][:16]}`\n  From: {sender}\n  Re: {subject}\n  {date}\n  {snippet}\n")
            except Exception:
                lines.append(f"`{m['id'][:16]}` (error)\n")
        _wa_send_chunks(from_wa, "\n".join(lines))
    except Exception as e:
        _twilio_send(from_wa, f"❌ Inbox error: {e}")


# ── Model override detection ─────────────────────────────────────────────────
_MODEL_PREFIXES = {
    "OPUS:"     : "claude-opus-4-8",
    "SONNET:"   : "claude-sonnet-4-6",
    "HAIKU:"    : "claude-haiku-4-5-20251001",
    "GROK:"     : "grok",
    "DEEPSEEK:" : "deepseek",
    "GEMINI:"   : "gemini",
    "GPT:"      : "gpt-4o-mini",
    "LLAMA:"    : "llama",
}

def _detect_model_override(text: str):
    """Returns (model_override_or_None, stripped_text)."""
    upper = text.upper()
    for prefix, model in _MODEL_PREFIXES.items():
        if upper.startswith(prefix):
            return model, text[len(prefix):].strip()
    return None, text


# ── Async dispatcher ─────────────────────────────────────────────────────────
def _dispatch(from_wa: str, msg_body: str) -> None:
    """Route inbound message to the right handler. Runs in background thread."""
    msg = msg_body.strip()
    if not msg:
        return

    log.info("DISPATCH from=%s body=%r", from_wa, msg[:80])

    # Command routing
    if msg.startswith("/"):
        parts  = msg.split()
        cmd    = parts[0].lower()
        args   = parts[1:]
        rest   = " ".join(args)

        if cmd in ("/help", "/h"):
            cmd_help(from_wa)
        elif cmd in ("/status", "/s"):
            cmd_status(from_wa)
        elif cmd in ("/brief", "/b"):
            cmd_brief(from_wa)
        elif cmd in ("/missions", "/m"):
            limit = int(args[0]) if args and args[0].isdigit() else 20
            cmd_missions(from_wa, limit)
        elif cmd == "/tpb":
            cmd_tpb(from_wa, rest)
        elif cmd == "/drafts":
            cmd_drafts(from_wa)
        elif cmd == "/approve":
            cmd_approve(from_wa, args)
        elif cmd == "/reject":
            cmd_reject(from_wa, args)
        elif cmd in ("/inbox", "/i"):
            cmd_inbox(from_wa, args)
        elif cmd in ("/agent", "/a"):
            if not rest:
                _twilio_send(from_wa, "Usage: /agent <task>")
                return
            _twilio_send(from_wa, "⏳ Hale thinking…")
            ctx = CTX_D2MC2C.read_text() if CTX_D2MC2C.exists() else ""
            reply = hale_claude_engine(ctx, rest, None)
            _wa_send_chunks(from_wa, reply)
        elif cmd in ("/relay", "/r"):
            if not rest:
                _twilio_send(from_wa, "Usage: /relay <message to Wing>")
                return
            ts = datetime.now().strftime("%Y-%m-%d %H:%M MT")
            relay_msg = f"Commander via WA [{ts}]: {rest}"
            ok = _tg_relay(relay_msg, label="COMMANDER-WA")
            if ok:
                _twilio_send(from_wa, f"✅ Relayed to Wing via Telegram:\n{rest[:200]}")
            else:
                _twilio_send(from_wa, "❌ Telegram relay failed — check TG gateway logs.")
        else:
            _twilio_send(from_wa, f"Unknown command: {cmd}\nType /help")
        return

    # Model override check
    model_override, clean_msg = _detect_model_override(msg)
    if model_override:
        _twilio_send(from_wa, f"⏳ Routing to {model_override.split('-')[0].upper()}…")

    # Auto-relay detection: Commander says "notify the wing" etc → real Telegram relay
    msg_lower = clean_msg.lower()
    auto_relay = any(trigger in msg_lower for trigger in _RELAY_TRIGGERS)

    # Natural language → Hale engine
    ctx = CTX_D2MC2C.read_text() if CTX_D2MC2C.exists() else ""
    try:
        reply = hale_claude_engine(ctx, clean_msg, model_override)
    except Exception as exc:
        reply = f"⚡ Engine error — {exc}"

    _wa_send_chunks(from_wa, reply)

    # If auto-relay triggered, actually send to Telegram (not just claim to)
    if auto_relay:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M MT")
        relay_body = f"Commander via WA [{ts}]:\n{clean_msg}\n\n— Hale response:\n{reply[:500]}"
        ok = _tg_relay(relay_body, label="AUTO-RELAY")
        if ok:
            _twilio_send(from_wa, "✅ Wing notified via Telegram relay.")
        else:
            _twilio_send(from_wa, "⚠️ Telegram relay failed — use /relay <msg> to retry.")


# ── Twilio signature validation ──────────────────────────────────────────────
def _validate_twilio_request(url: str, params: dict, signature: str) -> bool:
    """Validate incoming Twilio request using X-Twilio-Signature.

    Twilio's algorithm (POST form data):
      1. Start with the full URL
      2. Sort POST params alphabetically by key
      3. Append each key+value (no delimiter) to the URL string
      4. HMAC-SHA1 of that string with the Auth Token
      5. Base64-encode and compare

    Common bug: hashing (url + raw_body_string) — WRONG.
    The body must be parsed and sorted, not passed raw.
    """
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not token:
        log.error("TWILIO_AUTH_TOKEN not set — cannot validate signature")
        return False

    # Build the string Twilio signed: URL + sorted params concatenated
    s = url
    for key in sorted(params.keys()):
        s += key + (params[key] or "")
    mac = hmac.new(token.encode(), s.encode("utf-8"), hashlib.sha1)
    computed_sig = b64encode(mac.digest()).decode()

    valid = hmac.compare_digest(computed_sig, signature)
    if not valid:
        log.warning("Twilio signature FAILED (computed=%s, got=%s)", computed_sig, signature)
    return valid


# ── HTTP server ──────────────────────────────────────────────────────────────
class WAHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"wa_c2 OK")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path not in ("/whatsapp", "/whatsapp/"):
            self.send_response(404)
            self.end_headers()
            return

        length   = int(self.headers.get("Content-Length", 0))
        body     = self.rfile.read(length)
        body_str = body.decode("utf-8")
        params   = dict(urllib.parse.parse_qsl(body_str))
        from_wa  = params.get("From", "")
        msg_body = params.get("Body", "").strip()

        log.info("Inbound WA from=%s body=%r", from_wa, msg_body[:80])

        # Validate Twilio signature FIRST
        signature = self.headers.get("X-Twilio-Signature", "")
        # URL used for signature: full URL with scheme/host
        url = f"https://wa.d2mluxury.quest{self.path}"

        if not _validate_twilio_request(url, params, signature):
            log.error("Signature validation failed — rejecting request (likely spam/replay)")
            self.send_response(403)
            self.end_headers()
            return

        # CRITICAL: Verify sender is the Commander (whitelist only COMMANDER_WA)
        if from_wa != COMMANDER_WA:
            log.error("UNAUTHORIZED sender — rejecting: from=%s (expected %s)", from_wa, COMMANDER_WA)
            self.send_response(403)
            self.end_headers()
            return

        # Acknowledge immediately — Twilio 15s hard timeout
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        self.wfile.write(b'<?xml version="1.0" encoding="UTF-8"?><Response></Response>')
        log.info("Webhook signature + sender authorization validated ✓")

        if msg_body:
            threading.Thread(
                target=_dispatch, args=(from_wa, msg_body), daemon=True
            ).start()


class _ReuseAddrHTTPServer(HTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    log.info("WhatsApp C2 starting on port %d", PORT)
    log.info("Endpoint: https://wa.d2mluxury.quest/whatsapp")
    log.info("Engine: %s", _ENGINE_SOURCE)
    server = _ReuseAddrHTTPServer(("127.0.0.1", PORT), WAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutdown")
