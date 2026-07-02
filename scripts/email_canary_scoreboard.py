#!/usr/bin/env python3
"""
email_canary_scoreboard.py — Phase B canary classification comparison report

Reads the audit DB and computes:
  1. Shadow-vs-shadow agreement  (inbox-zero-style vs n8n-style)
     — Always available; does not require account match with live sweep.
  2. Custom-vs-shadow agreement  (live sweep vs each shadow classifier)
     — Requires same-account reads AND the vocabulary normalization map below.
     — Shows overlap count so zero-agreement isn't misread as success.
  3. Missed directives: messages where a classifier said DIRECTIVE
     but the other said something different.
  4. Per-source category distribution.

Outputs to stdout + output/EMAIL_CANARY_SCOREBOARD.md.

Usage:
  .venv/bin/python3 scripts/email_canary_scoreboard.py
  .venv/bin/python3 scripts/email_canary_scoreboard.py --since-hours 48
"""

import argparse
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
DB_PATH = REPO / "core" / "email" / "email_audit.db"
OUT_DIR = REPO / "output"
OUT_FILE = OUT_DIR / "EMAIL_CANARY_SCOREBOARD.md"

# ── Sources ────────────────────────────────────────────────────────────────────
SOURCE_INBOX_ZERO = "inbox-zero-style"
SOURCE_N8N        = "n8n-style"
CUSTOM_SOURCES    = {"sweep", "ingest", "inbox"}  # live sweep sources

# ── Vocabulary normalisation map ───────────────────────────────────────────────
# The live custom sweep uses a different vocabulary than the canary.
# Without this map, custom-vs-shadow comparison is meaningless.
# Update if sweep vocabulary changes.
CUSTOM_TO_CANARY = {
    "commander_directive": "DIRECTIVE",
    "direct_command":      "DIRECTIVE",
    "commander_email":     "DIRECTIVE",   # email_task_ingest default
    "client_inquiry":      "QUESTION",
    "vendor_comm":         "CC-FYI",
    "booking_confirmation":"CC-FYI",
    "financial":           "CC-FYI",
    "intel":               "CC-FYI",
    "personal":            "OTHER",
}

def _normalize_custom(classified_as: str | None) -> str:
    """Map a custom-sweep classified_as value → canary category. Unknown → OTHER."""
    if not classified_as:
        return "OTHER"
    return CUSTOM_TO_CANARY.get(classified_as.lower(), "OTHER")


# ════════════════════════════════════════════════════════════════════════════════
# DB queries
# ════════════════════════════════════════════════════════════════════════════════

