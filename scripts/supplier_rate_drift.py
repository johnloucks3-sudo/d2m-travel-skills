#!/usr/bin/env python3
"""Detect rebook opportunities: current supplier rate < booked rate."""
import json, urllib.request, os, logging, sys
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/supplier_rate_drift.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

DOSSIERS = Path('/home/john/Thunderbird/dossiers')
sys.path.insert(0, '/home/john/Thunderbird')

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

def current_rate(line, sail_date, booking):
    try:
        from core.travel import thunderbird_fare_watch as tfw
        if hasattr(tfw,'current_rate'):
            return tfw.current_rate(line, sail_date, booking)
        if hasattr(tfw,'check'):
            return tfw.check(line, sail_date, booking)
    except Exception as e:
        logging.debug(f'no fare watch: {e}')
    return None

def main():
    if not DOSSIERS.exists(): return
    today = date.today()
    drops = []
    for p in DOSSIERS.glob('*.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if not isinstance(d, dict): continue
        line = d.get('cruise_line') or d.get('supplier')
        sail = parse_date(d.get('sailing_date') or d.get('departure_date'))
        booked = d.get('booked_rate') or d.get('booking_total') or d.get('rate')
        if not (line and sail and booked): continue
        if (sail - today).days < 0: continue
        cur = current_rate(line, sail, d)
        try:
            if cur is None: continue
            if float(cur) < float(booked):
                client = d.get('client') or p.stem
                drops.append(f'• {client} {line} {sail}: ${cur} < ${booked}')
        except Exception:
            continue
    if drops:
        tg('🔻 RATE DRIFT — rebook opportunity:\n' + '\n'.join(drops[:20]))
        logging.info(f'{len(drops)} drops')
    else:
        logging.info('no rate drops')

if __name__ == '__main__':
    main()
