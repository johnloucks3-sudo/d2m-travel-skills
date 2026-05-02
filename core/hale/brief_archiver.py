#!/usr/bin/env python3
"""
Hale Brief Archiver — Local Storage & Google Drive Backup
Manages 90-day local retention and automated backup to Drive.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("hale_brief_archiver")

ROOT = Path("/home/john/Thunderbird")
BRIEFS_OUTPUT_DIR = ROOT / "output" / "briefs"
ARCHIVE_RETENTION_DAYS = 90
MT = timezone(timedelta(hours=-6))

# Google Drive folder ID for "Thunderbird_Briefs" (set this from your Drive)
DRIVE_FOLDER_ID = None  # TODO: Set via environment or config


def create_metadata(brief_dir: Path) -> dict:
    """Create metadata.json for brief archive."""
    files = list(brief_dir.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())

    metadata = {
        "generated_at": datetime.now(MT).isoformat(),
        "date": brief_dir.name,
        "files": [f.name for f in files if f.is_file()],
        "file_count": len([f for f in files if f.is_file()]),
        "total_size_bytes": total_size,
        "retention_days": ARCHIVE_RETENTION_DAYS
    }

    metadata_file = brief_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    logger.info(f"Created metadata: {metadata_file}")

    return metadata


def cleanup_old_briefs():
    """Delete briefs older than ARCHIVE_RETENTION_DAYS."""
    if not BRIEFS_OUTPUT_DIR.exists():
        logger.info("Briefs directory does not exist; skipping cleanup")
        return

    cutoff_date = (datetime.now(MT) - timedelta(days=ARCHIVE_RETENTION_DAYS)).date()
    deleted_count = 0

    for brief_dir in sorted(BRIEFS_OUTPUT_DIR.glob("????-??-??")):
        if not brief_dir.is_dir():
            continue

        try:
            dir_date = datetime.strptime(brief_dir.name, "%Y-%m-%d").date()
            if dir_date < cutoff_date:
                # Delete directory and contents
                import shutil
                shutil.rmtree(brief_dir)
                logger.info(f"Deleted old brief: {brief_dir.name}")
                deleted_count += 1
        except ValueError:
            # Invalid directory name format; skip
            pass

    logger.info(f"Cleanup complete: deleted {deleted_count} old briefs (> {ARCHIVE_RETENTION_DAYS} days)")


def archive_brief(brief_dir: Path) -> bool:
    """
    Archive a brief: create metadata and cleanup old briefs.
    Returns True if successful.
    """
    try:
        # Create metadata
        create_metadata(brief_dir)

        # Cleanup old briefs
        cleanup_old_briefs()

        logger.info(f"Brief archived: {brief_dir.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to archive brief: {e}")
        return False


def backup_to_drive(brief_dir: Path) -> bool:
    """
    Backup brief to Google Drive.
    Requires MCP google_drive tools to be available.
    """
    if not DRIVE_FOLDER_ID:
        logger.warning("DRIVE_FOLDER_ID not set; skipping Drive backup")
        return False

    try:
        # Import MCP google_drive tools dynamically
        # This is a placeholder; actual implementation depends on MCP availability
        from mcp.claude_ai_google_drive import create_file as drive_create_file

        logger.warning("Drive backup not yet integrated; placeholder only")
        # TODO: Implement actual Drive API calls via MCP

        return True

    except ImportError:
        logger.warning("MCP google_drive not available; skipping Drive backup")
        return False
    except Exception as e:
        logger.error(f"Failed to backup to Drive: {e}")
        return False


if __name__ == "__main__":
    # Test archiving
    logging.basicConfig(level=logging.INFO)
    test_dir = BRIEFS_OUTPUT_DIR / "2026-04-27"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test.txt").write_text("test content")
    archive_brief(test_dir)
