#!/usr/bin/env python3
"""
Qdrant Re-index — Incremental version with reduced memory footprint.

Instead of loading all files at once, processes file-by-file:
  - Reduces peak memory usage significantly
  - Provides progress visibility
  - Allows graceful handling of large memory changes

CLI:
  python3 qdrant_reindex_incremental.py [--memory-threshold 75] [--dry-run]
"""

import argparse
import glob
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

from core.memory.qdrant_memory import QdrantMemorySystem, MEMORY_DIR


class IncrementalReindexTask:
    """Incremental Qdrant reindex — lower memory footprint."""

    def __init__(self, memory_threshold=75, dry_run=False):
        self.memory_threshold = memory_threshold
        self.dry_run = dry_run
        self.start_time = time.time()
        self.stats = {
            "status": "running",
            "start_ts": datetime.now(timezone.utc).isoformat(),
            "memory_start_pct": self._get_memory_percent(),
            "files_processed": 0,
            "files_failed": 0,
            "chunks_total": 0,
            "elapsed_s": 0,
            "errors": [],
        }

    def _get_memory_percent(self) -> float:
        """Get current memory usage as percentage."""
        return psutil.virtual_memory().percent

    def _check_memory(self) -> bool:
        """Check if memory usage is acceptable."""
        pct = self._get_memory_percent()
        self.stats["memory_current_pct"] = pct

        if pct > self.memory_threshold:
            msg = f"Memory usage {pct:.1f}% exceeds threshold {self.memory_threshold}%"
            logger.warning(msg)
            return False

        return True

    def _ensure_qdrant(self) -> bool:
        """Verify Qdrant is accessible."""
        try:
            mem = QdrantMemorySystem()
            collection_info = mem.qdrant.get_collection("thunderbird_memories")
            logger.info(
                f"Qdrant healthy: collection has {collection_info.points_count} points"
            )
            return True
        except Exception as e:
            msg = f"Qdrant unavailable: {e}"
            logger.error(msg)
            self.stats["errors"].append(msg)
            return False

    def run(self) -> dict:
        """Execute incremental reindex."""

        logger.info("Starting incremental Qdrant memory reindex")

        # Pre-flight checks
        if not self._check_memory():
            self.stats["status"] = "skipped_memory"
            self.stats["reason"] = f"Memory usage {self.stats['memory_current_pct']:.1f}% exceeds {self.memory_threshold}%"
            logger.warning(f"Skipping: {self.stats['reason']}")
            return self._finalize()

        if not self._ensure_qdrant():
            self.stats["status"] = "failed"
            self.stats["reason"] = "Qdrant unavailable"
            return self._finalize()

        if self.dry_run:
            logger.info("DRY RUN: Would process files now")
            self.stats["status"] = "dry_run"
            return self._finalize()

        # Get list of memory files
        mem_dir = MEMORY_DIR
        files = sorted(glob.glob(str(mem_dir / "*.md")))
        if not files:
            logger.warning("No memory files found")
            self.stats["status"] = "success"
            return self._finalize()

        logger.info(f"Found {len(files)} memory files to process")

        # Process each file incrementally
        mem = QdrantMemorySystem()
        for i, fpath in enumerate(files, 1):
            # Pre-flight memory check every 10 files
            if i % 10 == 0 and not self._check_memory():
                msg = f"Memory threshold exceeded at file {i}/{len(files)}, stopping gracefully"
                logger.warning(msg)
                self.stats["errors"].append(msg)
                self.stats["stop_reason"] = f"Memory exhausted at file {i}/{len(files)}"
                break

            try:
                # Embed this single file (auto-deletes old chunks)
                result = mem.embed_new_memory(fpath)
                chunks = result.get("chunks", 0)
                self.stats["chunks_total"] += chunks
                self.stats["files_processed"] += 1

                if i % 20 == 0 or i == len(files):
                    logger.info(
                        f"Progress: {i}/{len(files)} files, "
                        f"{self.stats['chunks_total']} chunks, "
                        f"memory {self._get_memory_percent():.1f}%"
                    )

            except Exception as e:
                msg = f"Failed to embed {Path(fpath).name}: {e}"
                logger.error(msg)
                self.stats["errors"].append(msg)
                self.stats["files_failed"] += 1

        # Run session context blast (generate briefing)
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

        # Determine final status
        if self.stats["files_failed"] == 0:
            self.stats["status"] = "success"
        elif self.stats["files_processed"] > 0:
            self.stats["status"] = "partial_success"
        else:
            self.stats["status"] = "failed"

        return self._finalize()

    def _finalize(self) -> dict:
        """Finalize and return result."""
        self.stats["elapsed_s"] = round(time.time() - self.start_time, 1)
        self.stats["end_ts"] = datetime.now(timezone.utc).isoformat()
        self.stats["memory_end_pct"] = self._get_memory_percent()

        logger.info(
            f"Task complete: status={self.stats['status']}, "
            f"files={self.stats['files_processed']}, "
            f"chunks={self.stats['chunks_total']}, "
            f"elapsed={self.stats['elapsed_s']}s"
        )

        # Output JSON for systemd/journal
        print(json.dumps(self.stats, indent=2), file=sys.stderr)

        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Incremental Qdrant memory reindex (lower memory footprint)"
    )
    parser.add_argument(
        "--memory-threshold",
        type=int,
        default=75,
        help="Skip if memory usage exceeds this percentage (default: 75)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform pre-flight checks but skip actual indexing",
    )
    args = parser.parse_args()

    task = IncrementalReindexTask(
        memory_threshold=args.memory_threshold,
        dry_run=args.dry_run,
    )
    result = task.run()

    # Exit 0 for success/skip/dry-run, 1 for failure
    if result["status"] in ("success", "partial_success", "skipped_memory", "dry_run"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
