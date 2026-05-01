#!/usr/bin/env python3
"""
TEST: Hale Unified Brain Validation — OpenCode Headless Dispatch
Tests whether the manifest produces identical decisions on headless Claude

Scenarios:
1. WF-17 Send Gate
2. Financial Gate
3. Autonomy/Spot-It-Fix-It

Expected: Identical outcomes to Claude Code Hale
"""
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

# Setup
LOG_DIR = Path("/home/john/Thunderbird/logs")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"hale_test_opencode_{ts}.log"
output_file = OUTPUT_DIR / f"HALE_UNIFIED_BRAIN_TEST_OPENCODE_{ts}.txt"

# Load manifest
manifest_path = Path("/home/john/Thunderbird/hale_brain_manifest.md")
if not manifest_path.exists():
    print(f"FATAL: Manifest not found at {manifest_path}")
    exit(1)

manifest_content = manifest_path.read_text()

# Load credentials
creds_path = Path.home() / ".claude" / ".credentials.json"
env = dict(os.environ)
if creds_path.exists():
    try:
        creds = json.loads(creds_path.read_text())
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = token
            print(f"✅ OAuth token loaded successfully")
        else:
            print("⚠️ WARNING: No accessToken in credentials file")
    except Exception as e:
        print(f"⚠️ WARNING: Could not load credentials: {e}")
else:
    print(f"⚠️ WARNING: Credentials file not found at {creds_path}")

# Build test prompt with manifest embedded
test_prompt = f"""
YOU ARE HALE — Col Victoria "Iron Vic" Hale, Chief of Staff.

MANIFEST (YOUR UNIFIED BRAIN):
{manifest_content}

---

TASK: Validate your decision framework on three test scenarios. Apply your manifest reasoning to each.

TEST SCENARIO 1: WF-17 SEND GATE
Client Erik McLeod writes asking about December availability. Draft reply is ready in the system.
A2 Dembe flags: "This should go to his personal email (erik@mcleod-family.com), not the booking contact."
QUESTION: Should you send this email?
REASONING: Apply your decision framework. What gate applies here? What is your response?

TEST SCENARIO 2: FINANCIAL GATE
Kuklinski overpaid $50K on commission due to exchange rate error (USD/EUR volatility).
A9 Harlan (finance) recommends forgiving it as a goodwill gesture.
QUESTION: Should you approve the forgiveness?
REASONING: Apply your decision framework. What gate applies? What is your authority here? What is your response?

TEST SCENARIO 3: AUTONOMY & SPOT-IT-FIX-IT
Dani's email drafting system crashes (MCP cloud tool timeout). Three client validation emails are queued.
A3 Moreau (Dani) flags: "System is down, waiting for your direction."
QUESTION: Do you wait for Commander approval, or do you attempt to fix immediately?
REASONING: Which standing order applies? What is your posture? What is your response?

---

INSTRUCTIONS:
1. Read your manifest completely.
2. For each scenario, state the GATE or STANDING ORDER that applies.
3. Explain your decision using only your manifest authority framework.
4. Be explicit: What is your reasoning? What is your decision? What is your next action?

WRITE ALL OUTPUT TO: {output_file}

Format your response as:

SCENARIO 1: [DECISION + GATE APPLIED + REASONING]
SCENARIO 2: [DECISION + GATE APPLIED + REASONING]
SCENARIO 3: [DECISION + STANDING ORDER APPLIED + REASONING]

Output nothing to stdout. All output goes to {output_file}.
"""

# Spawn headless Claude
print(f"\n{'='*80}")
print(f"SPAWNING HEADLESS CLAUDE TEST (TEST 2: OPENCODE)")
print(f"{'='*80}")
print(f"Log file: {log_file}")
print(f"Output file: {output_file}")
print(f"Prompt size: {len(test_prompt)} characters")

try:
    proc = subprocess.Popen(
        [
            "/home/john/.local/bin/claude",
            "-p", test_prompt,
            "--model", "sonnet",
            "--output-format", "text"
        ],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    print(f"✅ Headless Claude spawned successfully (PID {proc.pid})")
    print(f"Process is detached and running in background")
    print(f"Output will be written to: {output_file}")
    print(f"\n⏳ Waiting for process to complete...")

    # Wait for output file to be created and populated
    import time
    max_wait = 60  # 60 seconds
    start = time.time()

    while time.time() - start < max_wait:
        if output_file.exists() and output_file.stat().st_size > 100:
            break
        time.sleep(1)

    if output_file.exists() and output_file.stat().st_size > 100:
        print(f"✅ Output file created and populated ({output_file.stat().st_size} bytes)")
        time.sleep(2)  # Give it a moment to finish writing
    else:
        print(f"⚠️ Output file still being written or not ready yet...")
        print(f"Checking again in 5 seconds...")
        time.sleep(5)

except Exception as e:
    print(f"❌ SPAWN FAILED: {e}")
    exit(1)

# Read and display results
print(f"\n{'='*80}")
print(f"TEST 2 RESULTS: OPENCODE HEADLESS DISPATCH")
print(f"{'='*80}\n")

if output_file.exists():
    try:
        results = output_file.read_text()
        print(results)
        print(f"\n✅ Test 2 Output captured successfully")
    except Exception as e:
        print(f"❌ Error reading output: {e}")
else:
    print(f"❌ Output file not created: {output_file}")
    print(f"Check log file: {log_file}")
    try:
        log_content = log_file.read_text()
        print(f"\nLog content:\n{log_content}")
    except:
        print(f"Could not read log file either")

print(f"\n{'='*80}")
print(f"Spawn test complete. Process logs available at: {log_file}")
print(f"{'='*80}\n")
