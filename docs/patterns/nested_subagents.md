# Nested Subagents Pattern — Per-Client Children
*ELON A12 · 2026-06-21 · A12 pattern documentation*

## The Pattern
A parent orchestrator agent spawns per-client child agents, each operating in an isolated context with only that client's data. The parent holds no client PII after dispatch; children hold PII only for their run duration.

## Thunderbird Implementation

```
Orchestrator (Hale / Claude Code)
    ├── child-agent: Furlow
    │     context: dossiers/Furlow*.md, tess_token, booking 3096289
    │     task: TP 1.1 Voyage Preview draft
    │     output: WRITE drafts/furlow_tp11.html
    │
    ├── child-agent: Kuklinski
    │     context: dossiers/Kuklinski*.md, tess_token, booking 3106xxx
    │     task: TP 4.1 Specialty Dining draft
    │     output: WRITE drafts/kuklinski_tp41.html
    │
    └── child-agent: McLeod
          context: dossiers/McLeod*.md, tess_token, booking 2984034
          task: FPD reminder draft
          output: WRITE drafts/mcleod_fpd.html
```

## Spawn Command (each child)
```python
# In thunderbird_headless_spawn.py — pass per-client context only
proc = subprocess.Popen(
    [CLAUDE_BIN, "-p",
     f"Client: {client_name}\nDossier: {dossier_path}\n"
     f"Task: {task_description}\n"
     f"WRITE output to {output_path}",
     "--model", "claude-haiku-4-5-20251001"],  # Haiku for drafts
    env={**base_env, "CLIENT_SCOPE": client_name},
    start_new_session=True,
    stdout=open(log_path, "w"),
    stderr=subprocess.STDOUT,
)
```

## PII Fence Compliance
- Parent orchestrator strips all PII before dispatching to DeepSeek/OpenCode counter-voice
- Each child receives exactly one client's dossier — no cross-contamination
- Children run with `start_new_session=True` — isolated process, no shared memory with parent
- Output files are the only artifact; child context dies with the process

## When to Use
- Parallel lifecycle TP drafts across multiple clients (same TP type, different clients)
- Batch dossier freshness checks (each client checked by its own child)
- Commission reconciliation per booking (one child per booking ref)
- Any task where client isolation is required and work is parallelizable

## Anti-patterns
- Do NOT pass multiple clients' dossiers to a single child — that is the contamination pattern
- Do NOT use for tasks requiring cross-client comparison (use parent orchestrator for that)
- Do NOT use Opus for children in parallel batches — Haiku for drafts, Sonnet for synthesis only

## Token Economics
10 parallel children at Haiku: ~$0.01-0.03 total for a full TP draft batch.
Same task serialized through a single Sonnet session: ~$0.15-0.30 + context bleed risk.

*Pattern authored from integration-59-results Phase 2 recon · 2026-06-21*
