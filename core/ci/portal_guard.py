"""Portal-access guard — throttle-from-request-1 + abort-on-first-403.

Prevents the self-inflicted Imperva rate-limit that blocked the Commander's own
IP (hale_decisions.md 2026-06-13: over-aggressive scrape ~6 req/IP). Standing
scraping doctrine: >=3s between requests per host from request 1, abort on the
first 403/429 (back off, do not retry). $0, no proxy.

Usage:
    g = Throttle()                     # >=3s/host
    g.wait("api.rssc.com")             # paces before each request
    resp = session.get(url)
    g.check_response(resp.status_code) # raises PortalAbort on 403/429
"""
from __future__ import annotations
import time

# Per standing scraping doctrine (hale_decisions.md 2026-06-13).
DEFAULT_MIN_INTERVAL_S = 3.0
ABORT_STATUSES = (403, 429)


class PortalAbort(Exception):
    """Raised on a bot-wall/rate-limit status. Caller MUST back off, not retry."""


class Throttle:
    def __init__(self, min_interval: float = DEFAULT_MIN_INTERVAL_S,
                 clock=time.monotonic, sleeper=time.sleep):
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleeper
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> float:
        """Sleep so >=min_interval has elapsed since the last request to host.
        Returns the seconds actually slept (0.0 on the first request to a host)."""
        now = self._clock()
        last = self._last.get(host)
        slept = 0.0
        if last is not None:
            elapsed = now - last
            if elapsed < self.min_interval:
                slept = self.min_interval - elapsed
                self._sleep(slept)
        self._last[host] = self._clock()
        return slept

    def check_response(self, status_code: int) -> None:
        """Raise PortalAbort on a rate/bot-wall status — do NOT retry on these."""
        if status_code in ABORT_STATUSES:
            raise PortalAbort(
                f"Abort on HTTP {status_code} — rate/bot wall hit; back off, do not retry "
                f"(protects Commander IP per scraping doctrine)")
