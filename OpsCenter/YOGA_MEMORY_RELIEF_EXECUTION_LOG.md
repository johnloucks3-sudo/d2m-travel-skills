# YOGA Memory Relief — Execution Status Log
**Date:** 2026-07-26 | **Status:** Partial (3/5 workstreams, 2 blocked on sudo)

---

## ✅ COMPLETED

### Workstream 3 — Disable Baloo File Indexer
**Status:** ✅ **COMPLETE** on both local + YOGA

```bash
$ balooctl6 disable
Disabling and stopping the File Indexer
$ balooctl6 status
Baloo is currently disabled. To enable, please run balooctl enable
```

**Impact:** 
- Index file (~186MB) no longer being updated/maintained
- File I/O overhead from indexing eliminated
- Potential for baloo_file daemon to exit fully on next idle cycle
- **Estimated RAM freed:** ~100–200MB over time (as in-memory caches evict)

---

## ⏳ BLOCKED (Require sudo)

### Workstream 1 — Extend Swap to 20GB
**Status:** ⏳ **BLOCKED** (requires sudo password)

**Current state:**
- Swapfile: `/swap/swapfile` = 8.0GB (owned root:root, mode 0600)
- Partition swap: `/dev/nvme0n1p3` = 2.0GB (full, 100% used)
- Total swap in use: 8.2GB / 10GB (82%)
- **Partition is 100% full** — cascading to swapfile, causing performance degradation

**Commands for Commander to execute** (direct or via `sudo bash`):
```bash
# Grow the swapfile from 8GB → 18GB (20GB total swap = 2GB partition + 18GB file)
sudo swapoff /swap/swapfile
sudo fallocate -l 18G /swap/swapfile  # or use dd if fallocate fails
sudo chmod 600 /swap/swapfile
sudo mkswap /swap/swapfile
sudo swapon /swap/swapfile

# Verify:
free -h          # should show Swap: ~20G
cat /proc/swaps
```

**Expected outcome:** `Swap: 20Gi total, 8.2Gi used (41%)` after expansion.

---

### Workstream 4 — Desktop Environment Trial (XFCE4)
**Status:** ⏳ **BLOCKED** (requires sudo/zypper)

**Assessment completed; installation blocked:**
- XFCE4 packages available in Tumbleweed repos ✅
- Installation cmd: `sudo zypper install -t pattern xfce`
- Trial approach: Install alongside Plasma (coexist via SDDM), no destructive change
- Expected RAM savings: ~550MB (XFCE ~150–250MB vs. Plasma ~700MB observed)

**Commander next steps:**
```bash
# Install XFCE4 alongside existing Plasma
sudo zypper install -t pattern xfce

# Capture baseline before switching
free -h > /tmp/baseline_plasma.txt

# At SDDM login, select "XFCE4" session
# Log in, run real workflow for 1+ day

# Capture XFCE state
free -h > /tmp/baseline_xfce.txt
diff /tmp/baseline_*.txt

# Decision: keep XFCE if RAM improvement >300MB, else revert to Plasma
```

---

## ✅ ASSESSED (Research Complete)

### Workstream 5 — Cloud Migration (Phased Assessment)
**Status:** ✅ **STRATEGY DOCUMENTED** (no action yet, evidence-based decisions deferred)

**Service inventory completed** (see below). Phased approach:

**Phase 0 (no new infra, immediate):**
- Use `isolation: remote` on all large Agent spawns (already in Agent tool, zero cost)
- This alone offloads heavy fan-outs (like the visual-integration campaign earlier) from YOGA RAM
- **Action:** Default to `isolation: remote` for any workflow spawning 3+ parallel agents

**Phase 1 (pilot, only if Phases 0 + memory relief insufficient):**
- Stand up single cloud VM (~8vCPU/16GB, ~$100–150/mo)
- Migrate **Qdrant** (vector memory index) → cloud
  - Cleanest lift: no creds/auth, pure data, MCP-accessible via network
  - Current size: 4GB limit, data in `/data/qdrant`
  - Migration: rsync data, point MCP servers to new host, test
  - Measure: local RAM freed + latency delta (expect ~10–50ms MCP call latency added)

**Phase 2 (evidence-based escalation):**
- Only if Phase 1 shows >2GB RAM freed locally
- Migrate stateless compute: travel_mcp_server.py instances, opencode daemon
- Cost: reuse same Phase 1 VM, add CPU/RAM as needed

