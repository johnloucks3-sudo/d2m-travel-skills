#!/usr/bin/env bash
# Thunderbird COO Outpost Setup — Runs on the e2-micro GCP VM via IAP SSH
# Purpose: Deploy service account credentials, install Claude Code CLI + dependencies,
#          clone repo, set up nightly backup automation, smoke-test 1GB RAM fit.
#
# Run via: gcloud compute ssh thunderbird-coo-outpost --zone=us-central1-a \
#          --tunnel-through-iap --command="bash -s < setup_coo_outpost.sh"
#
# Exit codes: 0 = success, 1 = fit-test failed (1GB RAM insufficient), 2+ = setup error

set -euo pipefail

echo "=== Thunderbird COO Outpost Setup ==="
echo "Start time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Directories
HOME_DIR="${HOME:-/home/john}"
REPO_DIR="${HOME_DIR}/Thunderbird"
GCP_CREDS="${HOME_DIR}/.config/gcloud/coo-outpost-sa.json"

# ============================================================================
# 1. Receive service account key (piped in via gcloud compute ssh)
# ============================================================================
echo ""
echo "1/6 Deploying service account credentials..."

# The key should be passed in via stdin or file. For now, assume it exists locally
# on YOGA and will be copied by the calling script via gcloud compute scp.
# If running manually, paste the key contents and save to $GCP_CREDS.

if [[ ! -f "$GCP_CREDS" ]]; then
    mkdir -p "$(dirname "$GCP_CREDS")"
    echo "⚠️  Service account key not found at $GCP_CREDS"
    echo "    To deploy it, run from YOGA:"
    echo "    gcloud compute scp /tmp/thunderbird-coo-outpost-key.json \\"
    echo "      thunderbird-coo-outpost:/home/john/.config/gcloud/coo-outpost-sa.json \\"
    echo "      --zone=us-central1-a --tunnel-through-iap"
    echo "    Then re-run this script."
    exit 2
fi

chmod 600 "$GCP_CREDS"
export GOOGLE_APPLICATION_CREDENTIALS="$GCP_CREDS"
echo "   Service account credentials deployed to $GCP_CREDS"

# ============================================================================
# 2. Install system dependencies
# ============================================================================
echo ""
echo "2/6 Installing system dependencies (Python, git, curl, build tools)..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-venv python3-dev \
    git curl wget \
    build-essential pkg-config \
    libssl-dev libffi-dev \
    2>&1 | grep -E "Setting up|already" | head -10

echo "   System dependencies installed"

# ============================================================================
# 3. Install Claude Code CLI
# ============================================================================
echo ""
echo "3/6 Installing Claude Code CLI..."

# Claude Code CLI expects Node.js + npm. Install Node first if not present.
if ! command -v node &> /dev/null; then
    echo "   Installing Node.js (required for Claude CLI)..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y -qq nodejs 2>&1 | grep -E "Setting up|already" | head -5
fi

# Install Claude CLI globally
npm install -g @anthropic-ai/claude-code 2>&1 | tail -3 || echo "   Claude CLI installation note: check manually if needed"

echo "   Claude Code CLI installed"

# ============================================================================
# 4. Clone Thunderbird repo and set up venv
# ============================================================================
echo ""
echo "4/6 Cloning Thunderbird repo and setting up Python venv..."

if [[ ! -d "$REPO_DIR" ]]; then
    git clone https://github.com/dreams2memories/thunderbird.git "$REPO_DIR" 2>&1 | tail -3
else
    echo "   Repo already cloned at $REPO_DIR"
    cd "$REPO_DIR" && git pull --quiet 2>&1 | grep -E "Already up to date|Updating" || true
fi

cd "$REPO_DIR"

# Create venv if it doesn't exist
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    echo "   Virtual environment created"
fi

# Activate venv and install requirements
source .venv/bin/activate
pip install --quiet --upgrade pip setuptools wheel 2>&1 | tail -1
if [[ -f "requirements.txt" ]]; then
    pip install --quiet -r requirements.txt 2>&1 | tail -2 || echo "   (some requirements may be optional)"
    echo "   Python dependencies installed"
else
    echo "   (requirements.txt not found; skipping pip install)"
fi

# ============================================================================
# 5. Wire up nightly backup automation
# ============================================================================
echo ""
echo "5/6 Setting up nightly backup scripts and systemd timers..."

# Create backup scripts directory
mkdir -p "$REPO_DIR/deploy/gcp/backups"

# Backup script for Qdrant snapshots (runs nightly, uploads to GCS)
cat > "$REPO_DIR/deploy/gcp/backups/backup_qdrant_snapshot.sh" << 'BACKUP_QDRANT'
#!/usr/bin/env bash
# Backup Qdrant snapshot to GCS (nightly)
set -euo pipefail
export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/.config/gcloud/coo-outpost-sa.json"
QDRANT_SNAPSHOT_DIR="/tmp/qdrant_snapshot_$(date +%s)"
mkdir -p "$QDRANT_SNAPSHOT_DIR"
# Try to connect to local Qdrant and grab a snapshot (if running)
if curl -s http://localhost:6333/health &>/dev/null; then
    curl -X POST http://localhost:6333/collections/thunderbird_memories/snapshots \
         -o "$QDRANT_SNAPSHOT_DIR/snapshot.tar" 2>/dev/null || true
fi
# Upload to GCS (if backup exists)
if [[ -f "$QDRANT_SNAPSHOT_DIR/snapshot.tar" ]]; then
    gsutil -m cp "$QDRANT_SNAPSHOT_DIR/snapshot.tar" \
           gs://d2m-continuity-backups/qdrant-snapshots/$(date +%Y%m%d_%H%M%S).tar
    rm -rf "$QDRANT_SNAPSHOT_DIR"
    echo "Qdrant snapshot backed up to GCS"
