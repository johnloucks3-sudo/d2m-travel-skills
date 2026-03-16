# DV7 Migration Plan — Scheduler + Heartbeat
## Move all automation from YOGA to dv7 (always-on server)

---

## Why
- YOGA (Chromebook/Crostini) is a workstation — not always on
- dv7 (HP Pavilion, Linux Mint) is always-on with systemd + cloudflared tunnel
- Moving scheduler to dv7 means heartbeats, alerts, and backups run 24/7
- Commander can work from ANY thin client via SSH/tunnel

## Current dv7 State
- **IP:** 10.0.0.64 (LAN) / ssh.d2mluxury.quest (remote)
- **Running:** d2m-mcp.service, d2m-api.service, d2m-tunnel.service
- **Python:** needs verification
- **USB Drive:** 1TB removable, needs mount point setup
- **User:** john

## Migration Steps

### Phase 1: Sync Code to dv7
```bash
# From YOGA — rsync entire Thunderbird to dv7
rsync -avz --exclude='.venv' --exclude='venv' --exclude='__pycache__' \
    --exclude='node_modules' --exclude='.git' \
    ~/Thunderbird/ john@10.0.0.64:~/Thunderbird/
```

### Phase 2: Setup Python Environment on dv7
```bash
ssh john@10.0.0.64
cd ~/Thunderbird
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt  # need to generate this first
# Copy credentials
# - credentials.json (Google service account)
# - gmail_token.json (Gmail OAuth)
# - drive_token.json (Drive OAuth)
# - calendar_token.json (Calendar OAuth — if exists)
```

### Phase 3: Copy Secrets
```bash
# From YOGA
scp ~/Thunderbird/credentials.json john@10.0.0.64:~/Thunderbird/
scp ~/Thunderbird/gmail_token.json john@10.0.0.64:~/Thunderbird/
scp ~/Thunderbird/drive_token.json john@10.0.0.64:~/Thunderbird/

# Copy env vars
ssh john@10.0.0.64 'cat >> ~/.bashrc << EOF
export GROQ_API_KEY="***REMOVED-SECRET***"
export HF_API_KEY="***REMOVED-SECRET***"
export TOGETHER_API_KEY="***REMOVED-SECRET***"
export XAI_API_KEY="***REMOVED-SECRET***"
export EVERNOTE_TOKEN="TBD"
EOF'
```

### Phase 4: Create Scheduler Service on dv7
```bash
# Create systemd user service
cat > ~/.config/systemd/user/d2m-scheduler.service << 'EOF'
[Unit]
Description=D2M Thunderbird Scheduler
After=network-online.target d2m-mcp.service

[Service]
Type=simple
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/.venv/bin/python thunderbird_scheduler.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable d2m-scheduler.service
systemctl --user start d2m-scheduler.service
```

### Phase 5: Setup USB Drive
```bash
# Find the USB drive
lsblk
# Mount (example — adjust device name)
sudo mkdir -p /mnt/usb
sudo mount /dev/sdb1 /mnt/usb
# Add to fstab for auto-mount
echo '/dev/sdb1 /mnt/usb auto defaults,nofail 0 0' | sudo tee -a /etc/fstab
# Create backup directory
mkdir -p /mnt/usb/thunderbird_backups
```

### Phase 6: Setup Ongoing Sync (YOGA → dv7)
```bash
# Cron on YOGA — sync code changes to dv7 hourly during work hours
# (or use the 0300 Drive backup as the source of truth)
```

### Phase 7: Disable Scheduler on YOGA
```bash
# On YOGA — stop local scheduler to avoid duplicate jobs
systemctl --user stop thunderbird-scheduler.service
systemctl --user disable thunderbird-scheduler.service
```

## After Migration
- All heartbeats, payment alerts, email classifier, etc. run on dv7
- YOGA becomes pure workstation (Claude CLI + development)
- Chromebook connects via tunnel — same experience
- USB drive gets local backups alongside Drive + Evernote cloud backups

## Verification Checklist
- [ ] All 16 scheduler jobs show in --status on dv7
- [ ] SMS alerts arrive on Commander's phone
- [ ] Gmail drafts appear in Commander Review
- [ ] Drive sync works from dv7
- [ ] USB backup writes successfully
- [ ] Evernote weekly backup runs
- [ ] Health check on dv7 monitors scheduler service
