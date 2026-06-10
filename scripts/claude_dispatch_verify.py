#!/usr/bin/env python3
"""
claude_dispatch_verify.py — Claude MAX Dispatch System Health Check

Verifies that the headless Claude dispatch infrastructure is healthy and ready:
1. OAuth token freshness (not stale)
2. OAuth keepalive daemon running
3. Credentials file exists and valid
4. Can spawn a test task
5. Output file writing works
6. Log file creation works

Usage:
  python3 scripts/claude_dispatch_verify.py           # Full health check
  python3 scripts/claude_dispatch_verify.py --quick   # Quick checks only (no spawn test)
  python3 scripts/claude_dispatch_verify.py --reset   # Reset OAuth token cache
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import argparse

THUNDERBIRD = Path("/home/john/Thunderbird")
LOGS_DIR = THUNDERBIRD / "logs"
CREDS_PATH = Path.home() / ".claude" / ".credentials.json"


def check_systemd_timer(timer_name: str) -> tuple[bool, str]:
    """Check if a systemd timer is active."""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", timer_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, "ACTIVE"
    else:
        return False, "INACTIVE"


def check_oauth_token_freshness() -> tuple[bool, str]:
    """Check if OAuth token exists and is not stale."""
    if not CREDS_PATH.exists():
        return False, f"Credentials file missing: {CREDS_PATH}"

    try:
        creds = json.loads(CREDS_PATH.read_text())
        token_info = creds.get("claudeAiOauth", {})
        token = token_info.get("accessToken")

        if not token:
            return False, "No accessToken in credentials"

        # Check token expiry if available
        issued_at = token_info.get("issuedAt")
        if issued_at:
            try:
                issued_ts = datetime.fromisoformat(issued_at.replace('Z', '+00:00')).timestamp()
                now = datetime.now(timezone.utc).timestamp()
                age_minutes = (now - issued_ts) / 60
                if age_minutes < 0:
                    return False, "Token has future timestamp (clock skew)"
                if age_minutes > 8 * 60:  # 8 hours old
                    return False, f"Token is {int(age_minutes // 60)}h old (should be <2h)"
                return True, f"Token age: {int(age_minutes)} minutes"
            except Exception as e:
                return False, f"Cannot parse token timestamp: {e}"

        return True, "Token exists"
    except Exception as e:
        return False, f"Cannot read credentials: {e}"


def check_logs_directory() -> tuple[bool, str]:
    """Check if logs directory exists and is writable."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = LOGS_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True, f"Writable: {LOGS_DIR}"
    except Exception as e:
        return False, f"Cannot write to {LOGS_DIR}: {e}"


def check_dispatch_cli() -> tuple[bool, str]:
    """Check if dispatch_claude.py CLI is available."""
    cli_path = THUNDERBIRD / "OpsCenter" / "dispatch_claude.py"
    if not cli_path.exists():
        return False, f"CLI not found: {cli_path}"

    # Check if it's executable
    if not cli_path.stat().st_mode & 0o111:
        return False, f"CLI not executable: {cli_path}"

    return True, f"Available: {cli_path}"


def spawn_test_task() -> tuple[bool, str]:
    """Attempt a real spawn to verify the system works end-to-end."""
    import tempfile
    import time

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_output.txt"

            # Run a simple task
            result = subprocess.run(
                [
                    sys.executable,
                    str(THUNDERBIRD / "OpsCenter" / "dispatch_claude.py"),
                    "--task", "dispatch_verify_test",
                    "--output", str(output_file),
                    "--prompt", "Say OK in one word. WRITE to " + str(output_file),
                    "--model", "haiku",
                    "--foreground",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return False, f"Spawn failed: {result.stderr[:200]}"

            # Check if output was written
            time.sleep(1)
            if output_file.exists() and output_file.stat().st_size > 0:
                content = output_file.read_text()
                if "OK" in content or "ok" in content.lower():
                    return True, "Test spawn succeeded"
                else:
                    return False, f"Output missing expected content: {content[:100]}"
            else:
                return False, "Output file not created"

    except subprocess.TimeoutExpired:
        return False, "Spawn timeout (>60s)"
    except Exception as e:
        return False, f"Spawn error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Claude Dispatch System Health Check")
    parser.add_argument("--quick", action="store_true", help="Skip spawn test")
    parser.add_argument("--reset", action="store_true", help="Reset token cache")
    args = parser.parse_args()

    print("\n=== CLAUDE DISPATCH SYSTEM HEALTH CHECK ===\n")

    checks = {
        "OAuth Keepalive Timer": lambda: check_systemd_timer("claude-oauth-keepalive.timer"),
        "Token Monitor Timer": lambda: check_systemd_timer("claude-token-monitor.timer"),
        "Thunderbird Watchdog": lambda: check_systemd_timer("thunderbird-watchdog.timer"),
        "OAuth Token Freshness": check_oauth_token_freshness,
        "Logs Directory": check_logs_directory,
        "Dispatch CLI": check_dispatch_cli,
    }

    results = {}
    all_pass = True

    for check_name, check_fn in checks.items():
        status, msg = check_fn()
        results[check_name] = (status, msg)
        emoji = "✓" if status else "✗"
        print(f"{emoji} {check_name}: {msg}")
        if not status:
            all_pass = False

    if not args.quick:
        print("\nSpawn Test (this may take 30 seconds)...")
        status, msg = spawn_test_task()
        results["Spawn Test"] = (status, msg)
        emoji = "✓" if status else "✗"
        print(f"{emoji} {msg}")
        if not status:
            all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("✓ ALL CHECKS PASSED — Dispatch system is healthy")
        return 0
    else:
        print("✗ SOME CHECKS FAILED — See errors above")
        print("\nQuick fixes:")
        print("  systemctl --user enable --now claude-oauth-keepalive.timer")
        print("  systemctl --user enable --now claude-token-monitor.timer")
        print("  systemctl --user enable --now thunderbird-watchdog.timer")
        return 1


if __name__ == "__main__":
    sys.exit(main())
