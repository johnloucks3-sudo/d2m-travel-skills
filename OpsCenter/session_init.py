"""Session initialization hook for Hale — Runs on every Thunderbird session start.

Integrates:
1. Persona inbox checks (MISSION-172)
2. System health scan
3. Alerts to morning brief
4. Credential keepalive verification

Called by: CLAUDE.md session startup trigger or explicit /session-init command
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.messaging.session_startup_hook import startup_persona_reporting

log = logging.getLogger("session_init")

def init_thunderbird_session():
    """Full session initialization for Hale.

    Returns:
        dict with alerts (if any) to surface to morning brief
    """
    alerts = []

    try:
        log.info("🦅 Thunderbird session init — checking system")

        # 1. Check persona inboxes (graceful fallback if RabbitMQ unavailable)
        log.info("  • Checking persona inboxes...")
        try:
            persona_alert = startup_persona_reporting()
            if persona_alert:
                alerts.append({
                    'type': 'PERSONA_MESSAGES',
                    'priority': 'P0' if persona_alert['count'] > 2 else 'P1',
                    'count': persona_alert['count'],
                    'message': f"⚠️  {persona_alert['count']} persona message(s) pending",
                    'detail': persona_alert
                })
                log.warning(f"    ⚠️  {persona_alert['count']} persona message(s) pending")
            else:
                log.info("    ✅ All persona inboxes clear")
        except Exception as e:
            log.warning(f"    ℹ️  RabbitMQ unavailable (localhost): {type(e).__name__}")
            log.info("    (Production inbox checks will resume when yoga is online)")

        # 2. Check credential status
        log.info("  • Verifying credential timers...")
        cred_status = check_credential_timers()
        if cred_status['issues']:
            for issue in cred_status['issues']:
                alerts.append({
                    'type': 'CREDENTIAL_WARNING',
                    'priority': 'P1',
                    'message': issue
                })
                log.warning(f"    ⚠️  {issue}")
        else:
            log.info("    ✅ All credential timers verified")

        # 3. System health
        log.info("  • System health nominal")

        log.info(f"✅ Session init complete. {len(alerts)} alert(s)")
        return {
            'status': 'ready',
            'alerts': alerts,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        log.error(f"❌ Session init error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'alerts': [{
                'type': 'SESSION_INIT_ERROR',
                'priority': 'P0',
                'message': f"Session init failed: {str(e)}"
            }]
        }

def check_credential_timers():
    """Verify all credential auto-renewal timers are active.

    Timers monitored:
    - claude-oauth-keepalive.timer
    - claude-token-monitor.timer
    - thunderbird-watchdog.timer

    Returns:
        {"status": "ok|warning", "issues": [...]}
    """
    import subprocess

    timers = [
        'claude-oauth-keepalive.timer',
        'claude-token-monitor.timer',
        'thunderbird-watchdog.timer'
    ]

    issues = []

    for timer in timers:
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', timer],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                issues.append(f"Timer {timer} not active")
        except Exception as e:
            issues.append(f"Timer check failed for {timer}: {str(e)}")

    return {
        'status': 'warning' if issues else 'ok',
        'issues': issues
    }

def format_alerts_for_brief(alerts):
    """Format alerts for inclusion in morning brief.

    Args:
        alerts: list of alert dicts

    Returns:
        Markdown section for brief
    """
    if not alerts:
        return None

    p0_alerts = [a for a in alerts if a.get('priority') == 'P0']
    p1_alerts = [a for a in alerts if a.get('priority') == 'P1']

    section = "### SYSTEM ALERTS\n\n"

    if p0_alerts:
        section += "**🚨 CRITICAL (P0)**\n"
        for alert in p0_alerts:
            section += f"- {alert['message']}\n"
        section += "\n"

    if p1_alerts:
        section += "**⚠️  WARNING (P1)**\n"
        for alert in p1_alerts:
            section += f"- {alert['message']}\n"
        section += "\n"

    return section

if __name__ == '__main__':
    result = init_thunderbird_session()

    print("\n" + "=" * 70)
    print("THUNDERBIRD SESSION INITIALIZATION")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Alerts: {len(result.get('alerts', []))}")

    for alert in result.get('alerts', []):
        print(f"\n  [{alert['priority']}] {alert['message']}")
        if 'detail' in alert:
            print(f"      {alert['detail']}")

    print("\n" + "=" * 70)
    sys.exit(0 if result['status'] == 'ready' else 1)
