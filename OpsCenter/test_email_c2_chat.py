#!/usr/bin/env python3
"""
test_email_c2_chat.py — 3-iteration chat command integration test.

Tests email_c2 chat layer WITHOUT Gmail credentials.
Directly exercises: _is_wing_email, _clean_subject, detect_chat_command,
_chat_list, _chat_status, _chat_abort, _db_submit, _db_get, _db_update.

Iterations:
  1 — LIST:   seed DB with 3 tasks → run LIST → verify all appear
  2 — STATUS: pick seeded task → run STATUS <id> → verify fields
  3 — ABORT:  submit new task → run ABORT <id> → verify terminal state
"""

import sys, os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Patch gmail imports so email_c2 loads cleanly without credentials
import unittest.mock as mock

# email_c2 lazily imports Gmail only when _wing_service() is called — safe to import directly
import OpsCenter.email_c2 as c2

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    print(f"  {status}  {label}" + (f"  [{detail}]" if detail else ""))
    return condition


# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════")
print("  RELAY v2 — Email C2 Chat Test  (3 iterations)")
print("══════════════════════════════════════════════════════\n")

# ── Ensure DB is ready ────────────────────────────────────────────────────────
c2._db_init()

# ─────────────────────────────────────────────────────────────────────────────
print("── ITERATION 1 — LIST ───────────────────────────────")
# Seed 3 tasks
t1 = c2._db_submit("Check Westbrook fare watch status",        task_type="email_c2", source="test")
t2 = c2._db_submit("Pull morning brief and send to Commander", task_type="email_c2", source="test")
t3 = c2._db_submit("Run airline route sweep for June bookings", task_type="email_c2", source="test")
print(f"  Seeded: {t1}, {t2}, {t3}")

list_output = c2._chat_list("")
print(f"\n  LIST output:\n{list_output}\n")

check("LIST returns non-empty string",  bool(list_output.strip()))
check("LIST contains seeded task t1",   t1 in list_output, t1)
check("LIST contains seeded task t2",   t2 in list_output, t2)
check("LIST contains seeded task t3",   t3 in list_output, t3)
check("LIST shows status labels",       "[pending]" in list_output.lower() or "pending" in list_output.lower())

# ─────────────────────────────────────────────────────────────────────────────
print("\n── ITERATION 2 — STATUS ─────────────────────────────")
status_output = c2._chat_status(t2)
print(f"  STATUS {t2}:\n{status_output}\n")

check("STATUS returns non-empty",           bool(status_output.strip()))
check("STATUS contains task ID",            t2 in status_output)
check("STATUS contains 'pending' state",    "pending" in status_output.lower())
check("STATUS shows created_at",            "created" in status_output.lower())

# STATUS on unknown ID
bad_output = c2._chat_status("RELAY-DEADBEEF")
check("STATUS unknown ID returns error",    "No task found" in bad_output, bad_output[:60])

# Natural-form subject → detect_chat_command routes to STATUS
nat_subject = f"Hale, status {t2}"
cmd_result = c2.detect_chat_command(nat_subject)
check("detect_chat_command: natural STATUS fires", cmd_result is not None and cmd_result[0] == "STATUS",
      str(cmd_result))
check("detect_chat_command: args = task ID",       cmd_result and cmd_result[1].upper() == t2.upper(),
      str(cmd_result))

# ─────────────────────────────────────────────────────────────────────────────
print("\n── ITERATION 3 — ABORT ──────────────────────────────")
t4 = c2._db_submit("Draft Kuklinski voyage coming together email", task_type="email_c2", source="test")
print(f"  Submitted: {t4}")
c2._db_update(t4, "active")

# Confirm active before abort
row_before = c2._db_get(t4)
check("Task is active before abort",    row_before and row_before["status"] == "active",
      str(row_before.get("status") if row_before else "MISSING"))

abort_output = c2._chat_abort(t4)
print(f"  ABORT {t4}: {abort_output}")

check("ABORT returns success message",  "aborted" in abort_output.lower() or "✅" in abort_output)

row_after = c2._db_get(t4)
check("DB status = aborted after ABORT", row_after and row_after["status"] == "aborted",
      str(row_after.get("status") if row_after else "MISSING"))
check("DB result logged",               row_after and bool(row_after.get("result")))

# Abort idempotency — abort an already-aborted task
abort2 = c2._chat_abort(t4)
check("ABORT on aborted task: terminal-state guard fires", "terminal" in abort2.lower(), abort2[:60])

# Natural form: "COO, abort <id>"
nat_abort = f"COO, abort {t4}"
cmd2 = c2.detect_chat_command(nat_abort)
check("detect_chat_command: natural ABORT fires", cmd2 and cmd2[0] == "ABORT")

# ─────────────────────────────────────────────────────────────────────────────
print("\n── BONUS — is_wing_email + clean_subject ────────────")
cases = [
    ("[WING] run fare watch",          "",                   True),
    ("COS, pull blackboard",           "",                   True),
    ("HALE — brief me",                "",                   True),
    ("VIC: abort RELAY-ABC",           "",                   True),
    ("RE: [WING] run fare watch",      "",                   False),  # loop guard (Re:)
    ("Normal email subject",           "",                   False),
    ("Normal email",                   "Hey there, vic",     False),  # 'vic' mid-body = no
    ("Normal email",                   "Hale — do this now", True),   # body anchor
]
for subj, body, expected in cases:
    result_val = c2._is_wing_email(subj, body)
    check(f"is_wing_email({subj[:30]!r}…)", result_val == expected,
          f"got {result_val}, want {expected}")

clean_cases = [
    ("[WING] run fare watch",     "run fare watch"),
    ("COS, pull blackboard",      "pull blackboard"),
    ("COO — pull dossier",        "pull dossier"),
    ("Hale: brief me",            "brief me"),
    ("VIC  status RELAY-123",     "status RELAY-123"),
]
for raw, expected_clean in clean_cases:
    got = c2._clean_subject(raw)
    check(f"_clean_subject({raw!r})", got == expected_clean, f"got {got!r}, want {expected_clean!r}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════")
passed  = sum(1 for s,_,_ in results if s == PASS)
failed  = sum(1 for s,_,_ in results if s == FAIL)
total   = len(results)
pct     = int(100 * passed / total) if total else 0
verdict = "✅ ALL PASS" if failed == 0 else f"❌ {failed} FAILURE(S)"
print(f"  {verdict}  —  {passed}/{total}  ({pct}%)")
print("══════════════════════════════════════════════════════\n")

if failed:
    print("FAILURES:")
    for s, label, detail in results:
        if s == FAIL:
            print(f"  {label}  {detail}")
    sys.exit(1)
