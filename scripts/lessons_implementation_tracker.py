#!/usr/bin/env python3
"""Track WING EXERCISE lessons-learned implementation rate; write rate to hale_state."""
import json, urllib.request, os, logging, re, subprocess
from pathlib import Path

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/lessons_implementation_tracker.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

OPSCENTER = Path('/home/john/Thunderbird/OpsCenter')
HALE_STATE = Path('/home/john/Thunderbird/hale_state.json')
SEARCH_ROOTS = [Path('/home/john/Thunderbird/scripts'),
                Path('/home/john/Thunderbird/core'),
                Path('/home/john/Thunderbird/OpsCenter')]

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def collect_lessons():
    lessons = []
    if not OPSCENTER.exists(): return lessons
    for p in OPSCENTER.rglob('*'):
        n = p.name.lower()
        if not (n.endswith('.md') or n.endswith('.json')): continue
        if 'lesson' not in n and 'aar' not in n: continue
        try: text = p.read_text(errors='ignore')
        except Exception: continue
        for m in re.finditer(r'(?:^|\n)\s*(?:[-*]\s*|\d+\.\s*)L\d{2,4}[:\-\s]\s*([^\n]+)',
                             text):
            lessons.append(m.group(1).strip()[:120])
        for m in re.finditer(r'(?:lesson|fix|action)\s*[:\-]\s*([^\n]{10,120})', text, re.I):
            lessons.append(m.group(1).strip())
    return list(dict.fromkeys(lessons))[:200]

def implemented(lesson):
    tokens = [t for t in re.findall(r'[A-Za-z_]{4,}', lesson) if len(t) >= 4][:3]
    if not tokens: return False
    for root in SEARCH_ROOTS:
        if not root.exists(): continue
        try:
            r = subprocess.run(['grep','-r','-l','-i','--include=*.py',
                                tokens[0], str(root)],
                               capture_output=True, text=True, timeout=20)
            if r.stdout.strip(): return True
        except Exception: continue
    return False

def main():
    lessons = collect_lessons()
    if not lessons:
        logging.info('no lessons found')
        return
    impl = sum(1 for l in lessons if implemented(l))
    rate = round(100.0 * impl / len(lessons), 1)
    state = {}
    if HALE_STATE.exists():
        try: state = json.loads(HALE_STATE.read_text())
        except Exception: state = {}
    state['lessons_implementation_rate_pct'] = rate
    state['lessons_total'] = len(lessons)
    state['lessons_implemented'] = impl
    try:
        HALE_STATE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logging.warning(f'write hale_state: {e}')
    tg(f'📚 Lessons implementation rate: {rate}% ({impl}/{len(lessons)})')
    logging.info(f'rate={rate}% impl={impl} total={len(lessons)}')

if __name__ == '__main__':
    main()
