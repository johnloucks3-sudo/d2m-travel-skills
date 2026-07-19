"""
core/staffing/directive_ledger.py — capture every Commander message during a
discussion so no MANDATORY directive is missed when framing acceptance criteria.

Root-cause fix (Commander directive 2026-07-18/19): the "CROSS HALE COORDINATION
IS MANDATORY" clue arrived as message 4 of a multi-message discussion. It was
never input into the Staff Summary Sheet acceptance criteria, so CHIEF SILVER's
gate could not enforce it and a failed sheet closed anyway. The failure was
structural: mandatory criteria depended on the agent *remembering* each message
instead of the system *capturing* them.

This ledger captures every message sent during a build discussion, auto-flags
the ones that assert a mandate (the word "mandatory"/"must", or a known gate
pattern), and exposes the active mandates so `open_sss()` can BIND them to every
new sheet and `close_sss()` can refuse to close a sheet with an unmet mandate.
Missing a mandatory clue is now a hard block, not a silent omission.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
LEDGER = ROOT / "OpsCenter/mandatory_directives.jsonl"

# Known mandate → the structural gate key the SSS model enforces. A message
# matching any pattern binds that gate to every sheet opened afterwards.
MANDATE_GATES: dict[str, list[str]] = {
    "cross_hale": [r"cross[\s\-]?hale.{0,40}mandat", r"mandat.{0,40}cross[\s\-]?hale"],
    "silver":     [r"silver.{0,30}\b(front|back)\b", r"\b(front|back)\b.{0,30}silver"],
}

# A message is a mandate if it names a known gate OR asserts obligation language.
_OBLIGATION = re.compile(r"\bmandat|\bmust\b|\brequired\b|\bnon-?negotiable\b", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_gates(text: str) -> list[str]:
    hits = []
    for gate, patterns in MANDATE_GATES.items():
        if any(re.search(p, text, re.I) for p in patterns):
            hits.append(gate)
    return hits


def capture(text: str, *, source: str, ts: Optional[str] = None) -> dict:
    """Record one Commander message from the discussion. Auto-flags it as a
    mandate when it names a known gate or uses obligation language, and tags the
    structural gate(s) it binds. Idempotent per (source, text) — re-capturing the
    same message does not duplicate it."""
    text = (text or "").strip()
    gates = _detect_gates(text)
    mandatory = bool(gates) or bool(_OBLIGATION.search(text))
    entry = {
        "text": text[:1000],
        "source": source,
        "gates": gates,
        "mandatory": mandatory,
        "ts": ts or _now(),
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    existing = _read()
    if any(e.get("source") == source and e.get("text") == entry["text"] for e in existing):
        return entry  # already captured
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _read() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def all_messages() -> list[dict]:
    """Every captured message this discussion — the full record, mandate or not."""
    return _read()


def active_mandates() -> list[dict]:
    """The captured messages that assert a mandate."""
    return [e for e in _read() if e.get("mandatory")]


def active_gate_keys() -> list[str]:
    """The distinct structural gate keys currently mandated (e.g. cross_hale,
    silver). Bound onto every sheet at open so the close gate enforces them —
    plus a synthetic `unmapped:<text>` for a mandate with no known gate, so a
    NEW mandatory directive blocks close instead of being silently ignored."""
    keys: list[str] = []
    for e in active_mandates():
        if e.get("gates"):
            keys.extend(e["gates"])
        else:
            keys.append("unmapped:" + e["text"][:60])
    return sorted(set(keys))


# Human-readable gate → what it obliges, for the plan-mode briefing.
_GATE_MEANING = {
    "cross_hale": "MUST DO — genuine cross-Hale coordination (a different engine "
                  "CC/OC/AG must really do/certify the work; a same-engine backstop "
                  "of a failed seat does NOT count and BLOCKS the sheet)",
    "silver":     "MUST HAVE — CHIEF SILVER front frame (checkable 'done' + named "
                  "ground truth) and back gate on the artifact before any close",
}


def must_haves_must_dos() -> str:
    """Render the captured MANDATORY directives as a MUST-HAVE / MUST-DO briefing.

    Commander directive 2026-07-18/19: surface this before executing whenever the
    Commander puts me in PLAN mode, so no mandate is silently dropped from a plan.
    Driven entirely by the captured ledger — not by memory."""
    mandates = active_mandates()
    lines = ["## 🔒 MUST-HAVES / MUST-DOS (captured mandatory directives)"]
    if not mandates:
        lines.append("- (none captured this discussion)")
        return "\n".join(lines)
    seen = set()
    for e in mandates:
        for g in (e.get("gates") or ["unmapped"]):
            meaning = _GATE_MEANING.get(g)
            key = meaning or e["text"]
            if key in seen:
                continue
            seen.add(key)
            if meaning:
                lines.append(f"- {meaning}")
            else:
                lines.append(f"- MUST — {e['text'][:160]}  _(source: {e.get('source')})_")
    lines.append("")
    lines.append("_Every open Staff Summary Sheet binds these; the close gate "
                 "enforces them (`_unmet_mandates`). Confirm the plan satisfies each._")
    return "\n".join(lines)