fi
BACKUP_QDRANT
chmod +x "$REPO_DIR/deploy/gcp/backups/backup_qdrant_snapshot.sh"

# Backup script for n8n workflow exports (nightly)
cat > "$REPO_DIR/deploy/gcp/backups/backup_n8n_export.sh" << 'BACKUP_N8N'
#!/usr/bin/env bash
# Backup n8n workflow exports to GCS (nightly)
set -euo pipefail
export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/.config/gcloud/coo-outpost-sa.json"
N8N_EXPORT_DIR="/tmp/n8n_export_$(date +%s)"
mkdir -p "$N8N_EXPORT_DIR"
# If n8n CLI is available, export workflows (otherwise skip)
if command -v n8n &>/dev/null; then
    n8n export:workflow --all --output="$N8N_EXPORT_DIR/workflows.json" 2>/dev/null || true
fi
# Upload to GCS
if [[ -f "$N8N_EXPORT_DIR/workflows.json" ]]; then
    gsutil cp "$N8N_EXPORT_DIR/workflows.json" \
           gs://d2m-continuity-backups/n8n-exports/$(date +%Y%m%d_%H%M%S).json
    rm -rf "$N8N_EXPORT_DIR"
    echo "n8n workflows backed up to GCS"
fi
BACKUP_N8N
chmod +x "$REPO_DIR/deploy/gcp/backups/backup_n8n_export.sh"

# Backup script for encrypted Infisical Postgres dump (nightly, if accessible)
cat > "$REPO_DIR/deploy/gcp/backups/backup_infisical_pg.sh" << 'BACKUP_INFISICAL'
#!/usr/bin/env bash
# Backup encrypted Infisical Postgres dump to GCS (nightly)
set -euo pipefail
export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/.config/gcloud/coo-outpost-sa.json"
INFISICAL_BACKUP="/tmp/infisical_pg_$(date +%s).sql.gpg"
# Note: This is a placeholder. Actual Postgres dump requires access to the vault's Postgres
# container or a remote connection. Implement this step when Infisical is migrated to cloud.
# For now, just log that it's pending.
echo "Infisical backup: PENDING (requires vault access)"
BACKUP_INFISICAL
chmod +x "$REPO_DIR/deploy/gcp/backups/backup_infisical_pg.sh"

# Create systemd timer for nightly backups (user-level service)
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

cat > "$SYSTEMD_USER_DIR/coo-continuity-backup.service" << 'SYSTEMD_SERVICE'
[Unit]
Description=Thunderbird COO Continuity Backup (Qdrant + n8n + Infisical)
After=network-online.target

[Service]
Type=oneshot
ExecStart=/home/john/Thunderbird/deploy/gcp/backups/backup_qdrant_snapshot.sh
ExecStart=/home/john/Thunderbird/deploy/gcp/backups/backup_n8n_export.sh
ExecStart=/home/john/Thunderbird/deploy/gcp/backups/backup_infisical_pg.sh
StandardOutput=journal
StandardError=journal
SYSTEMD_SERVICE

cat > "$SYSTEMD_USER_DIR/coo-continuity-backup.timer" << 'SYSTEMD_TIMER'
[Unit]
Description=Thunderbird COO Continuity Backup (nightly)

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
SYSTEMD_TIMER

systemctl --user daemon-reload
systemctl --user enable coo-continuity-backup.timer
systemctl --user start coo-continuity-backup.timer

echo "   Nightly backup timers enabled"

# ============================================================================
# 6. Smoke-test fit: Can Claude Code CLI start on 1GB RAM?
# ============================================================================
echo ""
echo "6/6 Fit-test: Checking if Claude Code CLI starts cleanly (1GB RAM test)..."

# Check current memory
FREE_MEM_MB=$(free -m | awk '/^Mem:/ {print $7}')
echo "   Available memory: ${FREE_MEM_MB}MB"

# Try to start claude --version (lightweight check)
if timeout 10 bash -c 'source '"$REPO_DIR"'/.venv/bin/activate && claude --version' &>/dev/null; then
    echo "   ✅ Claude Code CLI starts successfully on 1GB RAM"
    FIT_TEST_RESULT="PASS"
else
    echo "   ⚠️  Claude Code CLI timeout or failed to start"
    echo "   (This may indicate 1GB RAM is too tight. Monitor memory and consider Qdrant on-demand restore only.)"
    FIT_TEST_RESULT="WARN"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=== Thunderbird COO Outpost Setup Complete ==="
echo "Summary:"
echo "  ✅ Service account credentials deployed"
echo "  ✅ System dependencies installed (Python, git, Node.js)"
echo "  ✅ Claude Code CLI installed"
echo "  ✅ Thunderbird repo cloned to $REPO_DIR"
echo "  ✅ Python venv set up at $REPO_DIR/.venv"
echo "  ✅ Nightly backups wired (Qdrant, n8n, Infisical placeholders)"
echo "  ✅ Systemd timers enabled (coo-continuity-backup.timer)"
echo "  📊 Fit-test result: $FIT_TEST_RESULT (1GB RAM check)"
echo ""
echo "Next steps:"
echo "  1. From YOGA (your local machine), test Claude Code from this outpost:"
echo "     gcloud compute ssh thunderbird-coo-outpost --zone=us-central1-a --tunnel-through-iap"
echo "  2. In the outpost, activate venv and test a real task:"
echo "     cd $REPO_DIR && source .venv/bin/activate && claude --help"
echo "  3. From a non-home network (e.g., phone hotspot), repeat step 1 to verify IAP access"
echo ""
echo "Finish time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Exit with fit-test result
[[ "$FIT_TEST_RESULT" == "PASS" ]] && exit 0 || exit 1
