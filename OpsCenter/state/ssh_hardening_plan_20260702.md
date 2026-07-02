# SSH Hardening Plan — YOGA (192.168.1.198 / 100.69.222.124 Tailscale)
**Date:** 2026-07-02 | **Mission:** MISSION-250 | **Status:** COMPLETE — verified live

---

## Current State (Verified 2026-07-02 via live SSH probe)

```
/etc/ssh/sshd_config active lines:
  UsePAM yes
  ClientAliveInterval 60
  ClientAliveCountMax 3
  TCPKeepAlive yes
  AllowUsers john
  PasswordAuthentication no
  KbdInteractiveAuthentication no
```

### sshguard
- **Status:** active (running) since Sun 2026-06-28 10:36:47 MDT — 3 days uptime
- **Enabled:** yes (preset: disabled, manually enabled)
- **PID:** 1582 — 8 tasks, ~1.5 min CPU over 3 days (healthy, light load)
- **Config:** /etc/sshguard/whitelist present

### Auth log (last 20 entries)
- All logins: `Accepted publickey for john from 100.69.222.124` (Tailscale)
- Zero password attempts, zero brute force, zero unauthorized users
- Only connection source: 100.69.222.124 (YOGA Tailscale self-address via Thunderbird)

---

## Hardening Checklist — All Items Verified COMPLETE

| Control | Target | Status |
|---------|--------|--------|
| PasswordAuthentication no | Disable password login | **DONE** |
| KbdInteractiveAuthentication no | Disable keyboard-interactive | **DONE** |
| AllowUsers john | Restrict to single user | **DONE** |
| sshguard | Brute-force IP blocking | **DONE — active 3 days** |
| PubkeyAuthentication | Key-only login enforced (implicit when pw off) | **DONE** |
| PermitRootLogin | Not explicitly set — defaults to `prohibit-password` (openSUSE default), root key login blocked by AllowUsers john | **ACCEPTABLE** |
| MaxAuthTries | Not set — defaults to 6. sshguard compensates at the firewall layer | **ACCEPTABLE** |
| LoginGraceTime | Not set — defaults to 120s. Low-risk given Tailscale-only exposure | **ACCEPTABLE** |
| CrowdSec | Not installed | **NOT REQUIRED — sshguard covers single-node use case** |

---

## Residual Gap Assessment (A7 Finding)

### GAP-1: PermitRootLogin not explicitly hardened
**Risk:** LOW. openSUSE default is `prohibit-password` which already blocks root password login. AllowUsers john further blocks root key login. Explicit `PermitRootLogin no` would be belt-and-suspenders.
**Commander action (optional):**
```bash
sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
# If line not present:
echo 'PermitRootLogin no' | sudo tee -a /etc/ssh/sshd_config
sudo systemctl reload sshd
```

### GAP-2: MaxAuthTries not minimized
**Risk:** LOW. sshguard blocks IPs after 4 failures at the firewall layer, making MaxAuthTries largely irrelevant. Explicit `MaxAuthTries 3` is hygiene.
**Commander action (optional):**
```bash
echo 'MaxAuthTries 3' | sudo tee -a /etc/ssh/sshd_config
sudo systemctl reload sshd
```

### GAP-3: CrowdSec not installed
**Assessment:** NOT REQUIRED for this threat model. CrowdSec adds value in distributed environments (shared threat intel across multiple servers). YOGA is a single-node home lab behind Tailscale with no public SSH port forward confirmed. sshguard is the correct tool here. CrowdSec would add complexity without proportional security gain.
**Metric:** If YOGA gains a public-facing port (e.g., ssh.d2mluxury.quest tunnel activates), reassess CrowdSec.

---

## What Was Done (Execution Log)

| Date | Action | Executor |
|------|--------|----------|
| 2026-06-15 | sshguard installed + enabled. AllowUsers john applied + sshd reloaded | Auto-executor |
| 2026-06-18 | Verification audit — AllowUsers + sshguard confirmed | Auto-executor |
| 2026-06-24 | PasswordAuthentication no + KbdInteractiveAuthentication no applied | Auto-executor |
| 2026-07-02 | Live wire verification — all controls confirmed active | A7 Sterling |

---

## Measurement & Cadence

**Metric:** sshguard block events per 7-day window (target: captured and non-zero on any brute-force attempt)
**Measurement:** `sudo journalctl -u sshguard --since '7d ago' | grep -c BLOCK` — weekly
**Threshold:** GREEN = 0 unblocked password attempts. RED = any `Accepted password` in auth log.
**Owner:** A7 Sterling
**Cadence:** Included in weekly Baldrige sweep (Sunday 18:00 MT)

---

## Commander Actions Required

**Optional hardening (belt-and-suspenders):**
```bash
# Run on YOGA — keep existing session open before executing
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.20260702
echo 'PermitRootLogin no' | sudo tee -a /etc/ssh/sshd_config
echo 'MaxAuthTries 3' | sudo tee -a /etc/ssh/sshd_config
sudo systemctl reload sshd
# Verify: ssh yoga "cat /etc/ssh/sshd_config | grep -E 'PermitRoot|MaxAuth'"
```

**No Commander action required** to close MISSION-250. All primary deliverables are live.

---

*A7 Sterling — 2026-07-02 | Baldrige Standard: measure, threshold, owner on every finding*
