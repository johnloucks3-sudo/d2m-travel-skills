"""
core/monitoring/sitecustomize.py — fleet-wide, zero-touch crash reporter install.

Python's `site` module auto-imports a module named `sitecustomize` at
interpreter start-up if one is importable anywhere on sys.path. Adding
this directory (core/monitoring) to PYTHONPATH — done in
deploy/thunderbird_pythonpath.env — makes this run for EVERY Python
process that sources that env file, with zero edits to any of the ~50+
individual scripts.

Must be side-effect-free on failure: this runs in every subprocess,
including throwaway ones (pip, pytest workers, etc). Any exception here
must never break the host script's ability to start.
"""

try:
    from core.monitoring.crash_reporter import install

    install()
except Exception:
    # Never let the crash reporter itself be the reason a script fails to
    # start. If this can't install (e.g. core/ not importable in this
    # context), the script just runs without it — same as before this
    # existed.
    pass
