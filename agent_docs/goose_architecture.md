# THUNDERBIRD OS — GOOSE MIGRATION PLAN
## Dreams2Memories Travel Intelligence Suite
**Version:** 1.0 | **Date:** 2026-03-27 | **Owner:** John Loucks

---

## REALITY CHECK (Read Before Building)

The AppScript migration described in earlier planning docs **is already complete.** All 13 Tier 1 intel modules exist as Python FastMCP files registered in `travel_mcp_server.py`. Most are already running on systemd timers or the batch runner.

**What Goose actually adds:**
- Unified recipe-based execution for all 13 modules
- Agent oversight — Goose retries, adapts, and reports when a module fails
- Poe inference on the 2 modules that call AI APIs (saves Max plan tokens)
- Natural language trigger via Telegram: "run ship intel" → Goose recipe fires
- `AGENT.md` context gives Goose D2M awareness across all runs

**Poe/Max split reality:**
- 11 of 13 modules are pure Python (no AI calls) — Poe saves nothing here
- `x_osint` calls Claude CLI directly → migrate to Goose → use Poe points
- `price_monitor` calls Anthropic SDK (Haiku fallback) → migrate to Goose → use Poe points

---

## CURRENT STATE INVENTORY

| Module | Lines | Current Trigger | AI Calls | Status |
|--------|-------|----------------|----------|--------|
| `thunderbird_morning_briefing` | — | `d2m-brief-telegram.timer` 07:30 MDT | None | ✅ Running |
| `thunderbird_ship_intel` | 487 | Batch runner 12:05 MDT | None | ✅ Running |
| `thunderbird_world_intel` | 921 | Batch runner 12:05 MDT | None | ✅ Running |
| `thunderbird_tech_monitor` | — | Batch runner 12:05 MDT | None | ✅ Running |
| `thunderbird_fare_watch` | — | Batch runner 12:05 MDT | None | ✅ Running |
| `thunderbird_dossier_scanner` | — | Batch + `d2m-fpd-alert.timer` 07:00 | None | ✅ Running |
| `thunderbird_booking_monitor` | — | `d2m-booking-monitor.timer` every 6h | None | ✅ Running |
| `thunderbird_innovation_scanner` | — | `thunderbird-innovation-scan.timer` 06:30 | None | ✅ Running |
| `thunderbird_academic_scanner` | — | Possibly via incubator AM scrape | None | ⚠️ Uncertain |
| `thunderbird_x_osint` | — | No timer | Claude CLI | ❌ Not scheduled |
| `thunderbird_price_monitor` | — | Partial via booking reconciliation | Anthropic SDK | ⚠️ Partial |
| `thunderbird_airline_monitor` | — | **KILLED** in batch runner | None | ❌ Dead |
| `thunderbird_worldfactbook` | — | On-demand MCP only | None | ⚠️ No schedule |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    GOOSE AGENT                              │
│  Provider: Anthropic → ANTHROPIC_HOST=https://api.poe.com   │
│  Config:   ~/.config/goose/config.yaml                      │
│  Context:  ~/Thunderbird/AGENT.md                           │
└──────────┬──────────────────────────┬───────────────────────┘
           │ MCP Extension            │ Developer Extension
           │ (stdio → travel_mcp)     │ (shell commands)
           ▼                          ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│  travel_mcp_server   │    │  Direct Python execution        │
│  All 13 modules as   │    │  for pure-scraper modules       │
│  registered MCP tools│    │  (no AI overhead)               │
└──────────────────────┘    └─────────────────────────────────┘
```

**Execution model per module:**
- AI-calling modules (x_osint, price_monitor): Goose recipe → MCP tool → module → **Poe inference**
- Pure Python modules: Goose recipe → shell exec OR MCP tool → no AI involved, same result

---

## PHASE 0: FOUNDATION (One-time setup, ~30 min)

### Step 1 — Install block/goose

```bash
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
# Installs to ~/.local/bin/goose
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
goose --version
```

### Step 2 — Configure Goose with Poe as provider

```bash
mkdir -p ~/.config/goose
cat > ~/.config/goose/config.yaml << 'EOF'
GOOSE_PROVIDER: "anthropic"
GOOSE_MODEL: "claude-sonnet-4-6"
GOOSE_MODE: "auto"
GOOSE_MAX_TURNS: 50
GOOSE_TELEMETRY_ENABLED: false

