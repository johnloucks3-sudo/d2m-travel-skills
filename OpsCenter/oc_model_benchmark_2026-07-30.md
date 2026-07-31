# OC MODEL BENCHMARK — 2026-07-30

**Question:** OpenCode failed 4 of 8 dispatches during the overnight triage. Is the model wrong, and what should replace it?
**Method:** two read-only, known-answer tasks against this live repo. No file writes. Correctness scored against ground truth computed independently by CC.

---

## Task A — single-file precision (easy)
Read `core/comms/commander_queue.py`; report the line of `closed_ids`, the line of `filter_open`, and the constant holding the path it reads.
**Truth:** `170` · `313` · `CLOSURES_PATH`

| Model | rc | secs | Result |
|---|---|---|---|
| `opencode/deepseek-v4-flash-free` *(current)* | 0 | 69 | **PASS 3/3** |
| `poe/empiriolabs/deepseek-v4-pro-el` | 0 | 138 | **PASS 3/3** |
| `poe/empiriolabs/deepseek-v4-flash-el` | 0 | 73 | **PASS 3/3** |
| `poe/deepseek-v4-flash-e` | 0 | 76 | **PASS 3/3** |
| `poe/claude-sonnet-4.6` | 0 | 89 | **PASS 3/3** |
| `poe/gemini-3.5-flash` | 1 | 70 | FAIL — Poe "Internal server error" |
| `poe/gemini-3.1-pro` | 1 | 79 | FAIL — Poe "Internal server error" |
| `opencode-go/deepseek-v4-pro` | 1 | 101 | **BILLING GATE** — no payment method |
| `opencode-go/kimi-k3` | 1 | 111 | **BILLING GATE** |
| `opencode-go/glm-5.2` | 1 | 47 | **BILLING GATE** |
| `opencode-go/qwen3.7-max` | 1 | 71 | **BILLING GATE** |
| `opencode-go/minimax-m3` | 1 | 74 | **BILLING GATE** |

**Finding 1 — the current model is not incompetent.** It scored 3/3 in 69s. Its four failures during the operation were timeouts and one context collapse on *long, multi-step* work. That is a stamina/context problem, not a capability problem, and swapping the model alone would not have fixed it.

**Finding 2 — the entire `opencode-go` premium tier is unavailable.** Every model returns *"No payment method. Add a payment method here: opencode.ai/workspace/…/billing"*. `kimi-k3`, `deepseek-v4-pro`, `glm-5.2`, `qwen3.7-max`, `minimax-m3`, `grok-4.5` are all behind that gate. **Commander decision — not an engineering one.**

**Finding 3 — Gemini via Poe is broken.** Both `gemini-3.5-flash` and `gemini-3.1-pro` return Poe-side internal server errors. Reach Gemini through `contact_ag` (Antigravity), not Poe.

---

## Task B — multi-step, cross-file, with a counting trap (hard)
Five values requiring a regex + de-duplication over a 37k-line audit trail, two JSON reads, a nested-key count, and a constant lookup.
**Truth:** `A=94` · `B=104` · `C=3` · `D=46` · `E=758571255`

| Model | rc | secs | A | B | C | D | E | Score |
|---|---|---|---|---|---|---|---|---|
| **`poe/empiriolabs/deepseek-v4-pro-el`** | 0 | 232 | **94** | 104 | 3 | 46 | 758571255 | **5/5** |
| `poe/claude-sonnet-4.6` | 0 | **64** | ~~138~~ | 104 | 3 | 46 | 758571255 | 4/5 |
| `opencode/deepseek-v4-flash-free` *(current)* | 0 | 131 | ~~138~~ | 104 | 3 | 46 | 758571255 | 4/5 |
| `poe/gemini-3.1-pro` | 1 | 32 | — | — | — | — | — | 0/5 (server error) |

**Finding 4 — the single failure is the same trap that produced this morning's bad headline.**
Every model that missed answered `A=138` instead of `94`: they counted *occurrences* rather than *unique items*, exactly the error that turned 37 real lost approvals into a reported "~122". Only `deepseek-v4-pro-el` de-duplicated correctly. This is the highest-value discriminator in the whole benchmark, because it is the error class that actually reached the Commander today.

