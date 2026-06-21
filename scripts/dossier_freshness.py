#!/usr/bin/env python3
"""Alert on stale dossier files for trips departing within 60 days."""
import json, urllib.request, os, logging, time
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/dossier_freshness.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

DOSSIERS = Path('/home/john/Thunderbird/dossiers')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def parse_date(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00')).date()
    except Exception: return None

def main():
    if not DOSSIERS.exists():
        logging.info('no dossiers dir')
        return
    today = date.today()
    now = time.time()
    stale = []
    for p in DOSSIERS.glob('*.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if not isinstance(d, dict): continue
        dep = parse_date(d.get('departure_date') or d.get('start_date')
                         or d.get('embarkation_date'))
        if not dep: continue
        delta = (dep - today).days
        if not (0 <= delta <= 60): continue
        age_days = (now - p.stat().st_mtime) / 86400
        if age_days > 14:
            client = d.get('client') or d.get('client_name') or p.stem
            stale.append(f'• {client} (dep {dep}, file {age_days:.0f}d stale)')
    if stale:
        tg('📂 DOSSIER FRESHNESS — stale active trips:\n' + '\n'.join(stale[:30]))
        logging.info(f'{len(stale)} stale')
    else:
        logging.info('all active dossiers fresh')

if __name__ == '__main__':
    main()
