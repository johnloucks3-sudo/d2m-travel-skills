"""
MAGSuiteClient — Chrome DevTools Protocol interface for MAG agent portal.

www.myagentgenie.com is the primary MAG agent dashboard. Like Odysseus,
it runs behind Cloudflare — CDP via live Chrome port 9222 is the only
automated path.

Usage:
    with MAGSuiteClient() as client:
        tab = client.get_mag_tab()
        content = client.get_page_content(tab)
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
MAG_HOST = "www.myagentgenie.com"
SESSION_FILE = OA_STATE_DIR / "mag_session.json"


class MAGSuiteError(Exception):
    pass


class MAGSuiteClient:
    """CDP client for MAG Suite portal access via live Chrome instance."""

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
            raise MAGSuiteError(f"Chrome CDP unreachable at {self.base}: {e}")

    def get_mag_tab(self) -> dict:
        """Find the MAG Suite tab (www.myagentgenie.com), or raise if not found."""
        tabs = self._get_tabs()
        for tab in tabs:
            url = tab.get("url", "")
            if MAG_HOST in url:
                logger.info("Found MAG tab: %s", url)
                return tab
        raise MAGSuiteError(
            f"No tab found for {MAG_HOST}. "
            "Open Chrome to www.myagentgenie.com and ensure --remote-debugging-port=9222."
        )

    def get_or_open_mag_tab(self) -> dict:
        """Find MAG tab; if not open, create a new one."""
        try:
            return self.get_mag_tab()
        except MAGSuiteError:
            logger.info("No MAG tab found — opening new tab")
            return self._open_new_tab(f"https://{MAG_HOST}/")

    def _open_new_tab(self, url: str) -> dict:
        # Chrome 80+ requires PUT (not GET) for /json/new
        try:
            resp = requests.put(f"{self.base}/json/new?{url}", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise MAGSuiteError(f"Failed to open new tab: {e}")

    def is_chrome_reachable(self) -> bool:
        try:
            requests.get(f"{self.base}/json/version", timeout=3)
            return True
        except requests.RequestException:
            return False

    def get_page_content(self, tab: dict) -> str:
        """Return the current page URL and title for health-check purposes."""
        return json.dumps({
            "url": tab.get("url", ""),
            "title": tab.get("title", ""),
            "id": tab.get("id", ""),
        })

    def _write_session_health(self) -> None:
        try:
            OA_STATE_DIR.mkdir(parents=True, exist_ok=True)
            health = {
                "last_check": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "chrome_reachable": self.is_chrome_reachable(),
                "host": MAG_HOST,
            }
            SESSION_FILE.write_text(json.dumps(health, indent=2))
        except OSError as e:
            logger.warning("Could not write session health: %s", e)
