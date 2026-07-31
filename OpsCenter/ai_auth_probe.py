#!/usr/bin/env python3
"""
AI Auth Probe — active health checks for critical AI/API endpoints.
Runs every 15 minutes via ai-auth-probe.timer.

OODA loop per component:
  Precheck (network liveness) → Probe (real API call) → Classify (3-state)
  → TRANSIENT: log + skip, no repair, no escalate
  → AUTH_FAILED: Repair (deterministic, zero LLM dependency) → Re-probe
      → Re-probe HEALTHY: reset strike counter, log to hale_decisions.md
      → Re-probe still failing: increment persistent strike counter
        → strike 1: log only (do not escalate — could be a one-off)
        → strike 2+: enqueue to incident_queue (hale-incident-handler pages Commander)

Advisor constraint: repair logic is deterministic script, not LLM-based.
Bootstrapping trap: if auth is down, an LLM repair agent also 401s.

Root cause fixed 2026-07-06: probe was treating network ECONNRESET (transient)
as an auth failure and restarting the gateway on a single blip. Fix is a
3-state classifier (HEALTHY / AUTH_FAILED / TRANSIENT) + a network-liveness
precheck (skip the whole cycle if the network path itself is down) + a
two-strike gate (only escalate on 2 consecutive AUTH_FAILED cycles for the
same component, persisted across the 15-min timer's process boundary).
"""

import errno
import fcntl
import json
import os
import socket
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
STATE_PATH = THUNDERBIRD / "OpsCenter" / ".ai_auth_probe_state.json"

# ── 3-state classification ────────────────────────────────────────────────────
# Every probe result collapses to exactly one of these. TRANSIENT never
# repairs or escalates (it's noise, not signal). AUTH_FAILED is the only
# state that feeds the two-strike escalation gate.
HEALTHY = "HEALTHY"
AUTH_FAILED = "AUTH_FAILED"
TRANSIENT = "TRANSIENT"

_TRANSIENT_ERRNOS = {
    errno.ECONNRESET, errno.ETIMEDOUT, errno.ECONNREFUSED,
    errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EPIPE,
}
_TRANSIENT_MARKERS = (
    "econnreset", "etimedout", "connection reset", "connection refused",
    "timed out", "timeout", "network is unreachable", "no route to host",
    "temporary failure",
)
_AUTH_MARKERS = (
    "401", "403", "400", "unauthorized", "invalid authentication",
    "invalid oauth", "invalid token", "forbidden",
)


def classify_probe_result(exc: Exception = None, http_status: int = None, message: str = "") -> str:
    """Collapse a probe outcome to HEALTHY / AUTH_FAILED / TRANSIENT.

    Priority: HTTP status (most reliable signal) → exception type/errno →
    string markers in a captured message (subprocess output, exception text).
    Unknown failure shapes default to AUTH_FAILED — fail loud rather than
    silently swallow a novel failure mode.
    """
    if http_status is not None:
        if 200 <= http_status < 300:
            return HEALTHY
        if http_status in (400, 401, 403):
            return AUTH_FAILED

    if exc is not None:
        if isinstance(exc, (socket.timeout, TimeoutError, subprocess.TimeoutExpired,
                             ConnectionResetError, ConnectionRefusedError)):
            return TRANSIENT
        if isinstance(exc, OSError) and getattr(exc, "errno", None) in _TRANSIENT_ERRNOS:
            return TRANSIENT

    msg = (message or "").lower()
    if any(m in msg for m in _TRANSIENT_MARKERS):
        return TRANSIENT
    if any(m in msg for m in _AUTH_MARKERS):
        return AUTH_FAILED

    return AUTH_FAILED


def check_network_liveness() -> tuple[bool, str]:
    """One lightweight precheck per cycle, before any auth probe runs.

    A single TCP handshake to a well-known reachable host. If the network
    path itself is down, every probe in this cycle would fail identically —
    running (and possibly escalating on) each one individually would just be
    the same false alarm N times. Skip the whole cycle instead.
    """
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=3):
            return True, "network reachable"
    except OSError as e:
        return False, f"network unreachable: {e}"


# ── Persistent two-strike state ───────────────────────────────────────────────

def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(state, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)
    tmp.replace(STATE_PATH)


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
        "details": f"{component}: repair exhausted after {attempts} consecutive AUTH_FAILED cycle(s). {details[:300]}",
        "source": "ai_auth_probe",
    })
    log(f"ESCALATE → incident queue: {component} unrecovered after {attempts} consecutive AUTH_FAILED cycle(s)")


