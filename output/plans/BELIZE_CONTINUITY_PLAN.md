# BELIZE CONTINUITY PLAN
**Classification:** T2 Wing Exercise | **Owner:** Hale (COS) | **Created:** 2026-05-26
**Next trip:** September 2026 | **Hard deadline:** 2026-08-31

---

## MISSION STATEMENT

Enable Commander to run D2M Travel from Belize with YOGA either:
- Running normally (best case — full capability)
- Unreachable / hung / needing reboot (recovery in <30 min from Belize)
- Fully dead / YAYA (emergency ops via cloud stack in <60 min)

---

## CONTEXT CORRECTIONS (2026-05-26)

- **YOGA runs 24/7** — already configured. Shutdown is not the risk.
- **Internet issue (May)** — separate router/modem issue, not YOGA. OpenWRT firmware on router handles self-healing. Not a YOGA problem.
- **Real risk** — YOGA hung, crashed, or Cloudflare tunnel dropped. Recovery path = WoL-via-ethernet hard reset OR cloud fallback.
- **OCTOPUS (Chromebook)** — Crostini dead. ttyd at code.d2mluxury.quest is sole terminal. HARDENED 2026-05-26 with 5-min watchdog (Gate 0 complete ✅).

---

## FOUR DOMAINS + STATUS

### Domain 1 — MCP Exposure via Cloudflare
**Goal:** MCP server (port 8765) accessible from OCTOPUS / Belize at `mcp.d2mluxury.quest`
**Why YOGA must be up:** MCP server runs locally. Exposure just makes it reachable remotely.
**Status:** 🔴 NOT DONE
**Owner:** A7 Sterling (design) → Hale (cloudflared edit + reload)
**Effort:** 20 min, $0

Steps:
1. [ ] Add `mcp.d2mluxury.quest → http://localhost:8765` to `~/.cloudflared/config.yml`
2. [ ] Reload cloudflared on YOGA
3. [ ] Add nginx auth wrapper (MCP currently no auth — must protect)
4. [ ] Test from OCTOPUS
5. [ ] Document in infra notes

---

### Domain 2 — YOGA Remote Recovery (Hung/Unreachable from Belize)
**Goal:** If YOGA hangs or crashes, Commander can hard-reset it from Belize without physical access.
**Status:** 🔴 NOT DONE
**Owner:** A7 Sterling
**Effort:** ~3 hrs + hardware order

Phase A — WoWLAN (interim, zero cost, this week):
1. [ ] Enable WoWLAN on YOGA WiFi NIC (RTL8852CE, driver supports it)
2. [ ] Make WoWLAN persistent via udev rule or systemd ExecStartPost
3. [ ] Test: send magic packet from another device on LAN
4. [ ] Document test procedure

Phase B — Wired WoL (August, requires ethernet):
1. [ ] Commander plugs YOGA into ethernet (USB-C adapter or dock)
2. [ ] Verify `eno1` or similar interface appears
3. [ ] Enable WoL on wired NIC: `sudo ethtool -s eno1 wol g`
4. [ ] Make persistent: `/etc/udev/rules.d/81-wol.rules`
5. [ ] Test: shut YOGA down → send magic packet → YOGA wakes
6. [ ] Hardware needed: TP-Link Kasa smart plug ($15) for hard power-cycle if YOGA truly hangs

Phase C — WoL trigger from Belize:
1. [ ] Option 1: Router sends magic packet via OpenWRT WoL plugin (free)
2. [ ] Option 2: Python script on Raspberry Pi / cloud VPS sends packet via Tailscale
3. [ ] Test end-to-end: Belize → magic packet → YOGA wakes

---

### Domain 3 — Router Firmware (OpenWRT)
**Goal:** Router self-heals on WAN loss. Also enables WoL relay from internet.
**Status:** 🔴 NOT DONE — compatibility check needed first
**Owner:** A7 Sterling
**Effort:** ~2 hrs (if compatible) + testing before August

Steps:
1. [ ] Identify router model (MAC cc:28:aa:5b:4e:90 = TP-Link)
2. [ ] Check OpenWRT compatibility at openwrt.org/toh
3. [ ] If compatible: backup router config, flash OpenWRT
4. [ ] Configure: WAN watchdog (auto-restart on loss), WoL relay plugin
5. [ ] Test: pull WAN → router self-heals; send WoL from WAN → YOGA wakes
6. [ ] If NOT compatible: buy supported router (~$40-60) — Castillo to assess

---

### Domain 4 — Belize Operating Model (YOGA = YAYA)
**Goal:** Commander can run D2M ops from Belize for 48h+ even if YOGA is fully dead.
**Status:** 🟡 PARTIALLY DEFINED (recon complete, implementation pending)
**Owner:** A5 Castillo (strategy), A12 ELON (simplification)
**Effort:** ~4 hrs across 2 sessions

Cloud stack to deploy (emergency or pre-staged):
1. [ ] Telegram bots → Railway.app free tier (migrate from YOGA-local)
2. [ ] n8n cloud (15 pure-API workflows) → n8n.io cloud free tier OR $5/mo VPS
3. [ ] Emergency VPS playbook (DigitalOcean: spin up in 5 min, deploy n8n + bots in 25 min)
4. [ ] Document: "30-minute YOGA-YAYA recovery procedure" (Hale authors)
5. [ ] Test: simulate YOGA-down from Belize, run through playbook

---

## TIMELINE

| Phase | What | Deadline | $$ |
|-------|------|----------|----|
| **This week** | Domain 1 (MCP exposure), Domain 2A (WoWLAN) | 2026-05-31 | $0 |
| **June** | Domain 3 router compatibility check, Domain 4 cloud stack design | 2026-06-15 | $0 |
| **July** | Domain 2B (wired WoL), hardware order if needed | 2026-07-15 | ~$30-60 |
| **August** | Domain 3 router firmware, full Belize simulation test | 2026-08-15 | — |
| **Sep pre-trip** | All tests passed, playbook final, cloud stack staged | 2026-08-31 | — |

---

## HARDWARE SHOPPING LIST (Decide in July)

| Item | Purpose | Est. Cost | Priority |
|------|---------|-----------|----------|
| TP-Link Kasa EP25 smart plug | Hard power-cycle YOGA if hung | ~$15 | HIGH |
| USB-C to Ethernet adapter (if YOGA doesn't have one) | Wired WoL | ~$15-25 | HIGH |
| Router (if current TP-Link not OpenWRT compatible) | Self-healing firmware | ~$40-60 | MEDIUM |

---

## SUCCESS CRITERIA

- [ ] From Belize, Commander can reach YOGA MCP tools at `mcp.d2mluxury.quest`
- [ ] From Belize, Commander can send WoL packet to wake/reset YOGA
- [ ] If YOGA is dead, Commander is running at 80% capability within 30 min via cloud stack
- [ ] Router self-heals WAN loss without Commander intervention
- [ ] All tests passed before 2026-08-31

---

## DECISIONS NEEDED FROM COMMANDER

1. **Domain 3:** Confirm OK to check/flash router firmware (requires ~2h downtime window)
2. **Domain 4:** Authorize cloud n8n migration (which 5 workflows go to free tier vs paid VPS)
3. **Hardware:** Approve shopping list spend ~$30-80 in July

---

*Plan authored by V. Hale, VCS | 2026-05-26 | Reviewed by A7 Sterling (pending)*
*Next review: 2026-06-01 | Full plan: `output/plans/BELIZE_CONTINUITY_PLAN.md`*
