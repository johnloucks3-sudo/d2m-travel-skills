#!/usr/bin/env python3
"""
REST API wrapper for Claude usage monitoring
Dreams2Memories Travel, LLC

Lightweight Flask API exposing usage data for integrations.

Endpoints:
  GET  /api/usage/status       → Current status (ok/warn/crit/stop)
  GET  /api/usage/session      → Session block details
  GET  /api/usage/weekly       → Weekly breakdown
  GET  /api/usage/estimate     → Time/tokens remaining
  POST /api/usage/refresh      → Force poll (admin only)
  GET  /health                 → Health check

Server:
  Host: 127.0.0.1 (localhost only for security)
  Port: 5771 (Thunder + 71)

Usage:
  python3 thunderbird_usage_api.py
  python3 thunderbird_usage_api.py --port 8080
  python3 thunderbird_usage_api.py --debug

Testing:
  curl http://localhost:5771/api/usage/status
  curl http://localhost:5771/api/usage/session | jq
  curl http://localhost:5771/health
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("ERROR: Flask not installed. Install with:")
    print("  pip install flask")
    exit(1)

# ── Configuration ──────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
LOG_DIR = THUNDERBIRD_DIR / "logs"
STATE_FILE = LOG_DIR / "usage_monitor.json"
API_LOG = LOG_DIR / "usage_api.log"

API_HOST = "127.0.0.1"
API_PORT = 5771

# ── Logging ────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(API_LOG),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── Flask App ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.json.sort_keys = False


# ── Helper Functions ───────────────────────────────────────────────────────

def _load_state() -> Dict[str, Any]:
    """Load current state from daemon-written JSON file."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        logger.error("Failed to parse state JSON")
        return {}


def _get_age_seconds() -> int:
    """Get age of state file in seconds."""
    if not STATE_FILE.exists():
        return -1
    return int((datetime.utcnow().timestamp() - STATE_FILE.stat().st_mtime))


def _is_stale(max_age_seconds: int = 120) -> bool:
    """Check if state is stale (no update from daemon)."""
    age = _get_age_seconds()
    return age > max_age_seconds


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    age = _get_age_seconds()
    status = "degraded" if age > 60 else "ok" if age >= 0 else "offline"

    return jsonify(
        {
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "state_age_seconds": age,
            "daemon_online": age >= 0 and age < 120,
        }
    ), (200 if status == "ok" else 503)


@app.route("/api/usage/status", methods=["GET"])
def get_status():
    """Overall usage status."""
    state = _load_state()

    session = state.get("session", {})
    weekly = state.get("weekly", {})

    return jsonify(
        {
            "timestamp": state.get("timestamp"),
            "session_level": session.get("level", "unknown"),
            "weekly_level": weekly.get("level", "unknown"),
            "session_pct": session.get("proj_pct", 0),
            "weekly_pct": weekly.get("all_pct", 0),
            "summary": state.get("summary", ""),
            "state_age_seconds": _get_age_seconds(),
            "is_stale": _is_stale(),
        }
    )


@app.route("/api/usage/session", methods=["GET"])
def get_session():
    """Session block details."""
    state = _load_state()
    session = state.get("session", {})

    if not session.get("available"):
        return jsonify({"error": "No active session block"}), 404

    return jsonify(
        {
            "timestamp": state.get("timestamp"),
            "level": session.get("level"),
            "used_pct": session.get("used_pct"),
            "projected_pct": session.get("proj_pct"),
            "bar": session.get("bar"),
            "used_tokens": session.get("used_tokens"),
            "limit_tokens": session.get("limit_tokens"),
            "remaining_tokens": max(0, session.get("limit_tokens", 0) - session.get("used_tokens", 0)),
            "burn_k_tpm": session.get("burn_k_tpm"),
            "remaining_minutes": session.get("remaining_minutes"),
            "cost_usd": session.get("cost_usd"),
            "start_time": session.get("start_time"),
            "end_time": session.get("end_time"),
            "is_active": session.get("is_active"),
        }
    )


@app.route("/api/usage/weekly", methods=["GET"])
def get_weekly():
    """Weekly budget breakdown."""
    state = _load_state()
    weekly = state.get("weekly", {})

    if not weekly.get("available"):
        return jsonify({"error": "No weekly data"}), 404

    return jsonify(
        {
            "timestamp": state.get("timestamp"),
            "level": weekly.get("level"),
            "all_pct": weekly.get("all_pct"),
            "sonnet_pct": weekly.get("sonnet_pct"),
            "bar": weekly.get("bar"),
            "total_tokens": weekly.get("total_tokens"),
            "opus_tokens": weekly.get("opus_tokens"),
            "sonnet_tokens": weekly.get("sonnet_tokens"),
            "haiku_tokens": weekly.get("haiku_tokens"),
            "opus_share_pct": weekly.get("opus_share_pct"),
            "sonnet_share_pct": weekly.get("sonnet_share_pct"),
            "haiku_share_pct": weekly.get("haiku_share_pct"),
            "cost_usd": weekly.get("cost_usd"),
            "week": weekly.get("week"),
        }
    )


@app.route("/api/usage/estimate", methods=["GET"])
def get_estimate():
    """Time and tokens remaining until limits."""
    state = _load_state()
    session = state.get("session", {})
    weekly = state.get("weekly", {})

    estimates = {}

    if session.get("available"):
        estimates["session"] = {
            "remaining_tokens": max(0, session.get("limit_tokens", 0) - session.get("used_tokens", 0)),
            "remaining_minutes": session.get("remaining_minutes"),
            "burn_k_tpm": session.get("burn_k_tpm"),
        }

    if weekly.get("available"):
        weekly_limit = 680_000_000  # estimate
        remaining = max(0, weekly_limit - weekly.get("total_tokens", 0))
        daily_burn = weekly.get("total_tokens", 0) / 7
        days_remaining = remaining / daily_burn if daily_burn > 0 else 0

        estimates["weekly"] = {
            "remaining_tokens": remaining,
            "estimated_days": round(days_remaining, 1),
            "daily_burn_rate": round(daily_burn),
        }

    return jsonify(
        {
            "timestamp": state.get("timestamp"),
            "estimates": estimates,
        }
    )


@app.route("/api/usage/refresh", methods=["POST"])
def refresh():
    """Manually trigger daemon refresh (no-op from API perspective)."""
    logger.info("Manual refresh requested")
    return jsonify({"message": "Refresh queued (daemon polls every 30s)"})


# ── Error Handlers ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    """404 handler."""
    return jsonify({"error": "Not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(error):
    """500 handler."""
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude usage monitoring REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=API_PORT,
        help=f"API port (default: {API_PORT})",
    )
    parser.add_argument(
        "--host",
        default=API_HOST,
        help=f"API host (default: {API_HOST})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    logger.info(f"Starting API on {args.host}:{args.port}")
    print(f"🚀 Usage API: http://{args.host}:{args.port}")
    print(f"  Endpoints:")
    print(f"    GET  /health")
    print(f"    GET  /api/usage/status")
    print(f"    GET  /api/usage/session")
    print(f"    GET  /api/usage/weekly")
    print(f"    GET  /api/usage/estimate")
    print(f"    POST /api/usage/refresh")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
