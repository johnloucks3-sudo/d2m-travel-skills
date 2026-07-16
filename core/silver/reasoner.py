"""
core/silver/reasoner.py — Silver's reasoning dispatch: the Commander-DNA clone,
implemented (2026-07-16).

The charter says Silver is "cloned from the Commander's leadership DNA" — but
until this module, no code ever loaded Personas/commander_leadership_dna.md
into anything. build_context_pack() assembles Silver's mind for every run:
the DNA file (verbatim), his charter, the last 14 days of Commander decisions,
the master-plan head, and the open mission board. dispatch() runs a genuine
reasoning pass over that pack — intent-level judgment, not keyword triggers.

Used by core/silver/insight_exchange.py (Silver as collector/predictor).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DNA = ROOT / "Personas/commander_leadership_dna.md"
CHARTER = ROOT / "Personas/silver_sterling_command_chief.md"
DECISIONS = ROOT / "hale_decisions.md"
MASTER_PLAN = ROOT / "THUNDERBIRD_MASTER_PLAN.md"
MISSION_BOARD = ROOT / "OpsCenter/mission_board.json"

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def _recent_decisions(days: int = 14, max_bytes: int = 40_000) -> str:
    """Tail of hale_decisions.md filtered to the last `days` of dated lines.
    The file is ~5MB; only the bounded tail is scanned."""
    if not DECISIONS.exists():
        return "(hale_decisions.md missing)"
    tail = DECISIONS.read_text(errors="replace")[-200_000:]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    lines = [l for l in tail.splitlines()
             if (m := re.search(r"\b(20\d{2}-\d{2}-\d{2})", l)) is None or m.group(1) >= cutoff]
    out = "\n".join(lines)
    return out[-max_bytes:]


def _open_missions(max_items: int = 40) -> str:
    try:
        board = json.loads(MISSION_BOARD.read_text())
    except Exception as e:
        return f"(mission board unreadable: {e})"
    rows = [f"- {m.get('id')} [{m.get('priority')}] {m.get('status')}: {m.get('title')}"
            for m in board.get("missions", [])
            if m.get("status") in ("active", "in_progress", "open", "pending", "assigned")]
    return "\n".join(rows[:max_items]) or "(no open missions)"


def build_context_pack(days: int = 14) -> str:
    """Silver's mind, assembled fresh each run. DNA + charter load verbatim and
    are REQUIRED — a pack without them is not Silver, so missing files raise."""
    if not DNA.exists():
        raise FileNotFoundError(f"Commander DNA file missing: {DNA}")
    if not CHARTER.exists():
        raise FileNotFoundError(f"Silver charter missing: {CHARTER}")
    sections = [
        ("COMMANDER LEADERSHIP DNA (you are cloned from this — reason AS he would)",
         DNA.read_text()),
        ("YOUR CHARTER — CMSgt Steve 'Silver' Sterling, Command Chief / Overseer",
         CHARTER.read_text()),
        (f"COMMANDER DECISIONS — last {days} days (his actual choices and corrections)",
         _recent_decisions(days)),
        ("MASTER PLAN (head)", MASTER_PLAN.read_text(errors="replace")[:20_000]
         if MASTER_PLAN.exists() else "(missing)"),
        ("OPEN MISSION BOARD", _open_missions()),
    ]
    return "\n\n".join(f"═══ {title} ═══\n{body}" for title, body in sections)


def dispatch(task: str, out_path: str, *, model: str = DEFAULT_MODEL,
             days: int = 14, wait: bool = False) -> dict:
    """Run a headless reasoning pass as Silver via the ONLY approved spawn path
    (core/ai_infra/thunderbird_headless_spawn.py — A7 gate, SO 24 APR 2026)."""
    from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

    prompt = (
        "You are CMSgt Steve 'Silver' Sterling. Reason from the context pack below — "
        "as the Commander's DNA clone, not as a keyword matcher.\n\n"
        + build_context_pack(days)
        + f"\n\n═══ TASK ═══\n{task}\n\nWRITE your complete output to {out_path}"
    )
    return spawn_headless_claude(
        prompt, out_path, model=model, task_name="silver_reasoner",
        background=not wait, timeout=600,
    )


if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        pack = build_context_pack()
        dna_text = DNA.read_text()
        probe = dna_text.strip().splitlines()[-1][:60]  # last DNA line must survive assembly
        assert probe in pack, "DNA content NOT present in assembled pack"
        print(f"pack: {len(pack):,} bytes | DNA verbatim: YES | charter: "
              f"{'YES' if 'Command Chief' in pack else 'NO'} | "
              f"decisions section: {'YES' if 'COMMANDER DECISIONS' in pack else 'NO'}")
        sys.exit(0)
    print(__doc__)
