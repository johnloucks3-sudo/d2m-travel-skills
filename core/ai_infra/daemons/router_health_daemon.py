#!/usr/bin/env python3
"""
Router Health Daemon — probes every adapter every 5 minutes.
Records results to health DB. Marks RED on 3 consecutive failures.
Designed to run as systemd timer or long-lived service.

Usage:
    PYTHONPATH=/home/john/Thunderbird .venv/bin/python core/ai_infra/daemons/router_health_daemon.py
    # One-shot: --once
    # Custom interval: --interval 300
"""

import argparse
import logging
import sys
import time

sys.path.insert(0, "/home/john/Thunderbird")

from core.ai_infra.router_setup import register_all_adapters
from core.ai_infra.unified_router import get_adapter, registered_adapters
from core.ai_infra.router_health import health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("health_daemon")


def probe_all():
    names = registered_adapters()
    if not names:
        log.warning("No adapters registered")
        return

    for name in names:
        adapter = get_adapter(name)
        if adapter is None:
            continue
        t0 = time.monotonic()
        try:
            state, reason = adapter.health_probe()
            latency = int((time.monotonic() - t0) * 1000)
            health.set_state(name, state)
            health.record_probe(name, state, latency,
                                error=reason if state != "GREEN" else "")
            if state == "GREEN":
                log.info("Probe %s: GREEN (%dms)", name, latency)
            else:
                log.warning("Probe %s: %s (%dms) — %s", name, state, latency, reason)
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            health.record_failure(name)
            health.record_probe(name, "RED", latency, error=str(e))
            log.error("Probe %s crashed: %s (%dms)", name, e, latency)


def main():
    parser = argparse.ArgumentParser(description="Router Health Daemon")
    parser.add_argument("--once", action="store_true", help="Run one probe cycle and exit")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds")
    args = parser.parse_args()

    register_all_adapters()
    log.info("Health daemon started: %d adapters, interval=%ds",
             len(registered_adapters()), args.interval)

    if args.once:
        probe_all()
        return

    while True:
        probe_all()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
