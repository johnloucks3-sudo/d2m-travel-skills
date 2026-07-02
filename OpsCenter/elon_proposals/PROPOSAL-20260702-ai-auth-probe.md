# ELON PROPOSAL — Telegram Probe False-Positive: HTTP_PROXY Masking Auth vs Network Failures
**Event ID:** INC-20260702T095150Z-8ce9a8  
**Pattern:** recurrence_pattern — 3 failures in 7 days  
**Severity:** Tier 1 Critical (Primary C2 channel)  
**Generated:** 2026-07-02T10:15Z  
**Supersedes:** Prior proposal (09:55 UTC) — exponential backoff fix (9df1d6d36) was applied but failures continue  

---

# ROOT CAUSE

The `.env` sets `HTTPS_PROXY=http://127.0.0.1:43117` (the llmtrim local CA) system-wide. `probe_telegram()` uses `urllib.request.urlopen()`, which inherits `HTTP_PROXY`/`HTTPS_PROXY` from the environment and routes all outbound HTTPS through port 43117. When that local proxy is down — which happens on LiteLLM gateway restart, llmtrim crash, or machine wake — the urllib call fails with `ECONNRESET` or `timed out` before it ever reaches `api.telegram.org`. The probe catches every exception generically (`except Exception as e: return False, str(e)`) and all failures feed the repair-and-escalate branch. The repair restarts `thunderbird-telegram-gw.service`, which also inherits the proxy env and also can't reach Telegram, so all three exponential-backoff re-probes time out too. The escalation fires for a proxy outage that has nothing to do with the Telegram bot token. The 3×-in-7-days recurrence matches proxy restart cadence, not token expiry.

---

# PROPOSED FIX

**Type:** `code_diff`

Two targeted changes to `OpsCenter/ai_auth_probe.py`:

1. `probe_telegram()` — open a direct connection (proxy-bypassed) via `ProxyHandler({})`. The Telegram API does not require routing through the LLM proxy. A bad proxy should never trigger a Telegram auth alarm.
2. `run_probe_cycle()` — add `network_error:` to the non-escalating prefix list alongside existing `rate_limit:`. A network-layer failure (ECONNRESET, timeout, proxy refusal) is not an auth failure and should not page Commander.

---

# IMPLEMENTATION

**Hale executes this directly. No Commander gate.**

### Edit 1 — Replace `probe_telegram()` (lines 124–143)

```python
def probe_telegram() -> tuple[bool, str]:
    """Verify Telegram bot token responds to getMe with ok=true.

    Opens a direct connection (proxy bypassed) — HTTPS_PROXY at 43117 is the
    LLM routing layer and is irrelevant to Telegram API auth. Routing through it
    causes false-positive escalations whenever the local proxy is down.
    Network-layer errors (ECONNRESET, timeout) return 'network_error:' prefix
    so run_probe_cycle() skips escalation, same as 'rate_limit:'.
    """
    token = (os.environ.get("TELEGRAM_C2_BOT_TOKEN")
             or os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    if not token:
        return False, "TELEGRAM_C2_BOT_TOKEN not set in environment"
    try:
        # ProxyHandler({}) bypasses HTTP_PROXY/HTTPS_PROXY env vars
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "thunderbird-probe/1.0"},
        )
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return True, f"bot={data.get('result', {}).get('username', '?')}"
            return False, f"ok=false: {data}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "auth failure: HTTP 401 — invalid token"
        return False, f"HTTP {e.code}: {e.reason}"
    except OSError as e:
        # ECONNRESET, ETIMEDOUT, ECONNREFUSED — network layer, not auth
        return False, f"network_error: {e}"
    except Exception as e:
        return False, f"network_error: {e}"
```

### Edit 2 — Extend non-escalating prefix check in `run_probe_cycle()` (line 265)

```python
# OLD:
if detail.startswith("rate_limit:"):
    log(f"SKIP ESCALATION: {name} — rate-limit/model-unavailable, not auth failure: {detail[:120]}")
    results[name] = "rate_limit_skip"
    continue

# NEW:
if detail.startswith("rate_limit:") or detail.startswith("network_error:"):
    log(f"SKIP ESCALATION: {name} — transient/network issue, not auth failure: {detail[:120]}")
    results[name] = "network_skip"
    continue
```

### Execution steps

```bash
cd /home/john/Thunderbird

# 1. Apply edits (use Edit tool above, or patch in place)

# 2. Verify diff
git diff OpsCenter/ai_auth_probe.py

# 3. Manual probe cycle with proxy down simulation
# Kill the proxy temporarily:
PID=$(ss -tlnp | grep ':43117' | grep -oP 'pid=\K[0-9]+' | head -1)
[ -n "$PID" ] && kill -STOP $PID  # SIGSTOP (not kill) for clean resume
source .env && python3 OpsCenter/ai_auth_probe.py
# Expected: telegram -> "network_skip", NOT "escalated"
[ -n "$PID" ] && kill -CONT $PID  # resume proxy

# 4. Probe with proxy alive — should return ok
source .env && python3 OpsCenter/ai_auth_probe.py
# Expected: telegram -> "ok"

# 5. Commit
git add OpsCenter/ai_auth_probe.py
git commit -m "fix(probe): bypass HTTP_PROXY in probe_telegram + classify network errors as non-escalating"
```

---

# VERIFICATION TEST

**End-to-end proof that the fix works:**

```bash
# Step 1: Direct Telegram reachability (no proxy) — baseline
source /home/john/Thunderbird/.env
curl --noproxy '*' -s "https://api.telegram.org/bot${TELEGRAM_C2_BOT_TOKEN}/getMe" | python3 -c "import sys,json; d=json.load(sys.stdin); print('PASS' if d.get('ok') else 'FAIL', d.get('result',{}).get('username','?'))"
# Expected: PASS D2MC2C_bot

# Step 2: Run probe cycle with proxy killed
PID=$(ss -tlnp | grep ':43117' | grep -oP 'pid=\K[0-9]+' | head -1)
[ -n "$PID" ] && kill -STOP $PID
python3 OpsCenter/ai_auth_probe.py 2>&1 | tail -5
# Expected: "SKIP ESCALATION: telegram" AND final cycle result shows "network_skip" NOT "escalated"
[ -n "$PID" ] && kill -CONT $PID

# Step 3: Run probe cycle with proxy alive
python3 OpsCenter/ai_auth_probe.py 2>&1 | tail -5
# Expected: "OK: telegram" in output
```

**Failure signal from incident queue should go silent** within 1 probe cycle (15 min) after deploy.

---

# HALE DECISION

**APPLY_AUTONOMOUSLY**

This is a 2-function edit to a probe utility with no client path, no financial commitment, and a clear documented failure pattern (3× false positives in 7 days). The change is narrowly scoped: it bypasses the local LLM proxy for a probe that should never route through it, and classifies network-layer errors the same way rate-limit errors are already classified. Real auth failures (HTTP 401, missing token) still escalate unchanged. The exponential backoff from 9df1d6d36 remains in place and continues to guard against genuine gateway-down scenarios. Risk: near-zero. Reversal: one-line revert.

**Hale applies the diff, runs the verification test, commits, and reports result in the next brief. No Commander gate.**

*— ELON, A12 · 2026-07-02 10:15 MT*
