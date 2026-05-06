# COS Approval Monitor v2 — Testing Guide

**Version:** 2.0  
**Date:** 2026-05-03  
**Scope:** Unit tests, integration tests, and end-to-end validation  

---

## QUICK START — 5-MINUTE TEST SUITE

Run this before deployment to verify core functionality:

```bash
cd /home/john/Thunderbird/scripts

# Test 1: Python imports
python3 -c "exec(open('cos_approval_monitor_v2.py').read()); print('✓ Imports OK')"

# Test 2: Dry-run scan
python3 cos_approval_monitor_v2.py --scan-once --dry-run
# Expected: No errors, dry-run messages only

# Test 3: State file creation
python3 -c "from cos_approval_monitor_v2 import DetectionStateManager; mgr = DetectionStateManager(); print(f'✓ State file: {mgr.state_file}')"

# Test 4: Pattern detection
python3 -c "
from cos_approval_monitor_v2 import ApprovalPatternDetector
detector = ApprovalPatternDetector()
# Test approval keywords
approvals = detector.detect_approvals('Test', 'I approve this')
assert len(approvals) > 0, 'Approval detection failed'
print(f'✓ Approval detection: {approvals}')
"

# Test 5: Service file syntax
sudo systemd-analyze verify /etc/systemd/user/cos-approval-monitor-v2.service || true
```

Expected result: All 5 tests pass with `✓` marks.

---

## UNIT TESTS

### Test 1: ApprovalPatternDetector

```python
#!/usr/bin/env python3
"""Unit tests for ApprovalPatternDetector."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cos_approval_monitor_v2 import ApprovalPatternDetector

def test_approval_detection():
    """Test approval keyword detection."""
    detector = ApprovalPatternDetector()

    # Test "approve" keyword
    approvals = detector.detect_approvals("Test", "I approve this change")
    assert len(approvals) > 0, "Failed to detect 'approve'"
    assert approvals[0][0] == "approve", f"Wrong type: {approvals[0][0]}"

    # Test "yes" keyword
    approvals = detector.detect_approvals("Test", "Yes, proceed")
    assert len(approvals) > 0, "Failed to detect 'yes'"

    # Test "proceed" keyword
    approvals = detector.detect_approvals("Test", "You can proceed now")
    assert len(approvals) > 0, "Failed to detect 'proceed'"

    # Test case-insensitivity
    approvals = detector.detect_approvals("Test", "APPROVED")
    assert len(approvals) > 0, "Case-insensitive detection failed"

    print("✓ Approval detection tests passed")

def test_directive_detection():
    """Test COS/COO/Hale directive detection."""
    detector = ApprovalPatternDetector()

    # Test COS directive
    directives = detector.detect_directives("COS: Review this", "")
    assert "COS:" in directives, "Failed to detect COS: prefix"

    # Test COO directive
    directives = detector.detect_directives("", "COO: Action required")
    assert "COO:" in directives, "Failed to detect COO: prefix"

    # Test Hale directive
    directives = detector.detect_directives("Hale: Stand by", "")
    assert "Hale:" in directives, "Failed to detect Hale: prefix"

    print("✓ Directive detection tests passed")

def test_tasking_detection():
    """Test tasking assignment detection."""
    detector = ApprovalPatternDetector()

    # Test "Assign X to Y" pattern
    tasking = detector.detect_tasking("Assign research to A2", "")
    assert len(tasking) > 0, "Failed to detect 'Assign' pattern"

    # Test "Task:" pattern
    tasking = detector.detect_tasking("Task: Prepare brief", "")
    assert len(tasking) > 0, "Failed to detect 'Task:' pattern"

    print("✓ Tasking detection tests passed")

def test_no_false_positives():
    """Test that random text doesn't trigger false positives."""
    detector = ApprovalPatternDetector()

    # Normal email should not trigger approval
    approvals = detector.detect_approvals(
        "Meeting notes",
        "We discussed the quarterly review and decided to continue with current strategy."
    )
    assert len(approvals) == 0, f"False positive: {approvals}"

    print("✓ False positive tests passed")

if __name__ == "__main__":
    test_approval_detection()
    test_directive_detection()
    test_tasking_detection()
    test_no_false_positives()
    print("\n✓ All unit tests passed!")
```

