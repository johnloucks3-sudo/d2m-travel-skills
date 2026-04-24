#!/usr/bin/env python3
"""
Test whether Anthropic SDK auto-refreshes OAuth token on repeated invocations.

Invokes claude -p 5 times with 30-second intervals, monitoring whether the
token in ~/.claude/.credentials.json updates (indicating auto-refresh).
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
RESULTS = []

def read_token_state():
    """Read current token and metadata."""
    try:
        creds = json.loads(CREDS_PATH.read_text())
        token_data = creds.get("claudeAiOauth", {})
        return {
            "accessToken": token_data.get("accessToken", "")[:30],
            "expiresAt": token_data.get("expiresAt"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}

def invoke_claude(iteration):
    """Invoke claude -p with a simple prompt."""
    print(f"\n[{iteration}] Pre-invocation state:")
    state_before = read_token_state()
    print(f"  Token: {state_before.get('accessToken')}...")
    print(f"  Expires: {state_before.get('expiresAt')}")
    
    print(f"[{iteration}] Invoking claude -p...")
    try:
        result = subprocess.run(
            ["/home/john/.local/bin/claude", "-p", "Respond with: OK", "--model", "claude-haiku-4-5-20251001"],
            capture_output=True,
            text=True,
            timeout=15
        )
        output = result.stdout + result.stderr
        print(f"  Exit code: {result.returncode}")
        if "credit" in output.lower() or "balance" in output.lower():
            print(f"  ⚠ Credit error detected")
        if "OK" in output:
            print(f"  ✅ Claude responded successfully")
    except subprocess.TimeoutExpired:
        print(f"  ⏱ Timeout")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    time.sleep(1)
    print(f"[{iteration}] Post-invocation state:")
    state_after = read_token_state()
    print(f"  Token: {state_after.get('accessToken')}...")
    print(f"  Expires: {state_after.get('expiresAt')}")
    
    RESULTS.append({
        "iteration": iteration,
        "before": state_before,
        "after": state_after,
        "token_changed": state_before.get('accessToken') != state_after.get('accessToken'),
        "expiry_changed": state_before.get('expiresAt') != state_after.get('expiresAt'),
    })
    
    return state_before != state_after

print("=" * 70)
print("OAUTH SDK AUTO-REFRESH TEST")
print("=" * 70)
print(f"Credentials path: {CREDS_PATH}")
print(f"Test: Invoke Claude 5 times, monitor token refresh")
print(f"Start time: {datetime.now().isoformat()}")

# Test iterations
for i in range(1, 6):
    invoke_claude(i)
    if i < 5:
        print(f"\n  Waiting 30s before next invocation...")
        time.sleep(30)

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

token_refreshed = any(r.get("token_changed") for r in RESULTS)
expiry_updated = any(r.get("expiry_changed") for r in RESULTS)

print(f"Total invocations: {len(RESULTS)}")
print(f"Token changed: {token_refreshed}")
print(f"Expiry updated: {expiry_updated}")

if token_refreshed or expiry_updated:
    print("\n✅ SDK IS AUTO-REFRESHING TOKEN")
    print("   Conclusion: Token will refresh automatically before expiry.")
    print("   Recommendation: No preemptive refresh needed.")
else:
    print("\n⚠️ NO AUTO-REFRESH DETECTED")
    print("   Token unchanged across 5 invocations.")
    print("   Recommendation: Implement preemptive refresh (Path 2).")

print(f"\nEnd time: {datetime.now().isoformat()}")
print("=" * 70)

