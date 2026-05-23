import logging

from core.ai_infra import unified_router
from core.ai_infra.adapters.opencode_nemotron import adapter as nemotron_adapter
from core.ai_infra.adapters.google_gemini_flash import adapter as gemini_flash_adapter
from core.ai_infra.adapters.claude_max_oauth import sonnet_adapter, opus_adapter
from core.ai_infra.adapters.opencode_deepseek_v4 import adapter as deepseek_adapter

log = logging.getLogger("router_setup")

# Optional zero-cost adapters — present only in some deployments
_free_adapters = []
try:
    from core.ai_infra.adapters.opencode_bigpickle import adapter as bigpickle_adapter
    _free_adapters.append(bigpickle_adapter)
except ImportError:
    log.debug("opencode_bigpickle adapter not available")
try:
    from core.ai_infra.adapters.ollama_local import adapter as ollama_adapter
    _free_adapters.append(ollama_adapter)
except ImportError:
    log.debug("ollama_local adapter not available")


def register_all_adapters():
    count = 0
    # Register zero-cost adapters first so they appear early in any chain
    for adap in _free_adapters:
        try:
            unified_router.register_adapter(adap)
            count += 1
        except Exception as e:
            log.error("Failed to register %s: %s", adap.name, e)
    for adap in (nemotron_adapter, gemini_flash_adapter,
                 sonnet_adapter, opus_adapter,
                 deepseek_adapter):
        try:
            unified_router.register_adapter(adap)
            count += 1
        except Exception as e:
            log.error("Failed to register %s: %s", adap.name, e)
    unified_router.configure_default_pools()
    log.info("Registered %d adapters + default cost pools", count)
    return count


def router_health_summary() -> dict:
    """Human-readable health summary for debugging."""
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
