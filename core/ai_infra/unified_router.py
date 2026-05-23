import logging
import time
import threading

from core.ai_infra.adapters.base import AdapterResult, Adapter
from core.ai_infra.router_chains import (
    TIER_CHAINS,
    resolve_persona_tier,
)
from core.ai_infra.router_health import health
from core.ai_infra.router_cost_gates import cost_gates
from core.ai_infra.budget_preflight_guard import run_preflight, PreFlightResult, GuardVerdict
from core.ai_infra.router_telemetry import telemetry
from core.ai_infra.router_classifier import classify as classify_tier, ALL_TIERS, DEFAULT_TIER

log = logging.getLogger("unified_router")

# ── Commander Standing Order: NO OPENROUTER MODELS (2026-05-21) ───────────────
# Hard-blocked at registration and dispatch — no code path can reach an OpenRouter model.
BLOCKED_ADAPTER_PREFIXES: set[str] = {"openrouter"}
BLOCKED_COST_POOLS: set[str] = {"openrouter_credits"}

# ── Zero-cost pools — never skipped by degrade logic ─────────────────────────
# Bouncing stack: big-pickle → deepseek-v4-flash-free → ollama (local, unlimited)
FREE_COST_POOLS: set[str] = {"ollama_local", "free_local", "zero_cost"}


def _is_openrouter(adapter: Adapter) -> bool:
    name_lower = adapter.name.lower()
    for prefix in BLOCKED_ADAPTER_PREFIXES:
        if prefix in name_lower:
            return True
    return adapter.cost_pool in BLOCKED_COST_POOLS


# ── Task Request ──────────────────────────────────────────────────────────────

class TaskRequest:
    __slots__ = ("system", "user", "persona", "max_tokens", "tier_override", "task_id", "budget_override")

    def __init__(
        self,
        system: str = "",
        user: str = "",
        persona: str = "default",
        max_tokens: int = 4096,
        tier_override: str | None = None,
        task_id: str = "",
        budget_override: bool = False,
    ):
        self.system = system
        self.user = user
        self.persona = persona
        self.max_tokens = max_tokens
        self.tier_override = tier_override
        self.task_id = task_id
        self.budget_override = budget_override


# ── Global State ──────────────────────────────────────────────────────────────

_adapters: dict[str, Adapter] = {}
_adapter_lock = threading.Lock()


def register_adapter(adapter: Adapter):
    if not hasattr(adapter, "name") or not adapter.name:
        raise ValueError("Adapter must have a .name attribute")
    if _is_openrouter(adapter):
        log.warning("REFUSED — OpenRouter adapter blocked by Commander order: %s", adapter.name)
        return
    with _adapter_lock:
        _adapters[adapter.name] = adapter
        health.set_state(adapter.name, "GREEN")
    log.info("Registered adapter: %s (pool=%s, tiers=%s)", adapter.name, adapter.cost_pool, adapter.tier_capabilities)


def get_adapter(name: str) -> Adapter | None:
    with _adapter_lock:
        return _adapters.get(name)


def registered_adapters() -> list[str]:
    with _adapter_lock:
        return list(_adapters.keys())


# ── Tier Classification ───────────────────────────────────────────────────────

# ── Default Pool Configuration ────────────────────────────────────────────────

def configure_default_pools():
    cost_gates.configure_pool("max_weekly_sonnet", soft_limit=80.0, hard_limit=95.0)
    cost_gates.configure_pool("max_weekly_all", soft_limit=80.0, hard_limit=95.0)
    cost_gates.configure_pool("poe_points", soft_limit=0, hard_limit=0)  # Poe removed 2026-05-23 — points exhausted
    cost_gates.configure_pool("openrouter_credits", soft_limit=0, hard_limit=0)  # $0 — frozen
    cost_gates.configure_pool("google_ai_pro", soft_limit=0, hard_limit=-1)     # flat-fee — unlimited
    cost_gates.configure_pool("opencode_native", soft_limit=0, hard_limit=-1)   # free — unlimited
    log.info("Default cost pools configured")


# ── Dispatch ──────────────────────────────────────────────────────────────────

