#!/usr/bin/env python3
"""thunderbird_sentinel.py — Thunderbird Stringent Monitoring Daemon (rebuild)

Original (v1.0, 2026-05-07) was deleted 2026-06-10, never committed, and its
timer was stubbed to /bin/true pending a Commander-held rebuild-scope decision
(see docs/AUTONOMY_BUILD_TRIAGE_20260807.md #7). Original design was recovered
by disassembling the surviving __pycache__ bytecode (dis/marshal — no source
was needed). Commander approved a 3-piece rebuild 2026-08-08, not a full
restore — the rest of the original (generic service/timer restart-and-escalate)
has since been rebuilt, better and broader, by thunderbird_coo_watchdog.py
(13+ services vs. the original's 7). Rebuilding that here would duplicate it.

The 3 pieces that are still genuinely missing from the wing:

  1. Telegram gateway conflict detector — duplicate-process detection (two
     instances of thunderbird_telegram_gw.py fighting over the same getUpdates
     long-poll produces Telegram 409 Conflict) + auto-kill-all-but-newest.
     This exact failure mode recurs in this codebase (git log: keepalive
     zombie-task kills, supertimer duplicate kills) and nothing else catches it.
  2. Content-level log-pattern scanner — CRITICAL/ERROR/WARNING regex sweep
     over journald output for watched services. Systemd's own "active/failed"
     status misses errors that don't crash the process.
  3. nginx + ttyd proxy-chain checks — HTTP/port probes on the layer between
     the Commander's browser and the wing (nginx :80, ttyd-proxy :8099, ttyd
     direct :3100). Nothing else in the wing checks this layer specifically.

Alerting goes through core.comms.commander_channel.notify() (dedup + audit
trail already built in) rather than a bespoke Telegram sender — reuses the
one gateway everything else already uses.

Known limitation vs. the original: nginx's own error log
(/var/log/nginx/error.log) requires root and this process does not have
passwordless sudo — that half of the nginx check is skipped, not guessed at.
HTTP-probe + systemctl status still catch "nginx is down" the way the 2026-06-10
partial rebuild (nginx_health_check.sh) does.

State: OpsCenter/sentinel/sentinel_state.json
Run via: thunderbird-sentinel.timer (every 60s)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(THUNDERBIRD))

STATE_FILE = Path(__file__).resolve().parent / "sentinel_state.json"

TELEGRAM_GW_PROCESS_PATTERN = "thunderbird_telegram_gw.py"
TELEGRAM_GW_SERVICE = "thunderbird-telegram-gw.service"

CONFLICT_LOG_PATTERNS = (
    re.compile(r"409.*Conflict"),
    re.compile(r"terminated by other getUpdates"),
    re.compile(r"conflict.*getUpdates", re.IGNORECASE),
    re.compile(r"ConflictError"),
)

# (severity, compiled_pattern) — first match wins, most severe patterns first.
LOG_SEVERITY_PATTERNS = (
    ("CRITICAL", re.compile(r"Unhandled exception|Traceback \(most recent call last\)|fatal error", re.IGNORECASE)),
    ("ERROR", re.compile(r"\bERROR\b|failed to connect|authentication.*failed|token.*expired|401 Unauthorized|500 Internal Server", re.IGNORECASE)),
    ("WARNING", re.compile(r"retry attempt|slow response|429 Too Many Requests|timeout", re.IGNORECASE)),
)

# Services whose journald output gets the content-level pattern scan.
WATCHED_LOG_SERVICES = (
    "thunderbird-telegram-gw.service",
    "thunderbird-mcp.service",
    "ttyd-terminal.service",
)

LOG_SCAN_WINDOW = "3 min ago"

PROXY_CHAIN_PROBES = (
    ("nginx front door", "http://127.0.0.1/"),
    ("ttyd nginx proxy", "http://127.0.0.1:8099/"),
    ("ttyd direct", "http://127.0.0.1:3100/"),
)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"last_run": None, "last_log_scan_ts": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ── Piece 1: Telegram gateway conflict detector ────────────────────────────

def find_telegram_gw_pids() -> list[dict]:
    """Return [{pid, start_epoch}] for every running thunderbird_telegram_gw.py process.

    SAFETY: `pgrep -af <pattern>` self-matches any shell wrapper whose own command
    line happens to contain the search pattern (e.g. a `bash -c 'eval "pgrep -af
    thunderbird_telegram_gw.py"'` snapshot wrapper) — verified live 2026-08-08,
    this genuinely produces a false second "process". Guard on two independent
    signals before counting a match: (1) the line must NOT contain the tell-tale
    wrapper tokens, and (2) the process's actual argv[0] (via /proc, not the
    pgrep -a text) must be a python interpreter. Never trust -a text alone for
    a check that can trigger a kill.
    """
    result = _run(["pgrep", "-f", TELEGRAM_GW_PROCESS_PATTERN])
    if result.returncode not in (0, 1):
        return []
    procs = []
    for pid in result.stdout.split():
        if not pid.isdigit():
            continue
        cmdline_path = Path(f"/proc/{pid}/cmdline")
        if not cmdline_path.exists():
            continue
        try:
            argv = cmdline_path.read_bytes().split(b"\x00")
            argv = [a.decode(errors="replace") for a in argv if a]
        except OSError:
            continue
        if not argv:
            continue
        # Real gateway process: python interpreter as argv[0], script path as an arg.
        # Excludes pgrep/bash/eval wrapper noise that merely mentions the filename.
        is_python = "python" in Path(argv[0]).name.lower()
        has_script = any(TELEGRAM_GW_PROCESS_PATTERN in a for a in argv)
        if not (is_python and has_script):
            continue
        etimes = _run(["ps", "-p", pid, "-o", "etimes=", "--no-headers"])
        if etimes.returncode == 0 and etimes.stdout.strip().isdigit():
            procs.append({"pid": int(pid), "age_secs": int(etimes.stdout.strip())})
    return procs


def scan_gw_journal_for_conflict() -> list[str]:
    result = _run(["journalctl", "--user", "-u", TELEGRAM_GW_SERVICE, "--since", LOG_SCAN_WINDOW, "--no-pager"])
    if result.returncode != 0:
        return []
    hits = []
    for line in result.stdout.splitlines():
        if any(p.search(line) for p in CONFLICT_LOG_PATTERNS):
            hits.append(line.strip())
    return hits[-10:]


def kill_duplicate_telegram_processes(procs: list[dict]) -> list[int]:
    """Kill all gateway processes except the most recently started one (lowest age_secs).

    The one destructive action in this rebuild — only fires when >1 process is
    genuinely found, never touches a single healthy process.
    """
    if len(procs) <= 1:
        return []
    newest = min(procs, key=lambda p: p["age_secs"])
    killed = []
    for p in procs:
        if p["pid"] == newest["pid"]:
            continue
        r = _run(["kill", "-TERM", str(p["pid"])])
        if r.returncode == 0:
            killed.append(p["pid"])
    return killed


def check_telegram_gateway() -> dict:
    result = {"check": "telegram_gateway", "status": "PASS", "detail": ""}
    procs = find_telegram_gw_pids()

    if not procs:
        svc = _run(["systemctl", "--user", "is-active", TELEGRAM_GW_SERVICE])
        result["status"] = "FAIL" if svc.stdout.strip() != "active" else "WARN"
        result["detail"] = "No gateway process found via pgrep despite service state: " + svc.stdout.strip()
        return result

    if len(procs) > 1:
        conflict_lines = scan_gw_journal_for_conflict()
        killed = kill_duplicate_telegram_processes(procs)
        result["status"] = "CONFLICT"
        result["detail"] = (
            f"{len(procs)} gateway processes running (PIDs {[p['pid'] for p in procs]}). "
            f"Killed duplicates: {killed}. Kept newest (age {min(p['age_secs'] for p in procs)}s). "
            f"Recent conflict log lines: {conflict_lines[-3:] if conflict_lines else 'none'}"
        )
        return result

    result["detail"] = f"1 process running (PID {procs[0]['pid']}, age {procs[0]['age_secs']}s)"
    return result


# ── Piece 2: content-level log-pattern scanner ──────────────────────────────

def scan_service_log(service: str) -> list[tuple[str, str]]:
    """Return [(severity, line)] for new-since-last-scan matches in this service's journal."""
    result = _run(["journalctl", "--user", "-u", service, "--since", LOG_SCAN_WINDOW, "--no-pager"])
    if result.returncode != 0:
        return []
    hits = []
    for line in result.stdout.splitlines():
        for severity, pattern in LOG_SEVERITY_PATTERNS:
            if pattern.search(line):
                hits.append((severity, line.strip()))
                break
    return hits


