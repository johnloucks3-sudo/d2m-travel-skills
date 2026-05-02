#!/usr/bin/env python3
"""
Headless Claude MCP Tools — Example Usage

This script demonstrates how to use the two new MCP tools:
1. headless_claude_task — High-level task execution
2. headless_claude_spawn — Low-level spawn control

File path: /home/john/Thunderbird/examples/headless_claude_mcp_example.py

These examples assume the MCP tools are registered and callable via an MCP client.
In production, these would be called from:
- OpenCode agents
- Claude Code headless workflows
- Any Thunderbird system needing long-running Claude tasks
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any

# These would come from an MCP client in production
# For demonstration, we show the expected method signatures


class HeadlessClaudeMCPClient:
    """Mock MCP client for demonstration purposes"""

    async def call_headless_claude_task(
        self,
        task_description: str,
        output_path: str,
        task_name: str,
        model: str = "claude-opus-4-7",
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Call the headless_claude_task MCP tool

        This is a high-level interface that automatically builds a prompt
        from your task description and handles all the complexity of spawning.
        """
        # In production, this would call the real MCP tool
        # For now, we show what the response would look like
        return {
            "status": "SPAWNED",
            "pid": 12345,
            "output_file": output_path,
            "log_file": "/home/john/Thunderbird/logs/headless_market_analysis_20260426_143022.log",
            "task_name": task_name,
            "model": model,
            "timestamp": "2026-04-26T14:30:22.123456",
            "attempt": 1
        }

    async def call_headless_claude_spawn(
        self,
        prompt: str,
        output_file: str,
        model: str = "claude-opus-4-7",
        task_name: str = "headless_task",
        log_file: str = None
    ) -> Dict[str, Any]:
        """
        Call the headless_claude_spawn MCP tool

        This is a low-level interface for advanced use cases where you
        need full control over the prompt and parameters.
        """
        # In production, this would call the real MCP tool
        return {
            "status": "SPAWNED",
            "pid": 12346,
            "output_file": output_file,
            "log_file": log_file or "/home/john/Thunderbird/logs/headless_custom_task_20260426_143022.log",
            "task_name": task_name,
            "model": model,
            "timestamp": "2026-04-26T14:30:22.654321"
        }


# ============================================================================
# EXAMPLE 1: Market Analysis Task (High-Level)
# ============================================================================

async def example_1_market_analysis():
    """
    Example 1: Execute a market analysis task using the high-level tool.

    This is the simplest approach — just describe what you want Claude to do,
    and the tool handles the rest: building the prompt, spawning the process,
    retrying on failure, etc.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Market Analysis (High-Level headless_claude_task)")
    print("=" * 70)

    client = HeadlessClaudeMCPClient()

    # Define the task
    task_description = """
    Analyze the luxury cruise market trends for Q2 2026.

    Focus on:
    1. Top cruise lines by revenue and passenger count
    2. Most popular destinations (Caribbean, Mediterranean, Alaska)
    3. Pricing trends for 7-day cruises
    4. Emerging markets (Asian cruises, river cruises)
    5. Impact of economic factors on booking patterns

    Provide data-driven insights suitable for a luxury travel company.
    Include citations for all sources.
    """

    output_path = "/home/john/Thunderbird/output/market_analysis_q2_2026.txt"

    # Execute the task
    print(f"\nSpawning task: market_analysis_q2...")
    print(f"Output will be written to: {output_path}")

    try:
        result = await client.call_headless_claude_task(
            task_description=task_description,
            output_path=output_path,
            task_name="market_analysis_q2",
            model="claude-opus-4-7",
            max_retries=1
        )

        # Parse and display result
        if result.get("status") == "SPAWNED":
            print(f"\n✅ SUCCESS!")
            print(f"   Task spawned with PID: {result['pid']}")
            print(f"   Output file: {result['output_file']}")
            print(f"   Log file: {result['log_file']}")
            print(f"   Model: {result['model']}")
            print(f"   Timestamp: {result['timestamp']}")

            # In production, you'd monitor the output file:
            # while not Path(output_path).exists():
            #     await asyncio.sleep(5)
            # with open(output_path) as f:
            #     print(f.read())
        else:
            print(f"\n❌ FAILED: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")


# ============================================================================
# EXAMPLE 2: Competitor Research Task (High-Level)
# ============================================================================

async def example_2_competitor_research():
    """
    Example 2: Execute a competitor research task.

    Similar to Example 1 but focused on competitive intelligence.
    Still using the high-level headless_claude_task tool.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Competitor Research (High-Level headless_claude_task)")
    print("=" * 70)

    client = HeadlessClaudeMCPClient()

    task_description = """
    Research the top 5 luxury cruise operators and their competitive positioning.

    For each operator, provide:
    1. Fleet size, age, and average capacity
    2. Price positioning (budget/mid/luxury/ultra-luxury)
    3. Key destinations and voyage lengths
    4. Unique selling propositions (enrichment, dining, services)
    5. Recent innovations (technology, sustainability, pricing models)
    6. Market share estimates
    7. Target demographics (age, income, interests)

    Compare D2M's positioning against these competitors.
    Identify gaps and opportunities.
    """

    output_path = "/home/john/Thunderbird/output/competitor_analysis_2026.txt"

    print(f"\nSpawning task: competitor_research...")

    try:
        result = await client.call_headless_claude_task(
            task_description=task_description,
            output_path=output_path,
            task_name="competitor_research",
            model="claude-sonnet-4-6",  # Sonnet for detailed analysis
            max_retries=2  # More retries for longer task
        )

        if result.get("status") == "SPAWNED":
            print(f"\n✅ SUCCESS! (Attempt {result.get('attempt', 1)})")
            print(f"   PID: {result['pid']}")
            print(f"   Output: {result['output_file']}")
        else:
            print(f"\n❌ FAILED: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")


