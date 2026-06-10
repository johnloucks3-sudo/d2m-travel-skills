"""
Xvfb + Headful Firefox driver for Playwright.
Bypasses Akamai Bot Manager and similar CDN bot detectors by presenting
a real X11 desktop environment with a full Firefox profile.

Architecture:
  XvfbDriver  (async context manager)
   ├── __init__  — config (display num, profile dir, viewport)
   ├── __aenter__ — lock cleanup, Xvfb spawn, DISPLAY set, Firefox launch,
   │                context/page creation, cookie restore
   ├── __aexit__  — cookie save, browser close, Xvfb kill
   ├── save_cookies / load_cookies  — JSON file persistence
   ├── screenshot / navigate / evaluate — convenience wrappers
   └── main()     — smoke test (example.com → screenshot → page info)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DISPLAY_BASE = "/tmp/.X11-unix"
XVFB_READY_TIMEOUT = 10.0
XVFB_READY_POLL = 0.1


class XvfbDriver:
    """Async context manager: start Xvfb + headful Firefox, tear down on exit.

    Usage::

        async with XvfbDriver(display_num=99, profile_dir="/tmp/fx-profile") as d:
            await d.navigate("https://example.com")
            info = await d.navigate("https://target.site/login")
            await d.screenshot("/tmp/login.png")
            cookies = await d.page.context.cookies()
    """

    def __init__(
        self,
        display_num: int = 99,
        profile_dir: str | Path | None = None,
        viewport: dict | None = None,
        headless: bool = False,
    ) -> None:
        self.display_num = display_num
        self.display = f":{display_num}"
        self.profile_dir = Path(profile_dir).resolve() if profile_dir else None
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.headless = headless

        self._xvfb_proc: asyncio.subprocess.Process | None = None
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._saved_display: str | None = None

    # ── Public properties ──────────────────────────────────────────────

    @property
    def browser(self) -> Any:
        if self._browser is None:
            raise RuntimeError("browser not started — use async with")
        return self._browser

    @property
    def context(self) -> Any:
        if self._context is None:
            raise RuntimeError("context not created — use async with")
        return self._context

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("page not created — use async with")
        return self._page

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def __aenter__(self) -> XvfbDriver:
        self._saved_display = os.environ.get("DISPLAY")
        self._clean_stale_locks()
        await self._start_xvfb()
        os.environ["DISPLAY"] = self.display
        await self._wait_for_xvfb()
        await self._launch_browser()
        logger.info("xvfb: ready — display=%s, profile=%s", self.display, self.profile_dir)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: Any = None,
    ) -> None:
        if self.profile_dir:
            try:
                await self.save_cookies(self.profile_dir / "cookies.json")
            except Exception:
                logger.exception("xvfb: cookie save failed during teardown")
        if self._context:
            try:
                await self._context.close()
            except Exception:
                logger.exception("xvfb: context close error during teardown")
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                logger.exception("xvfb: browser close error during teardown")
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                logger.exception("xvfb: playwright stop error during teardown")
        if self._xvfb_proc:
            try:
                self._xvfb_proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(self._xvfb_proc.wait(), timeout=5.0)
                except TimeoutError:
                    logger.warning("xvfb: process did not exit — sending SIGKILL")
                    self._xvfb_proc.send_signal(signal.SIGKILL)
                    await self._xvfb_proc.wait()
            except Exception:
                logger.exception("xvfb: kill error during teardown")
        # Restore DISPLAY so caller's env is unchanged.
        if self._saved_display is not None:
            os.environ["DISPLAY"] = self._saved_display
        else:
            os.environ.pop("DISPLAY", None)

    # ── Cookie persistence ─────────────────────────────────────────────

    async def save_cookies(self, filepath: str | Path) -> None:
        """Save current browser context cookies to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        cookies = await self.context.cookies()
        filepath.write_text(
            json.dumps(cookies, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(
            "xvfb: saved %d cookies → %s",
            len(cookies),
            filepath,
        )

    async def load_cookies(self, filepath: str | Path) -> None:
        """Load cookies from a JSON file into the browser context."""
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning("xvfb: cookie file not found: %s", filepath)
            return
        raw = filepath.read_text(encoding="utf-8")
        cookies: list[dict[str, Any]] = json.loads(raw)
        # Playwright's add_cookies expects list[dict] with correct types.
        await self.context.add_cookies(cookies)
        logger.info(
            "xvfb: loaded %d cookies from %s",
            len(cookies),
            filepath,
        )

    # ── Convenience wrappers ───────────────────────────────────────────

    async def screenshot(self, filepath: str | Path) -> None:
        """Capture a page screenshot to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(filepath), full_page=True)
        logger.info("xvfb: screenshot saved → %s", filepath)

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30_000,
    ) -> dict[str, Any]:
        """Navigate to *url* and return page metadata."""
        logger.info("xvfb: navigating → %s", url)
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)
        current_url = self.page.url
        title = await self.page.title()
        text_snippet = (
            await self.page.evaluate(
                "document.body?.innerText?.substring(0, 500) ?? ''"
            )
        ) or ""
        info = {
            "url": current_url,
            "title": title.strip() if title else "",
            "text_snippet": text_snippet.strip()[:200],
        }
        logger.info(
            "xvfb: loaded  %s  |  title=%s",
            current_url,
            info["title"][:80],
        )
        return info

    async def evaluate(self, js: str) -> Any:
        """Run JavaScript in the page context with error wrapping."""
        try:
            return await self.page.evaluate(js)
        except Exception as e:
            logger.error("xvfb: evaluate failed: %s", e)
            raise

    # ── Internal helpers ───────────────────────────────────────────────

    def _clean_stale_locks(self) -> None:
        """Remove stale X lock files that would prevent Xvfb from starting."""
        lock_file = Path(f"/tmp/.X{self.display_num}-lock")
        if lock_file.exists():
            lock_file.unlink()
            logger.info("xvfb: removed stale lock: %s", lock_file)
        unix_socket = Path(DISPLAY_BASE) / f"X{self.display_num}"
        if unix_socket.exists():
            try:
                unix_socket.unlink()
                logger.info("xvfb: removed stale socket: %s", unix_socket)
            except OSError:
                logger.warning(
                    "xvfb: could not remove stale socket: %s", unix_socket
                )

    async def _start_xvfb(self) -> None:
        """Launch Xvfb as a subprocess."""
        logger.info("xvfb: starting Xvfb on display %s", self.display)
        self._xvfb_proc = await asyncio.create_subprocess_exec(
            "Xvfb",
            self.display,
            "-screen",
            "0",
            f"{self.viewport['width']}x{self.viewport['height']}x24",
            "-nolisten",
            "tcp",
            "-ac",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def _wait_for_xvfb(self) -> None:
        """Block until Xvfb's Unix socket appears or timeout elapses."""
        sock_path = Path(DISPLAY_BASE) / f"X{self.display_num}"
        deadline = time.monotonic() + XVFB_READY_TIMEOUT
        while time.monotonic() < deadline:
            if sock_path.exists() and self._xvfb_proc and self._xvfb_proc.returncode is None:
                logger.info("xvfb: ready on %s (socket: %s)", self.display, sock_path)
                return
            await asyncio.sleep(XVFB_READY_POLL)
        raise RuntimeError(
            f"xvfb: did not become ready within {XVFB_READY_TIMEOUT}s "
            f"(display={self.display}, socket={sock_path})"
        )

    async def _launch_browser(self) -> None:
        """Launch headful Firefox, create context + page, restore cookies."""
        from playwright.async_api import async_playwright
        launch_args = []
        if self.profile_dir:
            self.profile_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "xvfb: launching Firefox (headless=%s, display=%s)",
            self.headless,
            self.display,
        )

        self._pw = await async_playwright().start()
        self._browser = await self._pw.firefox.launch(
            headless=self.headless,
            args=launch_args,
        )
        self._context = await self._browser.new_context(
            viewport=self.viewport,
            no_viewport=False,
            locale="en-US",
            timezone_id="America/New_York",
        )
        self._page = await self._context.new_page()

        # Restore persisted cookies.
        if self.profile_dir:
            cookie_file = self.profile_dir / "cookies.json"
            if cookie_file.exists():
                await self.load_cookies(cookie_file)

        logger.info("xvfb: Firefox launched and ready")


async def _test_driver() -> None:
    """Smoke test: navigate, screenshot, print page info."""
    async with XvfbDriver(display_num=99) as driver:
        info = await driver.navigate(
            "https://example.com",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await driver.screenshot("/tmp/xvfb_smoke_test.png")
        print(f"URL:      {info['url']}")
        print(f"Title:    {info['title']}")
        print(f"Snippet:  {info['text_snippet'][:120]}...")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(_test_driver())


if __name__ == "__main__":
    main()
