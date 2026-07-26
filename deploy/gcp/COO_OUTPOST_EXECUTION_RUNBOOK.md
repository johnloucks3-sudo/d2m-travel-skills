# Thunderbird COO Outpost — Execution Runbook

**Plan:** `/home/john/.claude/plans/gleaming-riding-canyon.md` (ADDENDUM section)  
**Status:** Infrastructure ready (Steps 1–4 complete or in-progress), awaiting Commander actions (Step 1 + Step 7)  
**Last updated:** 2026-07-26

---

## Current State

| Step | Task | Status | Owner |
|------|------|--------|-------|
| 1 | Activate GitHub Actions heartbeat (free) | ⏳ BLOCKED | Commander (requires Telegram bot token) |
| 2 | Verify D2M_API_KEY security posture | ✅ NOTED | — (live, accessed via Infisical vault) |
| 3 | Provision e2-micro VM on GCP | ✅ COMPLETE | Hale (VM running in us-central1-a, IAP SSH verified) |
| 4 | Mint scoped credentials | ✅ IN PROGRESS | Hale (SA created, key on VM, GCS bucket ready) |
| 5 | Install + fit-test Claude Code CLI | ⏳ PENDING | Auto-run via script, Commander reviews output |
| 6 | Wire nightly backup automation | ✅ SCRIPTED | Auto-run via script (systemd timers for GCS uploads) |
| 7 | Real-world test from non-home network | ⏳ PENDING | Commander (test from Door County/overseas to verify continuity) |

---

## What's Been Done

### Step 3: Outpost VM Provisioned ✅
- **VM name:** `thunderbird-coo-outpost`
- **Zone:** `us-central1-a` (Always-Free tier eligible)
- **Machine type:** e2-micro (1 vCPU, 1GB RAM, 30GB disk)
- **Access:** IAP SSH tunneling only (no public IP)
- **Status:** Running and reachable via `gcloud compute ssh --tunnel-through-iap`
- **Verification:** IAP SSH test confirmed (uname command executed successfully)

### Step 4: Credentials & Backups Setup ✅ / ⏳
- **Service account:** `thunderbird-coo-outpost@d2m-python-pipeline.iam.gserviceaccount.com` created
- **Service account key:** Generated and copied to VM at `/tmp/coo-outpost-sa-key.json`
- **GCS backup bucket:** `gs://d2m-continuity-backups` created in us-central1 (Always-Free storage)
- **IAM binding:** Service account granted `roles/storage.objectViewer` (read-only)
- **Backup scripts:** Committed to repo at `deploy/gcp/backups/*.sh` (Qdrant, n8n, Infisical)
- **Systemd timers:** Pre-configured in `setup_coo_outpost.sh` to run nightly

### Provisioning Script ✅
- **Location:** `/home/john/Thunderbird/deploy/gcp/setup_coo_outpost.sh`
- **Commits:** `95f08667`
- **Contents:** Automated Steps 4–6 (credentials, package installs, venv setup, backup automation, fit-test)
- **Status:** Ready to execute on the VM

---

## Remaining Actions

### ⏳ Step 1: Activate GitHub Actions Heartbeat (Commander Action)

The free off-box heartbeat (already built, just needs activation) will page Telegram if YOGA goes dark. No cost, no dependencies on the GCP outpost.

**Action:**
```bash
cd /home/john/Thunderbird
bash deploy/offbox_heartbeat/ACTIVATE_P2.sh
```

**When prompted:** Paste your Telegram bot token (D2MC2C bot ID, format `nnnnnnnnnn:xxxxxxxxxxx`)

**Verify:**
```bash
gh secret list | grep TELEGRAM_BOT_TOKEN
gh workflow run "Off-box Wing Heartbeat"
gh run list --workflow="Off-box Wing Heartbeat" --limit=1
```

---

### ⏳ Steps 4–6: Run Provisioning Script on Outpost (Hale in Background)

The script is committed and ready. Run it on the VM via IAP SSH:

```bash
gcloud compute ssh thunderbird-coo-outpost \
  --zone=us-central1-a \
  --tunnel-through-iap \
  --command="bash /tmp/coo-outpost-sa-key.json && \
             mkdir -p ~/.config/gcloud && \
             cp /tmp/coo-outpost-sa-key.json ~/.config/gcloud/coo-outpost-sa.json && \
             bash /home/john/Thunderbird/deploy/gcp/setup_coo_outpost.sh"
```

**What it does:**
1. Places service account key at `~/.config/gcloud/coo-outpost-sa.json`
2. Installs Python, git, Node.js, Claude CLI
3. Clones Thunderbird repo + sets up venv
4. Wires nightly backup scripts to GCS (systemd timers)
5. Smoke-tests Claude Code CLI on 1GB RAM (fit-test)

