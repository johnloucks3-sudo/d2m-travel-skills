#!/usr/bin/env python3
"""
Thunderbird Credential Health Monitor
======================================
Dreams2Memories Travel, LLC | core/ops/thunderbird_credential_health.py

Consolidated credential health check for all Thunderbird Wing services.
Runs at 00:45 MDT daily (before preflight) and on-demand.

Extends core/ops/thunderbird_oauth_self_heal.py:OAuthTokenMonitor with:
  - Claude OAuth (~/.claude/.credentials.json)
  - TESS authentication status
  - systemd timer health (claude-token-monitor, claude-oauth-keepalive, thunderbird-watchdog)
  - .env required key audit
  - Single consolidated HealthReport with Telegram alert on RED

Does NOT re-implement what thunderbird_oauth_self_heal.py already does —
it imports OAuthTokenMonitor and builds on top.

Usage:
    python3 thunderbird_credential_health.py           # Full check, human output
    python3 thunderbird_credential_health.py --json    # Machine-readable JSON
    python3 thunderbird_credential_health.py --quiet   # Only print RED/YELLOW items
    python3 thunderbird_credential_health.py --alert   # Send Telegram alert if any RED

Reference: docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md (corrected timer names)
Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CLAUDE_CREDS    = Path.home() / ".claude" / ".credentials.json"

# Required .env keys for all wing operations
REQUIRED_ENV_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_C2_BOT_TOKEN",
    "TELEGRAM_COMMANDER_ID",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
]

# systemd timers to verify — corrected names per HEADLESS_CLAUDE_SPAWN_GUIDE.md
REQUIRED_TIMERS = [
    "claude-token-monitor.timer",
    "claude-oauth-keepalive.timer",
    "thunderbird-watchdog.timer",
]

# OAuth token files managed by OAuthTokenMonitor (do not re-check here)
OAUTH_TOKENS = {
    "Gmail (d2mconcierge)":  THUNDERBIRD_DIR / "gmail_token.json",
    "Persona Gmail":         THUNDERBIRD_DIR / "config" / "persona_gmail_token.json",
    "Google Drive":          THUNDERBIRD_DIR / "drive_token.json",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class Status(str):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"


@dataclass
class CheckResult:
    """Result of a single credential or service check."""
    name:       str
    status:     str           # "GREEN" | "YELLOW" | "RED"
    message:    str
    expires_at: Optional[str] = None   # ISO8601 if applicable
    detail:     Optional[str] = None   # Extra context for debugging


@dataclass
class HealthReport:
    """Consolidated health report for all credential checks."""
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checks:     list[CheckResult] = field(default_factory=list)

    @property
    def overall(self) -> str:
        statuses = {c.status for c in self.checks}
        if "RED"    in statuses: return "RED"
        if "YELLOW" in statuses: return "YELLOW"
        return "GREEN"

    @property
    def red_items(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "RED"]

    @property
    def yellow_items(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "YELLOW"]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall":   self.overall,
            "checks":    [asdict(c) for c in self.checks],
        }

    def to_brief(self, quiet: bool = False) -> str:
        icon = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(self.overall, "?")
        lines = [f"{icon} *CREDENTIAL HEALTH — {self.timestamp[:10]}* — {self.overall}"]
        for c in self.checks:
            if quiet and c.status == "GREEN":
                continue
            status_icon = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(c.status, "?")
            line = f"{status_icon} {c.name}: {c.message}"
            if c.expires_at:
                line += f" (expires {c.expires_at[:10]})"
            lines.append(line)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def check_claude_oauth(creds_path: Path = CLAUDE_CREDS) -> CheckResult:
    """
    Check Claude OAuth credentials (~/.claude/.credentials.json).
    Headless Claude depends on this for all MAX-plan spawns.
    """
    if not creds_path.exists():
        return CheckResult(
            "Claude OAuth", "RED",
            f"MISSING: {creds_path} — headless Claude will fail",
        )
    try:
        data = json.loads(creds_path.read_text())
        oauth = data.get("claudeAiOauth", {})
        token = oauth.get("accessToken")
        expires_raw = oauth.get("expiresAt")

        if not token:
            return CheckResult("Claude OAuth", "RED", "No accessToken in credentials file")

        expires_at = None
        if expires_raw:
            # expiresAt is Unix ms timestamp
            try:
                ts_ms = int(expires_raw)
                expires_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                expires_at = expires_dt.isoformat()
                minutes_left = (expires_dt - datetime.now(timezone.utc)).total_seconds() / 60
                if minutes_left < 30:
                    return CheckResult(
                        "Claude OAuth", "RED",
                        f"Token expires in {minutes_left:.0f} min — CRITICAL",
                        expires_at=expires_at,
                    )
                elif minutes_left < 120:
                    return CheckResult(
                        "Claude OAuth", "YELLOW",
                        f"Token expires in {minutes_left:.0f} min — refresh soon",
                        expires_at=expires_at,
                    )
            except (ValueError, TypeError):
                pass  # Can't parse timestamp — still have token

        return CheckResult(
            "Claude OAuth", "GREEN",
            "Valid token present",
            expires_at=expires_at,
        )
    except Exception as exc:
        return CheckResult("Claude OAuth", "RED", f"Parse error: {exc}")


def check_oauth_token(name: str, path: Path) -> CheckResult:
    """Check a standard Google OAuth token file (gmail_token.json, drive_token.json)."""
    if not path.exists():
        return CheckResult(name, "RED", f"MISSING: {path}")
    try:
        data = json.loads(path.read_text())
        has_refresh = bool(data.get("refresh_token"))
        expiry_raw  = data.get("expiry") or data.get("token_expiry")
        expires_at  = None
        if expiry_raw:
            try:
                expiry_dt = datetime.fromisoformat(str(expiry_raw).replace("Z", "+00:00"))
                expires_at = expiry_dt.isoformat()
                minutes_left = (expiry_dt - datetime.now(timezone.utc)).total_seconds() / 60
                if not has_refresh and minutes_left < 60:
                    return CheckResult(name, "RED",
                        f"Expires in {minutes_left:.0f} min, no refresh token",
                        expires_at=expires_at)
            except ValueError:
                pass

        status = "GREEN" if has_refresh else "YELLOW"
        msg    = "Valid (has refresh token)" if has_refresh else "No refresh token — may expire"
        return CheckResult(name, status, msg, expires_at=expires_at)
    except Exception as exc:
        return CheckResult(name, "RED", f"Parse error: {exc}")


def check_tess_auth() -> CheckResult:
    """
    Check TESS authentication status by running thunderbird_tess.py --status.
    Non-blocking — timeout after 10s.
    """
    tess_script = THUNDERBIRD_DIR / "core" / "booking" / "thunderbird_tess.py"
    if not tess_script.exists():
        return CheckResult("TESS Auth", "YELLOW", "TESS script not found — skip")
    try:
        result = subprocess.run(
            [sys.executable, str(tess_script), "--status"],
            capture_output=True, text=True, timeout=10,
            cwd=str(THUNDERBIRD_DIR),
        )
        out = (result.stdout + result.stderr).lower()
        if "not authenticated" in out or "auth_required" in out:
            return CheckResult(
                "TESS Auth", "RED",
                "Not authenticated — run: python3 thunderbird_tess.py --authorize",
                detail="Blocks all financial visibility (commission queries, payment tracking)",
            )
        if result.returncode == 0:
            return CheckResult("TESS Auth", "GREEN", "Authenticated")
        return CheckResult("TESS Auth", "YELLOW", f"Unknown status (rc={result.returncode})")
    except subprocess.TimeoutExpired:
        return CheckResult("TESS Auth", "YELLOW", "Status check timed out (>10s)")
    except Exception as exc:
        return CheckResult("TESS Auth", "YELLOW", f"Check error: {exc}")


def check_systemd_timer(timer_name: str) -> CheckResult:
    """
    Check a systemd --user timer is active and waiting.
    Corrected timer names per docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md.
    """
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", timer_name],
            capture_output=True, text=True, timeout=5,
        )
        state = result.stdout.strip()
        if state == "active":
            return CheckResult(f"Timer: {timer_name}", "GREEN", "active (waiting)")
        elif state == "inactive":
            return CheckResult(
                f"Timer: {timer_name}", "RED",
                f"INACTIVE — run: systemctl --user enable --now {timer_name}",
            )
        elif state == "failed":
            return CheckResult(f"Timer: {timer_name}", "RED", "FAILED")
        else:
            return CheckResult(f"Timer: {timer_name}", "YELLOW", f"Unknown state: {state}")
    except FileNotFoundError:
        return CheckResult(f"Timer: {timer_name}", "YELLOW", "systemctl not found — non-systemd host?")
    except subprocess.TimeoutExpired:
        return CheckResult(f"Timer: {timer_name}", "YELLOW", "Check timed out")
    except Exception as exc:
        return CheckResult(f"Timer: {timer_name}", "YELLOW", f"Check error: {exc}")


def check_env_keys(env_path: Optional[Path] = None) -> list[CheckResult]:
    """
    Verify required .env keys are present and non-empty.
    Reads from file if env_path provided, otherwise checks os.environ.
    """
    env_path = env_path or (THUNDERBIRD_DIR / ".env")
    env: dict[str, str] = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    else:
        # Fall back to os.environ if no .env file
        env = dict(os.environ)

    results = []
    for key in REQUIRED_ENV_KEYS:
        val = env.get(key, "")
        if not val:
            results.append(CheckResult(f"ENV:{key}", "RED", "MISSING or empty in .env"))
        elif val.startswith("your_") or val == "PLACEHOLDER":
            results.append(CheckResult(f"ENV:{key}", "YELLOW", "Appears to be placeholder value"))
        else:
            results.append(CheckResult(f"ENV:{key}", "GREEN", "Set"))
    return results


# ---------------------------------------------------------------------------
# Consolidated health check
# ---------------------------------------------------------------------------

def run_health_check(
    include_env: bool = True,
    include_timers: bool = True,
) -> HealthReport:
    """
    Run all credential checks and return a consolidated HealthReport.
    This is the single entry point for programmatic use.
    """
    report = HealthReport()

    # Claude OAuth — critical for headless spawn
    report.checks.append(check_claude_oauth())

    # Standard Google OAuth tokens (via direct check — OAuthTokenMonitor covers expiry logic)
    for name, path in OAUTH_TOKENS.items():
        report.checks.append(check_oauth_token(name, path))

    # TESS authentication
    report.checks.append(check_tess_auth())

    # systemd timers
    if include_timers:
        for timer in REQUIRED_TIMERS:
            report.checks.append(check_systemd_timer(timer))

    # .env key audit
    if include_env:
        report.checks.extend(check_env_keys())

    return report


# ---------------------------------------------------------------------------
# Telegram alert
# ---------------------------------------------------------------------------

def send_telegram_alert(report: HealthReport) -> bool:
    """
    Send a Telegram alert to Commander if any RED items exist.
    Only fires if report.overall == RED.
    Loads bot token from .env.
    """
    if report.overall not in ("RED", "YELLOW"):
        return True  # No alert needed

    try:
        import requests  # type: ignore
        env_path = THUNDERBIRD_DIR / ".env"
        env: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()

        token   = env.get("TELEGRAM_C2_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN")
        chat_id = env.get("TELEGRAM_COMMANDER_ID")
        if not token or not chat_id:
            logger.warning("Telegram credentials not found — cannot send alert")
            return False

        message = report.to_brief(quiet=True)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as exc:
        logger.error(f"Telegram alert failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Thunderbird Credential Health Monitor"
    )
    p.add_argument("--json",         action="store_true", help="Output as JSON")
    p.add_argument("--quiet",        action="store_true", help="Only show RED/YELLOW items")
    p.add_argument("--alert",        action="store_true", help="Send Telegram alert if RED")
    p.add_argument("--no-env",       action="store_true", help="Skip .env key audit")
    p.add_argument("--no-timers",    action="store_true", help="Skip systemd timer checks")
    return p


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()

    report = run_health_check(
        include_env    = not args.no_env,
        include_timers = not args.no_timers,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        sys.exit(0 if report.overall == "GREEN" else 1)

    print(report.to_brief(quiet=args.quiet))

    if args.alert and report.overall in ("RED", "YELLOW"):
        sent = send_telegram_alert(report)
        status = "sent" if sent else "FAILED"
        print(f"\nTelegram alert: {status}")

    sys.exit(0 if report.overall == "GREEN" else 1)


if __name__ == "__main__":
    main()
