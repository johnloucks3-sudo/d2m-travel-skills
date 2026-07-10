#!/usr/bin/env python3
"""
AI Model Cost Attribution — spend by function, model, and time period
=======================================================================
Dreams2Memories Travel · Thunderbird Wing · Phase 4 roadmap (cost optimization)

Reads the existing per-provider usage logs in core/ai_infra/data/*.jsonl,
normalizes them onto a common schema (ts, provider, model, function,
input_tokens, output_tokens, cost_usd, success), and aggregates spend by
model / function / time period for a monthly ROI report.

Function categories are attributed by SOURCE FILE, not guessed from content —
each usage log already corresponds to exactly one function in the wing today
(claude_narrative_usage.jsonl -> narrative_generation, etc). Add a new entry
to SOURCES the day a new usage log comes online (e.g. a proposal-generation
or research-session logger); do not retrofit content-sniffing heuristics.

Uninstrumented-metric discipline (same rule as PERSONA_HEALTH_SCORECARD):
a function with no real log source is reported as NOT_INSTRUMENTED, never
defaulted to $0 or omitted silently. See UNINSTRUMENTED_FUNCTIONS below.

CLI:
    python3 cost_attribution.py report [--month YYYY-MM] [--out DIR]
    python3 cost_attribution.py report --since 2026-06-01 --until 2026-06-30
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path("/home/john/Thunderbird/OpsCenter/cost_reports")

# $/1M-token rates — used only as a fallback when a log record carries token
# counts but no precomputed cost_usd. Keep in sync with core/ai_infra/router_cost_gates.py
# and api/thunderbird_api_costs.py pricing tables when models change.
MODEL_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
    "gemini-2.5-flash-lite": {"input": 0.0, "output": 0.0},  # free tier
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

# Known usage logs -> (function category, provider label).
# `token_fields` names the (input, output) keys as they actually appear in
# that file, since the three existing logs don't share a schema.
SOURCES: list[dict[str, Any]] = [
    {
        "file": "claude_narrative_usage.jsonl",
        "function": "narrative_generation",
        "provider": "Claude",
        "token_fields": ("input_tokens", "output_tokens"),
        "unit_label": "cost_per_narrative",
    },
    {
        "file": "gemini_usage.jsonl",
        "function": "data_processing",
        "provider": "Gemini",
        "token_fields": ("input_tokens_est", "output_tokens_est"),
        "unit_label": "cost_per_data_processing_call",
    },
    {
        "file": "gemini_file_usage.jsonl",
        "function": "data_processing",
        "provider": "Gemini",
        "token_fields": ("tokens_est", None),
        "unit_label": "cost_per_data_processing_call",
    },
]

# Functions the Phase 4 roadmap calls out that have no wired-up log source yet.
# Never fabricate a spend number for these — surface the gap instead.
UNINSTRUMENTED_FUNCTIONS = ["research", "proposal_generation"]


@dataclass
class UsageRecord:
    ts: datetime
    provider: str
    function: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_estimated: bool
    success: bool
    source_file: str


def _parse_ts(raw: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = MODEL_RATES.get(model)
    if rates is None:
        return None
    return round(
        (input_tokens / 1_000_000) * rates["input"]
        + (output_tokens / 1_000_000) * rates["output"],
        6,
    )


def load_records(
    data_dir: Path = DATA_DIR,
    sources: list[dict[str, Any]] = SOURCES,
) -> list[UsageRecord]:
    """Read every configured usage log and normalize to UsageRecord rows.

    Missing files are skipped, not errors — a usage log that hasn't been
    written yet (e.g. a fresh persona with zero calls this month) is a
    legitimate zero-activity state, not a load failure.
    """
    records: list[UsageRecord] = []
    for src in sources:
        path = data_dir / src["file"]
        if not path.exists():
            continue
        in_key, out_key = src["token_fields"]
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue  # malformed line — skip, don't crash the whole read
                ts = _parse_ts(row.get("ts", ""))
                if ts is None:
                    continue
                model = row.get("model", "unknown")
                input_tokens = int(row.get(in_key, 0) or 0) if in_key else 0
                output_tokens = int(row.get(out_key, 0) or 0) if out_key else 0
                success = bool(row.get("success", True))

                cost_estimated = False
                cost_usd = row.get("cost_usd")
                if cost_usd is None:
                    cost_usd = _estimate_cost(model, input_tokens, output_tokens)
                    cost_estimated = True
                if cost_usd is None:
                    cost_usd = 0.0
                    cost_estimated = True

                records.append(
                    UsageRecord(
                        ts=ts,
                        provider=src["provider"],
                        function=src["function"],
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=float(cost_usd),
                        cost_estimated=cost_estimated,
                        success=success,
                        source_file=src["file"],
                    )
                )
    return records


def filter_period(
    records: Iterable[UsageRecord], since: datetime | None, until: datetime | None
) -> list[UsageRecord]:
    out = []
    for r in records:
        if since and r.ts < since:
            continue
        if until and r.ts >= until:
            continue
        out.append(r)
    return out


def aggregate_by_model(records: list[UsageRecord]) -> dict[str, dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0,
                                                           "input_tokens": 0, "output_tokens": 0})
    for r in records:
        bucket = agg[r.model]
        bucket["cost_usd"] += r.cost_usd
        bucket["calls"] += 1
        bucket["input_tokens"] += r.input_tokens
        bucket["output_tokens"] += r.output_tokens
    for bucket in agg.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 4)
    return dict(agg)


def aggregate_by_function(records: list[UsageRecord]) -> dict[str, dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0,
                                                           "successful_calls": 0})
    for r in records:
        bucket = agg[r.function]
        bucket["cost_usd"] += r.cost_usd
        bucket["calls"] += 1
        if r.success:
            bucket["successful_calls"] += 1
    for function, bucket in agg.items():
        bucket["cost_usd"] = round(bucket["cost_usd"], 4)
        successful = bucket["successful_calls"]
        bucket["cost_per_success"] = (
            round(bucket["cost_usd"] / successful, 6) if successful else None
        )
    return dict(agg)


def monthly_report(
    year_month: str | None = None,
    since: str | None = None,
    until: str | None = None,
    data_dir: Path = DATA_DIR,
    sources: list[dict[str, Any]] = SOURCES,
) -> dict[str, Any]:
    """Build the ROI report for one calendar month, or an explicit [since, until) range."""
    if year_month:
        y, m = (int(p) for p in year_month.split("-"))
        period_since = datetime(y, m, 1, tzinfo=timezone.utc)
        period_until = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if m == 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc)
        period_label = year_month
    elif since or until:
        period_since = _parse_ts(since) if since else None
        period_until = _parse_ts(until) if until else None
        period_label = f"{since or '...'}_to_{until or '...'}"
    else:
        now = datetime.now(timezone.utc)
        period_since = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        period_until = None
        period_label = now.strftime("%Y-%m")

    all_records = load_records(data_dir=data_dir, sources=sources)
    records = filter_period(all_records, period_since, period_until)

    by_model = aggregate_by_model(records)
    by_function = aggregate_by_function(records)
    total_cost = round(sum(r.cost_usd for r in records), 4)
    estimated_cost = round(sum(r.cost_usd for r in records if r.cost_estimated), 4)

    return {
        "period": period_label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_spend_usd": total_cost,
        "estimated_portion_usd": estimated_cost,
        "total_calls": len(records),
        "spend_by_model": by_model,
        "spend_by_function": by_function,
        "uninstrumented_functions": {
            fn: "NOT_INSTRUMENTED — no usage log source wired up for this function yet"
            for fn in UNINSTRUMENTED_FUNCTIONS
        },
    }


def summary_text(report: dict[str, Any]) -> str:
    lines = [
        f"AI MODEL COST ATTRIBUTION — {report['period']}",
        f"Total spend: ${report['total_spend_usd']:.2f}"
        + (f" (${report['estimated_portion_usd']:.2f} estimated from tokens, no logged cost)"
           if report["estimated_portion_usd"] else ""),
        f"Calls logged: {report['total_calls']}",
        "",
        "By function:",
    ]
    if not report["spend_by_function"]:
        lines.append("  (no usage records in this period)")
    for fn, data in sorted(report["spend_by_function"].items(), key=lambda kv: -kv[1]["cost_usd"]):
        per = f"${data['cost_per_success']:.4f}/success" if data["cost_per_success"] is not None else "n/a"
        lines.append(f"  {fn}: ${data['cost_usd']:.4f} across {data['calls']} calls ({per})")
    lines.append("")
    lines.append("By model:")
    for model, data in sorted(report["spend_by_model"].items(), key=lambda kv: -kv[1]["cost_usd"]):
        lines.append(f"  {model}: ${data['cost_usd']:.4f} across {data['calls']} calls")
    if report["uninstrumented_functions"]:
        lines.append("")
        lines.append("NOT INSTRUMENTED (no data pipeline — not defaulted to $0):")
        for fn in report["uninstrumented_functions"]:
            lines.append(f"  - {fn}")
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"cost_attribution_{report['period']}.json"
    path.write_text(json.dumps(report, indent=2))
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_report = sub.add_parser("report", help="Generate the monthly ROI report")
    p_report.add_argument("--month", help="YYYY-MM, defaults to current month")
    p_report.add_argument("--since", help="ISO date, inclusive")
    p_report.add_argument("--until", help="ISO date, exclusive")
    p_report.add_argument("--out", help="Output directory", default=str(OUTPUT_DIR))

    args = parser.parse_args(argv)

    if args.cmd == "report":
        report = monthly_report(year_month=args.month, since=args.since, until=args.until)
        path = write_report(report, output_dir=Path(args.out))
        print(summary_text(report))
        print(f"\nWritten: {path}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
