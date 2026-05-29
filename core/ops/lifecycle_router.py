#!/usr/bin/env python3
"""Lifecycle ARC Router — MISSION-044.
Reads lifecycle_decision_trees.yaml and returns routing decisions.
Both HALE-OC and HALE-CC use this to auto-route touchpoints.
"""
import os
import yaml
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
YAML_PATH = ROOT / "core" / "ops" / "lifecycle_decision_trees.yaml"

_cache = None

def _load():
    global _cache
    if _cache is None:
        with open(YAML_PATH) as f:
            _cache = yaml.safe_load(f)
    return _cache

def get_arc_route(arc_id: str, position: str):
    """Get routing for an ARC touchpoint.
    arc_id: 'arc1', 'arc2', 'arc3', 'arc4'
    position: 'a', 'b', 'c', 'd'
    Returns: dict with route, client_facing, cos_review
    """
    data = _load()
    arc = data.get("arc_routing", {}).get(arc_id)
    if not arc:
        return {"error": f"Unknown ARC: {arc_id}"}
    pos = arc.get("positions", {}).get(position)
    if not pos:
        return {"error": f"Unknown position: {arc_id}/{position}"}
    return {
        "arc_id": arc_id,
        "label": arc.get("label"),
        "position": position,
        "position_label": pos.get("label"),
        "route": pos.get("route", []),
        "client_facing": pos.get("client_facing", False),
        "cos_review": pos.get("cos_review", False),
    }

def get_touchpoint_route(tp_id: str):
    """Get routing for a non-ARC touchpoint.
    tp_id: 'tp_0_5', 'tp_1', 'tp_1_1', 'tp_2', 'tp_3', 'tp_5', 'tp_6'
    """
    data = _load()
    tp = data.get("touchpoint_routing", {}).get(tp_id)
    if not tp:
        return {"error": f"Unknown touchpoint: {tp_id}"}
    return {
        "touchpoint_id": tp_id,
        "label": tp.get("label"),
        "route": tp.get("route", []),
        "client_facing": tp.get("client_facing", False),
        "cos_review": tp.get("cos_review", False),
    }

def list_arcs():
    """List all ARC families and their positions."""
    data = _load()
    result = []
    for arc_id, arc in data.get("arc_routing", {}).items():
        for pos_id, pos in arc.get("positions", {}).items():
            persona_names = [s["persona"] for s in pos.get("route", [])]
            result.append({
                "arc": arc_id,
                "position": pos_id,
                "label": pos.get("label"),
                "route": " → ".join(persona_names),
                "client_facing": pos.get("client_facing", False),
            })
    return result

def list_touchpoints():
    """List all non-ARC touchpoints."""
    data = _load()
    result = []
    for tp_id, tp in data.get("touchpoint_routing", {}).items():
        persona_names = [s["persona"] for s in tp.get("route", [])]
        result.append({
            "id": tp_id,
            "label": tp.get("label"),
            "route": " → ".join(persona_names),
            "client_facing": tp.get("client_facing", False),
        })
    return result

def validate():
    """Validate YAML is well-formed and all personas exist in roster."""
    try:
        data = _load()
    except Exception as e:
        return [f"YAML parse error: {e}"]

    errors = []
    valid_personas = {"a1", "a2", "a3", "a5", "a6", "a7", "a8", "a9", "a12", "cos", "exec", "ch", "a10"}

    for arc_id, arc in data.get("arc_routing", {}).items():
        for pos_id, pos in arc.get("positions", {}).items():
            for step in pos.get("route", []):
                if step["persona"] not in valid_personas:
                    errors.append(f"{arc_id}/{pos_id}: Unknown persona '{step['persona']}'")

    for tp_id, tp in data.get("touchpoint_routing", {}).items():
        for step in tp.get("route", []):
            if step["persona"] not in valid_personas:
                errors.append(f"{tp_id}: Unknown persona '{step['persona']}'")

    return errors

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        errors = validate()
        if errors:
            print("VALIDATION ERRORS:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("✓ All routes valid")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        print("=== ARC ROUTES ===")
        for r in list_arcs():
            print(f"  {r['arc']}-{r['position'].upper()}: {r['label']}")
            print(f"    Route: {r['route']}")
            print(f"    Client: {'YES' if r['client_facing'] else 'no'}")
        print("\n=== TOUCHPOINTS ===")
        for t in list_touchpoints():
            print(f"  {t['id']}: {t['label']}")
            print(f"    Route: {t['route']}")
            print(f"    Client: {'YES' if t['client_facing'] else 'no'}")
    elif len(sys.argv) > 2 and sys.argv[1] == "route":
        arc = sys.argv[2]
        pos = sys.argv[3] if len(sys.argv) > 3 else "a"
        if arc.startswith("tp"):
            r = get_touchpoint_route(arc)
        else:
            r = get_arc_route(arc, pos)
        if "error" in r:
            print(f"ERROR: {r['error']}")
        else:
            print(f"Route: {r.get('label', '')}")
            for step in r.get("route", []):
                print(f"  → {step['persona']} ({step['model']}): {step['action']}")
            print(f"Client-facing: {'YES' if r.get('client_facing') else 'no'}")
            print(f"COS review: {'YES' if r.get('cos_review') else 'no'}")
    else:
        print("Usage:")
        print("  lifecycle_router.py validate")
        print("  lifecycle_router.py list")
        print("  lifecycle_router.py route <arc_id> <position>")
        print("  lifecycle_router.py route <tp_id>")
