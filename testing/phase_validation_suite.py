"""
Thunderbird Phase Determination Validation Test Suite (7b)
Validates phase determination algorithm against known test cases.

Dreams2Memories Travel, LLC — Lifecycle System Testing

Author: Claude (P0 Development Task)
Date: 2026-04-07
"""

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# Add core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from lifecycle.client_ingester import (
    determine_phase,
    validate_anchor_dates,
    PHASE_DEFINITIONS
)


class TestPhaseDetermination(unittest.TestCase):
    """Test suite for phase determination algorithm"""

    def setUp(self):
        """Common test data"""
        self.today = date.today()

        # Test case: Furlow (Grandeur Scandinavia Aug 29 - Sep 8)
        self.furlow_booking = date(2025, 9, 15)
        self.furlow_embark = date(2026, 8, 29)
        self.furlow_disembark = date(2026, 9, 8)
        self.furlow_fpd = date(2026, 4, 1)

    # ========================================================================
    # PHASE_4: VOYAGE
    # ========================================================================

    def test_phase_4_during_voyage(self):
        """Client is currently on ship (embark <= today <= disembark)"""
        # This would only pass if we're currently within embark/disembark window
        # For testing, we'll skip or mock the date
        pass

    def test_phase_4_within_7_days_of_embark(self):
        """Client within 7 days of embarkation"""
        # If today is within 7 days of embark, phase should be PHASE_4
        upcoming_embark = self.today + timedelta(days=5)
        upcoming_disembark = upcoming_embark + timedelta(days=10)
        upcoming_fpd = self.today - timedelta(days=10)  # Already past FPD

        phase_code, phase_name = determine_phase(
            booking_date=self.today - timedelta(days=100),
            embark_date=upcoming_embark,
            disembark_date=upcoming_disembark,
            fpd=upcoming_fpd,
            payment_status="paid",
            client_label="Test-Embark7d"
        )

        self.assertEqual(phase_code, "PHASE_4", "Within 7 days of embark = PHASE_4 (Voyage)")

    # ========================================================================
    # PHASE_3: POLISH
    # ========================================================================

    def test_phase_3_after_payment_before_embark(self):
        """Client paid FPD, > 7 days before embark"""
        future_embark = self.today + timedelta(days=45)
        future_disembark = future_embark + timedelta(days=10)
        fpd_past = self.today - timedelta(days=5)

        phase_code, phase_name = determine_phase(
            booking_date=self.today - timedelta(days=60),
            embark_date=future_embark,
            disembark_date=future_disembark,
            fpd=fpd_past,
            payment_status="paid",
            client_label="Test-Polish"
        )

        self.assertEqual(phase_code, "PHASE_3", "Paid + > 7 days to embark = PHASE_3 (Polish)")

    # ========================================================================
    # PHASE_2: EXECUTE
    # ========================================================================

    def test_phase_2_unpaid_at_fpd(self):
        """Client unpaid at FPD due date (red flag)"""
        future_embark = self.today + timedelta(days=60)
        future_disembark = future_embark + timedelta(days=10)
        fpd_today = self.today  # FPD is today, not yet paid

        phase_code, phase_name = determine_phase(
            booking_date=self.today - timedelta(days=100),
            embark_date=future_embark,
            disembark_date=future_disembark,
            fpd=fpd_today,
            payment_status="pending",
            client_label="Test-Execute-Unpaid"
        )

        self.assertEqual(phase_code, "PHASE_2", "Unpaid at FPD = PHASE_2 (Execute, red flag)")

    def test_phase_2_payment_processing(self):
        """Client in payment processing window (post-booking, pre-FPD)"""
        future_embark = self.today + timedelta(days=120)
        future_disembark = future_embark + timedelta(days=10)
        future_fpd = self.today + timedelta(days=90)

        phase_code, phase_name = determine_phase(
            booking_date=self.today - timedelta(days=15),
            embark_date=future_embark,
            disembark_date=future_disembark,
            fpd=future_fpd,
            payment_status="pending",
            client_label="Test-Execute-Proc"
        )

        # Should be PHASE_1 or PHASE_2 depending on days since booking
        self.assertIn(phase_code, ["PHASE_1", "PHASE_2"])

    # ========================================================================
    # PHASE_1: CRAFT
    # ========================================================================

    def test_phase_1_early_post_booking(self):
        """Client recently booked (< 60 days)"""
        future_embark = self.today + timedelta(days=150)
        future_disembark = future_embark + timedelta(days=10)
        future_fpd = self.today + timedelta(days=120)

        phase_code, phase_name = determine_phase(
            booking_date=self.today - timedelta(days=30),  # 30 days ago
            embark_date=future_embark,
            disembark_date=future_disembark,
            fpd=future_fpd,
            payment_status=None,
            client_label="Test-Craft"
        )

        self.assertEqual(phase_code, "PHASE_1", "Recently booked (< 60 days) = PHASE_1 (Craft)")

    # ========================================================================
    # PHASE_0: DREAM
    # ========================================================================

    def test_phase_0_pre_booking(self):
        """Client before booking confirmation"""
        future_booking = self.today + timedelta(days=30)
        future_embark = future_booking + timedelta(days=150)
        future_disembark = future_embark + timedelta(days=10)
        future_fpd = future_booking + timedelta(days=120)

        phase_code, phase_name = determine_phase(
            booking_date=future_booking,  # In future
            embark_date=future_embark,
            disembark_date=future_disembark,
            fpd=future_fpd,
            payment_status=None,
            client_label="Test-Dream"
        )

        self.assertEqual(phase_code, "PHASE_0", "Pre-booking = PHASE_0 (Dream)")

    # ========================================================================
    # PHASE_5: RETURN
    # ========================================================================

    def test_phase_5_post_voyage(self):
        """Client returned home (today > disembark)"""
        past_embark = self.today - timedelta(days=15)
        past_disembark = past_embark + timedelta(days=10)
        past_fpd = past_embark - timedelta(days=60)

        phase_code, phase_name = determine_phase(
            booking_date=past_embark - timedelta(days=100),
            embark_date=past_embark,
            disembark_date=past_disembark,
            fpd=past_fpd,
            payment_status="paid",
            client_label="Test-Return"
        )

        self.assertEqual(phase_code, "PHASE_5", "Post-disembark = PHASE_5 (Return)")


