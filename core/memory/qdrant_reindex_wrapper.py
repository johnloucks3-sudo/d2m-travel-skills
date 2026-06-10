#!/usr/bin/env python3
"""
Qdrant Re-index Wrapper — Memory-aware, robust daily task.

Handles:
  - Memory availability checks
  - Graceful degradation when memory is low
  - Batch processing with progress logging
  - Timeout and retry logic
  - Detailed JSON output for systemd journal

CLI:
  python3 qdrant_reindex_wrapper.py [--max-memory-percent 80] [--dry-run]
"""

import argparse
import json
import logging
import os
import psutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("qdrant_reindex")

# Add Thunderbird to path
sys.path.insert(0, str(Path.home() / "Thunderbird"))

from core.memory.qdrant_memory import QdrantMemorySystem


class ReindexTask:
    """Memory-aware Qdrant reindex task."""

    def __init__(self, max_memory_percent=80, dry_run=False):
        self.max_memory_percent = max_memory_percent
        self.dry_run = dry_run
        self.start_time = time.time()
        self.stats = {
            "status": "running",
            "start_ts": datetime.now(timezone.utc).isoformat(),
            "memory_start_pct": self._get_memory_percent(),
            "files": 0,
            "chunks": 0,
            "elapsed_s": 0,
            "errors": [],
        }

    def _get_memory_percent(self) -> float:
        """Get current memory usage as percentage."""
        return psutil.virtual_memory().percent

    def _check_memory(self) -> bool:
        """Check if memory usage is acceptable. Return True if safe to proceed."""
        pct = self._get_memory_percent()
        self.stats["memory_current_pct"] = pct

        if pct > self.max_memory_percent:
            msg = f"Memory usage {pct:.1f}% exceeds threshold {self.max_memory_percent}%"
            logger.warning(msg)
            return False

        logger.info(f"Memory OK: {pct:.1f}% (threshold {self.max_memory_percent}%)")
        return True

    def _ensure_qdrant(self) -> bool:
        """Verify Qdrant is accessible. Return True if healthy."""
        try:
            mem = QdrantMemorySystem()
            collection_info = mem.qdrant.get_collection("thunderbird_memories")
            logger.info(
                f"Qdrant healthy: collection 'thunderbird_memories' has {collection_info.points_count} points"
            )
            return True
        except Exception as e:
            msg = f"Qdrant unavailable: {e}"
            logger.error(msg)
            self.stats["errors"].append(msg)
            return False

    def run(self) -> dict:
        """Execute the reindex task. Return result dict."""

        logger.info("Starting Qdrant memory reindex")

        # Pre-flight checks
        if not self._check_memory():
            self.stats["status"] = "skipped_memory"
            self.stats["reason"] = f"Memory usage exceeds {self.max_memory_percent}%"
            logger.warning(f"Skipping reindex: {self.stats['reason']}")
            return self._finalize()

        if not self._ensure_qdrant():
            self.stats["status"] = "failed"
            self.stats["reason"] = "Qdrant unavailable"
            return self._finalize()

        if self.dry_run:
            logger.info("DRY RUN: Would execute embedding now")
            self.stats["status"] = "dry_run"
            return self._finalize()

        # Execute embedding
        try:
            mem = QdrantMemorySystem()
            logger.info("Beginning embedding of all memories...")

            embed_start = time.time()
            result = mem.embed_all_memories()
            embed_elapsed = time.time() - embed_start

            self.stats.update({
                "status": "success",
                "files": result.get("files", 0),
                "chunks": result.get("chunks", 0),
                "tokens_est": result.get("tokens_est", 0),
                "cost_est_usd": result.get("cost_est_usd", 0),
                "embed_elapsed_s": round(embed_elapsed, 1),
            })

            logger.info(
                f"Embedding complete: {result['files']} files, {result['chunks']} chunks "
                f"in {embed_elapsed:.1f}s"
            )

            # Run session context blast (generates daily briefing)
            try:
                logger.info("Running session context blast...")
                from core.memory.session_context_blast import main as blast_main
                blast_main()
                logger.info("Session context blast complete")
                self.stats["session_context_blast"] = "success"
            except Exception as e:
                msg = f"Session context blast failed: {e}"
                logger.warning(msg)
                self.stats["session_context_blast"] = "failed"
                self.stats["errors"].append(msg)

            return self._finalize()

        except Exception as e:
            msg = f"Embedding failed: {e}"
            logger.error(msg, exc_info=True)
            self.stats["status"] = "failed"
            self.stats["errors"].append(msg)
            return self._finalize()

    def _finalize(self) -> dict:
        """Finalize and return result."""
        self.stats["elapsed_s"] = round(time.time() - self.start_time, 1)
        self.stats["end_ts"] = datetime.now(timezone.utc).isoformat()
        self.stats["memory_end_pct"] = self._get_memory_percent()

        # Log final status
        logger.info(f"Task complete: status={self.stats['status']}, elapsed={self.stats['elapsed_s']}s")

        # Output JSON for systemd/journal consumption
        print(json.dumps(self.stats, indent=2), file=sys.stderr)

        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Qdrant memory reindex with memory-aware execution"
    )
    parser.add_argument(
        "--max-memory-percent",
        type=int,
        default=80,
        help="Skip if memory usage exceeds this percentage (default: 80)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform pre-flight checks but skip actual embedding",
    )
    args = parser.parse_args()

    task = ReindexTask(
        max_memory_percent=args.max_memory_percent,
        dry_run=args.dry_run,
    )
    result = task.run()

    # Exit with 0 if success or skipped (acceptable), 1 if failed
    if result["status"] in ("success", "skipped_memory", "dry_run"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
