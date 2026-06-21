#!/usr/bin/env python3
"""Self-audit of systemd user timers — alert on dead/lagging timers."""
import json, urllib.request, os, subprocess, logging, re
from pathlib import Path

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/timer_self_audit.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def main():
    try:
        out = subprocess.check_output(
            ['systemctl','--user','list-timers','--all','--no-pager'],
            text=True, timeout=30)
    except Exception as e:
        logging.error(f'list-timers failed: {e}')
        return
    dead = []
    for line in out.splitlines():
        if not line.strip() or 'NEXT' in line.upper() or 'timers listed' in line.lower():
            continue
        # detect 'NONE' / 'n/a' next elapse
        if re.search(r'\bn/?a\b', line, re.I) or line.strip().startswith('-'):
            dead.append(line.strip()[:160])
    if dead:
        msg = '⚠️ TIMER AUDIT — dead/inactive timers:\n' + '\n'.join(dead[:20])
        tg(msg)
        logging.info(f'flagged {len(dead)} timers')
    else:
        logging.info('all clear — all timers scheduled')

if __name__ == '__main__':
    main()
