#!/usr/bin/env python3
"""
hale_tier_enforcer.py — Hale Autonomy Tier Enforcement
=======================================================
Implements the four-tier task classification and enforcement system defined in
SO 29 APR 2026 and hale_cos.md.

TIER DEFINITIONS:
  T1 — Execute + Report:      Full auto. No gate. Pure ops.
  T2 — Execute + Notify:      Execute immediately, log autonomous decision after.
  T3 — Propose + Hold:        Do NOT execute. Write proposal to wing_comms.md.
  T4 — Flag Only:             Do NOT execute. Log BLOCKER. Await Commander direction.

THE FOUR GENUINE COMMANDER GATES (T3/T4 triggers):
  1. Send to a client (WF-17) — anything client-facing
  2. Financial commitment / spend
  3. New client relationship (first contact)
  4. Strategy direction change

WITHIN-WING EXCEPTION (SO 24 MAR 2026):
  Sends to johnloucks3@gmail.com and d2mconcierge@gmail.com are T1 — free within wing.
  Only external client sends trigger T3.

T2 RATIONALE (anything autonomous but worth a notify):
  Supplier contact, file deletion, staff tasking, schedule changes, modifications
  to standing artifacts (dossiers, configs, templates). Documented here for COS
  review — not buried.

Author: Col Victoria "Iron Vic" Hale — Thunderbird Wing
Version: 1.0 | 2026-05-04
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# ─── Constants ────────────────────────────────────────────────────────────────

WING_COMMS_PATH = Path("/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md")
WITHIN_WING_ADDRESSES = {
    "johnloucks3@gmail.com",
    "d2mconcierge@gmail.com",
    "johnloucks3",
    "d2mconcierge",
}

# ─── Tier Keyword Patterns ────────────────────────────────────────────────────

TIER_KEYWORDS: dict[str, list[str]] = {

    # ── T3/T4 Patterns: The Four Commander Gates ────────────────────────────

    # Gate 1: Send to a client (WF-17)
    # Includes email send, SMS, proposal delivery, quote delivery, client notification.
    # EXCLUDES within-wing sends (johnloucks3, d2mconcierge).
    "CLIENT_SEND": [
        r"send.*email.*to.*client",
        r"send.*proposal.*to",
        r"email.*client",
        r"send.*client",
        r"deliver.*to.*client",
        r"send.*quote.*to",
        r"send.*itinerary.*to",
        r"client.*email.*send",
        r"send.*confirmation.*to.*client",
        r"forward.*to.*client",
        r"send.*to\s+\w+\s+client",
        r"client.*notification.*send",
        r"send.*sms.*to.*client",
        r"whatsapp.*client",
        r"first.*contact.*client",          # catches "make first contact" as well
        r"reach.*out.*to.*client",
        r"contact.*new.*client",
    ],

    # Gate 2: Financial commitment / spend
    "FINANCIAL": [
        r"pay\b",
        r"payment",
        r"deposit",
        r"charge\b",
        r"purchase\b",
        r"spend\b",
        r"invoice\b",
        r"commit.*financial",
        r"financial.*commit",
        r"transfer.*funds",
        r"wire.*transfer",
        r"credit.*card.*charge",
        r"approve.*charge",
        r"authorize.*payment",
        r"book.*and.*pay",
        r"\$\d",                             # dollar amount present
        r"\d+.*usd",
        r"\d+.*dollar",
        r"budget.*approval",
        r"expense.*approval",
    ],

    # Gate 3: New client relationship (first contact)
    "NEW_CLIENT": [
        r"new.*client.*onboard",
        r"onboard.*new.*client",
        r"first.*contact.*with",
        r"initial.*outreach",
        r"first.*touch.*client",
        r"welcome.*new.*client",
        r"create.*client.*profile",
        r"add.*new.*client",
        r"intake.*new.*client",
    ],

    # Gate 4: Strategy direction change
    "STRATEGY": [
        r"pivot.*strategy",
        r"strategy.*change",
        r"change.*strategy",
        r"strategic.*direction",
        r"direction.*change",
        r"new.*strategy",
        r"overhaul.*approach",
        r"reposition.*brand",
        r"brand.*pivot",
        r"business.*model.*change",
        r"market.*pivot",
        r"exit.*market",
        r"enter.*market",
        r"discontinue.*service",
        r"launch.*new.*service",
        r"restructure.*wing",
        r"restructure.*staff",
    ],

    # ── T2 Patterns: Execute + Notify (autonomous decisions worth flagging) ──
    # Supplier contact, file deletion, dossier/config mods, staff tasking,
    # schedule changes, standing artifact modifications.
    "T2_AUTONOMOUS": [
        r"contact.*supplier",
        r"supplier.*contact",
        r"email.*supplier",
        r"email.*vendor",
        r"contact.*vendor",
        r"vendor.*contact",
        r"delete.*file",
        r"remove.*file",
        r"archive.*file",
        r"purge.*files",
        r"clean.*up.*files",
        r"delete.*dossier",
        r"modify.*dossier",
        r"update.*dossier",
        r"task.*staff",
        r"assign.*task",
        r"dispatch.*task",
        r"reschedule.*task",
        r"schedule.*change",
        r"modify.*schedule",
        r"update.*config",
        r"modify.*config",
        r"change.*config",
        r"update.*template",
        r"modify.*template",
        r"update.*standing.*order",
        r"modify.*standing.*order",
        r"restart.*service",
        r"restart.*daemon",
        r"deploy.*change",
    ],
}

# Compile all patterns at module load for speed
_COMPILED: dict[str, list[re.Pattern]] = {
    gate: [re.compile(p, re.IGNORECASE) for p in patterns]
    for gate, patterns in TIER_KEYWORDS.items()
}


# ─── Classification ───────────────────────────────────────────────────────────

def _is_within_wing(task_description: str) -> bool:
    """Return True if the task targets a within-wing address (never T3 on these)."""
    task_lower = task_description.lower()
    for addr in WITHIN_WING_ADDRESSES:
        if addr.lower() in task_lower:
            return True
    return False


def classify_tier(task_description: str) -> str:
    """
    Classify a task description into T1 / T2 / T3 / T4.

    Logic (in priority order):
      1. Check T4 gates: strategy direction — flag only, Commander must decide.
      2. Check T3 gates: client send (excl. within-wing), financial, new client.
      3. Check T2: autonomous decisions worth notifying (supplier, deletions, etc.)
      4. Default: T1 — full auto.

    Returns: "T1" | "T2" | "T3" | "T4"
    """
    task_lower = task_description.lower()

    # ── T4: Strategy direction (always flag-only, no exceptions) ──
    for pattern in _COMPILED["STRATEGY"]:
        if pattern.search(task_lower):
            return "T4"

    # ── T3: Financial commitment / spend ──
    for pattern in _COMPILED["FINANCIAL"]:
        if pattern.search(task_lower):
            return "T3"

    # ── T3: New client relationship ──
    for pattern in _COMPILED["NEW_CLIENT"]:
        if pattern.search(task_lower):
            return "T3"

    # ── T3: Client send — but ONLY if NOT within-wing ──
    client_send_match = any(
        p.search(task_lower) for p in _COMPILED["CLIENT_SEND"]
    )
    if client_send_match and not _is_within_wing(task_description):
        return "T3"

    # ── T2: Autonomous decisions worth notifying ──
    for pattern in _COMPILED["T2_AUTONOMOUS"]:
        if pattern.search(task_lower):
            return "T2"

    # ── T1: Everything else — full auto ──
    return "T1"


# ─── Enforcement ──────────────────────────────────────────────────────────────

def _write_proposal(task_description: str, tier: str) -> None:
    """Append a T3/T4 proposal block to wing_comms.md."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = (
        f"\n\n---\n"
        f"## [{tier}] HELD FOR COMMANDER REVIEW — {ts}\n\n"
        f"**Task:** {task_description}\n\n"
        f"**Status:** Hale tier enforcer held this action pending Commander direction.\n"
        f"**Required:** Commander approval before execution.\n"
    )
    try:
        WING_COMMS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(WING_COMMS_PATH, "a", encoding="utf-8") as f:
            f.write(block)
    except Exception as e:
        # Log but don't crash
        try:
            from core.ops.hale_activity_logger import error_logged
            error_logged("wing_comms write failed", detail=str(e), source="tier_enforcer")
        except Exception:
            pass


