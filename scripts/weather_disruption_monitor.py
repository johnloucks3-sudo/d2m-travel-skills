#!/usr/bin/env python3
"""Scan upcoming travel for weather/disruption news via perplexity_search."""
import json, urllib.request, os, logging, sys
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/weather_disruption_monitor.log')
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

def pplx_search(q):
    try:
        from core.search import perplexity_search as ps
        if hasattr(ps,'search'):
            return ps.search(q)
    except Exception as e:
        logging.debug(f'no pplx backend: {e}')
    return None

DISRUPTION_KEYWORDS = ('hurricane','storm','strike','closed','cancel','typhoon',
                       'evacuat','flooding','wildfire','volcano','tsunami')

def main():
    if not DOSSIERS.exists(): return
    today = date.today()
    alerts = []
    seen = set()
    for p in DOSSIERS.glob('*.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if not isinstance(d, dict): continue
        city = d.get('departure_city') or d.get('origin_city') or d.get('embarkation_port')
        dep = parse_date(d.get('departure_date') or d.get('start_date'))
        if not city or not dep: continue
        if not (0 <= (dep - today).days <= 14): continue
        key = (city, dep.isoformat())
        if key in seen: continue
        seen.add(key)
        q = f'travel disruption {city} {dep.isoformat()}'
        res = pplx_search(q)
        if res is None: continue
        text = json.dumps(res) if not isinstance(res,str) else res
        low = text.lower()
        if any(k in low for k in DISRUPTION_KEYWORDS):
            alerts.append(f'• {city} ({dep}): possible disruption — review intel')
    if alerts:
        tg('⛈️ WEATHER/DISRUPTION:\n' + '\n'.join(alerts[:20]))
        logging.info(f'{len(alerts)} alerts')
    else:
        logging.info('no disruptions detected')

if __name__ == '__main__':
    main()
