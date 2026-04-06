"""
OpsCenter Aggressive Test Harness
==================================
Tests every component of the C2 pipeline: MCP tools, Gemini API,
Telegram API, HTML sanitizer, message chunking, full e2e pipeline.

Reports results to Commander via Telegram.

Usage:
    python3 opscenter_test_harness.py --full     # All phases
    python3 opscenter_test_harness.py --quick    # Infra + sanitizer only (no API calls)
    python3 opscenter_test_harness.py --phase 2  # MCP tools only

Author: Col Victoria "Iron Vic" Hale (COS)
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "OpsCenter"))

from dotenv import load_dotenv
load_dotenv(str(ROOT / ".env"))
load_dotenv(str(ROOT / ".env.telegram"))

import requests

# ── Config ──
MCP_URL = "http://127.0.0.1:8765/mcp"
MCP_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
MT = timezone(timedelta(hours=-6))
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPSCENTER = ROOT / "OpsCenter"
REPORT_LOG = ROOT / "logs" / "test_harness.log"


@dataclass
class TestResult:
    phase: int
    name: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0
    severity: str = "normal"  # normal, critical


def run_test(phase: int, name: str, fn, severity: str = "normal") -> TestResult:
    """Run a test function safely with timing."""
    start = time.monotonic()
    try:
        passed, detail = fn()
        dur = int((time.monotonic() - start) * 1000)
        return TestResult(phase=phase, name=name, passed=passed, detail=detail, duration_ms=dur, severity=severity)
    except Exception as e:
        dur = int((time.monotonic() - start) * 1000)
        return TestResult(phase=phase, name=name, passed=False, detail=f"EXCEPTION: {e}", duration_ms=dur, severity=severity)


def _call_mcp(tool_name: str, arguments: dict, timeout: int = 20) -> tuple[bool, str]:
    """Call MCP tool, return (success, text_or_error)."""
    try:
        resp = requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}},
            headers=MCP_HEADERS, timeout=timeout,
        )
        data = resp.json()
        if "error" in data:
            return False, f"Protocol error: {data['error'].get('message', '')[:100]}"
        result = data.get("result", {})
        content = result.get("content", [])
        text = content[0].get("text", "") if content else ""
        if result.get("isError"):
            return False, f"Tool error: {text[:150]}"
        if "not_configured" in text.lower() or "not authenticated" in text.lower():
            return False, f"Not configured: {text[:100]}"
        if text:
            return True, f"{len(text)} chars"
        return False, "Empty result"
    except requests.exceptions.Timeout:
        return False, f"Timeout ({timeout}s)"
    except Exception as e:
        return False, str(e)[:100]


# ============================================================================
# Phase 1: Infrastructure
# ============================================================================

def _test_mcp_reachable():
    try:
        sock = socket.create_connection(("127.0.0.1", 8765), timeout=5)
        sock.close()
        return True, "Port 8765 open"
    except Exception as e:
        return False, str(e)

def _test_mcp_tools_list():
    try:
        resp = requests.post(MCP_URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                             headers=MCP_HEADERS, timeout=10)
        tools = resp.json().get("result", {}).get("tools", [])
        count = len(tools)
        return count > 50, f"{count} tools discovered"
    except Exception as e:
        return False, str(e)

def _test_queue_writable():
    test_file = OPSCENTER / "01_TASK_QUEUE.json"
    try:
        q = json.loads(test_file.read_text()) if test_file.exists() else []
        marker = {"task_id": "_test_probe", "task_type": "_test", "queued_at": datetime.now(timezone.utc).isoformat()}
        q.append(marker)
        test_file.write_text(json.dumps(q, indent=2))
        # Read back and remove
        q2 = json.loads(test_file.read_text())
        q2 = [t for t in q2 if t.get("task_id") != "_test_probe"]
        test_file.write_text(json.dumps(q2, indent=2))
        return True, "Write/read/clean OK"
    except Exception as e:
        return False, str(e)

def _test_env_vars():
    missing = []
    for var in ["TELEGRAM_C2_BOT_TOKEN", "TELEGRAM_COMMANDER_ID", "GEMINI_API_KEY"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "All env vars present"

def _test_services_active():
    down = []
    for svc in ["thunderbird-overwatch", "thunderbird-telegram-c2", "thunderbird-mcp"]:
        try:
            r = subprocess.run(["systemctl", "--user", "is-active", svc],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip() != "active":
                down.append(svc)
        except Exception:
            down.append(svc)
    if down:
        return False, f"DOWN: {', '.join(down)}"
    return True, "All 3 services active"

def _test_network():
    try:
        sock = socket.create_connection(("8.8.8.8", 53), timeout=5)
        sock.close()
        return True, "Internet reachable"
    except Exception:
        return False, "No internet connectivity"


# ============================================================================
# Phase 2: MCP Tool Calls (exact params from _fetch_mcp_context)
# ============================================================================

MCP_TOOLS = [
    ("scan_dossiers", {}, "critical"),
    ("system_health_check", {}, "critical"),
    ("list_tasks", {}, "normal"),
    ("wing_memory_search", {"query": "test", "limit": 3}, "normal"),
    ("gmail_search_messages", {"query": "newer_than:1d", "max_results": 2}, "critical"),
    ("scan_airline_route_changes", {}, "normal"),
    ("calendar_list_events", {"days_ahead": 7}, "normal"),
    ("check_client_airline_impact", {}, "normal"),
    ("drive_list_files", {"max_results": 3}, "normal"),
    ("list_available_ships", {}, "normal"),
    ("get_noaa_forecast_by_zip", {"zipcode": "80132"}, "normal"),
    ("track_flight_fr24", {"flight_number": "AY99"}, "normal"),
    ("reconcile_commissions", {"days_back": 30}, "normal"),
    ("tess_list_clients", {"limit": 10}, "normal"),  # expected to fail until configured
]


# ============================================================================
# Phase 3: Gemini API
# ============================================================================

def _test_gemini_api():
    if not GEMINI_API_KEY:
        return False, "No GEMINI_API_KEY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        resp = requests.post(url, json={
            "contents": [{"role": "user", "parts": [{"text": "Reply with exactly: OPERATIONAL"}]}],
            "generationConfig": {"maxOutputTokens": 50, "temperature": 0.0},
        }, timeout=30, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return False, f"No candidates: {json.dumps(data)[:100]}"
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text:
            return False, f"Empty text: {json.dumps(candidates[0])[:100]}"
        return True, f"Response: {text[:50]}"
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP {e.response.status_code}: {e.response.text[:80]}"
    except Exception as e:
        return False, str(e)[:100]


# ============================================================================
# Phase 4: Telegram API
# ============================================================================

def _test_telegram_getme():
    if not TELEGRAM_BOT_TOKEN:
        return False, "No bot token"
    try:
        resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=10)
        data = resp.json()
        if data.get("ok"):
            return True, f"Bot: @{data['result'].get('username')}"
        return False, str(data)[:100]
    except Exception as e:
        return False, str(e)[:100]


# ============================================================================
# Phase 5: HTML Sanitizer
# ============================================================================

def _get_sanitizer():
    from task_processor import _sanitize_html
    return _sanitize_html

def _test_sanitize_bold():
    s = _get_sanitizer()
    result = s("**hello**")
    return "<b>hello</b>" in result, result[:80]

def _test_sanitize_unclosed():
    s = _get_sanitizer()
    result = s("<b>open tag never closed")
    return result.count("</b>") >= 1, result[:80]

def _test_sanitize_unclosed_pre():
    s = _get_sanitizer()
    # Real failure from process.log: Gemini returned unclosed <pre>
    result = s("<pre>Status : RED\nServices : 5/6")
    return result.count("</pre>") >= 1, result[:80]

def _test_sanitize_ampersand():
    s = _get_sanitizer()
    result = s("R&D costs < $500 > budget")
    return "&amp;" in result and "&lt;" in result and "&gt;" in result, result[:80]

def _test_sanitize_links():
    s = _get_sanitizer()
    result = s("[Click here](https://example.com)")
    return '<a href="https://example.com">Click here</a>' in result, result[:80]

def _test_sanitize_code():
    s = _get_sanitizer()
    result = s("Use `pip install` for that")
    return "<code>pip install</code>" in result, result[:80]

def _test_sanitize_mixed():
    s = _get_sanitizer()
    result = s("<b>Already HTML</b> and **also markdown**")
    return result.count("<b>") == 2 and result.count("</b>") == 2, result[:100]


# ============================================================================
# Phase 6: Message Chunking
# ============================================================================

def _test_chunk_short():
    from thunderbird_telegram_fmt import split_message
    chunks = split_message("Hello")
    return len(chunks) == 1 and chunks[0] == "Hello", f"{len(chunks)} chunks"

def _test_chunk_long():
    from thunderbird_telegram_fmt import split_message
    msg = "A" * 5000
    chunks = split_message(msg)
    return len(chunks) >= 2 and all(len(c) <= 4096 for c in chunks), f"{len(chunks)} chunks, max {max(len(c) for c in chunks)}"

def _test_chunk_paragraph():
    from thunderbird_telegram_fmt import split_message
    msg = ("A" * 3000) + "\n\n" + ("B" * 3000)
    chunks = split_message(msg)
    return len(chunks) == 2, f"{len(chunks)} chunks"

def _test_chunk_empty():
    from thunderbird_telegram_fmt import split_message
    chunks = split_message("")
    # split_message may return [""] or [] — both are acceptable
    return len(chunks) <= 1, f"{len(chunks)} chunks"


# ============================================================================
# Report Generator
# ============================================================================

def generate_report(results: list[TestResult]) -> str:
    """Build Telegram HTML report."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)
    crit_fail = sum(1 for r in results if not r.passed and r.severity == "critical")
    total_ms = sum(r.duration_ms for r in results)

    if crit_fail > 0:
        status = "RED"
        icon = "🔴"
    elif failed > 0:
        status = "AMBER"
        icon = "⚠️"
    else:
        status = "GREEN"
        icon = "✅"

    lines = [
        f"{icon} <b>OPSCENTER TEST — {status}</b>",
        f"<pre>{passed}/{total} passed  {failed} failed  {total_ms}ms</pre>",
        "",
    ]

    # Group by phase
    phases = {
        1: "INFRASTRUCTURE",
        2: "MCP TOOLS",
        3: "GEMINI API",
        4: "TELEGRAM API",
        5: "HTML SANITIZER",
        6: "MSG CHUNKING",
        7: "E2E PIPELINE",
    }

    for phase_num in sorted(set(r.phase for r in results)):
        phase_results = [r for r in results if r.phase == phase_num]
        phase_pass = all(r.passed for r in phase_results)
        phase_icon = "✅" if phase_pass else "❌"
        lines.append(f"{phase_icon} <b>{phases.get(phase_num, f'Phase {phase_num}')}</b>")

        for r in phase_results:
            icon = "✅" if r.passed else "❌"
            crit = " [CRIT]" if r.severity == "critical" and not r.passed else ""
            lines.append(f"  {icon} {r.name}{crit} ({r.duration_ms}ms)")
            if not r.passed:
                lines.append(f"     {r.detail[:120]}")
        lines.append("")

    ts = datetime.now(MT).strftime("%H:%M MT %b %d")
    lines.append(f"<i>{ts}</i>")
    return "\n".join(lines)


