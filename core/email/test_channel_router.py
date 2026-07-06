#!/usr/bin/env python3
"""Test: channel_router.route_by_content_type against 10 messages (5 Telegram-
type, 5 AgentMail-type) + a silent-switch anomaly simulation.

Run: python3 core/email/test_channel_router.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

import core.email.channel_router as router
from core.email.channel_router import (
    TELEGRAM, AGENTMAIL, route_by_content_type, check_thread_handoff,
    SilentSwitchError, context_miss_rate,
)

# Point state files at scratch copies so this test never touches production logs.
_tmpdir = Path(tempfile.mkdtemp(prefix="channel_router_test_"))
router.CONTEXT_MISS_STATE = _tmpdir / "channel_context_miss.json"
router.DECISIONS_LOG = _tmpdir / "hale_decisions.md"
router.DECISIONS_LOG.write_text("")

TEST_MESSAGES = [
    # (label, message_type, has_substance, recipient_email, expected)
    ("notify-and-wait ping", "notify", False, None, TELEGRAM),
    ("ack a task", "notify", False, None, TELEGRAM),
    ("daily digest summary", "daily_digest", False, None, TELEGRAM),
    ("status nudge, no recipient", "notify", False, None, TELEGRAM),
    ("ad-hoc low-substance ping", "quick_ping", False, None, TELEGRAM),
    ("ELON proposal for Commander", "proposal", True, None, AGENTMAIL),
    ("Dembe research reply", "research_reply", True, None, AGENTMAIL),
    ("ad-hoc durable artifact", "custom_report", True, None, AGENTMAIL),
    ("named-waiver correspondence (Nancy Lyons)", "notify", False, "klyons3@bellsouth.net", AGENTMAIL),
    ("named-waiver correspondence (Susan Loucks)", "research_reply", True, "susanna.loucks@gmail.com", AGENTMAIL),
]

print("=== channel_router.route_by_content_type — 10 message test ===\n")
failures = []
for label, msg_type, has_substance, recipient, expected in TEST_MESSAGES:
    result = route_by_content_type(msg_type, has_substance=has_substance, recipient_email=recipient)
    ok = result == expected
    print(f"{'PASS' if ok else 'FAIL':4} | {label:45} -> {result!r} (expected {expected!r})")
    if not ok:
        failures.append(label)

# gate_veto special case — both channels monitored, not a single string.
gate_result = route_by_content_type("gate_veto")
gate_ok = gate_result == (TELEGRAM, AGENTMAIL)
print(f"{'PASS' if gate_ok else 'FAIL':4} | {'gate_veto (both monitored)':45} -> {gate_result!r}")
if not gate_ok:
    failures.append("gate_veto")

print("\n=== Silent-switch anomaly simulation (Rule 3) ===\n")
# Deliberate silent switch: no handoff announced -> must raise + log anomaly.
silent_switch_flagged = False
try:
    check_thread_handoff(prior_channel=AGENTMAIL, next_channel=TELEGRAM, handoff_announced=False)
except SilentSwitchError as e:
    silent_switch_flagged = True
    print(f"PASS | silent switch correctly raised SilentSwitchError: {e}")
if not silent_switch_flagged:
    failures.append("silent-switch-not-flagged")
    print("FAIL | silent switch was NOT flagged")

miss_state = json.loads(router.CONTEXT_MISS_STATE.read_text())
anomaly_logged = len(miss_state.get("miss_events", [])) == 1
print(f"{'PASS' if anomaly_logged else 'FAIL'} | anomaly recorded in context-miss state: {miss_state['miss_events']}")
if not anomaly_logged:
    failures.append("anomaly-not-logged")

# Explicit, announced handoff -> must NOT raise or log an anomaly.
try:
    check_thread_handoff(prior_channel=AGENTMAIL, next_channel=TELEGRAM, handoff_announced=True)
    print("PASS | announced handoff did not raise")
except SilentSwitchError:
    failures.append("announced-handoff-incorrectly-raised")
    print("FAIL | announced handoff incorrectly raised SilentSwitchError")

miss_state_after = json.loads(router.CONTEXT_MISS_STATE.read_text())
still_one = len(miss_state_after.get("miss_events", [])) == 1
print(f"{'PASS' if still_one else 'FAIL'} | announced handoff did not add a spurious anomaly")
if not still_one:
    failures.append("announced-handoff-logged-anomaly")

print(f"\ncontext_miss_rate() after simulation: {context_miss_rate():.2%} (denominator 0 messages recorded, expect 0.0 with no ZeroDivisionError)")

print("\n" + ("=" * 50))
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print(f"RESULT: ALL {len(TEST_MESSAGES) + 5} CHECKS PASSED")