# ── Probes — each makes a real API call, never trusts exit code alone ─────────
# Return (state, detail) where state is one of HEALTHY / AUTH_FAILED / TRANSIENT.

def probe_claude_oauth() -> tuple[str, str]:
    """Full round-trip: Claude CLI → Anthropic API. Verifies OAuth token end-to-end."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    try:
        result = subprocess.run(
            [str(CLAUDE_BIN), "--dangerously-skip-permissions",
             "--model", "claude-haiku-4-5-20251001",
             "--strict-mcp-config",
             "--mcp-config", "/home/john/Thunderbird/config/probe_mcp_empty.json",
             "--settings", "/home/john/Thunderbird/config/probe_settings_empty/settings.json",
             "-p", "ok"],
            env=env, capture_output=True, text=True, timeout=45,
        )
        combined = (result.stdout + result.stderr).lower()

        # returncode 0 from the Claude CLI is the definitive auth proof — the
        # CLI authenticated with Anthropic's API and got a response. Checking
        # classify_probe_result(message=combined) here is wrong: that classifier
        # defaults to AUTH_FAILED for any content that doesn't match known
        # transient/auth-error string markers, so ALL valid Claude responses
        # (including "ok", persona greetings, etc.) were misclassified as
        # AUTH_FAILED, making HEALTHY permanently unreachable.
        if result.returncode == 0:
            return HEALTHY, "ok"

        # Model unavailable / overloaded — treat as transient, not auth
        if any(x in combined for x in (
            "there's an issue with the selected model",
            "may not exist or you may not have access",
            "overloaded", "rate limit", "529", "too many requests",
        )):
            return TRANSIENT, f"transient: {combined[:150]}"

        state = classify_probe_result(message=combined)
        return state, f"{state.lower()}: {combined[:150] or (result.stderr or result.stdout)[:150]}"

    except subprocess.TimeoutExpired as e:
        return classify_probe_result(exc=e), "transient: timeout after 45s"
    except FileNotFoundError:
        return AUTH_FAILED, f"claude binary not found at {CLAUDE_BIN}"
    except OSError as e:
        return classify_probe_result(exc=e, message=str(e)), str(e)


def probe_opencode() -> tuple[str, str]:
    """DISABLED 2026-06-20 — big-pickle model hung on build/execute.

    OpenCode daemon alive, but `opencode run -m opencode/big-pickle` hangs indefinitely
    (does not respond within 90s). Root cause: big-pickle build or model execution phase.
    Temp fix: disable probe to stop 15-min escalation cascade. Requires Commander investigation.
    """
    return AUTH_FAILED, "opencode_big_pickle model hung — probe disabled pending investigation"


def probe_telegram() -> tuple[str, str]:
    """Verify Telegram bot token responds to getMe with ok=true.

    Opens a direct connection (proxy bypassed) — HTTPS_PROXY at 43117 is the
    LLM routing layer and is irrelevant to Telegram API auth. Routing through it
    caused false-positive escalations whenever the local proxy was down.
    """
    token = (os.environ.get("TELEGRAM_C2_BOT_TOKEN")
             or os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    if not token:
        return AUTH_FAILED, "TELEGRAM_C2_BOT_TOKEN not set in environment"
    try:
        # ProxyHandler({}) bypasses HTTP_PROXY/HTTPS_PROXY env vars
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "thunderbird-probe/1.0"},
        )
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return HEALTHY, f"bot={data.get('result', {}).get('username', '?')}"
            return AUTH_FAILED, f"ok=false: {data}"
    except urllib.error.HTTPError as e:
        state = classify_probe_result(http_status=e.code)
        return state, f"HTTP {e.code}: {e.reason}"
    except (socket.timeout, OSError) as e:
        # ECONNRESET, ETIMEDOUT, ECONNREFUSED — network layer, not auth
        return classify_probe_result(exc=e, message=str(e)), f"transient: {e}"


def probe_mcp() -> tuple[str, str]:
    """HTTP probe to MCP server — 406 is alive (wrong method, correct host)."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8765/mcp")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return HEALTHY, f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code in (406, 405, 404):
                return HEALTHY, f"HTTP {e.code} (live)"
            return classify_probe_result(http_status=e.code), f"HTTP {e.code}"
    except ConnectionRefusedError:
        return TRANSIENT, "connection refused — MCP server not listening"
    except (socket.timeout, OSError) as e:
        return classify_probe_result(exc=e, message=str(e)), str(e)


