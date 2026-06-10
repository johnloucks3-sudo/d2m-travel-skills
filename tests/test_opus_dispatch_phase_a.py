#!/usr/bin/env python3
"""
PHASE A TEST — Verify Opus dispatch is live on D2MC2C bot

Tests:
  1. Import poe_config, verify TASK_MODEL_MAP uses Opus for "default"
  2. Verify thunderbird_telegram_tools_sdk uses Opus for persona dispatch
  3. Call call_cos_via_sdk() directly with "test" message
  4. Verify response comes from Opus (quality indicator)

Run:
  cd ~/Thunderbird && python tests/test_opus_dispatch_phase_a.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.thunderbird_poe_config import TASK_MODEL_MAP, route_model, poe_mode
from core.communication.thunderbird_telegram_tools_sdk import (
    call_cos_via_sdk,
    PERSONA_PROMPTS,
    DEFAULT_MODEL,
)

print("=" * 70)
print("PHASE A TEST — Opus Dispatch Verification")
print("=" * 70)

print("\n[TEST 1] Verify TASK_MODEL_MAP uses Opus")
print("-" * 70)
critical_tasks = [
    "default",
    "dani_response",
    "email_draft",
    "client_proposal",
    "research",
]
for task in critical_tasks:
    model = TASK_MODEL_MAP.get(task, "MISSING")
    is_opus = "opus" in model.lower()
    status = "✅ OPUS" if is_opus else f"❌ NOT OPUS: {model}"
    print(f"  {task:20} → {model:30} {status}")

print("\n[TEST 2] Verify route_model() returns Opus")
print("-" * 70)
test_models = route_model("default"), route_model("dani_response"), route_model("email_draft")
for m in test_models:
    is_opus = "opus" in m.lower()
    print(f"  route_model() → {m:30} {'✅' if is_opus else '❌'}")

print("\n[TEST 3] Verify DEFAULT_MODEL is Opus")
print("-" * 70)
is_default_opus = "opus" in DEFAULT_MODEL.lower()
print(f"  DEFAULT_MODEL = {DEFAULT_MODEL:30} {'✅ OPUS' if is_default_opus else '❌ NOT OPUS'}")

print("\n[TEST 4] Call COS via SDK with test message")
print("-" * 70)
print("  Dispatching test message to Opus (COS persona)...")
print("  (This will call Claude Opus 4.8 via Max plan, $0 cost)")

async def test_dispatch():
    result = await call_cos_via_sdk(
        message="PHASE A TEST: Respond with: model name, timestamp, and brief status check.",
        persona="COS",
        intent_type="TASK",
        conversation_history=None,
    )
    return result

try:
    result = asyncio.run(test_dispatch())
    response = result.get("response", "NO RESPONSE")
    model_used = result.get("model", "UNKNOWN")
    print(f"\n  ✅ Response received from {model_used}")
    print(f"\n  Response:\n")
    print(f"  {response[:500]}")
    if len(response) > 500:
        print(f"  ... [truncated, {len(response)} total chars]")

    # Check if response mentions Opus or Claude
    is_opus_response = "opus" in response.lower() or "4.8" in response.lower()
    print(f"\n  {'✅' if is_opus_response else '⚠️'} Response quality indicator: {model_used}")

except Exception as e:
    print(f"\n  ❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("PHASE A TESTS COMPLETE")
print("=" * 70)