extensions:
  developer:
    bundled: true
    enabled: true
    name: developer
    timeout: 300
    type: builtin
  thunderbird_mcp:
    name: Thunderbird MCP
    enabled: true
    type: stdio
    cmd: python3
    args: ["/home/john/Thunderbird/travel_mcp_server.py", "--stdio"]
    timeout: 600
    description: "D2M Travel Intelligence — 120+ tools"
EOF
```

### Step 3 — Fix thunderbird_poe_config.py (ANTHROPIC_HOST vs BASE_URL)

Goose uses `ANTHROPIC_HOST`, not `ANTHROPIC_BASE_URL`. One line change in `build_api_env()`:

```python
# In thunderbird_poe_config.py build_api_env(), add:
env["ANTHROPIC_HOST"] = url          # Goose uses HOST
env["ANTHROPIC_BASE_URL"] = url      # Claude SDK uses BASE_URL (keep both)
```

### Step 4 — Create goose launch wrapper

```bash
cat > ~/bin/goose-d2m << 'EOF'
#!/bin/bash
# Launch Goose with Poe credentials pre-loaded
source /home/john/Thunderbird/config/poe.env
export ANTHROPIC_API_KEY="$POE_API_KEY"
export ANTHROPIC_HOST="https://api.poe.com"
exec goose "$@"
EOF
chmod +x ~/bin/goose-d2m
```

### Step 5 — Create AGENT.md (D2M context for every Goose session)

```bash
cat > /home/john/Thunderbird/AGENT.md << 'EOF'
# Dreams2Memories Travel — Goose Agent Context

You are running automated intelligence tasks for Dreams2Memories Travel, LLC.

## Identity
- Company: Dreams2Memories Travel, LLC
- Owner: John Loucks (Yoda)
- Primary server: YOGA (192.168.1.198)
- Working directory: /home/john/Thunderbird/

## Ground Rules
- ALL output goes to Telegram, Google Sheets, or log files — never to stdout only
- Alerts fire via Telegram (Commander ID: 7554895206)
- Never send emails without explicit instruction
- Log all runs to ~/Thunderbird/logs/goose/

## MCP Tools Available
Use the Thunderbird MCP extension for all D2M operations.
Key tools: run_ship_intelligence_sweep, run_world_intelligence_sweep,
scan_dossiers_tool, fare_watch_check, run_daily_tech_monitor, and 100+ more.
EOF
```

### Step 6 — Test foundation

```bash
cd ~/Thunderbird
goose-d2m run --no-session -t "Call the gateway_status MCP tool and report back"
```

---

## PHASE 1: REVIVE KILLED + UNSCHEDULED MODULES (3 modules)

These are broken/missing. Fix first since they're highest gap.

### Module: thunderbird_airline_monitor (KILLED — revive)

**Current state:** Disabled in batch runner (task #7 `# ❌ KILLED`)
**Why killed:** Unknown — module exists and is functional
**Goose recipe:** `recipes/airline_monitor.yaml`

```yaml
version: "1.0"
title: Airline Route Monitor
description: Scan airline feeds for route changes affecting D2M clients
steps:
  - type: tool
    name: "thunderbird_mcp/tool_scan_route_changes"
  - type: tool
    name: "thunderbird_mcp/tool_check_impact"
```

**Systemd timer:** Create `d2m-airline-monitor.timer` → 06:00 MDT daily

---

### Module: thunderbird_x_osint (no schedule + AI caller)

**Current state:** No systemd timer, calls Claude CLI directly
**Migration value:** HIGH — replaces Max plan CLI call with Poe points
**Change needed:** x_osint calls `~/.local/bin/claude` for summarization → wrap in Goose recipe so inference goes through Poe

