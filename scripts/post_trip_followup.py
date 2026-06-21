#!/usr/bin/env python3
"""Queue post-trip touchpoints (T+7 testimonial, T+21 review, T+45 referral)."""
import json, urllib.request, os, logging
from pathlib import Path
from datetime import datetime, date, timedelta

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/post_trip_followup.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

DOSSIERS = Path('/home/john/Thunderbird/dossiers')
QUEUE_LOG = Path('/home/john/Thunderbird/logs/post_trip_queue.log')

STEPS = [(7,'testimonial_request'),(21,'review_reminder'),(45,'referral_ask')]

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
    if not DOSSIERS.exists(): return
    today = date.today()
    queued_today = []
    with QUEUE_LOG.open('a') as f:
        for p in DOSSIERS.glob('*.json'):
            try: d = json.loads(p.read_text())
            except Exception: continue
            if not isinstance(d, dict): continue
            ret = parse_date(d.get('return_date') or d.get('trip_end_date')
                             or d.get('disembarkation_date'))
            if not ret: continue
            client = d.get('client') or d.get('client_name') or p.stem
            for offset, kind in STEPS:
                if (today - ret).days == offset:
                    entry = {'date': today.isoformat(),'client': client,
                             'kind': kind,'dossier': p.name}
                    f.write(json.dumps(entry) + '\n')
                    queued_today.append(f'• {client} — {kind}')
                    logging.info(f'queued {kind} for {client}')
    if queued_today:
        tg('📨 POST-TRIP QUEUED TODAY:\n' + '\n'.join(queued_today[:30]))
    else:
        logging.info('no post-trip touchpoints due')

if __name__ == '__main__':
    main()