def enforce_tier(
    task_description: str,
    action_fn: Callable = None,
    *args: Any,
    **kwargs: Any,
) -> dict:
    """
    Execute action_fn (or hold/flag it) based on tier classification.

    Args:
        task_description: Human-readable description of the task.
        action_fn:        Callable to execute for T1/T2 tasks. Optional —
                          T3/T4 callers need not supply one (it won't be called).
                          T1/T2 callers with no action_fn return status "classified"
                          so the caller can dispatch its own way.
        *args, **kwargs:  Passed through to action_fn.

    Returns:
        dict with keys: tier, status, and tier-appropriate payload.

    Tier behaviors:
        T1 — Execute action_fn if provided; else return {"status":"classified"}.
        T2 — Execute action_fn if provided, log autonomous_decision. Else classify-only.
        T3 — DO NOT execute. Write proposal to wing_comms.md. Return held status.
        T4 — DO NOT execute. Log BLOCKER. Return flagged status.
    """
    tier = classify_tier(task_description)

    # ── T1: Full auto ──────────────────────────────────────────────────────
    if tier == "T1":
        if action_fn is None:
            return {"tier": "T1", "status": "classified", "result": None}
        try:
            result = action_fn(*args, **kwargs)
            return {"tier": "T1", "status": "executed", "result": result}
        except Exception as e:
            try:
                from core.ops.hale_activity_logger import error_logged
                error_logged(
                    "T1 execution error",
                    detail=f"task='{task_description}' | error={e}",
                    source="tier_enforcer",
                )
            except Exception:
                pass
            return {"tier": "T1", "status": "executed_error", "error": str(e)}

    # ── T2: Execute + Notify ───────────────────────────────────────────────
    if tier == "T2":
        if action_fn is None:
            try:
                from core.ops.hale_activity_logger import autonomous_decision
                autonomous_decision(
                    title=f"T2 classified (no action): {task_description[:80]}",
                    detail="Tier classified T2; no action_fn supplied — caller must execute.",
                    source="tier_enforcer",
                )
            except Exception:
                pass
            return {"tier": "T2", "status": "classified", "result": None}
        try:
            result = action_fn(*args, **kwargs)
            try:
                from core.ops.hale_activity_logger import autonomous_decision
                autonomous_decision(
                    title=f"T2 autonomous action: {task_description[:80]}",
                    detail="Executed without prior approval. Result logged.",
                    source="tier_enforcer",
                )
            except Exception:
                pass
            return {"tier": "T2", "status": "executed_notify", "result": result}
        except Exception as e:
            try:
                from core.ops.hale_activity_logger import error_logged
                error_logged(
                    "T2 execution error",
                    detail=f"task='{task_description}' | error={e}",
                    source="tier_enforcer",
                )
            except Exception:
                pass
            return {"tier": "T2", "status": "executed_error", "error": str(e)}

    # ── T3: Propose + Hold ─────────────────────────────────────────────────
    if tier == "T3":
        _write_proposal(task_description, "T3")
        try:
            from core.ops.hale_activity_logger import blocker_logged
            blocker_logged(
                title=f"T3 held: {task_description[:80]}",
                detail="Action requires Commander review. Proposal written to wing_comms.md.",
                source="tier_enforcer",
            )
        except Exception:
            pass
        return {
            "tier": "T3",
            "status": "held_for_review",
            "proposal": task_description,
        }

    # ── T4: Flag Only ──────────────────────────────────────────────────────
    if tier == "T4":
        _write_proposal(task_description, "T4")
        try:
            from core.ops.hale_activity_logger import blocker_logged
            blocker_logged(
                title=f"T4 flagged: {task_description[:80]}",
                detail="Strategy direction change — requires Commander direction. No action taken.",
                source="tier_enforcer",
            )
        except Exception:
            pass
        return {
            "tier": "T4",
            "status": "flagged",
            "reason": "Requires Commander direction",
        }

    # Should never reach here
    return {"tier": "UNKNOWN", "status": "error", "error": "Tier classification returned unexpected value"}


