"""
Engine Limits Module.

Sub-agents spawned BY an engine draw against that SAME parent engine's pool, not a fresh one.
Caps are independent per engine — OC's cap is not AG's cap is not Claude's MAX budget.
"""

import json
import time
import os
from pathlib import Path

DEFAULT_CAPS = {
    'OC': {'hourly': 30, 'daily': 200},
    'AG': {'hourly': 20, 'daily': 150},
    # POE is not rate-limited, it is PREPAID and EXPIRING. Its cap is a spend
    # ceiling, not a throughput ceiling — see POE_* below.
    'POE': {'hourly': 10, 'daily': 40},
}

DEFAULT_LEDGER_PATH = Path("/home/john/Thunderbird/OpsCenter/engine_usage_ledger.jsonl")

# ── POE SPEND GUARD ───────────────────────────────────────────────────────────
# 2026-07-30: ~99,147 Poe points (~1/3 of the Commander's August reserve) were
# burned in five minutes by an agentic benchmark. The first version of this guard
# modelled Poe as billing a FLAT RATE PER MESSAGE BY TIER. That was WRONG.
#
# GROUND TRUTH, read from each bot's "Rates" panel on poe.com (bot page -> Rates):
# Poe bills PER TOKEN, split input/output, with a 90% discount on cached chat.
# That is WHY agentic runs are expensive: every turn re-sends the accumulated
# context, so a long run pays the input bill once per turn over a growing prompt.
# The fix is not "avoid expensive tiers" — it is "watch total tokens x turns".
#
# Rates below are points per 1,000 tokens, verified 2026-07-30.
POE_RATES = {  # model: (input_pts_per_1k, output_pts_per_1k)
    'poe/gemini-3.6-flash':                (50, 250),
    'poe/gemini-3.5-flash':                (50, 300),
    'poe/gemini-3.1-pro':                  (67, 400),
    'poe/claude-opus-5':                  (167, 834),
    'poe/claude-sonnet-4.6':              (167, 834),   # conservative: Opus-class until measured
    'poe/empiriolabs/deepseek-v4-flash-el': (50, 250),  # conservative estimate, unverified panel
    'poe/deepseek-v4-flash-e':             (50, 250),   # conservative estimate, unverified panel
    'poe/empiriolabs/deepseek-v4-pro-el': (167, 834),   # conservative: Pro-class until measured
}
POE_CACHE_DISCOUNT = 0.10   # cached input costs 10% of list

# Gemini-3.1-Pro sharp edges, from its own Rates panel:
#   - input rate 2x and output rate 1.5x when context exceeds 200k tokens
#   - prompt caching only applies when web search is DISABLED
# Web search on any Gemini bot bills ~467 points/search on top of tokens.
POE_SEARCH_COST = 467

# ── GEMINI: 3.6-FLASH IS THE DEFAULT, AND IT OUTRANKS 3.1-PRO ────────────────
# "Flash" reads like a downgrade. It is not. The Gemini Pro line has been FROZEN
# at 3.1 Pro since February 2026 — no 3.5 Pro or 3.6 Pro exists — while the Flash
# line kept shipping. Published benchmarks, 3.6-Flash vs 3.5-Flash vs 3.1-Pro:
#     SWE-Bench Pro     58.7%  /  55.1%  /  54.2%
#     DeepSWE v1.1      49%    /  37%    /  12%     <- long-horizon agentic
#     Terminal-bench2.1 78.0%  /  76.2%  /  73.8%
#     MLE-Bench         63.9%  /  49.7%  /  42.6%
#     GDPVal-AA v2 Elo  1421   /  1349   /  965
# 3.6-Flash wins every one, is CHEAPER (250 vs 300 vs 400 output pts/1k) and
# FASTER (304 vs 289 tok/s). Confirmed empirically here too: google/gemini-3.6-flash
# passed the repo benchmark twice and solved a dedup trap that claude-sonnet-4.6
# and the OC free model both got wrong, self-verifying with two regexes.
#
# So ESCALATING from 3.6-Flash to 3.1-Pro is a DOWNGRADE for coding/agentic work.
# 3.1-Pro is only preferable where it holds a published lead: deep scientific
# reasoning (GPQA Diamond 94.3%), abstract reasoning (ARC-AGI-2 77.1%), and
# vision (83.1% six-task avg). Route by that, not by the word "Pro".
GEMINI_ROUTE = 'google/gemini-3.6-flash'          # default: coding, agentic, general
GEMINI_REASONING = 'google/gemini-3.1-pro'        # ONLY for GPQA-class reasoning / vision
GEMINI_PREFER_VIA = 'google/'                     # not poe/ — see below

# Gemini via OpenCode's poe/ adapter is BROKEN — but Poe itself is FINE.
# Verified 2026-07-30: `opencode run --model poe/gemini-3.1-pro` returns
# "Internal server error" (4-11s), as do the 3.5-flash and google/-namespaced
# variants. BUT a direct POST to api.poe.com/v1/chat/completions with
# model="Gemini-3.1-Pro" returns HTTP 200 and correct content. The fault is
# OpenCode's Poe adapter, NOT Poe and NOT the model name.
# NOTE: Gemini-3.1-Pro is a REASONING model — a small max_tokens returns an EMPTY
# string because the whole budget goes to reasoning tokens (measured: 72 reasoning
# tokens for a 2-token answer). Always allow generous max_tokens.
POE_BROKEN_VIA_OPENCODE = {
    'poe/gemini-3.1-pro',
    'poe/google/gemini-3.1-pro',
    'poe/gemini-3.5-flash',
    'poe/google/gemini-3.5-flash',
    'poe/gemini-3.6-flash',       # absent from Poe's OC integration entirely
    'poe/deepseek-v3.2',          # historic "invalid request error"
}
POE_BROKEN = POE_BROKEN_VIA_OPENCODE  # back-compat alias
POE_DIRECT_API = 'https://api.poe.com/v1/chat/completions'  # the working path

