# Itinerary Conveyor — Staff-Pipeline Daemon Design

**Mission:** MISSION-619 · **Author:** Hale (CC) · **Date:** 2026-07-16
**Status:** Implementation-ready design (not yet built)
**Governing SO:** `standing_orders/SO_ITINERARY_ZERO_LATITUDE_PIPELINE_20260715.md`

---

## 1. Problem & guarantee

Today an itinerary is built by a one-off script (the Grandeur rebuild). A single
model can carry a client deliverable end-to-end with no independent stage gate —
the exact failure the Zero-Latitude SO exists to prevent.

**The guarantee this daemon enforces:** *no single model instance builds a client
itinerary end-to-end unsupervised.* Each SO stage runs as its **own scoped
headless-Claude invocation** with a narrow prompt and an explicit exit checklist;
a job only advances when the current stage reports PASS **with evidence**, and the
final Certify stage (Hale) re-checks evidence rather than trusting stage reports.

This is a **conveyor**: a job is a unit of work that moves one stage at a time,
driven by a timer tick, with durable state between ticks.

## 2. Stage sequence (from the SO — source of truth, do not fork)

| # | Stage | Owner persona | Exit gate (abbrev — full checklist in the SO) |
|---|-------|---------------|-----------------------------------------------|
| 1 | Data | A9 Harlan | Every line verified vs LIVE source, not dossier cache |
| 2 | Port Intel | A2 Dembe | Narrative from scraped port pages only; longer-form |
| 3 | Image Sourcing | Luna A6 | Every URL 200 + Read-tool viewed + no dupes + subject match |
| 4 | Brand/Tech QC | Sterling A7 | Hex-exact vs `docs/ITINERARY_BRAND_SPEC.md`; route map + ship/port sections |
| 5 | Client Voice | Dani A3 | Per-couple voice; no generic template left |
| 6 | Brand Polish | EXEC Naia | Render PDF→PNG, inspect layout/page-breaks |
| 7 | Certify | Hale COS | Re-checks each stage's evidence; Commander sign-off before any send |

The daemon must read the stage list from the SO/registry, not hardcode it, so the
SO stays the single source of truth. (Parse the SO table once at load, or mirror
it into `config/itinerary_pipeline_stages.json` regenerated from the SO.)

## 3. Architecture — reuse, don't reinvent

Reuse existing, live primitives:

- **Job ledger / queue:** the `hale_bus` state pattern — a file-locked JSON ledger
  (`core/hale_bus/hale_bus_state.json` uses `.lock` + `fcntl`). New file:
  `output/itinerary_pipeline/queue.json`, same locking discipline
  (`core/hale_bus/c2_fabric_write.py::record_channel_event` is the reference impl).
- **Stage workers:** the mandatory headless spawn pattern in
  `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` — `subprocess.Popen([... claude -p ...],
  start_new_session=True)` with the OAuth token loaded from `~/.claude/.credentials.json`,
  and an explicit `WRITE <path>` instruction so output is never lost.
- **Tasking / audit:** `core/relay/task_delegation.py::route_task()` +
  `relay_handoff()/relay_ack()` (Block 1 wiring) to record each stage handoff on the
  C2 bus, giving the same audit trail the mission board gets.
- **Tick:** a systemd `.timer` (Hale has standing authority to create timers per
  AGENTS.md §"systemd Timer Create"). One tick advances every job by at most one
  stage attempt — keeps each process short and cgroup-safe.

### Data model — one job

```jsonc
{
  "job_id": "grandeur-furlow-20260716",
  "client": "Furlow",
  "voyage": "Grandeur Scandinavia Aug 2026",
  "dossier": "dossiers/Furlow_Regent_3071222.md",
  "brand_spec": "docs/ITINERARY_BRAND_SPEC.md",
  "output_html": "cruises_web/itinerary_grandeur_furlow.html",
  "stage": 3,                     // next stage to run (1-indexed per SO)
  "status": "in_progress",        // queued | in_progress | blocked | certified | failed
  "attempts": {"3": 1},           // per-stage attempt counter
  "evidence": {                   // each stage writes its PASS evidence here
    "1": {"pass": true, "artifact": "output/itinerary_pipeline/grandeur-furlow/stage1_data.md", "ts": "..."},
    "2": {"pass": true, "artifact": "...stage2_port.md", "ts": "..."}
  },
  "blocked_reason": null,
  "created": "...", "updated": "..."
}
```

### Tick loop (daemon, one invocation per timer fire)

