# CONTINUITY OF OPERATIONS — Offline Execution Layer

**Purpose:** Autonomous mission execution when YOGA internet is offline. Survives network isolation.

**Architecture:** Three-layer system
```
DEFERRED ALERTS (hale_state.json)
         ↓
CONTINUITY EXECUTOR (polls every 30s)
         ↓
HEADLESS CLAUDE SPAWN (on trigger)
         ↓
LOCAL RESULTS (results/*.json)
         ↓
NETWORK RECOVERY (on reconnect)
         ↓
EMAIL + TELEGRAM REPORT
```

---

## Components

### 1. continuity_executor.py
**Runs:** Continuously as systemd service
**Monitors:** `hale_state.json` deferred_alerts array
**Triggers:** Date-based and dependency-based
**Action:** Spawns headless Claude agent for alert evaluation

**Key function:** `spawn_headless_claude(alert)`
- Detached subprocess (start_new_session=True)
- Loads OAuth token from ~/.claude/.credentials.json
- Executes with explicit WRITE [PATH] instruction
- Logs to continuity_log.jsonl

### 2. continuity_recovery.py
**Runs:** When network-online.target fires (systemd event)
**Collects:** All result files from results/ directory
**Reports:** Email to johnloucks3 + Telegram to Commander
**Cleanup:** Deletes results after reporting

**Key function:** `send_recovery_report(results)`
- Calls scripts/send_d2mconcierge_email.py
- Sends Telegram via OpsCenter.thunderbird_telegram_gw

### 3. continuity_manifest.py
**Runs:** On-demand (called by watchdog every 5 minutes)
**Output:** manifest.json (real-time queue status)
**Use:** Injected into hale_brief.md for Commander visibility

**Example manifest:**
```json
{
  "status": "EXECUTING",
  "queued_missions": 2,
  "executing_missions": 1,
  "queued": [
    {
      "id": "MCLEOD-2984034-FPD-TRIGGER",
      "priority": "P0",
      "message": "McLeod Regent Grandeur 2984034 — FPD Jul 22..."
    }
  ],
  "executing": ["MCLEOD-2984034-FPD-TRIGGER"]
}
```

---

## File Structure

```
/home/john/Thunderbird/core/continuity/
├── continuity_executor.py       (main loop)
├── continuity_recovery.py       (network restore)
├── continuity_manifest.py       (queue status)
├── continuity_log.jsonl         (execution log)
├── manifest.json                (current status)
├── results/                     (offline execution outputs)
│   ├── ALERT_ID_result.json
│   └── ...
└── spawn_ALERT_ID.log           (headless Claude output)
```

---

## Trigger Logic

**Deferred alerts** in hale_state.json have condition_type:
- `date` — trigger when `trigger_date` ≤ now
- `date_and_client_status` — trigger + client returned
- `date_and_dependency` — trigger + dependency resolved (e.g., transfer booked)

Executor polls every 30 seconds. When trigger met, headless Claude is spawned with a structured prompt:
1. Evaluate alert condition
2. Recommend action
3. Write result JSON to results/ALERT_ID_result.json

**Headless Claude isolation:** No internet dependency. Runs offline-first. Token must be valid (keepalive timers refresh every 90 min).

---

## Network Recovery

When network is restored (systemd event network-online.target):
1. `continuity_recovery.py` runs automatically
2. Collects all results from results/ directory
3. Builds recovery report
4. Sends email to johnloucks3 + Telegram ping
5. Clears results/ directory
6. Mission board updated with findings

**Commander receives:** Email with full findings + recommendations. Can then act on findings normally.

---

## Observable Status

**For Commander visibility:**
1. `continuity_manifest.py` runs every 5 minutes (via watchdog)
2. Updates manifest.json (current queue + executing)
3. hale_brief.md injects continuity status section

Example brief entry:
```
🔄 CONTINUITY STATUS
├─ Queued: 2 missions
├─ Executing: 1 mission
└─ Last activity: 08:45 MT
```

---

## Activation

```bash
# Install systemd service
systemctl --user daemon-reload
systemctl --user enable thunderbird-continuity.service
systemctl --user start thunderbird-continuity.service

# Check status
systemctl --user status thunderbird-continuity.service
journalctl --user -u thunderbird-continuity -f

# View execution log
tail -20 /home/john/Thunderbird/core/continuity/continuity_log.jsonl

# View current manifest
cat /home/john/Thunderbird/core/continuity/manifest.json
```

---

## Error Handling

**If Claude spawn fails:**
- Error logged to continuity_log.jsonl
- Logged again on next poll (retry every 30s)
- After 3 failures, marked as "needs manual review"

**If network never returns:**
- Results persist locally in results/ directory
- Manual recovery: `python3 continuity_recovery.py` (explicit run)

**If token expires:**
- OAuth keepalive timer (every 90 min) should refresh it
- If keepalive fails, continuity executor will error and retry

---

## Testing

```bash
# Simulate a triggered alert (force execution)
python3 /home/john/Thunderbird/core/continuity/continuity_executor.py

# Check spawn logs
ls -la /home/john/Thunderbird/core/continuity/spawn_*.log

# View results
cat /home/john/Thunderbird/core/continuity/results/*.json

# Manually trigger recovery
python3 /home/john/Thunderbird/core/continuity/continuity_recovery.py
```

---

## Constraints & Design

**No external API calls** — headless Claude is the only dependency, and it has offline-capable OAuth tokens.

**Local-first execution** — all data persists on YOGA disk; network outage only affects reporting, not evaluation.

**Idempotent spawns** — same alert can be spawned multiple times; recovery protocol deduplicates via filename.

**Graceful fallback** — if recovery fails to send email, results stay in results/ until manually cleared.

---

## Next Phase

**Future:** Integrate with client-gated execution:
- P0 alerts can auto-execute (e.g., send validation email from d2mconcierge)
- P1+ alerts spawn for evaluation only, await Commander approval on recovery
- Implement dependency resolver for "date_and_dependency" conditions