def check_log_patterns() -> dict:
    result = {"check": "log_patterns", "status": "PASS", "hits": []}
    for service in WATCHED_LOG_SERVICES:
        hits = scan_service_log(service)
        for severity, line in hits:
            result["hits"].append({"service": service, "severity": severity, "line": line})
    if any(h["severity"] == "CRITICAL" for h in result["hits"]):
        result["status"] = "FAIL"
    elif result["hits"]:
        result["status"] = "WARN"
    return result


# ── Piece 3: nginx + ttyd proxy-chain checks ────────────────────────────────

def http_probe(url: str) -> tuple[bool, str]:
    r = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10", url])
    code = r.stdout.strip()
    # Any HTTP response (even 401/403/404) proves the daemon is serving —
    # only "no response at all" (curl prints nothing / 000) means down.
    alive = bool(code) and code != "000"
    return alive, code or "no response"


def check_proxy_chain() -> dict:
    result = {"check": "proxy_chain", "status": "PASS", "probes": []}
    nginx_svc = _run(["systemctl", "is-active", "nginx"])
    result["nginx_service_active"] = nginx_svc.stdout.strip() == "active"

    for label, url in PROXY_CHAIN_PROBES:
        alive, code = http_probe(url)
        result["probes"].append({"label": label, "url": url, "alive": alive, "http_code": code})
        if not alive:
            result["status"] = "FAIL"

    if not result["nginx_service_active"] and result["status"] == "PASS":
        result["status"] = "WARN"

    result["note"] = "nginx error-log scan skipped — /var/log/nginx/error.log needs root, no passwordless sudo available."
    return result


