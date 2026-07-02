#!/usr/bin/env python3
"""Two-way email conversation agent for Dreams2Memories Travel (Thunderbird Wing).

Closes the loop:

    Commander (johnloucks3@gmail.com)  ->  d2mconcierge@gmail.com  inbox
        -> this agent reads it, runs Hale (Claude) with thread history
        -> replies IN-THREAD from d2mconcierge (auto-send, Commander-only)
        -> Commander replies -> lands back in d2mconcierge -> multi-turn continues

    Client / anyone else  ->  d2mconcierge@gmail.com  inbox
        -> classified, drafted via the WF-17 path (create draft, DO NOT SEND)
        -> Commander reviews + sends manually.

Design constraints (hard):
  * Two structurally-separate send paths. There is NO shared send function that
    a client email and a Commander email both flow through.
      - Commander  -> gmail_reply_in_thread()  (auto-send; guarded to Commander addrs)
      - Client     -> gmail_create_draft_sync() (draft only; never sends)
      - Unknown    -> default-deny: draft-or-skip, never auto-send.
  * Threading uses the RFC822 `Message-ID` HEADER (not the Gmail API message id),
    so In-Reply-To / References nest correctly.
  * --test-mode is inert: no Gmail auth, no Anthropic call, no send. It only
    verifies imports resolve, persona/config load, and state files parse.

State:
  OpsCenter/email_conversation_state.json   -- per-thread conversation history
  OpsCenter/email_canary_scoreboard.json    -- interaction log / canary scoreboard

Usage:
    python3 core/email/email_conversation_agent.py --test-mode   # load check
    python3 core/email/email_conversation_agent.py               # one poll cycle
    python3 core/email/email_conversation_agent.py --dry-run     # classify, no send/draft
    python3 core/email/email_conversation_agent.py --loop 300    # poll every 300s
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Path bootstrap ───────────────────────────────────────────────────────────
# Repo root on sys.path so `from core.email...` resolves regardless of CWD.
THUNDERBIRD_DIR = Path(__file__).resolve().parents[2]
if str(THUNDERBIRD_DIR) not in sys.path:
    sys.path.insert(0, str(THUNDERBIRD_DIR))

# ── Configuration ────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # Haiku: lower latency, sufficient for email routing
MAX_TOKENS = 1500
COMMANDER_ADDRESS = "johnloucks3@gmail.com"
WING_INBOX = "d2mconcierge@gmail.com"
POLL_MAX_MESSAGES = 20
MAX_PER_RUN = 5  # Process at most 5 new messages per cycle to avoid API saturation
# How many prior turns of a thread to feed the model (keeps token cost bounded).
HISTORY_WINDOW = 20

STATE_FILE = THUNDERBIRD_DIR / "OpsCenter" / "email_conversation_state.json"
SCOREBOARD_FILE = THUNDERBIRD_DIR / "OpsCenter" / "email_canary_scoreboard.json"
PERSONA_FILE = THUNDERBIRD_DIR / "Personas" / "hale_cos.md"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] email_conv_agent: %(message)s",
)
log = logging.getLogger("email_conversation_agent")

# ── Hale system prompt (email replies) ───────────────────────────────────────
HALE_SYSTEM_PROMPT = """\
You are Victoria "Victory" Hale, SES-6, Chief of Staff for Thunderbird Wing, \
Dreams2Memories Travel, LLC. You report to the Commander (Gen John "Yoda" Loucks).

When the Commander emails you a task or question, you:
1. Process it immediately.
2. Reason over the context you have (dossiers, mission board, state files summarized below).
3. Reply concisely with the action taken or the answer given.
4. Sign off as: — V. Hale, VCS

Rules for email replies:
- Bottom line first. Active verbs. No throat-clearing, no trailing summaries.
- Keep replies brief and operational. This is a working back-and-forth, not a formal brief.
- Do NOT ask the Commander to choose between things you could just do. Decide and report.
- The only things that stop you: a client-facing SEND (WF-17 gate), a financial \
commitment, or a strategic decision (>90 days or >$5K). Everything else: execute and report.
- You are replying in an existing email thread. Do not restate the whole thread; \
answer what was just asked.

