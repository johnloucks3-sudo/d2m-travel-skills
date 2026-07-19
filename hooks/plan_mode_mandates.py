#!/usr/bin/env python3
"""PreToolUse hook on ExitPlanMode — surface the captured MUST-HAVES / MUST-DOS
(mandatory directives) before any plan is finalized or executed.

Root-cause guard (Commander directive 2026-07-18/19): a mandatory clue ("CROSS
HALE COORDINATION IS MANDATORY", message 4 of a multi-message discussion) was
missed because nothing forced the discussion's mandates into the plan. This hook
injects the current mandate briefing whenever a plan is presented, so the
Commander sees the must-haves/must-dos and the plan can be checked against them.
Driven by core/staffing/directive_ledger.py — captured, not remembered.
"""
import json
import sys

sys.path.insert(0, "/home/john/Thunderbird")

try:
    from core.staffing.directive_ledger import must_haves_must_dos
    summary = must_haves_must_dos()
except Exception as e:  # never block plan mode on a hook error
    summary = f"(directive ledger unavailable: {e})"

try:
    json.load(sys.stdin)  # consume hook input; content not needed
except Exception:
    pass

context = (
    "PLAN-MODE MANDATE CHECK — before presenting/executing this plan, confirm it "
    "satisfies EVERY captured mandatory directive below, and state in the plan how "
    "each is met:\n\n" + summary
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": context,
    },
    "systemMessage": "🔒 Plan-mode mandate check: surfaced captured MUST-HAVES / MUST-DOS.",
}))
