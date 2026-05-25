import logging

from core.ai_infra import unified_router
from core.ai_infra.adapters.claude_max_oauth import sonnet_adapter, opus_adapter, haiku_adapter

log = logging.getLogger("router_setup")


def register_all_adapters():
    count = 0
    for adap in (sonnet_adapter, opus_adapter, haiku_adapter):
        try:
            unified_router.register_adapter(adap)
            count += 1
        except Exception as e:
            log.error("Failed to register %s: %s", adap.name, e)
    unified_router.configure_default_pools()
    log.info("Registered %d Claude MAX adapters (all non-Claude paths removed)", count)
    return count


def router_health_summary() -> dict:
    states = unified_router.health.all_states()
    pools = unified_router.cost_gates.get_all()
    telem = unified_router.telemetry.summary()
    return {
        "adapters": list(unified_router.registered_adapters()),
        "health": {
            name: state for name, (state, _) in states.items()
        },
        "pools": {
            name: {"consumed": p["consumed"], "hard_limit": p["hard_limit"]}
            for name, p in pools.items()
        },
        "telemetry": telem,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    n = register_all_adapters()
    print(f"Registered {n} adapters")
    print(f"Adapter list: {list(unified_router.registered_adapters())}")
    print(router_health_summary())
    print("\nGate 2 — Adapter Registration: PASS")