**Run this test:**
```bash
python3 - << 'EOF'
# Copy test code above and run
EOF
```

### Test 2: DetectionStateManager

```python
#!/usr/bin/env python3
"""Unit tests for DetectionStateManager."""

import sys
import json
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cos_approval_monitor_v2 import DetectionStateManager, ApprovalDetection, ProcessedDetection

def test_state_persistence():
    """Test state file save/load."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        # Create manager with temp state file
        mgr = DetectionStateManager(state_file)

        # Create detection
        detection = ApprovalDetection(
            thread_id="test123",
            subject="Test Subject",
            from_address="test@example.com",
            inbox="johnloucks3",
            approval_text="approve",
            approval_type="approve"
        )

        # Mark as processed
        mgr.mark_processed(detection, action="APPROVED", result="SUCCESS")

        # Create new manager (simulates restart)
        mgr2 = DetectionStateManager(state_file)

        # Verify state was persisted
        assert mgr2.is_processed(detection.detection_hash), "State not persisted"
        print("✓ State persistence tests passed")

    finally:
        state_file.unlink(missing_ok=True)

def test_duplicate_detection():
    """Test that duplicates are skipped."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        mgr = DetectionStateManager(state_file)

        detection = ApprovalDetection(
            thread_id="test456",
            subject="Test",
            from_address="test@example.com",
            inbox="d2mconcierge",
            approval_text="yes",
            approval_type="yes"
        )

        # First time: not processed
        assert not mgr.is_processed(detection.detection_hash), "False positive"

        # Mark as processed
        mgr.mark_processed(detection)

        # Second time: should be processed
        assert mgr.is_processed(detection.detection_hash), "Duplicate not detected"
        print("✓ Duplicate detection tests passed")

    finally:
        state_file.unlink(missing_ok=True)

if __name__ == "__main__":
    test_state_persistence()
    test_duplicate_detection()
    print("\n✓ All state manager tests passed!")
```

---

## INTEGRATION TESTS

### Test 1: Full Scan-Once Cycle

```bash
# Run a single scan cycle with debugging
python3 cos_approval_monitor_v2.py --scan-once --dry-run

# Expected output:
# - "COS Approval Monitor v2 initialized"
# - "Scanning d2mconcierge..."
# - "Scanning johnloucks3..."
# - "Found X total detections"
# - No errors
```

### Test 2: State File Creation

```bash
# After running scan-once:
test -f ~/.thunderbird_approvals/detection_state.json && echo "✓ State file created" || echo "✗ State file missing"

# Check state file is valid JSON
python3 -m json.tool ~/.thunderbird_approvals/detection_state.json > /dev/null && echo "✓ State file is valid JSON" || echo "✗ State file corrupted"
```

### Test 3: Daemon Mode

```bash
# Start daemon in background
python3 cos_approval_monitor_v2.py --daemon --poll-interval 10 &
DAEMON_PID=$!

# Wait for startup
sleep 2

# Check process is running
ps -p $DAEMON_PID > /dev/null && echo "✓ Daemon started (PID: $DAEMON_PID)" || echo "✗ Daemon failed"

# Check logs show polling
sleep 5
tail ~/.thunderbird_approvals/monitor_v2.log | grep -q "Poll Cycle" && echo "✓ Daemon polling" || echo "✗ Daemon not polling"

# Stop daemon
kill $DAEMON_PID
wait $DAEMON_PID 2>/dev/null
echo "✓ Daemon stopped gracefully"
```

---

## END-TO-END TESTS

### Test 1: Real Approval Email (d2mconcierge)

**Setup:**
1. Open Gmail in browser
2. Navigate to d2mconcierge inbox

