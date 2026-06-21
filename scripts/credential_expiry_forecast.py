#!/usr/bin/env python3
"""Scan creds/ for token JSON files; alert on any expiring within 14 days."""
import json, urllib.request, os, logging, time
from pathlib import Path
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/credential_expiry_forecast.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

CREDS_DIR = Path('/home/john/Thunderbird/creds')
FIELDS = ('expiry','expires_at','token_expiry','expires_in_iso','exp')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def parse_when(val):
    if val is None: return None
    try:
        if isinstance(val,(int,float)):
            v = float(val)
            if v > 1e12: v /= 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc)
        s = str(val).strip().replace('Z','+00:00')
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
    except Exception:
        return None

def main():
    if not CREDS_DIR.exists():
        logging.info(f'no creds dir {CREDS_DIR}')
        return
    now = datetime.now(timezone.utc)
    flagged = []
    for p in CREDS_DIR.glob('*.json'):
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            logging.warning(f'parse {p.name}: {e}')
            continue
        when = None
        for f in FIELDS:
            if isinstance(data,dict) and f in data:
                when = parse_when(data[f])
                if when: break
        if when is None: continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        days = (when - now).total_seconds() / 86400
        if days <= 14:
            flagged.append((p.name, days, when.isoformat()))
            logging.info(f'expiring: {p.name} in {days:.1f}d')
    if flagged:
        flagged.sort(key=lambda x: x[1])
        body = '\n'.join(f'• {n} — {d:.1f}d ({iso[:10]})' for n,d,iso in flagged[:20])
        tg(f'🔑 CREDENTIAL EXPIRY (≤14d):\n{body}')
    else:
        logging.info('all credentials >14d to expiry')

if __name__ == '__main__':
    main()
