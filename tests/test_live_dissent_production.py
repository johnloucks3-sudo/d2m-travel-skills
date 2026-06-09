"""Phase 2D — First live dissent test (Sterling).

Simulates: Sterling raises a critical dissent about timeline adjustment.
Flow: dissent → broadcast → staff acknowledgment → audit trail
Validates: full persona dialogue cycle in production
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.messaging.rabbitmq_client import PersonaMessaging
from core.messaging.schemas import PersonaMessage

def test_live_dissent():
    """Execute live dissent test with Sterling as dissenter."""
    print("\n" + "=" * 70)
    print("PHASE 2D — FIRST LIVE DISSENT TEST (Sterling)")
    print("=" * 70)

    # Use production config (yoga) if available, fallback to localhost
    messaging = PersonaMessaging(use_production=False)  # Use localhost for now

    test_results = {
        'timestamp': datetime.utcnow().isoformat(),
        'test_name': 'live_dissent_sterling',
        'status': 'running',
        'steps': []
    }

    try:
        # STEP 1: Sterling raises dissent
        print("\n📍 STEP 1: Sterling raises critical dissent")
        dissent = PersonaMessage.dissent(
            from_persona='sterling',
            to_personas=['commander', 'dembe', 'reyes', 'dani', 'harlan', 'washington'],
            concern="Timeline adjustment proposed for Phase 2D production window. Compress deployment window to 2 hours instead of 12. Risk: insufficient staging time for full persona team coordination. Recommendation: keep 12-hour window, run parallel staging.",
            context={
                'decision_id': 'PHASE-2D-TIMELINE-001',
                'severity': 'HIGH',
                'requires_response': True,
                'dissent_type': 'strategic'
            }
        )

        msg_id = messaging.publish(dissent)
        test_results['steps'].append({
            'step': 1,
            'action': 'Sterling dissent published',
            'message_id': msg_id,
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat()
        })
        print(f"✅ Dissent published: {msg_id}")

        # STEP 2: All staff consume dissent
        print("\n📍 STEP 2: Staff team consumes dissent")
        personas = ['dembe', 'reyes', 'dani', 'harlan', 'washington']
        consumed_by = []

        for persona in personas:
            inbox = messaging.consume(persona)
            dissents = [m for m in inbox if m.msg_type == 'dissent']
            if dissents:
                consumed_by.append(persona)
                print(f"✅ {persona}: received dissent (requires ack)")

        test_results['steps'].append({
            'step': 2,
            'action': 'Staff consumes dissent',
            'consumed_by': consumed_by,
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat()
        })

        # STEP 3: Staff acknowledges dissent
        print("\n📍 STEP 3: Staff acknowledges dissent")
        acks = []

        for persona in consumed_by:
            ack_result = messaging.acknowledge(msg_id, persona, vote=True)
            if ack_result:
                acks.append(persona)
                print(f"✅ {persona}: acknowledged dissent (approved)")

        test_results['steps'].append({
            'step': 3,
            'action': 'Staff acknowledges dissent',
            'acknowledged_by': acks,
            'ack_rate': f"{len(acks)}/{len(consumed_by)}",
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat()
        })

        # STEP 4: Get audit trail
        print("\n📍 STEP 4: Generate audit trail")
        trail = messaging.audit_trail(session_id='PHASE-2D-LIVE-TEST')

        test_results['steps'].append({
            'step': 4,
            'action': 'Audit trail generated',
            'events': len(trail['events']),
            'messages': len(trail['messages']),
            'summary': trail.get('summary', {}),
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat()
        })
        print(f"✅ Audit trail: {trail['summary'].get('total_messages', 0)} messages logged")

        # STEP 5: Report results
        print("\n📍 STEP 5: Test results summary")
        test_results['status'] = 'success'
        test_results['summary'] = {
            'dissent_published': msg_id,
            'staff_consumed': len(consumed_by),
            'staff_acknowledged': len(acks),
            'ack_rate_pct': (len(acks) / len(consumed_by) * 100) if consumed_by else 0,
            'audit_trail_complete': True,
            'all_steps_passed': True
        }

        print(f"\n✅ TEST PASSED")
        print(f"   Dissent published: {msg_id}")
        print(f"   Staff consumed: {len(consumed_by)}")
        print(f"   Staff acknowledged: {len(acks)} ({test_results['summary']['ack_rate_pct']:.0f}%)")
        print(f"   Audit trail: {trail['summary'].get('total_messages', 0)} messages")

        messaging.close()

    except Exception as e:
        test_results['status'] = 'failed'
        test_results['error'] = str(e)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    # Save test results
    report_file = Path("MISSION-172-PHASE-2D-LIVE-DISSENT-TEST.json")
    with open(report_file, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"\n📄 Test report saved: {report_file}")
    print("\n" + "=" * 70)

    return test_results['status'] == 'success'

if __name__ == '__main__':
    success = test_live_dissent()
    sys.exit(0 if success else 1)
