"""
CDPSessionLock — file-based mutex for Chrome DevTools Protocol tab contention.

Prevents multiple modules (Odysseus CDP, TLN CDP) from simultaneously
operating on the same Chrome session and causing tab conflicts.

Usage:
    from api.thunderbird_cdp_lock import CDPSessionLock, CDPLockTimeout

    with CDPSessionLock(lock_path, timeout=30):
        # exclusive CDP access here
        pass
"""
import os
import time
from pathlib import Path


class CDPLockTimeout(Exception):
    """Raised when CDPSessionLock cannot be acquired within the timeout."""
    pass


class CDPSessionLock:
    """
    File-based mutex for CDP session access.

    Lock file contains the holder's PID. On acquire, checks if the PID in
    the lock file is still alive (stale lock detection). On release, removes
    the file only if we own it.
    """

    def __init__(self, lock_path: Path, timeout: int = 30, poll_interval: float = 0.5):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._acquired = False

    def _is_pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _try_acquire(self) -> bool:
        try:
            if self.lock_path.exists():
                try:
                    existing_pid = int(self.lock_path.read_text().strip())
                    if self._is_pid_alive(existing_pid):
                        return False
                    self.lock_path.unlink(missing_ok=True)
                except (ValueError, OSError):
                    self.lock_path.unlink(missing_ok=True)
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock_path.write_text(str(os.getpid()))
            self._acquired = True
            return True
        except OSError:
            return False

    def acquire(self) -> None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._try_acquire():
                return
            time.sleep(self.poll_interval)
        raise CDPLockTimeout(
            f"Could not acquire CDP session lock at {self.lock_path} "
            f"within {self.timeout}s"
        )

    def release(self) -> None:
        if self._acquired and self.lock_path.exists():
            try:
                current_pid = int(self.lock_path.read_text().strip())
                if current_pid == os.getpid():
                    self.lock_path.unlink(missing_ok=True)
            except (ValueError, OSError):
                pass
        self._acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()
