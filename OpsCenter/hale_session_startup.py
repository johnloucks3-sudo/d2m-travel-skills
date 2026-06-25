"""Hale session startup hook — Load inter-Hale state + check persona inboxes on session open.

Integrated into: hale_session_startup() or session init
Wired from: hale_cos.md MANDATORY_TURN_OPENING_PROTOCOL + HALE BUS CI (SO-2026-06-24)
Output: HALE BUS state loaded first, then persona inbox alerts surface to morning brief
"""

import logging
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hale_bus.hale_bus_read import load_bus_at_startup
from core.messaging.session_startup_hook import startup_persona_reporting

log = logging.getLogger("hale_startup")

def hale_session_startup():
    """Run on every Hale session open.

    L1 PRIORITY: Load inter-Hale state from HALE BUS (MANDATORY per SO-2026-06-24)
    L2: Check persona inboxes for pending dissent/observations.
    L3: Alert Commander if critical messages waiting.
    """
    try:
        # L1: HALE BUS load — FIRST operation
        instance_type = os.getenv("HALE_INSTANCE", "claude_code")
        log.info(f"⚡ HALE BUS load at startup (instance: {instance_type})")

        bus_state = load_bus_at_startup(instance_type)
        if bus_state:
            log.info(f"✅ Inter-Hale state loaded: {len(bus_state.get('hale_instances', {}))} instances")
            # Log critical directives if present
            directives = bus_state.get('critical_state', {}).get('commander_directives', [])
            if directives:
                log.warning(f"🔴 {len(directives)} critical directive(s) from inter-Hale state")

        # L2: Persona inbox check
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
