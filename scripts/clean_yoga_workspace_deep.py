#!/usr/bin/env python3
"""
DEEP CLEAN YOGA WORKSPACE
=========================
Authority: COS Victoria Hale SES-6 | Dreams2Memories Travel
Deep cleans the local YOGA Thunderbird root folder to facilitate search indexing.
Moves zip backups, old mission reports, scattered JSON dumps, and orphaned scripts.
"""

import os
import shutil
import logging
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BACKUPS_DIR = ROOT / "backups"
ARCHIVE_DIR = ROOT / "archive"
SCRIPTS_DIR = ROOT / "scripts"
DOCS_DIR = ROOT / "docs"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [DEEP-CLEAN]: %(message)s")
logger = logging.getLogger("DeepClean")

def deep_clean():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Move Zip backups from root
    for f in ROOT.glob("*.zip"):
        if f.is_file():
            target = BACKUPS_DIR / f.name
            logger.info(f"Moving backup zip: {f.name} -> backups/")
            shutil.move(str(f), str(target))

    # 2. Move scattered scripts to scripts/
    scattered_scripts = ["temp_intel_gatherer.py", "run_osint_and_get_results.py", "run_sweep.py"]
    for name in scattered_scripts:
        f = ROOT / name
        if f.is_file():
            target = SCRIPTS_DIR / name
            logger.info(f"Moving scattered script: {name} -> scripts/")
            shutil.move(str(f), str(target))

    # 3. Move old mission reports and temporary markdown files to archive/ or docs/
    old_md_files = [
        "MISSION-172-PHASE-2-STATUS.md",
        "KEYWORD_ROUTER_WIRED.md",
        "GATEWAY_STATUS.md",
        "FALLBACK_INSTRUCTION_20260627.md",
        "CHECKPOINT_20260621.md",
        "MISSION_WONDER_2026-06-12.md",
        "OpsCenter_KnowledgeBase.md",
        "research_email_agent_tools_20260701.md",
        "CLAUDE.md.archive.2026-07-11",
        "session_open_report.md"
    ]
    for name in old_md_files:
        f = ROOT / name
        if f.is_file():
            target = ARCHIVE_DIR / name
            logger.info(f"Moving historical report: {name} -> archive/")
            shutil.move(str(f), str(target))

    # Move doc/research md files to docs/
    doc_files = [
        "POSITION_PAPER_Q3_TECH_ADOPTION_20260711.md",
        "rapidapi_kiwi_search.md"
    ]
    for name in doc_files:
        f = ROOT / name
        if f.is_file():
            target = DOCS_DIR / name
            logger.info(f"Moving documentation file: {name} -> docs/")
            shutil.move(str(f), str(target))

    # 4. Move scattered data JSON dumps to archive/
    scattered_jsons = [
        "airline_scan_results.json",
        "ELON_MISSION_AUDIT_20260621.json",
        "Ship_Intel_20260714_0631.json",
        "scraped_articles.json",
        "MISSION-172-PHASE-2C-GATE3-REPORT.json",
        "MISSION-172-PHASE-2D-LIVE-DISSENT-TEST.json",
        "MISSION-172-SCENARIO-WALKTHROUGH.json",
        "MISSION-320-AUDIT-RESULTS.json",
        "payment_alerts_sent.json"
    ]
    for name in scattered_jsons:
        f = ROOT / name
        if f.is_file():
            target = ARCHIVE_DIR / name
            logger.info(f"Moving data JSON: {name} -> archive/")
            shutil.move(str(f), str(target))

    # 5. Move miscellaneous txt/doc files to archive/
    misc_files = [
        "Autonomy Survey.txt",
        "Command Chief Logo",
        "api_key.txt",
        "guidetoiceland_info.txt",
        "itinerary_passwords.txt",
        "brain_bridge.py" # Move the stale duplicate root script here
    ]
    for name in misc_files:
        f = ROOT / name
        if f.is_file():
            target = ARCHIVE_DIR / name
            logger.info(f"Moving miscellaneous file: {name} -> archive/")
            shutil.move(str(f), str(target))

    # Remove empty temp files
    temp_files = ["opencode", "increasing"]
    for name in temp_files:
        f = ROOT / name
        if f.is_file() and f.stat().st_size == 0:
            logger.info(f"Removing empty temp file: {name}")
            f.unlink()

    # Move logs and old monthly logs to logs/
    log_patterns = ["monthly_archive.log.*", "evernote_backup.log.*", "itinerary_generation.log"]
    log_dir = ROOT / "logs"
    for pattern in log_patterns:
        for f in ROOT.glob(pattern):
            if f.is_file():
                target = log_dir / f.name
                logger.info(f"Moving log file: {f.name} -> logs/")
                shutil.move(str(f), str(target))

    # 6. Move Aider histories to archive/aider_history/
    aider_dir = ARCHIVE_DIR / "aider_history"
    aider_dir.mkdir(parents=True, exist_ok=True)
    for name in [".aider.chat.history.md", ".aider.input.history"]:
        f = ROOT / name
        if f.is_file():
            target = aider_dir / name
            logger.info(f"Moving Aider history: {name} -> archive/aider_history/")
            shutil.move(str(f), str(target))

    # 7. Relocate raw credentials/tokens to creds/ and replace with symlinks in root
    creds_dir = ROOT / "creds"
    creds_dir.mkdir(parents=True, exist_ok=True)
    
    cred_files = [
        "blacklane_credentials.json",
        "calendar_token.json",
        "centrav_credentials.json",
        "hotelbeds_credentials.json",
        "keep_credentials.json",
        "mozio_credentials.json",
        "welcome_pickups_credentials.json",
        "tess_token.json",
        "gmail_token_commander.json",
        "gmail_token_johnloucks3_backup.json",
        "amadeus_credentials.json", # ensure these are sorted in creds
        "gmail_token.json"
    ]
    for name in cred_files:
        f = ROOT / name
        if f.is_file() and not f.is_symlink():
            target = creds_dir / name
            logger.info(f"Relocating raw credential file: {name} -> creds/")
            try:
                # Remove target if it already exists to prevent move collision
                if target.exists():
                    target.unlink()
                # Move to creds/
                shutil.move(str(f), str(target))
                # Create symlink in root
                os.symlink(f"creds/{name}", str(f))
                logger.info(f"✓ Created symlink in root: {name} -> creds/{name}")
            except Exception as e:
                logger.error(f"Failed to relocate credential file {name}: {e}")

    # 8. Relocate state JSONs, database files, and markdown logs to state/ and replace with symlinks in root
    state_dir = ROOT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_files = [
        "conversation_bridge.db",
        "hud_memory.db",
        "learning_rules.db",
        "zfold_test_state.json",
        "evernote_backup_state.json",
        "monthly_archive_state.json",
        "backup_verify_state.json",
        "email_intel_state.json",
        "commander_inbox_state.json",
        "commander_inbox_log.json",
        "briefing_sent.json",
        "claude_code_digest_seen.json",
        "preflight_last.json",
        "hale_activity_log.jsonl",
        "hale_decision_journal.jsonl",
        "hale_email_ooda_state.json",
        "hale_state.json",
        "hale_scan_results.json",
        "hale_vendor_calendar.json",
        "voice_ledger.json",
        "dani_training_data.json",
        "recipient_profiles.json",
        "d2m_brand_voice.json",
        "dani_voice_profile.json",
        "my_voice_profile.json",
        "flight_watch.json",
        "tui.json",
        "claude_inbox.md",
        "claude_outbox.md",
        "dani_followups.md",
        "session_autosave_latest.html",
        "session_autosave_latest.md",
        "OpsCenter_Master_Summary_2026.json"
    ]
    for name in state_files:
        f = ROOT / name
        if f.is_file() and not f.is_symlink():
            target = state_dir / name
            logger.info(f"Relocating state file: {name} -> state/")
            try:
                # Remove target if it already exists
                if target.exists():
                    target.unlink()
                # Move to state/
                shutil.move(str(f), str(target))
                # Create symlink in root
                os.symlink(f"state/{name}", str(f))
                logger.info(f"✓ Created symlink in root: {name} -> state/{name}")
            except Exception as e:
                logger.error(f"Failed to relocate state file {name}: {e}")

    # 9. Relocate configs to config/ and replace with symlinks in root
    config_dir = ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_files = [
        "poe.env",
        "x_osint_follow_list.txt",
        "d2m_osint_follow_list.txt"
    ]
    for name in config_files:
        f = ROOT / name
        if f.is_file() and not f.is_symlink():
            target = config_dir / name
            logger.info(f"Relocating config file: {name} -> config/")
            try:
                # Remove target if it already exists
                if target.exists():
                    target.unlink()
                # Move to config/
                shutil.move(str(f), str(target))
                # Create symlink in root
                os.symlink(f"config/{name}", str(f))
                logger.info(f"✓ Created symlink in root: {name} -> config/{name}")
            except Exception as e:
                logger.error(f"Failed to relocate config file {name}: {e}")

    logger.info("Deep clean of YOGA Thunderbird workspace root complete.")

if __name__ == "__main__":
    deep_clean()
