"""
CrewAI Agent Loader — reads .md files from .claude/agents/, parses frontmatter,
returns a dict of CrewAI Agent objects. Fully headless, no prompts.
"""
import re
from pathlib import Path
from typing import Dict, Any

AGENTS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "agents"


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract YAML-like key: value from --- delimited block."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    meta: Dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip("'\"-").strip()
            meta[key.strip()] = val
    return meta


def _parse_category(text: str) -> str:
    """Infer a category label from body content."""
    lower = text.lower()
    if "crisis" in lower or "logistic" in lower or "troubleshoot" in lower:
        return "crisis_logistics"
    if "research" in lower and ("intel" in lower or "competitor" in lower):
        return "research_intel"
    if "business" in lower and ("strateg" in lower or "pricing" in lower):
        return "strategy_planning"
    if "brand" in lower or "copy" in lower or "voice" in lower or "narrative" in lower:
        return "brand_copywriting"
    if "client" in lower and ("comm" in lower or "booking" in lower):
        return "operations_communications"
    if "commission" in lower or ("cost" in lower and "audit" in lower):
        return "finance_audit"
    if "ethic" in lower or "morale" in lower:
        return "ethics"
    if "automation" in lower or "first-principles" in lower:
        return "innovation"
    if "route" in lower or "orchestr" in lower or "staff meeting" in lower:
        return "coordination"
    return "general"


def load_agents(agents_dir: Path | None = None) -> Dict[str, Any]:
    """
    Scan *agents_dir* for *.md files, parse each one, and return
    ``{agent_name: CrewAI_Agent}``.
    """
    from crewai import Agent

    scan_dir = agents_dir or AGENTS_DIR
    result: Dict[str, Any] = {}

    if not scan_dir.is_dir():
        return result

    for md_file in sorted(scan_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(raw)
        name = fm.get("name", md_file.stem)
        description = fm.get("description", name)
        role = description.split("—")[0].strip() if "—" in description else name
        category = _parse_category(raw)

        agent = Agent(
            role=role,
            goal=description,
            backstory=raw[:500],
            verbose=False,
            allow_delegation=True,
            memory=False,
            cache=True,
        )
        result[name] = agent

    return result


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    agents = load_agents()
    print(f"Loaded {len(agents)} agents:")
    for n in sorted(agents):
        a = agents[n]
        print(f"  {n:22s} role={a.role[:60]}")
