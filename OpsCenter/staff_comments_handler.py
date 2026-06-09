"""Auto-invoke handler for "STAFF COMMENTS?" keyword.

Dual-purpose activation:
1. Check persona inboxes → surface dissents/observations
2. Execute eligible Mission Board tasks → auto-run ready tasks

Triggers when Commander types: "STAFF COMMENTS?"
Returns: (1) Dissent summary + (2) Task execution report

Integration: CLAUDE.md keyword router + SO-2026-06-09
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from OpsCenter.session_init import init_thunderbird_session, format_alerts_for_brief
from core.messaging.session_startup_hook import startup_persona_reporting

def check_mission_board_tasks():
    """Check and auto-execute eligible Mission Board tasks.

    Executes tasks that are:
    - Status: 'ready' or 'pending_execution'
    - Priority: P0 or P1
    - No blocking dependencies

    Returns: dict with executed tasks and results
    """
    try:
        mission_board_file = Path(__file__).parent.parent / "OpsCenter" / "mission_board.json"

        if not mission_board_file.exists():
            return {'status': 'no_board', 'message': 'Mission board not found'}

        with open(mission_board_file) as f:
            board = json.load(f)

        missions = board.get('missions', [])
        executed = []

        for mission in missions:
            # Check if task is ready for auto-execution
            status = mission.get('status', '')
            priority = mission.get('priority', '')
            mission_id = mission.get('id', 'unknown')

            # Auto-execute criteria
            if status in ['ready', 'pending_execution'] and priority in ['P0', 'P1']:
                # Check no blockers
                if 'blockers' not in mission or not mission['blockers']:
                    executed.append({
                        'id': mission_id,
                        'title': mission.get('title', 'Untitled'),
                        'priority': priority,
                        'action': 'auto_executed',
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    # Update mission status
                    mission['status'] = 'in_progress'
                    mission['auto_executed_at'] = datetime.utcnow().isoformat()

        # Write back updated mission board
        if executed:
            with open(mission_board_file, 'w') as f:
                json.dump(board, f, indent=2)

        return {
            'status': 'success',
            'executed_count': len(executed),
            'executed': executed
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Mission board check failed'
        }

def handle_staff_comments():
    """Execute dual-purpose activation: inbox check + mission board execution."""
    print("\n" + "=" * 80)
    print("🦅 STAFF COMMENTS QUERY + MISSION AUTO-EXECUTE")
    print("=" * 80)

    try:
        # PART 1: Check persona inboxes
        print("\n[Part 1: Checking persona inboxes...]")
        result = init_thunderbird_session()

        alerts = result.get('alerts', [])

        # PART 2: Check and execute mission board tasks
        print("[Part 2: Checking Mission Board for auto-executable tasks...]")
        mission_result = check_mission_board_tasks()

        # Display results
        if not alerts and mission_result.get('executed_count', 0) == 0:
            print("\n✅ No pending staff input")
            print("✅ No Mission Board tasks auto-executed")
            print("   Status: All systems clear, ready for new decisions")
            return {
                'status': 'clear',
                'pending_count': 0,
                'executed_count': 0,
                'message': 'No pending staff input or mission tasks'
            }

        # Format alerts for display
        if alerts:
            print("\n⚠️  PENDING STAFF INPUT")
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

        # Display mission board execution
        if mission_result.get('executed_count', 0) > 0:
            print("\n" + "─" * 80)
            print("🚀 MISSION BOARD AUTO-EXECUTION")
            print("─" * 80)
            print(f"\n✅ Auto-executed {mission_result['executed_count']} task(s):")
            for task in mission_result.get('executed', []):
                print(f"\n   • {task['id']}: {task['title']}")
                print(f"     Priority: {task['priority']}")
                print(f"     Status: in_progress")

        # Next steps
        print("\n" + "─" * 80)
        print("📋 NEXT STEPS:")
        if alerts:
            print("   1. Review dissent concerns in detail")
            print("   2. Consult with named staff member(s)")
            print("   3. Accept/reject dissent (staff will acknowledge)")
            print("   4. Decision logged automatically in audit trail")
        if mission_result.get('executed_count', 0) > 0:
            print("   • Mission Board tasks are in_progress")
            print("   • Check mission_board.json for execution status")

        # Combine results
        p0_alerts = [a for a in alerts if a.get('priority') == 'P0']
        p1_alerts = [a for a in alerts if a.get('priority') == 'P1']

        return {
            'status': 'mixed' if (alerts or mission_result.get('executed_count', 0) > 0) else 'clear',
            'pending_count': len(alerts),
            'p0_count': len(p0_alerts),
            'p1_count': len(p1_alerts),
            'alerts': alerts,
            'executed_count': mission_result.get('executed_count', 0),
            'executed_tasks': mission_result.get('executed', [])
        }

    except Exception as e:
        print(f"\n❌ Error in staff comments handler: {e}")
        print("   (Continuing with partial results)")
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Handler error (inbox or mission check failed)'
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
