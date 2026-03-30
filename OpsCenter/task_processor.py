"""
OpsCenter Task Processor — Hale-Loop Consumer
==============================================
Pops tasks from the JSON queue, classifies them, routes to the
correct engine, and sends results back via Telegram.

Division of Labor:
    Gemini 3.1 Pro   → Hale's primary brain. All operational tasks, summaries, routing.
    Gemini Flash ($)  → Research synthesis, bulk text, workspace tasks
    Claude MAX ($0)   → Client-facing emails, proposals, voice-matched copy, complex reasoning
    DeepSeek (cheap)  → Data extraction, analytics (PII-fenced)
    Local Python      → Queue mechanics, deadline checks, format checks (no LLM)

Claude MAX tokens are SCARCE (5-hour window). Never burn them on:
    - Polling/heartbeats
    - Classification/routing decisions
    - Summarization of known data
    - Queue processing overhead

Author: Col Victoria "Iron Vic" Hale (COS)
"""

import json
import logging
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent dir so we can import thunderbird modules
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Load env BEFORE importing model router (it reads keys at import time)
from dotenv import load_dotenv
load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

from thunderbird_model_router import (
    _call_groq,
    _call_gemini,
    classify_task,
    TaskType,
)
from thunderbird_innovation_scanner import run_daily_scan, run_weekly_scan
from thunderbird_morning_briefing import run_briefing as run_morning_briefing_pipeline
from thunderbird_overwatch import run_sentinel_sweep, _check_dossier_currency, _check_commission_math, CheckStatus, CheckResult


logger = logging.getLogger("opscenter.processor")

