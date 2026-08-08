# PROPOSAL — thunderbird-mcp recurrent restart (INC-20260807T150611Z-7410b8)

**From:** ELON · A12 Innovation & Disruption
**Date:** 2026-08-07 22:5x MT
**Trigger:** opscenter_watchdog `auto_healed` — recurrence_pattern, 36x in 7d
**Classification:** Infrastructure defect — not a memory leak

---

## BLUF

The 36 auto-heals are the visible 0.5% of the problem. Ground truth is **≈7,940 systemd
restarts, all inside one 34-hour window**, caused by two byte-identical systemd units
fighting over port 8765, each one SIGKILLing the other on startup. **The loop is live and
unremediated as of this writing**, adding ~2 restarts/min. Fix is a one-command change.
Separately, commit 44b908c99's "12h graceful restart" not only misdiagnosed this as a memory
leak — it installed a timer that will **stop MCP outright at 2026-08-08 10:03 MT** (F-4).

```
Watchdog reported   [█░░░░░░░░░░░░░░░░░░░]     36 restarts
Actual restarts     [████████████████████]  ≈7,940 restarts     (220x understated)
```

Denominators match: both counts are over the same 7-day journal window. Restarts in the 7d
*preceding* the incident = **0** (`--until '2026-08-06 12:00'`). 100% of churn is in the
34h window — 4,011 on `thunderbird-mcp` + 3,926 on `d2m-mcp`.

---

## ROOT CAUSE

`thunderbird-mcp.service` and `d2m-mcp.service` are **byte-identical files**
(both md5 `aaa521f00aeab9a785c635177686e59a`, both written 2026-08-02 15:25:19 by the same
deploy step). Both declare `ExecStart=... travel_mcp_server.py --http --port=8765` and,
critically, both declare `ExecStartPre=/bin/bash -c 'fuser -k 8765/tcp ...'`. `fuser -k`
sends **SIGKILL** by default and targets *whoever holds the port*, with no concept of which
systemd unit owns it. So each unit's startup is an unconditional execution order against the
other. Unit A starts → SIGKILLs B → B is `Restart=on-failure`/`RestartSec=10` → B restarts →
SIGKILLs A → A restarts → forever, at a ~21-second period (10s backoff + ~9-11s run). This
is a stable mutual-assassination equilibrium, not a degradation: the first principle being
violated is that *a liveness mechanism (`fuser -k`, `Restart=on-failure`, and two watchdogs)
was given authority over a resource it does not exclusively own*. Every recovery mechanism in
the stack is functioning exactly as designed and is, collectively, the disease. Memory is a
red herring — peak RSS is 210–310 MB against a 1 GB `MemoryMax`, flat across thousands of
cycles, zero growth trend, and zero kernel/`systemd-oomd` OOM events.

**Ignition:** 2026-08-06 12:27:29 MT. `d2m-mcp` is `disabled` with no wants-symlink, so it
never boots on its own — but `thunderbird_coo_watchdog.py` sweeps
`systemctl --user list-units --state=failed` and restarts any failed user unit up to 3x/hr,
and carries `d2m-mcp: 8765` in its own `SERVICE_PORTS` map. It ran clean for 45 seconds,
then took the first SIGKILL at 12:28:14 and has never recovered. Two watchdogs each own one
of the two duplicates: `opscenter_watchdog.py` restarts `thunderbird-mcp` (its 36 logged
auto-heals), `thunderbird_coo_watchdog.py` restarts `d2m-mcp`. Neither can see the other's
unit, so neither can ever diagnose a port co-owner.

---

## PROPOSED FIX

**`config_change`** — retire the duplicate unit, disarm the `fuser -k` weapon, and clean the
three inventories that would otherwise alarm on the retired unit.

---

## IMPLEMENTATION

All steps are user-scope systemd + repo config. No Commander gate applies (not client-send,
not financial, not >90d/>$5K). Standing doctrine "Fix Don't Ask Infra" governs.

**Step 1 — break the loop (immediate).**
```bash
systemctl --user stop d2m-mcp.service
systemctl --user mask d2m-mcp.service          # mask, not disable: blocks watchdog `start`
```
`mask` is required over `disable` — `d2m-mcp` was *already* `disabled` and still ran, because
`disable` only removes the boot symlink and does not block an explicit `systemctl start`.

```bash
systemctl --user reset-failed d2m-mcp.service  # clear it from the --state=failed list
                                               # that thunderbird_coo_watchdog.py sweeps
```
**Step 1 alone breaks the loop.** Steps 2–3 are hardening. Apply Step 1 first and confirm
counters go flat before bundling anything else, so a regression can be attributed.

