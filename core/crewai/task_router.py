"""
CrewAI Task Router — decomposes a task string into subtasks,
assigns each to the right agent from agent_loader.
"""
from typing import List, Tuple, Dict
from crewai import Task

# Keyword → agent-name routing table
_ROUTING_KEYWORDS = {
    "research": ["a2-dembe"],
    "cruise": ["a2-dembe", "a10-ikeda"],
    "intel": ["a2-dembe"],
    "competitor": ["a2-dembe"],
    "competit": ["a5-castillo"],
    "crisis": ["a10-ikeda"],
    "logistic": ["a10-ikeda"],
    "connection time": ["a10-ikeda"],
    "troubleshoot": ["a10-ikeda"],
    "break": ["a10-ikeda"],
    "strategy": ["a5-castillo"],
    "pricing": ["a5-castillo", "a9-harlan"],
    "budget": ["a9-harlan"],
    "cost": ["a9-harlan"],
    "commission": ["a9-harlan"],
    "roi": ["a9-harlan"],
    "audit": ["a9-harlan"],
    "brand": ["exec-solberg-vega", "a6-voss"],
    "copy": ["a6-voss"],
    "proposal": ["exec-solberg-vega"],
    "narrative": ["a6-voss"],
    "client comm": ["a3-moreau"],
    "booking": ["a3-moreau"],
    "payment": ["a3-moreau"],
    "deadlin": ["a3-moreau"],
    "ethic": ["ch-washington"],
    "morale": ["ch-washington"],
    "right thing": ["ch-washington"],
    "automation": ["a12-elon"],
    "first-principle": ["a12-elon"],
    "manual": ["a12-elon"],
    "coordination": ["wing-coordinator"],
    "route": ["wing-coordinator"],
    "staff meeting": ["wing-coordinator"],
    "validate": ["a10-ikeda", "a2-dembe", "a9-harlan", "a3-moreau"],
    "itinerary": ["a10-ikeda", "a2-dembe"],
    "trip": ["a10-ikeda", "a3-moreau"],
    "plan": ["a10-ikeda", "a5-castillo"],
    "decision": ["a5-castillo"],
}


def _match_agents(task_str: str) -> List[str]:
    """Return deduplicated list of agent names relevant to the task."""
    lower = task_str.lower()
    agents: List[str] = []
    for keyword, agent_names in _ROUTING_KEYWORDS.items():
        if keyword in lower:
            for a in agent_names:
                if a not in agents:
                    agents.append(a)
    return agents


def route_task(task_str: str, agents: Dict) -> List[Task]:
    """
    Create CrewAI Task objects from *task_str*, each assigned to the
    most relevant agent found in *agents*.
    """
    matched = _match_agents(task_str)
    if not matched:
        # Fallback: assign to wing-coordinator or first available
        fallback = "wing-coordinator" if "wing-coordinator" in agents else list(agents.keys())[0]
        matched = [fallback]

    tasks: List[Task] = []

    # Main task
    main_agents = [agents[n] for n in matched if n in agents]
    if main_agents:
        tasks.append(
            Task(
                description=task_str,
                expected_output="A comprehensive analysis and response covering all aspects of the task.",
                agent=main_agents[0],
                context=[],
            )
        )

    # If multiple agents matched, add parallel subtasks
    for agent_name in matched[1:]:
        if agent_name in agents:
            subtask = Task(
                description=f"As {agent_name}, provide your domain-specific assessment for: {task_str}",
                expected_output=f"Expert analysis from {agent_name} perspective.",
                agent=agents[agent_name],
                context=[],
            )
            tasks.append(subtask)
            # Wire into main task context
            tasks[0].context.append(subtask)

    return tasks
