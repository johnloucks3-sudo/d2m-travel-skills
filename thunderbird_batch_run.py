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


# ── IOC Tasks (added Mar 20) ────────────────────────────────────────────────

async def task_learning_extraction():
    """Extract principles from recent Commander corrections."""
    from thunderbird_learning import extract_principles
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, extract_principles)
    return {'principles_extracted': len(result) if result else 0, 'principles': result}


async def task_dossier_scan():
    """Scan all dossiers for gaps, missing data, approaching deadlines."""
    from thunderbird_dossier_scanner import scan_all_dossiers, generate_alert_digest
    loop = asyncio.get_event_loop()
    alerts = await loop.run_in_executor(None, scan_all_dossiers)
    digest = await loop.run_in_executor(None, generate_alert_digest)
    return {
        'total_alerts': len(alerts),
        'critical': sum(1 for a in alerts if a.severity == 'CRITICAL'),
        'warnings': sum(1 for a in alerts if a.severity == 'WARNING'),
        'digest': digest,
    }


async def task_commander_inbox():
    """Scan Commander's personal inbox for D2M-relevant emails."""
    try:
        from thunderbird_commander_inbox import run_commander_inbox_sweep
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_commander_inbox_sweep)
    except ImportError:
        return {'note': 'Commander inbox scanner not yet installed'}


async def task_fare_watch():
    """Check all active fare watches for price changes."""
    from thunderbird_fare_watch import list_watches, check_fare
    loop = asyncio.get_event_loop()
    watches = await loop.run_in_executor(None, list_watches)
    if not watches:
        return {'note': 'No active fare watches'}
    results = []
    for w in watches:
        try:
            result = await loop.run_in_executor(None, check_fare, w.get('id') or w.get('watch_id'))
            results.append(result)
        except Exception as e:
            results.append({'watch': w.get('route', 'unknown'), 'error': str(e)})
    return {'watches_checked': len(results), 'results': results}


async def task_voice_ledger_update():
    """Import new rules from learning compiler into voice ledger."""
    from thunderbird_voice_ledger import import_from_learning_compiler
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, import_from_learning_compiler)
    return {'imported': result}


async def task_booking_reconciliation():
    """Weekly: cross-check all bookings across dossiers, Sheets, and TESS."""
    from thunderbird_reconciliation import reconcile_all_bookings, reconciliation_briefing_line
    loop = asyncio.get_event_loop()
    reports = await loop.run_in_executor(None, reconcile_all_bookings)
    mismatches = [r for r in reports if r.status == 'RED']
    missing = [r for r in reports if r.status == 'YELLOW']
    return {
        'total': len(reports),
        'clean': sum(1 for r in reports if r.status == 'GREEN'),
        'mismatches': len(mismatches),
        'missing_data': len(missing),
        'briefing_line': reconciliation_briefing_line(reports),
        'mismatch_details': [r.summary_line for r in mismatches],
        'missing_details': [r.summary_line for r in missing],
    }


async def task_product_intake():
    """Scan vendor emails for new product offers — cruises, hotels, tours."""
    try:
        from thunderbird_product_intake import scan_vendor_emails, generate_product_digest
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(None, scan_vendor_emails, 3)
        digest = await loop.run_in_executor(None, generate_product_digest, 7)
        return {
            'new_products': len(products) if products else 0,
            'digest': digest[:1000] if digest else 'No new products',
        }
    except ImportError:
        return {'note': 'Product intake module not yet installed'}


async def task_guest_forms():
    """Batch: send guest profile forms for upcoming departures."""
    try:
        from thunderbird_guest_forms import send_all_pending_guest_forms
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, send_all_pending_guest_forms, 60)
        return result
    except ImportError:
        return {'note': 'Guest forms module not yet installed'}


