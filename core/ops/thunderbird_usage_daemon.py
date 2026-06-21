#!/usr/bin/env python3
"""
Real-time Claude Usage Monitoring Daemon
Dreams2Memories Travel, LLC

Polls ccusage every 30 seconds and writes JSON state file for integration
with OpsCenter, Telegram alerts, and REST API.

Usage:
  python3 thunderbird_usage_daemon.py                  # start daemon
  python3 thunderbird_usage_daemon.py --poll-interval 60  # custom interval

Signals:
  SIGTERM / SIGINT → graceful shutdown

Logging:
  File: /home/john/Thunderbird/logs/usage_daemon.log
  State: /home/john/Thunderbird/logs/usage_monitor.json
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from subprocess import run, PIPE, TimeoutExpired
from typing import Optional, Dict, Any

# ── Configuration ──────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
LOG_DIR = THUNDERBIRD_DIR / "logs"
OUTPUT_FILE = LOG_DIR / "usage_monitor.json"
DAEMON_LOG = LOG_DIR / "usage_daemon.log"

# Limits from Max Plan
SESSION_LIMIT = 59_826_434
WEEKLY_LIMIT_ALL = 680_000_000
WEEKLY_LIMIT_SONNET = 1_500_000_000

# Thresholds
WARN_PCT = 70
CRIT_PCT = 85
STOP_PCT = 95

# ── Logging Setup ──────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(DAEMON_LOG),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ── Utility Functions ──────────────────────────────────────────────────────

def _bar(pct: float, width: int = 20) -> str:
    """ASCII progress bar."""
    filled = min(int(pct / (100 / width)), width)
    return "█" * filled + "░" * (width - filled)


def _level_from_pct(pct: float) -> str:
    """Classify percentage into level."""
    if pct >= STOP_PCT:
        return "STOP"
    if pct >= CRIT_PCT:
        return "CRIT"
    if pct >= WARN_PCT:
        return "WARN"
    return "ok"


def _emoji(level: str) -> str:
    """Get emoji for level."""
    return {"ok": "✅", "WARN": "⚠️", "CRIT": "🔴", "STOP": "🚨"}.get(level, "ℹ️")


# ── Data Retrieval ────────────────────────────────────────────────────────

def get_active_block() -> Optional[Dict[str, Any]]:
    """Return currently active 5-hour billing block from ccusage."""
    try:
        result = run(
            ["ccusage", "blocks", "--json", "--since", "20260601"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"},
        )
        if result.returncode != 0:
            logger.warning(f"ccusage blocks failed: {result.stderr}")
            return None

        data = json.loads(result.stdout)
        blocks = data.get("blocks", [])

        # First try: find explicitly active block
        for b in reversed(blocks):
            if b.get("isActive") and not b.get("isGap"):
                return b

        # Fallback: most recent non-gap block
        for b in reversed(blocks):
            if not b.get("isGap"):
                return b

        return None
    except TimeoutExpired:
        logger.error("ccusage blocks timeout (15s)")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in blocks: {e}")
        return None
    except Exception as e:
        logger.error(f"get_active_block error: {e}")
        return None


def get_weekly_data() -> Optional[Dict[str, Any]]:
    """Return current week's token usage from ccusage."""
    try:
        result = run(
            ["ccusage", "weekly", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning(f"ccusage weekly failed: {result.stderr}")
            return None

        data = json.loads(result.stdout)
        weeks = data.get("weekly", [])

        if not weeks:
            logger.warning("No weekly data from ccusage")
            return None

        # Current week is last entry
        current = weeks[-1]
        total = current.get("totalTokens", 0)
        cost = current.get("totalCost", 0)

        # Per-model breakdown
        opus_tk = 0
        sonnet_tk = 0
        haiku_tk = 0
        for m in current.get("modelBreakdowns", []):
            name = m.get("modelName", "").lower()
            tok = (
                m.get("inputTokens", 0)
                + m.get("outputTokens", 0)
                + m.get("cacheCreationTokens", 0)
                + m.get("cacheReadInputTokens", 0)
            )
            if "opus" in name:
                opus_tk += tok
            elif "sonnet" in name:
                sonnet_tk += tok
            elif "haiku" in name:
                haiku_tk += tok

        return {
            "week": current.get("week", "?"),
            "total_tokens": total,
            "opus_tokens": opus_tk,
            "sonnet_tokens": sonnet_tk,
            "haiku_tokens": haiku_tk,
            "cost_usd": round(cost, 2),
            "all_pct": round(total / WEEKLY_LIMIT_ALL * 100, 1),
            "sonnet_pct": round(sonnet_tk / WEEKLY_LIMIT_SONNET * 100, 1),
            "opus_share_pct": round(opus_tk / total * 100, 1) if total else 0,
            "sonnet_share_pct": round(sonnet_tk / total * 100, 1) if total else 0,
            "haiku_share_pct": round(haiku_tk / total * 100, 1) if total else 0,
        }
    except TimeoutExpired:
        logger.error("ccusage weekly timeout (15s)")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in weekly: {e}")
        return None
    except Exception as e:
        logger.error(f"get_weekly_data error: {e}")
        return None


# ── Main Daemon Class ──────────────────────────────────────────────────────

class UsageDaemon:
    """Real-time usage monitoring daemon."""

    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self.running = True
        self.prev_alert_level = {}

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info(f"Daemon initialized (poll_interval={poll_interval}s)")

    def _handle_shutdown(self, signum, frame):
        """Handle termination signals gracefully."""
        logger.info("Shutdown signal received")
        self.running = False
        sys.exit(0)

    def _write_state(self, state: Dict[str, Any]) -> bool:
        """Write current state to JSON file."""
        try:
            OUTPUT_FILE.write_text(json.dumps(state, indent=2))
            return True
        except Exception as e:
            logger.error(f"Failed to write state: {e}")
            return False

    def _check_threshold_change(self, current_level: str, key: str) -> bool:
        """Return True if level changed to WARN/CRIT/STOP."""
        prev_level = self.prev_alert_level.get(key, "ok")
        self.prev_alert_level[key] = current_level

        # Alert if transitioned to alert state or escalated
        return (
            current_level in ("WARN", "CRIT", "STOP")
            and (prev_level == "ok" or prev_level != current_level)
        )

    def run(self):
        """Main daemon loop."""
        logger.info("Daemon started")
        poll_count = 0

        while self.running:
            try:
                poll_count += 1
                timestamp = datetime.utcnow().isoformat() + "Z"

                block = get_active_block()
                weekly = get_weekly_data()

                state = {
                    "timestamp": timestamp,
                    "poll_count": poll_count,
                    "session": self._process_block(block),
                    "weekly": self._process_weekly(weekly),
                    "summary": self._generate_summary(block, weekly),
                }

                # Write state file
                if self._write_state(state):
                    logger.debug(f"Poll #{poll_count}: state updated")
                else:
                    logger.error(f"Poll #{poll_count}: failed to write state")

                # Check for threshold alerts (TODO: integrate Telegram)
                if block:
                    session_level = state["session"].get("level", "ok")
                    if self._check_threshold_change(session_level, "session"):
                        logger.warning(f"Session threshold: {session_level}")

                if weekly:
                    weekly_level = state["weekly"].get("level", "ok")
                    if self._check_threshold_change(weekly_level, "weekly"):
                        logger.warning(f"Weekly threshold: {weekly_level}")

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Poll error: {e}", exc_info=True)
                time.sleep(self.poll_interval)

    def _process_block(self, block: Optional[Dict]) -> Dict[str, Any]:
        """Process session block into state dict."""
        if not block:
            return {"available": False}

        total = block.get("totalTokens", 0)
        proj = block.get("projection", {}) or {}
        proj_tk = proj.get("totalTokens", total)
        pct = round(total / SESSION_LIMIT * 100, 1)
        proj_pct = round(proj_tk / SESSION_LIMIT * 100, 1)
        burn = block.get("burnRate", {}) or {}
        burn_rpm = round(burn.get("tokensPerMinute", 0) / 1000, 1)
        remain = round(proj.get("remainingMinutes", 0))
        cost = round(block.get("costUSD", 0), 2)

        level = _level_from_pct(proj_pct)

        return {
            "available": True,
            "level": level,
            "used_pct": pct,
            "proj_pct": proj_pct,
            "bar": _bar(proj_pct),
            "used_tokens": total,
            "limit_tokens": SESSION_LIMIT,
            "burn_k_tpm": burn_rpm,
            "remaining_minutes": remain,
            "cost_usd": cost,
            "start_time": block.get("startTime", ""),
            "end_time": block.get("endTime", ""),
            "is_active": block.get("isActive", False),
        }

    def _process_weekly(self, weekly: Optional[Dict]) -> Dict[str, Any]:
        """Process weekly data into state dict."""
        if not weekly:
            return {"available": False}

        all_pct = weekly.get("all_pct", 0)
        sonnet_pct = weekly.get("sonnet_pct", 0)
        total_tok = weekly.get("total_tokens", 0)
        cost_wk = weekly.get("cost_usd", 0)

        level = _level_from_pct(all_pct)

        return {
            "available": True,
            "level": level,
            "all_pct": all_pct,
            "sonnet_pct": sonnet_pct,
            "bar": _bar(all_pct),
            "opus_share_pct": weekly.get("opus_share_pct", 0),
            "sonnet_share_pct": weekly.get("sonnet_share_pct", 0),
            "haiku_share_pct": weekly.get("haiku_share_pct", 0),
            "total_tokens": total_tok,
            "opus_tokens": weekly.get("opus_tokens", 0),
            "sonnet_tokens": weekly.get("sonnet_tokens", 0),
            "haiku_tokens": weekly.get("haiku_tokens", 0),
            "cost_usd": cost_wk,
            "week": weekly.get("week", ""),
        }

    def _generate_summary(self, block: Optional[Dict], weekly: Optional[Dict]) -> str:
        """Generate human-readable summary."""
        parts = []

        if block and block.get("projection"):
            proj_pct = round(
                block.get("projection", {}).get("totalTokens", 0) / SESSION_LIMIT * 100, 1
            )
            level = _level_from_pct(proj_pct)
            parts.append(
                f"Session: {_emoji(level)} {level} ({proj_pct}%) | "
                f"~{round(block.get('projection', {}).get('remainingMinutes', 0))} min"
            )

        if weekly:
            all_pct = weekly.get("all_pct", 0)
            level = _level_from_pct(all_pct)
            parts.append(f"Weekly: {_emoji(level)} {level} ({all_pct}%)")

        return " | ".join(parts) if parts else "No data"


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude usage monitoring daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    daemon = UsageDaemon(poll_interval=args.poll_interval)
    daemon.run()


if __name__ == "__main__":
    main()
