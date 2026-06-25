#!/usr/bin/env python3
"""
HALE BUS TEST HARNESS

Validates bus functionality: write, read, state sharing.

Usage:
    python3 core/hale_bus/test_hale_bus.py
"""

import json
import tempfile
from pathlib import Path

# For testing, we'll use temp directory
TEMP_BUS_PATH = None


def test_bus_write():
    """Test: write instance state to bus."""
    from core.hale_bus.hale_bus_write import write_bus_state

    print("✓ Testing bus write...")
    bus_state = write_bus_state(
        instance_type="claude_code",
        open_missions=["MISSION-317", "MISSION-318"],
        active_projects=["PROJ-MCLEOD-2984034-FPD"],
        alerts=[{"severity": "P0", "msg": "Test alert"}],
    )

    assert "hale_instances" in bus_state
    assert bus_state["hale_instances"]["claude_code"]["status"] == "ONLINE"
    assert len(bus_state["hale_instances"]["claude_code"]["open_missions"]) == 2
    print("  ✅ Bus write successful")
    return bus_state


def test_bus_read():
    """Test: read instance state from bus."""
    from core.hale_bus.hale_bus_read import (
        read_bus_state,
        get_other_instances_state,
        get_fpd_alerts,
    )

    print("✓ Testing bus read...")
    bus_state = read_bus_state()

    assert "hale_instances" in bus_state
    print("  ✅ Bus read successful")

    # Test: get other instances
    others = get_other_instances_state(exclude_instance="claude_code")
    assert isinstance(others, dict)
    print(f"  ✅ Found {len(others)} other instances")

    # Test: get FPD alerts
    fpds = get_fpd_alerts()
    assert isinstance(fpds, list)
    print(f"  ✅ Found {len(fpds)} FPD alerts")


def test_startup_brief():
    """Test: generate startup brief."""
    from core.hale_bus.hale_bus_read import startup_brief

    print("✓ Testing startup brief...")
    brief = startup_brief("opencode")

    assert isinstance(brief, str)
    assert len(brief) > 0
    print(f"  ✅ Brief generated ({len(brief)} chars)")
    return brief


def test_checkpoint():
    """Test: checkpoint session state."""
    from core.hale_bus.hale_bus_write import checkpoint_session

    print("✓ Testing checkpoint...")
    bus_state = checkpoint_session(instance_type="deepseek_telegram")

    assert bus_state is not None
    assert "hale_instances" in bus_state
    print("  ✅ Checkpoint successful")


def main():
    """Run all tests."""
    print("\n⚡ HALE BUS TEST SUITE")
    print("=" * 50)

    tests = [
        ("Bus Write", test_bus_write),
        ("Bus Read", test_bus_read),
        ("Startup Brief", test_startup_brief),
        ("Checkpoint", test_checkpoint),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n{name}:")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