```yaml
version: "1.0"
title: X/Twitter OSINT Sweep
description: Scrape X OSINT follow list and summarize with AI via Poe
steps:
  - type: tool
    name: "thunderbird_mcp/summarize_x_osint"
```

**Systemd timer:** Create `d2m-x-osint.timer` → 07:45 MDT daily (after morning brief)

---

### Module: thunderbird_worldfactbook (on-demand → add morning schedule)

**Current state:** On-demand only via MCP, no proactive runs
**What to add:** Weekly run covering all active client destinations

```yaml
version: "1.0"
title: World Factbook — Client Destination Refresh
description: Refresh country/port intel for all active client destinations
steps:
  - type: tool
    name: "thunderbird_mcp/get_country_intel"
    args: { country: "Norway" }
  - type: tool
    name: "thunderbird_mcp/get_country_intel"
    args: { country: "Iceland" }
  # Expand based on active client roster
```

**Systemd timer:** Create `d2m-factbook-refresh.timer` → Monday 08:00 MDT weekly

---

## PHASE 2: AI-CALLING MODULE MIGRATION (1 module — highest Poe value)

### Module: thunderbird_price_monitor (Anthropic SDK → Poe)

**Current state:** Calls `anthropic.Anthropic()` with Haiku as fallback for price extraction
**Migration:** Ensure `ANTHROPIC_HOST` env var is set when price_monitor runs under Goose

No recipe change needed — just ensure Goose launches with `ANTHROPIC_HOST=https://api.poe.com`.
When price_monitor calls `anthropic.Anthropic()`, it picks up `ANTHROPIC_HOST` from env and routes to Poe.

```yaml
version: "1.0"
title: Price Monitor — Cruise Departure Tracking
description: Check current prices on watched cruise departures
steps:
  - type: tool
    name: "thunderbird_mcp/run_price_check"
```

**Schedule:** Already partial — move from batch to Goose recipe at 06:45 MDT daily

---

## PHASE 3: WRAP RUNNING MODULES IN GOOSE RECIPES (9 modules)

These already work. Adding Goose recipes gives Commander natural language triggers
and consistent logging. **Do not remove existing systemd timers yet** — run in parallel
until recipes are verified stable (2-week burn-in).

### Recipe template pattern:

```yaml
version: "1.0"
title: <Module Name>
description: <What it does>
steps:
  - type: tool
    name: "thunderbird_mcp/<tool_function_name>"
```

| Module | MCP Tool Name | Recipe File | Current Timer | Priority |
|--------|--------------|-------------|---------------|----------|
| `morning_briefing` | `run_morning_briefing` | `recipes/morning_briefing.yaml` | `d2m-brief-telegram.timer` | HIGH |
| `ship_intel` | `tool_run_ship_intelligence_sweep` | `recipes/ship_intel.yaml` | Batch 12:05 | HIGH |
| `world_intel` | `tool_run_world_intel_sweep` | `recipes/world_intel.yaml` | Batch 12:05 | HIGH |
| `tech_monitor` | `run_daily_tech_monitor` | `recipes/tech_monitor.yaml` | Batch 12:05 | MED |
| `fare_watch` | `fare_watch_check` | `recipes/fare_watch.yaml` | Batch 12:05 | MED |
| `dossier_scanner` | `scan_dossiers_tool` | `recipes/dossier_scan.yaml` | Batch + FPD | MED |
| `booking_monitor` | direct Python (has `main()`) | `recipes/booking_monitor.yaml` | every 6h | LOW |
| `innovation_scanner` | `run_innovation_scan` | `recipes/innovation_scan.yaml` | 06:30 | LOW |
| `academic_scanner` | `run_academic_scan` | `recipes/academic_scan.yaml` | Incubator AM | LOW |

---

## PHASE 4: SCHEDULE MIGRATION (after 2-week burn-in)

Replace systemd timer exec targets with `goose-d2m run --recipe`:

**Before:**
```ini
[Service]
ExecStart=/home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/thunderbird_batch_run.py --task 2
```

