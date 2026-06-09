"""Session startup hook for checking persona inboxes.

Wired into CLAUDE.md and OpsCenter startup to ensure personas see incoming
dissent/observations/alternatives on session open.
"""

import logging
from .rabbitmq_client import PersonaMessaging

log = logging.getLogger("session_startup")

def check_persona_inboxes(persona_name: str = None) -> dict:
    """Check all persona inboxes (or specific persona) on session startup.

    Args:
        persona_name: Optional specific persona to check. If None, check all.

    Returns:
        {"status": "ok", "personas_checked": N, "total_messages": N, "summary": {...}}
    """
    try:
        messaging = PersonaMessaging()

        if persona_name:
            personas = [persona_name]
        else:
            personas = ['sterling', 'dembe', 'reyes', 'dani', 'harlan', 'washington']

        summary = {}
        total_messages = 0

        for p in personas:
            inbox = messaging.consume(p)
            total_messages += len(inbox)

            if inbox:
                # Categorize by type
                dissent_msgs = [m for m in inbox if m.msg_type == 'dissent']
                obs_msgs = [m for m in inbox if m.msg_type == 'observation']
                alt_msgs = [m for m in inbox if m.msg_type == 'alternative']

                summary[p] = {
                    'total': len(inbox),
                    'dissent': len(dissent_msgs),
                    'observations': len(obs_msgs),
                    'alternatives': len(alt_msgs),
                    'messages': inbox
                }

                # Log critical dissents
                if dissent_msgs:
                    log.warning(f"⚠️  {p} has {len(dissent_msgs)} dissent message(s)")
                    for msg in dissent_msgs:
                        log.warning(f"   [{msg.message_id}] from {msg.from_persona}: {msg.content[:80]}")

        messaging.close()

        return {
            "status": "ok",
            "personas_checked": len(personas),
            "total_messages": total_messages,
            "summary": summary
        }

    except Exception as e:
        log.error(f"❌ Inbox check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def startup_persona_reporting():
    """Integrated startup routine: check inboxes and report to Hale.

    Called by: hale_session_startup() in OpsCenter/
    Output: Logged to morning brief as PERSONA_INBOX section
    """
    result = check_persona_inboxes()

    if result['status'] == 'ok' and result['total_messages'] > 0:
        return {
            'alert': 'PERSONA_MESSAGES_PENDING',
            'count': result['total_messages'],
            'detail': result['summary']
        }

    return None
