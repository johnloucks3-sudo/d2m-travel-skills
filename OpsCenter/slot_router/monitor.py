"""
monitor.py — Execution Monitor for Slot Router
Dreams2Memories Travel, LLC

Watches running tasks and handles:
  success      — output file exists + PID dead
  failure      — PID dead, no output → retry
  double_fail  — retry exhausted → upgrade model (sonnet→opus)
  opus_failure — notify Hale via Telegram
  timeout      — notify Commander via Telegram

Polls every POLL_INTERVAL seconds.
Logs all outcomes to slot_router.log and outcomes.jsonl.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

POLL_INTERVAL = 10          # seconds between PID/output checks
LOG_DIR = Path(__file__).parent / 'logs'
LOG_FILE = Path(__file__).parent / 'slot_router.log'
OUTCOMES_FILE = Path(__file__).parent / 'outcomes.jsonl'

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MONITOR] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE), mode='a'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('slot_router.monitor')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _output_valid(output_file: str) -> bool:
    p = Path(output_file)
    return p.exists() and p.stat().st_size > 0


def _elapsed_seconds(started_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - start).total_seconds()
    except Exception:
        return 0.0


def _log_outcome(record: dict, outcome: str) -> None:
    entry = {
        'ts':         _now_iso(),
        'id':         record.get('id'),
        'outcome':    outcome,
        'type':       record.get('classified_type', ''),
        'complexity': record.get('complexity', ''),
        'attempts':   record.get('attempts', 0),
        'agent':      record.get('routed_to', {}).get('agent', ''),
        'model':      record.get('routed_to', {}).get('model', ''),
        'task_snip':  record.get('task', '')[:80],
    }
    logger.info(f"OUTCOME | {json.dumps(entry)}")
    with open(str(OUTCOMES_FILE), 'a') as f:
        f.write(json.dumps(entry) + '\n')


# ─── Single-task monitor (blocking) ──────────────────────────────────────────

def monitor_task(record: dict, timeout: int = 600) -> dict:
    """
    Block until a single task completes, fails, or times out.
    Handles all four escalation levels.
    Returns final updated record.
    """
    # Deferred imports to avoid circular at module load
    from dispatcher import _save_task, send_telegram_escalation, dispatch
    from routing_table import upgrade_route

    task_id    = record['id']
    outfile    = record.get('output_file', '')
    started_at = record.get('started_at', _now_iso())

    logger.info(
        f"Monitoring {task_id} | PID={record.get('pid')} | "
        f"timeout={timeout}s | complexity={record.get('complexity')}"
    )

    while True:
        elapsed   = _elapsed_seconds(started_at)
        pid       = record.get('pid')
        pid_alive = _pid_alive(pid)
        output_ok = _output_valid(outfile)
        attempts  = record.get('attempts', 1)

        # ── Success ──────────────────────────────────────────────────────────
        if output_ok and not pid_alive:
            record['status']       = 'success'
            record['completed_at'] = _now_iso()
            logger.info(f"{task_id} SUCCESS — {outfile}")
            _save_task(record)
            _log_outcome(record, 'success')
            return record

        # ── PID dead but no output → failure path ────────────────────────────
        if not pid_alive and not output_ok:
            logger.warning(f"{task_id} — PID dead, no output. attempts={attempts}")

            if attempts < 2:
                # Escalation level 1: retry same route
                logger.info(f"{task_id} — Escalation L1: retry (attempt {attempts + 1})")
                record['error']      = 'PID exited without output — retrying'
                record['started_at'] = _now_iso()
                record = dispatch(record, record.get('routed_to'))
                started_at = record.get('started_at', _now_iso())
                time.sleep(POLL_INTERVAL)
                continue

            current_model = record.get('routed_to', {}).get('model', 'sonnet')

            if current_model == 'sonnet':
                # Escalation level 2: upgrade sonnet → opus
                logger.info(f"{task_id} — Escalation L2: sonnet→opus")
                upgraded = upgrade_route(record.get('routed_to', {}))
                record['routed_to']  = upgraded
                record['error']      = 'Double failure — upgrading to Opus'
                record['started_at'] = _now_iso()
                record = dispatch(record, upgraded)
                started_at = record.get('started_at', _now_iso())
                time.sleep(POLL_INTERVAL)
                continue

            else:
                # Escalation level 3: Opus failed — notify Hale
                msg = (
                    f"\U0001f985 *SLOT ROUTER — OPUS FAILURE (Hale Action)*\n\n"
                    f"Task `{task_id}` failed after Opus upgrade.\n"
                    f"Type: `{record.get('classified_type', '')}`\n"
                    f"Task: {record.get('task', '')[:200]}\n"
                    f"Error: {record.get('error', 'unknown')}\n\n"
                    f"Manual intervention needed."
                )
                from dispatcher import send_telegram_escalation as _tg
                sent = _tg(task_id, msg)
                record['status'] = 'escalated'
                record['error']  = f'Opus failure — Hale notified (telegram={sent})'
                logger.error(f"{task_id} — L3 escalation to Hale (sent={sent})")
                _save_task(record)
                _log_outcome(record, 'escalated_hale')
                return record

        # ── Timeout ───────────────────────────────────────────────────────────
        if elapsed > timeout:
            msg = (
                f"\U0001f985 *SLOT ROUTER — TASK TIMEOUT*\n\n"
                f"Task `{task_id}` running for {int(elapsed)}s (limit={timeout}s).\n"
                f"Type: `{record.get('classified_type', '')}`\n"
                f"Task: {record.get('task', '')[:200]}\n"
                f"PID: {record.get('pid')}\n\n"
                f"Commander action may be needed."
            )
            from dispatcher import send_telegram_escalation as _tg, _save_task as _st
            sent = _tg(task_id, msg)
            record['status'] = 'escalated'
            record['error']  = f'Timeout {int(elapsed)}s — Commander notified (sent={sent})'
            logger.error(f"{task_id} — L4 TIMEOUT, Commander notified (sent={sent})")
            _st(record)
            _log_outcome(record, 'escalated_timeout')
            return record

        time.sleep(POLL_INTERVAL)


# ─── Background monitor loop (passive scan) ───────────────────────────────────

def run_monitor_loop(poll_seconds: int = 30) -> None:
    """
    Background daemon — periodically scans task store for running tasks
    and auto-resolves those whose PID has exited or timed out.
    Does NOT block on individual tasks (that's monitor_task's job).
    """
    from dispatcher import _load_tasks, _save_task, send_telegram_escalation
    from routing_table import get_timeout

    logger.info("Monitor background loop started")

    while True:
        try:
            tasks   = _load_tasks()
            running = [t for t in tasks.values() if t.get('status') == 'running']

            for record in running:
                elapsed   = _elapsed_seconds(record.get('started_at', _now_iso()))
                timeout   = get_timeout(record.get('complexity', 'simple'))
                pid       = record.get('pid')
                outfile   = record.get('output_file', '')
                task_id   = record.get('id', '?')

                if _output_valid(outfile) and not _pid_alive(pid):
                    record['status']       = 'success'
                    record['completed_at'] = _now_iso()
                    _save_task(record)
                    _log_outcome(record, 'success')
                    logger.info(f"{task_id} — loop auto-detected success")

                elif elapsed > timeout:
                    msg = (
                        f"\U0001f985 *SLOT ROUTER — TIMEOUT (loop)*\n\n"
                        f"Task `{task_id}` ran {int(elapsed)}s (limit={timeout}s).\n"
                        f"Task: {record.get('task', '')[:200]}"
                    )
                    send_telegram_escalation(task_id, msg)
                    record['status'] = 'escalated'
                    record['error']  = f'Timeout {int(elapsed)}s'
                    _save_task(record)
                    _log_outcome(record, 'escalated_timeout')

        except Exception as e:
            logger.error(f"Monitor loop error: {e}")

        time.sleep(poll_seconds)


if __name__ == '__main__':
    run_monitor_loop()