# ── Notify + main ────────────────────────────────────────────────────────

def notify_findings(gw_result: dict, log_result: dict, proxy_result: dict) -> None:
    from core.comms.commander_channel import notify

    if gw_result["status"] == "CONFLICT":
        notify(
            kind="ops",
            title="Sentinel: Telegram gateway CONFLICT — duplicates killed",
            body_md=f"{gw_result['detail']}",
            urgency="NOW",
            reason="Duplicate Telegram gateway processes cause 409 Conflict and can drop C2 messages — money/client-critical channel.",
            dedup_key="sentinel-tg-conflict",
            source="thunderbird_sentinel.py",
        )
    elif gw_result["status"] == "FAIL":
        notify(
            kind="ops", title="Sentinel: Telegram gateway DOWN",
            body_md=gw_result["detail"], urgency="NOW",
            reason="Primary C2 channel appears down.",
            dedup_key="sentinel-tg-down", source="thunderbird_sentinel.py",
        )

    if log_result["hits"]:
        lines = [f"{h['severity']} [{h['service']}]: {h['line'][:200]}" for h in log_result["hits"][:10]]
        notify(
            kind="ops",
            title=f"Sentinel: {len(log_result['hits'])} log pattern hit(s) ({log_result['status']})",
            body_md="\n".join(lines),
            urgency="WINDOW",
            dedup_key=f"sentinel-logscan-{log_result['status']}",
            source="thunderbird_sentinel.py",
        )

    if proxy_result["status"] != "PASS":
        down = [p for p in proxy_result["probes"] if not p["alive"]]
        lines = [f"{p['label']} ({p['url']}) — {p['http_code']}" for p in down]
        if not proxy_result["nginx_service_active"]:
            lines.append("nginx.service not active")
        notify(
            kind="ops",
            title=f"Sentinel: proxy chain {proxy_result['status']}",
            body_md="\n".join(lines) if lines else "degraded",
            urgency="NOW" if proxy_result["status"] == "FAIL" else "WINDOW",
            dedup_key="sentinel-proxy-chain",
            source="thunderbird_sentinel.py",
        )


def run_checks() -> dict:
    state = load_state()
    gw_result = check_telegram_gateway()
    log_result = check_log_patterns()
    proxy_result = check_proxy_chain()

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "telegram_gateway": gw_result,
        "log_patterns": log_result,
        "proxy_chain": proxy_result,
    }

    try:
        notify_findings(gw_result, log_result, proxy_result)
    except Exception as e:
        report["notify_error"] = str(e)

    state["last_run"] = report["ts"]
    save_state(state)
    return report


if __name__ == "__main__":
    report = run_checks()
    print(json.dumps(report, indent=2, default=str))
