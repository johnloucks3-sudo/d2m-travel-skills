#!/usr/bin/env python3
"""
Window Recommendation Engine — Date Flexibility System
Determines client-specific timeline windows based on booking behavior profile.

Author: Thunderbird (Claude)
Date: 2026-04-08
"""

import json
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, replace
from enum import Enum


class BookingPattern(Enum):
    """Client booking behavior classification."""
    EARLY_PLANNER = "early_planner"
    MID_PLANNER = "mid_planner"
    LATE_PLANNER = "late_planner"
    UNKNOWN = "unknown"


class RiskTolerance(Enum):
    """Client's comfort with booking window timing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BudgetTier(Enum):
    """Financial tier affecting research depth and timing."""
    BUDGET = "budget"
    MID_RANGE = "mid-range"
    PREMIUM = "premium"
    LUXURY = "luxury"


@dataclass
class DecisionWindow:
    """Represents a single decision point's timing window."""
    window_start_days: int  # T-minus: earliest reasonable
    window_end_days: int    # T-minus: latest acceptable
    system_recommendation_days: int  # T-minus: recommended trigger
    rationale: str


@dataclass
class ClientProfile:
    """Client booking behavior profile."""
    client_id: str
    client_name: str
    is_first_time_cruiser: bool
    prior_bookings_count: int
    booking_behavior_pattern: BookingPattern
    risk_tolerance: RiskTolerance
    budget_tier: BudgetTier
    cruise_departure: str  # YYYY-MM-DD
    stated_preference: Optional[str] = None
    special_requirements: Optional[List[str]] = None


