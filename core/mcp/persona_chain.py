"""Auto-Invoke Persona Chains — MISSION-046.
Detects when wing staff output is ready → auto-routes through the chain.
Uses hale_shared_state.jsonl (populated by drive_folder_monitor, MISSION-045).

Chain patterns:
  A1 Navarro profile ready → A8 Reyes experience mapping → COS review
  A8 Reyes recommendation ready → A3 Dani client email → COS gate
  Research complete → A9 finance validation → A3 Dani presentation
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHARED_STATE = ROOT / "OpsCenter" / "hale_shared_state.jsonl"
ROSTER = ROOT / "OpsCenter" / "wing_roster.yaml"
LIFECYCLE_ROUTER = ROOT / "core" / "ops" / "lifecycle_router.py"

# Chain definitions: source → next_persona → action
CHAINS = {
    "a1_profile_complete": {
        "source_persona": "a1",
        "source_event": "profile_complete",
        "chain": [
            {"persona": "a8", "action": "map_experience", "note": "Map Travel DNA to cruise/cabin/excursion/dining recommendations"},
            {"persona": "cos", "action": "review_profile", "note": "COS reviews full intake brief before any client contact"},
        ],
        "final_action": "surface_to_commander",
        "description": "A1 Navarro profile → A8 Reyes → COS Hale → Commander",
    },
    "a8_recommendation_ready": {
        "source_persona": "a8",
        "source_event": "recommendation_ready",
        "chain": [
            {"persona": "a3", "action": "craft_client_email", "note": "Dani crafts client-facing presentation with full intelligence"},
            {"persona": "cos", "action": "wf17_gate", "note": "COS applies WF-17 send gate"},
        ],
        "final_action": "surface_to_commander",
        "description": "A8 recommendation → Dani client email → COS gate → Commander",
    },
    "research_complete": {
        "source_persona": "a2",
        "source_event": "research_complete",
        "chain": [
            {"persona": "a9", "action": "validate_pricing", "note": "A9 validates pricing and commission"},
            {"persona": "a3", "action": "present_to_client", "note": "Dani presents to client with pricing validated"},
        ],
        "final_action": "surface_to_commander",
        "description": "A2 research → A9 finance → Dani → Commander",
    },
}


def check_for_new_output():
    """Scan hale_shared_state.jsonl for new persona output files."""
    if not SHARED_STATE.exists():
        return []

    new_outputs = []
    try:
        with open(SHARED_STATE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                path = entry.get("path", "")
                if _is_persona_output(path):
                    new_outputs.append(entry)
        return new_outputs
    except Exception:
        return []


def _is_persona_output(filepath):
    """Detect if a file path looks like a persona output."""
    path_lower = filepath.lower()
    triggers = ["navarro", "a1_", "dembe", "a2_", "reyes", "a8_",
                 "dani", "a3_", "harlan", "a9_", "luna", "a6_"]
    return any(t in path_lower for t in triggers)


def resolve_chain(filepath):
    """Determine which chain to invoke based on the output file."""
    path_lower = filepath.lower()

    if "navarro" in path_lower or "a1_" in path_lower:
        return "a1_profile_complete"
    if "reyes" in path_lower or "a8_" in path_lower:
        return "a8_recommendation_ready"
    if "dembe" in path_lower or "a2_" in path_lower:
        return "research_complete"

    return None


def build_chain_notification(chain_id, source_file):
    """Build a structured notification for the chain trigger."""
    chain = CHAINS.get(chain_id)
    if not chain:
        return None

    steps = []
    for step in chain["chain"]:
        steps.append(f"  → {step['persona'].upper()}: {step['action']}")

    return {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "persona_chain",
        "chain_id": chain_id,
        "description": chain["description"],
        "trigger_file": source_file,
        "steps": chain["chain"],
        "final_action": chain["final_action"],
        "summary": f"Chain triggered: {chain['description']}\n" + "\n".join(steps),
    }


def register_persona_chain_tools(mcp):
    """Register MCP tools for persona chain management."""

    @mcp.tool(name="resolve_persona_chain")
    async def resolve_persona_chain(filepath: str) -> str:
        """Detect which persona chain a file triggers and return routing steps."""
        chain_id = resolve_chain(filepath)
        if not chain_id:
            return json.dumps({"status": "no_chain_matched", "filepath": filepath})

        notification = build_chain_notification(chain_id, filepath)
        return json.dumps(notification, indent=2)

    @mcp.tool(name="list_persona_chains")
    async def list_persona_chains() -> str:
        """List all registered persona chains with their steps."""
        summary = []
        for chain_id, chain in CHAINS.items():
            step_names = " → ".join(s["persona"].upper() for s in chain["chain"])
            summary.append({
                "chain_id": chain_id,
                "description": chain["description"],
                "route": f"{chain['source_persona'].upper()} → {step_names} → {chain['final_action']}",
            })
        return json.dumps(summary, indent=2)
