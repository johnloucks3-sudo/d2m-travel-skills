#!/usr/bin/env python3
"""
OPTION 1 STACK HEALTH CHECK
Verifies all components are ready for execution.
"""
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

def check_gemini():
    """Check Gemini CLI and API connectivity."""
    try:
        import google.generativeai as genai
        key = os.environ.get('GEMINI_API_KEY')
        if not key:
            return ("✗ GEMINI_API_KEY not set", False)

        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content('test')
        return ("✓ Gemini CLI: READY (connectivity verified)", True)
    except ImportError:
        return ("✗ google-generativeai not installed. Run: pip3 install google-generativeai", False)
    except Exception as e:
        return (f"✗ Gemini connectivity failed: {e}", False)

def check_aider():
    """Check Aider installation and configuration."""
    try:
        result = subprocess.run(['aider', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            return (f"✓ Aider: READY ({version})", True)
    except FileNotFoundError:
        return ("✗ Aider not found. Run: pip3 install aider-chat", False)
    except Exception as e:
        return (f"✗ Aider check failed: {e}", False)

def check_claude_max():
    """Check Claude Code Max binary."""
    claude_path = Path("/home/john/.local/bin/claude")
    if claude_path.exists():
        try:
            result = subprocess.run([str(claude_path), '--version'], capture_output=True, text=True, timeout=5)
            return ("✓ Claude Code Max: READY", True)
        except Exception as e:
            return (f"⚠ Claude Code exists but version check failed: {e}", True)
    else:
        return ("✗ Claude Code binary not found at /home/john/.local/bin/claude", False)

def check_directories():
    """Check required directories exist."""
    dirs = [
        Path("/home/john/Thunderbird/logs"),
        Path("/home/john/Thunderbird/output"),
        Path("/home/john/Thunderbird/scripts"),
    ]

    all_exist = True
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)

    return ("✓ Directories: READY", True)

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n=== OPTION 1 STACK HEALTH CHECK [{timestamp}] ===\n")

    checks = [
        ("Directories", check_directories),
        ("Gemini CLI", check_gemini),
        ("Aider", check_aider),
        ("Claude Max", check_claude_max),
    ]

    results = []
    all_pass = True

    for name, check_func in checks:
        message, passed = check_func()
        results.append((name, message, passed))
        print(f"{message}")
        if not passed:
            all_pass = False

    print()

    if all_pass:
        print("✓ ALL CHECKS PASS — Stack is ready for execution")
        print("\nNext steps:")
        print("  1. Verify GEMINI_API_KEY is set: echo $GEMINI_API_KEY")
        print("  2. Test a simple task: bash ~/Thunderbird/scripts/option1_test_task.sh")
        print("  3. View manual: cat ~/Thunderbird/output/OPTION_1_USER_MANUAL.md")
        return 0
    else:
        print("❌ SOME CHECKS FAILED — See errors above")
        print("\nResolution steps:")
        for name, message, passed in results:
            if not passed and "not set" in message:
                print(f"  - {name}: export GEMINI_API_KEY='your-key-from-google-keep'")
            elif not passed and "not installed" in message:
                print(f"  - {name}: {message}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
