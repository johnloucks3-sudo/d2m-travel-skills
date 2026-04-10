#!/usr/bin/env python3
"""
KEYWORD ROUTER — 22-Test Validation Suite
Updated 2026-04-06: OpenCode/DeepSeek-first routing (Claude reserved for high-value only)
"""
import sys
sys.path.insert(0, '/home/john/Thunderbird/OpsCenter')
from keyword_router import classify_task

tests = [
  # (task_text, expected_engine, description)
  # --- Claude keyword matches (reserved high-value) ---
  ("architect the new pipeline", "claude", "architect keyword"),
  ("define the deployment strategy", "claude", "strategy keyword"),
  ("design the UI layout", "goose", "design keyword → Goose (generic)"),
  ("resolve the merge conflict", "claude", "resolve + conflict"),
  ("judge this proposal fairly", "claude", "judge keyword"),
  ("evaluate security posture", "goose", "evaluate → Goose (generic scan)"),
  ("write the deployment script", "claude", "write keyword"),
  ("compose email to stakeholders", "claude", "compose keyword"),
  ("this is a complex issue", "goose", "complex → Goose (too broad for Claude)"),
  ("analyze deeply the log output", "claude", "analyze deeply"),
  ("draft the incident report", "claude", "draft keyword"),
  ("assess the damage", "goose", "assess → Goose (generic)"),
  ("why did the service crash", "goose", "why → Goose (research/scan)"),

  # --- Claude precedence matches ---
  ("claude already reviewed this", "claude", "Claude precedence"),
  ("previous claude session flagged", "claude", "Previous Claude"),

  # --- Empty / unknown defaults → Goose ---
  ("", "goose", "Empty task → Goose default"),
  ("check server status", "goose", "Unknown → Goose default"),
  ("the thing broke again", "goose", "Vague → Goose default"),

  # --- Edge cases (Claude reserved) ---
  ("propose a fix for the bug", "claude", "propose keyword"),
  ("diplomatic response needed", "claude", "diplomatic keyword"),
  ("escalate to management", "claude", "escalate keyword"),
  ("negotiate the terms", "claude", "negotiate keyword"),
]

passed = 0
failed = 0

for task_text, expected_engine, desc in tests:
    result = classify_task(task_text)
    engine = result["engine"]
    status = "✅" if engine == expected_engine else "❌"
    if engine == expected_engine:
        passed += 1
    else:
        failed += 1
    print(f"{status} {desc:45s} → {engine.upper():6s} (conf: {result['confidence']:.0%})")

print(f"\n{'='*60}")
print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED — OpenCode/DeepSeek-first routing ACTIVE")
else:
    print("⚠️  FAILURES DETECTED — Review needed")
