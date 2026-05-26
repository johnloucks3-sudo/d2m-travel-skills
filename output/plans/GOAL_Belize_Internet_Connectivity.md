# GOAL — Belize Internet Connectivity: Always-On, Self-Healing
**Classification:** T2 Wing Exercise | **Owner:** A7 Sterling (design) · Hale (execution) · Commander (hardware)
**Created:** 2026-05-26 | **Deadline:** 2026-08-31

---

## 1. OBJECTIVE

Belize internet connectivity — always-on, self-healing. Commander must be able to run D2M operations from Belize without interruption, regardless of WAN hiccups or YOGA reboots.

**Business context:** September 2026 (1-week recon trip) and December 29 (25-day Miami→LA Panama Canal transit). During the December trip: McLeod voyage active, Kuklinski party of 8 traveling. Business continuity is non-negotiable on both trips.

---

## 2. TRIGGER

Commander departs for Belize — **September 2026** (first gate) and **December 29, 2026** (hard gate, 25-day duration).

---

## 3. SUCCESS CRITERIA

| # | Criterion | Measure |
|---|-----------|---------|
| 1 | WAN outage self-heals | < 5 minutes, no Commander intervention |
| 2 | YOGA reachable from Belize after going dark | < 10 minutes (WoL or cloud fallback) |
| 3 | All three components tested end-to-end | Passing simulation before 2026-08-31 |

---

## 4. SCOPE IN

| Component | What It Does |
|-----------|-------------|
| **Router firmware (OpenWRT)** | WAN watchdog — detects loss, auto-reboots modem/router. Directly addresses May 2026 outage (which required only a router reboot). |
| **Wake-on-LAN (WoL)** | Commander sends magic packet from Belize → YOGA wakes/recovers from hung state. Wired WoL (eno1) after ethernet adapter purchase; WoWLAN (wlp2s0, RTL8852CE) as interim. |
| **Cloudflare tunnel health** | Monitor tunnel status, auto-restart on failure. Tunnel must stay live for code.d2mluxury.quest and all exposed services. |

---

## 5. SCOPE OUT

| Excluded | Reason |
|----------|--------|
| Backup ISP / cellular failover | Out of scope — single-ISP Conexon Connect fiber |
| Cloudflare replacement | Keep as-is — not a problem to solve |
| Replacing YOGA hardware | Commander willing to travel with YOGA if home-alone risk assessment fails — but that's a fallback decision, not a planned scope item |

**Note on May 2026 outage:** Root cause was a simple router reboot — no ISP fault, no Cloudflare fault. OpenWRT WAN watchdog directly prevents recurrence at zero ongoing cost.

---

## 6. OWNERSHIP

| Role | Owner | Scope |
|------|-------|-------|
| Design | A7 Sterling | Architecture decisions, firmware selection, config specs |
| Execution | Hale | SSH tasks, config files, service installs, testing |
| Hardware | Commander | Physical installs: ethernet adapter, smart plug, router flash if needed |

---

## 7. DEADLINE

**Hard deadline: August 31, 2026** — all components tested and proven before September departure.

| Phase | Target | Deliverable |
|-------|--------|-------------|
| Now | 2026-05-31 | WoWLAN enabled (interim WoL), suspend policy set |
| June | 2026-06-15 | Router model confirmed, OpenWRT compatibility check |
| July | 2026-07-15 | Ethernet adapter purchased, wired WoL tested |
| August | 2026-08-15 | OpenWRT flashed (if compatible), tunnel health monitor active |
| Pre-trip | 2026-08-31 | Full simulation: YOGA dark → recover from Belize network |

---

## 8. COST CEILING

**Under $100 hardware spend** (Commander-approved).

| Item | Est. Cost | Priority |
|------|-----------|----------|
| USB-C to Ethernet adapter | ~$15-25 | HIGH — required for wired WoL |
| TP-Link Kasa EP25 smart plug | ~$15 | HIGH — hard power-cycle if YOGA truly hangs |
| Replacement router (if current not OpenWRT compatible) | ~$40-60 | MEDIUM — only if needed |

---

## 9. DEPENDENCIES

| Dependency | Blocks |
|------------|--------|
| Router model confirmed (MAC cc:28:aa:5b:4e:90, TP-Link, Conexon Connect fiber) | OpenWRT flash |
| Ethernet adapter purchased and plugged in | Wired WoL test |
| Conexon Connect fiber stable as baseline | All tests meaningful |

---

## 10. EXIT CONDITIONS

**Good exit (goal achieved):**
- All three components (router firmware, WoL, tunnel health) tested and passing before 2026-08-31
- Full Belize simulation completed successfully

**Bad exit — goal terminates early:**
- Router incompatible with OpenWRT AND replacement exceeds $100 → escalate to Commander for router decision + budget override
- Commander decides to travel with YOGA to Belize → home-alone connectivity goal superseded; pivot to YOGA-travel hardening

---

## RELATED PLANS

- Full Belize Continuity Plan (4 domains): `output/plans/BELIZE_CONTINUITY_PLAN.md`
- This goal = Domain 3 (Router) + Domain 2 (WoL) + Domain 1 partial (tunnel health)

---

*Goal constructed: V. Hale, VCS · 2026-05-26 · Per Commander dictation*
*A7 Sterling design review: pending*