**Step 2 — disarm `fuser -k` on the surviving unit (hardening, not the fix).**
Remove the `ExecStartPre` line from `~/.config/systemd/user/thunderbird-mcp.service`.
systemd already guarantees the prior `ExecStart` is dead before a restart; the line adds
nothing and re-arms the landmine for any future duplicate or manual run. Do the same in
`thunderbird-mcp-tailscale.service` (port 8768) for consistency — it is currently benign
only because nothing else contends for 8768.

**Step 3 — clean the inventories** so masking does not create a permanent false-alarm stream:
- `deploy/health_check.py:27` — drop `"d2m-mcp.service"`
- `scripts/preflight_gate.py:57` — drop `"d2m-mcp"`
- `OpsCenter/ai_auth_probe.py:342` — drop `"d2m-mcp.service"` from the tuple
- `OpsCenter/thunderbird_coo_watchdog.py:79` — repoint `SERVICE_PORTS` key `d2m-mcp` → `thunderbird-mcp`
- `OpsCenter/test_coo_watchdog.py` — 8 references use `d2m-mcp` as a fixture; repoint to the
  surviving unit or the tests will assert against a masked unit.

**Step 4 — reload and confirm.** `systemctl --user daemon-reload && systemctl --user restart thunderbird-mcp`

**Step 5 — reassess commit 44b908c99** (see Finding F-4; do not leave `thunderbird-mcp-gc`
running unexamined).

---

## VERIFICATION TEST

A point-in-time probe is insufficient — a single `systemctl is-active` would have returned
`active` at 22:50 in the middle of this loop. The test must be two-sided and time-windowed.

**1. Restart counters flat across a window ≥ 10 min** (~29 cycles at the old 21s period):
```bash
for u in thunderbird-mcp d2m-mcp; do echo "$u $(systemctl --user show $u.service -p NRestarts --value)"; done
sleep 600
for u in thunderbird-mcp d2m-mcp; do echo "$u $(systemctl --user show $u.service -p NRestarts --value)"; done
# PASS: both values identical before and after. Pre-fix delta was ~29.
```

**2. End-to-end MCP function, not port liveness.** Call the watchdog's own function directly,
so the probe and the alarm cannot disagree:
```bash
cd /home/john/Thunderbird && python3 -c \
  "from OpsCenter.opscenter_watchdog import _check_mcp_responding; print(_check_mcp_responding())"
# PASS: True   (asserts a JSON-RPC tools/list with >50 tools)
```
Do **not** substitute a hand-rolled `curl`. A bare `POST /mcp` with `tools/list` returns an
empty body even on a fully healthy server — streamable-HTTP MCP requires an `initialize`
handshake first. Verified this run: bare curl = empty, `_check_mcp_responding()` = **True**
on the same live server. `GET /health` returns **404** and is likewise not a valid probe
(F-5).

**3. Duplicate provably cannot return:**
```bash
systemctl --user is-active d2m-mcp.service     # expect: inactive
systemctl --user is-enabled d2m-mcp.service    # expect: masked
systemctl --user start d2m-mcp.service         # expect: FAILS — "Unit is masked"
```

**4. Single owner of 8765:** `ss -tlnp | grep 8765` returns exactly one PID, and that PID
equals `systemctl --user show thunderbird-mcp.service -p ExecMainPID --value`.

**5. Alarm stream quiet:** no new `auto_healed`/`thunderbird-mcp` events for 24h, and
`deploy/health_check.py` + `scripts/preflight_gate.py` both exit clean (no d2m-mcp failure).

---

## FINDINGS (complete list — confidence / severity, per ADHD full-coverage doctrine)

