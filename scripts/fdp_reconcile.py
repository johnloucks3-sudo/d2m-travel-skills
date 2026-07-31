#!/usr/bin/env python3
"""Reconcile Final Payment Due items against dossiers; alert FPD ≤30d unpaid."""
import json, urllib.request, os, logging
from pathlib import Path
from datetime import datetime, date

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/fdp_reconcile.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

HALE_STATES = [
    Path('/home/john/Thunderbird/hale_state.json'),
    Path('/home/john/Thunderbird/OpsCenter/hale_state.json'),
]
DOSSIERS = Path('/home/john/Thunderbird/dossiers')

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def parse_date(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00')).date()
    except Exception: return None

def load_hale():
    for p in HALE_STATES:
        if p.exists():
            try: return json.loads(p.read_text())
            except Exception as e: logging.warning(f'{p}: {e}')
    return {}

def main():
    today = date.today()
    hale = load_hale()
    deferred = hale.get('deferred_alerts', []) if isinstance(hale, dict) else []
    fpd_items = {}
    for a in deferred:
        if not isinstance(a, dict): continue
        tag = (a.get('type') or a.get('kind') or '').upper()
        if 'FPD' in tag or 'FINAL_PAYMENT' in tag or 'FPD' in (a.get('label','').upper()):
            key = a.get('booking_id') or a.get('client') or a.get('id')
            fpd_items[key] = a
    flagged = []
    if DOSSIERS.exists():
        for p in DOSSIERS.glob('*.json'):
            try: d = json.loads(p.read_text())
            except Exception: continue
            if not isinstance(d, dict): continue
            fpd = parse_date(d.get('final_payment_due') or d.get('fpd'))
            if not fpd: continue
            delta = (fpd - today).days
            if not (0 <= delta <= 30): continue
            if d.get('final_payment_paid') or d.get('fpd_paid'): continue
            client = d.get('client') or d.get('client_name') or p.stem
            flagged.append(f'• {client} — FPD {fpd} (+{delta}d)')
    if flagged:
        tg('💳 FPD RECONCILE — due ≤30d unpaid:\n' + '\n'.join(flagged[:30]))
        logging.info(f'{len(flagged)} flagged')
    else:
        logging.info('FPD all clear')

if __name__ == '__main__':
    main()
