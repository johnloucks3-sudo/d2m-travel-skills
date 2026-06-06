**Proposal complete.** Structured format written to `/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260605-thunderbird-overwatch.md`.

**Key finding:** The service isn't flaky — it's **dead on arrival** with a broken import (`GROQ_MODELS` missing from its startup sequence). Systemd correctly restarts it; the daemon just never recovers because the code error persists. This is a code hygiene issue, not an operational flake.

**ELON's call:** Remove the stale import or redirect it to the correct module. Surgical fix, instant verification. Flagged **`APPLY_AUTONOMOUSLY`** — Hale can execute without Commander gates (T0 routine).

**Next:** Hale scans `/OpsCenter/elon_proposals/` on her routine cycle and picks this up for execution. ~5 min to diagnosis, fix, restart, and verify.