# ── Hale's Brain: Gemini 3.1 Pro Preview ──
HALE_MODEL = "gemini-3.1-pro-preview"
HALE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{HALE_MODEL}:generateContent"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def _call_hale(system_prompt: str, query: str,
               max_tokens: int = 800, temperature: float = 0.5) -> str:
    """Call Gemini 3.1 Pro Preview — Hale's primary engine.

    Truthful, capable, free-tier eligible. Falls back to _call_gemini (Flash)
    if the key is missing or the call fails.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — falling back to Gemini Flash")
        return _call_gemini(system_prompt, query, max_tokens=max_tokens,
                            temperature=temperature)

    url = f"{HALE_URL}?key={GEMINI_API_KEY}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": query}]}
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=60,
                             headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.warning("Gemini 3.1 Pro failed (%s), falling back to Flash", e)
        return _call_gemini(system_prompt, query, max_tokens=max_tokens,
                            temperature=temperature)


# ── Paths ──
ROOT = Path(__file__).resolve().parent.parent
OPSCENTER = ROOT / "OpsCenter"
QUEUE_FILE = OPSCENTER / "01_TASK_QUEUE.json"
COMMAND_LOG = OPSCENTER / "00_COMMAND_LOG.md"
PROCESS_LOG = OPSCENTER / "process.log"

# ── Telegram ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

# ── Mountain Time ──
MT = timezone(timedelta(hours=-6))  # MDT


def _log(msg: str):
    """Append timestamped line to process log and stdout."""
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M:%S MT")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(PROCESS_LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _send_telegram(chat_id: str, text: str, parse_mode: str = "Markdown"):
    """Send a message back to Commander via Telegram C2 bot."""
    if not TELEGRAM_BOT_TOKEN:
        _log("WARN: No TELEGRAM_C2_BOT_TOKEN — cannot send reply")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram Markdown can be finicky — fall back to plain if it fails
    for mode in (parse_mode, None):
        try:
            payload = {
                "chat_id": chat_id,
                "text": text[:4096],  # Telegram limit
            }
            if mode:
                payload["parse_mode"] = mode
            resp = requests.post(url, json=payload, timeout=15)
            if resp.ok:
                return True
            # If Markdown failed, retry without parse_mode
            if mode and resp.status_code == 400:
                continue
            _log(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            _log(f"Telegram send error: {e}")
            if mode:
                continue
            return False
    return False


def _log_command(task_id: str, task_type: str, persona: str, result_summary: str):
    """Append to the command log markdown."""
    ts = datetime.now(MT).strftime("%a %b %d %I:%M:%S %p MT %Y")
    entry = f"- **[{ts}]** HALE routed `{task_type}` ({task_id}) → **{persona}** — {result_summary}\n"
    try:
        with open(COMMAND_LOG, "a") as f:
            f.write(entry)
    except OSError:
        pass


# ============================================================================
# TASK HANDLERS — Each returns a string response for the Commander
# ============================================================================

def _handle_commander_message(task: dict) -> str:
    """Process a free-text message from the Commander via Telegram.

    Division of labor:
        1. Groq classifies the message (free, fast)
        2. Route to appropriate engine based on classification
        3. Only use Claude MAX for client-facing output
    """
    content = task.get("content", "").strip()
    chat_id = task.get("chat_id", TELEGRAM_COMMANDER_ID)

    if not content:
        return "Empty message received. Standing by."

    # Step 1: Classify with local keyword matcher (zero API cost)
    task_type = classify_task(content)
    _log(f"Classified message as: {task_type.value}")

    # Step 2: Route based on classification
    # GROQ handles: operational, classification, summarization, research
    # GEMINI handles: morning_brief, data_extraction
    # CLAUDE MAX handles: client_facing, creative, voice_profile, crisis, strategic
    GROQ_TASKS = {
        TaskType.OPERATIONAL, TaskType.CLASSIFICATION,
        TaskType.SUMMARIZATION, TaskType.RESEARCH,
        TaskType.DATA_EXTRACTION, TaskType.EXTRACTION,
    }
    GEMINI_TASKS = {
        TaskType.MORNING_BRIEF,
    }
    # Everything else → Claude MAX (the money shot)

    system_prompt = (
        "You are Col Victoria Hale, COS of Dreams2Memories Travel. "
        "Respond to the Commander's message concisely and directly. "
        "If it's a task, confirm receipt and provide the result. "
        "If it's a question, answer it. Keep responses under 500 words."
    )

    try:
        if task_type in GROQ_TASKS:
            engine = "Gemini 3.1 Pro"
            response = _call_hale(system_prompt, content,
                                  max_tokens=800, temperature=0.5)
        elif task_type in GEMINI_TASKS:
            engine = "Gemini Flash"
            response = _call_gemini(system_prompt, content,
                                   max_tokens=800, temperature=0.5)
        else:
            # Client-facing, creative, strategic, crisis, code, voice → Claude MAX
            # But we DON'T call Claude directly from the daemon — that burns MAX tokens.
            # Instead, we queue it for the next Claude Code session and notify Commander.
            engine = "QUEUED for Claude MAX"
            response = (
                f"*Task classified as: {task_type.value}*\n\n"
                f"This requires Claude MAX (voice-matched output). "
                f"Queued for next Claude Code session.\n\n"
                f"Message: _{content[:200]}_"
            )
            # Write to a separate high-priority queue for Claude Code to pick up
            _queue_for_claude_max(task)
            _log(f"Queued for Claude MAX: {task_type.value}")

    except Exception as e:
        engine = "ERROR"
        response = f"Engine failure: {e}\nOriginal message: {content[:200]}"
        _log(f"Handler error: {e}")

    _log(f"Processed via {engine}: {content[:80]}...")
    return response


def _queue_for_claude_max(task: dict):
    """Write high-value tasks to a separate queue for Claude Code to process."""
    max_queue = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
    try:
        existing = json.loads(max_queue.read_text()) if max_queue.exists() else []
    except (json.JSONDecodeError, OSError):
        existing = []

    task["queued_at"] = datetime.now(MT).isoformat()
    task["requires"] = "claude_max"
    existing.append(task)

    max_queue.write_text(json.dumps(existing, indent=2))


def _handle_send_draft(task: dict) -> str:
    """Handle draft approval — Commander pressed Approve in Telegram."""
    draft_id = task.get("draft_id", "unknown")
    chat_id = task.get("chat_id", TELEGRAM_COMMANDER_ID)

    # This needs MCP gmail tools — queue for Claude Code
    _queue_for_claude_max({
        "task_type": "send_approved_draft",
        "draft_id": draft_id,
        "chat_id": chat_id,
        "queued_at": datetime.now(MT).isoformat(),
    })

    return f"Draft `{draft_id}` approved. Queued for send via Claude Code MCP."


def _handle_innovation_scan(task: dict) -> str:
    """Run innovation scan using thunderbird_innovation_scanner.py."""
    scan_type = task.get("scan_type", "daily")
    try:
        if scan_type == "weekly":
            result = run_weekly_scan()
        else:
            result = run_daily_scan()

        response_lines = [f"*A12 Innovation Scan Complete ({scan_type.title()})*", ""]
        if result.findings:
            response_lines.append(f"**Top {len(result.top_findings)} Findings:**")
            for i, f in enumerate(result.top_findings[:5], 1):
                response_lines.append(f"{i}. [{f.source}] {f.title} (Score: {f.score})")
                response_lines.append(f"   URL: {f.url}")
            if len(result.findings) > 5:
                response_lines.append(f"  ...and {len(result.findings) - 5} more. See digest for full details.")
        else:
            response_lines.append("No significant innovation findings today.")

        if result.errors:
            response_lines.append("\n**Errors during scan:**")
            for error_msg in result.errors:
                response_lines.append(f"- {error_msg}")

        response_lines.append(f"\nFull digest: `~/Thunderbird/intel/daily_innovation_digest.md`")
        return "\n".join(response_lines)
    except Exception as e:
        return f"Innovation scan failed: {e}"


def _handle_morning_briefing(task: dict) -> str:
    """Generate and send the morning briefing using the full pipeline."""
    preview = task.get("preview", False)
    weekly = task.get("weekly", False)
    try:
        result_message = run_morning_briefing_pipeline(preview=preview, weekly=weekly)
        status = "Preview saved" if preview else "Briefing sent"
        return f"*{status}*: {result_message}"
    except Exception as e:
        logger.error(f"Morning briefing pipeline failed: {e}", exc_info=True)
        return f"Morning briefing generation failed: {e}"


def _handle_fpd_alert(task: dict) -> str:
    """Process FPD (Final Payment Deadline) alert — local Python, no LLM needed."""
    # Import overwatch checks directly
    try:
        from thunderbird_overwatch import _check_deadline_tracking
        result = _check_deadline_tracking()
        return f"*FPD Alert*\n\nStatus: {result.status.value}\n{result.message}"
    except Exception as e:
        return f"FPD check failed: {e}"


def _handle_sentinel_sweep(task: dict) -> str:
    """Run a full Sentinel sweep and report results."""
    try:
        # Setting use_llm=True for Sentinel to synthesize with Groq, as per Overwatch design.
        # The OpsCenter README says Groq handles operational summaries.
        report = run_sentinel_sweep(use_llm=True)
        response_lines = [
            f"*Sentinel Sweep Complete* (ID: {report.sweep_id})",
            f"Red Flags: {report.red_flags}",
            f"Yellow Flags: {report.yellow_flags}",
            f"Green Checks: {report.green_count}",
            f"Duration: {report.duration_seconds:.2f}s",
            "\n**Detailed Checks:**"
        ]
        for check in report.checks:
            icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(check.status.value, "❓")
            response_lines.append(f"{icon} {check.check_name.replace("_", " ").title()}: {check.message}")
        
        if report.escalated_to_judge:
            response_lines.append("\n*Escalated to The Judge for deeper analysis.*")

        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Sentinel sweep failed: {e}", exc_info=True)
        return f"Sentinel sweep failed: {e}"


def _handle_dossier_check(task: dict) -> str:
    """Run a dossier currency check and report results."""
    try:
        result = _check_dossier_currency()
        icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(result.status.value, "❓")
        response_lines = [
            f"*Dossier Currency Check Complete*",
            f"{icon} Status: {result.status.value.upper()}",
            f"Message: {result.message}"
        ]
        if result.details:
            response_lines.append("\n**Details:**")
            for key, value in result.details.items():
                response_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value, indent=2) if isinstance(value, (list, dict)) else value}")
        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Dossier currency check failed: {e}", exc_info=True)
        return f"Dossier currency check failed: {e}"


def _handle_commission_audit(task: dict) -> str:
    """Run a commission math check and report results."""
    try:
        result = _check_commission_math()
        icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(result.status.value, "❓")
        response_lines = [
            f"*Commission Math Audit Complete*",
            f"{icon} Status: {result.status.value.upper()}",
            f"Message: {result.message}"
        ]
        if result.details:
            response_lines.append("\n**Details:**")
            for key, value in result.details.items():
                response_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value, indent=2) if isinstance(value, (list, dict)) else value}")
        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Commission math audit failed: {e}", exc_info=True)
        return f"Commission math audit failed: {e}"


def _process_claude_max_queue_tasks() -> str:
    """Process tasks from the 03_CLAUDE_MAX_QUEUE.json."""
    max_queue_file = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
    if not max_queue_file.exists():
        return "Claude MAX queue is empty or does not exist."

    try:
        queue = json.loads(max_queue_file.read_text())
    except (json.JSONDecodeError, OSError):
        return "Failed to read Claude MAX queue. Invalid JSON or file error."

    if not queue:
        return "Claude MAX queue is empty."

    processed_count = 0
    results = []

    # Process one task at a time to prevent blocking the daemon
    if queue:
        task = queue.pop(0)
        max_queue_file.write_text(json.dumps(queue, indent=2)) # Write back updated queue

        task_type = task.get("task_type", "unknown_claude_max_task")
        chat_id = str(task.get("chat_id", TELEGRAM_COMMANDER_ID))
        task_id = task.get("task_id", "UNKNOWN_MAX")

        _log(f"Processing Claude MAX task {task_id} (type: {task_type})")

        # Dispatch to specific Claude MAX sub-handlers here
        # For now, a placeholder. We will implement these in later steps.
        if task_type == "client_email_draft":
            # This is where the actual drafting logic will go
            results.append(f"Client email draft for task {task_id} initiated (placeholder).")
        elif task_type == "send_approved_draft":
            # This is where the draft sending logic will go
            results.append(f"Approved draft send for {task.get('draft_id')} initiated (placeholder).")
        else:
            results.append(f"Unsupported Claude MAX task type '{task_type}' for task {task_id}. Task content: {task.get('content', '')[:100]}...")

        processed_count += 1
    
    return f"Processed {processed_count} Claude MAX task(s). Results: {' | '.join(results)}"

# New handler for processing the Claude MAX queue
def _handle_process_claude_max_queue(task: dict) -> str:
    """Handler to trigger processing of the Claude MAX queue."""
    return _process_claude_max_queue_tasks()


# ============================================================================
# HANDLER DISPATCH TABLE
# ============================================================================

HANDLERS = {
    "commander_message": _handle_commander_message,
    "send_draft": _handle_send_draft,
    "innovation_scan": _handle_innovation_scan,
    "morning_briefing": _handle_morning_briefing,
    "fpd_alert": _handle_fpd_alert,
    "sentinel_sweep": _handle_sentinel_sweep,
    "dossier_check": _handle_dossier_check,
    "commission_audit": _handle_commission_audit,
    "process_claude_max_queue": _handle_process_claude_max_queue,
}


# ============================================================================
# QUEUE CONSUMER — Pop and process
# ============================================================================

def pop_task() -> dict | None:
    """Atomically pop the first task from the queue. Returns None if empty."""
    if not QUEUE_FILE.exists():
        return None

    try:
        queue = json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not queue:
        return None

    task = queue.pop(0)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    return task


def process_one() -> bool:
    """Pop one task, process it, send result back. Returns True if a task was processed."""
    task = pop_task()
    if not task:
        return False

    task_id = task.get("task_id", "UNKNOWN")
    task_type = task.get("task_type", "generic")
    chat_id = str(task.get("chat_id", TELEGRAM_COMMANDER_ID))

    _log(f"Processing task {task_id} (type: {task_type})")

    # Find handler
    handler = HANDLERS.get(task_type)
    if handler:
        try:
            response = handler(task)
        except Exception as e:
            response = f"Handler crashed for {task_type}: {e}"
            _log(f"CRASH in {task_type}: {e}")
    else:
        response = f"Unknown task type: `{task_type}`\nRaw: {json.dumps(task)[:500]}"
        _log(f"No handler for task type: {task_type}")

    # Send result back to Commander via Telegram
    _send_telegram(chat_id, response)

    # Log to command log
    summary = response[:100].replace("\n", " ")
    _log_command(task_id, task_type, "COS", summary)

    _log(f"Task {task_id} complete — response sent to Telegram")
    return True


def run_daemon(poll_interval: int = 5):
    """Run the Hale-Loop: poll queue, process tasks, repeat forever."""
    _log("Hale-Loop Task Processor started (Python)")
    _log(f"Queue: {QUEUE_FILE}")
    _log(f"Poll interval: {poll_interval}s")
    _log(f"Telegram bot: {'configured' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    _log(f"Commander ID: {TELEGRAM_COMMANDER_ID or 'MISSING'}")

    while True:
        try:
            processed = process_one()
            if processed:
                _log("Task processed. Applying 10-second rate limit before next task.")
                time.sleep(10)  # Apply 10-second rate limit between tasks
                continue
        except Exception as e:
            _log(f"Daemon loop error: {e}")

        time.sleep(poll_interval)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="OpsCenter Task Processor")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as daemon (poll queue forever)")
    parser.add_argument("--once", action="store_true",
                        help="Process one task and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show queue status")

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.once:
        if process_one():
            print("Task processed.")
        else:
            print("Queue empty.")
    elif args.status:
        try:
            queue = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
        except (json.JSONDecodeError, OSError):
            queue = []
        max_q = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
        try:
            max_queue = json.loads(max_q.read_text()) if max_q.exists() else []
        except (json.JSONDecodeError, OSError):
            max_queue = []
        print(f"Task Queue:       {len(queue)} pending")
        print(f"Claude MAX Queue: {len(max_queue)} pending")
        print(f"Telegram Bot:     {'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
        print(f"Commander ID:     {TELEGRAM_COMMANDER_ID or 'MISSING'}")
    else:
        parser.print_help()