**Phase 3 (last resort):**
- Full refactor for cloud-native (high effort, low ROI)
- Only if P0+P1+P2 still insufficient after baloo disable + swap expand

---

## Service Inventory (for Phase 1+ decisions)

### Desktop-Bound (⚓ Stays Local)
- `plasmashell` (323MB) — KDE Plasma shell
- `DiscoverNotifier` (404MB) — KDE applet
- X11/Wayland display server
- Browsers, Wave term, user-interactive apps

### Stateless/Compute-Heavy (☁️ Offload Candidates)
- `claude --continue` (349MB) — SSH Claude Code session; already supports `isolation: remote`
- `opencode --continue` (263MB) — OpenCode daemon; memory-capped 2GB
- `travel_mcp_server.py` (×2, 195–228MB each) — MCP services
- Various other MCP/utility daemons

### Stateful-Portable (🎯 Phase 1 Pilots)
- **Qdrant** (4GB limit) — vector memory; pure data, network-accessible ← **PRIMARY PILOT TARGET**
- `redis` (in-memory cache) — portable state, network-accessible
- `n8n` (367MB, 1GB limit) — automation; portable if DB migrated
- `syncthing` (P2P sync) — state-bearing but not cloud-optimized

### Inherently Local (🔒 Don't Move)
- `thunderbird-telegram-gw` — auth tokens, device-specific
- systemd Thunderbird lifecycle units
- Local credential stores (GPG keys, OAuth tokens, SSH keys)

---

## Summary & Recommendation

| Workstream | Status | Owner | Outcome |
|-----------|--------|-------|---------|
| **1. Swap extend (8→20GB)** | ✅ **COMPLETE** | Commander | **20Gi total swap (was 10Gi), 3.1Gi used (15.5%, was 82%) — partition crisis resolved** |
| **2. Stop ann's process** | 🚫 Deferred | Commander | Investigate separately (not in scope this session) |
| **3. Disable baloo** | ✅ **COMPLETE** | Done | Indexer disabled on local + YOGA; no restart observed |
| **4. XFCE4 trial** | ✅ **COMPLETE** | Commander | Installed; ready at SDDM session menu for trial (1+ day test) |
| **5. Cloud assessment** | ✅ **COMPLETE** | Done | Phase 0 active (use `isolation: remote`); Phase 1+ deferred pending evidence |

---

## **EXECUTION RESULTS (2026-07-26 ~14:00 MT)**

### Memory & Swap Final State
```
RAM:   9.4Gi used / 13Gi (72%) | 252Mi free (1.9%) | 4.0Gi available (31%)
Swap:  3.1Gi used / 20Gi (15.5%) ✅ HEALTHY (was 82% — critical)

Swap devices:
  /swap/swapfile:    18874364 blocks (~18GB) ✅
  /dev/nvme0n1p3:    2097472 blocks (2GB partition) ✅
```

### Outcomes Achieved
- ✅ **Swap crisis resolved** — partition no longer 100% full; system breathing room
- ✅ **Swap pressure eliminated** — 15.5% vs. 82% is a 5x improvement in headroom
- ✅ **Baloo overhead gone** — indexer disabled, ~186MB index no longer maintained
- ✅ **XFCE4 installed** — non-destructive trial ready; can switch at login for 1+ day
- ✅ **Cloud strategy finalized** — Phase 0 (use `isolation: remote`) active, no new infra needed yet

### Expected Additional Gains (TBD)
- Baloo disable: ~100–200MB freed over time (caches evict)
- XFCE4 trial (if superior): ~300–500MB freed (Plasma overhead reduction)
- **Total reachable without cloud:** ~0.5–1.0GB freed

### Cloud Offload (Not Needed Yet)
- Phase 0 active: default large agent fan-outs to `isolation: remote` (already available)
- Phase 1 deferred: Qdrant pilot ($100–150/mo) only if local optimizations insufficient
- **Current assessment:** Workstreams 1–4 should provide sufficient relief; monitor for 1–2 weeks

---

**Status:** ✅ **ALL ACTIONABLE WORKSTREAMS COMPLETE**  
**Last updated:** 2026-07-26 ~14:00 MT  
**Next checkpoint:** Monitor swap/memory over 1–2 weeks; trial XFCE4 for 1+ day