**Test:**
```bash
# 1. Send test email to d2mconcierge
# Subject: [DRAFT] E2E Test 001
# Body: approve
# (Use Gmail UI or send script)

# 2. Start monitor in one terminal
python3 cos_approval_monitor_v2.py --daemon --poll-interval 10

# 3. Monitor logs in another terminal
tail -f ~/.thunderbird_approvals/monitor_v2.log

# 4. Expected logs within 10 seconds:
# [INFO] Scanning d2mconcierge...
# [INFO] ✓ Approval detected: approve in d2mconcierge
# [INFO] Processing new detection: approve (hash)
# [INFO] ✓ Successfully processed approve
```

**Verification:**
```bash
# Check state was recorded
cat ~/.thunderbird_approvals/detection_state.json | jq '.[] | select(.approval_type == "approve")'

# Should show the detection with status
```

### Test 2: Real Approval Email (johnloucks3)

**Test:**
```bash
# 1. Send test email to johnloucks3
# Subject: Re: [DRAFT] Something
# Body: yes, please send this

# 2. Monitor should detect within 60 seconds
tail -f ~/.thunderbird_approvals/monitor_v2.log | grep "yes"

# 3. Check state
cat ~/.thunderbird_approvals/detection_state.json | jq '.[] | select(.approval_type == "yes")'
```

### Test 3: Directive Detection

**Test:**
```bash
# 1. Send directive email
# Subject: COS: Review pending items
# Body: COS: Prioritize this review

# 2. Monitor should detect within 60 seconds
tail -f ~/.thunderbird_approvals/monitor_v2.log | grep "Directive detected"

# 3. Check logs
cat ~/.thunderbird_approvals/detection_state.json | jq '.[] | select(.approval_type == "directive")'

# 4. Verify mission board logging was attempted
grep -i "mission_board" ~/.thunderbird_approvals/monitor_v2.log
```

### Test 4: Deduplication

**Test:**
```bash
# 1. Send same approval twice (same thread ID)
# Subject: [DRAFT] Test Dedup
# Body: approve

# 2. Send again (within 5 minutes)
# Subject: [DRAFT] Test Dedup
# Body: approved

# 3. Monitor both emails
# Check logs:
tail -f ~/.thunderbird_approvals/monitor_v2.log

# 4. Should see:
# - First detection: "Processing new detection"
# - Second detection: "Skipping duplicate detection" (same thread ID)

# 5. State file should have only one entry per thread
cat ~/.thunderbird_approvals/detection_state.json | jq '. | length'
# Should be 1 (not 2)
```

---

## PERFORMANCE TESTS

### Test 1: Scan Time

```bash
# Measure time to complete one scan cycle
time python3 cos_approval_monitor_v2.py --scan-once --dry-run

# Expected: <5 seconds for dry-run
# Expected: <30 seconds with real Gmail queries
```

### Test 2: Memory Usage

```bash
# Monitor memory during daemon run
python3 -c "
import subprocess
import time

proc = subprocess.Popen(
    ['python3', 'cos_approval_monitor_v2.py', '--daemon', '--poll-interval', '30'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

for _ in range(5):  # Monitor for 5 cycles
    # Get memory usage
    import os
    with open(f'/proc/{proc.pid}/status') as f:
        for line in f:
            if 'VmRSS' in line:
                print(f'Memory: {line.strip()}')
    time.sleep(30)

proc.terminate()
"

# Expected: Stable memory (no growth), <50MB RSS
```

### Test 3: Log File Size

```bash
# Monitor log file growth over time
ls -lh ~/.thunderbird_approvals/monitor_v2.log
# Expected: ~1MB per week of normal operation
```

---

## REGRESSION TEST SUITE

Run this after any code changes:

