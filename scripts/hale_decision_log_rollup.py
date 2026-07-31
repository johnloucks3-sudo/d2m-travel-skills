#!/usr/bin/env python3
"""Daily roll-up of last 24h Hale decisions; relay to OC via wing_relay + Telegram.

Edge-triggered, not level-triggered (Silver's ground-truth rule):
  - Parser matches the REAL entry header formats in hale_decisions.md
    (`## 2026-07-01 DECISIONS`, `### 2026-07-03 14:47:11 — ...`,
     `## Session 2026-07-02 ...`, `## 2026-07-01 01:16 UTC — ...`).
  - One-and-done per-day lock (mirrors thunderbird_eod_brief.py) kills the
    Persistent=true catch-up double-fire.
  - Silence-on-zero: 0 decisions in 24h is not news — no send at all.
"""
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
LOCK_DIR = Path('/home/john/Thunderbird/OpsCenter')

# Split before any markdown header (# .. ###) that opens a dated decision entry,
# with an optional "Session " prefix before the date.
_ENTRY_SPLIT = re.compile(r'\n(?=#{1,3}\s+(?:Session\s+)?\d{4}-\d{2}-\d{2})')
# Pull the date (+ optional time) out of that header line.
_ENTRY_HEAD = re.compile(
    r'^#{1,3}\s+(?:Session\s+)?(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?')


def _mt_date_str() -> str:
    try:
        import zoneinfo
        return datetime.now(tz=zoneinfo.ZoneInfo("America/Denver")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d")


def _lock_path(date_str: str) -> Path:
    return LOCK_DIR / f"hale_decision_rollup_sent_{date_str.replace('-', '')}.lock"


def _write_lock(date_str: str):
    p = _lock_path(date_str)
    p.write_text(json.dumps({"date": date_str, "sent_at": datetime.utcnow().isoformat()}))
    logging.info(f"decision-rollup send-lock written: {p}")


def tg(msg):
    # Routed through the single gate (C2 RECALIBRATION task 8, Commander
    # directive 2026-07-29). This used to hit the bot API directly.
    try:
        from core.comms.commander_channel import notify
        notify('ops', msg.splitlines()[0][:80] if msg.strip() else 'alert', msg,
               urgency='WINDOW', source=__name__)
    except Exception as e:
        logging.warning(f'notify() failed: {e}')


def count_recent(text: str, cutoff: datetime):
    """Return the list of decision entries with a header timestamp >= cutoff.

    Date-only headers (no time) are treated as 00:00:00 UTC of that date.
    Naive timestamps are assumed UTC (consistent with the log's convention).
    """
    entries = []
    for chunk in _ENTRY_SPLIT.split(text):
        m = _ENTRY_HEAD.match(chunk)
        if not m:
            continue
        date_part, time_part = m.group(1), m.group(2) or '00:00:00'
        try:
            ts = datetime.fromisoformat(f'{date_part}T{time_part}')
        except Exception:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue
        entries.append(chunk.strip())
    return entries


def main():
    if not DECISION_LOG.exists():
        logging.info(f'no decision log at {DECISION_LOG}')
        return

    date_str = _mt_date_str()
    if _lock_path(date_str).exists():
        logging.info(f'decision-rollup already sent for {date_str} — lock present, exiting')
        return

    text = DECISION_LOG.read_text(errors='ignore')
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    entries = count_recent(text, cutoff)
    n = len(entries)

    # Silence-on-zero: 0 decisions in 24h is not news — no send (mirrors the
    # credentials_health_check.py fix: don't page on "nothing happened").
    if n == 0:
        logging.info('0 decisions in last 24h — suppressing send (silence-on-zero)')
        return

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
    _write_lock(date_str)
    logging.info(f'rolled up {n} entries')


if __name__ == '__main__':
    main()
