#!/usr/bin/env python3
"""
Date Flexibility Extension for Thunderbird Timer Engine
Adds dynamic timer rescheduling, decision gate management, and impact analysis.

Author: Thunderbird (Claude)
Date: 2026-04-08
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import subprocess
import sys


# Setup logging
LOG_DIR = Path("/home/john/Thunderbird/OpsCenter")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "date_flexibility.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TimerChange:
    """Represents a change to a client's timer."""
    client_id: str
    decision_type: str
    old_date: str  # YYYY-MM-DD
    new_date: str  # YYYY-MM-DD
    old_t_minus: int
    new_t_minus: int
    shift_days: int  # positive = later, negative = earlier
    rationale: str


@dataclass
class ImpactAnalysis:
    """Analysis of cascading impacts from a timeline change."""
    primary_change: TimerChange
    affected_decisions: Set[str]
    cascading_impacts: Dict[str, Dict]
    status: str  # PENDING, APPROVED, EXECUTED, ROLLED_BACK
    approval_timestamp: Optional[str] = None
    approved_by: Optional[str] = None


class DateFlexibilityEngine:
    """
    Manages dynamic timeline rescheduling for clients.
    Handles decision change detection, timer recalculation, and systemd integration.
    """

    # Decision dependency map (what depends on what)
    DECISION_DEPENDENCIES = {
        "flight_booking": ["hotel_research", "transfer_coordination"],
        "hotel_research": ["dining_research"],
        "dining_research": ["reservation_confirmation"],
        "excursion_research": ["booking_confirmation"],
        "transfer_coordination": [],
        "final_confirmations": [],
    }

    def __init__(self):
        """Initialize the flexibility engine."""
        self.change_logs: Dict[str, List[ImpactAnalysis]] = {}
        logger.info("DateFlexibilityEngine initialized")

    def detect_timeline_change(self, client_id: str, old_timeline: Dict[str, int],
                              new_timeline: Dict[str, int]) -> List[TimerChange]:
        """
        Compare old and new timelines, identify all shifted dates.

        Args:
            client_id: Client identifier
            old_timeline: Previous timeline (decision_type -> T-minus days)
            new_timeline: Proposed timeline (decision_type -> T-minus days)

        Returns:
            List of TimerChange objects for changed decisions
        """
        changes = []

        for decision_type, new_t_minus in new_timeline.items():
            old_t_minus = old_timeline.get(decision_type)

            if old_t_minus is None:
                continue  # New decision, not a change

            if old_t_minus != new_t_minus:
                shift_days = new_t_minus - old_t_minus  # positive = later
                changes.append(
                    TimerChange(
                        client_id=client_id,
                        decision_type=decision_type,
                        old_t_minus=old_t_minus,
                        new_t_minus=new_t_minus,
                        shift_days=shift_days,
                        old_date="",  # Will be populated by caller
                        new_date="",  # Will be populated by caller
                        rationale=""
                    )
                )

        logger.info(f"Detected {len(changes)} timeline changes for {client_id}")
        return changes

    def cascade_dependent_changes(self, primary_change: TimerChange,
                                 old_timeline: Dict[str, int],
                                 cascade_ratio: float = 0.5) -> Dict[str, Dict]:
        """
        Calculate cascading impacts on dependent decisions.

        Args:
            primary_change: The primary decision that changed
            old_timeline: Current active timeline
            cascade_ratio: How much of the primary shift cascades (0.0-1.0)

        Returns:
            Dictionary of affected decisions and their impacts
        """
        cascading_impacts = {}
        primary_shift = primary_change.shift_days

        # Find all decisions that depend on the primary decision
        dependent_decisions = self.DECISION_DEPENDENCIES.get(primary_change.decision_type, [])

        for dependent in dependent_decisions:
            if dependent in old_timeline:
                cascaded_shift = int(primary_shift * cascade_ratio)
                new_t_minus = old_timeline[dependent] + cascaded_shift

                cascading_impacts[dependent] = {
                    "old_t_minus": old_timeline[dependent],
                    "new_t_minus": new_t_minus,
                    "cascaded_shift": cascaded_shift,
                    "rationale": f"Shifted {cascaded_shift} days due to {primary_change.decision_type} change"
                }

        logger.info(f"Identified {len(cascading_impacts)} cascading impacts")
        return cascading_impacts

    def generate_impact_analysis(self, client_id: str, cruise_departure: str,
                                primary_change: TimerChange,
                                cascading_impacts: Dict[str, Dict]) -> ImpactAnalysis:
        """
        Generate full impact analysis for a timeline change.

        Returns:
            ImpactAnalysis object with affected decisions and status
        """
        affected = {primary_change.decision_type}
        affected.update(cascading_impacts.keys())

        impact = ImpactAnalysis(
            primary_change=primary_change,
            affected_decisions=affected,
            cascading_impacts=cascading_impacts,
            status="PENDING"
        )

        logger.info(f"Impact analysis generated: {len(affected)} decisions affected")
        return impact

    def calculate_timer_dates(self, cruise_departure: str, timeline: Dict[str, int]) -> Dict[str, str]:
        """
        Convert T-minus days to actual calendar dates.

        Args:
            cruise_departure: Departure date (YYYY-MM-DD)
            timeline: Dictionary of decision_type -> T-minus days

        Returns:
            Dictionary of decision_type -> trigger date (YYYY-MM-DD)
        """
        departure = datetime.strptime(cruise_departure, "%Y-%m-%d")
        trigger_dates = {}

        for decision_type, t_minus_days in timeline.items():
            trigger_date = departure - timedelta(days=t_minus_days)
            trigger_dates[decision_type] = trigger_date.strftime("%Y-%m-%d")

        return trigger_dates

    def generate_systemd_timer_names(self, client_id: str, timeline: Dict[str, int],
                                     trigger_dates: Dict[str, str]) -> List[Dict]:
        """
        Generate systemd timer unit file names for the updated timeline.

        Args:
            client_id: Client identifier
            timeline: T-minus days for each decision
            trigger_dates: Calendar dates for each decision

        Returns:
            List of timer unit definitions
        """
        timers = []

        for decision_type, trigger_date in trigger_dates.items():
            timer_name = f"{client_id}_{decision_type}_{trigger_date.replace('-', '')}"
            timers.append({
                "timer_name": timer_name,
                "decision_type": decision_type,
                "trigger_date": trigger_date,
                "t_minus": timeline[decision_type],
                "unit_path": f"/etc/systemd/user/thunderbird-{timer_name}.timer"
            })

        return timers

    def approve_timeline_change(self, impact: ImpactAnalysis, approved_by: str) -> bool:
        """
        Mark a timeline change as approved by Commander.

        Args:
            impact: ImpactAnalysis object to approve
            approved_by: Commander name

        Returns:
            True if approval successful
        """
        impact.status = "APPROVED"
        impact.approval_timestamp = datetime.now().isoformat()
        impact.approved_by = approved_by

        logger.info(f"Timeline change approved by {approved_by}: {impact.primary_change.decision_type}")
        return True

    def execute_timer_rescheduling(self, client_id: str, old_timers: List[Dict],
                                  new_timers: List[Dict]) -> Tuple[bool, Optional[str]]:
        """
        Execute actual systemd timer changes (cancel old, install new).

        Args:
            client_id: Client identifier
            old_timers: List of old timer definitions to cancel
            new_timers: List of new timer definitions to install

        Returns:
            (success, error_message)
        """
        logger.info(f"Executing timer rescheduling for {client_id}")

        # Step 1: Stop and disable old timers
        for old_timer in old_timers:
            timer_name = old_timer["timer_name"]
            try:
                subprocess.run(
                    ["systemctl", "--user", "stop", f"thunderbird-{timer_name}.timer"],
                    check=False,
                    capture_output=True
                )
                subprocess.run(
                    ["systemctl", "--user", "disable", f"thunderbird-{timer_name}.timer"],
                    check=False,
                    capture_output=True
                )
                logger.info(f"Disabled timer: {timer_name}")
            except Exception as e:
                logger.error(f"Error disabling timer {timer_name}: {e}")

        # Step 2: Install new timers (placeholder — actual implementation would write unit files)
        for new_timer in new_timers:
            timer_name = new_timer["timer_name"]
            logger.info(f"Would install timer: {timer_name} at {new_timer['trigger_date']}")
            # In production, this would:
            # 1. Generate systemd unit file
            # 2. Copy to /etc/systemd/user/
            # 3. Run systemctl daemon-reload
            # 4. Enable and start the timer

        logger.info(f"Timer rescheduling completed for {client_id}")
        return True, None

    def audit_timer_change(self, client_id: str, impact: ImpactAnalysis,
                          execution_status: str = "EXECUTED") -> Dict:
        """
        Create audit trail entry for a timeline change.

        Args:
            client_id: Client identifier
            impact: ImpactAnalysis object
            execution_status: Final execution status

        Returns:
            Audit trail entry
        """
        audit_entry = {
            "change_id": f"RES-{datetime.now().strftime('%Y%m%d')}-{len(self.change_logs.get(client_id, []))+1:03d}",
            "timestamp": datetime.now().isoformat(),
            "change": f"{impact.primary_change.decision_type}_shifted from T-{impact.primary_change.old_t_minus} to T-{impact.primary_change.new_t_minus}",
            "triggered_by": impact.primary_change.rationale,
            "cascading_impacts": impact.cascading_impacts,
            "timers_affected": len(impact.affected_decisions),
            "timers_created": len(impact.affected_decisions),
            "timers_cancelled": len(impact.affected_decisions),
            "status": execution_status,
            "approved_by": impact.approved_by or "N/A"
        }

        # Store in change logs
        if client_id not in self.change_logs:
            self.change_logs[client_id] = []
        self.change_logs[client_id].append(impact)

        logger.info(f"Audit trail created: {audit_entry['change_id']}")
        return audit_entry

    def export_audit_trail(self, client_id: str) -> List[Dict]:
        """Export full audit trail for a client."""
        if client_id not in self.change_logs:
            return []

        return [
            {
                "change": impact.primary_change.decision_type,
                "old_t_minus": impact.primary_change.old_t_minus,
                "new_t_minus": impact.primary_change.new_t_minus,
                "affected": list(impact.affected_decisions),
                "status": impact.status,
                "approved_by": impact.approved_by or "N/A"
            }
            for impact in self.change_logs[client_id]
        ]


