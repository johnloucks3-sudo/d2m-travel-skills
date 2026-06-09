"""Hale session startup hook — Check persona inboxes on session open.

Integrated into: hale_session_startup() or session init
Wired from: hale_cos.md MANDATORY_TURN_OPENING_PROTOCOL
Output: Alerts to morning brief if critical messages pending
"""

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.messaging.session_startup_hook import startup_persona_reporting

log = logging.getLogger("hale_startup")

def hale_session_startup():
    """Run on every Hale session open.

    Checks persona inboxes for pending dissent/observations.
    Alerts Commander if critical messages waiting.
    """
    try:
        log.info("🦅 Hale session startup — checking persona inboxes")

        alert = startup_persona_reporting()

        if alert:
            log.warning(f"⚠️  PERSONA MESSAGES PENDING")
            log.warning(f"    Count: {alert['count']}")
            log.warning(f"    Alert: {alert['alert']}")
            log.warning(f"    Details: {alert['detail']}")

            # Surface to morning brief
            return {
                'section': 'PERSONA_INBOX_ALERT',
                'priority': 'P0' if alert['count'] > 0 else 'P2',
                'message': f"{alert['count']} persona message(s) pending review",
                'detail': alert
            }
        else:
            log.info("✅ All persona inboxes clear")
            return None

    except Exception as e:
        log.error(f"❌ Session startup check failed: {e}")
        return {
            'section': 'PERSONA_INBOX_ERROR',
            'priority': 'P1',
            'message': f"Inbox check failed: {str(e)}",
            'error': True
        }

if __name__ == '__main__':
    result = hale_session_startup()
    if result:
        print(f"\n{result['section']}")
        print(f"Priority: {result['priority']}")
        print(f"Message: {result['message']}")
        if 'detail' in result:
            print(f"Detail: {result['detail']}")
