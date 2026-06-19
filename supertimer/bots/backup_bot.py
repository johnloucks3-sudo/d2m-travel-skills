#!/usr/bin/env python3
"""
backup_bot — Drive sync, Evernote backup, logrotate, monthly archive, claude-sync.
Interval: 7200s. Tasks run daily or weekly.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash, goose

ROOT = Path("/home/john/Thunderbird")

class BackupBot(BotBase):
    bot_name = "backup_bot"
    tasks = [
        Task("evernote-backup",
             venv("api/thunderbird_evernote_backup.py"),
             interval_sec=604800, timeout_sec=300),  # weekly (was daily)
        Task("backup-verify",
             venv("core/watchtower/thunderbird_backup_verify.py"),
             interval_sec=86400, timeout_sec=120),
        Task("drive-sync",
             bash(f"{ROOT}/scripts/thunderbird-rclone-sync.sh"),
             interval_sec=86400, timeout_sec=300),
        Task("logrotate",
             bash(f"/usr/sbin/logrotate -s {ROOT}/logs/logrotate.state {ROOT}/config/logrotate.conf"),
             interval_sec=86400, timeout_sec=60),
        Task("monthly-archive",
             venv("core/ops/thunderbird_monthly_archive.py"),
             interval_sec=2592000, timeout_sec=300),
        Task("claude-sync",
             bash("claude-sync push >> ~/.claude/sync.log 2>&1"),
             interval_sec=86400, timeout_sec=120),
        Task("phase2-visuals",
             sys_py("OpsCenter/hale_dispatcher.py", "generate_phase2_visuals"),
             interval_sec=604800, timeout_sec=180),
        Task("factbook-refresh",
             sys_py("scripts/factbook_refresh.py"),
             interval_sec=604800, timeout_sec=120),  # Goose/DeepSeek retired 2026-06-19
        Task("drive-health",
             sys_py("scripts/drive_health_check.py"),
             interval_sec=86400, timeout_sec=120),  # daily health check
        Task("sheets-wing-sync",
             sys_py("scripts/sheets_wing_sync.py"),
             interval_sec=43200, timeout_sec=180),  # 2x/day push Wing→Sheets
        Task("sheets-pull",
             sys_py("scripts/sheets_pull.py"),
             interval_sec=14400, timeout_sec=180),  # every 4h pull Sheets→local
        Task("voice-sync",
             venv("core/learning/thunderbird_voice_harvest.py", "--sync"),
             interval_sec=86400, timeout_sec=120),
        Task("spsa-sheets-sync",
             venv("OpsCenter/thunderbird_spsa_sheets_sync.py")
             if (ROOT / "OpsCenter/thunderbird_spsa_sheets_sync.py").exists()
             else venv("OpsCenter/job_spsa_intake.py"),
             interval_sec=86400, timeout_sec=120),
    ]

if __name__ == "__main__":
    result = BackupBot().run()
    print(json.dumps(result))
