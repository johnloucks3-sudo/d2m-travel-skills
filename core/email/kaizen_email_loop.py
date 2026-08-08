#!/usr/bin/env python3
"""core/email/kaizen_email_loop.py — KAIZEN email answer loop (Instructor Mode
Round 3 build, 2026-08-08, Weapons Free / ~90% OC workshare).

BLUF: One poll cycle, two passes, one file.

Pass 1 — OUTBOUND: scan OpsCenter/tickets/*.json. For each ticket with
status done|blocked and no truthy `answer_emailed` (and a submitted_email),
email the ticket's result back to the submitter.
  - verified_reply == True (a follow-up created by Pass 2): AUTO-SEND via
    gmail_send_as_persona(), with a NOW-urgency Telegram alert and an hourly
    rate cap (3 per submitted_email, 10 system-wide — computed by scanning
    ticket files' answer_emailed_at timestamps, no new state file).
  - otherwise (an original ticket): DRAFT only via gmail_create_draft_sync()
    for Commander review. No alert — Commander already reviews drafts.
  - A blunt content guardrail scans the body before ANY draft/send; a hit
    marks the ticket answer_emailed="blocked_guardrail" and emails nothing.

Pass 2 — INBOUND: fetch_unread() the d2mconcierge inbox. Only messages whose
subject carries a [KAI-(kzn-...)] tag are owned by this loop; everything else
is left untouched (no mark_read) for the rest of the inbox. A tagged reply
becomes a new follow-up ticket for the tagged parent, only if the sender's
address exactly matches the parent's submitted_email. A mismatch fires a
NOW-urgency alert and marks the message read; no ticket is created.

CLI:
  python3 core/email/kaizen_email_loop.py            # --dry-run (default):
                                                     #   local ticket scan only,
                                                     #   prints what WOULD happen;
                                                     #   zero Gmail API calls,
                                                     #   zero file writes
  python3 core/email/kaizen_email_loop.py --dry-run  # same
  python3 core/email/kaizen_email_loop.py --live     # real thing (network+writes)

Field-name ground truth (verified against live code 2026-08-08, per build spec):
  - ticket["result"]  — real completion field written by
    scripts/kaizen_runner.py:80 (update_ticket). The answer to email is
    ticket["result"]. Spec's "result" assumption held.
  - fetch_unread()    — returns dicts keyed gmail_id/thread_id/message_id_header/
    from_addr/from_raw/subject/date/body (email_conversation_agent.py:237-274).
    NOTE: NOT 'from'/'message_id' as the spec assumed — using the real keys.
    from_addr is already _extract_addr()'d + lowercased by fetch_unread, so the
    sender check uses it directly.
  - gmail_create_draft_sync() (thunderbird_gmail.py:2847) creates a DRAFT,
    never sends; returns {"status":"success","draft_id",...}.
  - gmail_send_as_persona() (thunderbird_gmail.py:2485) REAL-SENDS; returns
    {"status":"success","message_id",...} or {"status":"blocked"} under
    SEND_LOCKOUT.
  - gmail_reply_in_thread() hard-blocks non-Commander addresses
    (thunderbird_gmail.py:2422) — deliberately NOT used; it is the wrong
    function for staff-address sends.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).resolve().parents[2]
if str(THUNDERBIRD_DIR) not in sys.path:
    sys.path.insert(0, str(THUNDERBIRD_DIR))

from core.relay.task_templates import TICKETS_DIR, build_cc_task, write_ticket

# ── Configuration ────────────────────────────────────────────────────────────
COMMANDER_EMAIL = "johnloucks3@gmail.com"  # mirrors scripts/kaizen_intake_server.py:52
ANSWER_TOPIC = "Your KAIZEN ticket result"

# Dedup state for Pass 2 — bounded processed-id list, same pattern as
# email_conversation_agent.py's `_processed_ids` (bounded to last 1000).
PROCESSED_STATE_FILE = THUNDERBIRD_DIR / "OpsCenter" / "state" / "kaizen_email_loop_processed.json"
PROCESSED_BOUND = 1000

# Auto-send rate caps (Pass 1, verified_reply only).
RATE_LIMIT_SAME_EMAIL = 3     # auto-sends to one submitted_email per hour
RATE_LIMIT_GLOBAL = 10        # auto-sends system-wide per hour
RATE_LIMIT_WINDOW = timedelta(hours=1)

# Inbound KAI tag — the bracket form this loop itself stamps into answer
# subjects, so a client's reply can be re-attached to the ticket thread.
KAI_TAG_RE = re.compile(r"\[KAI-(kzn-[a-zA-Z0-9_-]+)\]")
_RE_RE_FWD = re.compile(r"^(?:re|fwd|fw)\s*:\s*", re.IGNORECASE)

# Content guardrail — deliberately blunt first-pass filter (build spec: "do
# not try to be clever about it"). A body that leaks credentials or absolute
# home paths never gets drafted or sent.
_GUARDRAIL_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),      # AWS access key id
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),   # sk-* API key
    re.compile(r"/home/john/", re.IGNORECASE),            # absolute home path
    re.compile(r"ANTHROPIC_API_KEY", re.IGNORECASE),     # env var name
    re.compile(r"KAIZEN_INTAKE_PASS", re.IGNORECASE),    # shared intake password env
    re.compile(r"[a-zA-Z0-9]{32,}", re.IGNORECASE),       # 32+ char hex/base64 token
]


def say(msg: str) -> None:
    print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_all_tickets() -> list[dict]:
    """All ticket files, malformed ones skipped (mirrors read_open_tickets)."""
    if not TICKETS_DIR.exists():
        return []
    out = []
    for p in sorted(TICKETS_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def _guardrail_hits(body: str) -> list[str]:
    """Return which guardrail patterns matched, [] if the body is clean."""
    hits = []
    for rx in _GUARDRAIL_PATTERNS:
        if rx.search(body or ""):
            hits.append(rx.pattern)
    return hits


REPLY_BASE_URL = "https://kaizen.d2mluxury.quest/reply"


def _reply_link(ticket_id: str) -> str:
    """HMAC-signed link to the stripped reply-by-form page (RT-KAIZEN-
    REPLY-FORM, 2026-08-08) — replaces email-reply threading entirely, so
    this must be in every answer or the loop has no way back."""
    from scripts.kaizen_intake_server import sign_ticket_id
    sig = sign_ticket_id(ticket_id)
    return f"{REPLY_BASE_URL}?ticket={ticket_id}&sig={sig}"


REWRITE_PROMPT = """You are Dani Moreau, D2M's luxury travel concierge, writing a warm,
personal reply email. Below is the RAW output from a research/build ticket — it may contain
process narration ("Wilco", "researching...", "let me check", tool-call chatter), markdown
syntax (**, #, code fences), or other technical scaffolding that has no place in a client-
facing email.

Rewrite it as Dani would actually say it: warm, direct, personal, plain prose. Strip every
trace of the technical process — the reader should never see how the answer was produced,
only the answer itself. Do not invent, add, or drop any factual content — same substance,
different voice. No markdown syntax in the output (plain text email). Do not add a greeting
or sign-off — those are added separately. Output ONLY the rewritten body text, nothing else.

RAW CONTENT:
{raw}
"""


def _dani_rewrite(raw_result: str) -> str:
    """Voice pass (Commander directive 2026-08-08: "make the technical coding
    invisible, amp up the Dani voice"). Runs on Haiku — right-sized for a
    tone/formatting rewrite, not a reasoning task. Falls back to the raw
    result on any failure rather than blocking the email entirely — a
    technical-sounding answer beats no answer."""
    try:
        from scripts.kaizen_runner import run_local_claude
        r = run_local_claude(
            REWRITE_PROMPT.format(raw=raw_result[:4000]),
            alias="haiku", timeout_s=60,
        )
        if r.returncode == 0 and (r.stdout or "").strip():
            return r.stdout.strip()
    except Exception:
        pass
    return raw_result  # fallback — never block the email over a voice pass


def _answer_subject(ticket: dict) -> str:
    base = f"[KAI-{ticket.get('ticket_id', '?')}] {ANSWER_TOPIC}"
    if ticket.get("parent_ticket_id"):
        return f"Re: {base}"
    return base


def _answer_body(ticket: dict) -> str:
    raw_result = ticket.get("result") or "(no result recorded)"
    voiced = _dani_rewrite(raw_result)
    tid = ticket.get("ticket_id", "?")
    return "\n".join([
        "Hi there — Dani here at Dreams2Memories.",
        "",
        f"Your ticket ({tid}) came back. Here's what we found:",
        "",
        voiced,
        "",
        "---",
        f"Got a follow-up? Reply here: {_reply_link(tid)}",
        "",
        "Dani Moreau",
        "Dreams2Memories Travel, LLC",
    ])


def _count_recent_sends(tickets: list[dict], email: str, now: datetime) -> tuple[int, int]:
    """(same-email auto-sends, total auto-sends) within the last hour, from
    ticket answer_method/answer_emailed_at fields. Malformed timestamps are
    ignored rather than counted."""
    same = 0
    total = 0
    for t in tickets:
        if t.get("answer_method") != "sent" or not t.get("answer_emailed_at"):
            continue
        try:
            ts = datetime.fromisoformat(str(t["answer_emailed_at"]))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = now - ts
        if timedelta(0) <= delta <= RATE_LIMIT_WINDOW:
            total += 1
            if (t.get("submitted_email") or "").strip().lower() == email.lower():
                same += 1
    return same, total


def _load_processed() -> list[str]:
    """Insertion-ordered (oldest first) — a plain set loses that order, which
    would make the bound in _save_processed trim an arbitrary mix instead of
    strictly the oldest entries (AG cross-engine finding, 2026-08-08)."""
    try:
        return list(json.loads(PROCESSED_STATE_FILE.read_text()).get("processed_ids", []))
    except (json.JSONDecodeError, OSError):
        return []


def _save_processed(ids: list[str]) -> None:
    PROCESSED_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    bounded = ids[-PROCESSED_BOUND:]
    tmp = PROCESSED_STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"processed_ids": bounded}, indent=2))
    tmp.replace(PROCESSED_STATE_FILE)


def _notify_auto_send(ticket: dict, email: str, snippet: str) -> None:
    """NOW-urgency Telegram alert on every auto-send — no exceptions."""
    try:
        from core.comms.commander_channel import notify
        notify(
            "ops",
            f"KAIZEN auto-sent: {ticket.get('ticket_id', '?')}",
            (
                f"**Auto-sent** (verified follow-up reply) to **{email}** on "
                f"KAIZEN ticket `{ticket.get('ticket_id', '?')}`.\n\n"
                f"Subject: `{_answer_subject(ticket)}`\n\n"
                f"Snippet:\n```\n{snippet}\n```"
            ),
            urgency="NOW",
            reason="KAIZEN email loop auto-send (verified_reply) — every auto-send is visible",
            dedup_key=f"kaizen-autosend-{ticket.get('ticket_id', '?')}",
            source="kaizen_email_loop",
        )
    except Exception:
        say(f"  (auto-send Telegram alert failed — non-fatal)")


FACT_CHECK_PROMPT = """Fact-check the factual claims below (nothing else — ignore tone,
grammar, formatting). This content is about to be auto-sent to a real person with no
human review, so be strict: flag anything you are not confident is currently, exactly
correct, including tax law, benefits eligibility, prices, addresses, or any claim that
could have changed or could vary by circumstance.

If every factual claim checks out with real confidence, respond with EXACTLY:
VERIFIED: no issues found

If ANY claim is wrong, outdated, oversimplified, or you're not confident, respond with:
FLAGGED: <one sentence, name the specific claim and what's wrong or uncertain about it>

Respond with nothing else — one line, one of those two forms exactly.

CONTENT TO CHECK:
{content}
"""


def _fact_check(raw_result: str) -> tuple[bool, str]:
    """Independent cross-engine check (AG/Gemini, not the same engine that
    wrote the content) before ANY auto-send — Commander directive 2026-08-08
    after a real wrong tax-law claim reached a real inbox on the auto-send
    path. Fails CLOSED: any error, timeout, or ambiguous response is treated
    as FLAGGED (falls back to draft), never treated as a pass. Only gates
    the auto-send path — drafts already get Commander review and don't need
    this (and paying the latency for every draft would be wasteful)."""
    import subprocess
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, dir=str(THUNDERBIRD_DIR / "OpsCenter" / "state")
        ) as f:
            deliverable = f.name
        r = subprocess.run(
            [sys.executable, str(THUNDERBIRD_DIR / "core" / "relay" / "contact_ag.py"),
             FACT_CHECK_PROMPT.format(content=raw_result[:3000]),
             "--deliverable", deliverable, "--from", "CC", "--tag", "KAIZEN-FACTCHECK",
             "--timeout", "180"],
            capture_output=True, text=True, timeout=200,
        )
        verdict = Path(deliverable).read_text().strip() if Path(deliverable).exists() else ""
        Path(deliverable).unlink(missing_ok=True)
        if r.returncode != 0 or not verdict:
            return False, "fact-check dispatch failed or returned nothing — failing closed"
        if verdict.upper().startswith("VERIFIED"):
            return True, ""
        return False, verdict[:300]
    except Exception as exc:
        return False, f"fact-check error: {exc} — failing closed"


def _notify_unexpected_sender(ticket_id: str, actual: str, expected: str) -> None:
    """NOW-urgency alert when a tagged reply comes from a non-matching sender."""
    try:
        from core.comms.commander_channel import notify
        notify(
            "ops",
            f"KAIZEN reply from unexpected sender: {ticket_id}",
            (
                f"Reply to KAIZEN thread `{ticket_id}` from **{actual or '(blank)'}** "
                f"— expected **{expected or '(blank)'}**. No ticket created; message marked read."
            ),
            urgency="NOW",
            reason="KAIZEN email loop — sender mismatch on tagged thread",
            dedup_key=f"kaizen-mismatch-{ticket_id}",
            source="kaizen_email_loop",
        )
    except Exception:
        say("  (unexpected-sender Telegram alert failed — non-fatal)")


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — OUTBOUND
# ─────────────────────────────────────────────────────────────────────────────
def pass1_outbound(live: bool) -> int:
    tickets = _load_all_tickets()
    now = datetime.now(timezone.utc)
    acted = 0
    for t in tickets:
        tid = t.get("ticket_id", "?")
        if t.get("status") not in ("done", "blocked"):
            continue
        if t.get("answer_emailed"):
            continue
        email = (t.get("submitted_email") or "").strip()
        if not email:
            say(f"[{tid}] no submitted_email — left untouched")
            continue

        subject = _answer_subject(t)
        # Guardrail scans the ticket's OWN content only (result + spec) —
        # not the full rendered body, which now also contains our own
        # trusted infrastructure (the HMAC-signed reply link). A 32-char
        # signature legitimately matches the same blunt token pattern this
        # guardrail exists to catch in a model's actual output; scanning
        # post-render would self-sabotage the reply link on every ticket
        # (confirmed live, 2026-08-08).
        guardrail_source = f"{t.get('result', '')}\n{t.get('spec', '')}"
        body = _answer_body(t)
        hits = _guardrail_hits(guardrail_source)
        if hits:
            say(f"[{tid}] GUARDRAIL {hits} — no draft/send; "
                f"{'marked answer_emailed=blocked_guardrail' if live else 'WOULD mark answer_emailed=blocked_guardrail'}")
            if live:
                t["answer_emailed"] = "blocked_guardrail"
                t["answer_emailed_at"] = now.isoformat()
                write_ticket(t)
            acted += 1
            continue

        verified = t.get("verified_reply") is True
        if verified:
            same, total = _count_recent_sends(tickets, email, now)
            if same >= RATE_LIMIT_SAME_EMAIL or total >= RATE_LIMIT_GLOBAL:
                say(f"[{tid}] RATE CAP (same={same}/{RATE_LIMIT_SAME_EMAIL}, "
                    f"global={total}/{RATE_LIMIT_GLOBAL}) — answer_emailed left "
                    f"unset, retry next poll")
                continue

        if not live:
            action = "WOULD AUTO-SEND" if verified else "WOULD DRAFT"
            say(f"[DRY-RUN] [{tid}] {action} to {email} — subject={subject!r} ({len(body)} chars)")
            acted += 1
            continue

        # Independent fact-check gate — only on the auto-send path (a draft
        # already gets Commander review, no need to pay the latency there).
        # Fails closed: any doubt downgrades to draft, never blocks entirely.
        send_now = verified
        if verified:
            fc_pass, fc_note = _fact_check(t.get("result", ""))
            if not fc_pass:
                say(f"[{tid}] FACT-CHECK FLAGGED — downgrading to draft: {fc_note}")
                send_now = False
                body = body.replace(
                    "---\nGot a follow-up?",
                    f"[Note: an independent check flagged something in this answer for "
                    f"review before it goes out — {fc_note}]\n\n---\nGot a follow-up?",
                )

        if send_now:
            from core.email.thunderbird_gmail import gmail_send_as_persona
            res = gmail_send_as_persona(
                to=email, subject=subject, body=body,
                persona_id="CONCIERGE", cc=COMMANDER_EMAIL,
            )
            if res.get("status") == "success":
                t["answer_emailed"] = True
                t["answer_emailed_at"] = now.isoformat()
                t["answer_method"] = "sent"
                t["answer_message_id"] = res.get("message_id", "")
                write_ticket(t)
                say(f"[{tid}] AUTO-SENT to {email} — msg {res.get('message_id')}")
                _notify_auto_send(t, email, body[:200])
            else:
                say(f"[{tid}] send FAILED ({res.get('status')}: "
                    f"{res.get('error', '')}) — answer_emailed left unset, retry next poll")
        else:
            from core.email.thunderbird_gmail import gmail_create_draft_sync
            res = gmail_create_draft_sync(
                to=email, subject=subject, body=body, cc=COMMANDER_EMAIL,
            )
            if res.get("status") == "success":
                t["answer_emailed"] = True
                t["answer_emailed_at"] = now.isoformat()
                t["answer_method"] = "draft"
                t["answer_draft_id"] = res.get("draft_id", "")
                write_ticket(t)
                say(f"[{tid}] DRAFT created for {email} — draft {res.get('draft_id')}")
            else:
                say(f"[{tid}] draft FAILED ({res.get('status')}: "
                    f"{res.get('error', '')}) — answer_emailed left unset, retry next poll")
        acted += 1
    return acted


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — INBOUND
# ─────────────────────────────────────────────────────────────────────────────
def _strip_re_fwd(subject: str) -> str:
    s = (subject or "").strip()
    while True:
        n = _RE_RE_FWD.sub("", s, count=1).strip()
        if n == s:
            return s
        s = n


def pass2_inbound(live: bool) -> int:
    """RETIRED (RT-KAIZEN-REPLY-FORM, 2026-08-08): email-reply threading was
    structurally broken — the answer draft is hosted in the Commander's own
    Gmail account (so he reviews/sends from where he actually looks), which
    means a plain reply lands in HIS inbox, not the one this function polled.
    Replaced by the HMAC-signed reply-by-form link embedded in every answer
    (see _reply_link / kaizen_intake_server.py's /reply routes) — no email
    parsing needed, the parent link IS the correlation. Left in place, inert,
    rather than deleted, in case a future design wants the old mechanism back.
    """
    say("[LIVE] Pass 2 INBOUND retired — replaced by the reply-form link "
        "embedded in every answer (see RT-KAIZEN-REPLY-FORM)")
    return 0
    # --- retired implementation below, unreachable, kept for reference ---
    if not live:
        say("[DRY-RUN] Pass 2 INBOUND skipped — fetch_unread() is a Gmail "
            "network call; dry-run makes zero API calls")
        return 0

    from core.email.email_conversation_agent import (
        _strip_quoted_reply, fetch_unread, mark_read,
    )
    from core.email.thunderbird_gmail import _get_wing_gmail_service

    service = _get_wing_gmail_service()
    processed = _load_processed()          # insertion-ordered, oldest first
    seen_order = list(processed)           # what actually gets saved back
    seen_lookup = set(processed)           # O(1) membership check
    created = 0

    def _mark_seen(gmail_id: str) -> None:
        if gmail_id not in seen_lookup:
            seen_lookup.add(gmail_id)
            seen_order.append(gmail_id)

    unread = fetch_unread(service)
    say(f"[{len(unread)}] unread message(s) fetched")

    for msg in unread:
        gid = msg.get("gmail_id") or ""
        if not gid or gid in seen_lookup:
            continue

        subject = _strip_re_fwd(msg.get("subject") or "")
        m = KAI_TAG_RE.search(subject)
        if not m:
            continue  # not ours — leave unread for whatever else owns the inbox

        parent_id = m.group(1)
        parent_path = TICKETS_DIR / f"{parent_id}.json"
        if not parent_path.exists():
            say(f"[{gid}] [KAI-{parent_id}] tag but no such ticket — mark_read, skipped")
            mark_read(service, gid)
            _mark_seen(gid)
            continue
        try:
            parent = json.loads(parent_path.read_text())
        except (json.JSONDecodeError, OSError):
            say(f"[{gid}] [KAI-{parent_id}] parent ticket unreadable — mark_read, skipped")
            mark_read(service, gid)
            _mark_seen(gid)
            continue

        expected = (parent.get("submitted_email") or "").strip().lower()
        actual = (msg.get("from_addr") or "").strip().lower()
        if not expected or actual != expected:
            say(f"[{gid}] UNEXPECTED SENDER — {actual!r} != expected {expected!r} "
                f"— NOW alert + mark_read, no ticket")
            _notify_unexpected_sender(parent_id, actual, expected)
            mark_read(service, gid)
            _mark_seen(gid)
            continue

        stripped = _strip_quoted_reply(msg.get("body") or "")
        try:
            follow = build_cc_task(
                f"[FOLLOW-UP to {parent_id}] {stripped}\n\n"
                f"[Context: {(parent.get('spec') or '')[:300]}]",
                seat=parent.get("seat", "CC"),
                verify_step=parent.get("verify_step", ""),
                gates=parent.get("gates") or [],
                require_checkable=True,
            )
        except Exception as e:  # e.g. uncheckable parent verify_step
            say(f"[{gid}] [KAI-{parent_id}] follow-up build rejected ({e}) — mark_read, skipped")
            mark_read(service, gid)
            _mark_seen(gid)
            continue

        follow.update({
            "origin": "kaizen_email_reply",
            "parent_ticket_id": parent_id,
            "submitted_by": parent.get("submitted_by", "unknown"),
            "submitted_email": parent.get("submitted_email", ""),
            "submitted_phone": parent.get("submitted_phone", ""),
            "verified_reply": True,
        })
        write_ticket(follow)
        mark_read(service, gid)
        _mark_seen(gid)
        say(f"[{gid}] created follow-up ticket {follow['ticket_id']} "
            f"(parent {parent_id}, seat {follow['seat']})")
        created += 1

    if seen_order != processed:
        _save_processed(seen_order)
    return created


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    live = "--live" in sys.argv[1:]
    mode = "LIVE" if live else "DRY-RUN"
    say(f"[{mode}] kaizen_email_loop — pass 1 OUTBOUND")
    out = pass1_outbound(live)
    say(f"[{mode}] pass 1 complete: {out} ticket(s) acted on")
    say(f"[{mode}] kaizen_email_loop — pass 2 INBOUND")
    inbound = pass2_inbound(live)
    say(f"[{mode}] pass 2 complete: {inbound} follow-up ticket(s) created")


if __name__ == "__main__":
    main()
