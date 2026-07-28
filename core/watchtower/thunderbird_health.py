"""
Thunderbird OS — System Health Dashboard
=========================================
Dreams2Memories Travel, LLC

Aggregates health across all Thunderbird OS components:
  - Service liveness (MCP, REST API, Telegram, Scheduler, n8n, Portal)
  - Data freshness (briefing, dossier scanner, learning rules, voice ledger,
                    fare watches, commander inbox)
  - Resource usage (disk, log sizes, SQLite DB sizes)

Usage:
  python3 thunderbird_health.py          # Print summary to stdout
  python3 thunderbird_health.py --json   # Dump raw JSON

Import:
  from thunderbird_health import get_full_health, get_health_summary
"""

import json
import logging
import os
import socket
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DATA_DIR = THUNDERBIRD_DIR / "data"
LOGS_DIR = THUNDERBIRD_DIR / "logs"

_BRIEFING_SENT_JSON = THUNDERBIRD_DIR / "briefing_sent.json"
_DOSSIER_SCANNER_LOG = LOGS_DIR / "morning_briefing.log"
_COMMANDER_INBOX_STATE = THUNDERBIRD_DIR / "commander_inbox_state.json"
_FARE_WATCHES_JSON = DATA_DIR / "fare_watches.json"
_VOICE_LEDGER_JSON = THUNDERBIRD_DIR / "voice_ledger.json"
_LEARNING_DB = THUNDERBIRD_DIR / "learning_rules.db"
_CRUISE_DB = THUNDERBIRD_DIR / "cruise_content.db"
_HUD_DB = THUNDERBIRD_DIR / "hud_memory.db"
_SCHEDULER_LOG = THUNDERBIRD_DIR / "scheduler.log"
_MCP_LOG = LOGS_DIR / "mcp_sse.log"
_API_LOG = LOGS_DIR / "api.log"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _age_minutes(ts: datetime) -> float:
    """Minutes since a UTC datetime."""
    return (_now_utc() - ts.astimezone(timezone.utc)).total_seconds() / 60


def _parse_iso(s: str) -> Optional[datetime]:
    """Parse an ISO-8601 string; return None on failure."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _file_mtime(path: Path) -> Optional[datetime]:
    """Last-modified time of a file as UTC datetime."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except FileNotFoundError:
        return None


