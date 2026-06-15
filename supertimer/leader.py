#!/usr/bin/env python3
"""
leader.py — Thunderbird Supertimer Leader

Runs every 60s via thunderbird-supertimer.timer.
Reads registry.json, checks which bots are due, forks them as subprocesses
in parallel (max 6 concurrent). Writes health to OpsCenter/supertimer_health.json.
Alerts relay on consecutive bot-level failures.

This is the ONLY systemd timer needed for 11 bots / 113+ tasks.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
REGISTRY = ROOT / "supertimer/registry.json"
HEALTH_FILE = ROOT / "OpsCenter/supertimer_health.json"
STATE_FILE = ROOT / "OpsCenter/supertimer_leader_state.json"
LOG_FILE = ROOT / "logs/supertimer_leader.log"
RELAY = str(ROOT / "core/relay/wing_relay.py")
VENV_PYTHON = str(ROOT / ".venv/bin/python3")
SYS_PYTHON = "/usr/bin/python3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s LEADER %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("leader")


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text())


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {"bots": {}}


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.replace(STATE_FILE)


def load_health() -> dict:
    try:
        if HEALTH_FILE.exists():
            return json.loads(HEALTH_FILE.read_text())
    except Exception:
        pass
    return {}


def save_health(health: dict) -> None:
    tmp = HEALTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(health, indent=2, default=str))
    tmp.replace(HEALTH_FILE)


def build_env() -> dict:
    env = os.environ.copy()
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    pypath = ROOT / "deploy/thunderbird_pythonpath.env"
    if pypath.exists():
        for line in pypath.read_text().splitlines():
            if line.startswith("PYTHONPATH="):
                env["PYTHONPATH"] = line[len("PYTHONPATH="):]
    return env


def run_bot(bot_name: str, script: str, timeout_sec: int, env: dict) -> dict:
    """Run one bot subprocess. Returns health dict."""
    t0 = time.monotonic()
    script_path = str(ROOT / script)
    try:
        proc = subprocess.run(
            [VENV_PYTHON, script_path],
            cwd=str(ROOT),
            env=env,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
        )
        duration = time.monotonic() - t0
        if proc.returncode == 0:
            # bot may print JSON health on stdout
            health_out = {}
            try:
                health_out = json.loads(proc.stdout.strip().splitlines()[-1])
            except Exception:
                pass
            log.info("BOT OK [%s] %.1fs", bot_name, duration)
            return {
                "status": health_out.get("status", "GREEN"),
                "tasks_ran": health_out.get("tasks_ran", 0),
                "tasks_failed": health_out.get("tasks_failed", 0),
                "duration_sec": duration,
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": "",
            }
        else:
            err = (proc.stderr or proc.stdout or "")[:400]
            log.warning("BOT FAIL [%s] rc=%d %s", bot_name, proc.returncode, err[:100])
            return {
                "status": "RED",
                "tasks_ran": 0,
                "tasks_failed": 1,
                "duration_sec": duration,
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": err,
            }
    except subprocess.TimeoutExpired:
        log.error("BOT TIMEOUT [%s] after %ds", bot_name, timeout_sec)
        return {
            "status": "RED",
            "tasks_ran": 0,
            "tasks_failed": 1,
            "duration_sec": float(timeout_sec),
            "ts": datetime.now(timezone.utc).isoformat(),
            "error": f"timeout after {timeout_sec}s",
        }
    except Exception as exc:
        log.error("BOT ERROR [%s] %s", bot_name, exc)
        return {
            "status": "RED",
            "tasks_ran": 0,
            "tasks_failed": 1,
            "duration_sec": time.monotonic() - t0,
            "ts": datetime.now(timezone.utc).isoformat(),
            "error": str(exc)[:300],
        }


def alert_relay(msg: str) -> None:
    try:
        subprocess.run(
            [SYS_PYTHON, RELAY, "send", "OC", msg],
            timeout=15, capture_output=True,
        )
    except Exception:
        pass


def main() -> None:
    log.info("=== SUPERTIMER LEADER TICK ===")
    registry = load_registry()
    state = load_state()
    health = load_health()
    env = build_env()
    now = time.time()

    bots_cfg = registry["bots"]
    leader_cfg = registry["leader"]
    max_parallel = leader_cfg.get("max_parallel_bots", 6)
    alert_threshold = leader_cfg.get("alert_on_consecutive_failures", 2)

    # Determine which bots are due
    due_bots: list[tuple[str, dict]] = []
    for bot_name, cfg in bots_cfg.items():
        last_run = state["bots"].get(bot_name, {}).get("last_run", 0)
        interval = cfg["interval_sec"]
        if now - last_run >= interval:
            due_bots.append((bot_name, cfg))
            log.info("DUE [%s] interval=%ds", bot_name, interval)
        else:
            remaining = int(interval - (now - last_run))
            log.debug("SKIP [%s] next in %ds", bot_name, remaining)

    if not due_bots:
        log.info("No bots due this tick.")
        return

    log.info("Launching %d bot(s) (max_parallel=%d)", len(due_bots), max_parallel)

    # Run due bots in parallel, capped at max_parallel
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {
            executor.submit(run_bot, name, cfg["script"], cfg["timeout_sec"], env): name
            for name, cfg in due_bots
        }
        # Add extra margin so we always collect results
        wall_timeout = max(cfg["timeout_sec"] for _, cfg in due_bots) + 30
        for future in as_completed(futures, timeout=wall_timeout):
            bot_name = futures[future]
            try:
                results[bot_name] = future.result()
            except Exception as exc:
                results[bot_name] = {
                    "status": "RED",
                    "tasks_ran": 0,
                    "tasks_failed": 1,
                    "duration_sec": 0,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                }

    # Update state + health
    for bot_name, result in results.items():
        prev = state["bots"].get(bot_name, {})
        consec = prev.get("consecutive_failures", 0)
        if result["status"] == "RED":
            consec += 1
        else:
            consec = 0

        state["bots"][bot_name] = {
            "last_run": now if result["status"] != "RED" else prev.get("last_run", 0),
            "last_attempt": now,
            "consecutive_failures": consec,
            "last_status": result["status"],
        }
        health[bot_name] = result
        health[bot_name]["consecutive_failures"] = consec

        if consec >= alert_threshold:
            alert_relay(
                f"SUPERTIMER LEADER: [{bot_name}] {consec} consecutive failures. "
                f"Error: {result.get('error', 'unknown')[:150]}"
            )

    save_state(state)
    save_health(health)

    # Summary log
    ok = sum(1 for r in results.values() if r["status"] != "RED")
    fail = len(results) - ok
    log.info("TICK DONE: %d OK / %d FAIL out of %d bots run", ok, fail, len(results))
    if fail:
        log.warning("FAILED BOTS: %s", [n for n, r in results.items() if r["status"] == "RED"])


if __name__ == "__main__":
    main()
