#!/usr/bin/env python3
"""Detect duplicate blackboard section headers (race conditions between staff)."""
import json, urllib.request, os, logging, re, time
from pathlib import Path
from collections import Counter

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/blackboard_conflict_resolver.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

BLACKBOARD = Path('/home/john/Thunderbird/OpsCenter/collaboration/blackboard.md')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

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
    if dup:
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
