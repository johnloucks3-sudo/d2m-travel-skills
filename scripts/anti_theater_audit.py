#!/usr/bin/env python3
"""Weekly anti-theater check: sample 10% of Hale decisions vs mission outcomes."""
import json, urllib.request, os, logging, random, re
from pathlib import Path
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/anti_theater_audit.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

LOGS = [
    Path('/home/john/Thunderbird/logs/hale_decisions.log'),
    Path('/home/john/Thunderbird/hale_decisions.md'),
    Path('/home/john/Thunderbird/OpsCenter/hale_decisions.md'),
]

OUTCOME_TOKENS = ('mission_id','client:','booking:','task:','P0','P1','P2',
                  'dossier','commission','FPD','touchpoint')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def load_recent_entries(days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []
    for p in LOGS:
        if not p.exists(): continue
        try:
            text = p.read_text(errors='ignore')
        except Exception: continue
        # split on blank lines / per-line, filter by leading ISO timestamp if present
        for chunk in re.split(r'\n(?=\d{4}-\d{2}-\d{2})', text):
            m = re.match(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?)', chunk)
            ts = None
            if m:
                try:
                    ts = datetime.fromisoformat(m.group(1).replace(' ','T'))
                except Exception: ts = None
            if ts and ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
            if ts and ts < cutoff: continue
            chunk = chunk.strip()
            if chunk: entries.append(chunk)
    return entries

def main():
    entries = load_recent_entries(7)
    if not entries:
        logging.info('no decision entries in last 7d')
        tg('🎭 ANTI-THEATER: 0 decisions logged this week')
        return
    rng = random.Random(len(entries))
    n_sample = max(1, len(entries) // 10)
    sample = rng.sample(entries, n_sample)
    tied = 0
    for s in sample:
        low = s.lower()
        if any(tok.lower() in low for tok in OUTCOME_TOKENS):
            tied += 1
            logging.info(f'TIED: {s[:120]}')
        else:
            logging.info(f'UNTIED: {s[:120]}')
    msg = (f'🎭 Anti-theater: {tied}/{n_sample} sampled actions tied to mission '
           f'outcomes (of {len(entries)} total this week)')
    tg(msg)

if __name__ == '__main__':
    main()
