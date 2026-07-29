"""
core/comms/commander_channel.py — THE SINGLE OUTBOUND GATE TO THE COMMANDER.

C2 RECALIBRATION, Commander directive 2026-07-29. Plan: ~/.claude/plans/misty-churning-feather.md

WHY THIS EXISTS
---------------
Before this module, 44 files called `messages().send()` directly and 140 could send
Telegram. Exactly 2 used the canonical sender. Consequences, all verified on 2026-07-29:

  * "[D2M Weekly Report]" delivered 11:34 AND 11:48. "D2M FPD ALERT" 11:30 AND 11:43.
    Same subject, ~13 minutes apart. No send-level dedup existed anywhere, so
    "stop sending me dupes" had nowhere to be implemented.
  * The Innovation Scan arrived as raw markdown ("# Innovation Scan", "**Generated:**").
    The Weekly Report body contained "Base directory for this skill: /home/john/.claude/"
    — skill-loader scaffolding leaking straight into the Commander's inbox.
  * SO-REPORTING-2026 declared two delivery windows. Nothing enforced them: the
    consolidated briefs were ADDED and the old senders were never turned off.

Every byte that reaches the Commander now passes through notify(). One place to dedup,
one renderer, one schedule, one audit trail.

CONTRACT
--------
    notify(kind, title, body_md, *, urgency="WINDOW", dedup_key=None,
           source=None, reason=None) -> dict

  urgency="WINDOW" (default) — QUEUED, not sent. Flushed into the 06:30 or 18:30
      consolidated brief by flush_window(). This is the Commander's chosen posture.
  urgency="NOW" — breaks through immediately. Reserved for money-at-risk and
      client-critical dates. REQUIRES `reason`, which is recorded in the audit log.

Returns {"status": "sent"|"queued"|"suppressed"|"rejected", ...} and NEVER raises on
a delivery problem — a broken notification must not take down its caller. Programming
errors (bad urgency, missing reason) DO raise, because those are bugs, not runtime faults.
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

COMMANDER = "johnloucks3@gmail.com"

AUDIT_PATH = ROOT / "OpsCenter" / "commander_channel.jsonl"
QUEUE_PATH = ROOT / "OpsCenter" / "state" / "commander_channel_queue.jsonl"

DEDUP_WINDOW_HOURS = 24

# ── Scaffolding defects observed in the Commander's actual inbox, 2026-07-29 ──────
# These are not hypothetical. Each pattern was pulled from a real delivered email.
_SCAFFOLD_PATTERNS = [
    (re.compile(r"Base directory for this skill:", re.I),
     "skill-loader scaffolding ('Base directory for this skill:') — seen in the "
     "2026-07-29 [D2M Weekly Report]"),
    (re.compile(r"^\s*(?:<[^>]+>\s*)?(?:Base directory|Allowed tools|Tool use:)", re.I | re.M),
     "agent-harness scaffolding leaked into body"),
    (re.compile(r"VCSAF-EQUIVALENT\s*[►▸>]\s*CHIEF OF STAFF", re.I),
     "persona banner boilerplate — pure chrome, zero information"),
]

_RAW_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)
_RAW_MD_BOLD_LINE = re.compile(r"^\s{0,3}\*\*[^*\n]+\*\*", re.M)


class NotifyError(ValueError):
    """A programming error in a notify() call — bad urgency, missing reason."""


# ─────────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a corrupt line must not blind the whole gate
    return out


def _audit(**row: Any) -> dict:
    row.setdefault("ts", _now().isoformat())
    _append(AUDIT_PATH, row)
    return row


# ─────────────────────────────────────────────────────────────────────────────────
# Content checks — the reason the Commander could not read his mail
# ─────────────────────────────────────────────────────────────────────────────────

def check_body(body_md: str) -> Optional[str]:
    """Return a rejection reason, or None if the body is fit to send.

    Rejections are LOUD: they are audited and the caller is told. A body that fails
    here is never silently shipped in a degraded form — silent degradation is how
    raw markdown reached the Commander's inbox in the first place.
    """
    if not body_md or not body_md.strip():
        return "empty body"
    for pattern, why in _SCAFFOLD_PATTERNS:
        if pattern.search(body_md):
            return f"scaffolding leak: {why}"
    return None


def _is_probably_html(text: str) -> bool:
    return bool(re.search(r"<(?:p|div|table|h[1-6]|ul|ol|br|span)\b", text, re.I))


# ── Claims check — designed by AG, 2026-07-29 ────────────────────────────────────
# Origin: the weekly report told the Commander "60+ initiatives executed across the
# Weapons Free surge". Its sibling claim, "approximately 124 commits", was ACCURATE
# (git: 125) — but "initiative" maps to no artifact in any system here, so the headline
# number could not be checked, and he read the whole report as inflation.
# SO-REPORTING-2026 §2.4 already bans anti-theater; nothing enforced it.
#
# DELIBERATE DEVIATION from AG's proposal: AG offered both a CHECKABLE_ARTIFACTS
# allowlist and a THEATER_NOUNS denylist. We implement the DENYLIST ONLY, because AG's
# own adversarial section showed the allowlist punishes legitimate specificity — it
# rejects "I spun up 3 new test harnesses" purely because "harnesses" wasn't enumerated.
# A gate that blocks honest precision trains people to write vaguer, which is the
# opposite of the goal. The denylist catches the actual offenders and lets real nouns
# through.
#
# KNOWN HOLE, AG's own finding, documented rather than papered over: "We took 60
# actions to improve client trust" passes, because "actions" is a real countable noun.
# It is exactly as unfalsifiable as "initiatives". This check raises the cost of
# theater; it does not make theater impossible.
_THEATER_NOUNS = (
    "initiative", "initiatives", "effort", "efforts", "win", "wins",
    "improvement", "improvements", "enhancement", "enhancements",
    "optimization", "optimizations", "capability", "capabilities",
)
_NUM_THEATER = re.compile(
    r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|dozens?|scores?)\s*\+?\s+"
    r"(?:[a-z][a-z\-]*\s+){0,2}"
    r"(" + "|".join(_THEATER_NOUNS) + r")\b",
    re.IGNORECASE,
)


def check_claims(body_md: str) -> Optional[str]:
    """Reject a body that attaches a number to something no system can count.

    Returns a rejection reason, or None if the body is clean.
    """
    m = _NUM_THEATER.search(body_md or "")
    if not m:
        return None
    return (
        f"unfalsifiable count: {m.group(0).strip()!r}. No system here counts "
        f"'{m.group(2).lower()}', so this number cannot be checked and reads as "
        "inflation. Cite a countable artifact instead — commits, missions, files, "
        "drafts, closures, dollars — or drop the number and describe the work."
    )


# ─────────────────────────────────────────────────────────────────────────────────
# Markdown → HTML. Self-contained: no `markdown` package on this host, and a
# notification path must not carry an optional dependency.
# ─────────────────────────────────────────────────────────────────────────────────

def _inline(text: str) -> str:
    out = _html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"`([^`\n]+)`",
                 r'<code style="background:#f1f5f9;padding:1px 4px;border-radius:3px;">\1</code>', out)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                 r'<a href="\2" style="color:#2563eb;">\1</a>', out)
    return out


def render_markdown(md: str) -> str:
    """Minimal, predictable markdown→HTML: headings, bold/italic/code/links,
    bullet and numbered lists, pipe tables, paragraphs. Anything unrecognised
    degrades to a paragraph rather than leaking its source markers."""
    lines = md.replace("\r\n", "\n").split("\n")
    html_parts: list[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = min(len(m.group(1)), 4) + 1
            size = {2: "19px", 3: "16px", 4: "15px", 5: "14px"}.get(lvl, "14px")
            html_parts.append(
                f'<h{lvl} style="font-family:Georgia,serif;font-size:{size};margin:16px 0 6px;">'
                f"{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^(?:---+|\*\*\*+|___+)$", line):
            html_parts.append('<hr style="border:0;border-top:1px solid #cbd5e1;margin:14px 0;">')
            i += 1
            continue

        # Pipe table
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            def cells(r: str) -> list[str]:
                return [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            th = "".join(
                f'<th style="padding:7px 9px;text-align:left;border:1px solid #e2e8f0;">{_inline(c)}</th>'
                for c in head)
            tb = ""
            for n, r in enumerate(rows):
                bg = "#ffffff" if n % 2 == 0 else "#f8fafc"
                tb += f'<tr style="background:{bg};">' + "".join(
                    f'<td style="padding:7px 9px;border:1px solid #e2e8f0;">{_inline(c)}</td>'
                    for c in r) + "</tr>"
            html_parts.append(
                '<table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px;">'
                f'<tr style="background:#07076b;color:#fff;">{th}</tr>{tb}</table>')
            continue

        # Lists
        if re.match(r"^[-*+]\s+\S", line) or re.match(r"^\d+[.)]\s+\S", line):
            ordered = bool(re.match(r"^\d+[.)]\s", line))
            items = []
            while i < len(lines):
                s = lines[i].strip()
                m2 = re.match(r"^(?:[-*+]|\d+[.)])\s+(.*)$", s)
                if not m2:
                    break
                items.append(f'<li style="margin:3px 0;">{_inline(m2.group(1))}</li>')
                i += 1
            tag = "ol" if ordered else "ul"
            html_parts.append(f'<{tag} style="margin:8px 0 8px 20px;padding:0;">' + "".join(items) + f"</{tag}>")
            continue

        # Paragraph
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|\||---+$)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            html_parts.append(
                '<p style="font-family:Georgia,serif;font-size:14px;line-height:1.6;margin:8px 0;">'
                + _inline(" ".join(buf)) + "</p>")

    return "\n".join(html_parts)


# ─────────────────────────────────────────────────────────────────────────────────
# Dedup
# ─────────────────────────────────────────────────────────────────────────────────

def _fingerprint(title: str, body_md: str, dedup_key: Optional[str]) -> str:
    basis = dedup_key if dedup_key else f"{title.strip()}\x00{re.sub(r'\\s+', ' ', body_md).strip()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _recent_fingerprints(hours: int = DEDUP_WINDOW_HOURS) -> dict[str, str]:
    cutoff = _now() - timedelta(hours=hours)
    seen: dict[str, str] = {}
    for row in _read_rows(AUDIT_PATH):
        if row.get("status") not in ("sent", "queued"):
            continue
        fp = row.get("fingerprint")
        if not fp:
            continue
        try:
            ts = datetime.fromisoformat(row["ts"])
        except (KeyError, ValueError):
            continue
        if ts >= cutoff:
            seen[fp] = row["ts"]
    return seen


# ─────────────────────────────────────────────────────────────────────────────────
# Delivery
# ─────────────────────────────────────────────────────────────────────────────────

def _deliver(subject: str, body_html: str, *, urgency: str = "NOW",
             item_id: Optional[str] = None) -> dict:
    """Hand the already-vetted payload to every configured transport.

    Email is authoritative and must succeed. Slack is additive: a Slack outage must
    never cost the Commander a payment deadline, so its failure is recorded and
    swallowed rather than raised. Transports are called ONLY from here — that
    single-chokepoint property is what tests/test_no_direct_sends.py enforces.
    """
    from d2m_email_builder import build_email_html      # scripts/
    from wing_email_sender import send_wing_email       # scripts/

    full = build_email_html(body_html)
    out: dict[str, Any] = {"message_id": send_wing_email(COMMANDER, subject, full)}

    try:
        from core.comms import slack_transport as _slack
        if _slack.is_configured():
            r = _slack.post(subject, body_html, urgency=urgency, item_id=item_id)
            out["slack_channel"] = r.get("channel")
            out["slack_ts"] = r.get("ts")
    except Exception as exc:                      # never let Slack break delivery
        out["slack_error"] = f"{type(exc).__name__}: {exc}"
    return out


# ─────────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────────

def notify(kind: str,
           title: str,
           body_md: str,
           *,
           urgency: str = "WINDOW",
           dedup_key: Optional[str] = None,
           source: Optional[str] = None,
           reason: Optional[str] = None) -> dict:
    """The only way anything reaches the Commander.

    kind      — coarse category ('fpd', 'brief', 'ops', 'client'), used for grouping.
    title     — the subject line / section heading.
    body_md   — markdown. Rendered once, here, so nothing ever ships raw again.
    urgency   — "WINDOW" (queue for 06:30/18:30) or "NOW" (breakthrough).
    dedup_key — stable identity for the thing being reported. Prefer this over
                content hashing when the same item may be reworded.
    source    — caller identity for the audit trail. Defaults to the calling module.
    reason    — REQUIRED when urgency="NOW". Recorded verbatim in the audit log.
    """
    urgency = (urgency or "WINDOW").upper()
    if urgency not in ("WINDOW", "NOW"):
        raise NotifyError(f"urgency must be WINDOW or NOW, got {urgency!r}")
    if urgency == "NOW" and not (reason or "").strip():
        raise NotifyError(
            "urgency='NOW' requires a reason. The breakthrough path is reserved for "
            "money-at-risk and client-critical dates, and every use is auditable."
        )

    if source is None:
        try:
            source = os.path.basename(sys._getframe(1).f_code.co_filename)
        except Exception:
            source = "unknown"

    base = {"kind": kind, "title": title, "urgency": urgency,
            "source": source, "reason": reason}

    # 1. Content fitness — scaffolding leaks, then unfalsifiable counts.
    bad = check_body(body_md) or check_claims(body_md)
    if bad:
        return _audit(status="rejected", detail=bad, **base)

    # 2. Dedup — the fix for the 13-minute duplicates.
    fp = _fingerprint(title, body_md, dedup_key)
    prior = _recent_fingerprints().get(fp)
    if prior:
        return _audit(status="suppressed", fingerprint=fp,
                      detail=f"identical content already delivered at {prior} "
                             f"(within {DEDUP_WINDOW_HOURS}h window)", **base)

    body_html = body_md if _is_probably_html(body_md) else render_markdown(body_md)

    # 3. Route.
    if urgency == "WINDOW":
        _append(QUEUE_PATH, {"ts": _now().isoformat(), "fingerprint": fp,
                             "body_html": body_html, **base})
        return _audit(status="queued", fingerprint=fp,
                      detail="held for the next 06:30/18:30 consolidated window", **base)

    try:
        res = _deliver(title, body_html, urgency=urgency, item_id=dedup_key)
    except Exception as exc:  # delivery failure must not crash the caller
        return _audit(status="failed", fingerprint=fp,
                      detail=f"{type(exc).__name__}: {exc}", **base)
    return _audit(status="sent", fingerprint=fp, **base, **res)


def drain_queue(clear: bool = True) -> list[dict]:
    """Return everything waiting for the next window, oldest first.

    Called by the 06:30 and 18:30 consolidated engines — they are the only things
    that flush. `clear=False` allows a dry run without consuming the queue.
    """
    rows = _read_rows(QUEUE_PATH)
    if clear and rows:
        QUEUE_PATH.write_text("", encoding="utf-8")
    return rows


def queue_depth() -> int:
    return len(_read_rows(QUEUE_PATH))


def audit_tail(n: int = 20) -> list[dict]:
    """Answers 'why did I get this / why didn't I' — every send AND suppression."""
    return _read_rows(AUDIT_PATH)[-n:]