# ============================================================================
# EXAMPLE 3: Custom Prompt with Low-Level Spawn
# ============================================================================

async def example_3_custom_prompt():
    """
    Example 3: Use low-level headless_claude_spawn with a custom prompt.

    This gives you full control over the prompt and parameters.
    Use when you need something more specific than the high-level tool provides.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Custom Prompt (Low-Level headless_claude_spawn)")
    print("=" * 70)

    client = HeadlessClaudeMCPClient()

    # Craft a custom prompt with specific formatting
    output_file = "/home/john/Thunderbird/output/pricing_analysis_custom.json"

    custom_prompt = f"""
You are a luxury travel pricing analyst for Dreams2Memories Travel, LLC.

TASK: Analyze Q2 2026 pricing for 7-day Mediterranean cruises on Silversea ships.

REQUIREMENTS:
1. Research published prices from Silversea's website for June-August 2026 voyages
2. Extract cabin category pricing (inside, ocean view, veranda, suite)
3. Identify any promotional discounts or early-bird offers
4. Compare to Q2 2025 pricing year-over-year
5. Segment pricing by voyage theme (cultural, gastronomic, wellness)

OUTPUT FORMAT:
Provide output as valid JSON with this structure:
{
  "report_date": "ISO_DATE",
  "cruise_line": "Silversea",
  "season": "Q2 2026",
  "voyages": [
    {
      "voyage_name": "string",
      "departure_date": "YYYY-MM-DD",
      "duration_nights": 7,
      "pricing_by_cabin": {
        "inside": number,
        "ocean_view": number,
        "veranda": number,
        "suite": number
      },
      "promotion": "string or null",
      "discount_percent": number
    }
  ],
  "trends": ["insight1", "insight2", "insight3"],
  "sources": ["URL1", "URL2", "URL3"]
}

