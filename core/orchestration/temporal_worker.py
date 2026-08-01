#!/usr/bin/env python3
"""
core/orchestration/temporal_worker.py — Thunderbird Wing Temporal Background Worker

Polls the 'thunderbird-main' task queue on local Temporal server (localhost:7233).
Executes durable workflows and activities for client intake, fare sweeps, and dossier sync.
"""

import asyncio
import logging
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thunderbird-temporal-worker")


# ── ACTIVITIES ───────────────────────────────────────────────────────────────

@activity.defn
async def scan_fares_activity(destination: str) -> dict:
    """Simulated fare scan activity with automatic retry protection."""
    logger.info(f"Scanning fares for destination: {destination}")
    return {"destination": destination, "status": "scanned", "best_fare": "$1,250"}


@activity.defn
async def generate_briefing_activity(topic: str) -> str:
    """Briefing generation activity."""
    logger.info(f"Generating briefing for: {topic}")
    return f"Executive Briefing for {topic}: Complete."


# ── WORKFLOWS ────────────────────────────────────────────────────────────────

@workflow.defn
class ClientInquiryWorkflow:
    @workflow.run
    async def run(self, destination: str) -> dict:
        logger.info(f"Starting ClientInquiryWorkflow for {destination}")
        fare_res = await workflow.execute_activity(
            scan_fares_activity,
            destination,
            start_to_close_timeout=timedelta(seconds=30)
        )
        return {"workflow": "ClientInquiryWorkflow", "result": fare_res}


@workflow.defn
class DailyIntelSweepWorkflow:
    @workflow.run
    async def run(self, topic: str) -> str:
        logger.info(f"Starting DailyIntelSweepWorkflow for {topic}")
        briefing_res = await workflow.execute_activity(
            generate_briefing_activity,
            topic,
            start_to_close_timeout=timedelta(seconds=30)
        )
        return briefing_res


# ── WORKER MAIN ──────────────────────────────────────────────────────────────

async def main():
    logger.info("Connecting to Temporal server at localhost:7233...")
    client = await Client.connect("localhost:7233")
    logger.info("Temporal client connected cleanly 🟢")

    worker = Worker(
        client,
        task_queue="thunderbird-main",
        workflows=[ClientInquiryWorkflow, DailyIntelSweepWorkflow],
        activities=[scan_fares_activity, generate_briefing_activity]
    )

    logger.info("Worker started. Polling task queue 'thunderbird-main'...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