| # | Finding | Conf | Sev |
|---|---|---|---|
| F-1 | Duplicate identical units `thunderbird-mcp` / `d2m-mcp` both bind 8765; `fuser -k` (SIGKILL) in each `ExecStartPre` creates a mutual-kill loop. **7,875 restarts / 34h.** | Confirmed | 🔴 Critical |
| F-2 | `~/.config/systemd/user/service.d/thunderbird-mcp-memory-override.conf` is documented as "per-unit" but sits in the **fleet-wide** `service.d/` dir, not `thunderbird-mcp.service.d/`. Sorting last, it raises `MemoryMax` 256MB→1GB for **every user service on the box**. This is the exact failure the `00-` file's own comment warns against. | Confirmed | 🔴 High |
| F-3 | `OnFailure=thunderbird-generic-remediate@%N.service` is also fleet-wide, so all 7,875 failures dispatched a remediation unit. Even if it no-ops on Lane-1-owned units, that is ~7,875 wasted process spawns in 34h. | Confirmed | 🟡 Med |
| F-4 | `thunderbird-mcp-gc.service` is `Type=oneshot` with `ExecStart=systemctl --user restart thunderbird-mcp` **and** `ExecStop=systemctl --user stop thunderbird-mcp`. A oneshot goes inactive right after ExecStart, which fires ExecStop — a plausible self-inflicted 12h **stop**, not a restart. Next fire 2026-08-08 10:03 MT. Verify before that time. | Plausible | 🔴 High |
| F-5 | `GET /health` on 8765 returns 404. Any probe or dashboard using `/health` as a liveness check is structurally unable to detect a down MCP. Correct path is `POST /mcp` JSON-RPC. | Confirmed | 🟡 Med |
| F-6 | Live `POST /mcp tools/list` returned an **empty body** during this investigation. If the watchdog's `_check_mcp_responding()` is failing this way continuously, its 36 "auto-heals" were reacting to a broken probe, not a broken server. Needs a clean-state retest post-fix. | Unverified | 🟡 Med |
| F-7 | `StartLimitBurst=5 / StartLimitIntervalSec=60` never fired — counter reached 5 over 83s and reset. The breaker is structurally incapable of arresting any loop slower than 12s/cycle, and will remain ineffective after this fix. | Confirmed | 🟡 Med |
| F-8 | `opscenter_watchdog.py` emitted `auto_heal_succeeded: true` 36 times for a service in permanent crash loop. Success is measured as "restart command returned 0," not "service stayed up." | Confirmed | 🟡 Med |
| F-9 | Two independent watchdogs (`opscenter_watchdog.py`, `thunderbird_coo_watchdog.py`) each own one duplicate unit and are mutually blind. No single component can see both co-owners of port 8765. | Confirmed | 🟡 Med |
| F-10 | Commit 44b908c99 ("arrest crash-loop via 12h graceful restart + lazy-load wrapper") misdiagnosed a port conflict as a memory leak. Evidence against leak: flat 210–310MB peak vs 1GB cap, no OOM events, no growth trend. | Confirmed | 🟢 Low |
| F-11 | `d2m-mcp` was `disabled` yet ran for 34h — `disable` does not block an explicit `start`. Any "we disabled it" remediation in this repo carries the same false-confidence flaw. | Confirmed | 🟢 Low |

---

## OPINION

The interesting failure here is not the duplicate unit — that is a routine deploy bug. It is
that **five layers of self-healing (two watchdogs, `Restart=on-failure`, fleet-wide
`OnFailure=` remediation, and a 12h GC timer) all fired correctly and collectively sustained
the outage for 34 hours**, while the reporting layer showed "36 auto-heals, succeeded: true."
The system's immune response was the pathology, and its instrumentation was calibrated to
report the immune response as health. Redundant healers without a shared, exclusive notion of
resource ownership do not add reliability; they multiply it into a feedback loop. F-2 and F-3
show the same structural error twice more: drop-ins written *as if* per-unit that are in fact
fleet-wide. That pattern — local intent, global blast radius — is worth a dedicated audit of
`~/.config/systemd/user/service.d/` beyond this incident.

The 218x gap between reported (36) and actual (7,875) is the metric that should change. An
auto-heal that has fired 36 times in 7 days for one service is not a success statistic; it is
an unresolved defect with a counter on it. **Recommend a standing rule: >3 auto-heals for the
same service in 24h escalates as a defect and suppresses further auto-heal, rather than
continuing to heal silently.** That rule alone would have surfaced this on 2026-08-06.

---

## RECOMMENDATION

1. Execute Implementation Steps 1–4 now. (~5 min, reversible via `systemctl --user unmask`.)
2. Verify F-4 **before 2026-08-08 10:03 MT** — the GC timer may stop MCP outright.
3. Fix F-2 by moving the memory override to a true `thunderbird-mcp.service.d/` dir; audit
   the rest of the fleet-wide `service.d/` for the same class of error.
4. Adopt the >3-auto-heals-in-24h escalation rule (F-8).

---

# HALE DECISION

**APPLY_AUTONOMOUSLY** — Steps 1–4.

Rationale: infrastructure repair, user-scope systemd only, fully reversible
(`systemctl --user unmask d2m-mcp.service` restores prior state). None of the Three Gates
apply — no client send, no financial commitment, no >90d/>$5K strategic commitment. Standing
doctrine "Fix Don't Ask Infra" applies directly.

**Carve-out — QUEUE_FOR_COMMANDER:** Finding F-2 (fleet-wide memory ceiling silently raised
256MB→1GB for every user service). Correcting it lowers the effective limit on ~40 unrelated
production units simultaneously and could induce OOM kills across the fleet. That is a
blast-radius decision, not a repair. Recommend it be scheduled with a canary, not applied
inline with this fix.

**Cross-engine verification required before closing** per SO 2026-07-19 (CC Integrity
Double-Check): dispatch AG or OC to independently confirm restart counters are flat and
`tools/list` returns >50 tools, via `integrity_check.verify_and_record()`. This proposal's
claims are drawn from live `systemctl`/`journalctl`/`ss` output at 2026-08-07 22:4x–22:5x MT
and have **not** yet been cross-engine verified.
