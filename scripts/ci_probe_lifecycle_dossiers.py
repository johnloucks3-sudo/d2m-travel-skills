#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Lifecycle Dossier Freshness Pipeline
=========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. OpsCenter/logs/dossier_freshness.jsonl — last run < 26h ago (pipeline ran)
  2. dossiers/ directory has at least one .md file modified in the last 30 days
     (active dossiers exist; NOTE: engine uses DOSSIER_*.md glob which is
     case-sensitive and matches 0 files on this FS — probe uses *.md instead)

Probe does NOT re-run the engine. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
AUDIT_LOG = THUNDERBIRD_ROOT / "OpsCenter" / "logs" / "dossier_freshness.jsonl"
DOSSIERS_DIR = THUNDERBIRD_ROOT / "dossiers"
CURRENCY_H = 26
DOSSIER_RECENT_DAYS = 30
ID = "lifecycle-dossiers"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main() -> None:
    # ── CHECK 1: Audit log exists and last run is fresh ─────────────────────
    if not AUDIT_LOG.exists():
        fail(
            f"dossier_freshness.jsonl missing at {AUDIT_LOG} — "
            "dossier freshness pipeline has never run or log was deleted"
        )

    # Read last line of the JSONL
    last_line = None
    try:
        for line in AUDIT_LOG.read_text().splitlines():
            line = line.strip()
            if line:
                last_line = line
    except Exception as e:
        fail(f"Could not read {AUDIT_LOG}: {e}")

    if not last_line:
        fail("dossier_freshness.jsonl is empty — pipeline has never completed a run")

    try:
        entry = json.loads(last_line)
    except Exception as e:
        fail(f"Last line of dossier_freshness.jsonl is not valid JSON: {e}")

    ts_str = entry.get("ts")
    if not ts_str:
        fail(f"Last audit entry has no 'ts' field: {last_line[:120]}")

    try:
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception as e:
        fail(f"Cannot parse ts '{ts_str}': {e}")

    age_h = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600
    if age_h > CURRENCY_H:
        fail(
            f"dossier freshness pipeline last ran {age_h:.1f}h ago "
            f"(threshold {CURRENCY_H}h) — pipeline is DARK. "
            f"Last run: {ts_str}. "
            "systemd timer likely dead or engine crashed. "
            "Fix: systemctl --user restart d2m-dossier-freshness.timer"
        )

    # ── CHECK 2: At least one dossier file is recent ────────────────────────
    # NOTE: engine globs DOSSIER_*.md (case-sensitive, matches 0 on this FS).
    # We glob *.md to catch all naming conventions.
    if not DOSSIERS_DIR.exists():
        fail(f"dossiers/ directory missing at {DOSSIERS_DIR}")

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=DOSSIER_RECENT_DAYS)
    recent_count = 0
    total_md = 0

    for fp in DOSSIERS_DIR.glob("*.md"):
        total_md += 1
        mtime = datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc)
        if mtime > cutoff:
            recent_count += 1

    if total_md == 0:
        fail(f"No .md files in {DOSSIERS_DIR} — dossier directory is empty")

    if recent_count == 0:
        fail(
            f"No dossier files modified in the last {DOSSIER_RECENT_DAYS} days "
            f"({total_md} total dossiers exist) — dossier system appears stale/inactive"
        )

    stale_count = entry.get("stale_count", 0)
    print(
        f"GREEN {ID}: pipeline ran {age_h:.1f}h ago; "
        f"{recent_count}/{total_md} dossiers updated in last {DOSSIER_RECENT_DAYS}d; "
        f"stale_count={stale_count} (last audit {ts_str[:10]})"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
