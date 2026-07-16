#!/usr/bin/env python3
"""
insight_generate.py — per-seat Insight Exchange generators (2026-07-16).

Each seat runs a REAL reasoning pass over the intent pack from its own unique
vantage — genuine anticipation of the Commander's next ask, not keyword
triggers — then its cards go through Silver's citation gate before posting.

  CC — headless Claude over the client/judgment vantage (dossiers, drafts,
       lifecycle touchpoints) — spawn pattern per HEADLESS_CLAUDE_SPAWN_GUIDE.
  OC — `opencode run` (DeepSeek v4) over the ops vantage (CI state, backlogs,
       mechanical queue).
  AG — interface reserved; not generated until AG's relay lane is real
       (one test message as of 2026-07-14 — no theater).

Usage: python3 scripts/insight_generate.py CC|OC [--ingest-only path.json]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from core.silver.insight_exchange import post_card  # noqa: E402
from core.silver.reasoner import build_context_pack, DEFAULT_MODEL  # noqa: E402

OC_MODEL = "opencode/deepseek-v4-flash-free"

CARD_FORMAT = """\
Output STRICT JSON: a list of 1-5 card objects, each:
{"kind": "<anticipated_ask|wing_priority|capability_offer|assist_offer|finding_share|kudos>",
 "insight": "...", "reasoning": "intent-level why — what the Commander is driving at",
 "signal": "existing file path or MISSION-id supporting it",
 "confidence": "CONFIRMED|INFERRED|UNKNOWN", "suggested_owner": "CC|OC|AG"}
Only cite signals that actually exist in the context. Include at least one
assist_offer or finding_share if you genuinely see one — the seats work
together like colleagues: share, encourage, assist. No prose outside JSON.
"""

VANTAGE = {
    "CC": ("your vantage: client work, judgment calls, drafts in flight, "
           "lifecycle touchpoints, what the Commander corrected recently. "
           "From that vantage: what will he ask for next? What should the "
           "Wing be doing before he asks? Where can you assist OC or AG?"),
    "OC": ("your vantage: ops mechanics, CI state, data backlogs, scheduled "
           "sweeps, systemd health. From that vantage: what will the Commander "
           "ask for next? What upstream ops problem will become his problem "
           "this week if nobody moves? Where can you assist CC or AG?"),
}


def generate_cc(out_path: str) -> int:
    """Headless CC pass via the ONLY approved spawn path (A7 gate)."""
    from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
    prompt = (f"You are Hale-CC of the Thunderbird Wing — {VANTAGE['CC']}\n\n"
              + build_context_pack() + "\n\n" + CARD_FORMAT
              + f"\nWRITE the JSON to {out_path}")
    result = spawn_headless_claude(prompt, out_path, model=DEFAULT_MODEL,
                                   task_name="insight_cc", timeout=600)
    return 0 if result.get("status") in ("SUCCESS", "COMPLETE", "OK") or Path(out_path).exists() else 1


def generate_oc(out_path: str) -> int:
    prompt = (f"You are Hale-OC (JET) of the Thunderbird Wing — {VANTAGE['OC']}\n\n"
              + build_context_pack() + "\n\n" + CARD_FORMAT
              + f"\nWrite the JSON to the file {out_path} using your file tools.")
    return subprocess.run(
        ["opencode", "run", "--model", OC_MODEL, prompt],
        cwd=str(ROOT), timeout=600,
        stdout=open(ROOT / "logs/insight_generate.log", "a"),
        stderr=subprocess.STDOUT,
    ).returncode


def ingest_as(seat: str, path: str) -> None:
    """Post a generator's output under its own seat via the citation gate."""
    import re
    raw = Path(path).read_text()
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0) if m else raw)
    posted = rejected = 0
    for it in items:
        try:
            post_card(seat, it.get("kind", "anticipated_ask"), it.get("insight", ""),
                      reasoning=it.get("reasoning", ""), signal=it.get("signal", ""),
                      confidence=it.get("confidence", "INFERRED"),
                      suggested_owner=it.get("suggested_owner", ""))
            posted += 1
        except (ValueError, KeyError) as e:
            rejected += 1
            print(f"  rejected: {str(e)[:100]}")
    print(f"{seat}: posted {posted}, rejected {rejected}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("CC", "OC"):
        sys.exit(__doc__)
    seat = sys.argv[1]
    if "--ingest-only" in sys.argv:
        ingest_as(seat, sys.argv[sys.argv.index("--ingest-only") + 1])
        sys.exit(0)
    out = str(ROOT / f"output/insight_cards_{seat.lower()}.json")
    Path(out).unlink(missing_ok=True)
    rc = generate_cc(out) if seat == "CC" else generate_oc(out)
    if not Path(out).exists():
        sys.exit(f"{seat} generator wrote nothing (rc={rc}) — see logs/insight_generate.log")
    ingest_as(seat, out)
