#!/usr/bin/env python3
"""
Phase 3A Health Check Worker
Runs every 30 seconds to detect Redis recovery and trigger cache sync
Part of error recovery framework: automatically restores cache to Redis on reconnect
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_file = Path("/home/john/Thunderbird/logs/phase3a_health_check.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("health_check_worker")

# Import all V2 connectors
try:
    from core.dani_redis_connector_cli_v2 import DaniRedisConnectorCLI
    from core.d2mc2_redis_connector_cli_v2 import D2MC2RedisConnectorCLIV2
    from core.goose_redis_connector_cli_v2 import GooseRedisConnectorCLIV2
    from core.opencode_redis_connector_cli_v2 import OpenCodeRedisConnectorCLIV2
    from core.claude_redis_subscriber_v2 import ClaudeRedisSubscriberV2
    logger.info("✅ All V2 connectors imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import connectors: {e}")
    sys.exit(1)


def check_connector_health(connector_class, connector_name: str) -> dict:
    """
    Check health of a single connector and sync cache if needed.

    Returns:
    - dict with status, was_down, recovered, synced info
    """
    try:
        connector = connector_class(host="127.0.0.1", port=6379)

        # Check if Redis is available
        was_available = connector.redis_available

        # Perform health check (detects recovery and triggers sync)
        connector.check_redis_health()

        # Return status
        return {
            "name": connector_name,
            "redis_available": connector.redis_available,
            "was_available": was_available,
            "recovered": (not was_available) and connector.redis_available,
            "cache_dir": str(connector.cache_dir),
            "status": "ok"
        }
    except Exception as e:
        return {
            "name": connector_name,
            "status": "error",
            "error": str(e)
        }


def run_health_check():
    """Run health check across all 5 connectors"""
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"\n{'='*70}")
    logger.info(f"HEALTH CHECK CYCLE @ {timestamp}")
    logger.info(f"{'='*70}\n")

    # Define connectors to check
    connectors = [
        (DaniRedisConnectorCLI, "Dani"),
        (D2MC2RedisConnectorCLIV2, "D2MC2"),
        (GooseRedisConnectorCLIV2, "Goose"),
        (OpenCodeRedisConnectorCLIV2, "OpenCode"),
        (ClaudeRedisSubscriberV2, "Claude/Subscriber")
    ]

    results = []
    recovered_count = 0
    error_count = 0

    for connector_class, connector_name in connectors:
        logger.info(f"Checking {connector_name}...")
        result = check_connector_health(connector_class, connector_name)
        results.append(result)

        if result["status"] == "ok":
            if result["recovered"]:
                logger.info(f"  ✅ RECOVERED: {connector_name} — cache syncing to Redis")
                recovered_count += 1
            elif result["redis_available"]:
                logger.info(f"  ✅ HEALTHY: {connector_name} — Redis connected")
            else:
                logger.info(f"  ⚠️  FALLBACK: {connector_name} — using local cache")
        else:
            logger.error(f"  ❌ ERROR: {connector_name} — {result.get('error')}")
            error_count += 1

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY: {len(results)} connectors checked")
    logger.info(f"  Recovered: {recovered_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info(f"{'='*70}\n")

    # Write results to status file
    status_file = Path("/home/john/Thunderbird/logs/phase3a_health_check_status.json")
    status = {
        "timestamp": timestamp,
        "connectors": results,
        "recovered_count": recovered_count,
        "error_count": error_count
    }
    status_file.write_text(json.dumps(status, indent=2))

    return recovered_count, error_count


if __name__ == "__main__":
    logger.info("Phase 3A Health Check Worker started")
    try:
        recovered, errors = run_health_check()
        if errors > 0:
            logger.warning(f"Health check completed with {errors} error(s)")
            sys.exit(1)
        else:
            logger.info("Health check completed successfully")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)