# ── POE POINT-EXPIRY BURN-DOWN TARGET (Commander directive 2026-07-30) ────────
# Points above the 1.5M carryover cap evaporate when the ~600K monthly replenish
# lands (~19 Aug 2026). Commander target: draw the reservoir down to 800K-900K
# by 19 Aug so the replenish clears with margin under the cap and nothing is
# lost. Burn ONLY through POE_WHITELIST or Commander-approved models — do not
# add a candidate model to the whitelist without a measured per-message price
# (see check_poe_model's fail-closed rule above). Check status before final
# resource allocation on a project, not on every task.
POE_BURNDOWN_TARGET_DATE = '2026-08-19'
POE_BURNDOWN_TARGET_MIN = 800_000
POE_BURNDOWN_TARGET_MAX = 900_000
POE_HARD_CAP = 1_500_000  # never exceed this on/after the target date

# Poe models CC may route to without asking. Gemini is deliberately NOT here —
# it goes through google/ (see GEMINI_ROUTE). Everything else needs per-task
# Commander approval.
POE_WHITELIST = {
    'poe/empiriolabs/deepseek-v4-flash-el',
    'poe/deepseek-v4-flash-e',
    'poe/gemini-3.6-flash',   # cheapest + strongest Gemini; usable via POE_DIRECT_API only
}

# A run costing more than this needs Commander approval regardless of model.
POE_RUN_APPROVAL_THRESHOLD = 15_000

# Typical agentic-run shape, used to ESTIMATE cost before dispatch. These are the
# numbers to change if runs get longer or context grows.
POE_RUN_TURNS = 8
POE_RUN_INPUT_TOKENS = 15_000   # per turn — context is re-sent every turn
POE_RUN_OUTPUT_TOKENS = 800     # per turn


def estimate_poe_run(model: str, *, turns: int = POE_RUN_TURNS,
                     input_tokens: int = POE_RUN_INPUT_TOKENS,
                     output_tokens: int = POE_RUN_OUTPUT_TOKENS,
                     cached: bool = False, searches: int = 0) -> int | None:
    """Estimate points for one agentic run. None if the model has no known rate.

    Poe bills PER TOKEN, and an agentic run re-sends its context every turn — so
    cost scales with turns x context, not with a per-message tier. `cached=True`
    applies the 90% cached-input discount.
    """
    rate = POE_RATES.get(model)
    if rate is None:
        return None
    in_rate, out_rate = rate
    if cached:
        in_rate *= POE_CACHE_DISCOUNT
    per_turn = (input_tokens / 1000) * in_rate + (output_tokens / 1000) * out_rate
    return int(turns * per_turn + searches * POE_SEARCH_COST)


def check_poe_model(model: str, *, approved_by_commander: bool = False, **run) -> dict:
    """Gate a Poe model BEFORE dispatch. Returns {'ok', 'reason', 'est_points'}.

    Fails CLOSED on an unknown model: no measured rate means no spend. Read the
    rate from the bot's page on poe.com (bot page -> "Rates" button) and add it
    to POE_RATES. Never discover a price by spending — that mistake cost ~99,147
    points on 2026-07-30.
    """
    if not model.startswith('poe/'):
        return {'ok': True, 'reason': 'not a Poe model', 'est_points': 0}

    if model in POE_BROKEN_VIA_OPENCODE:
        alt = (f" Use {GEMINI_ROUTE} via google/, or call Poe directly at "
               f"{POE_DIRECT_API} with model='Gemini-3.1-Pro' — the OpenCode "
               "adapter is what is broken, not Poe." if 'gemini' in model else "")
        return {'ok': False,
                'reason': f"{model} fails via OpenCode's poe/ adapter (verified 2026-07-30).{alt}",
                'est_points': 0}

    est = estimate_poe_run(model, **run)
    if est is None:
        return {'ok': False,
                'reason': (f"{model}: no measured token rate. Open its page on poe.com, "
                           "click Rates, and add it to POE_RATES. Never discover a "
                           "price by spending."),
                'est_points': None}

    if approved_by_commander:
        return {'ok': True, 'reason': 'Commander-approved', 'est_points': est}

    if est >= POE_RUN_APPROVAL_THRESHOLD:
        return {'ok': False,
                'reason': (f"{model}: estimated {est:,} pts for this run, over the "
                           f"{POE_RUN_APPROVAL_THRESHOLD:,} approval threshold. "
                           "Commander approval required — this is a financial commit."),
                'est_points': est}

    if model in POE_WHITELIST:
        return {'ok': True, 'reason': f'whitelisted (~{est:,} pts/run)', 'est_points': est}

    return {'ok': False,
            'reason': f"{model} is not whitelisted (~{est:,} pts/run). Commander approval required.",
            'est_points': est}
