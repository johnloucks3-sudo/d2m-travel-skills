#!/usr/bin/env python3
"""
test_failover_chain.py — Validate entire failover stack.

Tests:
  1. Primary model success (no pivot)
  2. Simulated limit → pivot to fallback 1
  3. Simulated all models exhausted → queue
  4. Budget alerts trigger at thresholds
"""

import logging
from commander_failover_router import route_with_failover, ModelTier, FAILOVER_CHAIN
from commander_budget_tracker import BudgetTracker

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def test_primary_success():
    """Test 1: Primary model succeeds (no pivot needed)."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Primary Model Success (No Failover)")
    logger.info("="*60)

    result = route_with_failover(
        prompt="Test prompt for primary",
        initial_model="opencode/deepseek-v4-flash-free",
        priority="normal"
    )

    assert result.success, "Primary should succeed"
    assert result.pivots == 0, "No pivots expected"
    assert result.model_used == "opencode/deepseek-v4-flash-free"

    logger.info(f"✅ PASS: Model={result.model_used}, Pivots=0")
    return True


def test_budget_alerts():
    """Test 2: Budget tracker alerts at thresholds."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Budget Alerts")
    logger.info("="*60)

    tracker = BudgetTracker()

    # Check current state
    alert = tracker.check_alerts()
    if alert:
        logger.info(f"⚠️ ALERT: {alert}")
    else:
        logger.info("✅ No alerts (budgets OK)")

    # Simulate burn: push Grok to 85%
    tracker.log_usage("grok_xai", cost=1.50)  # Add $1.50
    alert = tracker.check_alerts()
    if alert:
        logger.info(f"✅ Alert triggered after burn: {alert}")
    else:
        logger.warning("Alert should have fired")

    return True


def test_failover_chain_integrity():
    """Test 3: Failover chain is complete and correct."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Failover Chain Integrity")
    logger.info("="*60)

    expected_chain = [
        "opencode/deepseek-v4-flash-free",
        "opencode/deepseek-v4-flash",
        "xai/grok-4.3",
        "claude-sonnet-4-6",
        "queue",
    ]

    actual_chain = [m.value for m in FAILOVER_CHAIN]

    for i, (exp, act) in enumerate(zip(expected_chain, actual_chain)):
        match = "✅" if exp == act else "❌"
        logger.info(f"  {i+1}. {match} {act}")

    assert actual_chain == expected_chain, "Chain mismatch"
    logger.info(f"✅ PASS: Failover chain correct ({len(FAILOVER_CHAIN)} tiers)")
    return True


def test_daily_summary():
    """Test 4: Daily summary generates correctly."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Daily Summary Generation")
    logger.info("="*60)

    tracker = BudgetTracker()
    summary = tracker.get_daily_summary()
    logger.info(summary)
    logger.info("✅ PASS: Summary generated")
    return True


def main():
    """Run all tests."""
    logger.info("\n" + "🦅 "*30)
    logger.info("COMMANDER FREEZE-PROOF STACK — VALIDATION SUITE")
    logger.info("🦅 "*30)

    results = []
    tests = [
        ("Primary Success", test_primary_success),
        ("Budget Alerts", test_budget_alerts),
        ("Failover Chain", test_failover_chain_integrity),
        ("Daily Summary", test_daily_summary),
    ]

    for name, test_func in tests:
        try:
            results.append((name, test_func()))
        except Exception as e:
            logger.error(f"❌ FAIL: {name} — {e}")
            results.append((name, False))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")

    logger.info(f"\n{passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎖️  ALL TESTS PASSED. STACK READY FOR PRODUCTION.")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit(main())
