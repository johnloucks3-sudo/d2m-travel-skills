"""
core/orchestration/temporal_client.py — Temporal Workflow Control Plane Integration

Provides async helper utilities to connect to local Temporal Server (localhost:7233)
and execute durable multi-agent workflows and task queues.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from temporalio.client import Client

TEMPORAL_HOST = "localhost:7233"
DEFAULT_NAMESPACE = "default"
TASK_QUEUE = "thunderbird-wing-queue"

logger = logging.getLogger("thunderbird.temporal")


async def get_temporal_client(host: str = TEMPORAL_HOST, namespace: str = DEFAULT_NAMESPACE) -> Client:
    """Connect to local Temporal Server dev instance."""
    client = await Client.connect(host, namespace=namespace)
    return client


async def execute_durable_workflow(
    workflow_name: str,
    arg: Any,
    id: str,
    task_queue: str = TASK_QUEUE,
) -> Any:
    """Execute a durable workflow and wait for completion."""
    client = await get_temporal_client()
    result = await client.execute_workflow(
        workflow_name,
        arg,
        id=id,
        task_queue=task_queue,
    )
    return result


def check_temporal_health() -> bool:
    """Synchronous health check for Temporal gRPC endpoint."""
    import socket
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", 7233))
        s.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    healthy = check_temporal_health()
    print(f"Temporal Control Plane Health: {'ACTIVE 🟢' if healthy else 'OFFLINE 🔴'}")
