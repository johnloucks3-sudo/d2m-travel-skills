"""
wing_decision_engine.py — Thunderbird Autonomy Decision Engine
==============================================================
Callable by any service. Answers: "Should I auto-execute, send a silent
FYI alert, or stop and wait for Commander approval?"

Decision Levels:
  AUTO  — Execute immediately, no alert needed
  FYI   — Execute, send silent Telegram notification
  WAIT  — Do NOT execute. Queue for Commander approval via Telegram.

Standing Orders encoded here:
  SO 21 MAR 2026 — Client send gate
  SO 24 MAR 2026 — Email account separation / within-wing exception
  SO 27 MAR 2026 — Intel full send

Usage:
    from OpsCenter.wing_decision_engine import decide, DecisionLevel
    d = decide("send_client_email", {"recipient": "furlow@example.com"})
    if d.level == DecisionLevel.WAIT:
        queue_for_approval(action, d.reason)
    elif d.level == DecisionLevel.FYI:
        execute_and_notify(action, d.reason)
    else:
        execute_silently(action)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# ── Paths ──
ROOT = Path(__file__).resolve().parent.parent
MODE_FILE = ROOT / "logs" / "system_mode.json"

# ── Addresses that are within-wing (free to send) ──
WING_ADDRESSES = {
    "johnloucks3@gmail.com",
    "d2mconcierge@gmail.com",
}


class DecisionLevel(str, Enum):
    AUTO = "AUTO"   # Execute silently
    FYI  = "FYI"    # Execute + send Telegram notification
    WAIT = "WAIT"   # Do NOT execute — queue for Commander approval


@dataclass
class Decision:
    level: DecisionLevel
    reason: str
    so_ref: str = ""    # Standing Order reference if applicable

    def is_auto(self)  -> bool: return self.level == DecisionLevel.AUTO
    def is_fyi(self)   -> bool: return self.level == DecisionLevel.FYI
    def is_wait(self)  -> bool: return self.level == DecisionLevel.WAIT

    def __str__(self) -> str:
        ref = f" [{self.so_ref}]" if self.so_ref else ""
        return f"{self.level.value}: {self.reason}{ref}"


# ─────────────────────────────────────────────────────────────────────────────
# ACTION REGISTRY
# Each entry: action_key → (default_level, reason, so_ref)
# Action keys are lowercase strings used by callers.
# ─────────────────────────────────────────────────────────────────────────────
_REGISTRY: dict[str, tuple[DecisionLevel, str, str]] = {

    # ── AUTO: Read / Scan / Compute (no state change) ──
    "intel_sweep":          (DecisionLevel.AUTO, "Intel sweeps are autonomous", "SO 27 MAR 2026"),
    "world_intel_sweep":    (DecisionLevel.AUTO, "Intel sweeps are autonomous", "SO 27 MAR 2026"),
    "ship_intel_sweep":     (DecisionLevel.AUTO, "Intel sweeps are autonomous", "SO 27 MAR 2026"),
    "price_check":          (DecisionLevel.AUTO, "Price checks are autonomous", ""),
    "fare_watch_check":     (DecisionLevel.AUTO, "Fare watch polling is autonomous", ""),
    "weather_check":        (DecisionLevel.AUTO, "Weather/NOAA checks are autonomous", ""),
    "travel_advisory_check":(DecisionLevel.AUTO, "Travel advisory checks are autonomous", ""),
    "dossier_scan":         (DecisionLevel.AUTO, "Dossier gap scans are autonomous", ""),
    "email_classify":       (DecisionLevel.AUTO, "Email classification is autonomous", ""),
    "inbox_sweep":          (DecisionLevel.AUTO, "Inbox sweeps are autonomous", ""),
    "file_cleanup":         (DecisionLevel.AUTO, "File cleanup is autonomous", ""),
    "log_rotate":           (DecisionLevel.AUTO, "Log rotation is autonomous", ""),
    "drive_sync":           (DecisionLevel.AUTO, "Drive sync is autonomous", ""),
    "health_check":         (DecisionLevel.AUTO, "Health checks are autonomous", ""),
    "code_fix":             (DecisionLevel.AUTO, "Code fixes are autonomous per Commander grant", ""),
    "anchor_scan":          (DecisionLevel.AUTO, "Anchor date scans are autonomous", ""),
    "x_osint_sweep":        (DecisionLevel.AUTO, "X/OSINT sweeps are autonomous", "SO 27 MAR 2026"),
    "morning_briefing":     (DecisionLevel.AUTO, "Morning brief sends autonomously to johnloucks3", "SO 27 MAR 2026"),
    "innovation_scan":      (DecisionLevel.AUTO, "Innovation scans send autonomously", "SO 27 MAR 2026"),
    "fpd_alert":            (DecisionLevel.AUTO, "FPD alerts send autonomously to johnloucks3", "SO 27 MAR 2026"),
    "heartbeat":            (DecisionLevel.AUTO, "Wing heartbeat sends autonomously", "SO 27 MAR 2026"),
    "blackboard_sync":      (DecisionLevel.AUTO, "Blackboard sync is autonomous", ""),
    "chatlog_backup":       (DecisionLevel.AUTO, "Chat log backup is autonomous", ""),

    # ── FYI: State changes that Commander should know about ──
    "draft_created":        (DecisionLevel.FYI, "Draft created — notify Commander, no approval needed", ""),
    "dossier_updated":      (DecisionLevel.FYI, "Dossier updated — notify Commander", ""),
    "calendar_event_added": (DecisionLevel.FYI, "Calendar event added — notify Commander", ""),
    "booking_data_updated": (DecisionLevel.FYI, "Booking data updated — notify Commander", ""),
    "fare_drop_detected":   (DecisionLevel.FYI, "Fare drop detected — notify Commander", ""),
    "task_completed":       (DecisionLevel.FYI, "Task completed — notify Commander", ""),

    # ── WAIT: External sends / financial / client-facing ──
    "send_client_email":    (DecisionLevel.WAIT, "Client emails require Commander approval", "SO 21 MAR 2026"),
    "send_client_sms":      (DecisionLevel.WAIT, "Client SMS requires Commander approval", "SO 21 MAR 2026"),
    "send_client_whatsapp": (DecisionLevel.WAIT, "Client WhatsApp requires Commander approval", "SO 21 MAR 2026"),
    "financial_transaction":(DecisionLevel.WAIT, "Financial transactions require Commander approval", ""),
    "booking_commit":       (DecisionLevel.WAIT, "Booking commitments require Commander approval", ""),
    "external_commit":      (DecisionLevel.WAIT, "External commitments require Commander approval", ""),
    "new_client_contact":   (DecisionLevel.WAIT, "New client relationships require Commander first contact", ""),
    "strategy_change":      (DecisionLevel.WAIT, "Strategy changes require Commander decision", ""),
    "send_external_email":  (DecisionLevel.WAIT, "External emails require Commander approval", "SO 21 MAR 2026"),
}


def decide(action: str, context: dict | None = None) -> Decision:
    """
    Return a Decision for the given action.

    Special context keys:
      "recipient" — email address being sent to (auto-promotes within-wing sends)
      "system_mode" — override system mode check (GREEN/YELLOW/RED)

    Examples:
      decide("intel_sweep")                             → AUTO
      decide("send_client_email")                       → WAIT
      decide("send_external_email", {"recipient": "johnloucks3@gmail.com"})  → AUTO
      decide("draft_created", {"client": "Furlow"})    → FYI
    """
    ctx = context or {}
    action_lower = action.lower().replace("-", "_").replace(" ", "_")

    # ── Special case: within-wing email sends are AUTO ──
    if action_lower in ("send_external_email", "send_client_email", "gmail_send"):
        recipient = ctx.get("recipient", "")
        if recipient in WING_ADDRESSES:
            return Decision(
                level=DecisionLevel.AUTO,
                reason=f"Within-wing address {recipient} — auto-send permitted",
                so_ref="SO 24 MAR 2026",
            )

    # ── Look up registry ──
    if action_lower in _REGISTRY:
        level, reason, so_ref = _REGISTRY[action_lower]

        # ── In RED system mode: downgrade FYI→WAIT for state changes ──
        mode = _get_system_mode()
        if mode == "RED" and level == DecisionLevel.FYI:
            return Decision(
                level=DecisionLevel.WAIT,
                reason=f"System in RED mode — holding '{action}' for Commander review. Original: {reason}",
                so_ref=so_ref,
            )

        return Decision(level=level, reason=reason, so_ref=so_ref)

    # ── Unknown action: default to FYI (safe — notify but don't block) ──
    return Decision(
        level=DecisionLevel.FYI,
        reason=f"Unknown action '{action}' — defaulting to FYI (safe default)",
        so_ref="",
    )


def get_decision_matrix() -> dict[str, str]:
    """Return the full decision matrix as action → level mapping."""
    return {k: v[0].value for k, v in _REGISTRY.items()}


def _get_system_mode() -> str:
    """Read current system mode from watchdog's mode file. Defaults to GREEN."""
    try:
        if MODE_FILE.exists():
            data = json.loads(MODE_FILE.read_text())
            return data.get("mode", "GREEN")
    except Exception:
        pass
    return "GREEN"


def is_auto(action: str, context: dict | None = None) -> bool:
    return decide(action, context).is_auto()


def requires_approval(action: str, context: dict | None = None) -> bool:
    return decide(action, context).is_wait()


if __name__ == "__main__":
    # Self-test
    tests = [
        ("intel_sweep", {}),
        ("send_client_email", {"recipient": "furlow@example.com"}),
        ("send_external_email", {"recipient": "johnloucks3@gmail.com"}),
        ("morning_briefing", {}),
        ("draft_created", {"client": "Furlow"}),
        ("financial_transaction", {}),
        ("unknown_action_xyz", {}),
    ]
    print("Wing Decision Engine — self-test\n")
    for action, ctx in tests:
        d = decide(action, ctx)
        print(f"  {action:35s} → {d}")
