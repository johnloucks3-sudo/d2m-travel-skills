#!/usr/bin/env python3
"""Scan d2mconcierge Gmail for supplier promo emails in last 24h."""
import json, urllib.request, os, logging, sys
from pathlib import Path

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/supplier_promo_scan.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

sys.path.insert(0, '/home/john/Thunderbird')

SUPPLIERS = ['rssc.com','silversea.com','regent-seven-seas.com',
             'hollandamerica.com','princess.com']
PROMO_TERMS = ('promo','sale','offer','deal','reduced','% off','bonus','wave')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def search_gmail(query):
    try:
        from core.email import thunderbird_gmail as tg_mail
        for name in ('search','search_messages','list_messages'):
            fn = getattr(tg_mail, name, None)
            if fn: return fn(query)
    except Exception as e:
        logging.debug(f'gmail backend missing: {e}')
    return []

def main():
    hits = []
    for dom in SUPPLIERS:
        q = f'from:{dom} newer_than:1d'
        try:
            res = search_gmail(q) or []
        except Exception as e:
            logging.warning(f'search {dom}: {e}')
            continue
        for m in (res if isinstance(res, list) else []):
            subj = (m.get('subject') if isinstance(m, dict) else '') or ''
            sender = (m.get('from') if isinstance(m, dict) else '') or dom
            low = subj.lower()
            if any(t in low for t in PROMO_TERMS):
                hits.append((subj[:80], sender, dom))
                logging.info(f'promo {dom}: {subj[:80]}')
    if hits:
        body = '\n'.join(f'• {s} — {snd}' for s, snd, _ in hits[:20])
        tg(f'📬 SUPPLIER PROMOS (24h):\n{body}')
    else:
        logging.info('no supplier promos')

if __name__ == '__main__':
    main()