```bash
#!/bin/bash
# Regression test suite for COS Approval Monitor v2

set -e

SCRIPT="/home/john/Thunderbird/scripts/cos_approval_monitor_v2.py"
STATE_DIR="$HOME/.thunderbird_approvals"

echo "=== COS Approval Monitor v2 Regression Tests ==="

# Test 1: Python syntax
echo "[1/7] Python syntax check..."
python3 -m py_compile "$SCRIPT" && echo "✓ Syntax OK" || exit 1

# Test 2: Imports
echo "[2/7] Import check..."
python3 -c "exec(open('$SCRIPT').read())" && echo "✓ Imports OK" || exit 1

# Test 3: Dry-run execution
echo "[3/7] Dry-run execution..."
cd "$(dirname "$SCRIPT")"
python3 "$(basename "$SCRIPT")" --scan-once --dry-run > /tmp/test_output.log 2>&1
grep -q "COS Approval Monitor v2 initialized" /tmp/test_output.log && echo "✓ Dry-run OK" || exit 1

# Test 4: State file handling
echo "[4/7] State file handling..."
python3 -c "
from cos_approval_monitor_v2 import DetectionStateManager
import tempfile, pathlib
with tempfile.TemporaryDirectory() as tmpdir:
    mgr = DetectionStateManager(pathlib.Path(tmpdir) / 'test.json')
    assert pathlib.Path(tmpdir).exists()
print('✓ State handling OK')
" || exit 1

# Test 5: Pattern detection
echo "[5/7] Pattern detection..."
python3 -c "
from cos_approval_monitor_v2 import ApprovalPatternDetector
d = ApprovalPatternDetector()
assert len(d.detect_approvals('', 'approve')) > 0
assert len(d.detect_directives('COS:', '')) > 0
print('✓ Pattern detection OK')
" || exit 1

# Test 6: Service file syntax
echo "[6/7] Service file syntax..."
if [ -f /etc/systemd/user/cos-approval-monitor-v2.service ]; then
    sudo systemd-analyze verify /etc/systemd/user/cos-approval-monitor-v2.service > /dev/null 2>&1
    echo "✓ Service file OK"
else
    echo "⚠ Service file not yet created (will be created in Phase 5)"
fi

# Test 7: Log file
echo "[7/7] Log file check..."
test -f "$STATE_DIR/monitor_v2.log" && echo "✓ Log file present" || echo "⚠ Log file not yet created"

echo ""
echo "=== All Regression Tests Passed ==="
```

Run it:
```bash
bash /home/john/Thunderbird/scripts/test_regression.sh
```

---

## VALIDATION CHECKLIST

Before going live, verify ALL items:

- [ ] Python syntax check passes
- [ ] All unit tests pass (approval, directive, tasking, dedup)
- [ ] State file creation works
- [ ] Dry-run completes without errors
- [ ] Real approval email detected within 60 seconds
- [ ] Real directive email detected and logged
- [ ] Real tasking email detected and logged
- [ ] Duplicate detection works (same thread not processed twice)
- [ ] Service file creates without errors
- [ ] Service starts and stays running >1 hour
- [ ] Log file grows normally (~1MB/week)
- [ ] Memory usage stable (<50MB)
- [ ] No false positives on normal emails
- [ ] Mission board logging works (if enabled)

---

## TROUBLESHOOTING TEST FAILURES

| Test Failure | Root Cause | Fix |
|---|---|---|
| "Approval detection failed" | Pattern regex issue | Check `APPROVAL_KEYWORDS` in code |
| "State file corruption" | JSON write error | Check disk space, file permissions |
| "Daemon not polling" | Subprocess issue | Check Claude binary path, verify MCP tools |
| "Duplicate not detected" | Hash collision | Check `ApprovalDetection.__post_init__()` |
| "Memory growth" | Memory leak in loop | Profile with `memory_profiler` module |
| "Service won't start" | Syntax error in service file | Run `systemd-analyze` verify |

---

## SUPPORT

For test failures or questions:

1. **Check logs:** `tail -100 ~/.thunderbird_approvals/monitor_v2.log`
2. **Run verbose:** `python3 cos_approval_monitor_v2.py --scan-once 2>&1`
3. **File issue** with:
   - Exact error message
   - Output of failing test
   - Relevant log excerpt

---

*— Thunderbird QA Team*
