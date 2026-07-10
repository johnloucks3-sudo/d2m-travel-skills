#!/usr/bin/env python3
"""
CONTINUITY RECOVERY PROTOCOL
Runs when network is restored. Reports offline execution results.

Triggered by: network-online.target (systemd)
- Collects all results from continuity_executor spawns
- Reports to Commander via email + Telegram
- Syncs state back to mission board
- Clears offline queue
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
import sys

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CONTINUITY_DIR = THUNDERBIRD_ROOT / "core" / "continuity"
RESULTS_DIR = CONTINUITY_DIR / "results"
CONTINUITY_LOG = CONTINUITY_DIR / "continuity_log.jsonl"
HALE_STATE = THUNDERBIRD_ROOT / "hale_state.json"


def collect_results():
    """Gather all offline execution results"""
    results = {}

    if not RESULTS_DIR.exists():
        return results

    for result_file in RESULTS_DIR.glob("*_result.json"):
        alert_id = result_file.stem.replace("_result", "")
        try:
            with open(result_file) as f:
                results[alert_id] = json.load(f)
        except Exception as e:
            results[alert_id] = {"error": str(e)}

    return results


def build_recovery_report(results):
    """Build human-readable recovery report"""
    if not results:
        return "No offline execution results to report."

    lines = [
        "=== CONTINUITY RECOVERY REPORT ===",
        f"Recovery timestamp: {datetime.now().isoformat()}",
        f"Results collected: {len(results)}",
        "",
    ]

    for alert_id, result in results.items():
        lines.append(f"▸ {alert_id}")
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in ["timestamp"]:
                    lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {result}")
        lines.append("")

    return "\n".join(lines)


def send_recovery_report(results):
    """Send report to Commander via email"""
    if not results:
        return True

    report = build_recovery_report(results)

    # Build email via d2mconcierge
    email_cmd = [
        "python3",
        str(THUNDERBIRD_ROOT / "scripts" / "send_d2mconcierge_email.py"),
        "--to", "johnloucks3@gmail.com",
        "--subject", "CONTINUITY RECOVERY — Offline Execution Report",
        "--body", report,
    ]

    try:
        subprocess.run(email_cmd, check=True, capture_output=True, timeout=30)
        log_recovery("EMAIL_SENT", f"Recovery report sent to Commander")
        return True
    except Exception as e:
        log_recovery("EMAIL_FAILED", f"Failed to send report: {e}")
        return False


def send_telegram_alert(results):
    """Send quick alert to Commander via Telegram"""
    if not results:
        return True

    msg = f"🔄 **CONTINUITY RECOVERY**\n{len(results)} offline missions completed.\nReport in email."

    try:
        from OpsCenter import thunderbird_telegram_gw
        thunderbird_telegram_gw.send_to_commander(msg)
        log_recovery("TELEGRAM_SENT", f"Recovery alert sent")
        return True
    except Exception as e:
        log_recovery("TELEGRAM_FAILED", f"Failed to send Telegram: {e}")
        return False


def clear_results():
    """Clean up offline results after reporting"""
    if not RESULTS_DIR.exists():
        return

    for result_file in RESULTS_DIR.glob("*_result.json"):
        try:
            result_file.unlink()
        except Exception as e:
            log_recovery("CLEANUP_ERROR", f"Could not delete {result_file}: {e}")


def log_recovery(status, message):
    """Append recovery log entry"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "message": message
    }
    with open(CONTINUITY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    log_recovery("START", "Continuity recovery protocol initiated")

    # Collect results
    results = collect_results()
    log_recovery("COLLECTED", f"{len(results)} results found")

    # Report
    if results:
        send_recovery_report(results)
        send_telegram_alert(results)
        clear_results()
        log_recovery("COMPLETE", "Recovery complete, offline queue cleared")
    else:
        log_recovery("NO_WORK", "No offline execution results to report")

    return 0


if __name__ == "__main__":
    sys.exit(main())
