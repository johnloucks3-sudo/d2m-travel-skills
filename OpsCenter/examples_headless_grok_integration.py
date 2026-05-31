"""
Example: Integrating Headless Grok Build into Hale ZEN Workflows
=================================================================

Three common patterns for using headless Grok Build in the Thunderbird Wing.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from opencode_headless_grok_spawn import (
    spawn_grok,
    spawn_grok_custom,
    GrokSpawnConfig,
    SpawnMode
)


# ==============================================================================
# PATTERN 1: Async ZEN Counter-Voice (Fire-and-Forget)
# ==============================================================================
# Use case: Hale surfaces a strategic decision to the staff. While the room
# discusses, Grok analyzes in the background. Hale checks the log when ready.

def pattern_1_async_zen_counter():
    """Async Grok spawn for background analysis during meetings."""
    print("\n" + "=" * 70)
    print("PATTERN 1: Async ZEN Counter-Voice (Background Analysis)")
    print("=" * 70)

    decision_prompt = """
    The staff recommends using Opus 4.8 as the default synthesis model instead
    of Sonnet 4.6. They cite higher reasoning fidelity and claim the cost delta
    is acceptable. Push back: is this a cost-justified change? What's the
    actual token delta per 1K decisions? What are the hidden risks?
    """

    print("🧠 Dispatching to ZEN (Grok Build) for independent analysis...")
    result = spawn_grok(
        decision_prompt.strip(),
        model="xai/grok-build-0.1",
        blocking=False,  # Async — return immediately
        verbose=False
    )

    print(f"✓ Spawned: PID {result.pid}")
    print(f"  Log path: {result.log_path}")
    print(f"  Status: Running in background")
    print(f"  → Check log in ~10s for Grok perspective")

    return result.log_path


# ==============================================================================
# PATTERN 2: Blocking ZEN Counter-Voice (Immediate Perspective)
# ==============================================================================
# Use case: Hale needs a quick counter-perspective before a decision point.
# Wait for Grok, capture the response, surface to Chief immediately.

def pattern_2_blocking_zen_counter():
    """Blocking Grok spawn for immediate decision support."""
    print("\n" + "=" * 70)
    print("PATTERN 2: Blocking ZEN Counter-Voice (Immediate Response)")
    print("=" * 70)

    decision_prompt = """
    Should we continue routing routine tasks to OpenCode (cost ~$0.00) and
    reserve Claude Sonnet for synthesis-only work? Or should we add a middle
    tier—Claude Haiku—for structural tasks (code review, refactoring, testing)?

    Analyze: routing efficiency, token economics, quality loss risk.
    Recommend yes/no with reasoning.
    """

    print("🧠 Requesting ZEN perspective (blocking, 30s timeout)...")
    result = spawn_grok(
        decision_prompt.strip(),
        model="xai/grok-build-0.1",
        blocking=True,
        timeout=30,
        verbose=True
    )

    print(f"\n✓ Response received in {result.duration_sec:.1f}s")
    print("\n--- ZEN COUNTER-VOICE PERSPECTIVE ---")
    print(result.output)
    print("--- END ZEN ---\n")

    return result


# ==============================================================================
# PATTERN 3: Custom Model Selection (Advanced Reasoning)
# ==============================================================================
# Use case: The decision is complex and multi-step. Use grok-4.20-reasoning
# (if available) instead of grok-build-0.1 for deeper analysis.

def pattern_3_advanced_reasoning():
    """Use advanced Grok model for deep strategic analysis."""
    print("\n" + "=" * 70)
    print("PATTERN 3: Advanced Reasoning (Custom Model)")
    print("=" * 70)

    strategic_prompt = """
    Architectural critique: We're building a single-hop pipeline where client
    emails derive directly from primary sources (portal, TESS, dossier) instead
    of multi-hop memo chains. Pro: eliminates contamination. Con: loses the
    intermediate thinking layer. What emergent risks do we miss? What do we
    gain in reliability? Net: worth it?
    """

    config = GrokSpawnConfig(
        model="xai/grok-4.20-0309-reasoning",  # Advanced reasoning model
        mode=SpawnMode.BLOCKING,
        timeout=60,
        verbose=True
    )

    print("🧠 Requesting advanced reasoning analysis (60s timeout)...")
    result = spawn_grok_custom(config, strategic_prompt.strip())

    print(f"\n✓ Deep analysis completed in {result.duration_sec:.1f}s")
    print("\n--- ADVANCED REASONING OUTPUT ---")
    print(result.output)
    print("--- END ANALYSIS ---\n")

    return result


# ==============================================================================
# PATTERN 4: Integration with Hale Decision Journal
# ==============================================================================
# Use case: Log the ZEN perspective along with the final decision in
# hale_decisions.md for institutional memory.

def pattern_4_decision_journal_integration():
    """Capture ZEN perspective in decision log."""
    print("\n" + "=" * 70)
    print("PATTERN 4: Hale Decision Journal Integration")
    print("=" * 70)

    decision_prompt = """
    We're considering moving all internal email communication (staff papers,
    briefs, intel) to direct sends instead of drafts. Pro: faster, simpler.
    Con: loses audit trail. Counter: is this wise? What control do we lose?
    """

    print("🧠 Running ZEN counter-voice for decision journal...")
    result = spawn_grok(
        decision_prompt.strip(),
        blocking=True,
        timeout=30
    )

    # Simulate adding to hale_decisions.md
    decision_entry = f"""