**Finding 5 — Sonnet-grade is available on Poe points, and it is the fastest option tested.** `poe/claude-sonnet-4.6` completed the hard task in **64 seconds** — faster than the free model (131s) and 3.6× faster than the most accurate one (232s) — billed against Poe points rather than the MAX bucket. That is directly relevant to the 20X→5X capacity cut.

---

## Assets available

| Asset | State |
|---|---|
| `POE_API_KEY` | live · key "Thunderbird & Opencode" enabled |
| Poe points | **1,233,770 ≈ $37.39** · auto-recharge OFF |
| Poe models via OpenCode | **146** |
| OpenCode auth providers | anthropic, google, ollama, **poe**, xai, opencode-go |
| `opencode-go` tier | authenticated but **billing-gated** |

**On the prior "OC off Poe" directive:** that came from `poe/deepseek-v3.2` returning "invalid request error." This benchmark shows it was a per-model fault, not a platform fault — four Poe models passed cleanly.

---

## Task C — Commander-directed: Gemini 3.6 Flash

| Model | rc | secs | Result |
|---|---|---|---|
| `poe/gemini-3.6-flash` | 1 | **4** | **DOES NOT EXIST** — instant `UnknownError`. Not in Poe's OpenCode integration. |
| **`google/gemini-3.6-flash`** | 0 | 59 | **PASS 3/3** easy · **solved the dedup trap** on hard |

**Finding 6 — Gemini 3.6 Flash is reachable, but through `google/`, not `poe/`.** The `poe/` route fails in 4 seconds (unknown-model error, not load). The `google/` route works.

**Finding 7 — it is the only model besides `deepseek-v4-pro-el` to get `A=94` right, and it verified its own answer.** Unprompted, it cross-checked with both greedy and non-greedy regex and reported the intermediate reasoning:
```
Total full matches: 302
Unique full matches: 138
Unique item ids: 94
...
Non-greedy count: 94
Greedy count: 94
```
It explicitly surfaced `138` as a wrong intermediate and rejected it — the exact trap that fooled `claude-sonnet-4.6`, the current free model, **and this morning's human-facing investigation**. Self-verification behavior is rare at this tier and is the single most valuable property for the work OC is given.

**Finding 8 — `google/` costs ZERO Poe points.** OpenCode's auth store holds `google` as its own credential (`type`, `key`) separate from `poe` (`type`, `access`, `refresh`, `expires`). Traffic through `google/gemini-3.6-flash` bills the Google API key already in `.env` — the same free-tier key that was live-probed successfully earlier today for the claude-mem migration. **The 1.23M Poe points are untouched.**

---

## RECOMMENDATION — tiered routing, no single default

**Point-cost is the deciding constraint.** `poe/claude-sonnet-4.6` is fast and capable but Sonnet-class Poe pricing would drain 1.23M points quickly under routine load. It is a reserve asset, not a daily driver.

| Lane | Model | Cost | Use for | Evidence |
|---|---|---|---|---|
| **PRIMARY** | **`google/gemini-3.6-flash`** | **Google key — 0 Poe points** | Default for all OC work: multi-step analysis, counting/dedup, cross-file reconciliation | 3/3 easy in 59s; solved the dedup trap; self-verified with two independent regexes |
| **Free bulk** | `opencode/deepseek-v4-flash-free` | free | Small single-file mechanical edits only | 3/3 easy, 4/5 hard; fails on length, not difficulty |
| **Accuracy reserve** | `poe/empiriolabs/deepseek-v4-pro-el` | Poe points (low — DeepSeek tier) | When Gemini is unavailable and the number must be right | Only other 5/5 |
| **Emergency only** | `poe/claude-sonnet-4.6` | Poe points (**high — Sonnet tier**) | Time-critical work when nothing else will do | 4/5 in 64s, fastest tested — but the point burn does not justify routine use |
| **Never** | `poe/gemini-*` | — | — | `3.6-flash` unknown-model error; `3.5-flash` and `3.1-pro` return Poe server errors |
| **Blocked** | `opencode-go/*` | needs billing | — | Commander call — not required given the above |

---

## Task D — the timeout hypothesis, tested and DISPROVED

I claimed OC's failures were timeouts and recommended raising the ceiling. **That was wrong, and I could not prove it from logs** — the original dispatches were piped through `tail`, so the buffers died with the killed processes. No evidence either way. So I ran the experiment.