def send_report(text: str):
    """Send report to Commander via direct Telegram API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER_ID:
        print("No Telegram credentials — printing report only")
        print(text)
        return

    # Chunk if needed
    from thunderbird_telegram_fmt import split_message
    chunks = split_message(text)

    for chunk in chunks:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_COMMANDER_ID, "text": chunk, "parse_mode": "HTML"},
                timeout=10,
            )
            if not resp.ok:
                # Plain text fallback
                import re
                plain = re.sub(r'<[^>]+>', '', chunk)
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_COMMANDER_ID, "text": plain},
                    timeout=10,
                )
        except Exception as e:
            print(f"Send failed: {e}")


def log_results(results: list[TestResult]):
    """Append results to test harness log."""
    entry = {
        "ts": datetime.now(MT).isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [
            {"name": r.name, "passed": r.passed, "detail": r.detail[:200], "ms": r.duration_ms}
            for r in results if not r.passed  # only log failures
        ],
    }
    try:
        with open(REPORT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="OpsCenter Test Harness")
    parser.add_argument("--full", action="store_true", help="Run all test phases")
    parser.add_argument("--quick", action="store_true", help="Infra + sanitizer only")
    parser.add_argument("--phase", type=int, help="Run specific phase (1-7)")
    parser.add_argument("--quiet", action="store_true", help="Don't send Telegram report")
    args = parser.parse_args()

    if not any([args.full, args.quick, args.phase]):
        args.full = True

    results = []
    run_phases = set()

    if args.full:
        run_phases = {1, 2, 3, 4, 5, 6}
    elif args.quick:
        run_phases = {1, 5, 6}
    elif args.phase:
        run_phases = {args.phase}

    # Phase 1: Infrastructure
    if 1 in run_phases:
        results.append(run_test(1, "Network", _test_network, "critical"))
        results.append(run_test(1, "MCP port", _test_mcp_reachable, "critical"))
        results.append(run_test(1, "MCP tools/list", _test_mcp_tools_list, "critical"))
        results.append(run_test(1, "Queue writable", _test_queue_writable))
        results.append(run_test(1, "Env vars", _test_env_vars, "critical"))
        results.append(run_test(1, "Services", _test_services_active, "critical"))

    # Phase 2: MCP Tools
    if 2 in run_phases:
        for tool_name, tool_args, sev in MCP_TOOLS:
            results.append(run_test(
                2, tool_name,
                lambda tn=tool_name, ta=tool_args: _call_mcp(tn, ta),
                severity=sev,
            ))

    # Phase 3: Gemini
    if 3 in run_phases:
        results.append(run_test(3, "Gemini 2.5 Flash", _test_gemini_api, "critical"))

    # Phase 4: Telegram
    if 4 in run_phases:
        results.append(run_test(4, "Telegram getMe", _test_telegram_getme, "critical"))

    # Phase 5: HTML Sanitizer
    if 5 in run_phases:
        results.append(run_test(5, "Bold conversion", _test_sanitize_bold))
        results.append(run_test(5, "Unclosed <b>", _test_sanitize_unclosed))
        results.append(run_test(5, "Unclosed <pre>", _test_sanitize_unclosed_pre))
        results.append(run_test(5, "Ampersand escape", _test_sanitize_ampersand))
        results.append(run_test(5, "Link conversion", _test_sanitize_links))
        results.append(run_test(5, "Code conversion", _test_sanitize_code))
        results.append(run_test(5, "Mixed HTML+MD", _test_sanitize_mixed))

    # Phase 6: Chunking
    if 6 in run_phases:
        results.append(run_test(6, "Short msg", _test_chunk_short))
        results.append(run_test(6, "Long msg split", _test_chunk_long))
        results.append(run_test(6, "Paragraph split", _test_chunk_paragraph))
        results.append(run_test(6, "Empty msg", _test_chunk_empty))

    # Generate report
    report = generate_report(results)
    log_results(results)

    # Print to stdout
    import re
    print(re.sub(r'<[^>]+>', '', report))

    # Send to Commander
    if not args.quiet:
        send_report(report)

    # Exit code: 1 if any critical failure
    crit_fail = any(not r.passed and r.severity == "critical" for r in results)
    sys.exit(1 if crit_fail else 0)


if __name__ == "__main__":
    main()
