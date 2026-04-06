"""
Thunderbird OS — Daily Preflight Check
========================================
Dreams2Memories Travel, LLC

Runs at 00:50 MDT daily. Verifies all systems before AM intel cycle.
Two-tier alerting: Telegram -> Email

Usage:
  python3 thunderbird_preflight.py           # Run all checks
  python3 thunderbird_preflight.py --quick   # Skip slow checks (API tests)
"""

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
THUNDERBIRD_DIR = Path(__file__).parent.parent
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_FILE = LOG_DIR / "preflight.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("preflight")

# Required env vars
REQUIRED_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_COMMANDER_ID",
    "GROQ_API_KEY",
]

# ---------------------------------------------------------------------------
# Check functions — each returns (status, message)
# status: "GREEN", "YELLOW", "RED"
# ---------------------------------------------------------------------------

def check_services() -> List[Tuple[str, str, str]]:
    """Check critical services are running."""
    results = []
    checks = {
        "MCP Server": "travel_mcp_server",
        "Scheduler": "thunderbird_scheduler",
        "Telegram C2": "telegram_pager_c2",
    }
    for name, proc_name in checks.items():
        try:
            out = subprocess.run(
                ["pgrep", "-f", proc_name],
                capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                pids = out.stdout.strip().split("\n")
                results.append((name, "GREEN", f"Running (PID {pids[0]})"))
            else:
                results.append((name, "RED", "NOT RUNNING"))
        except Exception as e:
            results.append((name, "RED", f"Check failed: {e}"))
    return results


def check_tokens() -> List[Tuple[str, str, str]]:
    """Check OAuth tokens exist and are not expired."""
    results = []
    tokens = {
        "Gmail Token": THUNDERBIRD_DIR / "gmail_token.json",
        "Persona Token": THUNDERBIRD_DIR / "config" / "persona_gmail_token.json",
    }
    for name, path in tokens.items():
        if not path.exists():
            results.append((name, "RED", f"MISSING: {path}"))
            continue
        try:
            data = json.loads(path.read_text())
            # Check if token has refresh_token (can auto-renew)
            if data.get("refresh_token"):
                results.append((name, "GREEN", "Valid (has refresh token)"))
            else:
                results.append((name, "YELLOW", "No refresh token — may expire"))
        except Exception as e:
            results.append((name, "RED", f"Parse error: {e}"))
    return results


def check_disk() -> Tuple[str, str, str]:
    """Check disk space."""
    usage = shutil.disk_usage("/home")
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 2:
        return ("Disk Space", "RED", f"{free_gb:.1f} GB free — CRITICAL")
    elif free_gb < 5:
        return ("Disk Space", "YELLOW", f"{free_gb:.1f} GB free — low")
    return ("Disk Space", "GREEN", f"{free_gb:.1f} GB free")


def check_env_keys() -> List[Tuple[str, str, str]]:
    """Check required environment variables are set in .env."""
    results = []
    env_file = THUNDERBIRD_DIR / ".env"
    if not env_file.exists():
        return [("ENV File", "RED", ".env missing")]

    env_content = env_file.read_text()
    for key in REQUIRED_KEYS:
        # Check key exists and is not commented out
        if f"\n{key}=" in env_content or env_content.startswith(f"{key}="):
            results.append((key, "GREEN", "Set"))
        else:
            results.append((key, "RED", f"MISSING from .env"))
    return results


def check_connectivity() -> Tuple[str, str, str]:
    """Check internet connectivity."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return ("Internet", "GREEN", "Connected")
    except OSError:
        return ("Internet", "RED", "NO CONNECTIVITY")


def check_gemini_api(quick: bool = False) -> Tuple[str, str, str]:
    """Quick Gemini API health check."""
    if quick:
        return ("Gemini API", "YELLOW", "Skipped (--quick)")
    try:
        from google import genai as new_genai
        key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not key:
            env_file = THUNDERBIRD_DIR / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("GOOGLE_API_KEY=") or line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
        if not key:
            return ("Gemini API", "YELLOW", "No API key found")
        client = new_genai.Client(api_key=key)
        client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say OK"
        )
        return ("Gemini API", "GREEN", "Responding")
    except Exception as e:
        return ("Gemini API", "RED", f"Failed: {e}")


def check_mcp_port() -> Tuple[str, str, str]:
    """Check MCP server is listening on port 8765."""
    try:
        sock = socket.create_connection(("127.0.0.1", 8765), timeout=3)
        sock.close()
        return ("MCP Port 8765", "GREEN", "Listening")
    except OSError:
        return ("MCP Port 8765", "RED", "NOT LISTENING")


# ---------------------------------------------------------------------------
# Multi-channel alerting
# ---------------------------------------------------------------------------

def send_telegram_alert(message: str) -> bool:
    """Send alert via Telegram C2 bot."""
    try:
        import requests
        env = _load_env()
        token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_C2_BOT_TOKEN")
        chat_id = env.get("TELEGRAM_COMMANDER_ID")
        if not token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False


def send_email_alert(subject: str, body: str) -> bool:
    """Send alert via Gmail (d2mconcierge -> johnloucks3)."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR))
        from thunderbird_google_auth import get_credentials
        from googleapiclient.discovery import build
        import base64
        from email.mime.text import MIMEText

        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)
        msg = MIMEText(body)
        msg["to"] = "johnloucks3@gmail.com"
        msg["from"] = "d2mconcierge@gmail.com"
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception as e:
        logger.error(f"Email alert failed: {e}")
        return False


