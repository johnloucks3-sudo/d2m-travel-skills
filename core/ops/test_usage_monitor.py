#!/usr/bin/env python3
"""
Test suite for Claude usage monitoring system
Dreams2Memories Travel, LLC

Run all tests:
  python3 test_usage_monitor.py

Run specific test:
  python3 test_usage_monitor.py test_active_block
"""

import json
import sys
from pathlib import Path
from subprocess import run

# ── Import monitors ────────────────────────────────────────────────────────

try:
    from thunderbird_usage_monitor import (
        get_active_block,
        get_weekly_data,
        SESSION_LIMIT,
        WEEKLY_LIMIT_ALL,
    )
except ImportError as e:
    print(f"ERROR: Cannot import monitor: {e}")
    sys.exit(1)

# ── Tests ──────────────────────────────────────────────────────────────────

class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def pass_test(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail_test(self, name: str, reason: str):
        self.failed += 1
        print(f"  ❌ {name}: {reason}")

    def skip_test(self, name: str, reason: str):
        self.skipped += 1
        print(f"  ⏭️  {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        status = "✅ PASS" if self.failed == 0 else "❌ FAIL"
        print(f"\n{status} | {self.passed}/{total} passed")
        return self.failed == 0


results = TestResults()


def test_ccusage_available():
    """Test that ccusage CLI is installed."""
    print("\n[ccusage availability]")
    result = run(["which", "ccusage"], capture_output=True)
    if result.returncode == 0:
        results.pass_test("ccusage installed")
    else:
        results.fail_test("ccusage installed", "ccusage not found in PATH")


def test_active_block():
    """Test getting active block."""
    print("\n[Active block detection]")
    block = get_active_block()

    if block is None:
        results.skip_test("Active block detected", "No active block (expected outside usage window)")
        return

    # Verify structure
    required_keys = ["totalTokens", "costUSD", "startTime", "endTime"]
    missing = [k for k in required_keys if k not in block]

    if missing:
        results.fail_test("Block structure", f"Missing keys: {missing}")
        return

    tokens = block.get("totalTokens", 0)
    if tokens < 0 or tokens > SESSION_LIMIT * 2:  # sanity check
        results.fail_test("Token count sanity", f"Tokens {tokens} out of reasonable range")
        return

    results.pass_test("Active block detected and valid")


def test_weekly_data():
    """Test getting weekly data."""
    print("\n[Weekly data retrieval]")
    weekly = get_weekly_data()

    if not weekly:
        results.skip_test("Weekly data available", "No weekly data")
        return

    # Verify structure
    required_keys = ["total_tokens", "cost_usd"]
    missing = [k for k in required_keys if k not in weekly]

    if missing:
        results.fail_test("Weekly structure", f"Missing keys: {missing}")
        return

    tokens = weekly.get("total_tokens", 0)
    if tokens < 0:
        results.fail_test("Weekly tokens sanity", "Negative token count")
        return

    # Check percentages
    all_pct = weekly.get("all_pct", 0)
    if all_pct < 0 or all_pct > 150:  # allow >100% for burst
        results.fail_test("Weekly percentage sanity", f"Percentage {all_pct}% out of range")
        return

    results.pass_test("Weekly data valid")


def test_model_breakdown():
    """Test per-model breakdown in weekly data."""
    print("\n[Model breakdown]")
    weekly = get_weekly_data()

    if not weekly:
        results.skip_test("Model breakdown", "No weekly data")
        return

    total = weekly.get("total_tokens", 0)
    opus = weekly.get("opus_tokens", 0)
    sonnet = weekly.get("sonnet_tokens", 0)
    haiku = weekly.get("haiku_tokens", 0)

    breakdown_total = opus + sonnet + haiku

    if total > 0 and breakdown_total == 0:
        results.fail_test("Model breakdown", "Total > 0 but no breakdown")
        return

    if breakdown_total > total * 1.05:  # allow 5% rounding error
        results.fail_test("Model breakdown", f"Breakdown {breakdown_total} > total {total}")
        return

    results.pass_test("Model breakdown consistent")


def test_threshold_classification():
    """Test percentage to level conversion."""
    print("\n[Threshold classification]")
    from thunderbird_usage_monitor import _level, WARN_PCT, CRIT_PCT, STOP_PCT

    tests = [
        (50, "ok"),
        (WARN_PCT, "WARN"),
        (CRIT_PCT, "CRIT"),
        (STOP_PCT, "STOP"),
        (100, "STOP"),
    ]

    all_pass = True
    for pct, expected in tests:
        result = _level(pct)
        if result != expected:
            results.fail_test(f"Level classification at {pct}%", f"Got {result}, expected {expected}")
            all_pass = False

    if all_pass:
        results.pass_test("Threshold classification (all thresholds correct)")


def test_json_export():
    """Test JSON export of monitor output."""
    print("\n[JSON export]")
    result = run(
        ["python3", "thunderbird_usage_monitor.py", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        results.fail_test("JSON export", f"Command failed: {result.stderr}")
        return

    # Extract JSON from mixed output (human-readable output + JSON)
    lines = result.stdout.split('\n')
    json_start = -1
    for i, line in enumerate(lines):
        if line.startswith('{'):
            json_start = i
            break

    if json_start == -1:
        results.fail_test("JSON export", "No JSON found in output")
        return

    try:
        json_text = '\n'.join(lines[json_start:])
        data = json.loads(json_text)
        if "session" in data or "weekly" in data:
            results.pass_test("JSON export valid")
        else:
            results.fail_test("JSON export", "Missing expected keys")
    except json.JSONDecodeError as e:
        results.fail_test("JSON export", f"Invalid JSON: {e}")


def test_monitor_execution():
    """Test that monitor can run without errors."""
    print("\n[Monitor execution]")
    result = run(
        ["python3", "thunderbird_usage_monitor.py"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        results.fail_test("Monitor execution", f"Exit code {result.returncode}")
        return

    if "Session Block" in result.stdout or "Weekly" in result.stdout:
        results.pass_test("Monitor executes successfully")
    else:
        results.skip_test("Monitor execution", "No output (expected if no usage)")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    """Run all tests."""
    print("═" * 70)
    print("CLAUDE USAGE MONITOR — TEST SUITE")
    print("═" * 70)

    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        test_func = globals().get(f"test_{test_name}")
        if test_func:
            test_func()
        else:
            print(f"Unknown test: {test_name}")
            sys.exit(1)
    else:
        # Run all tests
        test_ccusage_available()
        test_active_block()
        test_weekly_data()
        test_model_breakdown()
        test_threshold_classification()
        test_json_export()
        test_monitor_execution()

    # Print summary
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
