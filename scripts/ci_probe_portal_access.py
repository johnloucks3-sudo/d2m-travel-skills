#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Cruise-line Portal Access
=============================================
Replaces `import camoufox` (library-present != portals-reachable). Reads the
live portal health written by scripts/portal_live_probe.py and REDs if the
result is stale or any CLIENT-AFFECTING portal is not alive. Portal access is
client-affecting: dead = no B2B quotes, no FPD/booking verification.

ADDED 2026-06-21 (Whetstone REFRESH): binary-staleness assertion. The
anti-detection asset is the Camoufox BROWSER BINARY, not the pip wrapper. A
stale binary = a stale fingerprint = exactly what Akamai/Imperva flag. The CI
was previously blind to this (currency-checked the wrapper, not the binary).
We assert the installed binary (version.json) matches the wrapper resolver's
"latest SUPPORTED" verdict — reusing the wrapper's own is_supported() logic
(CONSTRAINTS >=beta.19), so we never hardcode a version number and we never
false-RED on an alpha-only upstream the wrapper would reject (e.g. the 150
release whose Linux build is alpha). WARN/RED only when a FETCHABLE supported
update actually exists. This is a soft check: binary issues WARN (do not RED
the whole CI) unless the binary is missing entirely.
Exit 0 = healthy, 1 = degraded.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / "Thunderbird" / "OpsCenter" / "state" / "portal_live_health.json"
STALE_HOURS = 3
CAMOUFOX_VERSION_JSON = Path.home() / ".cache" / "camoufox" / "version.json"


def fail(m): print(f"RED portal-access: {m}"); sys.exit(1)


def check_binary_staleness():
    """Assert the installed Camoufox binary == latest SUPPORTED build per the
    wrapper resolver. Returns a one-line status string (printed by caller).
    Soft: returns WARN strings rather than exiting, EXCEPT a missing binary,
    which is a hard RED (no fingerprint = portal access broken)."""
    if not CAMOUFOX_VERSION_JSON.exists():
        fail("Camoufox binary not installed (no version.json) — "
             "run `.venv/bin/python3 -m camoufox fetch`")
    try:
        v = json.loads(CAMOUFOX_VERSION_JSON.read_text())
        installed = f"{v.get('version')}-{v.get('release')}"
    except Exception as e:
        return f"WARN binary: unreadable version.json ({e})"

    # Reuse the wrapper's own resolver to find the latest SUPPORTED release.
    # is_supported() enforces CONSTRAINTS (>=beta.19) and excludes alpha builds,
    # so an alpha-only upstream (e.g. 150) does NOT count as an available update.
    try:
        from camoufox.pkgman import CamoufoxFetcher  # noqa
        f = CamoufoxFetcher()  # __init__ runs fetch_latest() against GitHub
        # Compose the FULL version string (version + release) to match the
        # format version.json uses, e.g. '135.0.1-beta.24'. f.version alone
        # drops the '-beta.NN' release suffix and would false-flag STALE.
        vo = getattr(f, "_version_obj", None)
        if vo is not None and getattr(vo, "full_string", None):
            latest_supported = vo.full_string
        elif vo is not None:
            latest_supported = f"{vo.version}-{vo.release}"
        else:
            latest_supported = str(f.version)
    except Exception as e:
        # Offline / GitHub unreachable / wrapper internals changed: cannot
        # confirm upstream — do NOT fake it, just note we couldn't check.
        return (f"WARN binary: installed={installed}; "
                f"could not confirm latest-supported ({type(e).__name__}) — "
                f"binary currency unverified this run")

    if installed == latest_supported:
        return f"OK binary: {installed} (latest supported — current)"
    return (f"WARN binary STALE: installed={installed}, "
            f"latest-supported={latest_supported} — a FETCHABLE update exists; "
            f"run `.venv/bin/python3 -m camoufox fetch`")


def main():
    if not STATE.exists():
        fail("no portal_live_health.json — live portal probe has never run")
    d = json.loads(STATE.read_text())
    try:
        age_h = (datetime.now(timezone.utc) -
                 datetime.fromisoformat(d["checked_at_utc"])).total_seconds() / 3600
    except Exception:
        age_h = (sys.float_info.max)
    if age_h > STALE_HOURS:
        fail(f"stale: portal health {age_h:.1f}h old (probe stopped running)")
    dead = [f"{n}={r.get('status')}" for n, r in d.get("results", {}).items()
            if r.get("client_affecting") and not r.get("alive")]
    if dead:
        fail("client-affecting portal(s) down: " + ", ".join(dead))
    # Binary-staleness assertion (ADDED 2026-06-21). Soft: prints WARN, does not
    # gate the healthy exit unless the binary is missing (handled inside as RED).
    binary_status = check_binary_staleness()
    print(f"RAZOR_SHARP portal-access: {d.get('portals_checked')} portals, "
          f"{d.get('failures')} failures, {age_h:.1f}h old | {binary_status}")
    sys.exit(0)


if __name__ == "__main__":
    main()
