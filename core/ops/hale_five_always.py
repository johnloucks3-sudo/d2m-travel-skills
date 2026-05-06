#!/usr/bin/env python3
"""
hale_five_always.py — Five Always Pre-Auth Wiring
Dreams2Memories Travel, LLC · Thunderbird Wing

Implements SO 29 APR 2026: Five "Always" standing orders that are pre-authorized —
no Commander confirmation required. Used by the dispatcher to skip the confirmation gate.

Usage:
    from core.ops.hale_five_always import is_preauthorized, apply_always

    authorized, name = is_preauthorized(task_description)
    if authorized:
        result = apply_always(always_id, context=task_description)
        # proceed without confirmation gate
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Five Always Registry
# ---------------------------------------------------------------------------

FIVE_ALWAYS: list[dict] = [
    {
        "id": 1,
        "name": "staff_drafts_to_johnloucks3",
        "description": (
            "Staff drafts to johnloucks3 are auto-approved. "
            "No COS review gate within the wing inbox."
        ),
        "trigger_patterns": [
            r"(?i)(draft|send|email|forward).*johnloucks3",
            r"(?i)johnloucks3.*(draft|send|brief|report|intel|sitrep)",
            r"(?i)staff\s+(brief|report|draft|sitrep)\b",
            r"(?i)(morning\s+brief|daily\s+brief|intel\s+report)\b",
        ],
        "bypass_gate": True,
    },
    {
        "id": 2,
        "name": "mcp_to_python_pivot",
        "description": (
            "MCP-to-Python substitution — auto-pivot. "
            "If MCP fails or can't spawn but Python achieves the outcome, "
            "pivot without asking."
        ),
        "trigger_patterns": [
            r"(?i)mcp\s*(fail|down|unavailable|error|timeout)",
            r"(?i)pivot\s+to\s+python",
            r"(?i)mcp.*not\s+(available|working|responding)",
            r"(?i)(fallback|substitute)\s+(to\s+)?python",
            r"(?i)mcp\s+tool\s+(fail|unavailable|broke)",
        ],
        "bypass_gate": True,
    },
    {
        "id": 3,
        "name": "spot_it_fix_it",
        "description": (
            "Spot-it-fix-it. The instant a blocker is identified, attempt an immediate "
            "fix (or spawn a fix worker). Do not surface the problem alone."
        ),
        "trigger_patterns": [
            r"(?i)\bblocker\b",
            r"(?i)stuck\s+on\b",
            r"(?i)spawn\s+(a\s+)?fix(\s+worker)?",
            r"(?i)(blocking|blocked)\s+(issue|task|process)",
            r"(?i)immediate\s+fix",
            r"(?i)fix\s+worker",
        ],
        "bypass_gate": True,
    },
    {
        "id": 4,
        "name": "root_cause_priority",
        "description": (
            "Root-cause priority. When the source of a problem is identifiable, "
            "fix the source — never the symptom."
        ),
        "trigger_patterns": [
            r"(?i)root\s+cause",
            r"(?i)fix\s+the\s+source",
            r"(?i)underlying\s+(issue|problem|cause|fault)",
            r"(?i)(source|origin)\s+of\s+(the\s+)?(problem|issue|bug|error)",
            r"(?i)not\s+(just\s+)?the\s+symptom",
        ],
        "bypass_gate": True,
    },
    {
        "id": 5,
        "name": "ioi_creation",
        "description": (
            "IOI creation — no hesitation. Internal Operating Instructions for models, "
            "staff, decision trees, and procedures are written proactively. "
            "No permission required."
        ),
        "trigger_patterns": [
            r"(?i)\bIOI\b",
            r"(?i)internal\s+operating\s+instruction",
            r"(?i)write\s+(an?\s+)?IOI",
            r"(?i)create\s+(an?\s+)?(procedure|sop|operating\s+instruction)",
            r"(?i)(draft|write|create)\s+(staff\s+)?procedure",
            r"(?i)proactive\s+(procedure|instruction|sop|doc)",
        ],
        "bypass_gate": True,
    },
]

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _compile_patterns(always_entry: dict) -> list[re.Pattern]:
    """Compile regex patterns for a given always entry (cached at call time)."""
    return [re.compile(p) for p in always_entry["trigger_patterns"]]


def check_always_applies(task_description: str) -> Optional[dict]:
    """
    Returns the matching FIVE_ALWAYS entry if the task description matches
    a pre-authorized pattern, else None.

    This function is pure / idempotent — it does NOT write to the activity log.
    Used by dispatcher to determine whether to skip the confirmation gate.
    """
    if not task_description:
        return None

    for entry in FIVE_ALWAYS:
        for pattern in _compile_patterns(entry):
            if pattern.search(task_description):
                return entry

    return None


def is_preauthorized(task_description: str) -> tuple[bool, str]:
    """
    Returns (True, always_name) if a pre-auth always applies,
    (False, "") if not.

    Drop-in check for dispatcher gate logic:
        authorized, name = is_preauthorized(task_description)
        if authorized:
            result = apply_always(...)
    """
    match = check_always_applies(task_description)
    if match:
        return True, match["name"]
    return False, ""


# ---------------------------------------------------------------------------
# Apply pre-auth action
# ---------------------------------------------------------------------------

def apply_always(always_id: int, context: str = "") -> dict:
    """
    Execute the pre-authorized action for the given always_id.
    Logs a DECISION event to the activity log.

    Returns a dict with 'action' and 'gate_bypass' keys.
    Always 3 (spot-it-fix-it) also logs a BLOCKER event.
    """
    # Lazy import so logger errors never crash the caller
    try:
        from core.ops.hale_activity_logger import log_event, blocker_logged
    except ImportError:
        # Fallback stubs when running outside the package
        def log_event(category, title, detail="", source="", level="INFO"):  # type: ignore
            print(f"[LOG] [{category}] {title} | {detail}")

        def blocker_logged(title, detail="", source=""):  # type: ignore
            print(f"[LOG] [BLOCKER] {title} | {detail}")

    entry = next((e for e in FIVE_ALWAYS if e["id"] == always_id), None)
    if entry is None:
        return {"action": "unknown_always_id", "gate_bypass": False, "error": f"No always with id={always_id}"}

    always_name = entry["name"]

    # --- Per-always action logic ---

    if always_id == 1:
        result = {"action": "send_to_johnloucks3", "gate_bypass": True}

    elif always_id == 2:
        result = {"action": "pivot_to_python", "gate_bypass": True}

    elif always_id == 3:
        # Log the blocker first, then return fix-worker action
        blocker_logged(
            title=f"Blocker identified — spot-it-fix-it triggered",
            detail=context or "No additional context provided",
            source="hale_five_always",
        )
        result = {"action": "spawn_fix_worker", "gate_bypass": True}

    elif always_id == 4:
        result = {"action": "investigate_root_cause", "gate_bypass": True}

    elif always_id == 5:
        result = {"action": "write_ioi", "gate_bypass": True}

    else:
        result = {"action": "unknown_always_id", "gate_bypass": False}

    # Log the pre-auth bypass decision (fires only in apply_always, never in check/is_preauthorized)
    log_event(
        "DECISION",
        f"Pre-auth bypass: {always_name}",
        detail=f"always_id={always_id} | context={context[:200] if context else ''}",
        source="hale_five_always",
    )

    result["always_id"] = always_id
    result["always_name"] = always_name
    return result


# ---------------------------------------------------------------------------
# Test block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 7 test cases: 5 matching (one per Always) + 2 non-matching

    TEST_CASES = [
        # (description, expect_match, expected_always_id_or_None)
        (
            "Send morning brief to johnloucks3",
            True,
            1,
        ),
        (
            "MCP failed — pivot to Python fallback",
            True,
            2,
        ),
        (
            "There is a blocker on the redis connector task",
            True,
            3,
        ),
        (
            "Identify the root cause of the token expiry issue and fix the source",
            True,
            4,
        ),
        (
            "Write an IOI for the headless Claude spawn procedure",
            True,
            5,
        ),
        (
            "Generate cruise pricing comparison for McLeod",
            False,
            None,
        ),
        (
            "Update the dossier for Furlow booking",
            False,
            None,
        ),
    ]

    print("=" * 60)
    print("FIVE ALWAYS PRE-AUTH — Test Suite")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, (desc, expect_match, expect_id) in enumerate(TEST_CASES, 1):
        authorized, name = is_preauthorized(desc)
        match_obj = check_always_applies(desc)
        actual_id = match_obj["id"] if match_obj else None

        ok = (authorized == expect_match) and (actual_id == expect_id)

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        print(f"\n[{status}] Test {i}: {desc!r}")
        print(f"       Expected: match={expect_match}, id={expect_id}")
        print(f"       Got:      match={authorized}, id={actual_id}, name={name!r}")

        # For matching cases, also show the apply_always result (without noisy log output)
        if authorized and match_obj:
            result = apply_always(match_obj["id"], context=desc)
            print(f"       apply_always → action={result['action']!r}, gate_bypass={result['gate_bypass']}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} PASS / {failed} FAIL / {len(TEST_CASES)} total")
    if failed == 0:
        print("ALL TESTS PASSED — Five Always pre-auth wiring is live.")
    else:
        print(f"WARNING: {failed} test(s) failed. Review patterns above.")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