def _load_rows(con: sqlite3.Connection, since_hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    rows = con.execute(
        """
        SELECT message_id, source, classified_as, action_taken, ts
        FROM email_events
        WHERE ts >= ?
        ORDER BY ts ASC
        """,
        (cutoff_str,),
    ).fetchall()
    return [
        {"message_id": r[0], "source": r[1], "classified_as": r[2],
         "action_taken": r[3], "ts": r[4]}
        for r in rows
    ]


def _group_by_message(rows: list[dict]) -> dict[str, dict[str, str]]:
    """Returns {message_id: {source: classified_as}} for 'classified' rows only."""
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for r in rows:
        if r["action_taken"] == "classified":
            grouped[r["message_id"]][r["source"]] = r["classified_as"]
    return grouped


def _per_source_counts(rows: list[dict]) -> dict[str, dict[str, int]]:
    """Returns {source: {category: count}} for classified rows."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["action_taken"] == "classified":
            counts[r["source"]][r["classified_as"] or "OTHER"] += 1
    return counts


# ════════════════════════════════════════════════════════════════════════════════
# Agreement calculation
# ════════════════════════════════════════════════════════════════════════════════

def _agreement(
    grouped: dict[str, dict[str, str]],
    source_a: str,
    source_b: str,
    norm_a: bool = False,
    norm_b: bool = False,
) -> tuple[int, int, float, list[str]]:
    """Compare two sources across all messages where both have a 'classified' row.

    norm_a / norm_b: apply CUSTOM_TO_CANARY normalisation before comparing.
    Returns (overlap_count, agree_count, agree_pct, missed_directive_msg_ids).
    """
    overlap = 0
    agree = 0
    missed_directive: list[str] = []

    for msg_id, src_map in grouped.items():
        if source_a not in src_map or source_b not in src_map:
            continue
        overlap += 1

        cat_a = src_map[source_a]
        cat_b = src_map[source_b]

        if norm_a:
            cat_a = _normalize_custom(cat_a)
        if norm_b:
            cat_b = _normalize_custom(cat_b)

        if cat_a == cat_b:
            agree += 1
        else:
            # Missed directive: one side said DIRECTIVE, the other didn't
            if "DIRECTIVE" in (cat_a, cat_b):
                missed_directive.append(
                    f"  {msg_id[:12]}  {source_a}={cat_a}  {source_b}={cat_b}"
                )

    pct = (agree / overlap * 100) if overlap else 0.0
    return overlap, agree, pct, missed_directive


# ════════════════════════════════════════════════════════════════════════════════
# Report builder
# ════════════════════════════════════════════════════════════════════════════════

def _fmt_row(label: str, overlap: int, agree: int, pct: float) -> str:
    bar = "█" * int(pct / 5)  # 20-char max bar
    return f"| {label:<38} | {overlap:>7} | {agree:>5} | {pct:>5.1f}% | {bar:<20} |"


def build_report(rows: list[dict], since_hours: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    grouped = _group_by_message(rows)
    per_source = _per_source_counts(rows)

    lines = [
        "# EMAIL CANARY SCOREBOARD",
        f"*Generated: {now} | Window: last {since_hours}h*",
        "",
        "> **Vocabulary note:** The live sweep uses `commander_directive`, `client_inquiry`, etc.",
        "> The canary uses `DIRECTIVE`, `QUESTION`, `CC-FYI`, `OTHER`.",
        "> Custom-vs-shadow rows are normalised via CUSTOM_TO_CANARY map before comparison.",
        "> An overlap of 0 means same-account data not yet available — shadow-vs-shadow is always valid.",
        "",
        "## 1. SHADOW-vs-SHADOW AGREEMENT (always available)",
        "",
        f"| {'Comparison':<38} | {'Overlap':>7} | {'Agree':>5} | {'Agree%':>6} | {'Bar':<20} |",
        f"|{'-'*40}|{'-'*9}|{'-'*7}|{'-'*8}|{'-'*22}|",
    ]

    ovl, agr, pct, missed = _agreement(grouped, SOURCE_INBOX_ZERO, SOURCE_N8N)
    lines.append(_fmt_row(f"{SOURCE_INBOX_ZERO} vs {SOURCE_N8N}", ovl, agr, pct))
    lines.append("")

    # Missed directives — shadow vs shadow
    if missed:
        lines.append(f"**Missed directives ({len(missed)})** — one classifier said DIRECTIVE, other didn't:")
        for m in missed:
            lines.append(m)
    else:
        if ovl == 0:
            lines.append(f"*No overlap yet (0 messages classified by both shadow sources). "
                         f"Run `email_canary_shadow.py --limit 25` to populate.*")
        else:
            lines.append(f"*No missed directives — classifiers agree on all {ovl} overlapping messages.*")
    lines.append("")

    # Custom sources present?
    custom_sources_present = [s for s in per_source if s in CUSTOM_SOURCES]
    lines.append("## 2. CUSTOM-vs-SHADOW AGREEMENT")
    lines.append("")
    if not custom_sources_present:
        lines.append(
            "*No custom-sweep rows in audit DB yet (sweep writes with source='sweep'/'ingest'/'inbox'). "
            "Shadow-vs-shadow above is the operative signal for now.*"
        )
    else:
        lines.append(
            f"| {'Comparison':<38} | {'Overlap':>7} | {'Agree':>5} | {'Agree%':>6} | {'Bar':<20} |"
        )
        lines.append(f"|{'-'*40}|{'-'*9}|{'-'*7}|{'-'*8}|{'-'*22}|")

        for csrc in sorted(custom_sources_present):
            for shadow in [SOURCE_INBOX_ZERO, SOURCE_N8N]:
                ovl, agr, pct, missed = _agreement(
                    grouped, csrc, shadow,
                    norm_a=True,   # normalise custom → canary vocab
                    norm_b=False,
                )
                label = f"{csrc}(norm) vs {shadow}"
                lines.append(_fmt_row(label, ovl, agr, pct))
                if missed:
                    lines.append(f"  Missed directives ({len(missed)}):")
                    for m in missed:
                        lines.append(m)

    lines.append("")
    lines.append("## 3. PER-SOURCE CATEGORY DISTRIBUTION")
    lines.append("")

    all_cats = {"DIRECTIVE", "QUESTION", "CC-FYI", "OTHER"}
    all_sources = sorted(per_source.keys())

    if not all_sources:
        lines.append("*No classified rows yet.*")
    else:
        # Header
        header = f"| {'Source':<28} | {'Total':>5} |"
        for cat in sorted(all_cats):
            header += f" {cat:>9} |"
        lines.append(header)
        sep = f"|{'-'*30}|{'-'*7}|" + f"{'-'*11}|" * len(all_cats)
        lines.append(sep)

        for src in all_sources:
            counts = per_source[src]
            # For custom sources, normalise category keys before displaying
            if src in CUSTOM_SOURCES:
                normalised: dict[str, int] = defaultdict(int)
                for k, v in counts.items():
                    normalised[_normalize_custom(k)] += v
                counts = normalised

            total = sum(counts.values())
            row = f"| {src:<28} | {total:>5} |"
            for cat in sorted(all_cats):
                row += f" {counts.get(cat, 0):>9} |"
            lines.append(row)

    lines.append("")
    lines.append("## 4. GLOSSARY")
    lines.append("")
    lines.append("| Canary category | Mapped from (custom sweep) |")
    lines.append("|---|---|")
    for k, v in CUSTOM_TO_CANARY.items():
        lines.append(f"| {v} | `{k}` |")
    lines.append("")
    lines.append(f"*Sources: shadow rows written by `scripts/email_canary_shadow.py`. "
                 f"Custom rows written by `OpsCenter/run_commander_directive_sweep.py` "
                 f"and `OpsCenter/email_task_ingest.py`.*")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Email canary scoreboard")
    parser.add_argument("--since-hours", type=int, default=168,
                        help="Look back N hours (default: 168 = 7 days)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERROR] Audit DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    rows = _load_rows(con, args.since_hours)
    con.close()

    report = build_report(rows, args.since_hours)

    # ── Stdout ──────────────────────────────────────────────────────────────
    print(report)

    # ── File ────────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(report)
    print(f"\n[Saved → {OUT_FILE}]", file=sys.stderr)


if __name__ == "__main__":
    main()