def _file_size_mb(path: Path) -> Optional[float]:
    """File size in MB; None if missing."""
    try:
        return round(path.stat().st_size / 1_048_576, 3)
    except FileNotFoundError:
        return None


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if TCP port accepts a connection within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def _process_running(name: str) -> bool:
    """Return True if any running process cmdline contains `name`."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _age_label(minutes: Optional[float]) -> str:
    """Human-readable age string."""
    if minutes is None:
        return "unknown"
    if minutes < 60:
        return f"{int(minutes)}m ago"
    if minutes < 1440:
        return f"{int(minutes / 60)}h ago"
    return f"{int(minutes / 1440)}d ago"


# ---------------------------------------------------------------------------
# 1 — Service checks
# ---------------------------------------------------------------------------

def check_services() -> Dict[str, Any]:
    """Check liveness of all Thunderbird OS services."""
    services: Dict[str, Any] = {}

    checks = [
        ("mcp_server",       "localhost", 8765),
        ("rest_api",         "localhost", 8766),
        ("n8n",              "localhost", 5678),
        ("portal",           "localhost", 8780),
    ]

    for name, host, port in checks:
        up = _port_open(host, port)
        services[name] = {
            "status": "UP" if up else "DOWN",
            "port": port,
        }

    # Process-based checks (no fixed port to probe)
    proc_checks = [
        ("telegram_c2",  "thunderbird_telegram_(c2|gw)"),
        ("scheduler",    "thunderbird_scheduler"),
    ]
    for name, pattern in proc_checks:
        running = _process_running(pattern)
        services[name] = {
            "status": "UP" if running else "DOWN",
            "process": pattern,
        }

    up_count = sum(1 for v in services.values() if v["status"] == "UP")
    total = len(services)
    services["_summary"] = {
        "up": up_count,
        "total": total,
        "all_healthy": up_count == total,
    }
    return services


# ---------------------------------------------------------------------------
# 2 — Data freshness checks
# ---------------------------------------------------------------------------

def check_data_freshness() -> Dict[str, Any]:
    """Check recency and counts for all data stores."""
    freshness: Dict[str, Any] = {}

    # Morning briefing — last send date from briefing_sent.json or lock files
    try:
        # Check lock files in OpsCenter first
        lock_dir = THUNDERBIRD_DIR / "OpsCenter"
        lock_files = list(lock_dir.glob("morning_brief_sent_*.lock"))
        latest_lock_dt = None
        latest_date = None

        if lock_files:
            latest_lock = max(lock_files, key=lambda p: p.name)
            try:
                lock_data = json.loads(latest_lock.read_text(encoding="utf-8"))
                sent_at_str = lock_data.get("sent_at")
                if sent_at_str:
                    latest_lock_dt = _parse_iso(sent_at_str)
                    if latest_lock_dt:
                        latest_date = latest_lock_dt.strftime("%Y-%m-%d")
            except Exception:
                latest_lock_dt = _file_mtime(latest_lock)
                if latest_lock_dt:
                    latest_date = latest_lock_dt.strftime("%Y-%m-%d")

        if latest_lock_dt:
            age = _age_minutes(latest_lock_dt)
            freshness["morning_briefing"] = {
                "last_sent": latest_date,
                "age_label": _age_label(age),
                "stale": age is None or age > 1440,
            }
        elif _BRIEFING_SENT_JSON.exists():
            data = json.loads(_BRIEFING_SENT_JSON.read_text(encoding="utf-8"))
            # Values are date strings "YYYY-MM-DD"; find the most recent
            if data:
                latest_date = sorted(data.values())[-1]
                dt = _parse_iso(latest_date + "T06:00:00+00:00")  # treat as 6 AM send
                age = _age_minutes(dt) if dt else None
                freshness["morning_briefing"] = {
                    "last_sent": latest_date,
                    "age_label": _age_label(age),
                    "stale": age is None or age > 1440,  # >24h = stale
                }
            else:
                freshness["morning_briefing"] = {"last_sent": None, "stale": True}
        else:
            freshness["morning_briefing"] = {"last_sent": None, "stale": True}
    except Exception as e:
        freshness["morning_briefing"] = {"error": str(e), "stale": True}

    # Dossier scanner — last line of morning_briefing.log
    try:
        mtime = _file_mtime(_DOSSIER_SCANNER_LOG)
        age = _age_minutes(mtime) if mtime else None
        freshness["dossier_scanner"] = {
            "log_mtime": mtime.isoformat() if mtime else None,
            "age_label": _age_label(age),
            "stale": age is None or age > 1440,
        }
    except Exception as e:
        freshness["dossier_scanner"] = {"error": str(e), "stale": True}

    # Learning compiler — pending rules count from SQLite
    try:
        pending_count = 0
        total_rules = 0
        if _LEARNING_DB.exists():
            conn = sqlite3.connect(str(_LEARNING_DB))
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM principles WHERE applied = 0")
                row = cur.fetchone()
                pending_count = row[0] if row else 0
                cur.execute("SELECT COUNT(*) FROM principles")
                row = cur.fetchone()
                total_rules = row[0] if row else 0
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()
        freshness["learning_compiler"] = {
            "pending_rules": pending_count,
            "total_rules": total_rules,
            "db_exists": _LEARNING_DB.exists(),
        }
    except Exception as e:
        freshness["learning_compiler"] = {"error": str(e)}

    # Voice ledger — rule count
    try:
        rule_count = 0
        if _VOICE_LEDGER_JSON.exists():
            ledger = json.loads(_VOICE_LEDGER_JSON.read_text(encoding="utf-8"))
            global_rules = len(ledger.get("global_rules", []))
            tier_rules = sum(
                len(v) for v in ledger.get("tier_rules", {}).values()
                if isinstance(v, list)
            )
            client_rules = sum(
                len(v) for v in ledger.get("client_rules", {}).values()
                if isinstance(v, list)
            )
            rule_count = global_rules + tier_rules + client_rules
        freshness["voice_ledger"] = {
            "rule_count": rule_count,
            "ledger_exists": _VOICE_LEDGER_JSON.exists(),
        }
    except Exception as e:
        freshness["voice_ledger"] = {"error": str(e)}

    # Fare watches — active count
    try:
        active = 0
        if _FARE_WATCHES_JSON.exists():
            watches = json.loads(_FARE_WATCHES_JSON.read_text(encoding="utf-8"))
            if isinstance(watches, list):
                active = sum(1 for w in watches if w.get("active", True))
            elif isinstance(watches, dict):
                active = sum(1 for w in watches.values() if isinstance(w, dict) and w.get("active", True))
        freshness["fare_watches"] = {
            "active_count": active,
            "file_exists": _FARE_WATCHES_JSON.exists(),
        }
    except Exception as e:
        freshness["fare_watches"] = {"error": str(e)}

    # Commander inbox — last sweep timestamp
    try:
        if _COMMANDER_INBOX_STATE.exists():
            state = json.loads(_COMMANDER_INBOX_STATE.read_text(encoding="utf-8"))
            last_sweep = state.get("last_sweep") or state.get("last_run")
            dt = _parse_iso(last_sweep) if last_sweep else None
            age = _age_minutes(dt) if dt else None
            freshness["commander_inbox"] = {
                "last_sweep": last_sweep,
                "age_label": _age_label(age),
                "stale": age is None or age > 1440,
            }
        else:
            freshness["commander_inbox"] = {"last_sweep": None, "stale": True, "note": "state file missing"}
    except Exception as e:
        freshness["commander_inbox"] = {"error": str(e), "stale": True}

    return freshness


# ---------------------------------------------------------------------------
# 3 — Resource checks
# ---------------------------------------------------------------------------

def check_resources() -> Dict[str, Any]:
    """Disk space, log sizes, SQLite DB sizes."""
    resources: Dict[str, Any] = {}

    # Disk usage for ~/Thunderbird
    try:
        result = subprocess.run(
            ["du", "-sh", str(THUNDERBIRD_DIR)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            used = result.stdout.split()[0]
        else:
            used = "error"

        stat = os.statvfs(THUNDERBIRD_DIR)
        free_gb = round((stat.f_bavail * stat.f_frsize) / 1_073_741_824, 2)
        total_gb = round((stat.f_blocks * stat.f_frsize) / 1_073_741_824, 2)
        used_pct = round(100 * (1 - stat.f_bavail / stat.f_blocks), 1) if stat.f_blocks else 0

        resources["disk"] = {
            "thunderbird_dir_used": used,
            "filesystem_free_gb": free_gb,
            "filesystem_total_gb": total_gb,
            "used_pct": used_pct,
            "warning": used_pct > 85,
        }
    except Exception as e:
        resources["disk"] = {"error": str(e)}

    # Key log file sizes
    log_files = {
        "scheduler.log":       THUNDERBIRD_DIR / "scheduler.log",
        "morning_briefing.log": LOGS_DIR / "morning_briefing.log",
        "mcp_sse.log":         LOGS_DIR / "mcp_sse.log",
        "api.log":             LOGS_DIR / "api.log",
        "heartbeat.log":       THUNDERBIRD_DIR / "heartbeat.log",
        "concierge_monitor.log": LOGS_DIR / "concierge_monitor.log",
    }
    log_sizes = {}
    for name, path in log_files.items():
        sz = _file_size_mb(path)
        log_sizes[name] = {
            "size_mb": sz,
            "exists": path.exists(),
            "warning": sz is not None and sz > 50,
        }
    resources["log_files"] = log_sizes

    # SQLite DB sizes
    db_files = {
        "learning_rules.db": _LEARNING_DB,
        "cruise_content.db": _CRUISE_DB,
        "hud_memory.db":     _HUD_DB,
    }
    db_sizes = {}
    for name, path in db_files.items():
        sz = _file_size_mb(path)
        db_sizes[name] = {
            "size_mb": sz,
            "exists": path.exists(),
            "warning": sz is not None and sz > 200,
        }
    resources["databases"] = db_sizes

    return resources


# ---------------------------------------------------------------------------
# 4 — Aggregate + format
# ---------------------------------------------------------------------------

def get_full_health() -> Dict[str, Any]:
    """Run all health checks and return a structured dict."""
    ts = _now_utc().isoformat()
    services = check_services()
    freshness = check_data_freshness()
    resources = check_resources()

    # Overall status: RED / YELLOW / GREEN
    issues: List[str] = []

    critical_services = ["mcp_server", "rest_api", "telegram_c2"]
    for svc in critical_services:
        if services.get(svc, {}).get("status") == "DOWN":
            issues.append(f"CRITICAL: {svc} is DOWN")

    if freshness.get("morning_briefing", {}).get("stale"):
        issues.append("WARNING: Morning briefing not sent in >24h")

    if resources.get("disk", {}).get("warning"):
        issues.append(f"WARNING: Disk usage {resources['disk'].get('used_pct')}%")

    for name, info in resources.get("log_files", {}).items():
        if info.get("warning"):
            issues.append(f"WARNING: {name} is {info['size_mb']:.1f} MB")

    if not issues:
        overall = "GREEN"
    elif any("CRITICAL" in i for i in issues):
        overall = "RED"
    else:
        overall = "YELLOW"

    return {
        "timestamp": ts,
        "overall": overall,
        "issues": issues,
        "services": services,
        "data_freshness": freshness,
        "resources": resources,
    }


def get_health_summary(health: Optional[Dict[str, Any]] = None) -> str:
    """Return a formatted text SITREP suitable for Telegram or CLI."""
    if health is None:
        health = get_full_health()

    ts = health.get("timestamp", "")[:19].replace("T", " ")
    overall = health.get("overall", "?")
    issues = health.get("issues", [])
    services = health.get("services", {})
    freshness = health.get("data_freshness", {})
    resources = health.get("resources", {})

    status_icon = {"GREEN": "✓", "YELLOW": "!", "RED": "✗"}.get(overall, "?")
    lines = [
        f"THUNDERBIRD OS — SITREP  [{ts} UTC]",
        f"Overall: {status_icon} {overall}",
        "",
        "SERVICES",
    ]

    for svc, info in services.items():
        if svc.startswith("_"):
            continue
        icon = "UP" if info.get("status") == "UP" else "DOWN"
        label = svc.replace("_", " ").title()
        lines.append(f"  {icon:<5} {label}")

    svc_sum = services.get("_summary", {})
    lines.append(f"  {svc_sum.get('up', '?')}/{svc_sum.get('total', '?')} services up")

    lines += ["", "DATA FRESHNESS"]
    for key, info in freshness.items():
        if isinstance(info, dict):
            if "age_label" in info:
                stale_mark = " [STALE]" if info.get("stale") else ""
                lines.append(f"  {key.replace('_', ' ').title():<22} {info['age_label']}{stale_mark}")
            elif "rule_count" in info:
                lines.append(f"  {'Voice Ledger':<22} {info['rule_count']} rules")
            elif "total_rules" in info:
                pending = info.get("pending_rules", 0)
                total = info.get("total_rules", 0)
                lines.append(f"  {'Learning Rules':<22} {total} rules, {pending} pending")
            elif "active_count" in info:
                lines.append(f"  {'Fare Watches':<22} {info['active_count']} active")

    disk = resources.get("disk", {})
    lines += [
        "",
        "RESOURCES",
        f"  Disk used: {disk.get('thunderbird_dir_used', '?')}  "
        f"({disk.get('used_pct', '?')}% of filesystem)",
        f"  Disk free: {disk.get('filesystem_free_gb', '?')} GB",
    ]

    if issues:
        lines += ["", "ISSUES"]
        for issue in issues:
            lines.append(f"  {issue}")
    else:
        lines.append("")
        lines.append("No issues detected.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_health_tools(mcp):
    """Register system_health_check with the MCP server."""
    from pydantic import Field

    @mcp.tool(
        name="system_health_check",
        annotations={"title": "Thunderbird OS System Health Check", "readOnlyHint": True},
    )
    async def system_health_check(
        format: str = Field(
            "summary",
            description="Output format: 'summary' (human-readable text) or 'json' (full dict)",
        ),
    ) -> str:
        """
        Run a full health check across all Thunderbird OS components.

        Returns service liveness, data freshness, disk usage, and an overall
        GREEN / YELLOW / RED status with a list of any active issues.
        """
        health = get_full_health()
        if format == "json":
            return json.dumps(health, indent=2)
        return get_health_summary(health)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    health = get_full_health()
    if "--json" in sys.argv:
        print(json.dumps(health, indent=2))
    else:
        print(get_health_summary(health))