CRITICAL INSTRUCTION:
WRITE your complete JSON output to {output_file}
Do NOT output to stdout. All output goes to {output_file}.
"""

    print(f"\nSpawning custom analysis task...")

    try:
        result = await client.call_headless_claude_spawn(
            prompt=custom_prompt,
            output_file=output_file,
            model="claude-opus-4-7",
            task_name="pricing_analysis_silversea",
            log_file="/home/john/Thunderbird/logs/custom_pricing_20260426.log"
        )

        if result.get("status") == "SPAWNED":
            print(f"\n✅ SUCCESS!")
            print(f"   Output will be JSON at: {result['output_file']}")
            print(f"   Process PID: {result['pid']}")

            # In production, poll the file:
            # output_path = Path(output_file)
            # while not output_path.exists():
            #     await asyncio.sleep(2)
            # with open(output_path) as f:
            #     pricing_data = json.load(f)
            #     print(f"Pricing data loaded: {len(pricing_data['voyages'])} voyages")
        else:
            print(f"\n❌ FAILED: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")


# ============================================================================
# EXAMPLE 4: Error Handling and Retry Logic
# ============================================================================

async def example_4_error_handling():
    """
    Example 4: Demonstrate error handling and retry logic.

    Shows how to handle failures and read the output file when complete.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Error Handling and Monitoring")
    print("=" * 70)

    client = HeadlessClaudeMCPClient()

    output_path = "/home/john/Thunderbird/output/test_output.txt"

    print(f"\nSpawning task with error handling...")

    try:
        result = await client.call_headless_claude_task(
            task_description="Generate a list of luxury hotels in Rome, Italy with ratings and price per night.",
            output_path=output_path,
            task_name="rome_hotels",
            model="claude-haiku-4-5-20251001",
            max_retries=2
        )

        # Handle different response statuses
        status = result.get("status")

        if status == "SPAWNED":
            print(f"✅ Task spawned successfully")
            print(f"   Monitor progress: tail -f {result['log_file']}")
            print(f"   Check output: cat {result['output_file']}")

            # In production, you'd poll the output file
            output_file_path = Path(output_path)
            max_wait = 300  # seconds
            elapsed = 0
            poll_interval = 5

            # print(f"\n   Waiting for output (max {max_wait}s)...")
            # while not output_file_path.exists() and elapsed < max_wait:
            #     await asyncio.sleep(poll_interval)
            #     elapsed += poll_interval
            #     print(f"   ... {elapsed}s elapsed")

            # if output_file_path.exists():
            #     with open(output_file_path) as f:
            #         output = f.read()
            #     print(f"\n✅ Output ready ({len(output)} bytes):")
            #     print(output[:500] + "..." if len(output) > 500 else output)
            # else:
            #     print(f"\n⚠️  Timeout waiting for output after {max_wait}s")

        elif status == "FAILED":
            print(f"❌ Task failed: {result.get('error')}")
            print(f"   Check logs at: {result.get('log_file')}")

        else:
            print(f"⚠️  Unknown status: {status}")
            print(f"   Full result: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"❌ Exception during task: {str(e)}")
        import traceback
        traceback.print_exc()


# ============================================================================
# EXAMPLE 5: Integration with OpenCode Agent
# ============================================================================

async def example_5_opencode_integration():
    """
    Example 5: Show how OpenCode agents would use these tools.

    This example shows the pattern for OpenCode integration.
    In production, OpenCode would call these MCP tools via the MCP client.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: OpenCode Agent Integration Pattern")
    print("=" * 70)

    print("""
In OpenCode, you would use these MCP tools like this:

```python
# Inside an OpenCode agent task
from mcp_client import MCPClient

async def run_market_research_background():
    '''Execute market research in background via headless Claude'''

    mcp = MCPClient("mcp.d2mluxury.quest:8765")

    # Call the high-level MCP tool
    result = await mcp.call_tool(
        "headless_claude_task",
        {
            "task_description": "Research Q2 cruise pricing trends...",
            "output_path": "/home/john/Thunderbird/output/q2_prices.txt",
            "task_name": "q2_pricing_research",
            "model": "claude-opus-4-7",
            "max_retries": 1
        }
    )

    if result["status"] == "SPAWNED":
        # Task is running in background
        # Log PID and output path for monitoring
        logging.info(f"Research task spawned: PID {result['pid']}")

        # In a monitoring loop, you can check the output file:
        while not Path(result["output_file"]).exists():
            await asyncio.sleep(10)

        # Read and process results
        with open(result["output_file"]) as f:
            analysis = f.read()

        # Do something with the results
        return analysis
    else:
        # Handle failure
        logging.error(f"Spawn failed: {result['error']}")
        raise Exception(f"Background task failed: {result['error']}")
```

WORKFLOW:
1. OpenCode agent needs long-running Claude task
2. Calls headless_claude_task MCP tool
3. Tool spawns detached Claude process
4. Returns PID and output file path
5. Agent can continue or monitor output file
6. Results are available in output file when complete

ADVANTAGES:
- Non-blocking: Agent doesn't wait for Claude to finish
- Fault-tolerant: Process continues even if agent crashes
- Monitorable: Logs and output file available for inspection
- Retryable: Built-in retry logic on spawn failure
""")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""

    print("\n" + "=" * 70)
    print("THUNDERBIRD HEADLESS CLAUDE MCP TOOLS — EXAMPLES")
    print("=" * 70)
    print("\nFile: /home/john/Thunderbird/examples/headless_claude_mcp_example.py")
    print("\nThese examples demonstrate how to use the two new MCP tools:")
    print("  1. headless_claude_task — High-level task execution")
    print("  2. headless_claude_spawn — Low-level spawn control")

    # Run examples
    await example_1_market_analysis()
    await example_2_competitor_research()
    await example_3_custom_prompt()
    await example_4_error_handling()
    await example_5_opencode_integration()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - Module: /home/john/Thunderbird/core/mcp/thunderbird_headless_claude.py")
    print("  - Docs: /home/john/Thunderbird/docs/MCP_HEADLESS_CLAUDE_INTEGRATION.md")
    print("  - Spawn guide: /home/john/Thunderbird/docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(main())
