#!/usr/bin/env python3
"""
healthchecks_wire.py — wire dead-man switches into critical Thunderbird timers.
M5 / SO_TOTAL_CI. Kills the silent-timer-death class.

Two phases:
  A) Given a Healthchecks read-write API key, create a check per critical target
     (POST /api/v3/checks/), capture each ping_url → config/healthchecks_map.json.
  B) Write a systemd --user drop-in per target that pings the check on run
     (ExecStartPre=.../start, ExecStartPost=ping) so a missed run alerts you.

Bootstrap the API key once (docker group not in login session — use sudo):
  sudo docker exec healthchecks python manage.py shell -c \
    "from hc.accounts.models import Project; import secrets; p=Project.objects.first(); \
     p.api_key=(p.api_key or secrets.token_hex(16)); p.save(); print('HC_API_KEY='+p.api_key)"

Run:
  .venv/bin/python scripts/healthchecks_wire.py --api-key <KEY>          # A + B
  .venv/bin/python scripts/healthchecks_wire.py --wire-only             # B from saved map
"""
from __future__ import annotations
import argparse, json, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HC_BASE = "http://localhost:8123"
MAP = ROOT / "config" / "healthchecks_map.json"
DROPIN_DIR = Path.home() / ".config" / "systemd" / "user"

# Curated CRITICAL dead-man targets (unit, human name, expected period sec, grace sec).
# Highest-value first: credential keepalives (silent-death class) + heartbeat + CI + fares.
TARGETS = [
    ("thunderbird-supertimer.service", "supertimer-heartbeat", 300, 600),
    ("ci-sweep.service",               "ci-sweep",             86400, 7200),
    ("ci-auto-repair.service",         "ci-auto-repair",       600, 900),
    ("claude-oauth-keepalive.service", "claude-oauth-keepalive", 5400, 3600),
    ("tess-keepalive.service",         "tess-keepalive",       5400, 3600),
    ("johnloucks3-oauth-keepalive.service", "johnloucks3-oauth", 5400, 3600),
    ("d2mconcierge-oauth-keepalive.service", "d2mconcierge-oauth", 2700, 2700),
    ("portal-keepalive.service",       "portal-keepalive",     10800, 5400),
    ("d2m-centrav-warm.service",       "centrav-warm",         5400, 3600),
    ("thunderbird-fare-sweep.service", "fare-sweep",           86400, 10800),
]


def _api(method: str, path: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{HC_BASE}{path}", data=data, method=method,
                                 headers={"X-Api-Key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def create_checks(key: str) -> dict:
    mapping = {}
    for unit, name, period, grace in TARGETS:
        try:
            # unique=["name"] makes this idempotent — re-runs update, don't duplicate.
            res = _api("POST", "/api/v3/checks/", key, {
                "name": f"tb-{name}", "slug": f"tb-{name}",
                "timeout": period, "grace": grace, "unique": ["name"],
                "tags": "thunderbird deadman",
            })
            ping = res.get("ping_url") or res.get("update_url", "").replace("/api/v3/checks/", "/ping/")
            mapping[unit] = {"name": name, "ping_url": res.get("ping_url"), "period": period, "grace": grace}
            print(f"[check] {name}: {res.get('ping_url')}")
        except Exception as e:
            print(f"[check] {name}: FAILED {e}", file=sys.stderr)
    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps(mapping, indent=2))
    print(f"[map] wrote {len(mapping)} → {MAP}")
    return mapping


def write_dropins(mapping: dict) -> int:
    n = 0
    for unit, info in mapping.items():
        ping = info.get("ping_url")
        if not ping:
            continue
        d = DROPIN_DIR / f"{unit}.d"
        d.mkdir(parents=True, exist_ok=True)
        # -/usr/bin/curl with `-` prefix: a failed ping never fails the unit.
        (d / "healthcheck.conf").write_text(
            "[Service]\n"
            f"ExecStartPre=-/usr/bin/curl -fsS -m 5 {ping}/start\n"
            f"ExecStartPost=-/usr/bin/curl -fsS -m 5 {ping}\n"
        )
        n += 1
        print(f"[dropin] {unit} → pings {info['name']}")
    if n:
        subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=30)
        print(f"[systemd] daemon-reload done ({n} drop-ins)")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", help="Healthchecks read-write API key")
    ap.add_argument("--wire-only", action="store_true", help="Write drop-ins from saved map (skip check creation)")
    args = ap.parse_args()

    if args.wire_only:
        if not MAP.exists():
            print("No healthchecks_map.json — run with --api-key first.", file=sys.stderr); sys.exit(2)
        mapping = json.loads(MAP.read_text())
    else:
        if not args.api_key:
            print("Provide --api-key (see docstring for the docker-exec bootstrap).", file=sys.stderr); sys.exit(2)
        mapping = create_checks(args.api_key)

    wired = write_dropins(mapping)
    print(f"\nDONE — {wired} critical timers now have dead-man coverage in Healthchecks.")
    print("A missed run pages you via Healthchecks' own Telegram integration (set in HC UI).")


if __name__ == "__main__":
    main()
