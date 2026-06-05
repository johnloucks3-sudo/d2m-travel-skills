#!/usr/bin/env python3
"""
Sterling Validation — Supplier Lifecycle Management Operational Effectiveness
==============================================================================
Validates that all session keepalive and sentinel systems are operating correctly.
Called by Sterling during code review and by the morning brief health check.

Checks:
  1. Regent session keepalive — cookie freshness, timer next fire, log health
  2. Centrav session keepalive — cookie freshness, timer next fire, log health
  3. Perx session keepalive — cookie freshness, timer next fire, log health
  4. Site structure sentinel — state file, last run, log health
  5. Credentials health check — alert state, stale credentials
  6. Dead man switch — has each timer fired in the expected window?

Usage:
    python3 scripts/sterling_validate_lifecycle.py           # full validation
    python3 scripts/sterling_validate_lifecycle.py --report  # summary only, no checks
    python3 scripts/sterling_validate_lifecycle.py --alert   # send Telegram on failures

Output: JSON to OpsCenter/state/sterling_lifecycle_validation.json

Dreams2Memories Travel, LLC — Thunderbird Wing — Sterling Code 2026-06-04
"""
import json, logging, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
CREDS_DIR = THUNDERBIRD / "creds"
STATE_DIR = THUNDERBIRD / "OpsCenter" / "state"
LOG_DIR = THUNDERBIRD / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s STERLING %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "sterling_validation.log"), mode="a"),
    ],
)
log = logging.getLogger("sterling")

TIMERS = {
    "d2m-rssc-session-keepalive": {
        "expected_interval_h": 4,
        "tolerance_h": 1,
        "cookie_files": ["regent_cookies.json", "regent_cookies_oa.json"],
    },
    "d2m-centrav-session-keepalive": {
        "expected_interval_h": 1.5,
        "tolerance_h": 0.5,
        "cookie_files": ["centrav_cookies.json"],
    },
    "d2m-perx-session-keepalive": {
        "expected_interval_h": 6,
        "tolerance_h": 1,
        "cookie_files": ["perx_cookies.json"],
    },
    "d2m-portal-keepalive": {
        "expected_interval_h": 2,
        "tolerance_h": 1,
        "cookie_files": [
            "silversea_cookies.json", "seabourn_cookies.json",
            "windstar_cookies.json", "princess_cookies.json",
            "carnival_cookies.json", "kensington_cookies.json",
            "agentmax_cookies.json", "globus_cookies.json",
            "room_res_cookies.json", "agent_universe_cookies.json",
            "atlas_cookies.json", "explora_cookies.json",
        ],
    },
    "d2m-site-sentinel": {
        "expected_interval_h": 24,
        "tolerance_h": 4,
        "cookie_files": [],
    },
}


def check_timer(name: str, config: dict) -> dict:
    """Check a systemd timer's status and derive health."""
    result = {"timer": name, "active": False, "last_trigger": None, "next_trigger": None, "health": "unknown", "issues": []}

    try:
        out = subprocess.run(
            ["systemctl", "show", "--property=ActiveState,LastTriggerUSec,NextElapseUSec", f"{name}.timer"],
            capture_output=True, text=True, timeout=10
        )
        props = {}
        for line in out.stdout.strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v

        state = props.get("ActiveState", "inactive")
        result["active"] = (state == "active")

        last_str = props.get("LastTriggerUSec", "").replace("USec", "").strip()
        next_str = props.get("NextElapseUSec", "").replace("USec", "").strip()

        if last_str and last_str != "0":
            result["last_trigger"] = last_str

        if next_str and next_str != "0":
            result["next_trigger"] = next_str

        now = datetime.now(timezone.utc)
        if last_str and last_str != "0":
            last_dt = datetime.fromisoformat(last_str.replace(" ", "T"))
            hours_since = (now - last_dt).total_seconds() / 3600
            expected = config["expected_interval_h"]
            tolerance = config["tolerance_h"]
            if hours_since > expected + tolerance:
                result["health"] = "overdue"
                result["issues"].append(
                    f"Last fired {hours_since:.1f}h ago (expected ≤{expected + tolerance:.1f}h)"
                )
            else:
                result["health"] = "ok"
        else:
            result["health"] = "never_fired"
            result["issues"].append("Timer has never fired")

        for cf in config["cookie_files"]:
            cpath = CREDS_DIR / cf
            if cpath.exists():
                mtime = datetime.fromtimestamp(cpath.stat().st_mtime, tz=timezone.utc)
                hours = (now - mtime).total_seconds() / 3600
                if hours > config["expected_interval_h"] * 2:
                    result["issues"].append(f"{cf} stale: last modified {hours:.1f}h ago")
            else:
                result["issues"].append(f"{cf} missing")

    except Exception as e:
        result["health"] = "error"
        result["issues"].append(f"Check failed: {e}")

    if not result["issues"] and result["health"] != "error":
        result["health"] = "ok"
    elif result["health"] == "unknown":
        result["health"] = "degraded"

    return result


