#!/usr/bin/env python3
"""
thunderbird_temporal.py — Temporal durable workflow adapter for Thunderbird.
Wraps temporalio Python SDK. Use for long-running agent tasks that must survive
session restarts: portal keepalive rewrites, overnight scraping pipelines, FPD watches.

Dev server: `temporal server start-dev` (runs on :7233, UI at :8233)

Usage:
    from core.ai_infra.thunderbird_temporal import run_workflow, ThunderbirdActivity

    # Define an activity (a unit of work)
    @activity.defn
    async def fetch_portal_prices(client_id: str) -> dict:
        ...

    # Define a workflow (orchestrates activities with retries/timeouts)
    @workflow.defn
    class FPDWatchWorkflow:
        @workflow.run
        async def run(self, booking_id: str) -> str:
            return await workflow.execute_activity(fetch_portal_prices, ...)

    # Run it
    result = await run_workflow("FPDWatchWorkflow", booking_id="2984034")
"""
from __future__ import annotations
import asyncio
from typing import Any, Type

TEMPORAL_HOST = "localhost:7233"
TEMPORAL_NAMESPACE = "default"
TEMPORAL_TASK_QUEUE = "thunderbird-main"


async def run_workflow(
    workflow_class: Any,
    *args,
    task_queue: str = TEMPORAL_TASK_QUEUE,
    id: str = None,
    **kwargs,
) -> Any:
    """Execute a Temporal workflow and return the result."""
    from temporalio.client import Client
    client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)
    handle = await client.start_workflow(
        workflow_class.run,
        *args,
        id=id or f"thunderbird-{workflow_class.__name__}-{asyncio.get_event_loop().time():.0f}",
        task_queue=task_queue,
        **kwargs,
    )
    return await handle.result()


async def get_client():
    """Get a Temporal client connection."""
    from temporalio.client import Client
    return await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)


def run_worker(workflows: list, activities: list, task_queue: str = TEMPORAL_TASK_QUEUE):
    """Start a Temporal worker (blocking). Pass workflow and activity classes."""
    from temporalio.client import Client
    from temporalio.worker import Worker

    async def _run():
        client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)
        worker = Worker(client, task_queue=task_queue, workflows=workflows, activities=activities)
        await worker.run()

    asyncio.run(_run())


if __name__ == "__main__":
    import subprocess, sys
    print("Temporal dev server status:")
    r = subprocess.run(["temporal", "workflow", "list"], capture_output=True, text=True)
    print(r.stdout[:200] or r.stderr[:200])
    print(f"Connect at: {TEMPORAL_HOST} | UI at: http://localhost:8233")
