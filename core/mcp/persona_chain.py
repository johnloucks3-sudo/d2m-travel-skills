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
    "ci_health_signal": {
        "source_persona": "grim_reaper",
        "source_event": "ci_health_event",
        "chain": [
            {"persona": "elon", "action": "evaluate_adopt", "note": "ELON evaluates capability/tech stack health and adoption opportunities"},
            {"persona": "sterling", "action": "gate_metrics", "note": "Sterling verifies code process, test gates, and health metrics"},
            {"persona": "whetstone", "action": "currency_replace", "note": "Whetstone maintains currency, trims rot, and manages replacements"},
        ],
        "final_action": "auto_report",
        "description": "Grim Reaper CI health event → ELON evaluate → Sterling gate → Whetstone currency → Auto Report",
    },
    "luna_narrative_ready": {
        "source_persona": "luna",
        "source_event": "narrative_ready",
        "chain": [
            {"persona": "naia", "action": "brand_pass", "note": "Naia brand pass — tone, D2M markers, structure (SLA: 4h fallback)"},
            {"persona": "dani", "action": "client_presentation", "note": "Dani crafts final client presentation with narrative copy"},
            {"persona": "cos", "action": "wf17_gate", "note": "COS applies WF-17 send gate"},
        ],
        "final_action": "surface_to_commander",
        "description": "Luna narrative copy → Naia brand pass (4h timeout) → Dani client presentation → COS gate → Commander",
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
    triggers = [
        "navarro", "a1_", "dembe", "a2_", "reyes", "a8_",
        "dani", "a3_", "harlan", "a9_", "luna", "a6_",
        "grim_reaper", "ci_health"
    ]
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
    if "grim_reaper" in path_lower or "ci_health" in path_lower:
        return "ci_health_signal"
    if "luna" in path_lower or "a6_" in path_lower:
        return "luna_narrative_ready"

    return None


def check_luna_naia_timeouts(timeout_hours: float = 4.0) -> list[dict]:
    """Check for pending Luna->Naia brand pass handoffs exceeding timeout.
    
    If Naia has not actioned a brand pass within timeout_hours (default 4h),
    auto-posts an ASK signal to Hale on staff_signal_bus to unblock Dani.
    """
    naia_queue_file = ROOT / "storage" / "naia_brand_pass_queue.jsonl"
    if not naia_queue_file.exists():
        return []

    escalations = []
    now = datetime.now(timezone.utc)
    lines = naia_queue_file.read_text(encoding="utf-8").splitlines()
    updated_lines = []

    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            status = entry.get("status", "pending")
            if status in ("completed", "approved", "bypassed"):
                updated_lines.append(line)
                continue

            ts_str = entry.get("ts", "")
            if not ts_str:
                updated_lines.append(line)
                continue

            # Parse ISO timestamp
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                updated_lines.append(line)
                continue

            elapsed_hours = (now - ts).total_seconds() / 3600.0
            if elapsed_hours >= timeout_hours and not entry.get("escalated_to_hale"):
                client = entry.get("client", "Unknown Client")
                tp_id = entry.get("tp_id", "N/A")
                subject = entry.get("subject", "")

                try:
                    from core.ai_infra.staff_signal_bus import post
                    sig_id = post(
                        from_persona="dani",
                        type="ASK",
                        subject=f"Luna->Naia Creative Timeout: {client} (TP {tp_id})",
                        detail=(
                            f"Luna's copy for {client} (TP {tp_id}, '{subject}') has been waiting on "
                            f"Naia brand pass for {elapsed_hours:.1f}h (SLA {timeout_hours}h). "
                            f"Auto-escalating to COS Hale for routing decision / bypass."
                        ),
                        priority="high",
                    )
                    entry["escalated_to_hale"] = True
                    entry["escalation_sig_id"] = sig_id
                    entry["escalated_at"] = now.isoformat()
                    escalations.append({
                        "client": client,
                        "tp_id": tp_id,
                        "elapsed_hours": elapsed_hours,
                        "signal_id": sig_id,
                    })
                except Exception as exc:
                    pass

            updated_lines.append(json.dumps(entry))
        except Exception:
            updated_lines.append(line)

    if escalations:
        naia_queue_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    return escalations


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

    @mcp.tool(name="check_chain_timeouts")
    async def check_chain_timeouts(timeout_hours: float = 4.0) -> str:
        """Check for unacted persona handoffs exceeding SLA and auto-escalate to Hale."""
        escalations = check_luna_naia_timeouts(timeout_hours=timeout_hours)
        return json.dumps({"escalations": escalations, "count": len(escalations)}, indent=2)

