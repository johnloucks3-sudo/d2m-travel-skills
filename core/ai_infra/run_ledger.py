#!/usr/bin/env python3
"""
RUN LEDGER — the fuel gauge + the bomb-bay-door indicator
=========================================================
Dreams2Memories Travel · built 2026-06-21 (Harlan + ELON + Sterling STAFF COMMENTS)

Every fleet/hunt run closes on a hard ledger so "we ran 20 agents" can NEVER
count as success on its own. Folds three staff findings into one instrument:

  • Harlan — cost meter + per-run token BUDGET with a hard kill. A run declares a
    token ceiling; over it = OVER_BUDGET, and `remaining()` lets a live loop stop
    BEFORE it retries into the rate limiter.
  • ELON — the FAILURE flag. adopted=0 AND killed=0 AND cost over the floor =
    FAILURE, not "activity." The kill path must fire or the run is a failure.
  • Sterling — the ≥75% completion gate. returned/total < 0.75 = INCOMPLETE; the
    run adopts/recommends NOTHING (partial fleet output launders incompleteness
    as coverage).

Cost is an ESTIMATE from tokens at a configurable metered rate — NOT a live read
of Anthropic's $100 metered pool (that's the ccusage/OTEL follow-on, WS-02). It
is honest about that. The point today is: no run is unpriced, and no run with a
dead drain is logged as a win.

Ledger: state/run_ledger.jsonl (append-only).
CLI:  log --label X --tokens N --agents-total T --agents-returned R [--adopted A --killed K --budget B]
      remaining --spent N --ceiling C
      digest [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEDGER = Path("/home/john/Thunderbird/state/run_ledger.jsonl")

# Tunable economics (rough metered estimate; refine when WS-02 ccusage/OTEL lands)
RATE_PER_MTOK = 6.0        # blended $/M tokens, metered-pool estimate
FAILURE_COST_FLOOR = 0.50  # $ above which a zero-adopt, zero-kill run is a FAILURE
COMPLETION_MIN = 0.75      # Sterling's gate
MONTHLY_POOL = 100.0       # MISSION-296 metered ceiling we must not blow


def estimate_cost(tokens: int) -> float:
    return round((tokens / 1_000_000) * RATE_PER_MTOK, 4)


def remaining(spent_tokens: int, ceiling_tokens: int) -> int:
    """Live helper: tokens left under the per-run ceiling (0 = STOP, do not retry)."""
    return max(0, ceiling_tokens - spent_tokens)


def verdict(tokens: int, agents_total: int, agents_returned: int,
            adopted: int = 0, killed: int = 0, budget_tokens: int | None = None) -> dict:
    cost = estimate_cost(tokens)
    completion = (agents_returned / agents_total) if agents_total else 1.0
    flags = []
    status = "COMPLETE"

    if budget_tokens and tokens > budget_tokens:
        status = "OVER_BUDGET"; flags.append(f"tokens {tokens} > budget {budget_tokens}")
    if completion < COMPLETION_MIN:
        status = "INCOMPLETE"
        flags.append(f"completion {completion:.0%} < {COMPLETION_MIN:.0%} — adopts/recommends NOTHING")
    if adopted == 0 and killed == 0 and cost > FAILURE_COST_FLOOR:
        status = "FAILURE"
        flags.append(f"zero adopted + zero killed at ${cost} — the drain didn't fire")

    return {
        "tokens": tokens, "cost_est_usd": cost, "completion": round(completion, 3),
        "agents_total": agents_total, "agents_returned": agents_returned,
        "adopted": adopted, "killed": killed, "budget_tokens": budget_tokens,
        "status": status, "flags": flags,
    }


def log_run(label: str, tokens: int, agents_total: int, agents_returned: int,
            adopted: int = 0, killed: int = 0, budget_tokens: int | None = None) -> dict:
    v = verdict(tokens, agents_total, agents_returned, adopted, killed, budget_tokens)
    v["label"] = label
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(v) + "\n")
    return v


def _all() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def digest() -> dict:
    runs = _all()
    spend = round(sum(r.get("cost_est_usd", 0) for r in runs), 2)
    return {
        "runs": len(runs),
        "est_spend_usd": spend,
        "pool_pct": round(100 * spend / MONTHLY_POOL, 1),
        "failures": sum(1 for r in runs if r.get("status") == "FAILURE"),
        "incomplete": sum(1 for r in runs if r.get("status") == "INCOMPLETE"),
        "over_budget": sum(1 for r in runs if r.get("status") == "OVER_BUDGET"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("log")
    l.add_argument("--label", required=True)
    l.add_argument("--tokens", type=int, required=True)
    l.add_argument("--agents-total", type=int, required=True)
    l.add_argument("--agents-returned", type=int, required=True)
    l.add_argument("--adopted", type=int, default=0)
    l.add_argument("--killed", type=int, default=0)
    l.add_argument("--budget", type=int, default=None)
    r = sub.add_parser("remaining"); r.add_argument("--spent", type=int, required=True); r.add_argument("--ceiling", type=int, required=True)
    d = sub.add_parser("digest"); d.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.cmd == "log":
        v = log_run(a.label, a.tokens, a.agents_total, a.agents_returned, a.adopted, a.killed, a.budget)
        print(f"{v['status']}: {a.label} — {v['agents_returned']}/{v['agents_total']} agents, "
              f"{v['tokens']} tok ~${v['cost_est_usd']}, adopted {v['adopted']} killed {v['killed']}")
        for f in v["flags"]:
            print(f"  ⚠ {f}")
    elif a.cmd == "remaining":
        print(remaining(a.spent, a.ceiling))
    elif a.cmd == "digest":
        print(json.dumps(digest(), indent=2) if a.json else digest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
