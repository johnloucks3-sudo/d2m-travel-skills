"""
base_bot.py — BotBase: shared scaffolding for all 11 supertimer bots.

Every bot:
  - Maintains its own state JSON (last_run per task, consecutive_failures)
  - Runs only tasks whose interval has elapsed since last_run
  - Calls each task as a subprocess with a hard timeout
  - Catches every exception — one task failure never kills others
  - Writes health dict on exit
  - Alerts relay on consecutive_failures >= threshold
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
VENV_PYTHON = str(ROOT / ".venv/bin/python3")
SYS_PYTHON = "/usr/bin/python3"
RELAY = str(ROOT / "core/relay/wing_relay.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class Task:
    name: str
    cmd: list[str]              # full argv
    interval_sec: int           # how often to run
    timeout_sec: int = 120      # hard kill timeout
    cwd: str = str(ROOT)
    env_file: Optional[str] = str(ROOT / ".env")


@dataclass
class TaskResult:
    name: str
    ran: bool = False
    success: bool = False
    duration_sec: float = 0.0
    error: str = ""


class BotBase:
    bot_name: str
    tasks: list[Task]
    state_file: Path
    consecutive_failure_threshold: int = 3

    def __init__(self):
        self.logger = logging.getLogger(self.bot_name)
        self.state_file = ROOT / f"OpsCenter/supertimer_{self.bot_name}_state.json"

    # ------------------------------------------------------------------ state
    def _load_state(self) -> dict:
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text())
        except Exception:
            pass
        return {"tasks": {}, "consecutive_failures": 0, "last_run": None}

    def _save_state(self, state: dict) -> None:
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, default=str))
        tmp.replace(self.state_file)

    # ---------------------------------------------------------------- env
    def _build_env(self, env_file: Optional[str]) -> dict:
        env = os.environ.copy()
        if env_file and Path(env_file).exists():
            for line in Path(env_file).read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip())
        # Always include Thunderbird PYTHONPATH
        pypath_file = ROOT / "deploy/thunderbird_pythonpath.env"
        if pypath_file.exists():
            for line in pypath_file.read_text().splitlines():
                if line.startswith("PYTHONPATH="):
                    env["PYTHONPATH"] = line[len("PYTHONPATH="):]
        return env

    # --------------------------------------------------------------- run task
    def _run_task(self, task: Task) -> TaskResult:
        result = TaskResult(name=task.name, ran=True)
        t0 = time.monotonic()
        try:
            env = self._build_env(task.env_file)
            proc = subprocess.run(
                task.cmd,
                cwd=task.cwd,
                env=env,
                timeout=task.timeout_sec,
                capture_output=True,
                text=True,
            )
            result.duration_sec = time.monotonic() - t0
            if proc.returncode == 0:
                result.success = True
                self.logger.info("PASS [%s] %.1fs", task.name, result.duration_sec)
            else:
                result.error = (proc.stderr or proc.stdout or "")[:500]
                self.logger.warning("FAIL [%s] rc=%d %s", task.name, proc.returncode, result.error[:120])
        except subprocess.TimeoutExpired:
            result.duration_sec = task.timeout_sec
            result.error = f"timeout after {task.timeout_sec}s"
            self.logger.error("TIMEOUT [%s]", task.name)
        except Exception as exc:
            result.duration_sec = time.monotonic() - t0
            result.error = str(exc)[:300]
            self.logger.error("ERROR [%s] %s", task.name, result.error)
        return result

    # ------------------------------------------------------------------- main
    def run(self) -> dict:
        now = time.time()
        state = self._load_state()
        task_states = state.get("tasks", {})

        # Identify due tasks
        due: list[Task] = []
        for task in self.tasks:
            last = task_states.get(task.name, {}).get("last_run", 0)
            if now - last >= task.interval_sec:
                self.logger.info("DUE [%s] interval=%ds", task.name, task.interval_sec)
                due.append(task)

        # Run due tasks CONCURRENTLY (bot runtime ≈ slowest task, not sum)
        results: list[TaskResult] = []
        if due:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            max_w = min(len(due), 8)
            with ThreadPoolExecutor(max_workers=max_w) as pool:
                futures = {pool.submit(self._run_task, t): t for t in due}
                wall = max(t.timeout_sec for t in due) + 15
                for future in as_completed(futures, timeout=wall):
                    task = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = TaskResult(name=task.name, ran=True, success=False,
                                            error=str(exc)[:200])
                    results.append(result)
                    task_states[task.name] = {
                        "last_run": now if result.success else
                                    task_states.get(task.name, {}).get("last_run", 0),
                        "last_attempt": now,
                        "last_status": "ok" if result.success else "fail",
                        "last_error": result.error,
                    }

        # update consecutive_failures for this bot
        if results:
            any_fail = any(not r.success for r in results)
            if any_fail:
                state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            else:
                state["consecutive_failures"] = 0

        state["tasks"] = task_states
        state["last_run"] = now
        self._save_state(state)

        # alert relay if too many consecutive failures
        consec = state.get("consecutive_failures", 0)
        if consec >= self.consecutive_failure_threshold:
            self._alert_relay(consec, results)

        ran = [r for r in results if r.ran]
        failed = [r for r in ran if not r.success]
        return {
            "bot": self.bot_name,
            "tasks_ran": len(ran),
            "tasks_failed": len(failed),
            "consecutive_failures": consec,
            "status": "RED" if failed else ("GREEN" if ran else "IDLE"),
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    def _alert_relay(self, consec: int, results: list[TaskResult]) -> None:
        failures = [r for r in results if not r.success]
        msg = (
            f"SUPERTIMER ALERT [{self.bot_name}] "
            f"{consec} consecutive failure(s). "
            f"Failed tasks: {', '.join(r.name + ': ' + r.error[:60] for r in failures)}"
        )
        try:
            subprocess.run(
                [SYS_PYTHON, RELAY, "send", "OC", msg],
                timeout=15, capture_output=True,
            )
        except Exception:
            pass
        # Escalate to SMS for P0 — Commander's primary C2 channel
        try:
            sms_msg = f"🔴 WING ALERT: {self.bot_name} — {len(failures)} task(s) failed x{consec}. Check Telegram."
            subprocess.run(
                [VENV_PYTHON, str(ROOT / "core/comms/wing_sms.py"), sms_msg],
                timeout=15, capture_output=True,
            )
        except Exception:
            pass


def venv(script: str, *args: str) -> list[str]:
    """Helper: build argv for a .venv script."""
    return [VENV_PYTHON, str(ROOT / script)] + list(args)


def sys_py(script: str, *args: str) -> list[str]:
    """Helper: build argv for a /usr/bin/python3 script."""
    return [SYS_PYTHON, str(ROOT / script)] + list(args)


def bash(cmd: str) -> list[str]:
    return ["/bin/bash", "-c", cmd]


def goose(recipe: str) -> list[str]:
    return ["/home/john/bin/goose-d2m", "run", "--no-session", "--recipe", str(ROOT / recipe)]
