#!/usr/bin/env python3
"""
integration_scoreboard.py — HALE-OS 100% Integration Progress Tracker
ELON (A12) · 2026-07-02

Reads actual on-disk state and scores 0-100 per dimension:
  1. Seat Integration   — declared seats vs .claude/agents/ files + OC config
  2. Plane Integration  — brain_bridge_board.json cross-lane plan depth
  3. Memory Integration — Qdrant + Graphiti runbook + Graphiti MCP config
  4. Process Integration— metronome heartbeat + OC worker + board completions

Outputs:
  /home/john/Thunderbird/OpsCenter/integration_scoreboard.json  (machine)
  Human-readable table (stdout)
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

# ---------------------------------------------------------------------------
# ALIAS MAP: wing_org.yaml seat name → expected .claude/agents/<file>.md name
# ---------------------------------------------------------------------------
SEAT_ALIAS = {
    "hale":      "cos-hale",
    "dembe":     "a2-dembe",
    "dani":      "a3-moreau",
    "luna":      "a6-voss",
    "sterling":  "a7-sterling",
    "reyes":     "a8-reyes",
    "harlan":    "a9-harlan",
    "ikeda":     "a10-ikeda",
    "elon":      "a12-elon",
    "naia":      "exec-solberg-vega",
    "whetstone": "a14-whetstone",
}
OC_SEATS = {"oc-scout-1", "oc-scout-2"}


# ---------------------------------------------------------------------------
# 1. SEAT INTEGRATION
# ---------------------------------------------------------------------------
def score_seats() -> tuple[int, dict]:
    agents_dir = ROOT / ".claude" / "agents"
    disk_stems = set()
    if agents_dir.exists():
        for f in agents_dir.iterdir():
            if f.suffix == ".md":
                disk_stems.add(f.stem)

    oc_agents_path = ROOT / "config" / "opencode_agents.generated.json"
    oc_present = set()
    if oc_agents_path.exists():
        try:
            data = json.loads(oc_agents_path.read_text())
            oc_present = set(data.keys())
        except Exception:
            pass

    wing_org_path = ROOT / "config" / "wing_org.yaml"
    declared_cc = list(SEAT_ALIAS.keys())
    declared_oc = list(OC_SEATS)

    detail = {}
    found = 0

    for seat in declared_cc:
        file_stem = SEAT_ALIAS[seat]
        present = file_stem in disk_stems
        detail[seat] = {"engine": "cc", "file": file_stem + ".md", "found": present}
        if present:
            found += 1

    for seat in declared_oc:
        present = seat in oc_present
        detail[seat] = {"engine": "oc", "file": "opencode_agents.generated.json", "found": present}
        if present:
            found += 1

    total = len(declared_cc) + len(declared_oc)
    score = round((found / total) * 100) if total else 0
    return score, detail


# ---------------------------------------------------------------------------
# 2. PLANE INTEGRATION
# ---------------------------------------------------------------------------
def score_plane() -> tuple[int, dict]:
    board_path = ROOT / "OpsCenter" / "brain_bridge_board.json"
    if not board_path.exists():
        return 0, {"board_exists": False, "reason": "brain_bridge_board.json not found"}

    try:
        board = json.loads(board_path.read_text())
    except Exception as e:
        return 0, {"board_exists": True, "parse_error": str(e)}

    plans = board.get("plans", {})
    if not plans:
        return 50, {"board_exists": True, "plans": 0, "cross_lane_plans": 0}

    cross_lane = 0
    for plan_id, plan in plans.items():
        tasks = plan.get("tasks", {})
        lanes = {t.get("lane") for t in tasks.values() if t.get("lane")}
        if "cc" in lanes and "oc" in lanes:
            cross_lane += 1

    score = 100 if cross_lane >= 1 else 50
    return score, {
        "board_exists": True,
        "total_plans": len(plans),
        "cross_lane_plans": cross_lane,
    }


# ---------------------------------------------------------------------------
# 3. MEMORY INTEGRATION
# ---------------------------------------------------------------------------
def score_memory() -> tuple[int, dict]:
    detail = {}

    # Qdrant up?
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "2", "http://127.0.0.1:6333/collections"],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        qdrant_up = data.get("status") == "ok"
        collections = [c["name"] for c in data.get("result", {}).get("collections", [])]
    except Exception as e:
        qdrant_up = False
        collections = []
    detail["qdrant"] = {"up": qdrant_up, "collections": collections}

    # Graphiti runbook exists?
    runbook_path = ROOT / "docs" / "GRAPHITI_SELFHOST_RUNBOOK.md"
    graphiti_runbook = runbook_path.exists()
    detail["graphiti_runbook"] = {"exists": graphiti_runbook, "path": str(runbook_path)}

    # Graphiti in .mcp.json?
    mcp_path = ROOT / ".mcp.json"
    graphiti_mcp = False
    if mcp_path.exists():
        try:
            mcp_data = json.loads(mcp_path.read_text())
            servers = mcp_data.get("mcpServers", {})
            graphiti_mcp = any("graphiti" in k.lower() for k in servers)
        except Exception:
            pass
    detail["graphiti_mcp_configured"] = graphiti_mcp

    score = (33 if qdrant_up else 0) + (33 if graphiti_runbook else 0) + (33 if graphiti_mcp else 0)
    return score, detail


# ---------------------------------------------------------------------------
# 4. PROCESS INTEGRATION
# ---------------------------------------------------------------------------
def score_process() -> tuple[int, dict]:
    detail = {}

    # .metronome_seq exists (OODA heartbeat running)?
    metronome_path = ROOT / "OpsCenter" / ".metronome_seq"
    metronome_up = metronome_path.exists()
    detail["metronome_seq"] = {"exists": metronome_up, "path": str(metronome_path)}

    # scripts/opencode_worker.py exists?
    oc_worker_path = ROOT / "scripts" / "opencode_worker.py"
    oc_worker = oc_worker_path.exists()
    detail["opencode_worker_py"] = {"exists": oc_worker, "path": str(oc_worker_path)}

    # At least one completed task in brain_bridge board?
    board_path = ROOT / "OpsCenter" / "brain_bridge_board.json"
    board_has_completed = False
    if board_path.exists():
        try:
            board = json.loads(board_path.read_text())
            for plan in board.get("plans", {}).values():
                for task in plan.get("tasks", {}).values():
                    if task.get("status") == "completed":
                        board_has_completed = True
                        break
        except Exception:
            pass
    detail["board_has_completed_task"] = board_has_completed

    score = (33 if metronome_up else 0) + (33 if oc_worker else 0) + (33 if board_has_completed else 0)
    return score, detail


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    ts = datetime.now(timezone.utc).isoformat()

    seat_score, seat_detail = score_seats()
    plane_score, plane_detail = score_plane()
    memory_score, memory_detail = score_memory()
    process_score, process_detail = score_process()

    overall = round((seat_score + plane_score + memory_score + process_score) / 4)

    # --- gaps: what's missing for each dimension to reach 100 ---
    gaps = []
    if seat_score < 100:
        missing = [s for s, d in seat_detail.items() if not d["found"]]
        gaps.append(f"Seat: missing agent files for {missing}")
    if plane_score < 100:
        gaps.append("Plane: no cross-lane (cc+oc) plan on brain_bridge board yet")
    if memory_score < 100:
        sub = []
        if not memory_detail["qdrant"]["up"]:
            sub.append("Qdrant down")
        if not memory_detail["graphiti_runbook"]["exists"]:
            sub.append("Graphiti runbook missing")
        if not memory_detail["graphiti_mcp_configured"]:
            sub.append("Graphiti not wired into .mcp.json")
        gaps.append("Memory: " + "; ".join(sub))
    if process_score < 100:
        sub = []
        if not process_detail["metronome_seq"]["exists"]:
            sub.append(".metronome_seq missing")
        if not process_detail["opencode_worker_py"]["exists"]:
            sub.append("scripts/opencode_worker.py not built")
        if not process_detail["board_has_completed_task"]:
            sub.append("no completed board tasks")
        gaps.append("Process: " + "; ".join(sub))

    result = {
        "generated_at": ts,
        "overall": overall,
        "dimensions": {
            "seat_integration": {
                "score": seat_score,
                "max": 100,
                "detail": seat_detail,
            },
            "plane_integration": {
                "score": plane_score,
                "max": 100,
                "detail": plane_detail,
            },
            "memory_integration": {
                "score": memory_score,
                "max": 100,
                "detail": memory_detail,
            },
            "process_integration": {
                "score": process_score,
                "max": 100,
                "detail": process_detail,
            },
        },
        "gaps_to_100": gaps,
    }

    out_path = ROOT / "OpsCenter" / "integration_scoreboard.json"
    out_path.write_text(json.dumps(result, indent=2))

    # --- Human-readable table ---
    bar_width = 30

    def bar(score):
        filled = round(score / 100 * bar_width)
        return "[" + "█" * filled + "·" * (bar_width - filled) + "]"

    def emoji(score):
        if score == 100: return "✅"
        if score >= 66:  return "🟡"
        if score >= 33:  return "🟠"
        return "🔴"

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      HALE-OS INTEGRATION SCOREBOARD  —  2026-07-02          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  OVERALL                                              {overall:3d}/100 ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    rows = [
        ("1. Seat Integration",    seat_score),
        ("2. Plane Integration",   plane_score),
        ("3. Memory Integration",  memory_score),
        ("4. Process Integration", process_score),
    ]
    for label, score in rows:
        b = bar(score)
        e = emoji(score)
        print(f"║  {e} {label:<22} {b}  {score:3d} ║")

    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  GAPS TO 100%                                                ║")
    if gaps:
        for g in gaps:
            # word-wrap at 58 chars
            words = g.split()
            line = ""
            for w in words:
                if len(line) + len(w) + 1 > 58:
                    print(f"║    {line:<58}║")
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                print(f"║    {line:<58}║")
    else:
        print("║    None — 100% integration achieved!                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\nJSON written → {out_path}")


if __name__ == "__main__":
    main()
