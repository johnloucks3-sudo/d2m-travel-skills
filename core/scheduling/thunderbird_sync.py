"""
thunderbird_sync.py — Compatibility shim
thunderbird_sync.py was replaced by rclone shell scripts during the core/ reorg.
This shim provides the sync() interface the scheduler expects,
delegating to the actual rclone sync scripts.
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

RCLONE_SCRIPT = "/home/john/Thunderbird/scripts/thunderbird-rclone-sync.sh"
D2M_SCRIPT = "/home/john/.local/bin/d2m-drive-sync.sh"


def sync(full: bool = False) -> bool:
    """Run rclone sync scripts. full=True runs both D2M and Thunderbird mirrors."""
    try:
        result = subprocess.run(
            ["/bin/bash", RCLONE_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.warning(f"thunderbird rclone sync exited {result.returncode}: {result.stderr[:200]}")
        else:
            logger.info("thunderbird rclone sync completed OK")

        if full:
            result2 = subprocess.run(
                ["/bin/bash", D2M_SCRIPT],
                capture_output=True, text=True, timeout=120
            )
            if result2.returncode != 0:
                logger.warning(f"d2m rclone sync exited {result2.returncode}: {result2.stderr[:200]}")
            else:
                logger.info("d2m rclone sync completed OK")

        return True
    except Exception as e:
        logger.error(f"sync() failed: {e}")
        return False
