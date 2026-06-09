"""Auto-invoke handler for "STAFF COMMENTS?" keyword.

Purpose: Allow staff to comment on recent implementations and raise concerns.
Triggers when Commander types: "STAFF COMMENTS?"
Returns: Summary of all pending dissents/observations/alternatives

Staff can use this to:
- Raise dissents about recent changes (MISSION-172, auto-execution, etc.)
- Share observations and feedback
- Propose alternatives to recent implementations

Integration: CLAUDE.md keyword router + SO-2026-06-09
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from OpsCenter.session_init import init_thunderbird_session, format_alerts_for_brief
from core.messaging.session_startup_hook import startup_persona_reporting

def handle_staff_comments():
    """Check persona inboxes for staff feedback on implementations."""
    print("\n" + "=" * 80)
    print("🦅 STAFF COMMENTS QUERY")
    print("=" * 80)
    print("\nStaff input on recent implementations:\n")

    try:
        # Run full session init to check inboxes
        result = init_thunderbird_session()

        alerts = result.get('alerts', [])

        if not alerts:
            print("✅ No pending staff input")
            print("   All persona inboxes clear")
            print("   Status: Ready for new decisions")
            return {
                'status': 'clear',
                'pending_count': 0,
                'message': 'No pending staff input'
            }

        # Format alerts for display
        print("⚠️  PENDING STAFF INPUT")
        print("─" * 80)

        p0_alerts = [a for a in alerts if a.get('priority') == 'P0']
        p1_alerts = [a for a in alerts if a.get('priority') == 'P1']

        if p0_alerts:
            print("\n🚨 CRITICAL (P0) — Requires immediate attention:")
            for alert in p0_alerts:
                print(f"\n   Message: {alert['message']}")
                if 'detail' in alert and 'count' in alert['detail']:
                    count = alert['detail']['count']
                    print(f"   Count: {count} message(s)")
                    if 'summary' in alert['detail']:
                        summary = alert['detail']['summary']
                        print(f"   Breakdown:")
                        print(f"     - Dissents: {summary.get('dissent_count', 0)}")
                        print(f"     - Observations: {summary.get('observation_count', 0)}")
                        print(f"     - Alternatives: {summary.get('alternative_count', 0)}")

        if p1_alerts:
            print("\n⚠️  WARNING (P1) — Informational:")
            for alert in p1_alerts:
                print(f"   {alert['message']}")

        print("\n" + "─" * 80)
        print("📋 NEXT STEPS:")
        print("   1. Review staff concerns in detail")
        print("   2. Consult with named staff member(s)")
        print("   3. Address dissents (staff will acknowledge)")
        print("   4. Decision logged automatically in audit trail")

        return {
            'status': 'alerts',
            'pending_count': len(alerts),
            'p0_count': len(p0_alerts),
            'p1_count': len(p1_alerts),
            'alerts': alerts
        }

    except Exception as e:
        print(f"\n❌ Error checking staff comments: {e}")
        print("   (RabbitMQ may be offline — continuing with fallback)")
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Inbox check unavailable'
        }

def format_brief_section(result):
    """Format result as morning brief section."""
    if result['status'] == 'clear':
        return "### STAFF INPUT STATUS\n\n✅ All persona inboxes clear — ready for new decisions"

    if result['status'] == 'alerts':
        section = "### STAFF INPUT PENDING\n\n"
        if result['p0_count'] > 0:
            section += f"🚨 **{result['p0_count']} CRITICAL message(s)** — requires immediate response\n"
        if result['p1_count'] > 0:
            section += f"⚠️  **{result['p1_count']} informational message(s)** — for review\n"
        section += f"\nTotal pending: {result['pending_count']}\n"
        return section

    return "### STAFF INPUT CHECK\n\n⚠️  Status unavailable (inbox service offline)"

if __name__ == '__main__':
    result = handle_staff_comments()

    # For integration with keyword router, return JSON-serializable result
    import json
    print("\n" + "=" * 80)
    print("Status: " + result['status'].upper())
    print("=" * 80)

    sys.exit(0 if result['status'] != 'error' else 1)