Operational context (current as of the latest brief):
- Active clients: 16. Pipeline currently $0 (all bookings pre-voyage / paid).
- McLeod (Erik Wiedenbach McLeod + Melissa Etola McGlasson): Regent Seven Seas \
Grandeur 2984034, FPD $11,943.15 due 2026-07-22. Contact hold lifted 2026-07-07 \
(client returned from Silver Muse voyage 2026-07-06). TP 1.1 Voyage Preview staged.
- Kuklinski Group (6 guests, 3 cabins): Viking Ocean Viking Mars, departs 2026-12-17, PAID.
- Loucks family (Commander as client): 3 voyages — Door County Sep 2026, Regent \
Grandeur Dec 2026 (booking 3122006, FPD Aug 1, balance ~$24,798), Silversea Silver \
Nova May 2027. WF-17 waived for Loucks-as-client.
- Furlow / Ely-Darrow / Nichols group: Regent Grandeur, departs 2026-08-29, PAID. \
Itinerary build due 2026-07-22 (MISSION-802).

If you do not know a specific figure, say so plainly rather than inventing one \
(Negative-Space Rule: unconfirmed facts do not go in writing)."""


# ─────────────────────────────────────────────────────────────────────────────
# State + scoreboard I/O
# ─────────────────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    """Load per-thread conversation state. Returns {} if absent/corrupt."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("State file unreadable (%s) — starting fresh", e)
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def load_scoreboard() -> dict:
    """Load the canary scoreboard, initializing the canonical schema if missing."""
    if SCOREBOARD_FILE.exists():
        try:
            sb = json.loads(SCOREBOARD_FILE.read_text())
            sb.setdefault("emails_processed", 0)
            sb.setdefault("entries", [])
            return sb
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Scoreboard unreadable (%s) — reinitializing", e)
    return {
        "canary_start": "2026-07-02",
        "canary_end": "2026-07-09",
        "systems": ["n8n_python", "lindy_ai"],
        "emails_processed": 0,
        "entries": [],
    }


def save_scoreboard(sb: dict) -> None:
    SCOREBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SCOREBOARD_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sb, indent=2))
    tmp.replace(SCOREBOARD_FILE)


def log_interaction(sb: dict, entry: dict) -> None:
    """Append one interaction to the scoreboard and bump the counter."""
    entry.setdefault("ts", _now_iso())
    entry.setdefault("system", "n8n_python")
    sb["entries"].append(entry)
    sb["emails_processed"] = sb.get("emails_processed", 0) + 1


# ─────────────────────────────────────────────────────────────────────────────
# Email parsing helpers
# ─────────────────────────────────────────────────────────────────────────────
def _extract_addr(raw_from: str) -> str:
    """Return the bare lower-cased email address from a From header value."""
    if not raw_from:
        return ""
    m = re.search(r"<([^>]+)>", raw_from)
    addr = m.group(1) if m else raw_from
    return addr.strip().lower()


def _decode_body(payload: dict) -> str:
    """Depth-first extraction of the text/plain body from a Gmail payload."""
    def walk(part):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for sub in part.get("parts", []) or []:
            got = walk(sub)
            if got:
                return got
        return ""

    text = walk(payload)
    if text:
        return text
    # Fallback: some messages carry only text/html.
    def walk_html(part):
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for sub in part.get("parts", []) or []:
            got = walk_html(sub)
            if got:
                return got
        return ""

    html = walk_html(payload)
    if html:
        return re.sub(r"<[^>]+>", " ", html)  # crude tag strip; body is model input only
    return ""


def _strip_quoted_reply(body: str) -> str:
    """Trim the quoted prior message from a reply so the model sees only new text."""
    lines = body.splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        # Common quote markers / reply headers.
        if s.startswith(">"):
            break
        if re.match(r"^On .+wrote:$", s):
            break
        if s.startswith("-----Original Message-----"):
            break
        if re.match(r"^\s*—\s*V\.\s*Hale", ln):  # our own prior signature block
            break
        out.append(ln)
    trimmed = "\n".join(out).strip()
    return trimmed or body.strip()


