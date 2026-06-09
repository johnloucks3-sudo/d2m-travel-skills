#!/usr/bin/env python3
"""
worktree_dossier_sweep.py — Parallel Dossier Validation via Git Worktrees
=========================================================================
M-090 | Reyes A8 domain | Dreams2Memories Travel, LLC

Creates isolated git worktrees, runs validate_dossier.py in parallel on
each active dossier, reports results, and auto-cleans unmodified branches.

Usage:
    python3 scripts/worktree_dossier_sweep.py                    # full sweep
    python3 scripts/worktree_dossier_sweep.py --dry-run          # preview only
    python3 scripts/worktree_dossier_sweep.py --cleanup          # remove stale worktrees
    python3 scripts/worktree_dossier_sweep.py --dossier "Furlow" # single dossier test
    python3 scripts/worktree_dossier_sweep.py --workers 4        # parallel count

Dependencies: validate_dossier.py, git worktree, Python 3.10+
"""
import argparse
import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("worktree_sweep")

ROOT = Path("/home/john/Thunderbird")
DOSSIER_DIR = ROOT / "dossiers"
VALIDATE_SCRIPT = ROOT / "itinerary" / "validate_dossier.py"
WORKTREE_BASE = ROOT / ".claude" / "worktrees"
BRANCH_PREFIX = "sweep/dossier-"

ACTIVE_PREFIXES = (
    "DOSSIER_", "Furlow_", "Ely_", "Darrow_", "Nichols_",
    "McLeod_", "McGlasson_", "Kuklinski_", "Morton_", "Dodge_",
    "Westbrook_", "Loucks_", "Spencer_", "Lyons_", "Britan_",
    "Heer_", "Piontek_", "Rehfeldt_", "Trien_", "McLeran_",
)

PROSPECT_MARKERS = ("prospect", "PROSPECT", "Prospect", "tips", "guide", "CLAUDE.md")


def is_active_dossier(path: Path) -> bool:
    """Return True if this file looks like an active client dossier."""
    name = path.name
    if not name.endswith(".md") and not name.endswith(".MD"):
        return False
    if any(m in name.lower() for m in ("prospect", "tips_guide", "claude", "readme")):
        return False
    if name in ("CLAUDE.md",):
        return False
    if not name.startswith(ACTIVE_PREFIXES):
        # Also catch files like Loucks_Regent_Grandeur_3122006.md
        for known_client in ("Loucks_", "Britan_", "Heer_", "Piontek_", "Trien_",
                             "Westbrook_", "Spencer_", "Lyons_", "McLeran_"):
            if name.startswith(known_client):
                return True
        return False
    return True


def get_active_dossiers() -> list[Path]:
    """Return sorted list of active dossier paths."""
    files = [f for f in sorted(DOSSIER_DIR.iterdir()) if is_active_dossier(f)]
    log.info(f"Found {len(files)} active dossiers in {DOSSIER_DIR}")
    return files


def _run(cmd: list[str], timeout: int = 120, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        cwd=str(cwd or ROOT),
    )


def create_worktree(dossier: Path) -> Optional[Path]:
    """Create a git worktree + branch for a single dossier. Returns worktree path or None."""
    slug = dossier.stem.lower().replace(" ", "-").replace("_", "-")[:60]
    branch = f"{BRANCH_PREFIX}{slug}"
    worktree_path = WORKTREE_BASE / f"sweep-{slug}"

    # Skip if worktree already exists
    result = _run(["git", "worktree", "list"])
    if str(worktree_path) in result.stdout:
        log.info(f"  worktree already exists: {worktree_path.name}")
        return worktree_path

    # Check if branch exists — if so, delete locally to start fresh
    branch_check = _run(["git", "branch", "--list", branch])
    if branch.strip() in branch_check.stdout:
        _run(["git", "branch", "-D", branch])

    # Create worktree from master on a new branch
    result = _run([
        "git", "worktree", "add", "-b", branch,
        str(worktree_path), "master",
    ], timeout=30)
    if result.returncode != 0:
        log.warning(f"  failed to create worktree for {dossier.name}: {result.stderr[:200]}")
        return None

    log.info(f"  created worktree: {worktree_path.name} (branch: {branch})")
    return worktree_path


def validate_in_worktree(worktree_path: Path, dossier: Path) -> dict:
    """Run validate_dossier.py on a single dossier inside its worktree."""
    validate_in_wt = worktree_path / "itinerary" / "validate_dossier.py"
    dossier_rel = f"dossiers/{dossier.name}"

    if not validate_in_wt.exists():
        return {
            "dossier": dossier.name,
            "status": "SKIPPED",
            "exit_code": -1,
            "stdout": "",
            "stderr": "validate_dossier.py not found in worktree",
            "duration_s": 0,
        }

    start = time.time()
    try:
        result = _run(
            [sys.executable, str(validate_in_wt), str(worktree_path / dossier_rel)],
            timeout=300, cwd=worktree_path,
        )
        duration = round(time.time() - start, 1)
        log.info(f"  {dossier.name}: exit={result.returncode} ({duration}s)")
        return {
            "dossier": dossier.name,
            "status": "PASS" if result.returncode == 0 else ("WARN" if result.returncode == 1 else "FAIL"),
            "exit_code": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
            "duration_s": duration,
        }
    except subprocess.TimeoutExpired:
        return {
            "dossier": dossier.name,
            "status": "TIMEOUT",
            "exit_code": -1,
            "stdout": "",
            "stderr": "Timed out after 300s",
            "duration_s": round(time.time() - start, 1),
        }