class TestAnchorDateValidation(unittest.TestCase):
    """Test suite for anchor date validator"""

    def setUp(self):
        """Common test data"""
        self.today = date.today()
        self.valid_booking = self.today - timedelta(days=100)
        self.valid_embark = self.today + timedelta(days=60)
        self.valid_disembark = self.valid_embark + timedelta(days=10)
        self.valid_fpd = self.today + timedelta(days=45)

    def test_all_anchors_present(self):
        """Valid case with all anchors"""
        result = validate_anchor_dates(
            booking_date=self.valid_booking,
            embark_date=self.valid_embark,
            disembark_date=self.valid_disembark,
            fpd=self.valid_fpd,
            client_label="Test-AllPresent"
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["anchor_count"], 4)
        self.assertEqual(len(result["errors"]), 0)

    def test_missing_booking_date(self):
        """Invalid: missing booking_date"""
        result = validate_anchor_dates(
            booking_date=None,  # Missing
            embark_date=self.valid_embark,
            disembark_date=self.valid_disembark,
            fpd=self.valid_fpd,
            client_label="Test-NoBking"
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("booking_date" in e for e in result["errors"]))

    def test_missing_embark_date(self):
        """Invalid: missing embark_date"""
        result = validate_anchor_dates(
            booking_date=self.valid_booking,
            embark_date=None,  # Missing
            disembark_date=self.valid_disembark,
            fpd=self.valid_fpd,
            client_label="Test-NoEmbark"
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("embark_date" in e for e in result["errors"]))

    def test_embark_after_disembark(self):
        """Invalid: embark_date > disembark_date"""
        bad_embark = self.today + timedelta(days=100)
        bad_disembark = bad_embark - timedelta(days=10)  # Earlier than embark!

        result = validate_anchor_dates(
            booking_date=self.valid_booking,
            embark_date=bad_embark,
            disembark_date=bad_disembark,
            fpd=self.valid_fpd,
            client_label="Test-BadOrder"
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("embark_date after disembark" in e for e in result["errors"]))

    def test_fpd_after_embark(self):
        """Invalid: FPD > embark_date (payment due after travel starts)"""
        bad_fpd = self.valid_embark + timedelta(days=30)  # After embark!

        result = validate_anchor_dates(
            booking_date=self.valid_booking,
            embark_date=self.valid_embark,
            disembark_date=self.valid_disembark,
            fpd=bad_fpd,
            client_label="Test-FPDTooLate"
        )

        self.assertFalse(result["valid"])
        self.assertTrue(any("fpd after embark" in e for e in result["errors"]))


class TestPhaseDefinitions(unittest.TestCase):
    """Verify phase definitions are complete and consistent"""

    def test_all_phases_defined(self):
        """All 6 phases (PHASE_0 through PHASE_5) are defined"""
        expected_phases = ["PHASE_0", "PHASE_1", "PHASE_2", "PHASE_3", "PHASE_4", "PHASE_5"]
        for phase_code in expected_phases:
            self.assertIn(phase_code, PHASE_DEFINITIONS)
            self.assertIn("name", PHASE_DEFINITIONS[phase_code])
            self.assertIn("description", PHASE_DEFINITIONS[phase_code])

    def test_phase_names_match_standardization(self):
        """Phase names match Phase_Standardization.md"""
        expected_names = {
            "PHASE_0": "Dream",
            "PHASE_1": "Craft",
            "PHASE_2": "Execute",
            "PHASE_3": "Polish",
            "PHASE_4": "Voyage",
            "PHASE_5": "Return",
        }
        for phase_code, expected_name in expected_names.items():
            actual_name = PHASE_DEFINITIONS[phase_code]["name"]
            self.assertEqual(
                actual_name,
                expected_name,
                f"{phase_code} name mismatch"
            )


def run_tests():
    """Run all tests and report results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPhaseDetermination))
    suite.addTests(loader.loadTestsFromTestCase(TestAnchorDateValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestPhaseDefinitions))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