def fetch_unread(service, max_results: int = POLL_MAX_MESSAGES) -> list[dict]:
    """Fetch unread messages in the d2mconcierge inbox.

    Returns dicts with: gmail_id, thread_id, message_id_header, from_addr,
    from_raw, subject, date, body. Includes ALL senders (Commander AND clients);
    routing by sender happens in the caller.
    """
    results = service.users().messages().list(
        userId="me", q="is:unread in:inbox", maxResults=min(max_results, 50)
    ).execute()
    stubs = results.get("messages", [])
    out = []
    for stub in stubs:
        try:
            full = service.users().messages().get(
                userId="me", id=stub["id"], format="full"
            ).execute()
        except Exception as e:  # noqa: BLE001 — one bad msg must not kill the run
            log.warning("Could not fetch message %s: %s", stub["id"], e)
            continue
        payload = full.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        out.append({
            "gmail_id": full.get("id", ""),
            "thread_id": full.get("threadId", ""),
            # RFC822 Message-ID header — REQUIRED for correct thread nesting.
            "message_id_header": headers.get("message-id", ""),
            "from_raw": headers.get("from", ""),
            "from_addr": _extract_addr(headers.get("from", "")),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "body": _decode_body(payload),
        })
    return out


def mark_read(service, gmail_id: str) -> None:
    try:
        service.users().messages().modify(
            userId="me", id=gmail_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:  # noqa: BLE001
        log.warning("Failed to mark %s read: %s", gmail_id, e)


# ─────────────────────────────────────────────────────────────────────────────
# Claude (Hale) call
# ─────────────────────────────────────────────────────────────────────────────
def build_messages(history: list[dict], new_user_text: str) -> list[dict]:
    """Assemble the Anthropic messages array from stored history + the new email."""
    msgs: list[dict] = []
    for turn in history[-HISTORY_WINDOW:]:
        role = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    # Ensure the new message is the last user turn (avoid duplicating if already stored).
    if not (msgs and msgs[-1]["role"] == "user" and msgs[-1]["content"] == new_user_text):
        msgs.append({"role": "user", "content": new_user_text})
    # Anthropic requires the first message to be a user turn.
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def call_hale(messages: list[dict]) -> str:
    """Call Claude with the Hale persona. Requires ANTHROPIC_API_KEY."""
    import anthropic  # local import: keeps --test-mode from needing the SDK live

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=HALE_SYSTEM_PROMPT,
        messages=messages,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Routing + handlers
# ─────────────────────────────────────────────────────────────────────────────
def is_commander(from_addr: str) -> bool:
    return from_addr == COMMANDER_ADDRESS


def classify_client(from_addr: str, subject: str, snippet: str) -> str:
    """Classify a non-Commander email. Falls back to a local heuristic if the
    canonical rules_classifier is unavailable."""
    try:
        from core.email.rules_classifier import classify  # type: ignore
        return classify(from_addr, subject, snippet)
    except Exception:  # noqa: BLE001
        blob = f"{subject} {snippet}".lower()
        if any(k in blob for k in ("quote", "booking", "cruise", "trip", "interested",
                                   "inquiry", "availability", "price")):
            return "client_inquiry"
        return "other"


def handle_commander(msg: dict, state: dict, sb: dict, dry_run: bool) -> dict:
    """Commander path: run Hale, reply in-thread (auto-send)."""
    from core.email.thunderbird_gmail import gmail_reply_in_thread

    thread_id = msg["thread_id"]
    thread = state.setdefault(thread_id, {
        "messages": [], "last_updated": _now_iso(), "participant": "commander",
    })

    user_text = _strip_quoted_reply(msg["body"]) or msg["subject"]

    if dry_run:
        log.info("[DRY-RUN] Commander msg on thread %s: %r", thread_id, user_text[:80])
        return {"category": "commander", "action": "dry_run", "thread_id": thread_id}

    # Build the model input from the EXISTING history + this new turn. Do NOT
    # mutate persistent history yet — a failed model call or failed send must not
    # leave a dangling user turn, which would corrupt the thread (consecutive
    # user roles) on the next cycle. History is committed only after success.
    messages = build_messages(thread["messages"], user_text)
    reply_text = call_hale(messages)

    send_result = gmail_reply_in_thread(
        thread_id=thread_id,
        in_reply_to=msg["message_id_header"],   # RFC822 header — correct nesting
        subject=msg["subject"],
        body=reply_text,
        persona_id="COS",
        to=COMMANDER_ADDRESS,
    )

    ok = send_result.get("status") == "success"
    if ok:
        # Commit both turns only now — history stays clean if anything above failed.
        thread["messages"].append({"role": "user", "content": user_text, "ts": _now_iso(),
                                   "gmail_id": msg["gmail_id"]})
        thread["messages"].append({"role": "assistant", "content": reply_text, "ts": _now_iso()})
        thread["last_updated"] = _now_iso()

    log_interaction(sb, {
        "category": "commander",
        "action": "replied" if ok else "reply_failed",
        "thread_id": thread_id,
        "from": msg["from_addr"],
        "subject": msg["subject"],
        "reply_status": send_result.get("status"),
        "reply_message_id": send_result.get("message_id"),
    })
    log.info("Commander reply %s on thread %s", send_result.get("status"), thread_id)
    if not ok:
        # Signal the caller NOT to mark-read/dedup so the message is retried.
        raise RuntimeError(f"Commander reply not sent: {send_result.get('error') or send_result.get('status')}")
    return {"category": "commander", "action": "replied", "result": send_result}


def handle_client(msg: dict, state: dict, sb: dict, dry_run: bool) -> dict:
    """Client / non-Commander path: draft via WF-17. NEVER auto-sends.

    Default-deny: only 'client_inquiry' produces a Hale-drafted reply staged for
    Commander review. Everything else is logged and skipped (no send, no draft)."""
    from core.email.thunderbird_gmail import gmail_create_draft_sync

    category = classify_client(msg["from_addr"], msg["subject"], msg["body"][:400])
    thread_id = msg["thread_id"]

    if category != "client_inquiry":
        log_interaction(sb, {
            "category": category, "action": "skipped_non_actionable",
            "thread_id": thread_id, "from": msg["from_addr"], "subject": msg["subject"],
        })
        log.info("Non-actionable (%s) from %s — skipped", category, msg["from_addr"])
        return {"category": category, "action": "skipped"}

    if dry_run:
        log.info("[DRY-RUN] Client inquiry from %s — would draft (WF-17)", msg["from_addr"])
        return {"category": "client_inquiry", "action": "dry_run"}

    # Draft a reply with Hale's help, but STAGE it — no send. WF-17 gate.
    user_text = _strip_quoted_reply(msg["body"]) or msg["subject"]
    draft_context = (
        f"[CLIENT EMAIL — draft a reply for Commander review, do NOT assume it will "
        f"auto-send.]\nFrom: {msg['from_raw']}\nSubject: {msg['subject']}\n\n{user_text}"
    )
    reply_text = call_hale([{"role": "user", "content": draft_context}])

    draft_result = gmail_create_draft_sync(
        to=msg["from_addr"],
        subject=msg["subject"] if msg["subject"].lower().startswith("re:")
        else f"Re: {msg['subject']}",
        body=reply_text,
    )

    # A failed draft must retry — don't let the caller mark it read/processed.
    if draft_result.get("status") not in ("success", "created", "draft_created"):
        raise RuntimeError(f"Client draft not created: "
                           f"{draft_result.get('error') or draft_result.get('status')}")

    log_interaction(sb, {
        "category": "client_inquiry", "action": "drafted_wf17",
        "thread_id": thread_id, "from": msg["from_addr"], "subject": msg["subject"],
        "draft_id": draft_result.get("draft_id"),
        "draft_status": draft_result.get("status"),
        "note": "WF-17: staged for Commander review, NOT sent.",
    })
    log.info("Client inquiry drafted (WF-17) for %s: draft %s",
             msg["from_addr"], draft_result.get("draft_id"))
    return {"category": "client_inquiry", "action": "drafted", "result": draft_result}


# ─────────────────────────────────────────────────────────────────────────────
# Poll cycle
# ─────────────────────────────────────────────────────────────────────────────
def run_cycle(dry_run: bool = False) -> dict:
    """One poll of the d2mconcierge inbox. Routes each unread message by sender."""
    from core.email.thunderbird_gmail import _get_wing_gmail_service

    service = _get_wing_gmail_service()
    state = load_state()
    sb = load_scoreboard()

    unread = fetch_unread(service)
    log.info("Fetched %d unread message(s)", len(unread))

    # Dedup: never process the same Gmail message twice.
    processed_ids = set(state.get("_processed_ids", []))
    summary = {"commander": 0, "client_drafted": 0, "skipped": 0, "already_seen": 0,
               "errors": 0}

    new_this_run = 0
    for msg in unread:
        gid = msg["gmail_id"]
        if gid in processed_ids:
            summary["already_seen"] += 1
            continue
        if new_this_run >= MAX_PER_RUN:
            log.info("Per-run cap (%d) reached — deferring remaining messages", MAX_PER_RUN)
            break
        try:
            if is_commander(msg["from_addr"]):
                handle_commander(msg, state, sb, dry_run)
                summary["commander"] += 1
            else:
                res = handle_client(msg, state, sb, dry_run)
                if res.get("action") == "drafted":
                    summary["client_drafted"] += 1
                else:
                    summary["skipped"] += 1
        except Exception as e:  # noqa: BLE001 — isolate per-message failures
            log.error("Error processing %s from %s: %s", gid, msg["from_addr"], e)
            summary["errors"] += 1
            continue

        if not dry_run:
            processed_ids.add(gid)
            mark_read(service, gid)
        new_this_run += 1

    if not dry_run:
        state["_processed_ids"] = list(processed_ids)[-1000:]  # bound growth
        save_state(state)
        save_scoreboard(sb)

    log.info("Cycle complete: %s", summary)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Test mode (inert): verifies wiring without any network/auth/send
# ─────────────────────────────────────────────────────────────────────────────
def run_test_mode() -> int:
    checks = []

    def check(name, fn):
        try:
            fn()
            checks.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            checks.append((name, False, str(e)))

    # 1. Persona file present.
    check("persona file exists", lambda: PERSONA_FILE.exists() or
          (_ for _ in ()).throw(FileNotFoundError(str(PERSONA_FILE))))

    # 2. State + scoreboard parse (or initialize cleanly).
    check("state loads", lambda: isinstance(load_state(), dict))
    check("scoreboard loads with schema", lambda: (
        lambda sb: all(k in sb for k in ("canary_start", "systems",
                                         "emails_processed", "entries"))
    )(load_scoreboard()) or (_ for _ in ()).throw(ValueError("scoreboard schema")))

    # 3. thunderbird_gmail import + required send functions resolve.
    def _gmail_imports():
        from core.email.thunderbird_gmail import (  # noqa: F401
            gmail_reply_in_thread, gmail_create_draft_sync, _get_wing_gmail_service,
            COMMANDER_ADDRS,
        )
        assert COMMANDER_ADDRESS in COMMANDER_ADDRS, \
            f"{COMMANDER_ADDRESS} missing from COMMANDER_ADDRS (reply guard would block)"
    check("gmail send paths import + guard set", _gmail_imports)

    # 4. anthropic SDK importable (no network call).
    check("anthropic SDK importable", lambda: __import__("anthropic"))

    # 5. Message-array assembly works.
    def _assemble():
        hist = [{"role": "user", "content": "hi"},
                {"role": "assistant", "content": "Wilco."}]
        m = build_messages(hist, "what's the McLeod FPD?")
        assert m[0]["role"] == "user"
        assert m[-1] == {"role": "user", "content": "what's the McLeod FPD?"}
    check("messages array assembles", _assemble)

    # 6. Sender routing is structurally separate.
    def _routing():
        assert is_commander(COMMANDER_ADDRESS) is True
        assert is_commander("stranger@example.com") is False
    check("sender routing", _routing)

    # 7. Body parsing helpers.
    def _parse():
        assert _extract_addr('"John" <johnloucks3@gmail.com>') == COMMANDER_ADDRESS
        assert _strip_quoted_reply("New text\n> quoted\n> more") == "New text"
    check("email parsing helpers", _parse)

    print("\n=== email_conversation_agent --test-mode ===")
    ok = True
    for name, passed, err in checks:
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}" + (f"  -- {err}" if err else ""))
        ok = ok and passed
    print(f"\nResult: {'ALL CHECKS PASSED' if ok else 'FAILURES PRESENT'}\n")
    return 0 if ok else 1


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="D2M two-way email conversation agent")
    ap.add_argument("--test-mode", action="store_true",
                    help="Inert load check — no auth, no network, no send.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch + classify + route, but never send or draft.")
    ap.add_argument("--loop", type=int, metavar="SECONDS",
                    help="Poll continuously every N seconds.")
    args = ap.parse_args()

    if args.test_mode:
        return run_test_mode()

    if args.loop:
        log.info("Starting poll loop every %ds (Ctrl-C to stop)", args.loop)
        while True:
            try:
                run_cycle(dry_run=args.dry_run)
            except Exception as e:  # noqa: BLE001
                log.error("Cycle failed: %s", e)
            time.sleep(args.loop)

    run_cycle(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
