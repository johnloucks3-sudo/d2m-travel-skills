"""
dispatcher.py — Task Dispatcher for Slot Router
Dreams2Memories Travel, LLC

Spawns tasks via:
  ask      → opencode_sonnet_inline.py (Sonnet)
  ask-opus → opencode_sonnet_inline.py --model opus
  telegram → Telegram API sendMessage to Commander
  script   → direct subprocess execution

Manages TaskRecord lifecycle (in-memory dict + JSON persistence).
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path('/home/john/Thunderbird')
OUTPUT_DIR = BASE_DIR / 'output'
TASK_STORE = Path(__file__).parent / 'tasks.json'
LOG_DIR = Path(__file__).parent / 'logs'
SONNET_SCRIPT = BASE_DIR / 'OpsCenter' / 'opencode_sonnet_inline.py'

MODEL_IDS: dict[str, str] = {
    'sonnet': 'claude-sonnet-4-6',
    'opus':   'claude-opus-4-7',
    'haiku':  'claude-haiku-4-5-20251001',
}

TELEGRAM_BOT_TOKEN    = os.environ.get('TELEGRAM_C2_BOT_TOKEN', '')
TELEGRAM_COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID', '7554895206')


# ─── Task store I/O ───────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_task_id() -> str:
    return 'slot_' + uuid.uuid4().hex[:8]


def _load_tasks() -> dict:
    if TASK_STORE.exists():
        try:
            return json.loads(TASK_STORE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_tasks(tasks: dict) -> None:
    TASK_STORE.parent.mkdir(parents=True, exist_ok=True)
    TASK_STORE.write_text(json.dumps(tasks, indent=2))


def _save_task(record: dict) -> None:
    tasks = _load_tasks()
    tasks[record['id']] = record
    _save_tasks(tasks)


def _load_task(task_id: str) -> dict | None:
    return _load_tasks().get(task_id)


# ─── TaskRecord factory ───────────────────────────────────────────────────────

def make_task_record(
    task_desc: str,
    classified_type: str,
    complexity: str,
    route: dict,
    task_id: str | None = None,
) -> dict:
    """
    Build a TaskRecord dict without dispatching it.
    Schema matches the spec exactly.
    """
    tid = task_id or _make_task_id()
    outfile = str(OUTPUT_DIR / f'{tid}.md')
    return {
        'id': tid,
        'task': task_desc,
        'classified_type': classified_type,
        'complexity': complexity,
        'routed_to': dict(route),
        'pid': None,
        'output_file': outfile,
        'started_at': _now_iso(),
        'status': 'pending',
        'attempts': 0,
        'error': None,
    }


# ─── Dispatch modes ───────────────────────────────────────────────────────────

def _dispatch_ask(record: dict, route: dict) -> dict:
    """
    Dispatch via opencode_sonnet_inline.py.
    Model is determined by route['model'] (sonnet or opus).
    Task prompt includes a WRITE instruction so the model outputs to outfile.
    """
    model_key = route.get('model', 'sonnet')
    model_id  = MODEL_IDS.get(model_key, MODEL_IDS['sonnet'])
    outfile   = record['output_file']
    task_desc = record['task']

    prompt = (
        f"{task_desc}\n\n"
        f"WRITE your complete response to: {outfile}\n"
        f"Create that file with the full output of your work."
    )

    cmd = [sys.executable, str(SONNET_SCRIPT), prompt, '--model', model_id]

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / f"{record['id']}.log"

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=open(str(log_file), 'w'),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(BASE_DIR),
        )
        record['pid'] = proc.pid
        record['status'] = 'running'
        record['attempts'] = record.get('attempts', 0) + 1
    except Exception as e:
        record['status'] = 'failed'
        record['error'] = str(e)

    return record


def _dispatch_telegram(record: dict) -> dict:
    """
    Send a decide-type task to Commander via Telegram for judgment.
    Uses TELEGRAM_C2_BOT_TOKEN + TELEGRAM_COMMANDER_ID from env.
    """
    import urllib.request
    import urllib.parse

    task_id   = record['id']
    task_desc = record['task']
    msg = (
        f"\U0001f985 *SLOT ROUTER — COMMANDER DECISION REQUIRED*\n\n"
        f"Task ID: `{task_id}`\n"
        f"Type: `{record['classified_type']}`\n\n"
        f"*Task:* {task_desc}\n\n"
        f"This task requires your judgment. Please advise."
    )

    token = TELEGRAM_BOT_TOKEN
    if not token:
        record['status'] = 'failed'
        record['error'] = 'TELEGRAM_C2_BOT_TOKEN not set in environment'
        return record

    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id':    TELEGRAM_COMMANDER_ID,
            'text':       msg,
            'parse_mode': 'Markdown',
        }).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get('ok'):
            record['status'] = 'escalated'
        else:
            record['status'] = 'failed'
            record['error']  = f"Telegram API: {result}"
    except Exception as e:
        record['status'] = 'failed'
        record['error']  = str(e)

    return record


def _dispatch_script(record: dict) -> dict:
    """
    Direct script execution for monitor-type tasks.
    task_desc is treated as a shell command.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / f"{record['id']}.log"

    # SECURITY (MISSION-258 / vuln-fix 2026-06-24): record['task'] is executed under
    # shell=True BY DESIGN — monitor tasks require shell pipes/redirects. Trust boundary:
    # task strings MUST originate from wing-internal callers (route_task), never from
    # external input. Defense-in-depth: block command injection metacharacters.
    _task = record.get('task')
    if not isinstance(_task, str) or '\x00' in _task:
        record['status'] = 'failed'
        record['error'] = 'invalid task payload (non-str or NUL byte) — refused'
        return record
    # Reject shell injection patterns (command substitution, chained exec)
    import re as _re
    _INJECTION = _re.compile(r'(\$\(|`|;\s*\S|&&\s*\S|\|\|\s*\S)', _re.DOTALL)
    if _INJECTION.search(_task):
        record['status'] = 'failed'
        record['error'] = 'task rejected: shell injection pattern detected'
        return record

    try:
        proc = subprocess.Popen(
            _task,
            shell=True,
            stdout=open(str(log_file), 'w'),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(BASE_DIR),
        )
        record['pid'] = proc.pid
        record['status'] = 'running'
        record['attempts'] = record.get('attempts', 0) + 1
    except Exception as e:
        record['status'] = 'failed'
        record['error']  = str(e)

    return record


