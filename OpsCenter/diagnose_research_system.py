#!/usr/bin/env python3
"""
DIAGNOSTIC: Research Task System Health Check
==============================================
Verifies all prerequisites for headless Claude research task.
Run this BEFORE attempting research if anything fails.

Usage: python3 diagnose_research_system.py
"""

import subprocess
import json
import sys
from pathlib import Path

def check_claude_binary():
    """Check if Claude CLI binary exists."""
    claude_bin = Path.home() / ".local" / "bin" / "claude"
    if claude_bin.exists():
        print(f"✅ Claude binary: {claude_bin}")
        return True
    else:
        print(f"❌ Claude binary NOT FOUND: {claude_bin}")
        return False

def check_oauth_credentials():
    """Check if OAuth credentials file exists and is valid."""
    creds_file = Path.home() / ".claude" / ".credentials.json"
    if not creds_file.exists():
        print(f"❌ Credentials file NOT FOUND: {creds_file}")
        return False

    try:
        creds = json.loads(creds_file.read_text())
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if token:
            print(f"✅ OAuth token found in: {creds_file}")
            return True
        else:
            print(f"❌ No accessToken in credentials file: {creds_file}")
            return False
    except Exception as e:
        print(f"❌ Failed to read credentials: {e}")
        return False

def check_token_refresh_daemon():
    """Check if token refresh daemon is running."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", "claude-token-monitor.timer", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "active (waiting)" in result.stdout or "running" in result.stdout.lower():
            print(f"✅ Token refresh daemon: RUNNING")
            return True
        elif "inactive" in result.stdout:
            print(f"⚠️  Token refresh daemon: INACTIVE")
            print(f"    Run: systemctl --user enable --now claude-token-monitor.timer")
            return False
        else:
            print(f"⚠️  Token refresh daemon: UNKNOWN (check manually)")
            return False
    except Exception as e:
        print(f"⚠️  Could not check token daemon: {e}")
        return False

def check_output_directories():
    """Check if output directories exist."""
    dirs = [
        Path("/home/john/Thunderbird/OpsCenter/opencode_knowledge"),
        Path("/home/john/Thunderbird/logs"),
    ]
    all_exist = True
    for d in dirs:
        if d.exists():
            print(f"✅ Directory exists: {d}")
        else:
            print(f"❌ Directory NOT FOUND: {d}")
            d.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {d}")
    return True

def check_gmail_config():
    """Check if Gmail MCP tools are configured."""
    try:
        # Try to import the Gmail module
        import sys
        sys.path.insert(0, "/home/john/Thunderbird")
        from core.email.thunderbird_gmail import gmail_send_from_wing
        print(f"✅ Gmail module available: core.email.thunderbird_gmail")
        return True
    except ImportError as e:
        print(f"❌ Gmail module not available: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("RESEARCH TASK SYSTEM DIAGNOSTICS")
    print("="*70 + "\n")

    checks = [
        ("Claude Binary", check_claude_binary),
        ("OAuth Credentials", check_oauth_credentials),
        ("Token Refresh Daemon", check_token_refresh_daemon),
        ("Output Directories", check_output_directories),
        ("Gmail Configuration", check_gmail_config),
    ]

    results = []
    for name, check_fn in checks:
        print(f"\n[CHECK] {name}...")
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Exception during {name}: {e}")
            results.append((name, False))

    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL CHECKS PASSED - Ready to run research task!")
        print("\nRun research task with:")
        print("  cd /home/john/Thunderbird/OpsCenter")
        print("  bash run_research_task.sh")
        return 0
    else:
        print(f"\n❌ {total - passed} checks failed. Fix issues above, then rerun diagnostics.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
