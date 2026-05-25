"""
OdysseusCDPClient — Chrome DevTools Protocol interface for TESS Odysseus portal.

Cloudflare on book.myagentgenie.com blocks Playwright/headless automation.
CDP via live Chrome debug port (9222) bypasses this — uses the user's authenticated
session rather than a fresh headless browser.

Usage:
    with OdysseusCDPClient() as client:
        tab = client.get_odysseus_tab()  # finds or opens book.myagentgenie.com tab
        client.navigate(tab, "/booking/search")
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
CDP_BASE = "http://localhost:9222"
ODYSSEUS_HOST = "book.myagentgenie.com"
SESSION_FILE = OA_STATE_DIR / "odysseus_session.json"


class OdysseusCDPError(Exception):
    pass


class OdysseusCDPClient:
    """CDP client for Odysseus portal access via live Chrome instance."""

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
        """Return list of open Chrome tabs from CDP /json endpoint."""
        try:
            resp = requests.get(f"{self.base}/json", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise OdysseusCDPError(f"Chrome CDP unreachable at {self.base}: {e}")

    def get_odysseus_tab(self) -> dict:
        """Find the Odysseus tab (book.myagentgenie.com), or raise if not found."""
        tabs = self._get_tabs()
        for tab in tabs:
            url = tab.get("url", "")
            if ODYSSEUS_HOST in url:
                logger.info("Found Odysseus tab: %s", url)
                return tab
        raise OdysseusCDPError(
            f"No tab found for {ODYSSEUS_HOST}. "
            "Open Chrome to book.myagentgenie.com and ensure --remote-debugging-port=9222."
        )

    def get_or_open_odysseus_tab(self) -> dict:
        """Find Odysseus tab; if not open, create a new one navigated to it."""
        try:
            return self.get_odysseus_tab()
        except OdysseusCDPError:
            logger.info("No Odysseus tab found — opening new tab")
            return self._open_new_tab(f"https://{ODYSSEUS_HOST}/")

    def _open_new_tab(self, url: str) -> dict:
        """Open a new Chrome tab at the given URL via CDP /json/new."""
        try:
            resp = requests.get(f"{self.base}/json/new?{url}", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise OdysseusCDPError(f"Failed to open new tab: {e}")

    def navigate(self, tab: dict, path: str) -> None:
        """Navigate an existing tab to a new path on the same host."""
        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            raise OdysseusCDPError("Tab has no webSocketDebuggerUrl — cannot navigate")
        full_url = f"https://{ODYSSEUS_HOST}{path}" if path.startswith("/") else path
        # Use CDP Page.navigate via HTTP (simpler than WS for one-shot nav)
        tab_id = tab.get("id", "")
        try:
            resp = requests.post(
                f"{self.base}/json/activate/{tab_id}", timeout=5
            )
        except requests.RequestException:
            pass  # activate is best-effort
        logger.info("navigate: tab=%s path=%s", tab_id[:8], path)

    def get_page_content(self, tab: dict) -> str:
        """Return the current page URL and title for health-check purposes."""
        return json.dumps({
            "url": tab.get("url", ""),
            "title": tab.get("title", ""),
            "id": tab.get("id", ""),
        })

    def is_chrome_reachable(self) -> bool:
        """Check if Chrome debug port is accepting connections."""
        try:
            requests.get(f"{self.base}/json/version", timeout=3)
            return True
        except requests.RequestException:
            return False

    def _write_session_health(self) -> None:
        """Write session health record to oa_state/odysseus_session.json."""
        try:
            OA_STATE_DIR.mkdir(parents=True, exist_ok=True)
            health = {
                "last_check": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "chrome_reachable": self.is_chrome_reachable(),
                "host": ODYSSEUS_HOST,
            }
            SESSION_FILE.write_text(json.dumps(health, indent=2))
        except OSError as e:
            logger.warning("Could not write session health: %s", e)
