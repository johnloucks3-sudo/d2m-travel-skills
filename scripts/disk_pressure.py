#!/usr/bin/env python3
"""Alert if /home/john disk usage exceeds 85%."""
import json, urllib.request, os, logging, shutil
from datetime import datetime
from pathlib import Path

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/disk_pressure.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

THRESHOLD = 85

# One-and-done dedup (2026-07-04, Silver/A7): 15-min timer re-paged every run
# while disk stayed >85%. Gate fires once when the condition starts, stays
# silent while it persists, re-arms once disk drops back under threshold.
DEDUP_STATE = Path('/home/john/Thunderbird/OpsCenter/state/disk_pressure_alert_dedup.json')

def _dedup_new_keys(active_keys):
    state = {}
    if DEDUP_STATE.exists():
        try:
            state = json.loads(DEDUP_STATE.read_text())
        except Exception:
            state = {}
    # Drop resolved conditions so they can re-fire fresh on recurrence.
    state = {k: v for k, v in state.items() if k in active_keys}
    new_keys = []
    for k in active_keys:
        if k not in state:
            new_keys.append(k)
            state[k] = datetime.now().isoformat()
    DEDUP_STATE.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_STATE.write_text(json.dumps(state, indent=2))
    return new_keys

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def main():
    try:
        u = shutil.disk_usage('/home/john')
    except Exception as e:
        logging.error(f'disk_usage failed: {e}')
        return
    pct = (u.used / u.total) * 100
    free_gb = u.free / (1024**3)
    logging.info(f'/home/john at {pct:.1f}% used, {free_gb:.1f} GB free')
    active = {'disk_pressure'} if pct > THRESHOLD else set()
    if 'disk_pressure' in _dedup_new_keys(active):
        tg(f'💾 DISK PRESSURE: /home/john at {pct:.1f}% — {free_gb:.1f} GB free — action required')

if __name__ == '__main__':
    main()