**Expect:** ~5–10 minutes, output will summarize what was installed and fit-test result

---

### ⏳ Step 7: Real-World Continuity Test (Commander Action)

**Goal:** Confirm you can SSH into the outpost and run Claude Code from a non-home network.

**Test environment:** Phone hotspot (not home WiFi, to verify IAP access works from anywhere)

**Commands:**
```bash
# From your phone hotspot, SSH to the outpost via IAP:
gcloud compute ssh thunderbird-coo-outpost \
  --zone=us-central1-a \
  --tunnel-through-iap

# Once logged in to the outpost, activate venv and test Claude Code:
cd /home/john/Thunderbird
source .venv/bin/activate
claude --version   # Should print version, not error

# Test a real task (optional but valuable):
# Draft a quick client email, check a booking dossier, etc.
# If it works, continuity goal is proven.
```

**Success criteria:**
- ✅ IAP SSH connection works from non-home network (no DNS/firewall blocking)
- ✅ Claude Code CLI starts successfully
- ✅ A real task runs end-to-end (e.g., check Gmail, draft reply)
- ✅ GCP billing still shows $0/mo (nothing paid yet)

**If fit-test failed (1GB RAM too tight):**
- Fallback mode: VM remains operational as backup landing zone + Qdrant snapshot restore-on-demand
- Still solves "detect + don't lose data," just not "run Claude Code live"
- Consider upgrading to e2-small (~$12/mo) only if test proves need

---

## Cost Verification Checklist

After provisioning, confirm actual GCP costs match the plan ($0/mo in-tier):

```bash
# Check GCP billing for the project (requires gcloud auth login with billing perms)
gcloud billing accounts list
gcloud compute project-info describe d2m-python-pipeline --format="value(billingAccountName)"

# Estimate costs for the current infrastructure:
gcloud compute instances list --format="table(NAME, MACHINE_TYPE, STATUS, ZONE)"
gsutil ls -L gs://d2m-continuity-backups   # Storage size

# Logs/auditing:
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=thunderbird-coo-outpost" \
  --limit=50 --format=json 2>&1 | jq -r '.[] | .timestamp, .jsonPayload' | head -20
```

**Red flag:** Any unexpected costs appearing. If so, review the plan's Always-Free assumptions and scale back if needed.

---

## Rollback / Troubleshooting

### If the VM needs to be recreated:
```bash
gcloud compute instances delete thunderbird-coo-outpost --zone=us-central1-a --quiet
# Then re-run the provisioning script (infrastructure is idempotent)
```

### If IAP SSH isn't working:
```bash
# Check if IAP is enabled in the GCP project:
gcloud compute security-policies list
gcloud compute backend-services list

# Re-enable IAP tunnel (should be automatic, but verify):
gcloud compute start-iap-tunnel thunderbird-coo-outpost 22 --local-host-port=localhost:2222 --zone=us-central1-a

# Then SSH via the tunnel:
ssh -i ~/.ssh/google_compute_engine -p 2222 john@localhost
```

### If the fit-test fails (Claude Code won't start):
1. Check memory: `free -h` on the outpost
2. Consider Qdrant as on-demand restore-only (don't run it resident)
3. If Claude Code absolutely won't fit at 1GB, escalate to e2-small (but costs $12+/mo, off-budget)

---

## Next Checkpoints

1. ✅ **Infrastructure ready** (VM created, IAP verified, keys deployed) — DONE
2. ⏳ **Heartbeat activated** — Commander runs ACTIVATE_P2.sh (blocks Step 1)
3. ⏳ **Provisioning complete** — Script runs on VM, fit-test passes/warns (10 min)
4. ⏳ **Real-world test** — Commander tests from non-home network (5 min)
5. ✅ **Closure** — SSS-A68ABE66 closed with front + back gate verification

**Estimated total time from here:** ~30 minutes (mostly waiting for Commander input + provisioning script)

---

## Plan Integration

This runbook is part of the larger **"Thunderbird GCP Continuity-of-Operations (COO) Plan"**:
- **Full plan:** `/home/john/.claude/plans/gleaming-riding-canyon.md` (ADDENDUM section)
- **Memory reference:** `project_coo_plan_gcp_continuity.md`
- **SSS tracking:** SSS-A68ABE66 (created 2026-07-26, awaiting Commander decision)

---

**Last update:** 2026-07-26 16:09 UTC  
**Status:** Awaiting Commander actions (Step 1 + Step 7)  
**Ready to proceed?** Run the steps above in order and report results.
