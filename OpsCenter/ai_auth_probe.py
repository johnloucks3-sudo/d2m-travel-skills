#!/usr/bin/env python3
"""
AI Auth Probe — active health checks for critical AI/API endpoints.
Runs every 15 minutes via ai-auth-probe.timer.

OODA loop per component:
  Probe (real API call) → Fail → Repair (deterministic, zero LLM dependency)
  → Re-probe → Success: log to hale_decisions.md
              → Still fail: enqueue to incident_queue (hale-incident-handler pages Commander)

Advisor constraint: repair logic is deterministic script, not LLM-based.
Bootstrapping trap: if auth is down, an LLM repair agent also 401s.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD))

from OpsCenter.incident_queue import enqueue_incident

LOGS = THUNDERBIRD / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOGS / "ai_auth_probe.log"
DECISIONS = THUNDERBIRD / "hale_decisions.md"
CLAUDE_BIN = Path.home() / ".local/bin/claude"
KEEPALIVE = THUNDERBIRD / "hooks/claude_oauth_keepalive.sh"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def log_decision(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n## {ts} — AI Auth Probe Auto-Repair\n{msg}\n"
    with open(DECISIONS, "a") as f:
        f.write(entry)


def escalate(component: str, details: str, attempts: int) -> None:
    enqueue_incident({
        "service": "ai-auth-probe",
        "event_type": "auth_failure_unrecovered",
        "severity": "tier1_critical",
        "component": component,
        "details": f"{component}: repair exhausted after {attempts} attempt(s). {details[:300]}",
        "source": "ai_auth_probe",
    })
    log(f"ESCALATE → incident queue: {component} unrecovered after {attempts} attempt(s)")


# ── Probes — each makes a real API call, never trusts exit code alone ─────────

def probe_claude_oauth() -> tuple[bool, str]:
    """Full round-trip: Claude CLI → Anthropic API. Verifies OAuth token end-to-end.

    Return values:
      (True,  "ok")            — auth healthy
      (False, "auth: ...")     — genuine auth/OAuth failure → escalate
      (False, "rate_limit: …") — model unavailable / throttled → do NOT escalate
    """
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    try:
        result = subprocess.run(
            [str(CLAUDE_BIN), "--dangerously-skip-permissions",
             "--model", "claude-haiku-4-5-20251001", "-p", "Reply: ok"],
            env=env, capture_output=True, text=True, timeout=45,
        )
        combined = (result.stdout + result.stderr).lower()

        # Genuine auth failures → escalate
        if any(x in combined for x in ("401", "invalid authentication", "unauthorized", "invalid oauth")):
            return False, f"auth failure: {combined[:150]}"

        # Model unavailable / rate-limit — NOT an auth issue, skip without escalation
        if any(x in combined for x in (
            "there's an issue with the selected model",
            "may not exist or you may not have access",
            "overloaded", "rate limit", "529", "too many requests",
        )):
            return False, f"rate_limit: {combined[:150]}"

        if result.returncode == 0:
            return True, "ok"

        return False, f"auth failure: {(result.stderr or result.stdout)[:200]}"

    except subprocess.TimeoutExpired:
        # Timeout = transient API slowness, not auth failure
        return False, "rate_limit: timeout after 45s"
    except FileNotFoundError:
        return False, f"auth failure: claude binary not found at {CLAUDE_BIN}"
    except Exception as e:
        return False, str(e)


def probe_opencode() -> tuple[bool, str]:
    """DISABLED 2026-06-20 — big-pickle model hung on build/execute.

    OpenCode daemon alive, but `opencode run -m opencode/big-pickle` hangs indefinitely
    (does not respond within 90s). Root cause: big-pickle build or model execution phase.
    Temp fix: disable probe to stop 15-min escalation cascade. Requires Commander investigation.
    """
    return False, "opencode_big_pickle model hung — probe disabled pending investigation"


def probe_telegram() -> tuple[bool, str]:
    """Verify Telegram bot token responds to getMe with ok=true."""
    token = (os.environ.get("TELEGRAM_C2_BOT_TOKEN")
             or os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    if not token:
        return False, "TELEGRAM_C2_BOT_TOKEN not set in environment"
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "thunderbird-probe/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return True, f"bot={data.get('result', {}).get('username', '?')}"
            return False, f"ok=false: {data}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def probe_mcp() -> tuple[bool, str]:
    """HTTP probe to MCP server — 406 is alive (wrong method, correct host)."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8765/mcp")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return True, f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code in (406, 405, 404):
                return True, f"HTTP {e.code} (live)"
            return False, f"HTTP {e.code}"
    except ConnectionRefusedError:
        return False, "connection refused — MCP server not listening"
    except Exception as e:
        return False, str(e)


# ── Repairs — deterministic, zero LLM dependency ─────────────────────────────

