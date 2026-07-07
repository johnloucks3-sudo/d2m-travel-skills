#!/usr/bin/env python3
"""
Staff Proposal Cadence — 1 proposal/persona/week, GATED on integration health.

Design correction (2026-07-07): the original recommendation ("expand to 80+ agents/batch,
gate only at deploy") was wrong. Verification of the 2026-07-06 batch showed the real
bottleneck was never proposal-generation volume — it was that proposals get committed as
code and then never wired into a live path, and never closed. Cranking generation volume
into a queue that isn't closing just grows a bigger backlog (81 open, 0 archived, 0 closed
under the new protocol as of this build).

So this cadence is INTEGRATION-GATED:
  - It reads the real integration rate from hale_state.json["elon_proposals"]
    (written by elon_proposal_integration_check.py — never self-reported).
  - If passing_both_bars / claimed_total < THROTTLE_THRESHOLD, it does NOT generate new
    proposals. Instead it emits an INTEGRATION_DEBT ticket naming the unwired backlog,
    because closing existing debt outranks generating more of it.
  - Only when the integration rate clears the threshold does it open the cadence slots,
    one proposal per persona for the week, written straight into the existing
    elon_proposals/ queue in the new CLOSURE_TARGET_DATE format so it's covered by the
    existing Sunday 18:00 MT closure review (ELON_PROPOSAL_CLOSURE_PROTOCOL.md) rather
    than a second parallel process.

Usage: python3 staff_proposal_cadence.py [--write]
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

REPO = Path("/home/john/Thunderbird")
STATE_FILE = REPO / "hale_state.json"
PROPOSALS_DIR = REPO / "OpsCenter" / "elon_proposals"
CADENCE_LOG = REPO / "OpsCenter" / "staff_cadence_log.json"

THROTTLE_THRESHOLD = 0.50  # integration rate must clear 50% before new proposals open

# Domain owners eligible for the standing cadence — one proposal slot each per week.
PERSONAS = ["ELON", "Whetstone", "Sterling", "Dembe", "Dani", "Harlan", "Reyes", "Luna", "Naia"]


def get_integration_state() -> dict:
    state = json.loads(STATE_FILE.read_text())
    ep = state.get("elon_proposals")
    if not ep:
        raise SystemExit("elon_proposals metrics block missing — run elon_proposal_integration_check.py --write first")
    return ep


def integration_rate(ep: dict) -> float:
    batch = ep["2026-07-06_batch_verified"]
    claimed = batch["claimed_total"]
    passing = batch["passing_both_bars_committed_and_wired"]
    return passing / claimed if claimed else 0.0


def unwired_backlog(ep: dict) -> list[str]:
    return [cap for cap, v in ep["per_capability"].items() if v["committed"] and not v["integrated"]]


def week_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def write_integration_debt_ticket(ep: dict, unwired: list[str]):
    target = (datetime.now(timezone.utc).astimezone() + timedelta(days=7)).strftime("%Y-%m-%d")
    path = PROPOSALS_DIR / f"PROPOSAL-{week_stamp()}-integration-debt.md"
    body = f"""# PROPOSAL: Close Integration Debt Before New Cadence Opens
**Author:** staff_proposal_cadence.py (gate, not ELON manual write)
**Date:** {week_stamp()}
**Decision:** QUEUE_FOR_COMMANDER
**CLOSURE_TARGET_DATE:** {target}

## Why this fired instead of new proposals
Integration rate is {integration_rate(ep):.0%} (threshold: {THROTTLE_THRESHOLD:.0%}).
Cadence is throttled — the backlog does not get to grow while this much of it sits
committed-but-unwired.

## Committed but NOT integrated ({len(unwired)} modules)
{chr(10).join(f"- {m}" for m in unwired)}

## Ask
Pick one of:
1. Assign an owner to wire N of these into a live path (import + call site, or a
   systemd timer) this week, OR
2. Explicitly mark any of these as WON'T-INTEGRATE (kill it, stop counting it as debt), OR
3. Override the throttle for this week (state reason; logged to hale_decisions.md).
"""
    path.write_text(body)
    return path


def write_cadence_proposals(week: str):
    target = (datetime.now(timezone.utc).astimezone() + timedelta(days=7)).strftime("%Y-%m-%d")
    written = []
    for persona in PERSONAS:
        path = PROPOSALS_DIR / f"PROPOSAL-{week}-cadence-{persona.lower()}.md"
        if path.exists():
            continue
        body = f"""# PROPOSAL: Weekly Cadence Slot — {persona}
**Author:** staff_proposal_cadence.py (standing cadence, 1/persona/week)
**Date:** {week}
**Decision:** QUEUE_FOR_COMMANDER
**CLOSURE_TARGET_DATE:** {target}

## Slot
{persona} owns this week's proposal slot. Domain expertise surfaces the opportunity;
this is a placeholder until {persona} (or Hale on their behalf) fills in a concrete,
named capability with a stated integration point (not just a script — where does it
get called from, on what trigger).

**This proposal auto-expires if not filled in by the CLOSURE_TARGET_DATE above** — an
empty slot is not debt, it just means that persona had nothing to propose this week.
"""
        path.write_text(body)
        written.append(path.name)
    return written


def main():
    write = "--write" in sys.argv
    ep = get_integration_state()
    rate = integration_rate(ep)
    unwired = unwired_backlog(ep)
    week = week_stamp()

    result = {
        "run_date": week,
        "integration_rate": round(rate, 3),
        "throttle_threshold": THROTTLE_THRESHOLD,
        "gate_decision": None,
        "detail": None,
    }

    if rate < THROTTLE_THRESHOLD:
        result["gate_decision"] = "THROTTLED — integration debt ticket issued, no new cadence slots opened"
        if write:
            ticket_path = write_integration_debt_ticket(ep, unwired)
            result["detail"] = {"ticket": str(ticket_path.relative_to(REPO)), "unwired_count": len(unwired)}
        else:
            result["detail"] = {"would_write_ticket_for": len(unwired), "unwired": unwired}
    else:
        result["gate_decision"] = "OPEN — cadence slots issued"
        if write:
            written = write_cadence_proposals(week)
            result["detail"] = {"proposals_written": written}
        else:
            result["detail"] = {"would_write_slots_for": PERSONAS}

    print(json.dumps(result, indent=2))

    if write:
        log = json.loads(CADENCE_LOG.read_text()) if CADENCE_LOG.exists() else {"runs": []}
        log["runs"].append(result)
        CADENCE_LOG.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
