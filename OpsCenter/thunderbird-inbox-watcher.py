import json
import os
import subprocess
import sys
import time
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# __ Paths __
ROOT = Path(__file__).resolve().parent.parent
OPSCENTER = ROOT / "OpsCenter"
COLLAB = OPSCENTER / "collaboration"
CLAUDE_INBOX_FILE = COLLAB / "claude_inbox.md"
CLAUDE_OUTPUT_DIR = COLLAB # Claude writes to specified output_destination, default is CLAUDE_OUTPUT_DIR
ROUTING_LOG_FILE = COLLAB / "routing_log.md"
WATCHER_STATE_FILE = COLLAB / "watcher_state.json"

# __ Configuration __
POLLING_INTERVAL_SECONDS = 5  # Check inbox every 5 seconds
CLAUDE_CLI_PATH = "/home/john/.local/bin/claude" # Assuming Claude CLI is in .local/bin
MT = timezone(timedelta(hours=-6)) # Mountain Time

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

# __ Utility Functions __
def _log(msg: str):
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M:%S MT")
    line = f"[{ts}] [WATCHER] {msg}"
    print(line)
    # Could also log to a dedicated watcher.log file

def _send_telegram_notification(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER_ID:
        _log("WARN: Telegram credentials missing. Cannot send notification.")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception as e:
        _log(f"ERROR: Failed to send Telegram notification: {e}")

def _safe_read_file(path: Path, default_content: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default_content
    except Exception as e:
        _log(f"ERROR: Failed to read {path}: {e}")
        return default_content

def _safe_write_file(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        _log(f"ERROR: Failed to write {path}: {e}")
        return False

def _safe_append_file(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        _log(f"ERROR: Failed to append to {path}: {e}")
        return False

def _load_watcher_state() -> dict:
    try:
        state_content = _safe_read_file(WATCHER_STATE_FILE, "{}")
        return json.loads(state_content)
    except json.JSONDecodeError:
        _log("WARN: watcher_state.json corrupted, resetting state.")
        return {}

def _save_watcher_state(state: dict):
    _safe_write_file(WATCHER_STATE_FILE, json.dumps(state, indent=2))

def _parse_last_task(inbox_content: str) -> dict | None:
    """Parses the last task entry from the Markdown-formatted claude_inbox.md."""
    # Split content into task blocks
    task_blocks = re.split(r'\n---\n## GOOSE TASK', '\n---\n## GOOSE TASK' + inbox_content.split('## GOOSE TASK', 1)[-1].strip(), flags=re.DOTALL)
    
    if len(task_blocks) < 2: # First split yields empty string, then first task block
        return None

    # Get the last task block
    last_block = task_blocks[-1].strip()

    # Extract fields using regex or simple string splitting
    task = {}
    task_id_match = re.search(r"task_id:\s*(.+)", last_block)
    if task_id_match:
        task["task_id"] = task_id_match.group(1).strip()
    
    instructions_match = re.search(r"instructions:\s*(.+?)(?=\noutput_destination:|\ndeadline:|\npii:)", last_block, re.DOTALL)
    if instructions_match:
        task["instructions"] = instructions_match.group(1).strip()
    
    context_files_match = re.search(r"context_files:\s*\[(.+?)\]", last_block)
    if context_files_match:
        task["context_files"] = [f.strip() for f in context_files_match.group(1).split(',') if f.strip()]
    else:
        task["context_files"] = []
        
    output_dest_match = re.search(r"output_destination:\s*(.+)", last_block)
    if output_dest_match:
        task["output_destination"] = output_dest_match.group(1).strip()

    return task if "task_id" in task else None

def _log_routing(task_id: str, agent: str, status: str, details: str = ""):
    ts = datetime.now(MT).strftime("%Y-%m-%dT%H:%M:%S MT")
    entry = f"[{ts}] | {task_id} | WATCHER→{agent} | claude_task | 0 | {status} | {details}\n"
    _safe_append_file(ROUTING_LOG_FILE, entry)

def run_watcher():
    _log("Claude Inbox Watcher started.")
    _log(f"Monitoring: {CLAUDE_INBOX_FILE}")
    _log(f"Claude CLI Path: {CLAUDE_CLI_PATH}")

    watcher_state = _load_watcher_state()
    last_processed_task_id = watcher_state.get("last_processed_task_id")
    _log(f"Last processed task ID: {last_processed_task_id}")

    while True:
        try:
            inbox_content = _safe_read_file(CLAUDE_INBOX_FILE)
            current_last_task = _parse_last_task(inbox_content)

            if current_last_task and current_last_task["task_id"] != last_processed_task_id:
                _log(f"New task detected: {current_last_task['task_id']}")
                
                # Construct Claude CLI command
                # The prompt instructs Claude to read the task from the inbox file.
                claude_prompt = (
                    f"Please execute the task with ID {current_last_task['task_id']} "
                    f"from the file {CLAUDE_INBOX_FILE}, including any context files "
                    f"listed in that task entry. Write your comprehensive output to "
                    f"the file specified as 'output_destination' in that task entry.\n\n"
                    f"Instructions: {current_last_task['instructions']}"
                )
                
                claude_command_args = [
                    CLAUDE_CLI_PATH,
                    "--ask", # Use --ask for full conversation-like interaction, which then writes. Or --print if it's purely one-shot
                    claude_prompt,
                    "--output", str(current_last_task["output_destination"]) # Direct Claude to write to output file
                ]

                # Ensure the output directory exists
                Path(current_last_task["output_destination"]).parent.mkdir(parents=True, exist_ok=True)

                _log(f"Attempting Claude CLI version check for task {current_last_task['task_id']}...")
                version_check = subprocess.run(
                    [CLAUDE_CLI_PATH, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if version_check.returncode != 0:
                    _log(f"ERROR: Claude CLI version check failed (Exit Code: {version_check.returncode}). Stderr: {version_check.stderr.strip()[:150]}")
                    _send_telegram_notification(
                        f"❌ <b>Claude CLI Setup Error:</b> Failed version check for task {current_last_task['task_id']}. Stderr: {version_check.stderr.strip()[:100]}")
                    _log_routing(current_last_task['task_id'], "Claude", "FAILED", "CLI not executable or failed version check")
                    last_processed_task_id = current_last_task['task_id']
                    _save_watcher_state({"last_processed_task_id": last_processed_task_id})
                    continue # Skip full execution
                _log(f"Claude CLI version check successful: {version_check.stdout.strip()[:100]}")

                _log(f"Executing Claude CLI for task {current_last_task['task_id']}...")
                _log(f"Command: {' '.join(claude_command_args)}")

                                _log(f"Claude CLI Environment: {os.environ}") # New logging
                claude_process = subprocess.run(
                    claude_command_args,
                    capture_output=True,
                    text=True,
                    timeout=300 # 5 minutes timeout for Claude execution
                )

                if claude_process.returncode == 0:
                    _log(f"Claude task {current_last_task['task_id']} completed successfully.")
                    _send_telegram_notification(
                        f"✅ <b>Claude Task Complete:</b> <code>{current_last_task['task_id']}</code><br>"
                        f"Output: <code>{current_last_task['output_destination']}</code>"
                    )
                    _log_routing(current_last_task['task_id'], "Claude", "EXECUTED", claude_process.stdout.strip()[:100])
                    last_processed_task_id = current_last_task["task_id"]
                    _save_watcher_state({"last_processed_task_id": last_processed_task_id})
                else:
                    _log(f"ERROR: Claude task {current_last_task['task_id']} failed (Exit Code: {claude_process.returncode}).")
                    _log(f"Stderr: {claude_process.stderr}")
                    _send_telegram_notification(
                        f"❌ <b>Claude Task Failed:</b> <code>{current_last_task['task_id']}</code><br>"
                        f"Reason: Claude CLI error. Check logs." # Consider including some stderr here
                    )
                    _log_routing(current_last_task['task_id'], "Claude", "FAILED", claude_process.stderr.strip()[:100])

            elif not current_last_task and last_processed_task_id: # Handles if inbox is explicitly cleared
                _log("Inbox appears empty or reset. Resetting last_processed_task_id.")
                last_processed_task_id = None
                _save_watcher_state({"last_processed_task_id": last_processed_task_id})

        except Exception as e:
            _log(f"CRITICAL WATCHER ERROR: {e}")
            _send_telegram_notification(f"⚠️ <b>Watcher Error:</b> {e}<br>Check OpsCenter logs.")
        
        time.sleep(POLLING_INTERVAL_SECONDS)

if __name__ == "__main__":
    _log("Starting Claude Inbox Watcher process...")
    # Load env for telegram token
    from dotenv import load_dotenv
    load_dotenv(str(ROOT / ".env"))
    load_dotenv(str(ROOT / ".env.telegram"))
    
    # Ensure subprocess can find claude CLI
    # Prioritize user's local bin and common Claude install paths
    original_path = os.environ.get("PATH", "")
    new_path_elements = [
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / ".local" / "share" / "claude" / "versions" / "current" / "bin"),
        original_path
    ]
    os.environ["PATH"] = ":".join([p for p in new_path_elements if p])

    # Unset Anthropic API key to force Claude CLI to use OAuth (MAX subscription)
    if "ANTHROPIC_API_KEY" in os.environ: # Check if it exists before trying to delete
        del os.environ["ANTHROPIC_API_KEY"]
        _log("ANTHROPIC_API_KEY unset to force Claude CLI OAuth (MAX subscription).")
    
    import requests # Imported here for telegram notification outside main loop

    try:
        run_watcher()
    except KeyboardInterrupt:
        _log("Claude Inbox Watcher stopped by user.")
    except Exception as e:
        _log(f"Unhandled exception in watcher: {e}")
        sys.exit(1)