class WindowRecommendationEngine:
    """
    Generates client-specific timeline window recommendations.
    Uses client profile to determine when each decision should be triggered.
    """

    # Default windows (fallback for unknown profiles)
    DEFAULT_WINDOWS = {
        "flight_booking": DecisionWindow(180, 60, 120, "Standard flight booking window"),
        "hotel_research": DecisionWindow(210, 90, 150, "Standard hotel research window"),
        "excursion_research": DecisionWindow(150, 20, 90, "Standard excursion research window"),
        "dining_research": DecisionWindow(120, 30, 60, "Standard dining research window"),
        "transfer_coordination": DecisionWindow(90, 15, 45, "Standard transfer coordination window"),
        "final_confirmations": DecisionWindow(30, 7, 14, "Standard final confirmation window"),
    }

    def __init__(self):
        """Initialize the engine with recommendation rules."""
        self.rules = self._build_rules()

    def generate_recommendations(self, profile: ClientProfile) -> Dict[str, DecisionWindow]:
        """
        Generate window recommendations for a client based on their profile.

        Args:
            profile: ClientProfile object with client information

        Returns:
            Dictionary of decision_type -> DecisionWindow
        """
        recommendations = {}

        # Apply rules in sequence: booking_pattern → budget_tier → risk_tolerance → special_requirements
        for decision_type in self.DEFAULT_WINDOWS.keys():
            window = self._calculate_window(decision_type, profile)
            recommendations[decision_type] = window

        return recommendations

    def _calculate_window(self, decision_type: str, profile: ClientProfile) -> DecisionWindow:
        """
        Calculate recommended window for a single decision type.
        Applies multiple rules in sequence.
        """
        base_window = copy.copy(self.DEFAULT_WINDOWS[decision_type])

        # Rule 1: Booking pattern adjustment
        pattern_adjustment = self.rules.get("booking_pattern", {}).get(
            profile.booking_behavior_pattern.value, {}
        )
        if decision_type in pattern_adjustment:
            adjustment = pattern_adjustment[decision_type]
            base_window.system_recommendation_days = adjustment.get(
                "recommended", base_window.system_recommendation_days
            )
            base_window.window_start_days = adjustment.get(
                "start", base_window.window_start_days
            )
            base_window.window_end_days = adjustment.get(
                "end", base_window.window_end_days
            )
            base_window.rationale = adjustment.get("rationale", base_window.rationale)

        # Rule 2: First-time vs repeat cruiser
        if profile.is_first_time_cruiser and decision_type in ["excursion_research", "dining_research"]:
            # First-timers need more guidance
            base_window.window_start_days += 30  # Push start earlier
            base_window.system_recommendation_days = max(
                base_window.window_end_days + 10,
                base_window.system_recommendation_days + 20
            )
            base_window.rationale = "First-time cruiser — earlier research for maximum guidance"

        # Rule 3: Budget tier adjustment
        tier_adjustment = self.rules.get("budget_tier", {}).get(
            profile.budget_tier.value, {}
        )
        if decision_type in tier_adjustment:
            adjustment = tier_adjustment[decision_type]
            recommended = adjustment.get("recommended", base_window.system_recommendation_days)
            base_window.system_recommendation_days = recommended
            base_window.rationale = adjustment.get("rationale", base_window.rationale)

        # Rule 4: Risk tolerance
        if profile.risk_tolerance == RiskTolerance.LOW:
            # Conservative clients book early
            base_window.system_recommendation_days = base_window.window_start_days - 10
            base_window.rationale = "Low risk tolerance — push earlier in window"
        elif profile.risk_tolerance == RiskTolerance.HIGH:
            # Aggressive clients wait until last moment
            base_window.system_recommendation_days = base_window.window_end_days + 5
            base_window.rationale = "High risk tolerance — book closer to deadline"

        # Rule 5: Stated preference override
        if profile.stated_preference:
            # Log but don't auto-override (Commander makes final call)
            base_window.rationale += f" [Client stated: {profile.stated_preference}]"

        return base_window

    def _build_rules(self) -> Dict:
        """Build recommendation rules matrix."""
        return {
            "booking_pattern": {
                BookingPattern.EARLY_PLANNER.value: {
                    "flight_booking": {
                        "recommended": 150,
                        "start": 180,
                        "end": 60,
                        "rationale": "Early planner — book at T-150 for best options"
                    },
                    "hotel_research": {
                        "recommended": 170,
                        "rationale": "Early planner — start hotel research early"
                    },
                    "excursion_research": {
                        "recommended": 120,
                        "rationale": "Early planner — time for thorough excursion review"
                    }
                },
                BookingPattern.MID_PLANNER.value: {
                    "flight_booking": {
                        "recommended": 120,
                        "rationale": "Mid planner — book at T-120 for good options"
                    },
                    "excursion_research": {
                        "recommended": 90,
                        "rationale": "Mid planner — excursion research mid-window"
                    }
                },
                BookingPattern.LATE_PLANNER.value: {
                    "flight_booking": {
                        "recommended": 80,
                        "rationale": "Late planner — book at T-80 (last-minute preference)"
                    },
                    "hotel_research": {
                        "recommended": 100,
                        "rationale": "Late planner — compress hotel research"
                    },
                    "excursion_research": {
                        "recommended": 50,
                        "rationale": "Late planner — final-window excursion decisions"
                    }
                }
            },
            "budget_tier": {
                BudgetTier.BUDGET.value: {
                    "flight_booking": {
                        "recommended": 100,
                        "rationale": "Budget tier — book late for discounts"
                    },
                    "excursion_research": {
                        "recommended": 60,
                        "rationale": "Budget tier — research close to departure"
                    }
                },
                BudgetTier.PREMIUM.value: {
                    "flight_booking": {
                        "recommended": 150,
                        "rationale": "Premium tier — early booking for best cabins/options"
                    },
                    "excursion_research": {
                        "recommended": 120,
                        "rationale": "Premium tier — thorough excursion research"
                    },
                    "dining_research": {
                        "recommended": 70,
                        "rationale": "Premium tier — early dining reservations"
                    }
                },
                BudgetTier.LUXURY.value: {
                    "flight_booking": {
                        "recommended": 160,
                        "rationale": "Luxury tier — earliest booking for concierge coordination"
                    },
                    "excursion_research": {
                        "recommended": 140,
                        "rationale": "Luxury tier — concierge curated options"
                    },
                    "dining_research": {
                        "recommended": 80,
                        "rationale": "Luxury tier — exclusive dining coordination"
                    }
                }
            }
        }

    def validate_window(self, decision_type: str, commander_set_days: int,
                       window: DecisionWindow) -> Tuple[bool, Optional[str]]:
        """
        Validate that Commander's chosen date is within acceptable bounds.

        Args:
            decision_type: The decision being set
            commander_set_days: T-minus days Commander chose
            window: The DecisionWindow bounds

        Returns:
            (is_valid, error_message)
        """
        if commander_set_days > window.window_start_days:
            return False, f"Date too early: {commander_set_days} days > window start {window.window_start_days}"
        if commander_set_days < window.window_end_days:
            return False, f"Date too late: {commander_set_days} days < window end {window.window_end_days}"
        return True, None

    def calculate_actual_date(self, cruise_departure: str, t_minus_days: int) -> str:
        """
        Convert T-minus days to actual calendar date.

        Args:
            cruise_departure: Departure date (YYYY-MM-DD)
            t_minus_days: T-minus days to subtract

        Returns:
            Actual trigger date (YYYY-MM-DD)
        """
        departure = datetime.strptime(cruise_departure, "%Y-%m-%d")
        trigger_date = departure - timedelta(days=t_minus_days)
        return trigger_date.strftime("%Y-%m-%d")

    def export_profile_to_json(self, profile: ClientProfile) -> Dict:
        """Export client profile to JSON-serializable dict."""
        return {
            "client_id": profile.client_id,
            "client_name": profile.client_name,
            "booking_date": datetime.now().isoformat(),
            "cruise_departure": profile.cruise_departure,
            "profile": {
                "is_first_time_cruiser": profile.is_first_time_cruiser,
                "prior_bookings": profile.prior_bookings_count,
                "booking_behavior_pattern": profile.booking_behavior_pattern.value,
                "risk_tolerance": profile.risk_tolerance.value,
                "budget_tier": profile.budget_tier.value,
                "stated_preference": profile.stated_preference,
                "special_requirements": profile.special_requirements or []
            }
        }

    def export_recommendations_to_json(self, recommendations: Dict[str, DecisionWindow]) -> Dict:
        """Export recommendations to JSON-serializable dict."""
        return {
            decision_type: {
                "window_start_days": window.window_start_days,
                "window_end_days": window.window_end_days,
                "system_recommendation_days": window.system_recommendation_days,
                "rationale": window.rationale
            }
            for decision_type, window in recommendations.items()
        }


