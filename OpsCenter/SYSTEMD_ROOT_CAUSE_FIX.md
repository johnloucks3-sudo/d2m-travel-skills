## Root Cause: /home/john Permissions (711) + systemd Path Traversal
**Date: 2026-04-04 | Author: COS Hale**

### Problem
`/home/john` has permissions `711` (execute-only for non-owners).
- systemd runs as root (NOT the owner of /home/john)
- root falls under "others" → only has execute (traverse), no read
- Systemd services pointing to `/home/john/Thunderbird/.venv/bin/python3` get `203/EXEC`
- `sudo cp /home/john/.../*` fails silently — can traverse but cannot access files
- FPD alert service and git-commit-alert service both fail with `203/EXEC`
- Evernote backup systemd install cannot copy files

### Fix (paste into terminal):
```bash
sudo chmod 755 /home/john
sudo cp /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.service /etc/systemd/system/
sudo cp /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.timer /etc/systemd/system/
for svc in /etc/systemd/system/thunderbird-*.service; do sudo sed -i 's|/home/john/Thunderbird/.venv/bin/python3|/usr/bin/python3|g' "$svc"; done
sudo systemctl daemon-reload
sudo systemctl enable --now thunderbird-evernote-backup.timer
sudo systemctl restart thunderbird-fpd-alert.service thunderbird-git-commit-alert.service
echo "=== VERIFY ==="
systemctl list-timers --all | grep -iE 'thunderbird|evernote|gdrive'
systemctl is-active thunderbird-fpd-alert.service thunderbird-git-commit-alert.service
```

### After Fix:
- /home/john: 755 (standard, readable + traversable)
- All systemd services: /usr/bin/python3 (bypasses .venv entirely)
- Evernote timer: fires weekly Mon 02:00 MDT
- FPD alert: running
- Git-commit alert: running
- GDrive sync: running (already verified)
