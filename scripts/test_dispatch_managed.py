#!/usr/bin/env python3
"""Test the --managed flag in dispatch_claude.py"""
import subprocess, sys, json
from pathlib import Path

output = "/tmp/dispatch_managed_test.md"
result = subprocess.run(
    [sys.executable, "OpsCenter/dispatch_claude.py",
     "--task", "dispatch-test",
     "--output", output,
     "--prompt", "List D2M's top 3 cruise line partners: Regent, Silversea, Viking. One line each.",
     "--model", "haiku",
     "--managed"],
    capture_output=True, text=True,
    cwd="/home/john/Thunderbird"
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:300] if result.stderr else "")
print("Return code:", result.returncode)
if Path(output).exists():
    print("OUTPUT FILE:", Path(output).read_text())
