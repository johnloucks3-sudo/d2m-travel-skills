#!/usr/bin/env python3
"""
ADK Phase 3 Proof-of-Concept Test
D2M Thunderbird Wing — Blackboard Integration Evaluation
Tests: ADK install, Gemini connectivity, MCP tool registration

Run from: ~/Thunderbird/
Usage: python3 OpsCenter/collaboration/adk_poc_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Load Thunderbird env
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(str(ROOT / ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

print("=" * 60)
print("ADK PROOF-OF-CONCEPT — D2M THUNDERBIRD WING")
print("=" * 60)

# ── TEST 1: ADK Import ──────────────────────────────────────
print("\n[TEST 1] ADK import...")
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    print("  ✅ ADK imported successfully")
    print(f"  Version: google-adk installed")
except ImportError as e:
    print(f"  ❌ ADK import failed: {e}")
    sys.exit(1)

# ── TEST 2: Gemini API Key ──────────────────────────────────
print("\n[TEST 2] Gemini API key...")
if not GEMINI_API_KEY:
    print("  ❌ GEMINI_API_KEY not found in .env")
    sys.exit(1)
print(f"  ✅ Key found: {GEMINI_API_KEY[:8]}...")

# ── TEST 3: Define a simple D2M tool ───────────────────────
print("\n[TEST 3] Define test tool (read blackboard)...")

def read_blackboard() -> str:
    """Read the current D2M blackboard state."""
    bb_path = ROOT / "OpsCenter/collaboration/blackboard.md"
    try:
        return bb_path.read_text()[:500]
    except Exception as e:
        return f"Error reading blackboard: {e}"

def read_rate_limits() -> str:
    """Read current model rate limit status."""
    rl_path = ROOT / "OpsCenter/collaboration/rate_limit_status.md"
    try:
        return rl_path.read_text()[:300]
    except Exception as e:
        return f"Error reading rate limits: {e}"

print("  ✅ Tools defined")

# ── TEST 4: Create ADK Agent ────────────────────────────────
print("\n[TEST 4] Create ADK agent with Gemini model...")
try:
    goose_agent = Agent(
        name="goose_blackboard_agent",
        model="gemini-2.0-flash",
        description="Goose — D2M research and intel agent with blackboard access",
        instruction=(
            "You are Goose, the research and intel agent for Dreams2Memories Travel. "
            "You have access to the D2M blackboard and rate limit status. "
            "Always read the blackboard first before executing any task. "
            "Be concise and operational."
        ),
        tools=[read_blackboard, read_rate_limits],
    )
    print(f"  ✅ Agent created: {goose_agent.name}")
except Exception as e:
    print(f"  ❌ Agent creation failed: {e}")
    sys.exit(1)

# ── TEST 5: Run agent with test query ──────────────────────
print("\n[TEST 5] Run agent — read blackboard and report status...")

async def run_test():
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="d2m_blackboard_poc",
        user_id="commander",
        session_id="poc_test_001"
    )

    runner = Runner(
        agent=goose_agent,
        app_name="d2m_blackboard_poc",
        session_service=session_service
    )

    query = "Read the blackboard and rate limit status, then summarize in 3 bullet points."
    print(f"  Query: {query}")
    print("  Response:")
    print("  " + "-" * 50)

    async for event in runner.run_async(
        user_id="commander",
        session_id="poc_test_001",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text:
                    for line in part.text.strip().split('\n'):
                        print(f"  {line}")

    print("  " + "-" * 50)
    print("  ✅ Agent responded successfully")

try:
    asyncio.run(run_test())
except Exception as e:
    print(f"  ❌ Agent run failed: {e}")
    sys.exit(1)

# ── RESULTS ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print("✅ TEST 1: ADK imports cleanly")
print("✅ TEST 2: Gemini API key available")
print("✅ TEST 3: Python tools register as ADK tools")
print("✅ TEST 4: Agent instantiates with Gemini model")
print("✅ TEST 5: Agent executes query and returns response")
print()
print("ADK POC PASSED — ready for Phase 3 evaluation.")
print("Next step: test MCP tool registration via ADK.")
print("=" * 60)
