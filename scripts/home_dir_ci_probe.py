#!/usr/bin/env python3
"""
home_dir_ci_probe.py — CI Health Probe for /home/john
Read-only survey: disk growth, loose files, critical bins, cache bloat, Downloads size.
Outputs JSON report to OpsCenter/state/home_dir_health_YYYYMMDD.json.

Exit codes:
  0 — HEALTHY (all checks pass)
  1 — WARNING (non-critical issues detected)
  2 — CRITICAL (action required)

Owner: Sterling (A7)
Registered: config/ci_registry.json as "home-dir-health"
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
HOME = Path("/home/john")
THUNDERBIRD = HOME / "Thunderbird"
STATE_DIR = THUNDERBIRD / "OpsCenter" / "state"
TODAY = datetime.now(timezone.utc).strftime("%Y%m%d")
REPORT_PATH = STATE_DIR / f"home_dir_health_{TODAY}.json"
BASELINE_PATH = STATE_DIR / "home_dir_health_baseline.json"

# Thresholds
CACHE_WARN_GB = 2.0         # ~/.cache > 2GB = CRITICAL
DOWNLOADS_WARN_MB = 500     # Downloads > 500MB = WARNING
LOCAL_WARN_GB = 35.0        # ~/.local > 35GB = WARNING
MAJOR_DIR_GROWTH_MB = 500   # growth > 500MB since last run = WARNING

# Critical executables that must exist and be executable
# n8n runs as a Docker container (~/n8n/docker-compose.yml), not a local bin.
# We check /usr/local/bin/n8n (system install) with ~/.local/bin as fallback.
CRITICAL_BINS = [
    HOME / ".local" / "bin" / "claude",
    Path("/usr/local/bin/n8n"),
]

# Standard directories at home root (not loose files)
STANDARD_DIRS = {
    "Thunderbird", "D2M", "Downloads", "Documents", "Desktop", "Pictures",
    "Videos", "Music", "Templates", "Public", "Projects", "Personal",
    "OpenMontage", "travel-hacking-toolkit", "google-cloud-sdk",
    "playwright-venv", "claude_usage", "signal-cli-data", "bin",
    "n8n", "ollama", "holyclaude",
}

# Known dotfiles (not loose files — these are expected)
KNOWN_DOTFILES = {
    ".bash_history", ".bash_profile", ".bashrc", ".profile",
    ".gitconfig", ".npmrc", ".emacs", ".viminfo", ".inputrc",
    ".dircolors", ".tmux.conf", ".alias", ".fzf.bash", ".wget-hsts",
    ".gtkrc-2.0", ".i18n", ".xim.template", ".pyhistory3.13",
    ".python_history", ".clasprc.json", ".claude.json", ".claude.json.backup",
    ".claude.json.ccs-lock", ".claude-sync.toml", ".cache_cleanup.log",
    ".telegram_gw_live.env", ".telegram_gw_live.env.template",
}


def get_dir_size_mb(path: Path) -> float:
    """Return directory size in MB using du (fast, OS-level)."""
    try:
        result = subprocess.run(
            ["du", "-sm", str(path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return float(result.stdout.split()[0])
    except Exception:
        pass
    return 0.0


def get_file_size_mb(path: Path) -> float:
    """Return file size in MB."""
    try:
        return path.stat().st_size / (1024 * 1024)
    except Exception:
        return 0.0


def check_cache_bloat() -> dict:
    """Check ~/.cache size."""
    cache_dir = HOME / ".cache"
    size_mb = get_dir_size_mb(cache_dir)
    size_gb = size_mb / 1024
    threshold_gb = CACHE_WARN_GB
    status = "CRITICAL" if size_gb > threshold_gb else "OK"
    return {
        "check": "cache_bloat",
        "path": str(cache_dir),
        "size_mb": round(size_mb, 1),
        "size_gb": round(size_gb, 2),
        "threshold_gb": threshold_gb,
        "status": status,
        "note": f"~/.cache is {size_gb:.1f}GB — {'exceeds' if status == 'CRITICAL' else 'within'} {threshold_gb}GB threshold"
    }


def check_downloads() -> dict:
    """Check ~/Downloads size."""
    dl_dir = HOME / "Downloads"
    size_mb = get_dir_size_mb(dl_dir)
    status = "WARNING" if size_mb > DOWNLOADS_WARN_MB else "OK"
    return {
        "check": "downloads_size",
        "path": str(dl_dir),
        "size_mb": round(size_mb, 1),
        "threshold_mb": DOWNLOADS_WARN_MB,
        "status": status,
        "note": f"Downloads is {size_mb:.0f}MB — {'exceeds' if status == 'WARNING' else 'within'} {DOWNLOADS_WARN_MB}MB threshold"
    }


def check_local_size() -> dict:
    """Check ~/.local size (tools, node_modules, etc. accumulate here)."""
    local_dir = HOME / ".local"
    size_mb = get_dir_size_mb(local_dir)
    size_gb = size_mb / 1024
    status = "WARNING" if size_gb > LOCAL_WARN_GB else "OK"
    return {
        "check": "local_size",
        "path": str(local_dir),
        "size_mb": round(size_mb, 1),
        "size_gb": round(size_gb, 2),
        "threshold_gb": LOCAL_WARN_GB,
        "status": status,
        "note": f"~/.local is {size_gb:.1f}GB — {'exceeds' if status == 'WARNING' else 'within'} {LOCAL_WARN_GB}GB threshold"
    }


def check_npm_size() -> dict:
    """Check ~/.npm cache size."""
    npm_dir = HOME / ".npm"
    size_mb = get_dir_size_mb(npm_dir)
    threshold_mb = 500
    status = "WARNING" if size_mb > threshold_mb else "OK"
    return {
        "check": "npm_cache_size",
        "path": str(npm_dir),
        "size_mb": round(size_mb, 1),
        "threshold_mb": threshold_mb,
        "status": status,
        "note": f"~/.npm is {size_mb:.0f}MB — {'exceeds' if status == 'WARNING' else 'within'} {threshold_mb}MB threshold"
    }


def check_critical_bins() -> dict:
    """Verify critical executables exist and are executable."""
    results = []
    overall = "OK"
    for bin_path in CRITICAL_BINS:
        exists = bin_path.exists()
        executable = os.access(str(bin_path), os.X_OK) if exists else False
        # Resolve symlinks
        real_path = None
        if exists:
            try:
                real_path = str(bin_path.resolve())
            except Exception:
                pass
        status = "OK" if (exists and executable) else "CRITICAL"
        if status == "CRITICAL":
            overall = "CRITICAL"
        results.append({
            "bin": str(bin_path),
            "exists": exists,
            "executable": executable,
            "real_path": real_path,
            "status": status,
        })
    return {
        "check": "critical_bins",
        "bins": results,
        "status": overall,
        "note": f"Checked {len(results)} critical executables"
    }


def check_loose_files() -> dict:
    """List non-dotfile, non-standard-dir items at home root."""
    loose = []
    try:
        for item in sorted(HOME.iterdir()):
            name = item.name
            # Skip dotfiles and dotdirs
            if name.startswith("."):
                continue
            # Skip standard directories
            if item.is_dir() and name in STANDARD_DIRS:
                continue
            # Skip if it's a standard dir we just don't know about yet (no alert)
            if item.is_dir():
                size_mb = get_dir_size_mb(item)
                loose.append({
                    "name": name,
                    "type": "directory",
                    "size_mb": round(size_mb, 1),
                    "path": str(item),
                })
            else:
                size_mb = get_file_size_mb(item)
                loose.append({
                    "name": name,
                    "type": "file",
                    "size_mb": round(size_mb, 3),
                    "path": str(item),
                })
    except Exception as e:
        return {"check": "loose_files", "status": "ERROR", "error": str(e), "loose_items": []}

    status = "WARNING" if loose else "OK"
    return {
        "check": "loose_files",
        "count": len(loose),
        "loose_items": loose,
        "status": status,
        "note": f"{len(loose)} non-standard items at home root" if loose else "Home root clean"
    }


def check_major_dir_growth() -> dict:
    """Compare major directory sizes against last baseline."""
    major_dirs = [
        HOME / "Thunderbird",
        HOME / "D2M",
        HOME / "Downloads",
        HOME / "OpenMontage",
        HOME / "google-cloud-sdk",
        HOME / "playwright-venv",
    ]

    current_sizes = {}
    for d in major_dirs:
        if d.exists():
            current_sizes[str(d)] = round(get_dir_size_mb(d), 1)

    # Load baseline if it exists
    growth_warnings = []
    if BASELINE_PATH.exists():
        try:
            baseline_data = json.loads(BASELINE_PATH.read_text())
            baseline_sizes = baseline_data.get("major_dir_sizes", {})
            for path_str, current_mb in current_sizes.items():
                prev_mb = baseline_sizes.get(path_str)
                if prev_mb is not None:
                    delta_mb = current_mb - prev_mb
                    if delta_mb > MAJOR_DIR_GROWTH_MB:
                        growth_warnings.append({
                            "path": path_str,
                            "prev_mb": prev_mb,
                            "current_mb": current_mb,
                            "delta_mb": round(delta_mb, 1),
                        })
        except Exception:
            pass

    status = "WARNING" if growth_warnings else "OK"
    return {
        "check": "major_dir_growth",
        "major_dir_sizes": current_sizes,
        "growth_threshold_mb": MAJOR_DIR_GROWTH_MB,
        "growth_warnings": growth_warnings,
        "status": status,
        "note": (
            f"{len(growth_warnings)} dir(s) grew >{MAJOR_DIR_GROWTH_MB}MB since last run"
            if growth_warnings
            else "No major growth detected vs baseline"
            if BASELINE_PATH.exists()
            else "No baseline yet — sizes recorded for next run"
        )
    }


def severity(status: str) -> int:
    """Map status string to numeric severity (higher = worse)."""
    return {"OK": 0, "WARNING": 1, "CRITICAL": 2, "ERROR": 2}.get(status, 0)


def run_probe() -> int:
    """Run all checks, write JSON report, return exit code."""
    ts = datetime.now(timezone.utc).isoformat()

    checks = [
        check_cache_bloat(),
        check_downloads(),
        check_local_size(),
        check_npm_size(),
        check_critical_bins(),
        check_loose_files(),
        check_major_dir_growth(),
    ]

    max_severity = max(severity(c["status"]) for c in checks)
    overall_status = ["HEALTHY", "WARNING", "CRITICAL"][max_severity]

    report = {
        "probe": "home-dir-health",
        "timestamp": ts,
        "date": TODAY,
        "overall_status": overall_status,
        "exit_code": max_severity,
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "ok": sum(1 for c in checks if c["status"] == "OK"),
            "warnings": sum(1 for c in checks if c["status"] == "WARNING"),
            "critical": sum(1 for c in checks if c["status"] in ("CRITICAL", "ERROR")),
        }
    }

    # Update baseline with current major dir sizes
    growth_check = next((c for c in checks if c["check"] == "major_dir_growth"), None)
    if growth_check:
        baseline = {
            "updated": ts,
            "major_dir_sizes": growth_check.get("major_dir_sizes", {}),
        }
        try:
            BASELINE_PATH.write_text(json.dumps(baseline, indent=2))
        except Exception as e:
            report["baseline_write_error"] = str(e)

    # Write report
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2))
    except Exception as e:
        print(f"ERROR: Could not write report to {REPORT_PATH}: {e}", file=sys.stderr)
        return 2

    # Print summary to stdout
    print(f"HOME DIR CI PROBE — {ts}")
    print(f"Overall: {overall_status} (exit {max_severity})")
    print(f"Report: {REPORT_PATH}")
    print()
    for c in checks:
        icon = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🔴", "ERROR": "❌"}.get(c["status"], "?")
        print(f"  {icon} [{c['status']:8s}] {c['check']}: {c.get('note', '')}")

    return max_severity


if __name__ == "__main__":
    sys.exit(run_probe())
