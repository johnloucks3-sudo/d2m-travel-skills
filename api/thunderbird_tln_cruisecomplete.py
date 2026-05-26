"""
TLNCruiseCompleteClient — CDP interface for TLN CruiseComplete portal.

TLN CruiseComplete is accessible via the Revelex/Travelport GDS integration
through TLN AgentUniverse. CDP via Chrome port 9222 is the access path
(same Cloudflare bypass pattern as Odysseus/MAG).

TLN membership confirmed. Credentials in Roboforms → D2M_TLN_CC_* keys in .env.vault.

Usage:
    with TLNCruiseCompleteClient() as client:
        tab = client.get_or_open_tln_tab()
        health = client.session_health()
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests

from api.thunderbird_cdp_lock import CDPSessionLock, CDPLockTimeout

logger = logging.getLogger(__name__)

OA_STATE_DIR = Path("/home/john/Thunderbird/oa_state")
CDP_LOCK_PATH = OA_STATE_DIR / "cdp_session.lock"
TLN_CC_HOST = "cruisecomplete.travelleaders.com"
SESSION_FILE = OA_STATE_DIR / "tln_cruisecomplete_session.json"


class TLNCruiseCompleteError(Exception):
    pass


class TLNCruiseCompleteClient:
    """CDP client for TLN CruiseComplete portal via live Chrome instance."""

    def __init__(self, chrome_port: int = 9222, lock_timeout: int = 30):
        self.base = f"http://localhost:{chrome_port}"
        self.lock_timeout = lock_timeout
        self._lock: Optional[CDPSessionLock] = None

    def __enter__(self):
        OA_STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = CDPSessionLock(CDP_LOCK_PATH, timeout=self.lock_timeout)
        self._lock.acquire()
        return self

    def __exit__(self, *args):
        if self._lock:
            self._lock.release()
        self._write_session_health()

    def _get_tabs(self) -> list[dict]:
        try:
            resp = requests.get(f"{self.base}/json", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise TLNCruiseCompleteError(f"Chrome CDP unreachable at {self.base}: {e}")

    def get_tln_tab(self) -> dict:
        """Find TLN CruiseComplete tab, raise if not open."""
        tabs = self._get_tabs()
        for tab in tabs:
            if TLN_CC_HOST in tab.get("url", ""):
                logger.info("Found TLN CC tab: %s", tab.get("url"))
                return tab
        raise TLNCruiseCompleteError(
            f"No tab found for {TLN_CC_HOST}. "
            "Open Chrome to TLN CruiseComplete and ensure --remote-debugging-port=9222."
        )

    def get_or_open_tln_tab(self) -> dict:
        """Find TLN CC tab; if not open, create one."""
        try:
            return self.get_tln_tab()
        except TLNCruiseCompleteError:
            logger.info("No TLN CC tab found — opening new tab")
            return self._open_new_tab(f"https://{TLN_CC_HOST}/")

    def _open_new_tab(self, url: str) -> dict:
        # Chrome 80+ requires PUT (not GET) for /json/new
        try:
            resp = requests.put(f"{self.base}/json/new?{url}", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise TLNCruiseCompleteError(f"Failed to open new tab: {e}")

    def is_chrome_reachable(self) -> bool:
        try:
            requests.get(f"{self.base}/json/version", timeout=3)
            return True
        except requests.RequestException:
            return False

    def session_health(self) -> dict:
        """Return session health dict without writing to disk."""
        return {
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "chrome_reachable": self.is_chrome_reachable(),
            "host": TLN_CC_HOST,
        }

    def _write_session_health(self) -> None:
        try:
            health = self.session_health()
            SESSION_FILE.write_text(json.dumps(health, indent=2))
        except OSError as e:
            logger.warning("Could not write TLN session health: %s", e)
