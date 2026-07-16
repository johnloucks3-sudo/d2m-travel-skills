"""
Phase 4 smoke tests — Module A, B, C, D import + structure verification.
All tests run OFFLINE. No live TESS API calls. No Chrome required.
"""
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest


# ── Module A: TESSWriteClient ─────────────────────────────────────────────────

def test_module_a_import():
    from core.booking.thunderbird_tess_crm import TESSWriteClient, TESSWriteError
    assert TESSWriteClient is not None
    assert TESSWriteError is not None


def test_module_a_methods():
    from core.booking.thunderbird_tess_crm import TESSWriteClient
    assert hasattr(TESSWriteClient, "create_trip")
    assert hasattr(TESSWriteClient, "create_booking")
    assert hasattr(TESSWriteClient, "upsert_client")


# ── Module B: OdysseusCDPClient ───────────────────────────────────────────────

def test_module_b_import():
    from api.thunderbird_odysseus_cdp import OdysseusCDPClient, OdysseusCDPError
    assert OdysseusCDPClient is not None


def test_module_b_context_manager():
    from api.thunderbird_odysseus_cdp import OdysseusCDPClient
    assert hasattr(OdysseusCDPClient, "__enter__")
    assert hasattr(OdysseusCDPClient, "__exit__")


def test_module_b_health_check_returns_bool():
    # Assert the connection-path health contract by TYPE, never by live
    # connectivity state (Sterling doctrine — CDP tests must not assert
    # environment state). Passes whether or not Chrome debug is running.
    from api.thunderbird_odysseus_cdp import OdysseusCDPClient
    assert isinstance(OdysseusCDPClient().is_chrome_reachable(), bool)


# ── Module C: MAGSuiteClient ──────────────────────────────────────────────────

def test_module_c_import():
    from api.thunderbird_mag_suite import MAGSuiteClient, MAGSuiteError
    assert MAGSuiteClient is not None


def test_module_c_context_manager():
    from api.thunderbird_mag_suite import MAGSuiteClient
    assert hasattr(MAGSuiteClient, "__enter__")
    assert hasattr(MAGSuiteClient, "__exit__")


# ── Module D: TLNCruiseCompleteClient ─────────────────────────────────────────

def test_module_d_import():
    from api.thunderbird_tln_cruisecomplete import TLNCruiseCompleteClient, TLNCruiseCompleteError
    assert TLNCruiseCompleteClient is not None


def test_module_d_context_manager():
    from api.thunderbird_tln_cruisecomplete import TLNCruiseCompleteClient
    assert hasattr(TLNCruiseCompleteClient, "__enter__")
    assert hasattr(TLNCruiseCompleteClient, "__exit__")


def test_module_d_session_health_structure():
    from api.thunderbird_tln_cruisecomplete import TLNCruiseCompleteClient
    client = TLNCruiseCompleteClient()
    # session_health() runs without requiring Chrome — validates structure only
    health = client.session_health()
    assert "last_check" in health
    assert "chrome_reachable" in health
    assert isinstance(health["chrome_reachable"], bool)
    assert health["host"] == "cruisecomplete.travelleaders.com"


# ── CDPSessionLock: mutex behavior ────────────────────────────────────────────

def test_cdp_lock_acquire_release():
    from api.thunderbird_cdp_lock import CDPSessionLock, CDPLockTimeout
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        lock = CDPSessionLock(lock_path, timeout=2)
        lock.acquire()
        assert lock_path.exists()
        pid_in_file = int(lock_path.read_text().strip())
        assert pid_in_file == os.getpid()
        lock.release()
        assert not lock_path.exists()


def test_cdp_lock_context_manager():
    from api.thunderbird_cdp_lock import CDPSessionLock
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        with CDPSessionLock(lock_path, timeout=2):
            assert lock_path.exists()
        assert not lock_path.exists()


def test_cdp_lock_stale_pid_recovery():
    """Lock with a dead PID should be acquirable (stale lock recovery)."""
    from api.thunderbird_cdp_lock import CDPSessionLock
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        # Write a stale lock with PID 99999 (almost certainly dead)
        lock_path.write_text("99999")
        lock = CDPSessionLock(lock_path, timeout=2)
        lock.acquire()  # Should succeed despite existing lock file
        assert lock_path.exists()
        pid_in_file = int(lock_path.read_text().strip())
        assert pid_in_file == os.getpid()
        lock.release()


def test_cdp_lock_timeout():
    """Lock held by alive process should raise CDPLockTimeout."""
    from api.thunderbird_cdp_lock import CDPSessionLock, CDPLockTimeout
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        # Write our own PID as a live holder
        lock_path.write_text(str(os.getpid()))
        lock = CDPSessionLock(lock_path, timeout=1, poll_interval=0.1)
        with pytest.raises(CDPLockTimeout):
            lock.acquire()
