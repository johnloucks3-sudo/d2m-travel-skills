---
proposal_id: ELON-20260607-telegram-gw-root-cause
author: ELON (A12 Innovation & Disruption)
created: 2026-06-07T16:57:00Z
severity: P2 (operational stability)
pattern: 16 restarts in 7 days (~2.3/day) — consistent recurrence indicates defect, not transient
---

# ROOT CAUSE

The gateway daemon has a recurring defect that triggers a crash or hang approximately every 8–10 hours. Auto-healing (systemd `Restart=always`) catches the failure and restarts the service, creating the illusion of stability while obscuring the underlying bug. The service is **not resilient** — it is **failing and recovering repeatedly**. This pattern indicates a defect in token refresh logic, message parsing, rate-limit handling, or network connection management that **demands diagnosis, not masking**.

The true problem: we're treating the symptom (service down) with a backstop (auto-restart) instead of fixing the disease (the daemon defect).

---

# PROPOSED FIX

**Type:** `code_diff` + `standing_order` (two-phase approach)

**Phase 1 (Diagnostic):** Disable auto-healing, add structured logging with stack traces, and run the daemon in a way that captures the actual crash signature. Once known, escalate the signature to Sterling for code review and diagnosis.

**Phase 2 (Correction):** Fix the root defect. After patching, re-enable auto-healing as a safety backstop (not a primary control).

**ELON's first-principles angle:** Before we fix the daemon, ask whether the daemon should exist at all. Can we replace the polling mechanism with Telegram webhooks? Webhooks eliminate the need for a daemon to poll, eliminating this crash vector at the source. This architectural decision belongs to the Chief — but the diagnostic must be completed first to inform the decision.

---

# IMPLEMENTATION

**Phase 1 (Hale can execute autonomously — operational troubleshooting):**

1. **Disable auto-healing temporarily:**
   - Edit `/etc/systemd/user/thunderbird-telegram-gw.service`
   - Change: `Restart=always` → `Restart=no`
   - Run: `systemctl --user daemon-reload`

2. **Ensure structured logging:**
   - Verify the service config has:
     ```ini
     StandardOutput=journal
     StandardError=journal
     SyslogIdentifier=thunderbird-telegram-gw
     ```
   - Or add if missing.

3. **Run the daemon with live log capture (24–48 hours):**
   ```bash
   journalctl -f -u thunderbird-telegram-gw.service -o short-precise
   ```
   Let it run and collect the crash signature (error message + stack trace).

4. **Capture the crash signature:**
   - Note the timestamp, error message, and any stack trace
   - Document which code path failed (e.g., "token refresh," "message parse," "network connect")

5. **Escalate to Sterling with the crash signature:**
   - Email: `"Telegram gateway crashes ~every 8–10 hours. Attached crash log. Need diagnosis and patch recommendation."`

**Phase 1b (Sterling, once crash is known):**
- Review the crash signature
- Either: diagnose the defect and prepare a patch, OR recommend architectural change (webhooks vs polling)

**Phase 2 (Hale, post-patch):**
- Deploy the patched daemon code (via Sterling)
- Re-enable `Restart=always` in the systemd service
- Verify 48h of zero crashes

---

# VERIFICATION TEST

**Pre-Fix Validation:**
- Systemd journal for 24h should show 2–3 crash events with full stack traces
- Each crash should have a **consistent signature** (same error, same code path)
- Example: `"FATAL: Telegram API token expired, unable to refresh"`

**Post-Fix Validation:**
- Deploy the patched daemon
- Run for 48h with `Restart=no` (auto-healing disabled)
- **Zero crashes observed** = success
- Then re-enable `Restart=always` and monitor next 7 days
- Target: 0 restarts in 7 days (previously 16)

---

# HALE DECISION

**Recommendation: `APPLY_AUTONOMOUSLY` (Phase 1 only)**

**Reasoning:**

1. **Phase 1 (diagnostics) is purely operational:**
   - Disabling auto-healing temporarily is not a code or strategy change
   - Collecting logs is a standard troubleshooting action
   - This is squarely in Hale's domain (infrastructure health)
   - **Hale executes Phase 1 autonomously**

2. **Phase 2 (patching) requires domain expertise:**
   - Once the crash signature is known, Sterling diagnoses the defect
   - Hale applies the patch once Sterling has reviewed it
   - **Hale executes Phase 2 once Sterling signs off on the fix**

3. **Architectural decision (webhooks vs polling) is strategic:**
   - This is worth a brief to the Chief once diagnostics are complete
   - **Chief decides the architecture; Sterling implements**

**How to brief Commander:**
> "Telegram gateway has a recurring defect — crashes 2–3 times per day and auto-healing masks it. Running a 24h diagnostic to capture the crash signature. Once known, will escalate to Sterling for diagnosis and patch. The underlying question: should we migrate from polling to webhooks? That's a strategic call for your review once we understand the defect."

**Timeline:**
- Phase 1 (diagnostic): 24–48 hours (Hale)
- Phase 1b (Sterling diagnosis): 2–4 hours (Sterling)
- Phase 2 (patch + verify): 2–4 hours (Hale + Sterling)
- Total: ~48–72 hours to resolve

---

**Next immediate action:** 
Hale disables auto-healing and starts the 24h observation window.

*— ELON, A12 Innovation & Disruption*
*"Why do we have this daemon? Can we eliminate the need?"*