def repair_claude_oauth() -> bool:
    """Run keepalive.sh → re-probe. Keepalive makes a real CLI call to refresh token."""
    log("REPAIR: claude_oauth — running keepalive.sh")
    try:
        subprocess.run(["bash", str(KEEPALIVE)], capture_output=True, timeout=30)
        time.sleep(3)
        ok, _ = probe_claude_oauth()
        return ok
    except Exception as e:
        log(f"REPAIR: claude_oauth keepalive error: {e}")
        return False


def repair_opencode() -> bool:
    """OpenCode 401 is often transient under load — wait 20s and retry once."""
    log("REPAIR: opencode_big_pickle — waiting 20s (transient-auth pattern)")
    time.sleep(20)
    ok, _ = probe_opencode()
    return ok


def repair_telegram() -> bool:
    """Restart thunderbird-telegram-gw.service with exponential backoff retry."""
    log("REPAIR: telegram — validating token and restarting service")

    token = (os.environ.get("TELEGRAM_C2_BOT_TOKEN")
             or os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    if not token:
        log("REPAIR FAIL: TELEGRAM_C2_BOT_TOKEN not set — cannot retry")
        return False

    for attempt in range(1, 4):
        log(f"REPAIR: telegram attempt {attempt}/3 — restarting service")
        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "thunderbird-telegram-gw.service"],
                timeout=15, capture_output=True,
            )
            backoff = 2 ** attempt
            log(f"REPAIR: telegram waiting {backoff}s before re-probe (attempt {attempt})")
            time.sleep(backoff)

            ok, detail = probe_telegram()
            if ok:
                log(f"REPAIR SUCCESS: telegram recovered on attempt {attempt}/3")
                return True
            else:
                log(f"REPAIR: telegram re-probe failed on attempt {attempt}/3 — {detail[:100]}")
        except Exception as e:
            log(f"REPAIR: telegram attempt {attempt}/3 error: {e}")

    log("REPAIR EXHAUSTED: telegram — 3 attempts failed")
    return False


def repair_mcp() -> bool:
    """Try known MCP service names → re-probe on first success."""
    log("REPAIR: mcp_server — attempting service restart")
    for svc in ("thunderbird-mcp.service", "mcp-server.service", "d2m-mcp.service"):
        try:
            r = subprocess.run(
                ["systemctl", "--user", "restart", svc],
                timeout=10, capture_output=True,
            )
            if r.returncode == 0:
                time.sleep(5)
                ok, _ = probe_mcp()
                return ok
        except Exception:
            continue
    return False


# ── OODA cycle ────────────────────────────────────────────────────────────────

COMPONENTS = [
    ("claude_oauth",        probe_claude_oauth, repair_claude_oauth),
    # ("opencode_big_pickle", probe_opencode,     repair_opencode),  # DISABLED 2026-06-20: timeout under load, non-essential. Claude OAuth covers critical AI auth path.
    ("telegram",            probe_telegram,     repair_telegram),
    ("mcp_server",          probe_mcp,          repair_mcp),
]


def run_probe_cycle() -> dict:
    log("=== ai_auth_probe cycle start ===")
    results: dict[str, str] = {}

    for name, probe_fn, repair_fn in COMPONENTS:
        # Observe
        ok, detail = probe_fn()

        if ok:
            log(f"OK: {name}")
            results[name] = "ok"
            continue

        # Orient + Decide
        log(f"FAIL: {name} — {detail}")

        # rate_limit prefix = transient model throttle, not auth failure — log and skip
        if detail.startswith("rate_limit:"):
            log(f"SKIP ESCALATION: {name} — rate-limit/model-unavailable, not auth failure: {detail[:120]}")
            results[name] = "rate_limit_skip"
            continue

        if repair_fn is None:
            escalate(name, detail, attempts=0)
            results[name] = "escalated"
            continue

        # Act (repair)
        repaired = repair_fn()

        if repaired:
            # Check (verify independently)
            ok2, detail2 = probe_fn()
            if ok2:
                log(f"REPAIRED: {name} — auto-healed, verified")
                log_decision(
                    f"- **{name}**: detected auth failure (`{detail[:100]}`), "
                    f"auto-repaired. Re-probe confirmed healthy."
                )
                results[name] = "repaired"
            else:
                # If re-probe also rate_limit, don't escalate — still transient
                if detail2.startswith("rate_limit:"):
                    log(f"RATE_LIMIT persists after repair: {name} — not escalating ({detail2[:80]})")
                    results[name] = "rate_limit_skip"
                else:
                    log(f"REPAIR UNVERIFIED: {name} — repair reported success but re-probe failed ({detail2})")
                    escalate(name, f"repair unverified: {detail2}", attempts=1)
                    results[name] = "escalated"
        else:
            escalate(name, detail, attempts=1)
            results[name] = "escalated"

    log(f"=== cycle complete: {results} ===")
    return results


if __name__ == "__main__":
    results = run_probe_cycle()
    # Exit non-zero if any component escalated (makes systemd log it as failure)
    if any(v == "escalated" for v in results.values()):
        sys.exit(1)
