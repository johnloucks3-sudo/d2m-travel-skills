#!/usr/bin/env python3
"""
Agent Pool Manager — OpenCode + Claude mixed worker pool
Persistent pool of N workers maintaining task queue with auto-restart and status exposure.

File: /home/john/Thunderbird/OpsCenter/agent_pool_manager.py
"""

import asyncio
import subprocess
import threading
import logging
import json
import os
import argparse
import signal
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

from OpsCenter.task_queue import (
    get_pending_tasks, mark_running, complete_task, fail_task,
    get_queue_stats, init_db, has_pending
)
from OpsCenter.agent_runner import route, _base_env, ROUTE_TABLE
from OpsCenter.thunderbird_tasking_watcher import (
    refresh_oauth_token_preemptive, load_oauth_env
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_pool_manager")


class WorkerState(Enum):
    """Worker subprocess state machine."""
    IDLE = "idle"
    WORKING = "working"
    WAITING_OUTPUT = "waiting_output"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentType(Enum):
    """Agent type routing."""
    OPENCODE = "opencode"
    CLAUDE = "claude"


@dataclass
class WorkerStatus:
    """Live worker status snapshot."""
    worker_id: str
    state: str
    agent_type: str
    task_id: Optional[str]
    pid: Optional[int]
    log_file: Optional[str]
    output_file: Optional[str]
    elapsed_sec: float


class AgentWorker:
    """Single subprocess slot managing one task at a time."""

    def __init__(self, worker_id: str, agent_type: AgentType, log_dir: Path, output_dir: Path):
        self.worker_id = worker_id
        self.agent_type = agent_type
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.state = WorkerState.IDLE
        self.state_lock = threading.Lock()

        self.task_id = None
        self.proc = None
        self.pid = None
        self.log_file = None
        self.output_file = None
        self.start_time = None
        self.monitor_thread = None
        self._pool_ref = None  # Back-reference for replace_worker callback

    def assign(self, task: dict, pool_ref) -> bool:
        """Assign task to worker. Returns False if busy."""
        with self.state_lock:
            if self.state != WorkerState.IDLE:
                return False
            self.state = WorkerState.WORKING
            self.task_id = task.get("id")
            self._pool_ref = pool_ref

        try:
            self._spawn(task)
            with self.state_lock:
                self.state = WorkerState.WAITING_OUTPUT
            # Start daemon monitor thread
            self.monitor_thread = threading.Thread(target=self._monitor_fn, daemon=True)
            self.monitor_thread.start()
            return True
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: spawn failed — {e}")
            with self.state_lock:
                self.state = WorkerState.ERROR
            return False

    def _spawn(self, task: dict):
        """Spawn agent subprocess with WRITE [PATH] instruction."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"worker_{self.worker_id}_{self.task_id}_{ts}.log"
        self.output_file = self.output_dir / f"worker_{self.worker_id}_{self.task_id}_{ts}.txt"
        self.start_time = datetime.now()

        prompt = task.get("prompt", f"Execute task {self.task_id}")
        model = task.get("model", "claude-haiku-4-5-20251001")

        argv = self._argv(prompt, model)

        # Build environment
        if self.agent_type == AgentType.CLAUDE:
            env = dict(os.environ)
            try:
                refresh_oauth_token_preemptive()
                env.update(load_oauth_env())
            except Exception as e:
                logger.warning(f"Worker {self.worker_id}: OAuth refresh failed — {e}")
        else:  # OPENCODE
            env = _base_env()

        # Spawn subprocess
        with open(self.log_file, "w") as log_fh:
            self.proc = subprocess.Popen(
                argv,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,  # CRITICAL: detach
            )
            self.pid = self.proc.pid
            logger.info(f"Worker {self.worker_id}: spawned {self.agent_type.value} (PID {self.pid}) task {self.task_id}")

    def _argv(self, prompt: str, model: str) -> List[str]:
        """Build subprocess argv for agent type."""
        if self.agent_type == AgentType.OPENCODE:
            return [
                "/home/john/.local/bin/opencode",
                "run",
                f"{prompt}\nWRITE output to {self.output_file}"
            ]
        else:  # CLAUDE
            return [
                "/home/john/.local/bin/claude",
                "-p", f"{prompt}\nWRITE output to {self.output_file}",
                "--model", model,
                "--output-format", "text"
            ]

    def _monitor_fn(self):
        """Daemon monitor thread. Block on proc.wait(), check output stability, handle completion."""
        try:
            self.proc.wait()
            logger.info(f"Worker {self.worker_id}: subprocess exited (PID {self.pid})")

            # Poll for output file stability
            stable, content = self._poll_stable(timeout=30)

            with self.state_lock:
                if stable and content:
                    # Output file stable → task complete
                    logger.info(f"Worker {self.worker_id}: output stable, marking complete")
                    complete_task(self.task_id)
                    self.state = WorkerState.IDLE
                else:
                    # No output or file didn't stabilize → task failed, retry
                    logger.warning(f"Worker {self.worker_id}: output not stable or missing, retry queued")
                    fail_task(self.task_id, retry=True)
                    self.state = WorkerState.IDLE
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: monitor thread exception — {e}")
            with self.state_lock:
                self.state = WorkerState.ERROR
        finally:
            # Trigger pool replacement if dead
            if self._pool_ref:
                try:
                    self._pool_ref.replace_worker(self)
                except Exception as e:
                    logger.error(f"Worker {self.worker_id}: replace_worker callback failed — {e}")

    def _poll_stable(self, timeout: int) -> tuple:
        """Poll output file for stability. Returns (stable: bool, content: str)."""
        start = datetime.now()
        prev_size = None
        same_count = 0

        while (datetime.now() - start).total_seconds() < timeout:
            if not self.output_file.exists():
                threading.Event().wait(0.5)
                continue

            try:
                size = self.output_file.stat().st_size
                if size == prev_size:
                    same_count += 1
                    if same_count >= 2:
                        # File size stable across 2 reads → return content
                        return (True, self.output_file.read_text(errors="ignore"))
                else:
                    same_count = 0
                prev_size = size
            except Exception:
                pass

            threading.Event().wait(1)

        # Timeout → return whatever we have
        if self.output_file.exists():
            return (False, self.output_file.read_text(errors="ignore"))
        return (False, "")

    def terminate(self):
        """Terminate subprocess."""
        if self.proc:
            try:
                self.proc.terminate()
                logger.info(f"Worker {self.worker_id}: terminated (PID {self.pid})")
            except Exception as e:
                logger.error(f"Worker {self.worker_id}: terminate failed — {e}")
        with self.state_lock:
            self.state = WorkerState.TERMINATED

    def status(self) -> WorkerStatus:
        """Return live worker status."""
        with self.state_lock:
            elapsed = 0
            if self.start_time:
                elapsed = (datetime.now() - self.start_time).total_seconds()
            return WorkerStatus(
                worker_id=self.worker_id,
                state=self.state.value,
                agent_type=self.agent_type.value,
                task_id=self.task_id,
                pid=self.pid,
                log_file=str(self.log_file) if self.log_file else None,
                output_file=str(self.output_file) if self.output_file else None,
                elapsed_sec=elapsed
            )


class AgentPoolManager:
    """Persistent pool of workers maintaining fixed count with auto-restart."""

    def __init__(self, pool_config: Dict[AgentType, int] = None, poll_interval: float = 2.0):
        if pool_config is None:
            pool_config = {AgentType.OPENCODE: 2, AgentType.CLAUDE: 1}

        self.pool_config = pool_config
        self.poll_interval = poll_interval
        self.workers: Dict[str, AgentWorker] = {}
        self.shutdown_event = asyncio.Event()

        # Initialize database
        init_db()

        # Create log/output dirs
        self.log_dir = Path("/home/john/Thunderbird/logs/agent_pool")
        self.output_dir = Path("/home/john/Thunderbird/output/agent_pool")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Instantiate workers
        worker_id = 0
        for agent_type, count in pool_config.items():
            for _ in range(count):
                wid = f"{agent_type.value[0]}{worker_id}"
                self.workers[wid] = AgentWorker(wid, agent_type, self.log_dir, self.output_dir)
                worker_id += 1

        logger.info(f"Pool initialized: {sum(pool_config.values())} workers ({dict((k.value, v) for k, v in pool_config.items())})")

    async def run(self):
        """Main async loop. Install signal handlers, run dispatch loop."""
        loop = asyncio.get_event_loop()

        def sig_handler(sig, frame):
            logger.info(f"Signal {sig} received, initiating shutdown...")
            asyncio.create_task(self.shutdown(drain=True))

        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

        logger.info("Pool starting dispatch loop...")
        await self._dispatch_loop()
        logger.info("Pool shutdown complete")

    async def _dispatch_loop(self):
        """Poll for idle workers, pull pending tasks, assign to matching agent type."""
        while not self.shutdown_event.is_set():
            try:
                # Find idle workers
                idle_workers = [w for w in self.workers.values() if w.state == WorkerState.IDLE]

                if idle_workers:
                    # Pull tasks
                    limit = len(idle_workers)
                    tasks = get_pending_tasks(limit=limit)

                    for task in tasks:
                        # Route task to agent type
                        agent_type_str = route(task)
                        agent_type = AgentType.CLAUDE if agent_type_str == "hale" else AgentType.OPENCODE

                        # Find idle worker of matching type
                        worker = next((w for w in idle_workers if w.agent_type == agent_type), None)
                        if worker:
                            mark_running(task["id"])
                            worker.assign(task, self)
                            idle_workers.remove(worker)

                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Dispatch loop exception: {e}")
                await asyncio.sleep(self.poll_interval)

    def replace_worker(self, dead: AgentWorker):
        """Spawn replacement worker of same type to keep pool size constant."""
        try:
            # Find next available ID for this type
            agent_type = dead.agent_type
            count = sum(1 for w in self.workers.values() if w.agent_type == agent_type)
            wid = f"{agent_type.value[0]}{len(self.workers)}"

            replacement = AgentWorker(wid, agent_type, self.log_dir, self.output_dir)
            self.workers[wid] = replacement
            logger.info(f"Spawned replacement worker {wid} for {agent_type.value}")
        except Exception as e:
            logger.error(f"replace_worker failed: {e}")

    async def shutdown(self, drain: bool = True):
        """Graceful shutdown. If drain=True, wait for workers to complete."""
        self.shutdown_event.set()

        if drain:
            logger.info("Draining active workers (60s timeout)...")
            start = datetime.now()
            while (datetime.now() - start).total_seconds() < 60:
                active = [w for w in self.workers.values() if w.state != WorkerState.IDLE]
                if not active:
                    break
                await asyncio.sleep(1)

        # Terminate all
        for worker in self.workers.values():
            if worker.state != WorkerState.IDLE:
                worker.terminate()

        logger.info("Pool shutdown")

    def pool_status(self) -> dict:
        """Return full pool status including worker snapshots and queue stats."""
        return {
            "pool_config": {k.value: v for k, v in self.pool_config.items()},
            "workers": {
                wid: asdict(worker.status())
                for wid, worker in self.workers.items()
            },
            "queue": get_queue_stats(),
            "timestamp": datetime.now().isoformat()
        }

    def worker_status(self, worker_id: str) -> Optional[dict]:
        """Return status for single worker."""
        if worker_id in self.workers:
            return asdict(self.workers[worker_id].status())
        return None


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Pool Manager")
    parser.add_argument("--opencode", type=int, default=2, help="Number of OpenCode workers")
    parser.add_argument("--claude", type=int, default=1, help="Number of Claude workers")
    parser.add_argument("--poll", type=float, default=2.0, help="Poll interval (seconds)")
    parser.add_argument("--status", action="store_true", help="Print pool status and exit")

    args = parser.parse_args()

    pool_config = {
        AgentType.OPENCODE: args.opencode,
        AgentType.CLAUDE: args.claude
    }

    manager = AgentPoolManager(pool_config=pool_config, poll_interval=args.poll)

    if args.status:
        status = manager.pool_status()
        print(json.dumps(status, indent=2))
        return

    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())