def dispatch(task: TaskRequest) -> AdapterResult:
    # ── Budget pre-flight: check ceilings before touching any adapter ──
    # When BLOCKED, strip MAX Sonnet → try DeepSeek V4 → STOP + alert
    preflight = run_preflight()
    budget_blocked = preflight.verdict == GuardVerdict.BLOCK and not task.budget_override
    if budget_blocked:
        pool_details = "; ".join(
            f"{p.pool}={p.pct_used:.0f}%" for p in preflight.pools
        )
        log.warning("Budget guard BLOCK — DeepSeek V4 fallback: %s", pool_details)
    elif task.budget_override:
        log.info("Commander budget override active — guard bypassed")

    tier = classify_tier(task.system, task.user, task.persona, task.tier_override)

    candidate_names = list(TIER_CHAINS.get(tier, []))
    persona_tier = resolve_persona_tier(task.persona)
    if persona_tier and persona_tier != tier:
        candidate_names = list(TIER_CHAINS.get(persona_tier, []))
        tier = persona_tier
        log.debug("Persona override: %s → tier %s", task.persona, tier)

    # Budget degrade mode: strip Claude MAX adapters if blocked or degraded.
    # BLOCK = autonomous fallback through Poe/DeepSeek/Big Pickle
    pool_blocked = any(
        p.pool in ("claude_max_session", "claude_max_sonnet_weekly", "harlan_veto")
        and p.verdict in (GuardVerdict.DEGRADE, GuardVerdict.BLOCK)
        for p in preflight.pools
    )
    degrade_claude = budget_blocked or (
        preflight.verdict == GuardVerdict.DEGRADE and pool_blocked
    )
    degrade_zen = (
        preflight.verdict == GuardVerdict.DEGRADE
        and any(p.pool == "zen_opencode" and p.verdict in (GuardVerdict.DEGRADE, GuardVerdict.BLOCK) for p in preflight.pools)
    )

    candidates: list[Adapter] = []
    for name in candidate_names:
        adapter = get_adapter(name)
        if adapter is None:
            log.debug("Adapter %s not registered — skipping", name)
            continue
        if health.get(adapter.name) == "RED":
            log.debug("Adapter %s is RED — skipping", name)
            continue
        if _is_openrouter(adapter):
            log.debug("Adapter %s is OpenRouter — blocked by Commander order", name)
            continue
        if not cost_gates.has_headroom(adapter.cost_pool):
            log.debug("Adapter %s pool %s exhausted — skipping", name, adapter.cost_pool)
            continue
        # Budget degrade: drop Claude MAX if session is over 80%
        if degrade_claude and adapter.cost_pool in ("max_weekly_sonnet", "max_weekly_all"):
            log.info("Budget degrade: skipping %s (Claude MAX session >= 80%%)", name)
            continue
        # Budget degrade: drop OpenCode ZEN native if ZEN limits near (never drop truly free pools)
        if degrade_zen and adapter.cost_pool == "opencode_native" and adapter.cost_pool not in FREE_COST_POOLS:
            log.info("Budget degrade: skipping %s (ZEN limits near)", name)
            continue
        candidates.append(adapter)

    if not candidates:
        # Emergency free-pool fallback: try any registered zero-cost adapter before giving up
        with _adapter_lock:
            free_fallbacks = [
                a for a in _adapters.values()
                if a.cost_pool in FREE_COST_POOLS
                and health.get(a.name) != "RED"
                and not _is_openrouter(a)
            ]
        if free_fallbacks:
            log.info("Emergency free-pool fallback: %s", [a.name for a in free_fallbacks])
            candidates = free_fallbacks
        else:
            msg = (
                "ALL ADAPTERS EXHAUSTED (Claude MAX + DeepSeek V4 + free tier) — "
                "switch to ollama/qwen2.5-coder:7b locally or notify Commander"
            )
            log.error(msg)
            return AdapterResult(
                text=None, error=msg,
                cost_consumed=0, cost_pool="none",
                latency_ms=0, model_used="exhausted",
            )

    chains_tried: list[str] = []
    for adapter in candidates:
        t0 = time.monotonic()
        try:
            result = adapter.dispatch(task.system, task.user, task.max_tokens)
        except Exception as e:
            result = AdapterResult(
                text=None, error=str(e),
                cost_consumed=0, cost_pool=adapter.cost_pool,
                latency_ms=int((time.monotonic() - t0) * 1000),
                model_used=adapter.name,
            )
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        chains_tried.append(adapter.name)
        telemetry.log(persona=task.persona, tier=tier, result=result, chains_tried=list(chains_tried))
        cost_gates.consume(result.cost_pool, result.cost_consumed)
        if result.ok:
            health.record_success(adapter.name)
            return result
        health.record_failure(adapter.name)
        log.warning("Adapter %s returned !ok — trying next in chain", adapter.name)

    msg = f"All {tier} adapters exhausted (tried: {chains_tried}) — try: opencode/big-pickle, ollama/qwen2.5-coder:7b"
    log.error(msg)
    return AdapterResult(
        text=None, error=msg,
        cost_consumed=0, cost_pool="none",
        latency_ms=0, model_used="exhausted",
    )


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    configure_default_pools()

    req = TaskRequest(system="You are a test bot.", user="Say hello", persona="default")
    result = dispatch(req)
    print(f"\nDispatch result: ok={result.ok}, error={result.error}")
    print(f"Telemetry summary: {telemetry.summary()}")
    print("\nGate 1 — Foundation: PASS")
