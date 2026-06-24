#!/home/john/Thunderbird/.venv/bin/python3
"""
Client-Path Canary Monitor — MISSION-427
Monitors the client send path for defects before traffic hits live client addresses.
Part of the Vanguard SO enforcement: 7-day canary window for tools touching client-send path.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
OUTPUT_FILE = THUNDERBIRD / "output" / "client_path_canary_report.json"
CANARY_STATE = THUNDERBIRD / "OpsCenter" / "state" / "canary_registry.json"
LOG_FILE = THUNDERBIRD / "logs" / "client_path_canary.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Client-path tools registered for canary monitoring
# Each entry: tool name, enrolled date, canary_days, description
DEFAULT_CANARY_TOOLS = [
    {
        "tool": "litellm_gateway",
        "enrolled": "2026-06-24",
        "canary_days": 7,
        "description": "LiteLLM AI gateway on :4000 — routes AI calls for client product generation",
        "client_path": True,
        "internal_only": True,
        "graduated": False,
        "defects": [],
    },
    {
        "tool": "form_to_dossier",
        "enrolled": "2026-06-24",
        "canary_days": 7,
        "description": "Form → dossier pipeline — ingests client intake form data",
        "client_path": True,
        "internal_only": True,
        "graduated": False,
        "defects": [],
    },
    {
        "tool": "email_ingestion_pipeline",
        "enrolled": "2026-06-24",
        "canary_days": 7,
        "description": "Email ingestion — parses inbound client communications",
        "client_path": True,
        "internal_only": True,
        "graduated": False,
        "defects": [],
    },
]


def load_registry() -> list[dict]:
    if CANARY_STATE.exists():
        try:
            return json.loads(CANARY_STATE.read_text()).get("tools", [])
        except Exception:
            pass
    return DEFAULT_CANARY_TOOLS.copy()


def save_registry(tools: list[dict]) -> None:
    CANARY_STATE.parent.mkdir(parents=True, exist_ok=True)
    CANARY_STATE.write_text(json.dumps({"tools": tools, "last_updated": datetime.now(timezone.utc).isoformat()}, indent=2))


def days_since(date_str: str) -> int:
    enrolled = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - enrolled).days


def evaluate_canary(tool: dict) -> dict:
    """Evaluate whether a tool has passed its canary window."""
    days = days_since(tool["enrolled"])
    defect_count = len(tool.get("defects", []))
    canary_days = tool.get("canary_days", 7)

    if tool.get("graduated"):
        status = "GRADUATED"
        action = "Tool is in production — monitoring only."
    elif defect_count > 0:
        status = "FAILED"
        action = f"Canary FAILED — {defect_count} defect(s) on send path. Revert or fix before graduation."
    elif days >= canary_days:
        status = "READY_TO_GRADUATE"
        action = f"{days}d canary complete, zero defects. Ready for full production adoption."
    else:
        remaining = canary_days - days
        status = "IN_CANARY"
        action = f"{remaining}d remaining in canary window. {days}d elapsed, {defect_count} defects."

    return {
        "tool": tool["tool"],
        "status": status,
        "days_elapsed": days,
        "canary_days": canary_days,
        "defect_count": defect_count,
        "internal_only": tool.get("internal_only", True),
        "graduated": tool.get("graduated", False),
        "action": action,
        "description": tool.get("description", ""),
    }


def log_defect(tool_name: str, defect: str) -> None:
    """Log a client-path defect for a canary tool."""
    tools = load_registry()
    for t in tools:
        if t["tool"] == tool_name:
            t.setdefault("defects", []).append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "detail": defect,
            })
            log.error("[CANARY DEFECT] %s: %s", tool_name, defect)
            break
    save_registry(tools)


def graduate_tool(tool_name: str) -> bool:
    """Graduate a tool from canary to production after zero-defect window."""
    tools = load_registry()
    for t in tools:
        if t["tool"] == tool_name:
            result = evaluate_canary(t)
            if result["status"] in ("READY_TO_GRADUATE", "GRADUATED"):
                t["graduated"] = True
                t["internal_only"] = False
                log.info("[CANARY GRADUATED] %s → production", tool_name)
                save_registry(tools)
                return True
            else:
                log.warning("[CANARY] Cannot graduate %s: %s", tool_name, result["status"])
                return False
    return False


def enroll_tool(name: str, description: str, canary_days: int = 7) -> None:
    """Enroll a new tool in the canary program."""
    tools = load_registry()
    if not any(t["tool"] == name for t in tools):
        tools.append({
            "tool": name,
            "enrolled": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "canary_days": canary_days,
            "description": description,
            "client_path": True,
            "internal_only": True,
            "graduated": False,
            "defects": [],
        })
        save_registry(tools)
        log.info("[CANARY ENROLLED] %s — %dd window", name, canary_days)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Client-path canary monitor")
    parser.add_argument("--defect", nargs=2, metavar=("TOOL", "DETAIL"), help="Log a defect for a tool")
    parser.add_argument("--graduate", metavar="TOOL", help="Graduate a tool to production")
    parser.add_argument("--enroll", nargs=3, metavar=("TOOL", "DESC", "DAYS"), help="Enroll new tool")
    args = parser.parse_args()

    if args.defect:
        log_defect(args.defect[0], args.defect[1])
        return

    if args.graduate:
        graduate_tool(args.graduate)
        return

    if args.enroll:
        enroll_tool(args.enroll[0], args.enroll[1], int(args.enroll[2]))
        return

    # Default: run evaluation
    log.info("=== Client-Path Canary Evaluation — %s ===", datetime.now(timezone.utc).date())
    tools = load_registry()

    results = [evaluate_canary(t) for t in tools]
    failed = [r for r in results if r["status"] == "FAILED"]
    ready = [r for r in results if r["status"] == "READY_TO_GRADUATE"]
    in_canary = [r for r in results if r["status"] == "IN_CANARY"]

    for r in results:
        log.info("[%s] %s — %s", r["status"], r["tool"], r["action"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tools": len(results),
            "failed": len(failed),
            "ready_to_graduate": len(ready),
            "in_canary": len(in_canary),
            "graduated": sum(1 for r in results if r["status"] == "GRADUATED"),
        },
        "tools": results,
        "failed_tools": [r["tool"] for r in failed],
        "ready_to_graduate": [r["tool"] for r in ready],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2))
    log.info("Report → %s", OUTPUT_FILE)

    if failed:
        log.error("⚠️ %d tool(s) FAILED canary. Block from production until resolved.", len(failed))
        sys.exit(1)
    if ready:
        log.info("✅ %d tool(s) ready to graduate. Run: python3 scripts/client_path_canary.py --graduate TOOLNAME", len(ready))


if __name__ == "__main__":
    main()
