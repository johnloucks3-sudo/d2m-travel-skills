import sys
sys.path.insert(0, "/home/john/Thunderbird")
import pytest
from core.ci.portal_guard import Throttle, PortalAbort, DEFAULT_MIN_INTERVAL_S


class FakeClock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s  # advancing time models the sleep


def test_first_request_does_not_wait():
    c = FakeClock()
    g = Throttle(clock=c.now, sleeper=c.sleep)
    assert g.wait("rssc.com") == 0.0
    assert c.slept == []


def test_second_request_within_interval_waits_remainder():
    c = FakeClock()
    g = Throttle(min_interval=3.0, clock=c.now, sleeper=c.sleep)
    g.wait("rssc.com")          # t=1000, no wait
    c.t += 1.0                  # only 1s passed
    slept = g.wait("rssc.com")  # should sleep 2.0s
    assert slept == pytest.approx(2.0)
    assert c.slept == [pytest.approx(2.0)]


def test_no_wait_when_interval_already_elapsed():
    c = FakeClock()
    g = Throttle(min_interval=3.0, clock=c.now, sleeper=c.sleep)
    g.wait("rssc.com")
    c.t += 5.0                  # plenty of time
    assert g.wait("rssc.com") == 0.0


def test_per_host_independent():
    c = FakeClock()
    g = Throttle(min_interval=3.0, clock=c.now, sleeper=c.sleep)
    g.wait("rssc.com")
    assert g.wait("centrav.com") == 0.0  # different host, first hit


def test_check_response_aborts_on_403():
    g = Throttle()
    with pytest.raises(PortalAbort):
        g.check_response(403)


def test_check_response_aborts_on_429():
    g = Throttle()
    with pytest.raises(PortalAbort):
        g.check_response(429)


def test_check_response_passes_on_200():
    g = Throttle()
    g.check_response(200)  # no raise


def test_default_interval_is_3s():
    assert DEFAULT_MIN_INTERVAL_S == 3.0