# ─── Main dispatch entry point ────────────────────────────────────────────────

def dispatch(record: dict, route: dict | None = None) -> dict:
    """
    Dispatch a TaskRecord based on its route.dispatch mode.
    Updates and persists the record before returning.
    """
    if route is None:
        route = record.get('routed_to', {})

    dispatch_mode = route.get('dispatch', 'ask')

    if dispatch_mode in ('ask', 'ask-opus'):
        record = _dispatch_ask(record, route)
    elif dispatch_mode == 'telegram':
        record = _dispatch_telegram(record)
    elif dispatch_mode == 'script':
        record = _dispatch_script(record)
    else:
        record['status'] = 'failed'
        record['error']  = f'Unknown dispatch mode: {dispatch_mode}'

    _save_task(record)
    return record


# ─── Utilities ────────────────────────────────────────────────────────────────

def send_telegram_escalation(task_id: str, message: str) -> bool:
    """Send an escalation alert to Commander via Telegram. Returns True on success."""
    import urllib.request
    import urllib.parse

    token = TELEGRAM_BOT_TOKEN
    if not token:
        return False

    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id':    TELEGRAM_COMMANDER_ID,
            'text':       message,
            'parse_mode': 'Markdown',
        }).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        return result.get('ok', False)
    except Exception:
        return False


def cancel_task(task_id: str) -> dict | None:
    """Kill a running task PID, clean up output file, mark cancelled."""
    tasks = _load_tasks()
    record = tasks.get(task_id)
    if not record:
        return None

    pid = record.get('pid')
    if pid and record.get('status') == 'running':
        for sig in (15, 9):  # SIGTERM then SIGKILL
            try:
                os.kill(pid, sig)
                time.sleep(0.3)
            except ProcessLookupError:
                break

        outfile = Path(record.get('output_file', ''))
        if outfile.exists():
            try:
                outfile.unlink()
            except OSError:
                pass

    record['status'] = 'cancelled'
    tasks[task_id] = record
    _save_tasks(tasks)
    return record


if __name__ == '__main__':
    from routing_table import DEFAULT_ROUTE
    record = make_task_record(
        task_desc='Research Bergen weather July 2027',
        classified_type='research.destination',
        complexity='simple',
        route=DEFAULT_ROUTE,
    )
    print(f"TaskRecord: {record['id']}")
    print(json.dumps(record, indent=2))