def check_credential_health() -> dict:
    """Read the last credentials health state."""
    state_file = STATE_DIR / "credentials_health.json"
    if not state_file.exists():
        return {"status": "no_data", "alerts": []}
    try:
        data = json.loads(state_file.read_text())
        return {
            "status": "ok",
            "checked_at": data.get("checked_at", "?"),
            "alerts": data.get("alerts", []),
            "client_alerts": data.get("client_affecting_alerts", []),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "alerts": []}


def check_sentinel_health() -> dict:
    """Read the last sentinel run state."""
    state_file = STATE_DIR / "site_sentinel_state.json"
    if not state_file.exists():
        return {"status": "no_data", "baselines": 0, "last_run": None}
    try:
        data = json.loads(state_file.read_text())
        history = data.get("history", [])
        last = history[-1] if history else None
        return {
            "status": "ok",
            "baselines": len(data.get("baselines", {})),
            "last_run": last.get("run_at") if last else None,
            "summary": last.get("summary") if last else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def validate() -> dict:
    """Run all validation checks."""
    log.info("=== Sterling Lifecycle Validation ===")

    timer_results = {}
    for name, config in TIMERS.items():
        timer_results[name] = check_timer(name, config)
        h = timer_results[name]["health"]
        log.info(f"  Timer {name}: {h}")

    cred_health = check_credential_health()
    sentinel_health = check_sentinel_health()

    overall_alerts = []
    for name, tr in timer_results.items():
        if tr["health"] != "ok":
            for issue in tr["issues"]:
                overall_alerts.append({"source": name, "issue": issue})

    for alert in cred_health.get("alerts", []):
        overall_alerts.append({"source": "credentials_health", "issue": f"{alert['name']}: {alert['reason']}"})

    if sentinel_health.get("status") not in ("ok", "no_data"):
        overall_alerts.append({"source": "site_sentinel", "issue": sentinel_health.get("error", "unknown")})

    health = "ok"
    if cred_health.get("client_alerts"):
        health = "client_alerts"
    if overall_alerts:
        health = "degraded"

    for a in overall_alerts:
        log.warning(f"  ALERT: [{a['source']}] {a['issue']}")

    result = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "timers": timer_results,
        "credential_health": cred_health,
        "sentinel_health": sentinel_health,
        "alerts": overall_alerts,
        "alert_count": len(overall_alerts),
    }

    out_path = STATE_DIR / "sterling_lifecycle_validation.json"
    out_path.write_text(json.dumps(result, indent=2))
    log.info(f"Validation written to {out_path}")
    log.info(f"Overall health: {health} ({len(overall_alerts)} alerts)")

    return result


def send_alert(result: dict):
    """Send Telegram alert if there are client-affecting failures."""
    if not result.get("alerts"):
        return
    try:
        sys.path.insert(0, str(THUNDERBIRD))
        from OpsCenter.thunderbird_telegram_gw import send_telegram_message
        lines = ["🔧 STERLING VALIDATION — Lifecycle health check\n"]
        alerts = result.get("alerts", [])
        for a in alerts[:5]:
            lines.append(f"  ⚠ {a['source']}: {a['issue']}")
        if len(alerts) > 5:
            lines.append(f"  ...and {len(alerts) - 5} more")
        send_telegram_message("\n".join(lines))
        log.info(f"Sterling alert sent ({len(alerts)} issues)")
    except Exception as e:
        log.warning(f"Sterling Telegram alert failed: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sterling lifecycle validation")
    parser.add_argument("--report", action="store_true", help="Read last report only")
    parser.add_argument("--alert", action="store_true", help="Send Telegram on failures")
    args = parser.parse_args()

    if args.report:
        path = STATE_DIR / "sterling_lifecycle_validation.json"
        if path.exists():
            print(path.read_text())
        else:
            print("No validation report yet — run without --report first")
        return

    result = validate()
    if args.alert and result.get("alerts"):
        send_alert(result)

    if result["health"] == "degraded":
        sys.exit(1)
    elif result["health"] == "client_alerts":
        sys.exit(2)


if __name__ == "__main__":
    main()
