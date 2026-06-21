#!/usr/bin/env python3
"""Alert if /home/john disk usage exceeds 85%."""
import json, urllib.request, os, logging, shutil
from pathlib import Path

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/disk_pressure.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

THRESHOLD = 85

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
        u = shutil.disk_usage('/home/john')
    except Exception as e:
        logging.error(f'disk_usage failed: {e}')
        return
    pct = (u.used / u.total) * 100
    free_gb = u.free / (1024**3)
    logging.info(f'/home/john at {pct:.1f}% used, {free_gb:.1f} GB free')
    if pct > THRESHOLD:
        tg(f'💾 DISK PRESSURE: /home/john at {pct:.1f}% — {free_gb:.1f} GB free — action required')

if __name__ == '__main__':
    main()
