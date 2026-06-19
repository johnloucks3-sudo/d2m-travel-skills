#!/usr/bin/env python3
"""
drive_health_check.py — Google Drive health: rclone size check + local disk status.
Runs via backup_bot. Output to OpsCenter/state/drive_health_latest.txt.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
REPORT = ROOT / "OpsCenter/state/drive_health_latest.txt"
RCLONE = "/usr/bin/rclone"
REMOTE = "d2mconcierge:Thunderbird_Mirror"
CONFIG = str(ROOT / "config/rclone.conf")


def run_cmd(args: list, timeout: int = 60) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def main() -> int:
    lines = [
        f"# Drive Health Report — {datetime.now().strftime('%Y-%m-%d %H:%M')} MT",
        "",
    ]

    # 1. Local disk usage
    rc, out, err = run_cmd(["df", "-h", str(ROOT)])
    lines += ["## Local Disk (Thunderbird)", out or err, ""]

    # 2. Thunderbird directory size
    rc, out, err = run_cmd(["du", "-sh", "--exclude=.venv", "--exclude=node_modules", str(ROOT)], timeout=30)
    lines += ["## Thunderbird Directory Size (excl .venv)", out or err, ""]

    # 3. rclone size on remote
    rclone_args = [RCLONE, "--config", CONFIG, "size", REMOTE] if Path(CONFIG).exists() else [RCLONE, "size", REMOTE]
    rc, out, err = run_cmd(rclone_args, timeout=90)
    if rc == 0:
        lines += ["## Remote (Drive Mirror) Size", out, ""]
    else:
        lines += ["## Remote (Drive Mirror) Size", f"[skipped — rclone error: {err[:200]}]", ""]

    # 4. Last sync stamp
    sync_state = ROOT / "OpsCenter/state/last_drive_sync.txt"
    if sync_state.exists():
        lines += ["## Last Drive Sync", sync_state.read_text().strip(), ""]
    else:
        # Check rclone log for most recent sync
        sync_log = ROOT / "logs/rclone_sync.log"
        if sync_log.exists():
            tail_rc, tail_out, _ = run_cmd(["tail", "-5", str(sync_log)])
            lines += ["## Last Drive Sync (log tail)", tail_out, ""]

    # 5. OpsCenter/state file count (data health indicator)
    state_dir = ROOT / "OpsCenter/state"
    if state_dir.exists():
        state_files = list(state_dir.glob("*.json")) + list(state_dir.glob("*.txt"))
        lines += [f"## OpsCenter/state files: {len(state_files)}", ""]

    REPORT.write_text("\n".join(lines))
    print(f"drive_health_check: report → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