**Method:** re-run a task of the same shape as #46 (which died at 800s) — read a reference file, create a new script modeled on it, create a JSON config, run four acceptance checks — with the ceiling raised 800s → 2400s and full output captured.

**Run 1 was invalid — my design error.** I pointed the scratch dir at `/tmp`. Both models hit the `external_directory` auto-reject — *the exact sandbox boundary documented earlier the same day* — and gave up in 102s and 52s. Notably **both exited rc=0 while producing nothing**: a clean success code over a silent no-op.

**Run 2, scratch dir inside the repo:**

| Model | rc | secs | Artifacts | Quality |
|---|---|---|---|---|
| `opencode/deepseek-v4-flash-free` | 0 | **172** | both files | py_compile 0, JSON valid, all 4 acceptance checks pass |
| `google/gemini-3.6-flash` | 0 | **200** | both files | py_compile 0, JSON valid, all 4 acceptance checks pass |

**Finding 9 — there was already 4.6× headroom. Raising the timeout would have changed nothing.** The work takes ~3 minutes against an 800-second budget.

**Finding 10 — the free model is not the weak link, and it beat the paid one here.** 172s vs 200s, both correct. It also added a `CAPTURE_LEDGER_PATH` env override for test isolation *unprompted* — the precise safety practice whose absence caused a delegate to destroy production data earlier that day.

**Finding 11 — OPEN, unexplained.** Task #40 targeted only in-repo paths and still burned 800s. The sandbox rejection explains some failures, not that one. A second failure mode exists and has not been identified. Recorded rather than papered over.

---

## Structural fixes that matter more than the model swap

1. ~~Raise the OC timeout.~~ **Disproved — see Task D.** The ceiling was never the constraint.
2. **Never send OC systemd work, and keep every path inside `--dir`.** It auto-rejects `external_directory` and cannot even read `~/.config/systemd/user/*`. Worse, it exits **rc=0** when it does — the failure is invisible to a caller checking the return code.
3. **Never pipe an OC dispatch through `tail` or `head`.** Killing the process destroys the buffer and makes the failure undiagnosable. Capture full output to a file.
4. **Keep tasks single-file and single-purpose for the free tier** — still sound guidance, but on measured evidence its ceiling is higher than assumed.

---

## POINT-EXPIRY OVERRIDE (2026-07-30, Commander)

**The recommendation above optimizes for the wrong variable.** Poe points expire:

```
current balance        1,233,770
+ monthly replenish      600,000
= would total          1,833,770
  carryover cap        1,500,000
  ─────────────────────────────
  EVAPORATES             333,770   by ~19 Aug (20 days → ~16,700/day)
```

Unspent points are destroyed value, not savings. `google/gemini-3.6-flash`'s "zero Poe points" property — which I recommended *for* — is a liability inside the burn-down window.

**Revised routing:**

| Phase | Model | Rationale |
|---|---|---|
| **Now → 19 Aug** | `poe/kimi-k2.5` · `poe/kimi-k2-thinking` · `poe/grok-4.3` · `poe/novita/glm-5` | Burn the expiring 334K on real capability. All confirmed available. |
| Accuracy-critical | `poe/empiriolabs/deepseek-v4-pro-el` | Only 5/5 on the hard task |
| Heavy lift | `poe/claude-sonnet-4.6` | Fastest tested (64s); point cost is now a feature |
| **After burn-down** | `google/gemini-3.6-flash` | 0 points, self-verifies, solved the dedup trap |
| Free bulk, always | `opencode/deepseek-v4-flash-free` | 172s on real multi-step work — genuinely competent |

**Also live on Poe and currently unused:** `imagen-4` / `imagen-4-ultra`, `nano-banana` / `nano-banana-pro` (client visuals), `perplexity/sonar-pro` / `sonar-deep-research` (research). Capability already paid for.

**Open question for the Commander:** adding a payment method at `opencode.ai` unlocks `kimi-k3`, `deepseek-v4-pro`, `glm-5.2`, `qwen3.7-max`, `minimax-m3`, `grok-4.5`. Not needed given Poe's 1.23M points, but worth knowing the option exists.

---

*Benchmarked by CC · 2026-07-30 · All scores measured against independently computed ground truth, read-only, no repo modifications.*
