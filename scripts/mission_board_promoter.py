#!/usr/bin/env python3
"""Auto-promote stale P2 mission board tasks to P1 after 7 days."""
import json, urllib.request, os, logging, subprocess, re
from pathlib import Path
from datetime import datetime, date, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/mission_board_promoter.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

SYNC = '/home/john/Thunderbird/OpsCenter/mission_board_sync.py'

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def parse_when(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00'))
    except Exception: return None

def main():
    if not Path(SYNC).exists():
        logging.info(f'mission_board_sync not present at {SYNC}')
        return
    try:
        out = subprocess.check_output(['python3', SYNC, 'list'],
                                      text=True, timeout=60)
    except Exception as e:
        logging.error(f'list failed: {e}')
        return
    promoted = []
    now = datetime.now(timezone.utc)
    # try JSON first
    items = None
    try:
        items = json.loads(out)
    except Exception:
        items = None
    if isinstance(items, dict) and 'tasks' in items:
        items = items['tasks']
    if isinstance(items, list):
        for t in items:
            if not isinstance(t, dict): continue
            prio = str(t.get('priority','')).upper()
            if 'P2' not in prio: continue
            created = parse_when(t.get('created') or t.get('created_at')
                                 or t.get('updated_at'))
            if not created: continue
            if created.tzinfo is None: created = created.replace(tzinfo=timezone.utc)
            age = (now - created).total_seconds() / 86400
            if age < 7: continue
            tid = t.get('id') or t.get('task_id')
            if not tid: continue
            promoted.append(tid)
    else:
        # text fallback: lines with P2 + age marker
        for line in out.splitlines():
            m = re.search(r'\b(\d+)\b.*P2.*(\d+)\s*d(?:ays)?\b', line)
            if m and int(m.group(2)) >= 7:
                promoted.append(m.group(1))
    for tid in promoted:
        try:
            subprocess.run(['python3', SYNC, 'update', str(tid),
                            'P1 — auto-promoted by Hale (7d stale)'],
                           timeout=30, check=False)
            logging.info(f'promoted {tid}')
        except Exception as e:
            logging.warning(f'promote {tid}: {e}')
    if promoted:
        tg(f'🪪 MISSION BOARD: auto-promoted {len(promoted)} stale P2→P1')
    else:
        logging.info('no stale P2 tasks')

if __name__ == '__main__':
    main()
