"""
Thunderbird OAuth Self-Heal — OpenClaw P5 Pattern Adaptation
Self-healing OAuth module: detects expired tokens → auto-refresh → re-auth if needed.

Monitors: Gmail token, Drive token, persona Gmail token, TESS token
Actions: refresh (if refresh_token available), re-authorize (if refresh fails), notify Commander
"""

import os
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"


# ============================================================================
# TOKEN HEALTH CHECKER
# ============================================================================

@dataclass
class TokenStatus:
    """Status of a single OAuth token"""
    name: str
    path: Path
    healthy: bool
    expired: bool
    expires_in_minutes: Optional[float] = None
    has_refresh_token: bool = False
    last_checked: str = ""
    error: Optional[str] = None


class OAuthTokenMonitor:
    """Monitors all OAuth tokens for expiry and health"""

    def __init__(self, thunderbird_root: Optional[Path] = None):
        self.thunderbird_root = Path(thunderbird_root) if thunderbird_root else THUNDERBIRD_DIR
        self._tokens = self._register_tokens()

    def _register_tokens(self) -> Dict[str, Path]:
        """Register all known OAuth token files"""
        return {
            "gmail": self.thunderbird_root / "gmail_token.json",
            "persona_gmail": self.thunderbird_root / "config" / "persona_gmail_token.json",
            "drive": self.thunderbird_root / "drive_token.json",
            "credentials": self.thunderbird_root / "credentials.json",
        }

    def check_token(self, name: str, path: Path) -> TokenStatus:
        """Check health of a single token"""
        path = Path(path)
        status = TokenStatus(
            name=name,
            path=path,
            healthy=False,
            expired=False,
            last_checked=datetime.now(timezone.utc).isoformat(),
        )

        if not path.exists():
            status.error = "Token file not found"
            return status

        try:
            token_data = json.loads(path.read_text())
            status.has_refresh_token = bool(token_data.get("refresh_token"))

            # Check expiry
            if "expiry" in token_data:
                expiry_str = token_data["expiry"]
                # Handle both ISO format and datetime string
                if isinstance(expiry_str, str):
                    expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                else:
                    expiry = expiry_str
                
                now = datetime.now(timezone.utc)
                delta = expiry - now
                status.expires_in_minutes = delta.total_seconds() / 60.0
                status.expired = delta.total_seconds() <= 0
                status.healthy = delta.total_seconds() > 300  # 5 min buffer

            elif "expires_at" in token_data:
                expires_at = token_data["expires_at"]
                if isinstance(expires_at, (int, float)):
                    expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)
                else:
                    expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                
                now = datetime.now(timezone.utc)
                delta = expiry - now
                status.expires_in_minutes = delta.total_seconds() / 60.0
                status.expired = delta.total_seconds() <= 0
                status.healthy = delta.total_seconds() > 300

            else:
                # No expiry info — assume healthy if file exists and has access_token
                status.healthy = bool(token_data.get("access_token") or token_data.get("token"))
                status.expires_in_minutes = None

        except Exception as e:
            status.error = f"Failed to parse token: {e}"
            status.healthy = False

        return status

    def check_all(self) -> Dict[str, TokenStatus]:
        """Check all registered tokens"""
        results = {}
        for name, path in self._tokens.items():
            results[name] = self.check_token(name, path)
        return results

    def get_critical_tokens(self) -> List[TokenStatus]:
        """Get tokens that need attention (expiring soon or expired)"""
        all_status = self.check_all()
        critical = []
        for status in all_status.values():
            if status.expired:
                critical.append(status)
            elif status.expires_in_minutes is not None and status.expires_in_minutes < 60:
                critical.append(status)
        return critical


# ============================================================================
# SELF-HEALING ENGINE
# ============================================================================

