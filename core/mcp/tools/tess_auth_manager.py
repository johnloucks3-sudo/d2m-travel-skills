"""
TESS Auth Manager — lightweight token health check and refresh utility.

Standalone wrapper around TESSAuth for use by cron jobs, monitoring scripts,
and M-041 dossier auto-updater without importing the full TESS module.

Usage:
    from core.mcp.tools.tess_auth_manager import TESSAuthManager
    mgr = TESSAuthManager()
    if not mgr.is_valid():
        print("TESS token expired — run: python3 thunderbird_tess.py --keepalive")
    token = mgr.get_token()   # returns access_token string or None

CLI:
    python3 tess_auth_manager.py --check      # exit 0 if valid, 1 if expired
    python3 tess_auth_manager.py --refresh    # attempt keepalive refresh
    python3 tess_auth_manager.py --status     # human-readable status
"""
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

THUNDERBIRD = Path("/home/john/Thunderbird")
TOKEN_FILE = THUNDERBIRD / "tess_token.json"
EXPIRY_BUFFER_SECONDS = 300  # treat token as expired 5 min early


class TESSAuthManager:
    """Read-only view of the TESS token file with expiry logic."""

    def __init__(self, token_file: Path = TOKEN_FILE):
        self._file = token_file
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            try:
                self._data = json.loads(self._file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("tess_auth_manager: token file read error: %s", e)
                self._data = {}

    def is_valid(self) -> bool:
        """Return True if token exists and has not expired (with 5-min buffer)."""
        if not self._data:
            return False
        token = self._data.get("access_token") or self._data.get("token")
        if not token:
            return False
        expires_at = self._data.get("expires_at")
        if expires_at is None:
            return bool(token)
        try:
            return float(expires_at) - EXPIRY_BUFFER_SECONDS > time.time()
        except (TypeError, ValueError):
            return False

    def get_token(self) -> str | None:
        """Return access_token string if valid, else None."""
        if self.is_valid():
            return self._data.get("access_token") or self._data.get("token")
        return None

    def seconds_until_expiry(self) -> float | None:
        """Return seconds until token expires, or None if no expiry info."""
        expires_at = self._data.get("expires_at")
        if expires_at is None:
            return None
        try:
            return max(0.0, float(expires_at) - time.time())
        except (TypeError, ValueError):
            return None

    def status_dict(self) -> dict:
        """Return a structured status summary."""
        sec = self.seconds_until_expiry()
        return {
            "valid": self.is_valid(),
            "token_present": bool(self._data.get("access_token") or self._data.get("token")),
            "source": self._data.get("source", "unknown"),
            "user_id": self._data.get("userID"),
            "company_id": self._data.get("company_id"),
            "seconds_until_expiry": round(sec) if sec is not None else None,
            "hours_until_expiry": round(sec / 3600, 2) if sec is not None else None,
            "token_file": str(self._file),
            "file_exists": self._file.exists(),
        }

    def refresh(self) -> bool:
        """Attempt a keepalive refresh via thunderbird_tess TESSAuth.
        Returns True if refresh succeeded.
        """
        try:
            import sys
            sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
            from thunderbird_tess import TESSAuth  # type: ignore
            auth = TESSAuth()
            if auth.is_authenticated:
                refreshed = auth.refresh_token()
                if refreshed:
                    self._load()
                    return self.is_valid()
            return False
        except Exception as e:
            logger.error("tess_auth_manager: refresh failed: %s", e)
            return False


def get_tess_token() -> str | None:
    """Convenience function — returns valid TESS access token or None."""
    return TESSAuthManager().get_token()


def _cli() -> None:
    import argparse, sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="TESS Auth Manager CLI")
    parser.add_argument("--check", action="store_true", help="Exit 0 if token valid, 1 if expired")
    parser.add_argument("--refresh", action="store_true", help="Attempt keepalive token refresh")
    parser.add_argument("--status", action="store_true", help="Print status JSON")
    args = parser.parse_args()

    mgr = TESSAuthManager()

    if args.status or not (args.check or args.refresh):
        print(json.dumps(mgr.status_dict(), indent=2))

    if args.check:
        if mgr.is_valid():
            sec = mgr.seconds_until_expiry()
            hrs = f"{sec/3600:.1f}h" if sec else "unknown"
            print(f"VALID — expires in {hrs}")
            sys.exit(0)
        else:
            print("EXPIRED — run: python3 thunderbird_tess.py --keepalive")
            sys.exit(1)

    if args.refresh:
        print("Attempting refresh...")
        ok = mgr.refresh()
        if ok:
            print("Refresh succeeded.")
            sys.exit(0)
        else:
            print("Refresh failed — re-inject token manually.")
            sys.exit(1)


if __name__ == "__main__":
    _cli()
