#!/usr/bin/env python3
"""Crew Runner - assembles and executes CrewAI crews headless.
Wires all agents through the LLM Router (Groq -> DeepSeek -> OpenRouter).
NO Anthropic spend, NO Gemini. Anthropic key is a Poe routing decoy.
"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from llm_router import get_orchestrator_llm, get_reasoning_llm, get_router_llm, get_free_llm

def _build_agent(name, role, goal, backstory="", llm=None):
    try:
        from crewai import Agent
        kwargs = dict(role=role, goal=goal, backstory=backstory,
                     allow_delegation=False, verbose=False)
        if llm:
            kwargs["llm"] = llm
        return Agent(**kwargs)
    except Exception as e:
        print(f"[WARN] Failed to create Agent '{name}': {e}")
        return None

def build_crew(task_text, llm_tier="orchestrator"):
    from crewai import Crew, Task
    
    llm_getters = {
        "orchestrator": get_orchestrator_llm,
        "reasoning": get_reasoning_llm,
        "router": get_router_llm,
        "free": get_free_llm,
    }
    llm = llm_getters.get(llm_tier, get_orchestrator_llm)()
    if not llm:
        return {"status": "error", "error": "No LLM available. Check .env keys."}
    
    from agent_loader import load_all_agents
    from task_router import route_task
    
    all_agents = load_all_agents()
    task_plan = route_task(task_text, all_agents)
    
    crew_agents = []
    for match in task_plan["agent_assignments"]:
        agent_meta = all_agents.get(match["agent_name"])
        if agent_meta:
            a = _build_agent(
                match["agent_name"],
                match["role"],
                match["goal"],
                agent_meta.get("backstory", ""),
                llm=llm
            )
            if a: crew_agents.append(a)
    
    if not crew_agents:
        return {"status": "error", "error": "No agents matched for this task."}
    
    crew_tasks = []
    for sub in task_plan["subtasks"]:
        crew_tasks.append(Task(
            description=sub["description"],
            expected_output=sub["expected_output"],
            agent=crew_agents[0] if crew_agents else None,
            llm=llm
        ))
    
    crew = Crew(
        agents=crew_agents,
        tasks=crew_tasks,
        process="sequential",
        verbose=True,
    )
    
    return {"crew": crew, "task_plan": task_plan, "llm_tier": llm_tier, "agent_count": len(crew_agents)}

def run_crew(task_text, llm_tier="orchestrator", output_file=None):
    print(f"\n{'='*60}")
    print(f"CREW RUN: {task_text}")
    print(f"LLM Tier: {llm_tier}")
    print(f"{'='*60}\n")
    
    result = build_crew(task_text, llm_tier=llm_tier)
    
    if result.get("status") == "error":
        print(f"ERROR: {result['error']}")
        return result
    
    crew = result["crew"]
    task_plan = result["task_plan"]
    
    try:
        kickoff_result = crew.kickoff()
        output = str(kickoff_result) if kickoff_result else "No output"
        
        final = {
            "status": "success",
            "output": output,
            "task_plan": task_plan,
            "agent_count": result["agent_count"],
        }
        
        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(f"Task: {task_text}\n")
                f.write(f"Agents Used: {result['agent_count']}\n")
                f.write(f"{'='*60}\n\n")
                f.write(output)
            print(f"\nOutput written to: {output_file}")
        
        return final
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crew_runner.py 'task description'")
        sys.exit(1)
    
    task = sys.argv[1]
    llm_tier = sys.argv[2] if len(sys.argv) > 2 else "orchestrator"
    output = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = run_crew(task, llm_tier, output)
    print(json.dumps(result, indent=2, default=str)[:2000])