def alert_multi_channel(subject: str, message: str, severity: str = "GREEN"):
    """Two-tier alerting: Telegram -> Email based on severity.
    (tmomail SMS removed 2026-03-31 — unreliable/bouncing.)
    """
    # Always try Telegram
    tg_ok = send_telegram_alert(f"<b>{subject}</b>\n\n{message}")

    if severity in ("YELLOW", "RED"):
        # Add email for YELLOW+
        send_email_alert(f"[D2M {severity}] {subject}", message)

    if not tg_ok:
        logger.warning("Telegram failed — escalating to email")
        send_email_alert(f"[D2M ALERT] {subject}", message)


def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_file = THUNDERBIRD_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_preflight(quick: bool = False) -> Dict:
    """Run all preflight checks. Returns structured results."""
    logger.info("=" * 60)
    logger.info("THUNDERBIRD PREFLIGHT CHECK — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    all_results = []

    # Run checks
    all_results.extend(check_services())
    all_results.extend(check_tokens())
    all_results.append(check_disk())
    all_results.extend(check_env_keys())
    all_results.append(check_connectivity())
    all_results.append(check_gemini_api(quick=quick))
    all_results.append(check_mcp_port())

    # Determine overall severity
    statuses = [r[1] for r in all_results]
    if "RED" in statuses:
        overall = "RED"
    elif "YELLOW" in statuses:
        overall = "YELLOW"
    else:
        overall = "GREEN"

    # Format report
    report_lines = [f"Thunderbird Preflight — {overall}"]
    report_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}")
    report_lines.append("")

    for name, status, msg in all_results:
        icon = {"GREEN": "\u2705", "YELLOW": "\u26a0\ufe0f", "RED": "\U0001f534"}.get(status, "\u2753")
        report_lines.append(f"{icon} {name}: {msg}")
        logger.info(f"  [{status}] {name}: {msg}")

    report = "\n".join(report_lines)

    # Alert based on severity
    if overall != "GREEN":
        alert_multi_channel("Preflight Check", report, overall)
    else:
        # GREEN — still send Telegram confirmation
        send_telegram_alert(f"\u2705 <b>Preflight GREEN</b>\n{len(all_results)} checks passed\n{datetime.now().strftime('%H:%M MT')}")

    # Save last result
    result_file = THUNDERBIRD_DIR / "preflight_last.json"
    result_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "overall": overall,
        "checks": [{"name": n, "status": s, "message": m} for n, s, m in all_results],
    }, indent=2))

    return {"overall": overall, "checks": all_results, "report": report}


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    result = run_preflight(quick=quick)

    # Print summary
    print(f"\nOverall: {result['overall']}")
    reds = [c for c in result["checks"] if c[1] == "RED"]
    if reds:
        print(f"\n\U0001f534 RED issues ({len(reds)}):")
        for name, _, msg in reds:
            print(f"  - {name}: {msg}")

    sys.exit(0 if result["overall"] == "GREEN" else 1)
