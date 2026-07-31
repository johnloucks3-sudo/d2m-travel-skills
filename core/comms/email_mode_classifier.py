"""
core/comms/email_mode_classifier.py — Gmail as C2: TASKING / FYI / CC.

Commander directive (directive ledger, verbatim): "I want to use Gmail as a C2
tasking and FYI and CC capability" — three distinct modes:

    TASKING — do this. Creates real work (a mission).
    FYI     — know this. Filed, no work.
    CC      — you are informed. Logged, no work.

Measured failure this fixes: every inbound Commander email was treated
identically, so a genuine TASKING email (2026-07-30, "Add to Loucks dossier,
confirm flight arrangements...") produced no mission, no dossier entry, no
reply — dropped silently. The opposite failure (an FYI spawning a mission) is
the noise the Commander is separately furious about. Both directions matter;
this module is the one place the distinction gets made so it isn't made
differently by every caller.

Pure function, no I/O — classify_email_mode() takes strings, returns a mode
and a human-readable reason. Callers (core/comms/directive_executor.py) own
what happens next.
"""

from __future__ import annotations

import re
from typing import Iterable, Tuple

MODE_TASKING = "TASKING"
MODE_FYI = "FYI"
MODE_CC = "CC"

_DEFAULT_D2M_MARKERS = ("d2mconcierge", "d2mluxury")

# Subject prefixes that are noise around the Commander's own words, not part
# of them — stripped before any pattern match runs against the subject.
_SUBJECT_STRIP_RE = re.compile(r"^\s*(re|fwd?|aw)\s*:\s*", re.IGNORECASE)
_FORWARD_SUBJECT_RE = re.compile(r"^\s*fwd?\s*:", re.IGNORECASE)

# An explicit mode prefix is the Commander naming the mode himself — nothing
# outranks it. Matches "TASK:", "TASKING:", "FYI:", "CC:" (colon or dash).
_EXPLICIT_PREFIX_RE = re.compile(
    r"^\s*(task(?:ing)?|fyi|cc)\s*[:\-]\s*", re.IGNORECASE
)

# The line where a forward hands off to quoted/forwarded content — everything
# above this boundary is the Commander's own words (or nothing, for a bare
# forward with no instruction).
_FORWARD_BOUNDARY_RE = re.compile(
    r"(-{2,}\s*forwarded message\s*-{2,}"
    r"|-{2,}\s*original message\s*-{2,}"
    r"|^on .{0,80}\bwrote:\s*$"
    r"|^from:\s*.+$)",
    re.IGNORECASE | re.MULTILINE,
)

# Imperative phrasing — the Commander asking for an action, not reporting one.
# Deliberately broad: a missed TASKING (dropped order) costs more than an
# extra queue item, which is why doctrine also defaults ambiguity to TASKING
# below rather than trying to shrink this list to zero false positives.
_IMPERATIVE_RE = re.compile(
    r"\b(add|confirm|call|draft|check|book|cancel|update|send|verify|pull|"
    r"schedule|set\s?up|make sure|need you to|can you|could you|please|"
    r"get me|find out|look into|follow up|reach out|remind me|handle this)\b",
    re.IGNORECASE,
)


def _explicit_mode(text: str) -> str | None:
    m = _EXPLICIT_PREFIX_RE.match((text or "").strip())
    if not m:
        return None
    tok = m.group(1).lower()
    if tok in ("task", "tasking"):
        return MODE_TASKING
    if tok == "fyi":
        return MODE_FYI
    if tok == "cc":
        return MODE_CC
    return None


def _top_line(body: str) -> str:
    """The Commander's own words: whatever precedes a forward/reply boundary,
    capped to the first few non-empty lines (an instruction is rarely longer)."""
    body = body or ""
    m = _FORWARD_BOUNDARY_RE.search(body)
    head = body[: m.start()] if m else body
    lines = [ln.strip() for ln in head.splitlines() if ln.strip()]
    return " ".join(lines[:3])


def classify_email_mode(
    *,
    subject: str = "",
    body: str = "",
    to_addr: str = "",
    cc_addr: str = "",
    d2m_markers: Iterable[str] = _DEFAULT_D2M_MARKERS,
) -> Tuple[str, str]:
    """Classify one inbound Commander email into TASKING / FYI / CC.

    Returns (mode, reason). Precedence, most to least specific:

      1. Explicit "TASK:"/"FYI:"/"CC:" prefix (subject or body) — definitive,
         the Commander named the mode himself.
      2. A Fwd:/Fw: whose top line (before the forwarded content) carries an
         instruction — TASKING. This is exactly the Wave Pointe case that got
         dropped: a forward with a one-line order on top read as pure FYI.
      3. Imperative phrasing near the top of the message — TASKING.
      4. d2m address present only in Cc (never in To), no instruction found —
         CC: he is informed, not ordering.
      5. Genuinely ambiguous — TASKING. A dropped order costs more than an
         extra queue item he can close in one tap.
    """
    subject = subject or ""
    body = body or ""
    clean_subject = _SUBJECT_STRIP_RE.sub("", subject.strip())

    explicit = _explicit_mode(clean_subject) or _explicit_mode(body)
    if explicit:
        return explicit, f"explicit '{explicit}' prefix"

    is_forward = bool(_FORWARD_SUBJECT_RE.match(subject.strip())) or bool(
        _FORWARD_BOUNDARY_RE.search(body)
    )
    top = _top_line(body)

    if is_forward and _IMPERATIVE_RE.search(top):
        return MODE_TASKING, "forwarded message with an instruction on the top line"

    if _IMPERATIVE_RE.search(top or body[:200]):
        return MODE_TASKING, "imperative phrasing detected"

    to_l, cc_l = (to_addr or "").lower(), (cc_addr or "").lower()
    d2m_in_to = any(mk in to_l for mk in d2m_markers)
    d2m_in_cc = any(mk in cc_l for mk in d2m_markers)
    if d2m_in_cc and not d2m_in_to:
        return MODE_CC, "d2m address present only in Cc, no instruction found"

    return MODE_TASKING, "ambiguous — defaulting to TASKING per doctrine"
