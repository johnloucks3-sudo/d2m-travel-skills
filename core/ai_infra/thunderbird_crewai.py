"""
Thunderbird CrewAI — Wing Orchestration Engine
================================================
Maps D2M's 8-persona Wing to CrewAI agents with COS (Hale) as
the manager/orchestrator. Enables true multi-agent collaboration
where personas delegate, share context, and build on each other's work.

Architecture:
  - Each Wing persona → CrewAI Agent (with matching backstory + role)
  - COS → Manager agent (hierarchical process)
  - Tasks defined per-mission, not per-persona
  - Uses Claude Opus via Max plan ($0, no OpenAI dependency)

Usage:
  from thunderbird_crewai import run_wing_crew, run_research_crew

  # Full staff meeting — COS orchestrates all personas
  result = run_wing_crew("Analyze Mediterranean cruise options for the Kuklinski group")

  # Targeted crew — specific personas for a focused task
  result = run_research_crew("Best Alaska inside passage cruises for seniors, July 2026")
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger("thunderbird_crewai")

# ============================================================================
# LLM CONFIGURATION — Claude Opus via Max plan ($0)
# FIXED 2026-03-16: Gemini was primary, burning $10/mo GCP budget
# ============================================================================

# CrewAI uses LiteLLM format for model strings
# Claude Opus via Max plan ($0)
CREWAI_LLM = "anthropic/claude-sonnet-4-6"

# ============================================================================
# PERSONA → AGENT MAPPING
# ============================================================================

AGENT_DEFS = {
    "COS": {
        "role": "Chief of Staff — Orchestration & Synthesis",
        "goal": "Coordinate the Wing staff to deliver actionable intelligence and recommendations to the Commander. Synthesize multi-domain inputs into clear, prioritized briefs.",
        "backstory": (
            "Ms. Victoria 'Victory' Hale, SES-6. VCSAF-equivalent civilian senior executive. "
            "32-year career across RAND, OSD-P, J5, ONA, HAF/A5, PACAF. "
            "Georgetown SFS, SAIS, King's College PhD. Zero patience for wasted motion. "
            "The staff exists to make the Commander's decisions easier, not harder."
        ),
    },
    "EXEC": {
        "role": "Executive Communications & Brand Voice",
        "goal": "Transform raw intelligence and recommendations into polished, client-ready communications that embody the D2M luxury brand.",
        "backstory": (
            "Naia Solberg-Vega. Daughter of a Norwegian diplomat and Puerto Rican muralist. "
            "Columbia (comp lit) + Parsons (visual comms). Six years at a Relais & Chateaux property group. "
            "She writes the way the Commander talks. If it sounds like a form letter, it belongs in the trash."
        ),
    },
    "A2": {
        "role": "Research & Market Intelligence Analyst",
        "goal": "Provide evidence-based destination research, supplier pricing intelligence, competitor analysis, and travel advisories with confidence levels.",
        "backstory": (
            "Lt Col Marcus 'Wraith' Dembe. Intelligence officer, three tours at DIA, two at NSA. "
            "TS/SCI since age 22. Reads five languages. Treats every research question like a "
            "collection requirement — sources, confidence levels, gaps identified."
        ),
    },
    "A3": {
        "role": "D2M Luxury Travel Concierge",
        "goal": "Handle client interactions with warmth and operational precision. Coordinate bookings, manage trip logistics, and ensure every client touchpoint reflects D2M excellence.",
        "backstory": (
            "Danielle 'Dani' Moreau. 12 years at the Four Seasons Beverly Hills front desk, "
            "then concierge lead for a private travel club in Monaco. She remembers every client's "
            "name, preference, and anniversary date. Warm but operationally crisp."
        ),
    },
    "A5": {
        "role": "Strategy & Business Growth",
        "goal": "Analyze business opportunities, competitive positioning, and growth vectors. Provide strategic recommendations with clear ROI projections.",
        "backstory": (
            "Lt Col Ryan 'Viper' Castillo. USAF F-16 pilot turned strategist. MBA from Wharton. "
            "Thinks in OODA loops. Every problem is a targeting solution: observe, orient, decide, act."
        ),
    },
    "A9": {
        "role": "Finance & Process Improvement",
        "goal": "Audit commissions, analyze costs, calculate ROI, and eliminate waste. Every dollar has a job — find the dollars that don't.",
        "backstory": (
            "Victor 'Vic' Harlan. 30 years in defense contracting finance, retired GS-15. "
            "Calls waste 'theft' and underpricing 'charity.' Will find the money. "
            "Blunt, avuncular, numbers-first."
        ),
    },
    "CH": {
        "role": "Ethics, Wisdom & Morale",
        "goal": "Provide ethical grounding, perspective, and morale support. Ask the questions nobody else will ask. Protect the team's soul.",
        "backstory": (
            "Col James 'Padre' Washington. 28 years as USAF chaplain. Two combat deployments. "
            "Speaks sparingly but every word lands. Unhurried, warm, deeply grounded."
        ),
    },
    "A12": {
        "role": "Innovation & Disruption",
        "goal": "Challenge assumptions, propose automation, and redesign processes from first principles. 'Why are we doing this at all?'",
        "backstory": (
            "ELON. No rank, no history, no patience for 'we've always done it that way.' "
            "Direct, irreverent, first-principles. If a human is doing something a machine could do, "
            "that's a bug, not a feature."
        ),
    },
}


def _build_agents() -> Dict[str, Any]:
    """Build CrewAI Agent objects for each Wing persona."""
    from crewai import Agent, LLM

    # Strip ANTHROPIC_API_KEY so LiteLLM uses Max plan OAuth ($0)
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]

    llm = LLM(
        model=CREWAI_LLM,
        temperature=0.3,
    )

    agents = {}
    for pid, defn in AGENT_DEFS.items():
        agents[pid] = Agent(
            role=defn["role"],
            goal=defn["goal"],
            backstory=defn["backstory"],
            llm=llm,
            verbose=False,
            allow_delegation=(pid == "COS"),  # Only COS can delegate
            memory=True,
        )

    return agents


# ============================================================================
# CREW TEMPLATES — pre-built crew configurations
# ============================================================================

def run_wing_crew(mission: str, context: str = "") -> Dict[str, Any]:
    """Run a full Wing staff meeting via CrewAI with COS as manager.

    All 8 personas participate. COS orchestrates, delegates subtasks,
    and synthesizes the final brief.

    Args:
        mission: The question or task for the Wing
        context: Optional additional context

    Returns:
        Dict with crew output, token usage, and per-task results
    """
    from crewai import Crew, Task, Process

    agents = _build_agents()
    full_query = f"{mission}\n\nContext: {context}" if context else mission

    # Define tasks — COS assigns work, each persona contributes
    tasks = [
        Task(
            description=f"As A2 (Intelligence), research and analyze: {full_query}. Provide evidence-based findings with confidence levels.",
            expected_output="Research findings with sources and confidence assessments",
            agent=agents["A2"],
        ),
        Task(
            description=f"As A3 (Concierge), assess client impact and logistics: {full_query}. What does this mean for the client experience?",
            expected_output="Client experience assessment and logistics considerations",
            agent=agents["A3"],
        ),
        Task(
            description=f"As A5 (Strategy), evaluate strategic implications: {full_query}. What are the opportunities and risks?",
            expected_output="Strategic analysis with opportunities, risks, and recommendations",
            agent=agents["A5"],
        ),
        Task(
            description=f"As A9 (Finance), analyze the financial angle: {full_query}. What are the costs, commissions, and ROI?",
            expected_output="Financial analysis with cost breakdown and commission implications",
            agent=agents["A9"],
        ),
        Task(
            description=(
                f"As COS (Chief of Staff), synthesize all staff inputs into a unified brief for the Commander. "
                f"Mission: {full_query}\n\n"
                "Distill the key findings from A2 (intelligence), A3 (client impact), A5 (strategy), and A9 (finance) "
                "into a clear, prioritized recommendation with action items."
            ),
            expected_output="Synthesized brief with prioritized recommendations and action items for the Commander",
            agent=agents["COS"],
            context=[],  # Will be auto-populated by CrewAI's sequential process
        ),
    ]

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
        memory=True,
    )

    logger.info(f"Wing crew assembled — {len(agents)} agents, mission: {mission[:80]}")
    result = crew.kickoff()

    return {
        "mission": mission,
        "crew_type": "full_wing",
        "output": str(result),
        "token_usage": result.token_usage if hasattr(result, "token_usage") else {},
        "tasks_output": [
            {"agent": t.agent.role if t.agent else "unknown", "output": str(t.output)}
            for t in tasks if t.output
        ],
    }


def run_research_crew(query: str) -> Dict[str, Any]:
    """Run a targeted research crew: A2 (intel) + A9 (finance) + COS (synthesis).

    Lighter than a full staff meeting — focused on research + cost analysis.
    """
    from crewai import Crew, Task, Process

    agents = _build_agents()

    tasks = [
        Task(
            description=f"Research thoroughly: {query}. Provide detailed findings with sources and confidence levels.",
            expected_output="Detailed research findings",
            agent=agents["A2"],
        ),
        Task(
            description=f"Analyze the financial implications of: {query}. Costs, commissions, ROI, budget considerations.",
            expected_output="Financial analysis and cost assessment",
            agent=agents["A9"],
        ),
        Task(
            description=(
                f"Synthesize A2's research and A9's financial analysis into a recommendation brief. "
                f"Topic: {query}"
            ),
            expected_output="Synthesized recommendation brief",
            agent=agents["COS"],
        ),
    ]

    crew = Crew(
        agents=[agents["A2"], agents["A9"], agents["COS"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )

    logger.info(f"Research crew assembled — A2 + A9 + COS, query: {query[:80]}")
    result = crew.kickoff()

    return {
        "mission": query,
        "crew_type": "research",
        "output": str(result),
        "token_usage": result.token_usage if hasattr(result, "token_usage") else {},
    }


def run_client_crew(client_name: str, request: str) -> Dict[str, Any]:
    """Run a client-focused crew: A3 (concierge) + A2 (research) + EXEC (communications).

    For client requests that need research, then a polished response.
    """
    from crewai import Crew, Task, Process

    agents = _build_agents()

    tasks = [
        Task(
            description=f"Research what's needed to answer this client request from {client_name}: {request}",
            expected_output="Research findings relevant to the client request",
            agent=agents["A2"],
        ),
        Task(
            description=f"As Dani (concierge), draft a response to {client_name}'s request: {request}. Use A2's research.",
            expected_output="Draft client response with accurate information",
            agent=agents["A3"],
        ),
        Task(
            description=f"Polish Dani's draft response for {client_name} into D2M luxury brand voice. Warm, personal, never corporate.",
            expected_output="Polished, brand-aligned client communication",
            agent=agents["EXEC"],
        ),
    ]

    crew = Crew(
        agents=[agents["A2"], agents["A3"], agents["EXEC"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )

    logger.info(f"Client crew assembled — A2 + A3 + EXEC for {client_name}")
    result = crew.kickoff()

    return {
        "mission": f"Client request from {client_name}: {request}",
        "crew_type": "client",
        "output": str(result),
        "token_usage": result.token_usage if hasattr(result, "token_usage") else {},
    }


def run_innovation_crew(topic: str) -> Dict[str, Any]:
    """Run an innovation crew: A12 (ELON) + A5 (Strategy) + COS (synthesis).

    For 'why are we doing this?' and automation/improvement questions.
    """
    from crewai import Crew, Task, Process

    agents = _build_agents()

    tasks = [
        Task(
            description=f"Challenge from first principles: {topic}. Why are we doing this at all? What should be automated?",
            expected_output="First-principles analysis with automation recommendations",
            agent=agents["A12"],
        ),
        Task(
            description=f"Evaluate ELON's proposals strategically: {topic}. What's feasible? What's the competitive impact?",
            expected_output="Strategic feasibility assessment",
            agent=agents["A5"],
        ),
        Task(
            description=f"Synthesize ELON's innovation proposals and A5's strategic assessment into an implementation brief.",
            expected_output="Prioritized innovation brief with implementation steps",
            agent=agents["COS"],
        ),
    ]

    crew = Crew(
        agents=[agents["A12"], agents["A5"], agents["COS"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )

    logger.info(f"Innovation crew assembled — A12 + A5 + COS, topic: {topic[:80]}")
    result = crew.kickoff()

    return {
        "mission": topic,
        "crew_type": "innovation",
        "output": str(result),
        "token_usage": result.token_usage if hasattr(result, "token_usage") else {},
    }


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_crewai_tools(mcp):
    """Register CrewAI crew tools with the MCP server."""
    from pydantic import Field

    @mcp.tool(name="crew_staff_meeting",
              annotations={"title": "Run Wing Staff Meeting (CrewAI)", "readOnlyHint": True})
    async def crew_staff_meeting(
        mission: str = Field(..., description="The mission/question for the full Wing staff"),
        context: str = Field("", description="Optional additional context"),
    ) -> str:
        """Run a full Wing staff meeting with all 8 personas via CrewAI. COS orchestrates."""
        try:
            result = run_wing_crew(mission, context)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="crew_research",
              annotations={"title": "Run Research Crew (A2 + A9 + COS)", "readOnlyHint": True})
    async def crew_research(
        query: str = Field(..., description="Research question"),
    ) -> str:
        """Run a focused research crew: A2 (intel) + A9 (finance) + COS (synthesis)."""
        try:
            result = run_research_crew(query)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="crew_client_response",
              annotations={"title": "Run Client Response Crew (A2 + A3 + EXEC)", "readOnlyHint": True})
    async def crew_client_response(
        client_name: str = Field(..., description="Client name"),
        request: str = Field(..., description="Client's request or question"),
    ) -> str:
        """Run a client-focused crew: A2 researches, A3 drafts, EXEC polishes."""
        try:
            result = run_client_crew(client_name, request)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="crew_innovate",
              annotations={"title": "Run Innovation Crew (A12 + A5 + COS)", "readOnlyHint": True})
    async def crew_innovate(
        topic: str = Field(..., description="Topic to analyze from first principles"),
    ) -> str:
        """Run an innovation crew: ELON challenges, A5 evaluates, COS synthesizes."""
        try:
            result = run_innovation_crew(topic)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python thunderbird_crewai.py --meeting 'topic'    # Full staff meeting")
        print("  python thunderbird_crewai.py --research 'query'   # Research crew")
        print("  python thunderbird_crewai.py --client 'name' 'request'  # Client crew")
        print("  python thunderbird_crewai.py --innovate 'topic'   # Innovation crew")
        print("  python thunderbird_crewai.py --test               # Quick syntax test")
        sys.exit(0)

    if "--test" in sys.argv:
        print("CrewAI module loads OK")
        agents = _build_agents()
        print(f"Built {len(agents)} agents: {', '.join(agents.keys())}")
        print("Ready for missions.")
        sys.exit(0)

    if "--meeting" in sys.argv:
        idx = sys.argv.index("--meeting")
        topic = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "General status review"
        result = run_wing_crew(topic)
        print(json.dumps(result, indent=2, default=str))

    elif "--research" in sys.argv:
        idx = sys.argv.index("--research")
        query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "Market analysis"
        result = run_research_crew(query)
        print(json.dumps(result, indent=2, default=str))

    elif "--client" in sys.argv:
        idx = sys.argv.index("--client")
        name = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "Test Client"
        req = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else "What excursions are available?"
        result = run_client_crew(name, req)
        print(json.dumps(result, indent=2, default=str))

    elif "--innovate" in sys.argv:
        idx = sys.argv.index("--innovate")
        topic = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "Process improvement"
        result = run_innovation_crew(topic)
        print(json.dumps(result, indent=2, default=str))
