#!/usr/bin/env python3
"""Build COMMANDER-READY summary on blackboard: 24h decisions + open P0/P1 + blockers."""
import json, urllib.request, os, logging, subprocess, re
from pathlib import Path
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ.get('TELEGRAM_C2_BOT_TOKEN','PLACEHOLDER_D2MC2C_TOKEN_REVOKED_20260615')
COMMANDER_ID = os.environ.get('TELEGRAM_COMMANDER_ID','7554895206')

LOG_PATH = Path('/home/john/Thunderbird/logs/commander_context_restore.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

BLACKBOARD = Path('/home/john/Thunderbird/OpsCenter/collaboration/blackboard.md')
HALE_STATE = Path('/home/john/Thunderbird/hale_state.json')
HOOK = Path('/home/john/Thunderbird/OpsCenter/state_bridge/session_startup_hook.py')
DECISION_LOG = Path('/home/john/Thunderbird/hale_decisions.md')

def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')

def hook_summary():
    if not HOOK.exists(): return ''
    try:
        out = subprocess.check_output(['python3', str(HOOK)],
                                      text=True, timeout=30)
        return out.strip()
    except Exception as e:
        logging.warning(f'hook failed: {e}')
        return ''

def recent_decisions():
    if not DECISION_LOG.exists(): return []
    text = DECISION_LOG.read_text(errors='ignore')
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    out = []
    for chunk in re.split(r'\n(?=\d{4}-\d{2}-\d{2})', text):
        m = re.match(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?)', chunk)
        if not m: continue
        try: ts = datetime.fromisoformat(m.group(1).replace(' ','T'))
        except Exception: continue
        if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff: continue
        out.append(chunk.splitlines()[0][:200])
    return out

def open_nags():
    if not HALE_STATE.exists(): return []
    try: s = json.loads(HALE_STATE.read_text())
    except Exception: return []
    nags = s.get('nags') or s.get('deferred_alerts') or []
    out = []
    for n in nags if isinstance(nags, list) else []:
        if not isinstance(n, dict): continue
        prio = str(n.get('priority','')).upper()
        if 'P0' in prio or 'P1' in prio:
            out.append(f'[{prio}] {n.get("title") or n.get("label") or n.get("id","?")}')
    return out

def blockers():
    if not HALE_STATE.exists(): return []
    try: s = json.loads(HALE_STATE.read_text())
    except Exception: return []
    b = s.get('blockers') or []
    return [str(x.get('label') if isinstance(x, dict) else x) for x in b]

SECTION_START = '<!-- COMMANDER-READY:START -->'
SECTION_END = '<!-- COMMANDER-READY:END -->'

def main():
    decisions = recent_decisions()
    nags = open_nags()
    blocks = blockers()
    hook = hook_summary()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    body = [f'## COMMANDER-READY ({now})',
            f'### Last 24h decisions ({len(decisions)})']
    body.extend(f'- {d}' for d in decisions[:15]) or body.append('- (none)')
    body.append(f'\n### Open P0/P1 nags ({len(nags)})')
    body.extend(f'- {n}' for n in nags[:15]) or body.append('- (none)')
    body.append(f'\n### Blockers ({len(blocks)})')
    body.extend(f'- {b}' for b in blocks[:10]) or body.append('- (none)')
    if hook:
        body.append('\n### Startup hook')
        body.append(hook[:1500])
    section = f'{SECTION_START}\n' + '\n'.join(body) + f'\n{SECTION_END}'
    BLACKBOARD.parent.mkdir(parents=True, exist_ok=True)
    existing = BLACKBOARD.read_text(errors='ignore') if BLACKBOARD.exists() else ''
    if SECTION_START in existing and SECTION_END in existing:
        new = re.sub(re.escape(SECTION_START) + r'.*?' + re.escape(SECTION_END),
                     section, existing, flags=re.S)
    else:
        new = existing.rstrip() + '\n\n' + section + '\n'
    BLACKBOARD.write_text(new)
    logging.info(f'COMMANDER-READY refreshed: {len(decisions)}d / {len(nags)}n / {len(blocks)}b')

if __name__ == '__main__':
    main()
