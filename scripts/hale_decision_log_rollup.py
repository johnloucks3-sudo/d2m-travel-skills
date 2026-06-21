#!/usr/bin/env python3
"""Daily roll-up of last 24h Hale decisions; relay to OC via wing_relay."""
import json, urllib.request, os, logging, re, subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/hale_decision_log_rollup.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

DECISION_LOG = Path('/home/john/Thunderbird/hale_decisions.md')

def tg(msg):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json.dumps({'chat_id':COMMANDER_ID,'text':msg}).encode(),
            headers={'Content-Type':'application/json'}), timeout=15)
    except Exception as e:
        logging.warning(f'telegram failed: {e}')

def main():
    if not DECISION_LOG.exists():
        logging.info(f'no decision log at {DECISION_LOG}')
        return
    text = DECISION_LOG.read_text(errors='ignore')
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    entries = []
    for chunk in re.split(r'\n(?=\d{4}-\d{2}-\d{2})', text):
        m = re.match(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?)', chunk)
        if not m: continue
        try: ts = datetime.fromisoformat(m.group(1).replace(' ','T'))
        except Exception: continue
        if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff: continue
        entries.append(chunk.strip())
    n = len(entries)
    html_lines = ['<h2>Hale Decision Log — Last 24h</h2>',
                  f'<p><b>{n}</b> decisions logged.</p>']
    if entries:
        html_lines.append('<ul>')
        for e in entries[:50]:
            first = e.splitlines()[0][:200]
            html_lines.append(f'<li>{first}</li>')
        html_lines.append('</ul>')
    html = '\n'.join(html_lines)
    try:
        subprocess.run(['python3','/home/john/Thunderbird/core/relay/wing_relay.py',
                        'send','OC', f'Decision log: {n} decisions today\n\n{html}'],
                       timeout=30, check=False)
    except Exception as e:
        logging.warning(f'wing_relay: {e}')
    tg(f'📜 Decision log roll-up: {n} decisions in last 24h')
    logging.info(f'rolled up {n} entries')

if __name__ == '__main__':
    main()
