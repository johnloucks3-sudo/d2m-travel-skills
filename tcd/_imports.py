"""
Import shim — resolves Thunderbird modules whether the process runs from the
repo (package paths like ``api.thunderbird_google_auth``) or from the deploy
host root ``/home/john/Thunderbird`` (bare names like
``thunderbird_google_auth``). The two layouts differ between the checked-in
repo and the live box, so every cross-module import in this package goes
through here.

Nothing here requires credentials or network — importing a module is safe;
only *calling* the Google getters touches live services.
"""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Make both the repo-style and box-style locations importable.
for sub in ("", "api", "scripts"):
    p = ROOT / sub if sub else ROOT
    sp = str(p)
    if p.is_dir() and sp not in sys.path:
        sys.path.insert(0, sp)


def _first_import(names):
    """Return the first importable module from ``names``; raise the last error."""
    last = None
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception as e:  # ImportError, or downstream import errors
            last = e
    raise ImportError(
        f"none of {names} could be imported (last error: {last})"
    )


def load_google_auth():
    """Thunderbird unified Google auth module (repo or box layout)."""
    return _first_import(["api.thunderbird_google_auth", "thunderbird_google_auth"])


def load_tcd_data():
    """The existing local item builders we repurpose (repo or box layout)."""
    return _first_import(["scripts.tcd_data", "tcd_data"])


def load_keep():
    """Existing gkeepapi/master-token Keep integration (repo or box layout).
    Consumer-account path — no Workspace/service-account needed."""
    return _first_import(["api.thunderbird_keep", "thunderbird_keep"])
