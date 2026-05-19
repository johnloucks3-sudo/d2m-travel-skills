#!/usr/bin/env python3
"""
A7 Comms & Infrastructure Health Checker
=========================================
Verifies T1 infrastructure liveness and T2 comms pipeline integrity.

Per SO_STERLING_COMMS_VERIFICATION_PROTOCOL_20260518:
- T1: OAuth timers, tasking watcher, MCP server, Telegram gateway, TESS JWT, OpenCode/JET
- T2: Email reply function, unified classifier, Telegram ConversationBridge, Signal gateway

Anti-theater rule: Every check must be capable of returning FAIL.
A checker that always returns PASS does not check — it rubber-stamps.

Writes results to: OpsCenter/infra_health_log.jsonl (append)
Updates dashboard: OpsCenter/a7_metrics_dashboard.json (comms_verification block)
Writes alerts to: OpsCenter/hale_alerts.log (on failures)
Exit code: 0 if all PASS or WARN, 1 if any FAIL
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/home/john/Thunderbird")
INFRA_HEALTH_LOG = BASE / "OpsCenter" / "infra_health_log.jsonl"
A7_DASHBOARD = BASE / "OpsCenter" / "a7_metrics_dashboard.json"
HALE_ALERTS_LOG = BASE / "OpsCenter" / "hale_alerts.log"
HALE_DECISIONS = BASE / "hale_decisions.md"
COMMS_VERIFY_LOG = BASE / "logs" / "comms_verify.log"
INBOX_WATCHER_LOG = BASE / "logs" / "inbox_watcher.log"
TESS_TOKEN_FILE = BASE / "tess_token.json"
CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"
EMAIL_THREAD_CONTEXT = BASE / "OpsCenter" / "email_thread_context.jsonl"
HALE_CHAT_LOG = BASE / "OpsCenter" / "hale_chat_log.jsonl"
HALE_SIGNAL_LOG = BASE / "OpsCenter" / "hale_signal_log.jsonl"

SIGNAL_CLI_URL = "http://192.168.1.198:8080/v1/about"
MCP_PORT = 8765

NOW_UTC = datetime.now(timezone.utc)
NOW_ISO = NOW_UTC.isoformat()
NOW_TS = NOW_UTC.timestamp()

# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------
def result(system: str, status: str, detail: str) -> dict:
    """Return a standardized check result dict."""
    assert status in ("PASS", "FAIL", "WARN"), f"Invalid status: {status}"
    return {"system": system, "status": status, "detail": detail}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def systemctl_is_active(service: str, user: bool = True) -> bool:
    """Return True if the given systemd service/timer is active."""
    cmd = ["systemctl"]
    if user:
        cmd += ["--user"]
    cmd += ["is-active", "--quiet", service]
    try:
        rc = subprocess.run(cmd, timeout=5).returncode
        return rc == 0
    except Exception:
        return False


def log_mtime_age_seconds(path: Path) -> float:
    """Return seconds since last modification of file. Returns inf if missing."""
    try:
        return NOW_TS - path.stat().st_mtime
    except Exception:
        return float("inf")


def parse_jsonl_lines(path: Path, max_lines: int = None) -> list:
    """Read a JSONL file, return list of parsed dicts. Returns [] on error."""
    lines = []
    try:
        raw = path.read_text()
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                lines.append({"_parse_error": line})
        if max_lines is not None:
            lines = lines[-max_lines:]
    except Exception:
        pass
    return lines


def tcp_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if TCP port accepts a connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# T1 CHECKS — Infrastructure Liveness
# ---------------------------------------------------------------------------

def check_t1_oauth_timers() -> dict:
    """T1-CHECK-1: OAuth token timers active + token not expired."""
    name = "t1_oauth_timers"

    monitor_ok = systemctl_is_active("claude-token-monitor.timer")
    keepalive_ok = systemctl_is_active("claude-oauth-keepalive.timer")

    if not monitor_ok and not keepalive_ok:
        return result(name, "FAIL",
                      "Both claude-token-monitor.timer and claude-oauth-keepalive.timer are inactive. "
                      "Token will expire without refresh.")
    if not monitor_ok:
        return result(name, "FAIL",
                      "claude-token-monitor.timer inactive. Refresh daemon degraded.")
    if not keepalive_ok:
        return result(name, "FAIL",
                      "claude-oauth-keepalive.timer inactive. Keepalive daemon degraded.")

    # Timers active — check credentials file
    if not CREDENTIALS_FILE.exists():
        return result(name, "FAIL",
                      f"Credentials file missing: {CREDENTIALS_FILE}. "
                      "Claude headless will fail auth immediately.")

    try:
        creds = json.loads(CREDENTIALS_FILE.read_text())
        expires_at_ms = creds.get("claudeAiOauth", {}).get("expiresAt")
        if not expires_at_ms:
            return result(name, "WARN",
                          "Credentials file exists but expiresAt field missing. "
                          "Cannot verify token expiry.")
        now_ms = int(NOW_TS * 1000)
        minutes_left = (expires_at_ms - now_ms) / 60000

        if minutes_left <= 0:
            return result(name, "FAIL",
                          f"OAuth token EXPIRED {abs(minutes_left):.0f} min ago. "
                          "Headless Claude will fail auth. Refresh daemon may be stuck.")
        if minutes_left <= 30:
            return result(name, "WARN",
                          f"OAuth token expires in {minutes_left:.0f} min. "
                          "Refresh daemon should pick this up. Monitoring.")

        return result(name, "PASS",
                      f"Both timers active. Token valid for {minutes_left:.0f} min.")

    except Exception as e:
        return result(name, "WARN",
                      f"Credentials file parse error: {e}. Cannot verify token expiry.")


def check_t1_tasking_watcher() -> dict:
    """T1-CHECK-2: Tasking watcher service active + log file current."""
    name = "t1_tasking_watcher"

    if not systemctl_is_active("d2m-tasking-watcher.service"):
        return result(name, "FAIL",
                      "d2m-tasking-watcher.service is not active. "
                      "Autonomous task dispatch is offline. Wing cannot respond to inbox events.")

    if not INBOX_WATCHER_LOG.exists():
        return result(name, "FAIL",
                      f"Watcher log missing: {INBOX_WATCHER_LOG}. "
                      "Service reports active but is not writing — process anomaly.")

    age_s = log_mtime_age_seconds(INBOX_WATCHER_LOG)
    age_min = age_s / 60

    if age_s > 7200:  # 2 hours
        return result(name, "FAIL",
                      f"Watcher log last written {age_min:.0f} min ago. "
                      "Service active but not writing — likely stale PID or silent crash.")

    return result(name, "PASS",
                  f"Service active. Log written {age_min:.0f} min ago.")


def check_t1_mcp_server() -> dict:
    """T1-CHECK-3: MCP server service active + port 8765 accepting connections."""
    name = "t1_mcp_server"

    # NOTE: No /health endpoint exists on this server. TCP connect is the correct probe.
    service_ok = systemctl_is_active("thunderbird-mcp.service")
    port_ok = tcp_port_open("127.0.0.1", MCP_PORT)

    if not service_ok and not port_ok:
        return result(name, "FAIL",
                      f"thunderbird-mcp.service inactive AND port {MCP_PORT} not responding. "
                      "MCP server is down. All 140+ tools unavailable.")
    if not service_ok:
        return result(name, "WARN",
                      f"thunderbird-mcp.service reports inactive but port {MCP_PORT} is open. "
                      "Possible manual start without systemd. Investigate.")
    if not port_ok:
        return result(name, "FAIL",
                      f"thunderbird-mcp.service active but port {MCP_PORT} not accepting connections. "
                      "Service started but listener failed. Restart required.")

    return result(name, "PASS",
                  f"Service active. Port {MCP_PORT} accepting connections.")


def check_t1_telegram_gateway() -> dict:
    """T1-CHECK-4: Telegram gateway service active.
    Bot API liveness is covered in T2 CHECK 3 (L3.5). T1 checks service process only."""
    name = "t1_telegram_gateway"

    if not systemctl_is_active("thunderbird-telegram-gw.service"):
        return result(name, "FAIL",
                      "thunderbird-telegram-gw.service is not active. "
                      "Both D2MC2C and Dani bots are offline. Commander cannot reach wing via Telegram.")

    return result(name, "PASS",
                  "thunderbird-telegram-gw.service active. Gateway process running.")


def check_t1_tess_jwt() -> dict:
    """T1-CHECK-5: TESS JWT token exists and is not obviously expired."""
    name = "t1_tess_jwt"

    if not TESS_TOKEN_FILE.exists():
        return result(name, "FAIL",
                      f"TESS token file missing: {TESS_TOKEN_FILE}. "
                      "TESS auth unavailable. Re-extract JWT from localStorage.")

    try:
        token_data = json.loads(TESS_TOKEN_FILE.read_text())
    except Exception as e:
        return result(name, "FAIL",
                      f"TESS token file parse error: {e}. Token file corrupted.")

    # Try to extract expiry — TESS uses JWT bearer; check exp claim if stored separately
    # Common keys in thunderbird_tess.py token format
    exp = token_data.get("exp") or token_data.get("expires_at") or token_data.get("expiresAt")

    if exp is None:
        # Token file exists but no expiry field — pass with warning
        return result(name, "WARN",
                      "TESS token file present but no expiry field found. "
                      "Cannot verify freshness. Passive check only.")

    # exp may be in seconds or milliseconds
    exp_numeric = float(exp)
    if exp_numeric > 1e12:  # likely milliseconds
        exp_numeric /= 1000

    minutes_left = (exp_numeric - NOW_TS) / 60

    if minutes_left <= 0:
        return result(name, "FAIL",
                      f"TESS token expired {abs(minutes_left):.0f} min ago. "
                      "Re-extract JWT from localStorage via TESS UI.")

    if minutes_left <= 60:
        return result(name, "WARN",
                      f"TESS token expires in {minutes_left:.0f} min. "
                      "Re-extract JWT soon to avoid auth failure mid-session.")

    return result(name, "PASS",
                  f"TESS token valid for {minutes_left:.0f} min.")


def check_t1_opencode_jet() -> dict:
    """T1-CHECK-6: OpenCode supervisor service active + opencode binary running."""
    name = "t1_opencode_jet"

    supervisor_ok = systemctl_is_active("opencode-spsa-monitor.service")

    # Check for opencode process via pgrep
    try:
        pgrep_result = subprocess.run(
            ["pgrep", "-f", "opencode"],
            capture_output=True, text=True, timeout=5
        )
        pids = [p.strip() for p in pgrep_result.stdout.strip().splitlines() if p.strip()]
        process_ok = len(pids) > 0
    except Exception:
        pids = []
        process_ok = False

    if not supervisor_ok and not process_ok:
        return result(name, "FAIL",
                      "opencode-spsa-monitor.service inactive AND no opencode process found. "
                      "JET is offline. Build authority unavailable.")
    if not supervisor_ok:
        return result(name, "WARN",
                      f"Supervisor inactive but opencode process(es) running (PIDs: {pids}). "
                      "OpenCode running unsupervised. Restart supervisor.")
    if not process_ok:
        return result(name, "WARN",
                      "Supervisor active but no opencode binary process found. "
                      "May be idle between tasks — acceptable if recently quiet.")

    return result(name, "PASS",
                  f"Supervisor active. OpenCode process running (PIDs: {pids}).")


# ---------------------------------------------------------------------------
# T2 CHECKS — Comms Pipeline Integrity
# ---------------------------------------------------------------------------

def check_t2_email_reply() -> dict:
    """CHECK 1 — Email Thread Reply.
    Liveness: gmail_reply_in_thread importable, TOOL_REGISTRY entry present,
    email_thread_context.jsonl exists and is valid JSONL with correct schema.
    """
    name = "email_reply"
    failures = []

    # L1.1 — Function importable
    # NOTE: Actual function is gmail_reply_in_thread, not gmail_thread_reply
    # (see SO naming discrepancy note in protocol SO)
    try:
        sys.path.insert(0, str(BASE))
        from core.email.thunderbird_gmail import gmail_reply_in_thread  # noqa: F401
    except ImportError as e:
        failures.append(f"L1.1 FAIL: gmail_reply_in_thread not importable: {e}")

    # L1.2 — TOOL_REGISTRY check
    try:
        from core.email.thunderbird_gmail import TOOL_REGISTRY
        if "gmail_reply_in_thread" not in TOOL_REGISTRY:
            failures.append("L1.2 FAIL: gmail_reply_in_thread not in TOOL_REGISTRY")
    except ImportError:
        failures.append("L1.2 FAIL: TOOL_REGISTRY not importable from thunderbird_gmail")
    except Exception as e:
        failures.append(f"L1.2 WARN: TOOL_REGISTRY check error: {e}")

    # L1.3 — Context file exists
    if not EMAIL_THREAD_CONTEXT.exists():
        failures.append(f"L1.3 FAIL: {EMAIL_THREAD_CONTEXT} does not exist. "
                        "T2 email reply build step not complete.")
    else:
        # L1.4 — Valid JSONL
        lines = parse_jsonl_lines(EMAIL_THREAD_CONTEXT)
        parse_errors = [l for l in lines if "_parse_error" in l]
        if parse_errors:
            failures.append(f"L1.4 FAIL: {len(parse_errors)} JSONL parse errors in email_thread_context.jsonl")
        else:
            # L1.5 — Schema compliance
            schema_violations = []
            for i, entry in enumerate(lines):
                if "_parse_error" in entry:
                    continue
                missing = [k for k in ("thread_id", "message_id") if k not in entry]
                if missing:
                    schema_violations.append(f"entry {i} missing: {missing}")
            if schema_violations:
                failures.append(f"L1.5 FAIL: Schema violations: {schema_violations[:3]}")

        # Activity checks (only when entries exist)
        if lines and not parse_errors:
            recent = [l for l in lines[-50:] if "_parse_error" not in l]
            if recent:
                # A1.1 — first_reply field
                missing_first_reply = [l for l in recent if "first_reply" not in l]
                if missing_first_reply:
                    failures.append(f"A1.1 FAIL: {len(missing_first_reply)} entries missing 'first_reply' field")
                # A1.2 — reply_latency_seconds
                missing_latency = [l for l in recent if "reply_latency_seconds" not in l]
                if missing_latency:
                    failures.append(f"A1.2 FAIL: {len(missing_latency)} entries missing 'reply_latency_seconds'")
                # A1.3 — No error entries
                error_entries = [l for l in recent if "error" in l]
                if error_entries:
                    failures.append(f"A1.3 FAIL: {len(error_entries)} entries with 'error' key in last 50")

    if failures:
        return result(name, "FAIL", " | ".join(failures))
    return result(name, "PASS", "gmail_reply_in_thread importable, TOOL_REGISTRY registered, context file valid.")


def check_t2_unified_classifier() -> dict:
    """CHECK 2 — Unified Classifier.
    Liveness: module importable, classify_message callable, schema + enum compliance,
    override field detection.
    """
    name = "unified_classifier"
    failures = []

    # L2.1 — Module importable
    try:
        from core.comms.hale_unified_classifier import classify_message  # noqa: F401
    except ImportError as e:
        failures.append(f"L2.1 FAIL: hale_unified_classifier not importable: {e}. "
                        "T2 build step 2 not complete.")
        return result(name, "FAIL", " | ".join(failures))

    # L2.2 — Function callable
    try:
        test_result = classify_message("Hale, status?", "telegram", "commander")
    except Exception as e:
        failures.append(f"L2.2 FAIL: classify_message raised exception: {e}")
        return result(name, "FAIL", " | ".join(failures))

    # L2.3 — Return schema complete
    required_keys = {"intent", "brain", "persona", "format", "priority", "override"}
    missing_keys = required_keys - set(test_result.keys())
    if missing_keys:
        failures.append(f"L2.3 FAIL: Missing keys in result: {missing_keys}")

    # L2.4 — Enum compliance
    allowed = {
        "intent": {"task", "chat", "intel", "client", "urgent", "clarification"},
        "brain": {"haiku", "sonnet", "opus", "self"},
        "persona": {"hale", "dani"},
        "format": {"tq_talking", "tq_background", "plain", "stationery", "informal"},
        "priority": {"P0", "P1", "P2", "P3"},
    }
    for field, valid_set in allowed.items():
        val = test_result.get(field)
        if val is not None and val not in valid_set:
            failures.append(f"L2.4 FAIL: {field}='{val}' not in allowed set {valid_set}")

    # L2.5 — Override field detection
    try:
        override_test = classify_message("OPUS: analyze this", "telegram", "commander")
        if override_test.get("override") != "opus":
            failures.append(f"L2.5 FAIL: OPUS prefix not detected. override='{override_test.get('override')}' (expected 'opus')")
    except Exception as e:
        failures.append(f"L2.5 FAIL: Override test raised exception: {e}")

    if failures:
        return result(name, "FAIL", " | ".join(failures))
    return result(name, "PASS", "Module importable, callable, schema valid, enums compliant, override detected.")


def check_t2_telegram_bridge() -> dict:
    """CHECK 3 — Telegram ConversationBridge.
    Liveness: hale_chat_log.jsonl exists, valid JSONL, schema correct.
    Bot liveness via Telegram getMe API.
    Activity: XML/ANSI artifact scan, window size check, text length.
    """
    import os
    name = "telegram_bridge"
    failures = []

    # L3.1 — Chat log exists
    if not HALE_CHAT_LOG.exists():
        failures.append(f"L3.1 FAIL: {HALE_CHAT_LOG} does not exist")
        return result(name, "FAIL", " | ".join(failures))

    # L3.2 — Valid JSONL
    lines = parse_jsonl_lines(HALE_CHAT_LOG)
    parse_errors = [l for l in lines if "_parse_error" in l]
    if parse_errors:
        failures.append(f"L3.2 FAIL: {len(parse_errors)} JSONL parse errors in hale_chat_log.jsonl")

    # L3.3 — Schema compliance
    if not parse_errors:
        schema_violations = []
        for i, entry in enumerate(lines):
            if "_parse_error" in entry:
                continue
            missing = [k for k in ("ts", "chat_id", "role", "text") if k not in entry]
            if missing:
                schema_violations.append(f"entry {i} missing: {missing}")
        if schema_violations:
            failures.append(f"L3.3 FAIL: {len(schema_violations)} schema violations (first: {schema_violations[0]})")

    # L3.4 — Role enum valid
    if not parse_errors:
        valid_roles = {"commander", "hale"}
        invalid_roles = [l for l in lines if "_parse_error" not in l
                         and l.get("role") not in valid_roles]
        if invalid_roles:
            failures.append(f"L3.4 FAIL: {len(invalid_roles)} entries with invalid role value")

    # L3.5 — Telegram bot alive (API call)
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("D2MC2C_BOT_TOKEN")
    if not telegram_token:
        # Try reading from known config locations
        bot_config = BASE / "OpsCenter" / "thunderbird_telegram_gw.py"
        if bot_config.exists():
            content = bot_config.read_text()
            m = re.search(r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                telegram_token = m.group(1)

    if telegram_token:
        try:
            import urllib.request
            url = f"https://api.telegram.org/bot{telegram_token}/getMe"
            req = urllib.request.Request(url, headers={"User-Agent": "ThunderbirdA7/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if not data.get("ok"):
                    failures.append(f"L3.5 FAIL: Telegram getMe returned ok=false: {data}")
        except Exception as e:
            failures.append(f"L3.5 FAIL: Telegram bot API call failed: {e}")
    else:
        failures.append("L3.5 WARN: TELEGRAM_BOT_TOKEN not found in environment or gateway file. "
                        "Skipping live bot check. Treat as WARN.")

    # Activity checks (last 50 entries when data exists)
    if lines and not parse_errors:
        recent = [l for l in lines[-50:] if "_parse_error" not in l]
        if recent:
            # A3.1 — XML artifact scan
            xml_re = re.compile(r"\[/?[a-z_:]+\]")
            xml_hits = [l for l in recent if xml_re.search(l.get("text", ""))]
            if xml_hits:
                failures.append(f"A3.1 FAIL: {len(xml_hits)} entries with XML artifacts in last 50")

            # A3.2 — ANSI artifact scan
            ansi_re = re.compile(r"\x1b\[[0-9;]*m")
            ansi_hits = [l for l in recent if ansi_re.search(l.get("text", ""))]
            if ansi_hits:
                failures.append(f"A3.2 FAIL: {len(ansi_hits)} entries with ANSI codes in last 50")

            # A3.3 — ConversationBridge window (per chat_id)
            from collections import Counter
            chat_id_counts = Counter(l.get("chat_id") for l in recent if "chat_id" in l)
            overflowing = {cid: cnt for cid, cnt in chat_id_counts.items() if cnt > 20}
            if overflowing:
                failures.append(f"A3.3 FAIL: chat_id(s) with >20 entries in last 50: {overflowing}")

            # A3.4 — Text length compliance
            long_texts = [l for l in recent if len(l.get("text", "")) > 4096]
            if long_texts:
                failures.append(f"A3.4 FAIL: {len(long_texts)} entries with text >4096 chars (chunking bypassed)")

    if failures:
        # Separate WARNs from FAILs for status determination
        real_fails = [f for f in failures if not f.startswith("L3.5 WARN")]
        if not real_fails:
            return result(name, "WARN", " | ".join(failures))
        return result(name, "FAIL", " | ".join(failures))

    return result(name, "PASS", "Chat log valid, schema compliant, no artifacts detected.")


def check_t2_signal_gateway() -> dict:
    """CHECK 4 — Signal Gateway.
    Liveness: signal-cli container at YOGA:8080, SignalGateway importable,
    hale_signal_log.jsonl exists and valid, systemd service on YOGA (SSH).
    """
    name = "signal_gateway"
    failures = []

    # L4.1 — signal-cli container responding
    try:
        import urllib.request
        req = urllib.request.Request(
            SIGNAL_CLI_URL,
            headers={"User-Agent": "ThunderbirdA7/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                failures.append(f"L4.1 FAIL: signal-cli /v1/about returned HTTP {resp.status}")
    except Exception as e:
        failures.append(f"L4.1 FAIL: signal-cli container at {SIGNAL_CLI_URL} not responding: {e}. "
                        "YOGA signal-cli container may be down or YOGA unreachable.")

    # L4.2 — Gateway module importable
    try:
        from core.comms.thunderbird_signal_gw import SignalGateway  # noqa: F401
    except ImportError as e:
        failures.append(f"L4.2 FAIL: thunderbird_signal_gw not importable: {e}. "
                        "T2 build step 4 not complete.")

    # L4.3 — Signal log exists
    if not HALE_SIGNAL_LOG.exists():
        failures.append(f"L4.3 FAIL: {HALE_SIGNAL_LOG} does not exist. "
                        "Signal gateway has never written a log entry. T2 step 4 not complete.")
    else:
        # L4.4 — Valid JSONL
        lines = parse_jsonl_lines(HALE_SIGNAL_LOG)
        parse_errors = [l for l in lines if "_parse_error" in l]
        if parse_errors:
            failures.append(f"L4.4 FAIL: {len(parse_errors)} JSONL parse errors in hale_signal_log.jsonl")
        else:
            # L4.5 — Schema compliance
            schema_violations = []
            for i, entry in enumerate(lines):
                if "_parse_error" in entry:
                    continue
                missing = [k for k in ("ts", "sender", "direction", "text") if k not in entry]
                if missing:
                    schema_violations.append(f"entry {i}: {missing}")
            if schema_violations:
                failures.append(f"L4.5 FAIL: {len(schema_violations)} schema violations")

            # Activity checks
            if lines and not parse_errors:
                recent = [l for l in lines[-50:] if "_parse_error" not in l]
                if recent:
                    # A4.1 — Direction enum
                    valid_dirs = {"inbound", "outbound"}
                    bad_dirs = [l for l in recent if l.get("direction") not in valid_dirs]
                    if bad_dirs:
                        failures.append(f"A4.1 FAIL: {len(bad_dirs)} entries with invalid direction value")

                    # A4.2 — No error entries
                    error_entries = [l for l in recent if "error" in l]
                    if error_entries:
                        failures.append(f"A4.2 FAIL: {len(error_entries)} entries with 'error' key in last 50")

                    # A4.3 — Outbound paired with inbound
                    inbound = [l for l in recent if l.get("direction") == "inbound"]
                    for ib in inbound:
                        try:
                            ib_ts = datetime.fromisoformat(ib.get("ts", "")).timestamp()
                        except Exception:
                            continue
                        # Look for outbound within 3 minutes
                        paired = any(
                            l.get("direction") == "outbound"
                            and abs(
                                datetime.fromisoformat(l.get("ts", "1970-01-01")).timestamp()
                                - ib_ts
                            ) <= 180
                            for l in recent
                        )
                        if not paired and (NOW_TS - ib_ts) > 180:
                            failures.append(f"A4.3 FAIL: Unpaired inbound message at {ib.get('ts')} "
                                            "(no outbound response within 3 min)")
                            break  # Report first unpaired only

    # L4.6 — systemd service on YOGA (SSH check)
    # SSH to YOGA is a live probe — attempt but treat failure as WARN if SSH is unavailable
    try:
        ssh_result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             "john@192.168.1.198",
             "systemctl is-active thunderbird-signal-gw.service"],
            capture_output=True, text=True, timeout=10
        )
        if ssh_result.returncode != 0:
            yoga_status = ssh_result.stdout.strip() or "unknown"
            failures.append(f"L4.6 FAIL: thunderbird-signal-gw.service on YOGA reports: '{yoga_status}'")
    except subprocess.TimeoutExpired:
        failures.append("L4.6 WARN: SSH to YOGA timed out. Cannot verify signal gateway service on YOGA.")
    except Exception as e:
        failures.append(f"L4.6 WARN: SSH to YOGA failed: {e}. Cannot verify signal service remotely.")

    if failures:
        real_fails = [f for f in failures if "WARN" not in f]
        if not real_fails:
            return result(name, "WARN", " | ".join(failures))
        return result(name, "FAIL", " | ".join(failures))

    return result(name, "PASS", "Signal CLI responding, module importable, log valid, service active on YOGA.")


# ---------------------------------------------------------------------------
# Dashboard + Log Writers
# ---------------------------------------------------------------------------

def load_dashboard() -> dict:
    """Load existing dashboard JSON or return empty dict."""
    if A7_DASHBOARD.exists():
        try:
            return json.loads(A7_DASHBOARD.read_text())
        except Exception:
            return {}
    return {}


def save_dashboard(data: dict) -> None:
    """Write dashboard JSON."""
    A7_DASHBOARD.write_text(json.dumps(data, indent=2))


def write_health_log(run_record: dict) -> None:
    """Append run record to infra_health_log.jsonl."""
    INFRA_HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(INFRA_HEALTH_LOG, "a") as f:
        f.write(json.dumps(run_record) + "\n")


def write_alert(message: str) -> None:
    """Append alert to hale_alerts.log."""
    HALE_ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HALE_ALERTS_LOG, "a") as f:
        f.write(f"[{NOW_ISO}] A7 COMMS CHECKER: {message}\n")


def compute_14d_pass_rate() -> float:
    """Compute T2 pass rate over rolling 14-day window from infra_health_log.jsonl."""
    if not INFRA_HEALTH_LOG.exists():
        return 0.0
    cutoff_ts = NOW_TS - (14 * 86400)
    total = 0
    passed = 0
    try:
        for line in INFRA_HEALTH_LOG.read_text().strip().splitlines():
            try:
                rec = json.loads(line)
                run_ts = datetime.fromisoformat(rec.get("timestamp", "1970-01-01")).timestamp()
                if run_ts < cutoff_ts:
                    continue
                total += 1
                if rec.get("t2_status") == "GREEN":
                    passed += 1
            except Exception:
                continue
    except Exception:
        return 0.0
    return round((passed / total * 100), 1) if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------

def run_all_checks() -> int:
    """Run all T1 and T2 checks. Returns exit code (0=all OK, 1=any FAIL)."""
    print(f"[{NOW_ISO}] A7 Comms Health Check starting")

    # --- Run T1 checks ---
    t1_results = [
        check_t1_oauth_timers(),
        check_t1_tasking_watcher(),
        check_t1_mcp_server(),
        check_t1_telegram_gateway(),
        check_t1_tess_jwt(),
        check_t1_opencode_jet(),
    ]

    # --- Run T2 checks ---
    t2_results = [
        check_t2_email_reply(),
        check_t2_unified_classifier(),
        check_t2_telegram_bridge(),
        check_t2_signal_gateway(),
    ]

    all_results = t1_results + t2_results

    # --- Compute statuses ---
    def component_status(res: dict) -> str:
        return "GREEN" if res["status"] in ("PASS", "WARN") else "RED"

    t1_component_statuses = {r["system"]: component_status(r) for r in t1_results}
    t2_component_statuses = {r["system"]: component_status(r) for r in t2_results}

    t1_red_count = sum(1 for v in t1_component_statuses.values() if v == "RED")
    t2_red_count = sum(1 for v in t2_component_statuses.values() if v == "RED")

    # T1 system status
    if t1_red_count == 0:
        t1_status = "GREEN"
    elif t1_red_count == 1:
        t1_status = "YELLOW"
    else:
        t1_status = "RED"

    # T2 system status
    if t2_red_count == 0:
        t2_status = "GREEN"
    elif t2_red_count == 1:
        t2_status = "YELLOW"
    else:
        t2_status = "RED"

    # Overall status
    overall_failures = [r for r in all_results if r["status"] == "FAIL"]
    overall_warns = [r for r in all_results if r["status"] == "WARN"]

    if t1_red_count + t2_red_count >= 2:
        system_status = "RED"
    elif t1_red_count + t2_red_count == 1:
        system_status = "YELLOW"
    else:
        system_status = "GREEN"

    # --- Print results ---
    print(f"\n{'='*60}")
    print(f"T1 INFRASTRUCTURE: {t1_status}")
    for r in t1_results:
        marker = "PASS" if r["status"] in ("PASS", "WARN") else "FAIL"
        print(f"  [{marker}] {r['system']}: {r['detail']}")

    print(f"\nT2 COMMS PIPELINE: {t2_status}")
    for r in t2_results:
        marker = "PASS" if r["status"] in ("PASS", "WARN") else "FAIL"
        print(f"  [{marker}] {r['system']}: {r['detail']}")

    print(f"\nOVERALL: {system_status}")
    print(f"{'='*60}\n")

    # --- Load dashboard + compute 14d rate ---
    dashboard = load_dashboard()
    pass_rate_14d = compute_14d_pass_rate()

    # Determine graduation eligibility (simple heuristic — full graduation logic requires
    # consulting consecutive_green_days from log history; this is a placeholder)
    existing_infra = dashboard.get("infra_verification", {})
    consecutive_green = existing_infra.get("consecutive_green_days", 0)
    if system_status == "GREEN":
        consecutive_green = consecutive_green  # Will be incremented by daily rollup
    else:
        consecutive_green = 0  # Reset on any non-green

    graduation_eligible = (
        pass_rate_14d >= 98.0
        and consecutive_green >= 14
    )

    # --- Build run record ---
    run_record = {
        "timestamp": NOW_ISO,
        "t1_status": t1_status,
        "t2_status": t2_status,
        "system_status": system_status,
        "t1_components": t1_component_statuses,
        "t2_components": t2_component_statuses,
        "failures": [r for r in all_results if r["status"] == "FAIL"],
        "warnings": [r for r in all_results if r["status"] == "WARN"],
        "t2_pass_rate_14d": pass_rate_14d,
        "consecutive_green_days": consecutive_green,
        "graduation_eligible": graduation_eligible,
    }

    # --- Write health log ---
    write_health_log(run_record)

    # --- Update dashboard ---
    dashboard["infra_verification"] = {
        "last_run": NOW_ISO,
        "t1_status": t1_status,
        "t2_status": t2_status,
        "system_status": system_status,
        "consecutive_green_days": consecutive_green,
        "graduation_eligible": graduation_eligible,
        "t1_components": t1_component_statuses,
        "t2_components": t2_component_statuses,
        "failures_this_run": [
            {"system": r["system"], "detail": r["detail"]}
            for r in overall_failures
        ],
        "warnings_this_run": [
            {"system": r["system"], "detail": r["detail"]}
            for r in overall_warns
        ],
        "hourly_pass_rate_14d": pass_rate_14d,
    }
    save_dashboard(dashboard)
    print(f"Dashboard updated: {A7_DASHBOARD}")
    print(f"Health log appended: {INFRA_HEALTH_LOG}")

    # --- Alerts ---
    if overall_failures:
        failure_summary = "; ".join(f"{r['system']}({r['detail'][:60]})" for r in overall_failures)
        alert_msg = f"[{system_status}] {len(overall_failures)} FAIL(s): {failure_summary}"
        write_alert(alert_msg)
        print(f"Alert written to: {HALE_ALERTS_LOG}")

    # --- Exit code ---
    has_fail = any(r["status"] == "FAIL" for r in all_results)
    exit_code = 1 if has_fail else 0
    print(f"Exit code: {exit_code} ({'FAIL' if exit_code else 'PASS/WARN'})")
    return exit_code


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(run_all_checks())