```
1. Acquire queue.lock (fcntl). Read queue.json.
2. Select the highest-priority job whose status == queued|in_progress and not
   currently leased (lease = {holder_pid, expires}; steal on expiry).
3. Release the lock (so other ticks/tools can read) but keep the lease.
4. Resolve stage = job.stage from the SO stage list. Build the SCOPED prompt:
     - only that stage's Single Job + Exit Checklist,
     - the job's input artifacts (dossier, prior-stage evidence artifacts),
     - an explicit "WRITE your evidence to <artifact> as JSON {pass, checklist:{...}, notes}"
       and "do NOT perform any other stage's work".
5. Spawn the stage worker headless (start_new_session=True). Record relay_handoff().
6. On worker exit: read the evidence artifact.
     - pass==true AND every checklist key true  -> advance job.stage += 1,
       record evidence, relay_ack(). If stage was 7 (Certify) -> status=certified.
     - pass==false OR missing checklist item     -> attempts[stage]+=1.
         attempts < MAX_RETRY (2)  -> leave stage unchanged (retry next tick).
         attempts >= MAX_RETRY      -> status=blocked, blocked_reason=<failing item>,
                                       page Hale (wing_page / Telegram urgent-only).
7. Re-acquire lock, write job back, release lease. Exit.
```

Key properties:
- **One stage per process** → short-lived, sidesteps the cgroup-kill race that
  bites long local spawns (same class of failure this fleet hit with ci-sentinel).
- **Certify is not the builder.** Stage 7 spawns a *separate* Hale instance whose
  only job is to re-verify stages 1–6 evidence. It cannot edit the HTML.
- **Anti-theater:** the certifier instance is a different spawn than any builder
  stage — mirrors `task_delegation.py` §3.5 "certifier ≠ assignee".

## 4. Failure, retry, escalation

| Condition | Behavior |
|-----------|----------|
| Stage worker non-zero exit / no artifact | Treated as fail; retry up to MAX_RETRY, then `blocked` |
| Checklist item false | `blocked` at that stage with the specific item as `blocked_reason` |
| Image 404 (stage 3) | Hard block — SO forbids advance on any non-200 |
| Hex mismatch (stage 4) | Hard block — SO forbids substitute hex |
| Certify finds unshown evidence (stage 7) | Send job back to the failing stage (`stage` reset, status=in_progress) |
| Worker exceeds wall-clock (timeout) | Kill, count as attempt, retry |

Blocked jobs never auto-send. A certified job stops at "ready for Commander
sign-off" — WF-17 remains Commander-only; the daemon never sends.

## 5. File / unit layout

```
core/ops/itinerary_conveyor.py          # daemon: one-tick advance (main)
config/itinerary_pipeline_stages.json   # stage list mirrored from the SO
output/itinerary_pipeline/queue.json    # job ledger (fcntl-locked, + .lock)
output/itinerary_pipeline/<job_id>/     # per-stage evidence artifacts
~/.config/systemd/user/itinerary-conveyor.{service,timer}   # tick (e.g. every 10 min)
```

Enqueue CLI (reuse mission_board_sync.py style):
`python3 core/ops/itinerary_conveyor.py enqueue --client Furlow --dossier ... --output ...`
`python3 core/ops/itinerary_conveyor.py status [job_id]`

## 6. Phased build plan

- **Phase 1 (queue + tick, no spawns):** ledger, lock, enqueue/status CLI, tick loop
  that *simulates* stages (marks pass) — proves state machine + concurrency. Unit
  tests: enqueue, single-stage advance, retry→blocked, certify path, lock contention.
- **Phase 2 (real stage workers):** wire the headless spawn per stage with scoped
  prompts + evidence parsing. Test one stage (Data) end-to-end against a known job.
- **Phase 3 (bus + escalation):** relay_handoff/ack on the C2 bus, Hale paging on
  block, systemd timer install. Run the Grandeur trio through as the acceptance test.
- **Phase 4 (Certify hardening):** separate certifier spawn, evidence re-check, send-back.

## 7. Acceptance criteria

1. A job runs 1→7 across multiple ticks, one stage-spawn per tick, each stage a
   distinct process (verifiable in the relay/bus audit trail).
2. A deliberately-broken input (404 image) blocks at stage 3 and never reaches 7.
3. Certify sends a job back when a stage's evidence artifact is missing a checklist key.
4. No stage process both builds and certifies (certifier ≠ any builder spawn).
5. A certified job halts at "awaiting Commander sign-off" — zero auto-send path exists.

---

*Design only — no daemon code shipped under MISSION-619 this session. Build per the
phased plan above; each phase closes against its own passing tests, per house
anti-theater discipline.*
