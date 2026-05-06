"""
Thunderbird Multi-Agent Orchestrator — OpenClaw P4 Pattern
Spawn N agents, each with task variation, aggregate results.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_ROOT = Path.home() / "Thunderbird"
AGENT_LOG_DIR = THUNDERBIRD_ROOT / "logs" / "agents"
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)


class MultiAgentSwarm:
    """Legacy class for compatibility."""
    def spawn(self, agent_name: str, task: str):
        # Spawns a dedicated Thunderbird agent instance
        proc = subprocess.Popen(
            ["/home/john/Thunderbird/.venv/bin/python", "/home/john/Thunderbird/core/ai_infra/agent_wrapper.py", agent_name, task],
            start_new_session=True
        )
        return proc.pid


class MultiAgentOrchestrator:
    """Orchestrate N parallel Claude agents with aggregated results. (OpenClaw P4)"""

    def __init__(self, model: str = "claude-sonnet-4-6", timeout_seconds: int = 600):
        self.model = model
        self.timeout = timeout_seconds
        self.results: List[Dict[str, Any]] = []

    def _generate_variation(self, task: str, index: int) -> str:
        """Create task variation for agent N."""
        variations = [
            f"Focus on high-level strategic implications",
            f"Focus on tactical execution details and timeline",
            f"Focus on risk analysis and mitigation",
            f"Focus on competitive positioning",
            f"Focus on financial impact and ROI",
        ]

        variation = variations[index % len(variations)]
        return f"{task}\n\n[AGENT {index+1} VARIATION: {variation}]"

    async def spawn_agents(self, n: int, task: str, variations: List[str] = None) -> List[Dict[str, Any]]:
        """
        Spawn N Claude agents with task variations.

        Args:
            n: Number of agents to spawn (1-5)
            task: Base task description
            variations: Optional list of variations (generated if not provided)

        Returns:
            List of agent result dicts with status, output, log_file
        """
        if n < 1 or n > 5:
            raise ValueError("Agent count must be between 1 and 5")

        # Generate variations if not provided
        if not variations:
            variations = [self._generate_variation(task, i) for i in range(n)]

        tasks = []
        for i in range(n):
            task_variation = variations[i] if i < len(variations) else self._generate_variation(task, i)
            task_coro = self._spawn_single_agent(i, task_variation)
            tasks.append(task_coro)

        # Run all agents concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout
            )
            return results
        except asyncio.TimeoutError:
            logger.warning(f"Agent spawn timeout after {self.timeout}s")
            return [{"agent": i, "status": "timeout", "output": ""} for i in range(n)]

    async def _spawn_single_agent(self, agent_id: int, task: str) -> Dict[str, Any]:
        """Spawn a single agent and capture its output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = AGENT_LOG_DIR / f"agent_{agent_id}_{timestamp}.log"
        output_file = AGENT_LOG_DIR / f"agent_{agent_id}_{timestamp}_output.txt"

        prompt = f"""You are Agent {agent_id+1} in a multi-agent analysis team.

TASK:
{task}

INSTRUCTIONS:
1. Complete the task thoroughly
2. WRITE your complete output to {output_file}
3. Be concise but comprehensive
4. Format output as structured analysis with sections

Do NOT output to stdout. Write to {output_file}.
"""

        try:
            proc = subprocess.Popen(
                [
                    "/home/john/.local/bin/claude",
                    "-p", prompt,
                    "--model", self.model,
                ],
                stdout=open(log_file, "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )

            # Wait for completion with timeout
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, proc.wait),
                timeout=self.timeout
            )

            # Read output if available
            output = ""
            if output_file.exists():
                output = output_file.read_text()
                output_file.unlink()

            return {
                "agent": agent_id,
                "status": "complete",
                "output": output,
                "log_file": str(log_file),
                "pid": proc.pid
            }
        except asyncio.TimeoutError:
            return {
                "agent": agent_id,
                "status": "timeout",
                "output": "",
                "log_file": str(log_file)
            }
        except Exception as e:
            logger.error(f"Agent {agent_id} spawn failed: {e}")
            return {
                "agent": agent_id,
                "status": "error",
                "output": str(e),
                "log_file": str(log_file)
            }

    async def aggregate_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Consolidate N agent outputs into one report.

        Args:
            results: List of agent result dicts

        Returns:
            Aggregated report as string
        """
        report_lines = ["# Multi-Agent Analysis Report\n"]

        # Summary section
        complete = sum(1 for r in results if r.get("status") == "complete")
        report_lines.append(f"**Completion:** {complete}/{len(results)} agents successful\n")

        # Individual findings
        report_lines.append("## Agent Findings\n")
        for result in results:
            agent_id = result.get("agent", "?")
            status = result.get("status", "unknown")
            output = result.get("output", "")

            report_lines.append(f"### Agent {agent_id+1} ({status.upper()})\n")
            if output:
                # Extract key points (first 500 chars)
                summary = output[:500]
                if len(output) > 500:
                    summary += "\n_[truncated]_"
                report_lines.append(summary)
            report_lines.append("")

        # Consolidation section
        report_lines.append("## Key Themes Across Agents\n")

        # Simple deduplication: collect unique lines
        all_lines = set()
        for result in results:
            output = result.get("output", "")
            for line in output.split("\n"):
                line = line.strip()
                if len(line) > 20 and line not in all_lines:
                    all_lines.add(line)

        report_lines.append("**Common findings:**\n")
        for line in sorted(all_lines)[:5]:
            report_lines.append(f"- {line}")

        return "\n".join(report_lines)


# Legacy compatibility
swarm = MultiAgentSwarm()
if __name__ == "__main__":
    swarm.spawn("MemoryIndexer", "P1_Memory_Indexing")
    swarm.spawn("HeartbeatAuditor", "P2_Heartbeat_Audit")
    swarm.spawn("ConfigWatcher", "P3_HotReload_Config")
