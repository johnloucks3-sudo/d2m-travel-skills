#!/usr/bin/env python3
"""Test Managed Agents integration — run after adding API credits.

Usage: python3 scripts/test_managed_agents.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_infra.managed_agent_client import WingAgentClient

def main():
    print("Testing Anthropic Managed Agents API...")
    client = WingAgentClient()

    print("Step 1: Creating cloud environment...")
    env_id = client._get_or_create_environment()
    print(f"  ✅ env_id: {env_id}")

    print("Step 2: Creating Haiku agent...")
    agent_id = client._get_or_create_agent("haiku")
    print(f"  ✅ agent_id: {agent_id}")

    print("Step 3: Running a test task...")
    result = client.run_task(
        prompt="List 3 major cruise lines that operate in the Caribbean. One line each.",
        tier="haiku",
        label="test-task",
    )
    print(f"  ✅ Output:\n{result['output']}")
    print(f"  Tokens: {result['input_tokens']} in / {result['output_tokens']} out")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Session: {result['session_id']}")
    print()
    print("✅ Managed Agents integration LIVE. Wing is ready to route automations.")

if __name__ == "__main__":
    main()