# ── Repairs — deterministic, zero LLM dependency ─────────────────────────────

def repair_claude_oauth() -> bool:
    """Run keepalive.sh → re-probe. Keepalive makes a real CLI call to refresh token."""
    log("REPAIR: claude_oauth — running keepalive.sh")
    try:
        subprocess.run(["bash", str(KEEPALIVE)], capture_output=True, timeout=30)
        time.sleep(3)
        state, _ = probe_claude_oauth()
        return state == HEALTHY
    except Exception as e:
        log(f"REPAIR: claude_oauth keepalive error: {e}")
        return False


def repair_opencode() -> bool:
    """OpenCode 401 is often transient under load — wait 20s and retry once."""
    log("REPAIR: opencode_big_pickle — waiting 20s (transient-auth pattern)")
    time.sleep(20)
    state, _ = probe_opencode()
    return state == HEALTHY


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

            state, detail = probe_telegram()
            if state == HEALTHY:
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
                state, _ = probe_mcp()
                return state == HEALTHY
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

STRIKE_THRESHOLD = 2  # consecutive AUTH_FAILED cycles required before escalation


def run_probe_cycle() -> dict:
    log("=== ai_auth_probe cycle start ===")
    results: dict[str, str] = {}

    # Precheck once per cycle — if the network path itself is down, every
    # component would fail identically; don't run (or escalate on) each one.
    network_live, network_detail = check_network_liveness()
    if not network_live:
        log(f"NETWORK PRECHECK FAILED — skipping all probes this cycle: {network_detail}")
        for name, _, _ in COMPONENTS:
            results[name] = "network_down_skip"
        log(f"=== cycle complete (network precheck failed): {results} ===")
        return results

    state = _load_state()

    for name, probe_fn, repair_fn in COMPONENTS:
        comp_state = state.setdefault(name, {"consecutive_auth_fail": 0})

        # Observe + Classify
        probe_state, detail = probe_fn()

        if probe_state == HEALTHY:
            log(f"OK: {name}")
            comp_state["consecutive_auth_fail"] = 0
            results[name] = "ok"
            continue

        if probe_state == TRANSIENT:
            log(f"TRANSIENT: {name} — {detail[:120]} (no repair, no strike, retry next cycle)")
            results[name] = "transient_skip"
            continue

        # probe_state == AUTH_FAILED — Orient + Decide + Act
        log(f"AUTH_FAILED: {name} — {detail}")

        if repair_fn is not None:
            repaired = repair_fn()
            if repaired:
                verify_state, verify_detail = probe_fn()
                if verify_state == HEALTHY:
                    log(f"REPAIRED: {name} — auto-healed, verified")
                    log_decision(
                        f"- **{name}**: detected auth failure (`{detail[:100]}`), "
                        f"auto-repaired. Re-probe confirmed healthy."
                    )
                    comp_state["consecutive_auth_fail"] = 0
                    results[name] = "repaired"
                    continue
                if verify_state == TRANSIENT:
                    log(f"TRANSIENT after repair: {name} — not counting as a strike ({verify_detail[:100]})")
                    results[name] = "transient_skip"
                    continue
                detail = verify_detail  # still AUTH_FAILED after repair — fall through to strike gate

        # Two-strike gate: first AUTH_FAILED cycle logs only; second consecutive
        # cycle escalates. Resets to 0 the moment a HEALTHY probe is observed.
        comp_state["consecutive_auth_fail"] += 1
        strikes = comp_state["consecutive_auth_fail"]

        if strikes >= STRIKE_THRESHOLD:
            escalate(name, detail, attempts=strikes)
            results[name] = "escalated"
        else:
            log(f"STRIKE {strikes}/{STRIKE_THRESHOLD}: {name} — logged only, will escalate if it recurs next cycle")
            results[name] = "strike_logged"

    _save_state(state)
    log(f"=== cycle complete: {results} ===")
    return results


if __name__ == "__main__":
    results = run_probe_cycle()
    # Exit non-zero if any component escalated (makes systemd log it as failure)
    if any(v == "escalated" for v in results.values()):
        sys.exit(1)
