#!/usr/bin/env python3
"""Auto-repair: Chrome CDP health — restart Chrome debug service."""
import subprocess, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def main():
    # Auto-restart disabled 2026-06-27: was causing Chrome to spawn visibly every 60s.
    # Start chrome-debug manually when needed: systemctl --user start chrome-debug.service
    print("Chrome CDP health repair: DISABLED (auto-restart suppressed to prevent unwanted Chrome windows)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