# ─── Self-Test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure imports resolve from project root regardless of cwd
    _project_root = str(Path(__file__).resolve().parents[2])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    from core.ops.hale_activity_logger import autonomous_decision, blocker_logged  # noqa: F401 — force import check

    print("=" * 60)
    print("HALE TIER ENFORCER — Self-Test")
    print("=" * 60)

    test_cases = [
        # (description, expected_tier, mock_action_should_run)
        (
            "Run morning intel sweep and summarize cruise line news",
            "T1",
            True,
            "Pure ops — intel scan, no gate trigger",
        ),
        (
            "Send daily report to johnloucks3@gmail.com",
            "T1",
            True,
            "Within-wing exception — NOT a client send, T1 free",
        ),
        (
            "Delete archived dossier files older than 90 days",
            "T2",
            True,
            "File deletion — autonomous decision worth notifying",
        ),
        (
            "Send proposal email to client McLeod for Scandinavia cruise",
            "T3",
            False,
            "WF-17 gate — external client send",
        ),
        (
            "Pay $2,500 deposit to Silversea for McLeod booking",
            "T3",
            False,
            "Financial commitment — Commander gate",
        ),
        (
            "Pivot D2M strategy toward river cruises and exit ocean cruise market",
            "T4",
            False,
            "Strategy direction change — flag only",
        ),
        (
            "Send Furlow confirmation email to client",
            "T3",
            False,
            "T3 with no action_fn supplied — should hold without TypeError",
        ),
    ]

    all_passed = True
    action_calls: list[str] = []

    def mock_action(label: str):
        """Dummy action that records it was called."""
        action_calls.append(label)
        return f"mock_result:{label}"

    for i, (task, expected_tier, should_run, note) in enumerate(test_cases, 1):
        action_calls.clear()
        # Last test case verifies None-action path — don't pass mock_action
        if i == len(test_cases):
            result = enforce_tier(task)  # no action_fn
        else:
            result = enforce_tier(task, mock_action, task)
        actual_tier = result.get("tier")
        was_run = bool(action_calls)
        tier_ok = actual_tier == expected_tier
        run_ok = was_run == should_run

        status_icon = "PASS" if (tier_ok and run_ok) else "FAIL"
        if not (tier_ok and run_ok):
            all_passed = False

        print(f"\n[{i}] {status_icon}")
        print(f"  Task   : {task[:65]}...")
        print(f"  Note   : {note}")
        print(f"  Tier   : got={actual_tier}  expected={expected_tier}  {'OK' if tier_ok else 'WRONG'}")
        print(f"  Run    : got={was_run}  expected={should_run}  {'OK' if run_ok else 'WRONG'}")
        print(f"  Status : {result.get('status')}")

    print("\n" + "=" * 60)
    print(f"RESULT: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 60)

    # Verify within-wing edge case independently
    ww_cases = [
        "Send morning brief to johnloucks3",
        "Email d2mconcierge with intel summary",
        "Send report to johnloucks3@gmail.com",
    ]
    print("\nWithin-Wing Edge Cases (all should be T1):")
    for ww in ww_cases:
        t = classify_tier(ww)
        icon = "OK" if t == "T1" else "FAIL"
        print(f"  [{icon}] T={t} | {ww}")
