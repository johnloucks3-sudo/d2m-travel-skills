"""Test session_init.py with dissent message queued.

Flow:
1. Publish a test dissent from Sterling
2. Run session_init.py
3. Verify it detects the pending dissent
4. Show alert formatting
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.messaging.rabbitmq_client import PersonaMessaging
from core.messaging.schemas import PersonaMessage

def test_with_dissent_queued():
    """Publish dissent, then run session init."""
    print("\n" + "=" * 70)
    print("TEST: session_init.py with Dissent Queued")
    print("=" * 70)

    # Step 1: Publish test dissent
    print("\n📍 STEP 1: Publish test dissent from Sterling")
    try:
        messaging = PersonaMessaging(use_production=False)  # localhost

        dissent = PersonaMessage.dissent(
            from_persona='sterling',
            to_personas=['commander', 'dembe', 'reyes', 'dani', 'harlan', 'washington'],
            concern="Test dissent for session_init verification. This message should be detected by Hale inbox check.",
            context={
                'decision_id': 'TEST-SESSION-INIT-001',
                'severity': 'INFO',
                'test': True
            }
        )

        msg_id = messaging.publish(dissent)
        print(f"✅ Dissent published: {msg_id}")
        print(f"   Routed to: 6 personas (broadcast)")
        messaging.close()

    except Exception as e:
        print(f"❌ Publish failed: {e}")
        return False

    # Step 2: Run session init
    print("\n📍 STEP 2: Run session_init.py (Hale startup check)")
    try:
        from OpsCenter.session_init import init_thunderbird_session, format_alerts_for_brief

        result = init_thunderbird_session()

        print(f"✅ Session init complete")
        print(f"   Status: {result['status']}")
        print(f"   Alerts: {len(result.get('alerts', []))}")

        # Step 3: Verify dissent detected
        print("\n📍 STEP 3: Verify dissent detected")
        persona_alerts = [a for a in result.get('alerts', []) if a['type'] == 'PERSONA_MESSAGES']

        if persona_alerts:
            for alert in persona_alerts:
                print(f"✅ Dissent detected!")
                print(f"   Priority: {alert['priority']}")
                print(f"   Count: {alert.get('count', 'N/A')}")
                print(f"   Message: {alert['message']}")

                if 'detail' in alert:
                    detail = alert['detail']
                    print(f"   Summary: {detail.get('summary', {})}")
        else:
            print(f"❌ No dissent detected (unexpected)")
            return False

        # Step 4: Format for morning brief
        print("\n📍 STEP 4: Format for morning brief")
        brief_section = format_alerts_for_brief(result.get('alerts', []))
        if brief_section:
            print("Brief section:\n")
            print(brief_section)
        else:
            print("(No alerts for brief)")

        return True

    except Exception as e:
        print(f"❌ Session init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_with_dissent_queued()

    print("\n" + "=" * 70)
    if success:
        print("✅ TEST PASSED — Dissent detected in session init")
    else:
        print("❌ TEST FAILED")
    print("=" * 70)

    sys.exit(0 if success else 1)
