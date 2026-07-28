#!/usr/bin/env python3
"""
CLEAN YOGA WORKSPACE & ARCHIVE SCREENSHOTS
===========================================
Authority: COS Victoria Hale SES-6 | Dreams2Memories Travel
Organizes Thunderbird root files to facilitate indexing.
Moves scattered screenshots and HTML previews into archive.
"""

import os
import shutil
import logging
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LOG_DIR = ROOT / "logs"
ARCHIVE_DIR = ROOT / "archive"
SCREENSHOTS_DIR = ARCHIVE_DIR / "screenshots"
HTML_DIR = ARCHIVE_DIR / "html"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [YOGA-CLEAN]: %(message)s")
logger = logging.getLogger("YogaClean")

def clean_workspace():
    # Ensure directories exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Clean log files from root
    for f in ROOT.glob("*.log"):
        if f.is_file():
            target = LOG_DIR / f.name
            logger.info(f"Moving log file: {f.name} -> logs/")
            try:
                shutil.move(str(f), str(target))
            except Exception as e:
                logger.error(f"Error moving {f.name}: {e}")

    # 2. Clean screenshots/images from root
    image_extensions = ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.bmp")
    for ext in image_extensions:
        for f in ROOT.glob(ext):
            if f.is_file():
                target = SCREENSHOTS_DIR / f.name
                logger.info(f"Moving image file: {f.name} -> archive/screenshots/")
                try:
                    shutil.move(str(f), str(target))
                except Exception as e:
                    logger.error(f"Error moving {f.name}: {e}")

    # 3. Clean temporary HTML/PDF previews from root
    html_extensions = ("*.html", "*.pdf")
    for ext in html_extensions:
        for f in ROOT.glob(ext):
            # Skip dashboard or live target files that are actively served if any
            if f.name in ("trip_lifecycle.html", "progress_report.html", "d2m_ops_dashboard.html"):
                # Check if these are needed in root. Usually yes for dashboard serving.
                # Let's keep actively served Dashboards in root, move old ones.
                pass
            target = HTML_DIR / f.name
            logger.info(f"Moving HTML/PDF preview: {f.name} -> archive/html/")
            try:
                shutil.move(str(f), str(target))
            except Exception as e:
                logger.error(f"Error moving {f.name}: {e}")

    # 4. Clean old backups from root
    for f in ROOT.glob("*.bak*"):
        if f.is_file():
            target = ARCHIVE_DIR / f.name
            logger.info(f"Moving backup file: {f.name} -> archive/")
            try:
                shutil.move(str(f), str(target))
            except Exception as e:
                logger.error(f"Error moving {f.name}: {e}")

    logger.info("YOGA workspace root cleanup complete.")

if __name__ == "__main__":
    clean_workspace()