**After:**
```ini
[Service]
ExecStart=/home/john/bin/goose-d2m run --no-session --recipe /home/john/Thunderbird/recipes/ship_intel.yaml
```

**Batch runner fate:** Keep `thunderbird_batch_run.py` as fallback. Comment out tasks
as recipes stabilize. Do not delete until all 13 are confirmed stable on Goose.

---

## EXECUTION SCHEDULE (Target State)

| Time (MDT) | Module | Recipe | Timer |
|------------|--------|--------|-------|
| 06:00 | airline_monitor | `recipes/airline_monitor.yaml` | `d2m-airline-monitor.timer` (new) |
| 06:30 | innovation_scanner | `recipes/innovation_scan.yaml` | `thunderbird-innovation-scan.timer` |
| 07:00 | dossier_scanner | `recipes/dossier_scan.yaml` | `d2m-fpd-alert.timer` |
| 07:00 | academic_scanner | `recipes/academic_scan.yaml` | `d2m-incubator-am-scrape.timer` |
| 07:30 | morning_briefing | `recipes/morning_briefing.yaml` | `d2m-brief-telegram.timer` |
| 07:45 | x_osint | `recipes/x_osint.yaml` | `d2m-x-osint.timer` (new) |
| 08:00 | world_intel | `recipes/world_intel.yaml` | consolidate into batch |
| 08:30 | ship_intel | `recipes/ship_intel.yaml` | consolidate into batch |
| 09:00 | price_monitor | `recipes/price_monitor.yaml` | `d2m-price-monitor.timer` |
| 12:05 | tech_monitor | `recipes/tech_monitor.yaml` | batch |
| 12:05 | fare_watch | `recipes/fare_watch.yaml` | batch |
| Every 6h | booking_monitor | `recipes/booking_monitor.yaml` | `d2m-booking-monitor.timer` |
| Mon 08:00 | worldfactbook | `recipes/factbook_refresh.yaml` | `d2m-factbook-refresh.timer` (new) |

---

## BUILD SEQUENCE

| Phase | Work | Time | Poe Value |
|-------|------|------|-----------|
| **Phase 0** | Goose install, config, poe_config fix, AGENT.md | 30 min | Unlocks everything |
| **Phase 1** | Revive airline_monitor, add x_osint timer, worldfactbook weekly | 1 hr | HIGH (x_osint off Max) |
| **Phase 2** | price_monitor Goose recipe + ANTHROPIC_HOST env propagation | 30 min | MED (Haiku off Max) |
| **Phase 3** | 9 Goose recipe YAML files for running modules | 1 hr | Low (consistency) |
| **Phase 4** | Timer migration after 2-week burn-in | 30 min | Zero (ops cleanup) |

**Total build time:** ~3 hours across 2 sessions

---

## FILES TO CREATE

```
~/Thunderbird/
├── AGENT.md                          # D2M context for every Goose session
├── recipes/
│   ├── morning_briefing.yaml
│   ├── ship_intel.yaml
│   ├── world_intel.yaml
│   ├── tech_monitor.yaml
│   ├── fare_watch.yaml
│   ├── dossier_scan.yaml
│   ├── booking_monitor.yaml
│   ├── innovation_scan.yaml
│   ├── academic_scan.yaml
│   ├── airline_monitor.yaml          # NEW (revive)
│   ├── x_osint.yaml                  # NEW (add schedule)
│   ├── price_monitor.yaml            # Poe migration
│   └── factbook_refresh.yaml         # NEW (weekly)
└── deploy/systemd/
    ├── d2m-airline-monitor.service   # NEW
    ├── d2m-airline-monitor.timer     # NEW
    ├── d2m-x-osint.service           # NEW
    ├── d2m-x-osint.timer             # NEW
    └── d2m-factbook-refresh.timer    # NEW

~/bin/
└── goose-d2m                         # Poe-credentialed goose launcher

~/.config/goose/
└── config.yaml                       # Anthropic/Poe provider config
```

**Code change:** 2 lines in `thunderbird_poe_config.py` (add `ANTHROPIC_HOST` to `build_api_env()`)
