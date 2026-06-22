#!/usr/bin/env python3
"""
thunderbird_agno.py — Agno multi-agent framework adapter (formerly PhiData).
High-performance agent orchestration with built-in memory, tools, and storage.
Drop-in for standalone agent tasks where a full Wing exercise is overkill.

Usage:
    from core.ai_infra.thunderbird_agno import quick_agent, research_agent
    result = quick_agent("Summarize Viking Mars excursion options for Stockholm")
    result = research_agent("Compare Regent vs Silversea suite pricing for Dec 2026")
"""
from __future__ import annotations
import os
from pathlib import Path

_ENV = Path(__file__).parent.parent.parent / ".env"


def _get_key(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        for line in _ENV.read_text().splitlines():
            if line.startswith(f"{name}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def quick_agent(task: str, model_id: str = "claude-haiku-4-5-20251001") -> str:
    """Run a quick single-agent task via Agno with Claude as backend."""
    from agno.agent import Agent
    from agno.models.anthropic import Claude
    agent = Agent(
        model=Claude(id=model_id, api_key=_get_key("ANTHROPIC_API_KEY") or None),
        markdown=True,
    )
    response = agent.run(task)
    return response.content if hasattr(response, "content") else str(response)


def research_agent(task: str, tools: list = None) -> str:
    """Run a research agent with optional tools (list of agno Tool objects)."""
    from agno.agent import Agent
    from agno.models.anthropic import Claude
    kwargs = dict(
        model=Claude(id="claude-haiku-4-5-20251001"),
        markdown=True,
        show_tool_calls=False,
    )
    if tools:
        kwargs["tools"] = tools
    agent = Agent(**kwargs)
    response = agent.run(task)
    return response.content if hasattr(response, "content") else str(response)


if __name__ == "__main__":
    import sys
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Say hello from Agno/Thunderbird."
    print(quick_agent(task))
