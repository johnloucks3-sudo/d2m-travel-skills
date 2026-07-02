#!/usr/bin/env python3
"""
thunderbird_omnigent.py — Omnigent meta-harness adapter for Thunderbird.
omnigent is an Apache-2.0 meta-harness (4k+ stars) that hot-swaps Claude,
Codex, OpenAI agents SDK executors without changing application code.

Key capability: run the same AgentDef against any executor (Claude, OpenAI,
Databricks, etc.) by swapping ClaudeSDKExecutor → CodexExecutor → etc.

Usage:
    from core.ai_infra.thunderbird_omnigent import run_claude_agent, make_agent

    result = run_claude_agent(
        task="Research Regent Grandeur excursion options for Scandinavia 2026",
        model="claude-haiku-4-5-20251001",
        tools=["mcp"],  # MCP tools via MCPTool
    )
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

_VENV_SITE = next(
    (str(p) for p in Path("/home/john/Thunderbird/.venv/lib").glob("python*/site-packages")),
    None,
)
if _VENV_SITE:
    import sys
    if _VENV_SITE not in sys.path:
        sys.path.insert(0, _VENV_SITE)


def _make_executor(model: str | None = None):
    from omnigent import ClaudeSDKExecutor
    return ClaudeSDKExecutor(
        model=model or "claude-haiku-4-5-20251001",
        permission_mode="bypassPermissions",
    )


def make_agent(
    name: str,
    instructions: str,
    model: str = "claude-haiku-4-5-20251001",
    tools: list[str] | None = None,
) -> Any:
    """Build an omnigent AgentDef backed by ClaudeSDKExecutor."""
    from omnigent import AgentDef, MCPTool

    tool_list = []
    if tools:
        for t in tools:
            if t == "mcp":
                tool_list.append(MCPTool(server="thunderbird"))

    return AgentDef(
        name=name,
        instructions=instructions,
        executor=_make_executor(model),
        tools=tool_list,
    )


async def _run_agent_async(agent_def: Any, task: str) -> str:
    from omnigent.runner import run_agent
    result = await run_agent(agent_def, task)
    return str(result)


def run_claude_agent(
    task: str,
    name: str = "thunderbird-worker",
    instructions: str = "You are a Thunderbird wing assistant. Complete the task precisely.",
    model: str = "claude-haiku-4-5-20251001",
    tools: list[str] | None = None,
) -> str:
    """Run a one-shot Claude agent via omnigent. Returns final output string."""
    agent = make_agent(name=name, instructions=instructions, model=model, tools=tools)
    return asyncio.run(_run_agent_async(agent, task))


def run_haiku_worker(task: str, instructions: str = "") -> str:
    """Lightweight Haiku worker for cheap one-shot tasks."""
    return run_claude_agent(
        task=task,
        name="haiku-worker",
        instructions=instructions or "Complete the task. Be concise.",
        model="claude-haiku-4-5-20251001",
    )


def run_sonnet_analyst(task: str, instructions: str = "") -> str:
    """Sonnet analyst for multi-source synthesis tasks."""
    return run_claude_agent(
        task=task,
        name="sonnet-analyst",
        instructions=instructions or "Analyze carefully. Provide structured output.",
        model="claude-sonnet-4-6",
    )


if __name__ == "__main__":
    # Smoke test: verify omnigent imports and ClaudeSDKExecutor instantiates
    try:
        import omnigent
        executor = _make_executor()
        print(f"omnigent v{getattr(omnigent, '__version__', '?')} loaded")
        print(f"ClaudeSDKExecutor: {type(executor).__name__}")
        print("Available executors: ClaudeSDKExecutor, CodexExecutor, OpenAIAgentsSDKExecutor, OpenResponsesExecutor, DatabricksExecutor")
        print("thunderbird_omnigent: READY")
    except Exception as e:
        print(f"omnigent load error: {e}")
