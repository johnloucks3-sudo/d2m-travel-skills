#!/usr/bin/env python3
"""
Thunderbird Off-Peak Batch Runner
Dreams2Memories Travel, LLC

Calls intel sweep functions directly — no API credits needed.
Leverages 2x Claude usage promotion during off-peak hours (outside 8 AM–2 PM ET weekdays).
Scheduled: 12:05 PM MDT (18:05 UTC) Mon–Fri via systemd timer.
Promotion window: March 13–28, 2026.

Usage:
  python thunderbird_batch_run.py           # run all tasks
  python thunderbird_batch_run.py --task 2  # run specific task by index
  python thunderbird_batch_run.py --list    # list all tasks
  python thunderbird_batch_run.py --dry-run # show what would run, no execution
"""

import asyncio
import json
import logging
import sys
import argparse
import traceback
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path('/home/john/Thunderbird')
LOG_DIR = THUNDERBIRD_DIR / 'logs' / 'batch'
LOG_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(THUNDERBIRD_DIR))

# ── Logging ───────────────────────────────────────────────────────────────────
log = logging.getLogger('batch_runner')
log.setLevel(logging.INFO)
_fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
_fh = logging.FileHandler(LOG_DIR / 'batch_runner.log')
_sh = logging.StreamHandler()
_fh.setFormatter(_fmt)
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)


# ── Task Definitions ──────────────────────────────────────────────────────────
async def task_world_intel():
    from thunderbird_world_intel import run_world_intelligence_sweep
    return await run_world_intelligence_sweep()

async def task_ship_intel():
    from thunderbird_ship_intel import run_ship_intelligence_sweep
    return await run_ship_intelligence_sweep()

async def task_star_sweep():
    from thunderbird_star_protocol import run_star_sweep
    # run_star_sweep is sync — run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_star_sweep)

async def task_competitive():
    from thunderbird_competitive_surveillance import run_surveillance_sprint
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_surveillance_sprint)

async def task_email_intel():
    from thunderbird_email_intel import run_email_intel_sweep
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_email_intel_sweep)

async def task_dani_email():
    from thunderbird_dani_email import dani_email_sweep
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, dani_email_sweep)

async def task_tech_monitor():
    from thunderbird_tech_monitor import run_daily_tech_monitor
    return await run_daily_tech_monitor()

async def task_airline_scan():
    # scan_airline_route_changes lives in world_intel or email_intel
    try:
        from thunderbird_email_intel import scan_airline_route_changes
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scan_airline_route_changes)
    except ImportError:
        from thunderbird_world_intel import run_world_intelligence_sweep
        log.warning('scan_airline_route_changes not found standalone — folded into world intel')
        return {'note': 'airline scan included in world intel run'}


TASKS = [
    {'name': 'World Intelligence Sweep',        'weight': 'heavy',  'fn': task_world_intel},
    {'name': 'Ship Intelligence Sweep',         'weight': 'heavy',  'fn': task_ship_intel},
    {'name': 'Star Protocol Sweep',             'weight': 'medium', 'fn': task_star_sweep},
    {'name': 'Competitive Surveillance',        'weight': 'medium', 'fn': task_competitive},
    {'name': 'Email Intel Sweep',               'weight': 'medium', 'fn': task_email_intel},
    {'name': 'Dani Email Sweep',                'weight': 'medium', 'fn': task_dani_email},
    {'name': 'Tech Monitor',                    'weight': 'light',  'fn': task_tech_monitor},
    {'name': 'Airline Route Scan',              'weight': 'light',  'fn': task_airline_scan},
]


# ── Runner ────────────────────────────────────────────────────────────────────
async def run_task(task: dict) -> dict:
    name = task['name']
    log.info(f'▶  {name} [{task["weight"]}]')
    start = datetime.now()

    try:
        result = await asyncio.wait_for(task['fn'](), timeout=600)
        elapsed = (datetime.now() - start).total_seconds()

        # Serialize result to log file
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe = name.replace(' ', '_')[:35]
        out_file = LOG_DIR / f'{ts}_{safe}.json'
        out_file.write_text(json.dumps(result, indent=2, default=str))

        log.info(f'✓  {name} — {elapsed:.0f}s → {out_file.name}')
        return {'task': name, 'success': True, 'elapsed': elapsed, 'output': str(out_file)}

    except asyncio.TimeoutError:
        elapsed = (datetime.now() - start).total_seconds()
        log.error(f'⏱  TIMEOUT: {name} after {elapsed:.0f}s')
        return {'task': name, 'success': False, 'elapsed': elapsed, 'error': 'timeout'}
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        log.error(f'✗  {name}: {e}')
        log.debug(traceback.format_exc())
        return {'task': name, 'success': False, 'elapsed': elapsed, 'error': str(e)}


async def main_async(tasks_to_run: list):
    run_ts = datetime.now().strftime('%Y-%m-%d %H:%M MDT')
    log.info('=' * 60)
    log.info(f'Thunderbird Batch Run — {run_ts}')
    log.info(f'Tasks: {len(tasks_to_run)} | Off-peak 2x window active')
    log.info('=' * 60)

    results = []
    for task in tasks_to_run:
        results.append(await run_task(task))

    passed = sum(1 for r in results if r.get('success'))
    total_time = sum(r.get('elapsed', 0) for r in results)
    log.info('=' * 60)
    log.info(f'Complete: {passed}/{len(results)} succeeded | {total_time:.0f}s total')
    log.info('=' * 60)

    summary = LOG_DIR / f'summary_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    summary.write_text(json.dumps(results, indent=2, default=str))
    log.info(f'Summary → {summary.name}')

    return 0 if passed == len(results) else 1


def main():
    parser = argparse.ArgumentParser(description='Thunderbird Off-Peak Batch Runner')
    parser.add_argument('--list',    action='store_true', help='List all tasks and exit')
    parser.add_argument('--dry-run', action='store_true', help='Show tasks without executing')
    parser.add_argument('--task',    type=int,            help='Run single task by index (1-based)')
    args = parser.parse_args()

    if args.list or args.dry_run:
        print('\nThunderbird Batch Tasks:')
        for i, t in enumerate(TASKS, 1):
            print(f'  {i:2d}. [{t["weight"]:6s}] {t["name"]}')
        if args.dry_run:
            print('\n[dry-run — no tasks executed]')
        return

    tasks_to_run = [TASKS[args.task - 1]] if args.task else TASKS
    exit_code = asyncio.run(main_async(tasks_to_run))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