async def task_claude_code_batch(prompt: str, name: str = 'batch'):
    """Run a Claude Code CLI task headlessly. For off-peak heavy coding."""
    import subprocess, os
    cmd = [
        'claude', '-p', prompt,
        '--bare',  # v2.1.81: skips hooks, LSP, plugin sync, skill walks — faster batch
        '--allowedTools', 'Read,Edit,Write,Bash,Grep,Glob,mcp__dreams2memories__*',
        '--output-format', 'json',
        '--max-turns', '30',
        '--max-budget-usd', '2.00',
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=3600,
        cwd=str(THUNDERBIRD_DIR),
        env={**os.environ, 'CLAUDE_BATCH_MODE': '1', 'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', '')},
    )
    try:
        parsed = json.loads(result.stdout)
        return {'session_id': parsed.get('session_id'), 'result': parsed.get('result', '')[:500]}
    except json.JSONDecodeError:
        return {'stdout': result.stdout[:500], 'stderr': result.stderr[:200], 'exit_code': result.returncode}


# ── STANDING ORDER 2026-03-26 (AMENDED) — Commander selected 1,2,4,6,10-16 ──
# First pass killed all intel. Commander reviewed full manifest and restored
# World Intel, Ship Intel, Competitive Surveillance, Tech Monitor.
# Permanently killed: Star Protocol, Email Intel Sweep, Airline Route Scan,
#                     Commander Inbox Sweep, Dani Email Sweep.
# Full numbered manifest reference:
#   1=World Intel  2=Ship Intel  3=Star Protocol(KILL)  4=Competitive
#   5=Email Intel(KILL)  6=Tech Monitor  7=Airline Scan(KILL)
#   8=Cmd Inbox(KILL)  9=Dani Email(KILL)  10=Learning  11=Dossier
#   12=Fare Watch  13=Voice Ledger  14=Reconciliation  15=Product  16=Guest Forms

TASKS = [
    # ── INTEL — Commander-selected (1, 2, 4, 6) ────────────────────────────────
    {'name': 'World Intelligence Sweep',        'weight': 'heavy',  'fn': task_world_intel},       # 1 ✅
    {'name': 'Ship Intelligence Sweep',         'weight': 'heavy',  'fn': task_ship_intel},        # 2 ✅
    # {'name': 'Star Protocol Sweep',           'weight': 'medium', 'fn': task_star_sweep},        # 3 ❌ KILLED
    {'name': 'Competitive Surveillance',        'weight': 'medium', 'fn': task_competitive},       # 4 ✅
    # {'name': 'Email Intel Sweep',             'weight': 'medium', 'fn': task_email_intel},       # 5 ❌ KILLED
    {'name': 'Tech Monitor',                    'weight': 'light',  'fn': task_tech_monitor},      # 6 ✅
    # {'name': 'Airline Route Scan',            'weight': 'light',  'fn': task_airline_scan},      # 7 ❌ KILLED
    # {'name': 'Commander Inbox Sweep',         'weight': 'medium', 'fn': task_commander_inbox},   # 8 ❌ KILLED
    # {'name': 'Dani Email Sweep',              'weight': 'medium', 'fn': task_dani_email},        # 9 ❌ KILLED

    # ── OPERATIONAL — retained (10-16) ─────────────────────────────────────────
    {'name': 'Learning Extraction',             'weight': 'medium', 'fn': task_learning_extraction}, # 10 ✅
    {'name': 'Dossier Gap Scanner',             'weight': 'light',  'fn': task_dossier_scan},      # 11 ✅
    {'name': 'Fare Watch Check',                'weight': 'light',  'fn': task_fare_watch},        # 12 ✅
    {'name': 'Voice Ledger Update',             'weight': 'light',  'fn': task_voice_ledger_update}, # 13 ✅
    {'name': 'Booking Reconciliation',          'weight': 'light',  'fn': task_booking_reconciliation}, # 14 ✅
    {'name': 'Product Intake Scan',             'weight': 'medium', 'fn': task_product_intake},    # 15 ✅
    {'name': 'Guest Profile Forms',             'weight': 'light',  'fn': task_guest_forms},       # 16 ✅
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
