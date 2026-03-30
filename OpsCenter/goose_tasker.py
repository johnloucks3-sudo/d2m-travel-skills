"""
goose_tasker.py — Goose → Claude Consultant Interface
======================================================
Allows Goose to task Claude directly, acting on Commander's authority.
All tasks logged for Commander review. Claude executes but retains
dissent clause for tasks contradicting standing directives.

AUTHORITY MODEL:
  - Goose tasks Claude "ON BEHALF OF COMMANDER"
  - Full execution authority — no pre-confirmation required
  - ALL tasks logged to commander_review_log.md
  - Dissent triggers: task contradicts standing Commander directive
                      task touches client data/output outside wing
  - Dissent outcome: Claude executes AND flags concern prominently
  - Dissent destination: dissent_log.md + Telegram alert to Commander

PERMITTED TASK TYPES:
  research, synthesis, code_analysis, strategic, client_writing,
  system_ops, arbitration_prep, process_analysis, tech_opportunity

INVOCATION (Goose calls this script directly):
  python3 goose_tasker.py --task-type research --instructions "..." \
    --output-dest claude_output.md [--context-files file1.md,file2.md] \
    [--priority HIGH] [--pii false]

Author: Claude Sonnet 4.6 | Date: 2026-03-30
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──
ROOT       = Path(__file__).resolve().parent.parent
OPSCENTER  = ROOT / "OpsCenter"
COLLAB     = OPSCENTER / "collaboration"
INBOX      = COLLAB / "claude_inbox.md"
DISSENT    = COLLAB / "dissent_log.md"
REVIEW_LOG = COLLAB / "commander_review_log.md"
ROUTING    = COLLAB / "routing_log.md"
BLACKBOARD = COLLAB / "blackboard.md"

MT = timezone(timedelta(hours=-6))

# ── Permitted task types ──
PERMITTED_TYPES = {
    "research":          "Research & synthesis",
    "synthesis":         "Research & synthesis",
    "code_analysis":     "Code analysis & debugging",
    "debugging":         "Code analysis & debugging",
    "strategic":         "Strategic reasoning & planning",
    "planning":          "Strategic reasoning & planning",
    "client_writing":    "Client-facing writing (D2M voice)",
    "system_ops":        "System/file operations on YOGA",
    "arbitration_prep":  "Arbitration prep (writing Deepseek inbox)",
    "process_analysis":  "Process/procedure analysis",
    "tech_opportunity":  "Technology opportunity assessment",
}

# ── Standing Commander directives (Claude checks tasks against these) ──
STANDING_DIRECTIVES = [
    "Never send email outside the wing without explicit Commander approval",
    "Never create drafts in johnloucks3@gmail.com",
    "Never use Love Group Travel branding",
    "Never route PII tasks to Deepseek or Groq",
    "Never commit to git without Commander approval",
    "Never send client-facing output without WF-17 gate",
    "Deepseek is arbitrator — never route arbitration to Claude or Goose",
    "Goose does not touch 03_CLAUDE_MAX_QUEUE.json or thunderbird_model_router.py",
]

# ── Dissent triggers (task types that warrant extra scrutiny) ──
DISSENT_TRIGGER_TYPES = {"client_writing", "system_ops"}
DISSENT_KEYWORDS = [
    "send email", "send to client", "git commit", "git push",
    "delete", "rm -rf", "drop table", "love group travel",
    "johnloucks3 draft", "outside the wing", "override",
]

TELEGRAM_BOT_TOKEN   = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER   = os.environ.get("TELEGRAM_COMMANDER_ID", "")


def _ts() -> str:
    return datetime.now(MT).strftime("%Y-%m-%dT%H:%M:%S MT")


def _ts_id() -> str:
    return datetime.now(MT).strftime("%Y%m%d-%H%M")


def _safe_append(path: Path, text: str):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"[goose_tasker] Write failed {path.name}: {e}", file=sys.stderr)


def _send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_COMMANDER, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def _check_dissent(task_type: str, instructions: str, pii: bool) -> tuple[bool, str]:
    """
    Check if task contradicts any standing Commander directive.
    Returns (should_dissent: bool, reason: str)
    """
    instructions_lower = instructions.lower()

    # Hard block: PII to forbidden models
    if pii and task_type in {"arbitration_prep", "code_analysis", "debugging"}:
        return True, (
            "Task flagged PII=TRUE but task_type routes to Deepseek or Groq. "
            "Standing directive: PII tasks must stay with Claude or Goose only."
        )

    # Keyword check against known dangerous patterns
    triggered = [kw for kw in DISSENT_KEYWORDS if kw in instructions_lower]
    if triggered:
        return True, (
            f"Instructions contain potentially directive-contradicting language: "
            f"{triggered}. Verify this does not violate standing orders."
        )

    # client_writing requires WF-17 gate reminder
    if task_type == "client_writing":
        return True, (
            "client_writing task type flagged for WF-17 compliance reminder. "
            "Claude will execute but output must not leave wing without Commander approval."
        )

    return False, ""


def _write_dissent(task_id: str, reason: str, instructions: str):
    """Write dissent to dissent_log.md and alert Commander via Telegram."""
    entry = (
        f"\n---\n"
        f"DISSENT | {_ts()} | task_id: {task_id}\n"
        f"REASON: {reason}\n"
        f"TASK INSTRUCTIONS (first 200 chars): {instructions[:200]}\n"
        f"STATUS: Claude is executing task but flagging this concern.\n"
        f"ACTION REQUIRED: Commander review.\n"
    )
    _safe_append(DISSENT, entry)

    alert = (
        f"⚠️ <b>CLAUDE DISSENT — {_ts()}</b>\n"
        f"Task ID: <code>{task_id}</code>\n"
        f"Concern: {reason[:200]}\n"
        f"<i>Claude is executing but flagged this. Review dissent_log.md.</i>"
    )
    _send_telegram(alert)
    print(f"[goose_tasker] DISSENT filed: {reason[:80]}", file=sys.stderr)


def _log_commander_review(task_id: str, task_type: str, instructions: str,
                           output_dest: str, dissented: bool):
    """Log every task to commander_review_log.md — full Commander visibility."""
    entry = (
        f"\n---\n"
        f"TASK_ID: {task_id} | {_ts()}\n"
        f"SUBMITTED_BY: GOOSE (on behalf of Commander)\n"
        f"TASK_TYPE: {task_type}\n"
        f"INSTRUCTIONS: {instructions[:300]}\n"
        f"OUTPUT_DEST: {output_dest}\n"
        f"DISSENT_FILED: {'YES — see dissent_log.md' if dissented else 'NO'}\n"
        f"STATUS: QUEUED → claude_inbox.md\n"
    )
    _safe_append(REVIEW_LOG, entry)


def _write_inbox(task_id: str, task_type: str, instructions: str,
                 context_files: list, output_dest: str,
                 priority: str, pii: bool, dissented: bool):
    """Write formatted task entry to claude_inbox.md."""
    context_str = ", ".join(context_files) if context_files else "none"
    dissent_note = (
        "\n⚠️ NOTE: Claude filed a dissent on this task. "
        "See dissent_log.md. Claude will execute and flag concern in output."
        if dissented else ""
    )
    entry = (
        f"\n---\n"
        f"## GOOSE TASK — ON BEHALF OF COMMANDER\n"
        f"task_id: {task_id}\n"
        f"submitted_by: GOOSE\n"
        f"authority: ON BEHALF OF COMMANDER\n"
        f"submitted_at: {_ts()}\n"
        f"task_type: {task_type}\n"
        f"priority: {priority}\n"
        f"pii: {str(pii).lower()}\n"
        f"context_files: [{context_str}]\n"
        f"instructions: {instructions}\n"
        f"output_destination: {output_dest}\n"
        f"deadline: ASAP{dissent_note}\n"
    )
    _safe_append(INBOX, entry)


def _log_routing(task_id: str, task_type: str):
    entry = (
        f"[{_ts()}] | {task_id} | GOOSE→Claude | {task_type} | "
        f"UNKNOWN | QUEUED | Goose tasker — written to claude_inbox.md\n"
    )
    _safe_append(ROUTING, entry)


def submit_task(
    task_type: str,
    instructions: str,
    output_dest: str = None,
    context_files: list = None,
    priority: str = "NORMAL",
    pii: bool = False,
) -> dict:
    """
    Main entry point. Called by Goose to task Claude.
    Returns result dict with task_id, dissented, and status.
    """
    # ── Validate task type ──
    if task_type not in PERMITTED_TYPES:
        msg = (
            f"Task type '{task_type}' is not permitted. "
            f"Permitted: {list(PERMITTED_TYPES.keys())}"
        )
        print(f"[goose_tasker] ERROR: {msg}", file=sys.stderr)
        return {"status": "ERROR", "message": msg}

    # ── Generate task ID ──
    task_id = f"GT-{_ts_id()}-{task_type[:4].upper()}"

    # ── Resolve output destination ──
    if not output_dest:
        output_dest = str(COLLAB / "claude_output.md")

    # ── Context files ──
    context_files = context_files or []

    # ── Dissent check ──
    dissented, dissent_reason = _check_dissent(task_type, instructions, pii)

    # ── Write dissent if triggered ──
    if dissented:
        _write_dissent(task_id, dissent_reason, instructions)

    # ── Write to claude_inbox.md ──
    _write_inbox(
        task_id, task_type, instructions,
        context_files, output_dest, priority, pii, dissented
    )

    # ── Log for Commander review (every task) ──
    _log_commander_review(task_id, task_type, instructions, output_dest, dissented)

    # ── Routing log ──
    _log_routing(task_id, task_type)

    status = "QUEUED_WITH_DISSENT" if dissented else "QUEUED"
    print(f"[goose_tasker] Task {task_id} → {status}")
    print(f"[goose_tasker] Claude inbox: {INBOX}")
    print(f"[goose_tasker] Commander review log: {REVIEW_LOG}")
    if dissented:
        print(f"[goose_tasker] Dissent log: {DISSENT}")
    print(f"[goose_tasker] Trigger Claude with: 'Read your inbox and execute'")

    return {
        "task_id": task_id,
        "status": status,
        "dissented": dissented,
        "dissent_reason": dissent_reason if dissented else None,
        "inbox": str(INBOX),
        "output_dest": output_dest,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Goose → Claude Consultant Tasker (On Behalf of Commander)"
    )
    parser.add_argument(
        "--task-type", required=True,
        choices=list(PERMITTED_TYPES.keys()),
        help=f"Task type. Options: {list(PERMITTED_TYPES.keys())}"
    )
    parser.add_argument("--instructions", required=True,
                        help="Plain language instructions for Claude")
    parser.add_argument("--output-dest", default=None,
                        help="Output file path (default: collaboration/claude_output.md)")
    parser.add_argument("--context-files", default="",
                        help="Comma-separated list of context file paths")
    parser.add_argument("--priority", default="NORMAL",
                        choices=["HIGH", "NORMAL", "LOW"],
                        help="Task priority")
    parser.add_argument("--pii", action="store_true",
                        help="Flag if task involves client PII")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing files")

    args = parser.parse_args()

    context_files = [f.strip() for f in args.context_files.split(",") if f.strip()]

    if args.dry_run:
        print("\n[DRY RUN] Task would be submitted with:")
        print(f"  task_type:     {args.task_type}")
        print(f"  instructions:  {args.instructions[:100]}...")
        print(f"  output_dest:   {args.output_dest or 'collaboration/claude_output.md'}")
        print(f"  context_files: {context_files}")
        print(f"  priority:      {args.priority}")
        print(f"  pii:           {args.pii}")
        dissented, reason = _check_dissent(args.task_type, args.instructions, args.pii)
        print(f"  dissent:       {'YES — ' + reason[:80] if dissented else 'NO'}")
        return

    result = submit_task(
        task_type=args.task_type,
        instructions=args.instructions,
        output_dest=args.output_dest,
        context_files=context_files,
        priority=args.priority,
        pii=args.pii,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] in ("QUEUED", "QUEUED_WITH_DISSENT") else 1)


if __name__ == "__main__":
    main()
