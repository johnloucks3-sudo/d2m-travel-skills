# OPENCODE → HEADLESS CLAUDE — MODEL CALLING & AVAILABILITY
*Canonical for model selection specifically. For the general spawn mechanics (OAuth, daemons, WRITE-path prompts), see `docs/OPENCODE_HEADLESS_CLAUDE_SIMPLE.md` and `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` — those still govern the spawn pattern. This doc governs which `--model` value to pass and what happens when that model isn't available.*

**Verified live 2026-07-08** by direct CLI probe (`claude --model <X> -p "..."`) — not asserted from memory.

---

## 1. Entry point — don't call the CLI yourself

OpenCode never builds a `subprocess.Popen(["claude", ...])` call or picks a model string by hand. Go through Layer 2:

```python
from OpsCenter.opencode_headless_claude_dispatch import dispatch_headless_claude
# or, for direct control:
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
```

Layer 2 (`opencode_headless_claude_dispatch.py`) calls `route_model()` to pick a model, then hands it to Layer 1 (`thunderbird_headless_spawn.spawn_headless_claude`), which is the only code allowed to touch OAuth credentials and build the subprocess. This doc is about the `model=` argument that flows through that chain.

---

## 2. Model calling — alias vs pinned name

The `claude` CLI (`/home/john/.local/bin/claude`, v2.1.204) accepts **two forms** for `--model`:

| Form | Example | Behavior |
|---|---|---|
| **Alias** | `sonnet`, `opus`, `haiku`, `fable` | Resolves to Anthropic's *current latest* release for that tier, at call time. Never goes stale. |
| **Pinned full name** | `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` | Locks to that exact snapshot forever, even after Anthropic ships a newer generation. Still works if the snapshot exists — it just quietly stops being "the latest." |

**Live-verified mapping, 2026-07-08:**

| Alias | Resolves to | Notes |
|---|---|---|
| `sonnet` | `claude-sonnet-5` | Default synthesis/reasoning/client-voice tier |
| `opus` | `claude-opus-4-8` | Flagship, use sparingly (cost) |
| `haiku` | `claude-haiku-4-5-20251001` | Fast/cheap, current default in the spawn wrapper |
| `fable` | `claude-fable-5` | Not currently used in Thunderbird routing; documented for completeness |

**Rule: use the alias, not a pinned snapshot, unless you specifically need reproducibility.** Thunderbird's own code had drifted onto hardcoded `claude-sonnet-4-6` / `claude-opus-4-7` in two live paths (the model router's `SONNET_MAX_LARGE` tier and the spawn wrapper's retry-escalation ladder) — both silently kept working on an old snapshot for weeks while "the latest Sonnet" moved on without them. **Fixed 2026-07-08** (see §5). Don't reintroduce the pattern: write `"sonnet"`, not `"claude-sonnet-4-6"`, in new code.

---

## 3. Model availability handling

Three layers of availability handling exist. Use the right one for the failure mode:

### a) `--fallback-model` (CLI-native, per-call)
```
--fallback-model <model>[,<model>...]
```
Only works with `--print`. Tries each listed model in order **when the primary is overloaded or not available**, and re-tries the primary at the start of each turn. This is the right tool for "Anthropic-side capacity issue," not for "I want a smarter model on retry" (that's §b).

```python
spawn_headless_claude(
    prompt=prompt,
    output_file=out,
    model="sonnet",
    extra_args=["--fallback-model", "haiku"],
)
```

### b) Wrapper retry-escalation (`thunderbird_headless_spawn._spawn_with_retry`)
On a failed/empty-output attempt (not an availability signal specifically — any retryable failure), the wrapper escalates up the tier ladder `haiku → sonnet → opus` and retries (2 retries, 3 attempts total). As of the 2026-07-08 fix this ladder uses aliases, so each escalation step always lands on the then-current release of that tier — it will never hand you a fixed old snapshot.

### c) Prerequisite gate (`verify_prerequisites()`)
Before any spawn, the wrapper hard-blocks (returns `status: "FATAL_PREREQ"`) if OAuth keepalive isn't running or `~/.claude/.credentials.json` is missing. This is *account* availability, not *model* availability — a distinct failure mode. Check `result["status"]` for `FATAL_PREREQ` vs `FATAL_CREDS` vs a model-level failure before assuming a model name is bad.

**Diagnosing a stuck call:** a hung/slow response is not necessarily a bad model string — transient latency happens (observed directly during this guide's verification pass: an alias call timed out once, succeeded immediately on retry). A genuinely invalid model name fails fast with a CLI error, it does not hang. If a call exceeds ~30–40s with no output, retry once before concluding the model ID is wrong.

---

## 4. Automatic model selection — `route_model()`

If OpenCode doesn't want to hardcode a model, call the router first:

```python
from core.ai_infra.thunderbird_model_router import route_model

route = route_model(task_type="client_email", budget="normal")
model = route["model_id"]   # e.g. "sonnet" for the SONNET_MAX_LARGE tier
```

`route_model()` also routes to non-Claude tiers (Gemini direct API, DeepSeek) for cost reasons on non-client-voice tasks — see `CREW_MODEL_TIER` in the same module for which A-staff persona maps to which tier. That routing logic is out of scope for this doc; the only thing relevant here is that **when it does pick a Claude tier, it now hands you an alias, not a stale pinned name.**

---

## 5. What was fixed 2026-07-08 (root cause, not just this doc)

Two live code paths were pinned to a Claude generation that was no longer "latest":

| File | Was | Now |
|---|---|---|
| `core/ai_infra/thunderbird_model_router.py` — `MODEL_STRATEGY[SONNET_MAX_LARGE]["model_id"]` | `"claude-sonnet-4-6"` | `"sonnet"` |
| `core/ai_infra/thunderbird_headless_spawn.py` — `_spawn_with_retry()` escalation ladder | `["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-7"]` | `["haiku", "sonnet", "opus"]` |

**Known residual debt (not fixed, documented per Obstacle-Routing protocol):** a repo-wide grep for `claude-sonnet-4-6` / `claude-opus-4-7` turns up ~150 files, the large majority inside the vendored `tools/omnigent/` package and one-off scripts, not the two live OpenCode/Hale dispatch paths above. Those two were the ones actually in OpenCode's call chain and are fixed. The rest is a currency/deadwood sweep, not a headless-spawn correctness issue — flagged for Whetstone (A14, tech-currency owner) rather than bulk-edited here.

---

## 6. Quick verification (run this if a model call ever looks wrong)

```bash
/home/john/.local/bin/claude --model sonnet -p "reply with exactly your model id and nothing else" --output-format text
/home/john/.local/bin/claude --model opus   -p "reply with exactly your model id and nothing else" --output-format text
/home/john/.local/bin/claude --model haiku  -p "reply with exactly your model id and nothing else" --output-format text
```

Each should return a `claude-*` model ID within a few seconds. If one hangs past ~40s, retry once before treating it as broken.
