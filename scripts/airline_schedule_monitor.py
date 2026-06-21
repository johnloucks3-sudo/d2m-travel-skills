#!/usr/bin/env python3
"""Monitor stored PNRs for schedule changes vs booking record."""
import json, urllib.request, os, logging, sys
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/airline_schedule_monitor.log')
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

def check_schedule(pnr, origin, dest, dep_date):
    """Stub: hook for thunderbird_flight_search.check_pnr; returns None if unchanged."""
    try:
        from core.travel import thunderbird_flight_search as tfs
        if hasattr(tfs,'check_pnr_schedule'):
            return tfs.check_pnr_schedule(pnr, origin, dest, dep_date)
    except Exception as e:
        logging.debug(f'no flight search backend: {e}')
    return None

def main():
    if not DOSSIERS.exists():
        logging.info('no dossiers')
        return
    today = date.today()
    changes = []
    for p in DOSSIERS.glob('*.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if not isinstance(d, dict): continue
        flights = d.get('flights') or d.get('air_segments') or []
        if isinstance(flights, dict): flights = [flights]
        for f in flights:
            if not isinstance(f, dict): continue
            pnr = f.get('pnr') or f.get('record_locator')
            if not pnr: continue
            dep = parse_date(f.get('departure_date') or f.get('date'))
            if not dep: continue
            if (dep - today).days > 30 or (dep - today).days < 0: continue
            change = check_schedule(pnr, f.get('origin'), f.get('destination'), dep)
            if change:
                changes.append(f'• {pnr} {f.get("origin")}-{f.get("destination")} {dep}: {change}')
    if changes:
        tg('✈️ SCHEDULE CHANGE:\n' + '\n'.join(changes[:20]))
        logging.info(f'{len(changes)} changes')
    else:
        logging.info('no schedule changes')

if __name__ == '__main__':
    main()
