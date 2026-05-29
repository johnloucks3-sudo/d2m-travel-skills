"""Headless Claude Async Task Pool — MISSION-042.
Spawns 2-5 headless Claude instances in parallel via MAX OAuth.
Pool collects results asynchronously, surfaces when all complete.
Designed to respect MAX limits — configurable max_concurrent, short bursts only.

Architecture:
  - Pool manager: queue of tasks → dispatch workers → collect results
  - Worker: spawns headless Claude via dispatch_claude.py patterns
  - Result aggregator: collects all outputs, surfaces when done

MAX limit awareness:
  - Default max_concurrent: 2 (conservative)
  - Each worker is a short burst (~30s-2min)
  - Total dispatch per call limited by max_concurrent * timeout
"""
import asyncio
import json
import os
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Callable

ROOT = Path(__file__).resolve().parent.parent.parent
DISPATCH_SCRIPT = ROOT / "OpsCenter" / "dispatch_claude.py"

class PoolResult:
    def __init__(self, task_id: str, status: str, output: str = "", error: str = ""):
        self.task_id = task_id
        self.status = status
        self.output = output
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output": self.output[:2000] if self.output else "",
            "error": self.error,
            "completed_at": self.completed_at,
        }


class ClaudeAsyncPool:
    def __init__(self, max_concurrent: int = 2, default_timeout: int = 120):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._results: Dict[str, PoolResult] = {}

    async def _run_worker(self, task_id: str, prompt: str, model: str = "sonnet",
                          output_path: Optional[str] = None, timeout: Optional[int] = None) -> PoolResult:
        """Run a single worker — dispatches to headless Claude."""
        async with self._semaphore:
            try:
                cmd = [
                    sys.executable, str(DISPATCH_SCRIPT),
                    "--task", task_id,
                    "--prompt", prompt,
                    "--model", model,
                    "--foreground",
                ]
                if output_path:
                    cmd.extend(["--output", output_path])

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(ROOT),
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout or self.default_timeout
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return PoolResult(task_id, "timeout", error=f"Timed out after {(timeout or self.default_timeout)}s")

                if proc.returncode == 0:
                    output = stdout.decode() if stdout else ""
                    return PoolResult(task_id, "success", output=output)
                else:
                    error = stderr.decode() if stderr else f"Exit code: {proc.returncode}"
                    return PoolResult(task_id, "failed", error=error)

            except Exception as e:
                return PoolResult(task_id, "error", error=str(e))

    async def run_batch(self, tasks: List[Dict]) -> List[PoolResult]:
        """Run a batch of tasks in parallel.
        Each task: {"id": str, "prompt": str, "model": str, "output": str|None, "timeout": int|None}
        """
        self._results = {}
        workers = []

        for task in tasks:
            task_id = task.get("id", f"task-{int(time.time())}")
            worker = self._run_worker(
                task_id=task_id,
                prompt=task.get("prompt", ""),
                model=task.get("model", "sonnet"),
                output_path=task.get("output"),
                timeout=task.get("timeout"),
            )
            workers.append(worker)

        results = await asyncio.gather(*workers, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                result = PoolResult(tasks[i]["id"], "error", error=str(result))
            self._results[result.task_id] = result

        return list(self._results.values())

    def get_summary(self):
        """Return a summary of all results."""
        success = sum(1 for r in self._results.values() if r.status == "success")
        failed = sum(1 for r in self._results.values() if r.status in ("failed", "error", "timeout"))
        total = len(self._results)
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pct_success": (success / total * 100) if total > 0 else 0,
        }


def register_async_pool_tools(mcp):
    """Register MCP tools for the async task pool."""

    @mcp.tool(name="run_async_batch")
    async def run_async_batch(tasks_json: str, max_concurrent: int = 2) -> str:
        """Run a batch of headless Claude tasks in parallel.
        tasks_json: JSON array of {"id","prompt","model","output","timeout"}
        max_concurrent: max parallel workers (default 2, max 5)
        """
        try:
            tasks = json.loads(tasks_json)
            if not isinstance(tasks, list):
                return json.dumps({"error": "tasks_json must be a JSON array"})

            max_c = min(max_concurrent, 5)  # cap at 5
            pool = ClaudeAsyncPool(max_concurrent=max_c)
            results = await pool.run_batch(tasks)

            return json.dumps({
                "summary": pool.get_summary(),
                "results": [r.to_dict() for r in results],
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="run_single_task")
    async def run_single_task(
        task_id: str,
        prompt: str,
        model: str = "sonnet",
        output_path: str = "",
    ) -> str:
        """Run a single headless Claude task (simplified wrapper for one-off tasks)."""
        try:
            pool = ClaudeAsyncPool(max_concurrent=1)
            result = await pool.run_batch([{
                "id": task_id,
                "prompt": prompt,
                "model": model,
                "output": output_path or None,
            }])
            return json.dumps({"result": result[0].to_dict()}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
