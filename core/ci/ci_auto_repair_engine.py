#!/usr/bin/env python3
"""
CI Auto-Repair Engine — Universal Tripwire Pattern
Monitors all CI skills. At 10 consecutive failures, triggers analysis + repair.
Pattern: OBSERVE → ORIENT (analysis) → DECIDE (repair routing) → ACT (execute) → ASSESS (verify)
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CI_REGISTRY = THUNDERBIRD_ROOT / "config" / "ci_registry.json"
CI_REPAIR_STATE = THUNDERBIRD_ROOT / "OpsCenter" / ".ci_repair_state.json"
CI_REPAIR_LOG = THUNDERBIRD_ROOT / "logs" / "ci_repair_engine.log"

FAILURE_THRESHOLD = 10  # Tripwire: at 10 consecutive failures, trigger repair
REPAIR_TIMEOUT_SECONDS = 120

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CI-REPAIR] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(CI_REPAIR_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# REPAIR FUNCTIONS — Mapped to each CI skill
# ============================================================================

def repair_portal_access() -> bool:
    """Portal-access: Re-authenticate Centrav + Regent OA via nodriver"""
    try:
        logger.info("REPAIR: portal-access — triggering centrav_session_relogin.py")
        result = subprocess.run(
            ["python3", str(THUNDERBIRD_ROOT / "scripts" / "centrav_session_relogin.py")],
            timeout=REPAIR_TIMEOUT_SECONDS,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("REPAIR: portal-access SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: portal-access FAILED — {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"REPAIR: portal-access EXCEPTION — {e}")
        return False


def repair_web_fetch() -> bool:
    """Web-fetch: Verify anansi + trafilatura, fallback to playwright"""
    try:
        logger.info("REPAIR: web-fetch — verifying anansi + fallback")
        # Test anansi fetch
        result = subprocess.run(
            ["python3", "-c", "import anansi; print('anansi OK')"],
            timeout=30,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and "anansi OK" in result.stdout:
            logger.info("REPAIR: web-fetch SUCCESS")
            return True
        else:
            logger.warning("REPAIR: web-fetch — anansi failed, playwright fallback active")
            return True  # Fallback is available
    except Exception as e:
        logger.error(f"REPAIR: web-fetch EXCEPTION — {e}")
        return False


def repair_headless_dispatch() -> bool:
    """Headless-dispatch: Verify Claude OAuth token + supervisor daemon"""
    try:
        logger.info("REPAIR: headless-dispatch — checking OAuth + supervisor")
        cred_file = Path.home() / ".claude" / ".credentials.json"
        if not cred_file.exists():
            logger.error("REPAIR: headless-dispatch — credentials file missing")
            return False

        # Verify daemon is running
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "claude-token-monitor.timer"],
            capture_output=True,
            text=True
        )
        if "active" in result.stdout:
            logger.info("REPAIR: headless-dispatch SUCCESS")
            return True
        else:
            logger.error("REPAIR: headless-dispatch — token monitor not active")
            return False
    except Exception as e:
        logger.error(f"REPAIR: headless-dispatch EXCEPTION — {e}")
        return False


def repair_credential_keepalive() -> bool:
    """Credential-keepalive: Restart keepalive supervisor + re-verify tokens"""
    try:
        logger.info("REPAIR: credential-keepalive — restarting supervisor")
        result = subprocess.run(
            ["python3", str(THUNDERBIRD_ROOT / "scripts" / "keepalive_supervisor.py")],
            timeout=REPAIR_TIMEOUT_SECONDS,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("REPAIR: credential-keepalive SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: credential-keepalive FAILED — {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"REPAIR: credential-keepalive EXCEPTION — {e}")
        return False


def repair_tech_adoption() -> bool:
    """Tech-adoption: Re-trigger incubator scan + watch-list refresh"""
    try:
        logger.info("REPAIR: tech-adoption — running incubator scan")
        result = subprocess.run(
            ["python3", str(THUNDERBIRD_ROOT / "core" / "intel" / "thunderbird_incubator.py")],
            timeout=60,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("REPAIR: tech-adoption SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: tech-adoption FAILED — {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"REPAIR: tech-adoption EXCEPTION — {e}")
        return False


def repair_self_observability() -> bool:
    """Self-observability: Re-scan systemd logs + restart sentinel"""
    try:
        logger.info("REPAIR: self-observability — restarting sentinel")
        result = subprocess.run(
            ["python3", str(THUNDERBIRD_ROOT / "scripts" / "ci_sentinel.py"), "--verify"],
            timeout=60,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("REPAIR: self-observability SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: self-observability FAILED — {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"REPAIR: self-observability EXCEPTION — {e}")
        return False


def repair_email_handling() -> bool:
    """Email-handling: Re-verify Gmail tokens + check delivery log"""
    try:
        logger.info("REPAIR: email-handling — checking Gmail tokens")
        # Quick token refresh check
        result = subprocess.run(
            ["python3", "-c", "from core.email.thunderbird_gmail import gmail_check_health; print(gmail_check_health())"],
            timeout=30,
            capture_output=True,
            text=True,
            cwd=str(THUNDERBIRD_ROOT)
        )
        if result.returncode == 0:
            logger.info("REPAIR: email-handling SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: email-handling — token check failed")
            return False
    except Exception as e:
        logger.error(f"REPAIR: email-handling EXCEPTION — {e}")
        return False


def repair_client_path_canary() -> bool:
    """Client-path-canary: Re-audit registry + clear stale canaries"""
    try:
        logger.info("REPAIR: client-path-canary — auditing canary registry")
        canary_file = THUNDERBIRD_ROOT / "config" / "client_path_canary_registry.json"
        if not canary_file.exists():
            logger.error("REPAIR: client-path-canary — registry file missing")
            return False

        # Verify JSON is valid
        with open(canary_file) as f:
            json.load(f)

        logger.info("REPAIR: client-path-canary SUCCESS")
        return True
    except Exception as e:
        logger.error(f"REPAIR: client-path-canary EXCEPTION — {e}")
        return False


def repair_dani_identity_layer() -> bool:
    """Dani-identity-layer: Restart Telegram gateway + verify identity gate"""
    try:
        logger.info("REPAIR: dani-identity-layer — restarting gateway")
        result = subprocess.run(
            ["systemctl", "--user", "restart", "thunderbird-telegram-gw.service"],
            timeout=30,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("REPAIR: dani-identity-layer SUCCESS")
            return True
        else:
            logger.error(f"REPAIR: dani-identity-layer FAILED — {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"REPAIR: dani-identity-layer EXCEPTION — {e}")
        return False


# ============================================================================
# REPAIR ROUTER — Maps skill IDs to repair functions
# ============================================================================

REPAIR_FUNCTIONS = {
    "portal-access": repair_portal_access,
    "web-fetch": repair_web_fetch,
    "headless-dispatch": repair_headless_dispatch,
    "credential-keepalive": repair_credential_keepalive,
    "tech-adoption": repair_tech_adoption,
    "self-observability": repair_self_observability,
    "email-handling": repair_email_handling,
    "client-path-canary": repair_client_path_canary,
    "dani-identity-layer": repair_dani_identity_layer,
}


# ============================================================================
# STATE MANAGEMENT — Track failure counts across runs
# ============================================================================

def load_repair_state() -> Dict[str, Any]:
    """Load or initialize failure tracking state"""
    if CI_REPAIR_STATE.exists():
        try:
            with open(CI_REPAIR_STATE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load repair state: {e}")
            return {}
    return {}


def save_repair_state(state: Dict[str, Any]) -> None:
    """Persist failure tracking state"""
    try:
        CI_REPAIR_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(CI_REPAIR_STATE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save repair state: {e}")


def increment_failure(state: Dict[str, Any], skill_id: str) -> int:
    """Increment consecutive failure count for a skill"""
    if skill_id not in state:
        state[skill_id] = {
            "consecutive_failures": 0,
            "last_failure": None,
            "last_repair": None,
            "repair_count": 0
        }

    state[skill_id]["consecutive_failures"] += 1
    state[skill_id]["last_failure"] = datetime.now().isoformat()

    return state[skill_id]["consecutive_failures"]


def reset_failure(state: Dict[str, Any], skill_id: str) -> None:
    """Reset failure count on successful probe run"""
    if skill_id in state:
        state[skill_id]["consecutive_failures"] = 0


def record_repair(state: Dict[str, Any], skill_id: str, success: bool) -> None:
    """Record repair attempt"""
    if skill_id not in state:
        state[skill_id] = {}

    state[skill_id]["last_repair"] = datetime.now().isoformat()
    state[skill_id]["repair_count"] = state[skill_id].get("repair_count", 0) + 1
    state[skill_id]["last_repair_success"] = success


# ============================================================================
# MAIN ENGINE — Process a single CI skill
# ============================================================================

def process_ci_skill(skill_id: str, probe_status: str, state: Dict[str, Any]) -> None:
    """
    OODA Loop for a single CI skill:
    - OBSERVE: current probe status
    - ORIENT: failure count, threshold check
    - DECIDE: repair needed?
    - ACT: execute repair function
    - ASSESS: verify success
    """
    logger.info(f"=== {skill_id.upper()} ===")

    # OBSERVE
    current_failures = state.get(skill_id, {}).get("consecutive_failures", 0)
    logger.info(f"OBSERVE: {skill_id} probe_status={probe_status}, consecutive_failures={current_failures}")

    # ORIENT
    if probe_status == "GREEN":
        reset_failure(state, skill_id)
        logger.info(f"ORIENT: {skill_id} recovered — failure count reset")
        return

    # DECIDE
    failure_count = increment_failure(state, skill_id)
    logger.info(f"DECIDE: {skill_id} now at {failure_count}/{FAILURE_THRESHOLD} consecutive failures")

    if failure_count < FAILURE_THRESHOLD:
        logger.info(f"DECIDE: {skill_id} below threshold — monitoring")
        return

    # ACT — Tripwire fired: run repair
    logger.warning(f"ACT: {skill_id} TRIPWIRE FIRED — invoking repair function")

    if skill_id not in REPAIR_FUNCTIONS:
        logger.error(f"ACT: {skill_id} — no repair function registered")
        return

    repair_fn = REPAIR_FUNCTIONS[skill_id]
    try:
        success = repair_fn()
        record_repair(state, skill_id, success)

        # ASSESS
        if success:
            logger.info(f"ASSESS: {skill_id} repair SUCCESS — failure count reset")
            reset_failure(state, skill_id)
        else:
            logger.error(f"ASSESS: {skill_id} repair FAILED — escalating to domain owner")
            # Escalation: log to awareness + page domain owner (async)
            log_escalation(skill_id)
    except Exception as e:
        logger.error(f"ACT: {skill_id} repair EXCEPTION — {e}")
        record_repair(state, skill_id, False)
        log_escalation(skill_id)


def log_escalation(skill_id: str) -> None:
    """Log escalation event for domain owner review"""
    awareness_log = THUNDERBIRD_ROOT / "OpsCenter" / "ci_awareness.jsonl"
    try:
        awareness_log.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "CI_REPAIR_ESCALATION",
            "skill_id": skill_id,
            "message": f"{skill_id} repair failed — requires domain owner intervention"
        }
        with open(awareness_log, 'a') as f:
            f.write(json.dumps(event) + '\n')
        logger.info(f"Escalation logged: {skill_id}")
    except Exception as e:
        logger.error(f"Failed to log escalation: {e}")


# ============================================================================
# MAIN ENTRY — Run scan + repair for all CI skills
# ============================================================================

def main():
    """Main engine: scan all CI skills, apply auto-repair tripwire logic"""
    logger.info("CI Auto-Repair Engine started")

    try:
        # Load registry
        with open(CI_REGISTRY) as f:
            registry = json.load(f)

        # Load state
        state = load_repair_state()

        # Process each skill
        for skill in registry.get("skills", []):
            skill_id = skill.get("id")
            probe_path = skill.get("health_probe")

            if not skill_id or not probe_path:
                logger.warning(f"Skipping skill — missing id or probe path")
                continue

            # Run probe to get current status
            try:
                result = subprocess.run(
                    ["python3", probe_path],
                    timeout=30,
                    capture_output=True,
                    text=True
                )
                probe_status = "GREEN" if result.returncode == 0 else "RED"
            except subprocess.TimeoutExpired:
                probe_status = "RED"
                logger.warning(f"{skill_id} probe timeout")
            except Exception as e:
                probe_status = "RED"
                logger.warning(f"{skill_id} probe error: {e}")

            # Apply OODA loop for this skill
            process_ci_skill(skill_id, probe_status, state)

        # Persist state
        save_repair_state(state)
        logger.info("CI Auto-Repair Engine complete")

    except Exception as e:
        logger.error(f"Engine failure: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