def has_changes(worktree_path: Path) -> bool:
    """Check if worktree has uncommitted changes."""
    result = _run(["git", "status", "--porcelain"], cwd=worktree_path)
    return bool(result.stdout.strip())


def cleanup_worktree(worktree_path: Path, force: bool = False) -> bool:
    """Remove a worktree and its branch. Returns True on success."""
    slug = worktree_path.name.replace("sweep-", "")
    branch = f"{BRANCH_PREFIX}{slug}"

    if not force and has_changes(worktree_path):
        log.info(f"  keeping {worktree_path.name} — has uncommitted changes")
        return False

    _run(["git", "worktree", "remove", str(worktree_path)], timeout=15)
    _run(["git", "branch", "-D", branch], timeout=10)
    log.info(f"  cleaned: {worktree_path.name}")
    return True


def run_sweep(dossiers: list[Path], workers: int = 3, dry_run: bool = False, cleanup: bool = True) -> dict:
    """Full sweep: create worktrees, validate in parallel, report, cleanup."""
    start = time.time()
    results = []
    worktree_map = {}  # worktree_path -> dossier

    # Phase 1: Create worktrees
    log.info(f"Phase 1: Creating {len(dossiers)} worktrees...")
    for dossier in dossiers:
        if dry_run:
            log.info(f"  [DRY] would create worktree for {dossier.name}")
            continue
        wt = create_worktree(dossier)
        if wt:
            worktree_map[wt] = dossier

    if not dry_run and not worktree_map:
        log.warning("No worktrees created — check git status")
        return {"status": "aborted", "reason": "no worktrees", "results": []}

    # Phase 2: Validate in parallel
    log.info(f"Phase 2: Validating {len(worktree_map)} dossiers in parallel ({workers} workers)...")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(validate_in_worktree, wt, dossier): dossier.name
            for wt, dossier in worktree_map.items()
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({
                    "dossier": futures[future],
                    "status": "ERROR",
                    "error": str(exc),
                })

    # Summary
    results.sort(key=lambda r: r.get("dossier", ""))
    passed = sum(1 for r in results if r.get("status") == "PASS")
    warned = sum(1 for r in results if r.get("status") == "WARN")
    failed = sum(1 for r in results if r.get("status") in ("FAIL", "ERROR", "TIMEOUT"))
    total_time = round(time.time() - start, 1)

    log.info(f"\n{'='*60}")
    log.info(f"SWEEP COMPLETE — {total_time}s")
    log.info(f"  PASS: {passed} | WARN: {warned} | FAIL: {failed} | Total: {len(results)}")

    # Phase 3: Cleanup unmodified worktrees
    if cleanup and not dry_run:
        log.info(f"Phase 3: Cleaning unmodified worktrees...")
        cleaned = 0
        kept = 0
        for wt, dossier in worktree_map.items():
            if cleanup_worktree(wt, force=False):
                cleaned += 1
            else:
                kept += 1
                log.info(f"  preserved: {wt.name} (has changes)")
        log.info(f"  cleaned={cleaned}, kept={kept}")
    elif dry_run:
        log.info(f"Phase 3: [DRY] would clean unmodified worktrees")

    return {
        "status": "complete",
        "dossiers_checked": len(results),
        "passed": passed,
        "warned": warned,
        "failed": failed,
        "duration_s": total_time,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M-090 Worktree Dossier Sweep")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--cleanup", action="store_true", help="Remove all sweep worktrees")
    parser.add_argument("--dossier", type=str, default="", help="Validate a single dossier by name")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers (default 3)")
    parser.add_argument("--keep", action="store_true", help="Keep all worktrees after sweep")
    parser.add_argument("--output", type=str, default="", help="Write report to JSON file")
    args = parser.parse_args()

    # Ensure worktree base exists
    WORKTREE_BASE.mkdir(parents=True, exist_ok=True)

    if args.cleanup:
        # Remove all sweep/ worktrees
        count = 0
        for wt in WORKTREE_BASE.glob("sweep-*"):
            if cleanup_worktree(wt, force=True):
                count += 1
        log.info(f"Cleaned {count} sweep worktrees")
        sys.exit(0)

    # Select dossiers
    if args.dossier:
        # Find single dossier by name fragment
        dossiers = [f for f in DOSSIER_DIR.iterdir() if args.dossier.lower() in f.stem.lower()]
        if not dossiers:
            log.error(f"No dossier found matching '{args.dossier}'")
            sys.exit(1)
        log.info(f"Single dossier mode: {dossiers[0].name}")
    else:
        dossiers = get_active_dossiers()

    if not dossiers:
        log.info("No active dossiers to sweep")
        sys.exit(0)

    result = run_sweep(dossiers, workers=args.workers, dry_run=args.dry_run, cleanup=not args.keep)

    # Print detailed results
    print(f"\n{'='*60}")
    print(f"RESULTS — {result.get('dossiers_checked', 0)} dossiers in {result.get('duration_s', 0)}s")
    for r in result.get("results", []):
        icon = {"PASS": "✅", "WARN": "🟡", "FAIL": "❌", "TIMEOUT": "⏰", "ERROR": "💥", "SKIPPED": "⏭️"}
        ic = icon.get(r.get("status", ""), "❓")
        dur = r.get("duration_s", "?")
        exit_code = r.get("exit_code", "?")
        print(f"  {ic} [{r.get('status','?')}] {r.get('dossier','?')} (exit={exit_code}, {dur}s)")

    print(f"\n  Pass: {result.get('passed', 0)}  Warn: {result.get('warned', 0)}  Fail: {result.get('failed', 0)}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, default=str))
        log.info(f"Report written: {out_path}")

    sys.exit(0 if result.get("failed", 0) == 0 else 1)
