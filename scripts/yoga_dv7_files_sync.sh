#!/bin/bash
# yoga_dv7_files_sync.sh — curated, secret-safe rsync of YOGA session output → dv7.
#
# Runs ON YOGA (workstation, not always-on). Pushes the directories the Commander
# would want to reach from a phone/other device when YOGA is off, to the always-on
# dv7 box (~/thunderbird_files), where scripts/dv7_files_server.py serves them at
# files.d2mluxury.quest behind Cloudflare Access.
#
# dv7 being offline is NORMAL (it is a workstation too) — this script skips cleanly
# and retries on the next timer rather than erroring. See deploy/FILES_DV7_RUNBOOK.md.
set -uo pipefail

SRC="/home/john/Thunderbird"
DEST_HOST="dv7"                 # ~/.ssh/config alias -> 10.0.0.64, user john
DEST_DIR="thunderbird_files"    # lands at ~/thunderbird_files on dv7
LOG="/home/john/Thunderbird/logs/yoga_dv7_files_sync.log"
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new"

mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

# Curated set — session output worth reaching without YOGA. Deliberately NOT the
# whole repo: no logs/ (1GB), no storage backups, no code, no secrets.
INCLUDE_ITEMS=(
  dossiers
  output
  intel
  OpsCenter/collaboration
  Blackboard
  session_autosave_latest.md
  hale_brief.md
  hale_state.json
)

# Secret-safe excludes — mirrors scripts/thunderbird_sync_filters.txt. Belt-and-
# suspenders: the include list already omits credential dirs, but rsync enforces it.
EXCLUDES=(
  --exclude='creds/**'
  --exclude='credentials.json'
  --exclude='*_token.json'
  --exclude='*_credentials.json'
  --exclude='gmail_token.json'
  --exclude='drive_token.json'
  --exclude='.env*'
  --exclude='*.env'
  --exclude='*.pem'
  --exclude='*.key'
  --exclude='.api_token'
  --exclude='__pycache__/**'
  --exclude='node_modules/**'
  --exclude='.venv/**'
  --exclude='venv/**'
  --exclude='.git/**'
  --exclude='storage/backups/**'
  --exclude='storage/browser_profiles/**'
  --exclude='*.log'
)

log "=== sync start ==="

if ! ssh $SSH_OPTS "$DEST_HOST" true 2>/dev/null; then
  log "dv7 offline/unreachable — skipped (retry next timer)"
  exit 0
fi

ssh $SSH_OPTS "$DEST_HOST" "mkdir -p ~/$DEST_DIR" 2>/dev/null

rc=0
for item in "${INCLUDE_ITEMS[@]}"; do
  if [ ! -e "$SRC/$item" ]; then
    log "skip missing: $item"
    continue
  fi
  rsync -az --delete --timeout=60 "${EXCLUDES[@]}" \
    -e "ssh $SSH_OPTS" \
    "$SRC/$item" "$DEST_HOST:$DEST_DIR/" >> "$LOG" 2>&1 || rc=$?
done

if [ "$rc" -eq 0 ]; then
  log "=== sync ok ==="
else
  log "=== sync finished with rsync rc=$rc ==="
fi
exit 0