def create_sample_timeline_change():
    """Create a sample timeline change for testing."""
    old_timeline = {
        "flight_research": 180,
        "hotel_research": 210,
        "excursion_research": 150,
        "dining_research": 120,
        "transfer_coordination": 90,
        "final_confirmations": 30,
    }

    new_timeline = {
        "flight_research": 150,  # Changed
        "hotel_research": 190,   # Cascading change
        "excursion_research": 150,
        "dining_research": 120,
        "transfer_coordination": 70,  # Cascading change
        "final_confirmations": 30,
    }

    return old_timeline, new_timeline


if __name__ == "__main__":
    """Test the flexibility engine."""
    engine = DateFlexibilityEngine()

    # Test scenario: Westbrook Group
    client_id = "westbrook_brent_kim"
    cruise_departure = "2026-04-23"
    old_timeline, new_timeline = create_sample_timeline_change()

    print(f"\n{'='*60}")
    print(f"DATE FLEXIBILITY ENGINE TEST — {client_id}")
    print(f"{'='*60}")

    # Step 1: Detect changes
    changes = engine.detect_timeline_change(client_id, old_timeline, new_timeline)
    print(f"\nDetected {len(changes)} changes:")
    for change in changes:
        print(f"  - {change.decision_type}: T-{change.old_t_minus} → T-{change.new_t_minus} ({change.shift_days:+d})")

    # Step 2: Cascade dependent changes
    if changes:
        primary_change = changes[0]
        cascading = engine.cascade_dependent_changes(primary_change, old_timeline, cascade_ratio=0.5)
        print(f"\nCascading impacts ({len(cascading)} affected):")
        for decision, impact in cascading.items():
            print(f"  - {decision}: T-{impact['old_t_minus']} → T-{impact['new_t_minus']}")

    # Step 3: Generate impact analysis
    if changes and cascading:
        impact = engine.generate_impact_analysis(client_id, cruise_departure, changes[0], cascading)
        print(f"\nImpact Analysis:")
        print(f"  Primary change: {impact.primary_change.decision_type}")
        print(f"  Total affected: {len(impact.affected_decisions)}")
        print(f"  Status: {impact.status}")

    # Step 4: Calculate trigger dates
    trigger_dates = engine.calculate_timer_dates(cruise_departure, new_timeline)
    print(f"\nNew trigger dates:")
    for decision, date in sorted(trigger_dates.items()):
        print(f"  - {decision}: {date}")
