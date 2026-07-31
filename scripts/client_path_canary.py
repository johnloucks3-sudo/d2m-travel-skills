#!/home/john/Thunderbird/.venv/bin/python3
"""
Client-Path Canary Monitor — MISSION-427
Monitors the client send path for defects before traffic hits live client addresses.
Part of the Vanguard SO enforcement: 7-day canary window for tools touching client-send path.

Each registered tool is graded by an automated, read-only check (TOOL_CHECKS below), which
calls log_defect() itself on failure. A tool with no wired check is reported UNVERIFIED
instead of READY_TO_GRADUATE — this script never claims graduation readiness it cannot
back with evidence. (2026-07-30 fix: previously defects only entered via a manual --defect
CLI flag with zero callers anywhere in the codebase — see OpsCenter/state/health_check_efficacy_audit.md.)
"""

import json
import logging
import subprocess
import sys
import urllib.error
import urllib.request
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


def check_litellm_gateway() -> tuple[bool, str]:
    """Real check: hit the LiteLLM proxy's own liveness endpoint. Read-only."""
    url = "http://127.0.0.1:4000/health/liveliness"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                return True, f"GET {url} -> 200"
            return False, f"GET {url} -> HTTP {resp.status}"
    except (urllib.error.URLError, OSError) as e:
        return False, f"litellm gateway unreachable: {e}"


def check_form_to_dossier() -> tuple[bool, str]:
    """Real check: run the tool's own --dry-run --once mode (parses live Sheet, writes nothing)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(THUNDERBIRD / "scripts" / "form_to_dossier.py"), "--dry-run", "--once"],
            cwd=THUNDERBIRD, capture_output=True, text=True, timeout=45,
        )
        combined = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            return False, f"--dry-run --once exited {proc.returncode}: {combined[-300:]}"
        if "ERROR:" in combined or "Traceback" in combined:
            return False, f"--dry-run --once reported an error: {combined[-300:]}"
        return True, "dry-run --once completed cleanly"
    except subprocess.TimeoutExpired:
        return False, "dry-run --once timed out after 45s"
    except Exception as e:
        return False, f"dry-run --once failed to launch: {e}"


def check_email_ingestion_pipeline() -> tuple[bool, str]:
    """Real check: run the pipeline's own unit test suite (local classify/dedup logic, no live Gmail calls)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_email_ingestion_classify.py", "tests/test_email_ingestion_dedup.py", "-q"],
            cwd=THUNDERBIRD, capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return False, f"unit tests failed (exit {proc.returncode}): {proc.stdout.strip()[-300:]}"
        last_line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "tests passed"
        return True, last_line
    except subprocess.TimeoutExpired:
        return False, "unit test run timed out after 60s"
    except Exception as e:
        return False, f"unit test run failed to launch: {e}"


# Maps registered tool name -> automated, read-only check function.
# A tool with no entry here is graded UNVERIFIED, never READY_TO_GRADUATE.
TOOL_CHECKS = {
    "litellm_gateway": check_litellm_gateway,
    "form_to_dossier": check_form_to_dossier,
    "email_ingestion_pipeline": check_email_ingestion_pipeline,
}


def run_automated_checks(tools: list[dict]) -> None:
    """Run each tool's wired check and self-report defects via log_defect(). No-op for graduated tools."""
    for t in tools:
        if t.get("graduated"):
            continue
        check_fn = TOOL_CHECKS.get(t["tool"])
        if check_fn is None:
            continue
        ok, detail = check_fn()
        if ok:
            log.info("[CANARY CHECK PASS] %s: %s", t["tool"], detail)
        else:
            log_defect(t["tool"], detail)


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

    has_check = tool["tool"] in TOOL_CHECKS

    if tool.get("graduated"):
        status = "GRADUATED"
        action = "Tool is in production — monitoring only."
    elif defect_count > 0:
        status = "FAILED"
        action = f"Canary FAILED — {defect_count} defect(s) on send path. Revert or fix before graduation."
    elif not has_check:
        status = "UNVERIFIED"
        action = "No automated check wired for this tool — cannot claim graduation readiness without evidence. Wire a check in TOOL_CHECKS, or graduate manually only after documented verification."
    elif days >= canary_days:
        status = "READY_TO_GRADUATE"
        action = f"{days}d canary complete, zero defects, automated check passing. Ready for full production adoption."
    else:
        remaining = canary_days - days
        status = "IN_CANARY"
        action = f"{remaining}d remaining in canary window. {days}d elapsed, {defect_count} defects. Automated check passing."

    return {
        "tool": tool["tool"],
        "status": status,
        "days_elapsed": days,
        "canary_days": canary_days,
        "defect_count": defect_count,
        "internal_only": tool.get("internal_only", True),
        "graduated": tool.get("graduated", False),
        "has_automated_check": has_check,
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

    # Default: run automated checks (self-reports defects), then evaluate + persist
    log.info("=== Client-Path Canary Evaluation — %s ===", datetime.now(timezone.utc).date())
    tools = load_registry()

    run_automated_checks(tools)
    tools = load_registry()  # reload — run_automated_checks may have persisted new defects

    results = [evaluate_canary(t) for t in tools]
    failed = [r for r in results if r["status"] == "FAILED"]
    ready = [r for r in results if r["status"] == "READY_TO_GRADUATE"]
    in_canary = [r for r in results if r["status"] == "IN_CANARY"]
    unverified = [r for r in results if r["status"] == "UNVERIFIED"]

    for r in results:
        log.info("[%s] %s — %s", r["status"], r["tool"], r["action"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tools": len(results),
            "failed": len(failed),
            "ready_to_graduate": len(ready),
            "in_canary": len(in_canary),
            "unverified": len(unverified),
            "graduated": sum(1 for r in results if r["status"] == "GRADUATED"),
        },
        "tools": results,
        "failed_tools": [r["tool"] for r in failed],
        "ready_to_graduate": [r["tool"] for r in ready],
        "unverified_tools": [r["tool"] for r in unverified],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2))
    save_registry(tools)  # persist so state survives across runs instead of resetting to defaults
    log.info("Report → %s", OUTPUT_FILE)

    if failed:
        log.error("⚠️ %d tool(s) FAILED canary. Block from production until resolved.", len(failed))
        sys.exit(1)
    if unverified:
        log.warning("⚠️ %d tool(s) UNVERIFIED — no automated check, no graduation claim made.", len(unverified))
    if ready:
        log.info("✅ %d tool(s) ready to graduate. Run: python3 scripts/client_path_canary.py --graduate TOOLNAME", len(ready))


if __name__ == "__main__":
    main()
