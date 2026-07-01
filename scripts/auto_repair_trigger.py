#!/usr/bin/env python3
"""
Auto-repair trigger: monitors bot failures and triggers repair when threshold (10 failures) is reached.
Routes via hale_notify: HALE/STERLING handle internally; Commander only sees client-affecting escalations.
"""
import json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
HEALTH_FILE = ROOT / "OpsCenter/supertimer_health.json"
REPAIR_LOG = ROOT / "OpsCenter/repair_trigger.log"
THRESHOLD = 10

# Bots that affect client-facing paths — escalate to Commander on unresolved failure
CLIENT_AFFECTING_BOTS = {"comms_bot", "client_bot"}

try:
    from core.notify.hale_notify import notify_hale, notify_sterling
except Exception:
    def notify_hale(bot, task, error, repaired=False, client_affecting=False):
        pass
    def notify_sterling(issue, detail):
        pass

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(msg)

def trigger_infra_repair():
    """Run infra repair sequence for TESS OAuth, portal, Chrome, etc."""
    log("TRIGGER: infra_bot at threshold — attempting repair")

    repair_cmds = [
        (f"{ROOT}/scripts/tess_token_reauth.py", "TESS OAuth re-auth"),
        (f"{ROOT}/scripts/portal_keepalive_repair.py", "Portal session repair"),
        (f"{ROOT}/scripts/chrome_cdp_health_repair.py", "Chrome CDP restart"),
    ]

    repaired = []
    for cmd, desc in repair_cmds:
        if Path(cmd).exists():
            try:
                result = subprocess.run(
                    ["/usr/bin/python3", cmd],
                    cwd=str(ROOT),
                    timeout=120,
                    capture_output=True,
                    text=True
                )
                status = "OK" if result.returncode == 0 else f"FAIL(rc={result.returncode})"
                log(f"  • {desc}: {status}")
                repaired.append((desc, result.returncode == 0))
            except subprocess.TimeoutExpired:
                log(f"  • {desc}: TIMEOUT")
                repaired.append((desc, False))
            except Exception as e:
                log(f"  • {desc}: ERROR — {e}")
                repaired.append((desc, False))

    return repaired

def trigger_intel_repair():
    """Run intel repair — typically credential refresh."""
    log("TRIGGER: intel_bot at threshold — attempting repair")

    cmd = f"{ROOT}/scripts/intel_scrapers_restart.py"
    if Path(cmd).exists():
        try:
            result = subprocess.run(
                ["/usr/bin/python3", cmd],
                cwd=str(ROOT),
                timeout=120,
                capture_output=True,
                text=True
            )
            status = "OK" if result.returncode == 0 else f"FAIL(rc={result.returncode})"
            log(f"  • Intel scrapers restart: {status}")
            return status == "OK"
        except subprocess.TimeoutExpired:
            log(f"  • Intel scrapers restart: TIMEOUT")
        except Exception as e:
            log(f"  • Intel scrapers restart: ERROR — {e}")
    return False

def reset_bot_failures(bot_name):
    """Reset consecutive_failures counter for a bot after repair attempt."""
    try:
        health = json.loads(HEALTH_FILE.read_text())
        if bot_name in health:
            health[bot_name]["consecutive_failures"] = 0
            HEALTH_FILE.write_text(json.dumps(health, indent=2))
            log(f"RESET: {bot_name} consecutive_failures → 0")
            return True
    except Exception as e:
        log(f"WARN: Could not reset {bot_name} — {e}")
    return False

def main():
    if not HEALTH_FILE.exists():
        log("SKIP: supertimer_health.json not found")
        return

    try:
        health = json.loads(HEALTH_FILE.read_text())
    except Exception as e:
        log(f"ERROR: Could not read health — {e}")
        return

    # Check for threshold breaches
    infra_failures = health.get("infra_bot", {}).get("consecutive_failures", 0)
    intel_failures = health.get("intel_bot", {}).get("consecutive_failures", 0)

    repairs = []

    if infra_failures >= THRESHOLD:
        repaired = trigger_infra_repair()
        reset_bot_failures("infra_bot")
        repairs.extend([(f"infra_bot ({infra_failures} failures)", r[1]) for r in repaired])

    if intel_failures >= THRESHOLD:
        success = trigger_intel_repair()
        reset_bot_failures("intel_bot")
        repairs.append((f"intel_bot ({intel_failures} failures)", success))

    if repairs:
        success_count = sum(1 for _, s in repairs if s)
        log(f"SUMMARY: {success_count}/{len(repairs)} repairs succeeded")

        for label, success in repairs:
            bot_name = label.split()[0]
            client = bot_name in CLIENT_AFFECTING_BOTS
            if success:
                notify_hale(bot_name, "auto-repair", f"{label} — repair succeeded",
                            repaired=True, client_affecting=False)
            else:
                # Repair failed — notify HALE and Sterling; escalate to Commander if client-affecting
                notify_sterling("repair-failed", f"{label} repair FAILED — manual intervention needed")
                notify_hale(bot_name, "auto-repair", f"{label} — repair FAILED",
                            repaired=False, client_affecting=client)
    else:
        log("STATUS: All bots below threshold — no repair needed")

if __name__ == "__main__":
    main()
