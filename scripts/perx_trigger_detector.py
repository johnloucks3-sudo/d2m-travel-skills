#!/usr/bin/env python3
"""Detect Perx interline rate discounts >30% — queue to EOD report (no Telegram)."""
import json, os, logging, sys, re
from pathlib import Path
from datetime import datetime, timezone

LOG_PATH = Path('/home/john/Thunderbird/logs/perx_trigger_detector.log')
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# EOD queue — same file perx_intel_monitor uses, picked up by AM brief
EOD_QUEUE = Path('/home/john/Thunderbird/scripts/data/perx_eod_queue.json')

sys.path.insert(0, '/home/john/Thunderbird')


def sweep():
    try:
        from core.search import perplexity_search as ps
        if hasattr(ps, 'intel_sweep'):
            return ps.intel_sweep('Perx interline rate discount >30% airline')
        if hasattr(ps, 'search'):
            return ps.search('Perx interline crew rate discount airline today')
    except Exception as e:
        logging.debug(f'no pplx backend: {e}')
    return None


def _queue_for_eod(triggers: list[str], excerpt: str) -> None:
    """Append trigger signals to EOD queue for morning brief pickup."""
    EOD_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    queue = []
    if EOD_QUEUE.exists():
        try:
            queue = json.loads(EOD_QUEUE.read_text(encoding='utf-8'))
        except Exception:
            queue = []
    entry = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'source': 'perx_trigger_detector',
        'level': 'SIGNAL',
        'label': f'Perx discount signal(s): {", ".join(triggers[:4])}',
        'excerpt': excerpt[:400],
        'trigger_count': len(triggers),
    }
    queue.append(entry)
    EOD_QUEUE.write_text(json.dumps(queue, indent=2), encoding='utf-8')
    logging.info(f'Queued {len(triggers)} trigger(s) to EOD — no Telegram')


def main():
    result = sweep()
    if result is None:
        logging.info('no sweep result')
        return
    text = json.dumps(result) if not isinstance(result, str) else result
    triggers = []
    for m in re.finditer(r'(\d{2,3})\s*%\s*(?:off|discount|reduction)', text, re.I):
        pct = int(m.group(1))
        if pct >= 30:
            triggers.append(m.group(0))
    triggers = list(dict.fromkeys(triggers))
    if triggers:
        excerpt = text[:400].strip() if text else '(no text)'
        _queue_for_eod(triggers, excerpt)
    else:
        logging.info('no perx triggers ≥30%')


if __name__ == '__main__':
    main()
