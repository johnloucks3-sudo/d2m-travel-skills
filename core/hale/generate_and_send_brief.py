#!/usr/bin/env python3
"""
Hale Visual Communication Architecture — Brief Generator & Sender
Main orchestrator: loads data, renders visuals, archives locally, backs up to Drive, sends email.
Executed daily at 05:50 MT via systemd timer.
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader

from .brief_data_generator import load_or_fetch_data
from .brief_archiver import archive_brief, backup_to_drive
from .brief_email_sender import send_brief_email
from .hale_template_brief import generate_template_brief, save_brief_to_file

# Setup logging to systemd journal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - hale_brief_generator - %(levelname)s - %(message)s"
)
logger = logging.getLogger("hale_brief_generator")

ROOT = Path("/home/john/Thunderbird")
TEMPLATES_DIR = ROOT / "core" / "visual_synthesis" / "dashboard_app" / "templates"
BRIEFS_OUTPUT_DIR = ROOT / "output" / "briefs"
MT = timezone(timedelta(hours=-6))


def setup_jinja_environment():
    """Configure Jinja2 environment for template rendering."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return env


def create_brief_directory(date_str: str) -> Path:
    """Create dated brief output directory."""
    brief_dir = BRIEFS_OUTPUT_DIR / date_str
    brief_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created brief directory: {brief_dir}")
    return brief_dir


def save_brief_snapshot(brief_data: dict, brief_dir: Path) -> Path:
    """Save brief data as JSON snapshot for later reloading."""
    snapshot_file = brief_dir / "snapshot.json"
    snapshot_file.write_text(json.dumps(brief_data, indent=2, default=str))
    logger.info(f"Saved brief snapshot: {snapshot_file}")
    return snapshot_file


def render_visual(
    jinja_env: Environment,
    template_name: str,
    brief_data: dict,
    output_file: Path
) -> bool:
    """Render a single visual template with brief data."""
    try:
        template = jinja_env.get_template(template_name)
        html = template.render(brief_data=brief_data)
        output_file.write_text(html)
        logger.info(f"Rendered visual: {template_name} → {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to render {template_name}: {e}")
        return False


def render_all_visuals(jinja_env: Environment, brief_data: dict, brief_dir: Path) -> bool:
    """Render all 4 visual templates."""
    visuals = [
        ("brief_lifecycle_wheel.html", "lifecycle_wheel.html"),
        ("brief_financial_waterfall.html", "financial_waterfall.html"),
        ("brief_task_heatmap.html", "task_heatmap.html"),
        ("brief_risk_matrix.html", "risk_matrix.html"),
    ]

    success = True
    for template_name, output_name in visuals:
        output_file = brief_dir / output_name
        if not render_visual(jinja_env, template_name, brief_data, output_file):
            success = False

    return success


def generate_and_send_brief():
    """
    Main orchestration function.
    Steps:
    1. Load/fetch data with freshness checks
    2. Create dated output directory
    3. Save snapshot.json
    4. Render 4 visual templates
    5. Archive locally (90-day retention)
    6. Backup to Google Drive
    7. Send email to Commander
    """
    logger.info("=== HALE BRIEF GENERATION STARTING ===")

    # Step 0: Setup
    jinja_env = setup_jinja_environment()
    today_str = datetime.now(MT).strftime("%Y-%m-%d")
    today_iso = datetime.now(MT).isoformat()

    try:
        # Step 1: Load/fetch data
        logger.info("Loading operational data...")
        brief_data = load_or_fetch_data()
        brief_data["generated_at"] = today_iso
        logger.info(f"Data loaded: {len(brief_data['clients'])} clients, {len(brief_data['tasks'])} tasks, {len(brief_data['risks'])} risks")

        # Step 2: Create output directory
        logger.info(f"Creating brief directory for {today_str}...")
        brief_dir = create_brief_directory(today_str)

        # Step 3: Save snapshot
        logger.info("Saving brief snapshot...")
        snapshot_file = save_brief_snapshot(brief_data, brief_dir)

        # Step 4: Render visuals
        logger.info("Rendering 4 visual templates...")
        if not render_all_visuals(jinja_env, brief_data, brief_dir):
            logger.error("One or more visual rendering failed")
            # Continue anyway — partial brief is better than none

        # Step 5: Archive locally
        logger.info("Archiving brief locally...")
        archive_brief(brief_dir)

        # Step 6: Backup to Google Drive
        logger.info("Backing up to Google Drive...")
        try:
            backup_to_drive(brief_dir)
        except Exception as e:
            logger.warning(f"Drive backup failed (non-fatal): {e}")

        # Step 7: Generate template-based text brief (SO 2026-05-01)
        logger.info("Generating template-based text brief...")
        try:
            brief_file = save_brief_to_file()
            logger.info(f"Text brief saved: {brief_file}")
        except Exception as e:
            logger.warning(f"Template brief generation failed (non-fatal): {e}")

        # Step 8: Send email
        logger.info(f"Sending brief email to Commander...")
        try:
            send_brief_email(today_str)
            logger.info("Brief email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send brief email: {e}")
            return 1

        logger.info("=== HALE BRIEF GENERATION COMPLETE ===")
        return 0

    except Exception as e:
        logger.error(f"Critical error during brief generation: {e}")
        return 1


if __name__ == "__main__":
    exit_code = generate_and_send_brief()
    sys.exit(exit_code)