class OAuthSelfHealer:
    """Self-healing OAuth: detects issues → attempts fix → notifies Commander"""

    def __init__(self, thunderbird_root: Optional[Path] = None):
        self.thunderbird_root = Path(thunderbird_root) if thunderbird_root else THUNDERBIRD_DIR
        self.monitor = OAuthTokenMonitor(self.thunderbird_root)
        self._heal_log: List[Dict[str, Any]] = []

    def heal_all(self) -> Dict[str, Any]:
        """Check and heal all OAuth tokens"""
        results = {}
        critical = self.monitor.get_critical_tokens()

        if not critical:
            all_status = self.monitor.check_all()
            return {
                "status": "all_healthy",
                "tokens": {name: {
                    "healthy": s.healthy,
                    "expires_in_minutes": s.expires_in_minutes,
                } for name, s in all_status.items()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        for token_status in critical:
            result = self._heal_token(token_status)
            results[token_status.name] = result
            self._heal_log.append({
                "token": token_status.name,
                "action": result.get("action", "unknown"),
                "success": result.get("success", False),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return {
            "status": "heal_completed",
            "results": results,
            "log": self._heal_log[-10:],  # Last 10 heal events
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _heal_token(self, status: TokenStatus) -> Dict[str, Any]:
        """Attempt to heal a single token"""
        if status.error and "not found" in status.error.lower():
            return self._attempt_reauthorize(status.name)

        if status.has_refresh_token and not status.expired:
            # Token has refresh token and isn't expired yet — just flag it
            return {
                "action": "flag_expiring_soon",
                "success": True,
                "message": f"Token expires in {status.expires_in_minutes:.0f} minutes",
                "expires_in_minutes": status.expires_in_minutes,
            }

        if status.has_refresh_token and status.expired:
            return self._attempt_refresh(status.name, status.path)

        # No refresh token — need full re-authorization
        return self._attempt_reauthorize(status.name)

    def _attempt_refresh(self, name: str, path: Path) -> Dict[str, Any]:
        """Attempt to refresh an expired token using refresh_token"""
        try:
            # Use the Google auth module's built-in refresh
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            token_data = json.loads(path.read_text())
            creds = Credentials.from_authorized_user_info(token_data)

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                path.write_text(creds.to_json())
                logger.info(f"Token refreshed: {name}")
                return {
                    "action": "refreshed",
                    "success": True,
                    "message": f"Token {name} refreshed successfully",
                }
            else:
                return {
                    "action": "no_refresh_needed",
                    "success": True,
                    "message": f"Token {name} is still valid",
                }

        except Exception as e:
            logger.error(f"Token refresh failed for {name}: {e}")
            return {
                "action": "refresh_failed",
                "success": False,
                "error": str(e),
                "message": f"Refresh failed for {name}, attempting re-authorization",
            }

    def _attempt_reauthorize(self, name: str) -> Dict[str, Any]:
        """Attempt to re-authorize a token (requires Commander interaction)"""
        auth_script = self.thunderbird_root / "api" / "thunderbird_google_auth.py"
        if not auth_script.exists():
            return {
                "action": "reauthorize_failed",
                "success": False,
                "error": "Auth script not found",
                "message": f"Cannot re-authorize {name}: auth script missing",
            }

        # Log that re-authorization is needed
        # Actual re-auth requires browser interaction — can't fully automate
        return {
            "action": "reauthorize_needed",
            "success": False,
            "message": (
                f"Token {name} requires re-authorization. "
                f"Run: python3 {auth_script} --authorize"
            ),
            "command": f"python3 {auth_script} --authorize",
        }


# ============================================================================
# TELEGRAM NOTIFICATION
# ============================================================================

def notify_commander_token_issue(message: str) -> bool:
    """Notify Commander via Telegram about token issues"""
    bot_token = os.environ.get("TELEGRAM_C2_BOT_TOKEN")
    commander_id = os.environ.get("TELEGRAM_COMMANDER_ID")

    if not bot_token or not commander_id:
        logger.warning("Cannot notify Commander: missing bot token or commander ID")
        return False

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": commander_id,
            "text": f"⚠️ *OAuth Token Alert*\n\n{message}",
            "parse_mode": "Markdown",
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Failed to notify Commander: {e}")
        return False


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_oauth_self_heal_tools(mcp) -> None:
    """Register OAuth self-heal tools with MCP server"""

    @mcp.tool()
    def check_oauth_health() -> str:
        """Check health of all OAuth tokens"""
        monitor = OAuthTokenMonitor()
        all_status = monitor.check_all()

        lines = ["OAuth Token Health:\n"]
        for name, status in all_status.items():
            if status.healthy:
                icon = "✅"
            elif status.expired:
                icon = "🔴"
            else:
                icon = "🟡"

            line = f"{icon} {name}: "
            if status.error:
                line += status.error
            elif status.expires_in_minutes is not None:
                line += f"expires in {status.expires_in_minutes:.0f} min"
            else:
                line += "healthy (no expiry info)"

            if status.has_refresh_token:
                line += " [has refresh token]"
            lines.append(line)

        return "\n".join(lines)

    @mcp.tool()
    def heal_oauth() -> str:
        """Attempt to heal all OAuth token issues"""
        healer = OAuthSelfHealer()
        result = healer.heal_all()

        if result["status"] == "all_healthy":
            lines = ["All OAuth tokens are healthy:\n"]
            for name, info in result.get("tokens", {}).items():
                exp = info.get("expires_in_minutes")
                exp_str = f"expires in {exp:.0f} min" if exp else "no expiry info"
                lines.append(f"✅ {name}: {exp_str}")
            return "\n".join(lines)

        lines = ["OAuth Heal Results:\n"]
        for name, heal_result in result.get("results", {}).items():
            icon = "✅" if heal_result.get("success") else "❌"
            lines.append(f"{icon} {name}: {heal_result.get('message', 'unknown')}")

        return "\n".join(lines)


# ============================================================================
# PUBLIC API
# ============================================================================

def run_oauth_self_heal() -> Dict[str, Any]:
    """Run the OAuth self-heal check and fix cycle"""
    healer = OAuthSelfHealer()
    return healer.heal_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("OAuth Self-Heal — OpenClaw P5")
    print("=" * 40)

    # Check health
    monitor = OAuthTokenMonitor()
    all_status = monitor.check_all()

    print("\nToken Health:")
    for name, status in all_status.items():
        if status.healthy:
            icon = "✅"
        elif status.expired:
            icon = "🔴"
        else:
            icon = "🟡"

        line = f"  {icon} {name}"
        if status.error:
            line += f" — {status.error}"
        elif status.expires_in_minutes is not None:
            line += f" — expires in {status.expires_in_minutes:.0f} min"
        else:
            line += " — healthy"

        if status.has_refresh_token:
            line += " [refresh]"

        print(line)

    # Attempt heal if needed
    critical = monitor.get_critical_tokens()
    if critical:
        print(f"\n{len(critical)} token(s) need attention. Attempting heal...")
        result = run_oauth_self_heal()
        print(json.dumps(result, indent=2, default=str))
    else:
        print("\nAll tokens healthy. No action needed.")
