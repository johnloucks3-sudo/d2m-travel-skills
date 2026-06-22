#!/usr/bin/env python3
"""
api_registry_scan.py — Daily API key registry scanner for Thunderbird Wing.

Reads config/api_registry.json, checks .env for each credential's env_var,
writes config/api_registry_status.json, and syncs results to Google Sheets
"API costs" tab of the D2M AI Metrics sheet.

Usage:
    python3 scripts/api_registry_scan.py           # full run (Sheets sync included)
    python3 scripts/api_registry_scan.py --dry-run # skip Sheets write, print JSON only

Standing Order: SO-CI-RAZOR-SHARP-20260620. Owner: Harlan (A9) / Whetstone (A14).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ── project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]

REGISTRY_PATH = ROOT / "config" / "api_registry.json"
STATUS_PATH = ROOT / "config" / "api_registry_status.json"
DOTENV_PATH = ROOT / ".env"
TAB = "API costs"


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_dotenv(path: Path) -> set:
    """Return the set of key names defined in a .env file."""
    keys: set = set()
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=", 1)[0].strip()
                if key:
                    keys.add(key)
    except FileNotFoundError:
        pass
    return keys


def _scan_status(entry: dict, env_keys: set) -> tuple[bool | None, str]:
    """
    Derive (key_present, scan_status) for one registry entry.

    Returns:
        key_present: True / False / None (None means env_var is null — OAuth token)
        scan_status: "OK" | "PENDING" | "MISSING_KEY" | "DISABLED" | "EXPIRED"
    """
    status = entry.get("status", "")
    env_var = entry.get("env_var")

    if status == "disabled":
        return (None, "DISABLED")
    if status == "expired":
        return (None, "EXPIRED")
    if status == "pending_key":
        return (None, "PENDING")

    # status == "active"
    if env_var is None:
        # OAuth-style credential — no env var to check
        return (None, "OK")

    key_present = env_var in env_keys
    if key_present:
        return (True, "OK")
    return (False, "MISSING_KEY")


def _key_present_display(key_present: bool | None, env_var) -> str:
    """Human-readable cell value for Key Present column."""
    if env_var is None:
        return "N/A (OAuth)"
    if key_present is None:
        return "N/A"
    return "YES" if key_present else "NO"


# ── core scan ─────────────────────────────────────────────────────────────────

def run_scan(dotenv_path: Path = DOTENV_PATH) -> dict:
    """Load registry and .env; return status dict (does NOT write files)."""
    registry = json.loads(REGISTRY_PATH.read_text())
    credentials_raw = registry.get("credentials", [])
    env_keys = _load_dotenv(dotenv_path)

    scanned_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    ok_count = warning_count = error_count = 0
    results = []

    for entry in credentials_raw:
        key_present, scan_status = _scan_status(entry, env_keys)

        if scan_status == "OK":
            ok_count += 1
        elif scan_status in ("MISSING_KEY", "EXPIRED"):
            error_count += 1
        elif scan_status in ("PENDING", "DISABLED"):
            warning_count += 1

        results.append({
            "name": entry.get("name", ""),
            "env_var": entry.get("env_var"),
            "tier": entry.get("tier", ""),
            "monthly_cost_usd": entry.get("monthly_cost_usd", 0),
            "monthly_limit": entry.get("monthly_limit", ""),
            "status": entry.get("status", ""),
            "key_present": key_present,
            "scan_status": scan_status,
            "notes": entry.get("notes", ""),
            "added": entry.get("added", ""),
        })

    return {
        "scanned_at": scanned_at,
        "total": len(results),
        "ok_count": ok_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "credentials": results,
    }


# ── Sheets sync ───────────────────────────────────────────────────────────────

def sync_to_sheets(status: dict) -> bool:
    """
    Push scan results to Google Sheets "API costs" tab.

    Returns True on success, False on failure (caller logs gracefully).
    """
    try:
        sys.path.insert(0, str(ROOT))
        from core.data.sheets_write import clear_range, batch_update, AI_METRICS_SHEET_ID
    except ImportError as exc:
        print(f"[SHEETS] Import error — skipping Sheets sync: {exc}", file=sys.stderr)
        return False

    SHEET_ID = AI_METRICS_SHEET_ID
    scanned_at = status["scanned_at"]

    headers = [
        "Name",
        "Env Var",
        "Tier",
        "Monthly Cost ($)",
        "Monthly Limit",
        "Registry Status",
        "Key Present",
        "Scan Status",
        "Notes",
        "Last Scanned",
    ]

    data_rows = []
    for cred in status["credentials"]:
        env_var = cred.get("env_var")
        key_present = cred.get("key_present")
        notes_raw = cred.get("notes") or ""
        data_rows.append([
            cred.get("name", ""),
            env_var if env_var is not None else "N/A (OAuth)",
            cred.get("tier", ""),
            cred.get("monthly_cost_usd", 0),
            cred.get("monthly_limit", ""),
            cred.get("status", ""),
            _key_present_display(key_present, env_var),
            cred.get("scan_status", ""),
            notes_raw[:80],          # truncate long notes
            scanned_at,
        ])

    try:
        clear_range(SHEET_ID, f"{TAB}!A:Z")
        updates = [
            {"range": f"{TAB}!A1", "values": [headers]},
            {"range": f"{TAB}!A2", "values": data_rows},
        ]
        batch_update(SHEET_ID, updates)
        return True
    except Exception as exc:
        print(f"[SHEETS] Write failed — status JSON still written: {exc}", file=sys.stderr)
        return False


# ── output ────────────────────────────────────────────────────────────────────

def print_summary(status: dict, sheets_ok: bool | None = None) -> None:
    total = status["total"]
    ok = status["ok_count"]
    warn = status["warning_count"]
    err = status["error_count"]
    scanned_at = status["scanned_at"]

    print(f"\n{'─' * 60}")
    print(f"  API Registry Scan — {scanned_at}")
    print(f"{'─' * 60}")
    print(f"  Total credentials : {total}")
    print(f"  OK                : {ok}")
    print(f"  Warnings (pending/disabled) : {warn}")
    print(f"  Errors (missing/expired)    : {err}")
    print(f"{'─' * 60}")

    if err:
        print("  ERRORS:")
        for c in status["credentials"]:
            if c["scan_status"] in ("MISSING_KEY", "EXPIRED"):
                print(f"    🔴 {c['name']} [{c['scan_status']}] — env_var: {c['env_var']}")

    if warn:
        print("  WARNINGS:")
        for c in status["credentials"]:
            if c["scan_status"] in ("PENDING", "DISABLED"):
                print(f"    🟡 {c['name']} [{c['scan_status']}]")

    if sheets_ok is True:
        print(f"\n  ✅ Synced to Google Sheets tab '{TAB}'")
    elif sheets_ok is False:
        print(f"\n  ⚠️  Sheets sync failed — {STATUS_PATH.name} written locally")
    else:
        print(f"\n  (dry-run — Sheets sync skipped)")

    print(f"\n  Status JSON → {STATUS_PATH}")
    print()


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Thunderbird API Registry Scanner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Google Sheets write; print JSON summary only",
    )
    parser.add_argument(
        "--dotenv",
        default=str(DOTENV_PATH),
        help=f"Path to .env file (default: {DOTENV_PATH})",
    )
    args = parser.parse_args()

    dotenv_path = Path(args.dotenv)

    # 1. Scan
    status = run_scan(dotenv_path=dotenv_path)

    # 2. Write status JSON
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2))

    # 3. Sheets sync (unless --dry-run)
    sheets_ok: bool | None = None
    if not args.dry_run:
        sheets_ok = sync_to_sheets(status)

    # 4. Print summary
    print_summary(status, sheets_ok=sheets_ok)

    # Exit non-zero if there are errors, so a systemd timer can catch failures
    if status["error_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
