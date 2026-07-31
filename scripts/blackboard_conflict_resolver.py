#!/usr/bin/env python3
"""Detect duplicate blackboard section headers (race conditions between staff)."""
import json, urllib.request, os, logging, re, time
from datetime import datetime
from pathlib import Path
from collections import Counter

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/blackboard_conflict_resolver.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

BLACKBOARD = Path('/home/john/Thunderbird/OpsCenter/collaboration/blackboard.md')

# One-and-done dedup (2026-07-04, Silver/A7): 5-min timer re-paged every run
# while the same duplicate headers persisted. Key on the exact set of duplicate
# headers — a persisting conflict stays silent, a new/changed conflict re-fires,
# and the key clears once the duplicates are resolved so recurrence pages fresh.
DEDUP_STATE = Path('/home/john/Thunderbird/OpsCenter/state/blackboard_conflict_resolver_alert_dedup.json')

def _dedup_new_keys(active_keys):
    state = {}
    if DEDUP_STATE.exists():
        try:
            state = json.loads(DEDUP_STATE.read_text())
        except Exception:
            state = {}
    state = {k: v for k, v in state.items() if k in active_keys}
    new_keys = []
    for k in active_keys:
        if k not in state:
            new_keys.append(k)
            state[k] = datetime.now().isoformat()
    DEDUP_STATE.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_STATE.write_text(json.dumps(state, indent=2))
    return new_keys

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def main():
    if not BLACKBOARD.exists():
        logging.info(f'no blackboard at {BLACKBOARD}')
        return
    mtime_age = time.time() - BLACKBOARD.stat().st_mtime
    if mtime_age > 300:
        logging.info(f'blackboard not modified in last 5min (age {mtime_age:.0f}s)')
        return
    text = BLACKBOARD.read_text(errors='ignore')
    headers = re.findall(r'^#+\s*\[?([A-Z]{2,}[A-Z0-9_-]*)\]?', text, re.M)
    dup = [h for h, c in Counter(headers).items() if c > 1]
    active = {'dup:' + '|'.join(sorted(dup))} if dup else set()
    new_keys = _dedup_new_keys(active)
    if dup:
        if new_keys:
            winners = []
            for h in dup:
                # the LAST occurrence wins by timestamp / position
                winners.append(f'{h} → keep last occurrence')
            msg = ('🪧 BLACKBOARD CONFLICT — duplicate section headers:\n' +
                   '\n'.join(f'• {w}' for w in winners[:10]))
            tg(msg)
        logging.info(f'conflicts: {dup}')
    else:
        logging.info('no duplicate headers')

if __name__ == '__main__':
    main()
