"""
tests/test_no_direct_sends.py — the guard that stops the 44 senders from regrowing.

C2 RECALIBRATION task 8, Commander directive 2026-07-29.

WHY
---
On 2026-07-29 an audit found 44 files calling the Gmail send API directly and 140
capable of sending Telegram, while exactly 2 used the canonical sender. With no
chokepoint there was nowhere to implement "stop sending me dupes" — the same report
went out at 11:34 and 11:48 because two different entry points each thought they
owned it.

core/comms/commander_channel.py::notify() is now the only path to the Commander.
This test is what keeps it that way. Without it, the next convenient
`service.users().messages().send(...)` silently reopens the hole.

The allowlist is deliberately tiny and should stay that way. Adding a file here means
asserting it is a TRANSPORT — the thing the gate calls — not a caller.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The ONLY files permitted to touch a send transport directly.
ALLOWLIST = {
    "scripts/wing_email_sender.py",      # canonical Gmail transport
    "core/comms/slack_transport.py",     # canonical Slack transport (Phase 3)
    "tests/test_no_direct_sends.py",     # this file — it names the patterns
}

# Trees that are not ours to police, or are already retired.
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "archive", "mcps", "Antigravity-x64", ".smart-env",
    ".claude", "worktrees",
}

GMAIL_SEND = re.compile(r"messages\(\)\s*\.\s*send\s*\(")
TELEGRAM_SEND = re.compile(r"api\.telegram\.org/bot[^/\s\"']*/sendMessage")


def _candidate_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def _violations(pattern: re.Pattern) -> list[str]:
    bad = []
    for p in _candidate_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if pattern.search(line):
                bad.append(f"{rel}:{n}: {line.strip()[:100]}")
    return bad


BASELINE_PATH = Path(__file__).parent / "no_direct_sends_baseline.json"


def _load_baseline() -> dict[str, list[str]]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _file_of(v: str) -> str:
    return v.split(":", 1)[0]


@pytest.mark.parametrize("key,name,pattern", [
    ("gmail", "Gmail messages().send()", GMAIL_SEND),
    ("telegram", "Telegram sendMessage", TELEGRAM_SEND),
])
def test_no_new_direct_sends(key: str, name: str, pattern: re.Pattern) -> None:
    """RATCHET: no NEW file may bypass the gate, and the count may only shrink.

    A test that is red forever gets ignored, and an ignored guard is no guard. So
    this pins the known-bad set as a baseline and fails on regression instead:

      * a file not in the baseline gaining a direct send  -> FAIL (a new hole)
      * the total count rising                            -> FAIL
      * the count falling                                 -> PASS (and please
        regenerate the baseline so the ratchet tightens)

    Regenerate after migrating callers:
        python3 tests/test_no_direct_sends.py --update-baseline
    """
    current = _violations(pattern)
    baseline = _load_baseline().get(key, [])
    baseline_files = {_file_of(v) for v in baseline}

    new_files = sorted({_file_of(v) for v in current} - baseline_files)
    assert not new_files, (
        f"\n{len(new_files)} NEW file(s) call {name} directly, bypassing "
        "core/comms/commander_channel.py::notify().\n"
        "Route the message through notify() so it is deduped, rendered, batched to the\n"
        "06:30/18:30 windows, and audited. If this is genuinely a TRANSPORT rather than\n"
        "a caller, add it to ALLOWLIST and say why.\n\n  " + "\n  ".join(new_files)
    )

    assert len(current) <= len(baseline), (
        f"\n{name} direct-call count rose from {len(baseline)} to {len(current)}. "
        "The gate is being routed around."
    )


def test_baseline_is_shrinking_not_growing() -> None:
    """The baseline exists to be driven to zero, not to legitimise the status quo."""
    baseline = _load_baseline()
    assert baseline, (
        "No baseline recorded. Run: python3 tests/test_no_direct_sends.py --update-baseline"
    )
    # Measured on 2026-07-29 at the moment the gate landed: 164 Gmail call sites
    # across 44 files, 382 Telegram call sites across ~140 files. This is a high-water
    # mark, not an allowance. Lower it every time callers are migrated; never raise it.
    CEILING = 546
    total = sum(len(v) for v in baseline.values())
    assert total <= CEILING, (
        f"Baseline holds {total} known bypasses, above the {CEILING} high-water mark set "
        "2026-07-29. That ceiling is a migration backlog, not a budget — it must come "
        "down, never up."
    )


def test_allowlist_stays_small() -> None:
    """A growing allowlist means the gate is being routed around rather than used."""
    assert len(ALLOWLIST) <= 4, (
        f"ALLOWLIST has grown to {len(ALLOWLIST)} entries. Each one is a hole in the "
        "single-gate guarantee. Justify it or route the caller through notify()."
    )


def test_gate_module_exists() -> None:
    """The guard is meaningless if the gate it protects has been removed."""
    gate = ROOT / "core" / "comms" / "commander_channel.py"
    assert gate.exists(), "core/comms/commander_channel.py is missing — the gate is gone"
    src = gate.read_text(encoding="utf-8")
    assert "def notify(" in src, "commander_channel.py no longer exposes notify()"


if __name__ == "__main__":
    if "--update-baseline" in sys.argv:
        data = {"gmail": _violations(GMAIL_SEND), "telegram": _violations(TELEGRAM_SEND)}
        BASELINE_PATH.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        print(f"baseline written: gmail={len(data['gmail'])} telegram={len(data['telegram'])}")
    else:
        print("usage: python3 tests/test_no_direct_sends.py --update-baseline")
