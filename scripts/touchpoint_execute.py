#!/usr/bin/env python3
"""Run scheduled client touchpoints; surface to Hale via blackboard."""
import json, urllib.request, os, logging, subprocess
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/touchpoint_execute.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

QUEUE_PATHS = [
    Path('/home/john/Thunderbird/OpsCenter/lifecycle_queue.json'),
    Path('/home/john/Thunderbird/OpsCenter/touchpoint_queue.json'),
    Path('/home/john/Thunderbird/lifecycle_queue.json'),
]

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def load_queue():
    for p in QUEUE_PATHS:
        if p.exists():
            try: return json.loads(p.read_text()), p
            except Exception as e: logging.warning(f'{p}: {e}')
    return None, None

def main():
    q, path = load_queue()
    if q is None:
        logging.info('no touchpoint queue found')
        return
    today = date.today().isoformat()
    ready = []
    items = q.get('touchpoints', q) if isinstance(q, dict) else q
    for item in items if isinstance(items,list) else []:
        if not isinstance(item, dict): continue
        due = (item.get('due_date') or item.get('scheduled') or '')[:10]
        if due and due <= today and not item.get('sent'):
            ready.append(item)
            logging.info(f'ready: {item.get("client","?")} / {item.get("kind","?")}')
    n = len(ready)
    msg = f'Touchpoint queue: {n} ready'
    try:
        subprocess.run(['python3','/home/john/Thunderbird/core/relay/wing_relay.py',
                        'send','OC', msg], timeout=20, check=False)
    except Exception as e:
        logging.warning(f'wing_relay failed: {e}')
    if n:
        tg(f'📞 TOUCHPOINTS: {n} ready for Hale review')

if __name__ == '__main__':
    main()