def create_test_profiles() -> Dict[str, ClientProfile]:
    """Create test profiles for Kuklinski and Westbrook."""
    return {
        "kuklinski_group": ClientProfile(
            client_id="kuklinski_group",
            client_name="Kuklinski Group",
            is_first_time_cruiser=True,
            prior_bookings_count=0,
            booking_behavior_pattern=BookingPattern.UNKNOWN,
            risk_tolerance=RiskTolerance.MEDIUM,
            budget_tier=BudgetTier.MID_RANGE,
            cruise_departure="2026-07-15",  # ~3.5 months out
            stated_preference="Need guidance — first time cruisers",
            special_requirements=["educational_content_needed", "transfer_assistance"]
        ),
        "westbrook_brent_kim": ClientProfile(
            client_id="westbrook_brent_kim",
            client_name="Brent & Kim Westbrook",
            is_first_time_cruiser=False,
            prior_bookings_count=1,
            booking_behavior_pattern=BookingPattern.EARLY_PLANNER,
            risk_tolerance=RiskTolerance.MEDIUM,
            budget_tier=BudgetTier.PREMIUM,
            cruise_departure="2026-04-23",  # 16 days out
            stated_preference="Want best flight options, willing to book early",
            special_requirements=["pilot_client_premium_experience"]
        )
    }


if __name__ == "__main__":
    """Test the engine with sample profiles."""
    engine = WindowRecommendationEngine()
    test_profiles = create_test_profiles()

    for profile_id, profile in test_profiles.items():
        print(f"\n{'='*60}")
        print(f"CLIENT: {profile.client_name}")
        print(f"{'='*60}")

        recommendations = engine.generate_recommendations(profile)

        for decision_type, window in recommendations.items():
            actual_date = engine.calculate_actual_date(profile.cruise_departure, window.system_recommendation_days)
            print(f"\n{decision_type.upper()}")
            print(f"  Window: T-{window.window_start_days} to T-{window.window_end_days}")
            print(f"  Recommended: T-{window.system_recommendation_days} ({actual_date})")
            print(f"  Rationale: {window.rationale}")
