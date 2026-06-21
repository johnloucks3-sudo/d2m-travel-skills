#!/usr/bin/env python3
"""Flag bookings where trip ended >45d ago with no commission_received."""
import json, urllib.request, os, logging
from pathlib import Path
from datetime import datetime, date, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/commission_watch.log')
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
    try:
        return datetime.fromisoformat(str(s).replace('Z','+00:00')).date()
    except Exception:
        for f in ('%Y-%m-%d','%m/%d/%Y','%Y/%m/%d'):
            try: return datetime.strptime(str(s)[:10], f).date()
            except Exception: continue
    return None

def main():
    if not DOSSIERS.exists():
        logging.info('no dossiers dir')
        return
    today = date.today()
    flagged = []
    for p in DOSSIERS.glob('*.json'):
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            logging.warning(f'{p.name}: {e}')
            continue
        if not isinstance(d, dict): continue
        # try common shapes
        end = (d.get('trip_end_date') or d.get('return_date') or
               d.get('end_date') or d.get('disembarkation_date'))
        end_d = parse_date(end)
        if not end_d: continue
        days = (today - end_d).days
        if days < 45: continue
        if d.get('commission_received') or d.get('commission_received_date'):
            continue
        if not d.get('expected_commission') and not d.get('commission'):
            continue
        client = d.get('client') or d.get('client_name') or p.stem
        flagged.append(f'• {client} (ended {end_d.isoformat()}, +{days}d)')
    if flagged:
        tg('💰 COMMISSION WATCH — overdue (>45d):\n' + '\n'.join(flagged[:30]))
        logging.info(f'flagged {len(flagged)}')
    else:
        logging.info('no overdue commissions')

if __name__ == '__main__':
    main()