## 2026-05-31 | Model Selection: Opus vs Sonnet Default

**Decision:** Keep Sonnet as default synthesis model. Defer Opus tier to
high-stakes judgment calls only.

**ZEN Counter-Voice (Grok Build):**
{result.output}

**Hale Assessment:** ZEN's cost delta concern is material. Recommended: retain
Sonnet for synthesis, add Haiku tier for structural tasks. Defers Opus
escalation to Commander discretion case-by-case.

**Status:** LOGGED | 2026-05-31 15:30 MT
"""

    print("✓ Decision entry ready for hale_decisions.md:")
    print(decision_entry)

    return decision_entry


# ==============================================================================
# INTEGRATION POINT: Hale's ZEN Auto-Dispatch
# ==============================================================================
# How this fits into the standing trigger: when a decision prompt contains
# "counter", "challenge", "devil's advocate", keyword_router detects it and
# routes to ZEN via opencode_zen_counter.py. That script now uses this
# headless spawn module under the hood.

def show_integration_flow():
    """Document the full flow."""
    print("\n" + "=" * 70)
    print("INTEGRATION FLOW: Keyword → ZEN Dispatch → Headless Grok")
    print("=" * 70)

    flow = """
    1. Hale encounters a decision requiring independent perspective
    2. Hale calls spawn_grok() or uses opencode CLI with "zen" keyword
    3. OpsCenter/keyword_router.py detects "counter"/"challenge" keywords
    4. Routes to ZEN via OpsCenter/opencode_zen_counter.py
    5. opencode_zen_counter.py uses this spawn module (async mode)
    6. Grok analyzes in background while Chief continues decision discussion
    7. Result logged to /tmp/opencode_grok_*.log
    8. Hale surfaces ZEN perspective to Chief via brief or decision journal
    9. Chief incorporates independent perspective before final decision

    Timeline: Decision → ZEN spawn (0s) → Discussion (5-10s) → ZEN ready
    Result: No blocking, full context available when needed.
    """

    print(flow)


# ==============================================================================
# RUN EXAMPLES
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("HEADLESS GROK INTEGRATION EXAMPLES")
    print("=" * 70)
    print("\nRunning 4 integration patterns...\n")

    # Pattern 1: Async
    log_path = pattern_1_async_zen_counter()

    # Pattern 2: Blocking
    result = pattern_2_blocking_zen_counter()

    # Pattern 3: Custom model (if available)
    try:
        result = pattern_3_advanced_reasoning()
    except Exception as e:
        print(f"⚠ Pattern 3 skipped (grok-4.20 may not be available): {e}")

    # Pattern 4: Decision journal
    entry = pattern_4_decision_journal_integration()

    # Show full integration
    show_integration_flow()

    print("\n" + "=" * 70)
    print("All patterns demonstrated. Ready for production integration.")
    print("=" * 70 + "\n")
