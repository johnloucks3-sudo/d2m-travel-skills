# YOGA-YAYA — 30-Minute Emergency Recovery Playbook
**Scenario:** YOGA is fully dead from Belize. No SSH, no code.d2mluxury.quest, no MCP.
**Goal:** Back to 80% D2M ops capability within 30 minutes.
**Owner:** Commander (self-service) | **Authored:** V. Hale, VCS | **2026-05-26**

---

## WHAT YOU LOSE WHEN YOGA IS YAYA

| Service | Impact |
|---------|--------|
| code.d2mluxury.quest (ttyd) | No terminal — primary casualty |
| MCP server (mcp.d2mluxury.quest) | No AI tools |
| n8n (n8n.d2mluxury.quest) | 24 workflows paused |
| Telegram bots (D2MC2C, Dani) | No C2 over Telegram |
| All cloudflared routes | All YOGA subdomains dark |

## WHAT YOU KEEP (cloud-native, YOGA-independent)

| Service | Still works |
|---------|------------|
| Gmail (d2mconcierge + johnloucks3) | ✅ Full access |
| Google Drive | ✅ Full access |
| Claude.ai / Claude Code web | ✅ Full AI capability |
| Thunderbird repo (GitHub) | ✅ Full history |
| TESS (crm.myagentgenie.com) | ✅ Full booking access |
| Google Sheets (Booking Master) | ✅ Full access |
| Tailscale | ✅ If YOGA wakes via WoL |

---

## THE 30-MINUTE RECOVERY SEQUENCE

### MINUTE 0-2: Assess
- [ ] Can you ping YOGA? `ping 100.69.222.124` (Tailscale)
- [ ] If YOGA responds but ttyd is dark → run restore script via SSH:
  ```
  ssh john@100.69.222.124 ~/Thunderbird/scripts/restore_nginx_ttyd.sh
  ```
- [ ] If YOGA does NOT respond → proceed to WoL wake

### MINUTE 2-5: Wake YOGA (WoWLAN — no ethernet needed)
**From any device on same network OR via cloud relay:**
```bash
# Send magic packet to YOGA's WiFi MAC
wakeonlan c0:35:32:06:20:e1
```
**YOGA WiFi MAC:** `ip link show wlp2s0` — confirm and record below:
> YOGA wlp2s0 MAC: c0:35:32:06:20:e1 (confirmed 2026-05-26)

**Wait 60 seconds** → retry SSH.

### MINUTE 5-10: If YOGA still down — Hard power cycle
- [ ] If TP-Link Kasa smart plug is installed: Open Kasa app → power cycle YOGA
- [ ] Wait 90 seconds for boot → retry SSH

### MINUTE 10-15: If YOGA boots — verify services
```bash
ssh john@100.69.222.124 "
  systemctl --user status cloudflared | grep Active
  curl -s -o /dev/null -w '%{http_code}' http://localhost:8099/
  curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/
"
```

### MINUTE 15-30: If YOGA is TRULY dead — cloud fallback ops

**Telegram C2 (without bots):**
- Direct message to Commander inbox via phone
- All client communication via Gmail directly

**n8n (most critical workflows):**
Priority 1 — Fare Watch: Check fares manually at deluxecruises.com / cruisedirect.com
Priority 2 — Morning Brief: Run manually from Claude.ai with `/resume` + session context
Priority 3 — Client Email Sweep: Gmail search `is:unread from:(silversea OR regent OR viking)`

**MCP tools (without server):**
- Claude.ai web has Google Drive MCP via claude.ai integrations
- Gmail accessible directly
- TESS at crm.myagentgenie.com directly

**Emergency VPS (if >48h outage):**
1. DigitalOcean → Create Droplet → Ubuntu 22.04 → $6/mo basic
2. `apt install -y python3-pip nodejs npm`
3. Clone repo: `git clone https://github.com/[repo] Thunderbird`
4. `cd Thunderbird && pip install -r requirements.txt`
5. Start Telegram bots: `python3 OpsCenter/thunderbird_telegram_gw.py &`
6. ETA: 25 minutes to partial bot capability

---

## KEY CREDENTIALS & ENDPOINTS (Belize kit)

| Service | URL / Command | Auth |
|---------|---------------|------|
| YOGA SSH | `ssh john@100.69.222.124` | SSH key |
| ttyd | code.d2mluxury.quest | john / 5277 |
| MCP | mcp.d2mluxury.quest | john / 5277 |
| n8n | n8n.d2mluxury.quest | admin / (saved in browser) |
| TESS | crm.myagentgenie.com | (saved in browser) |
| Gmail | gmail.com | d2mconcierge@gmail.com |
| Router admin | 192.168.50.1 | admin / (your password) |

---

## PRE-BELIZE CHECKLIST (complete before September 2026)

- [ ] Record YOGA wlp2s0 MAC address in this doc
- [ ] Install WoWLAN test: send magic packet from phone → confirm YOGA wakes
- [ ] Install Kasa smart plug on YOGA power outlet
- [ ] Test Kasa power cycle from outside home network
- [ ] Test Tailscale from mobile data (not home WiFi)
- [ ] Confirm cloudflared auto-reconnects after YOGA reboot (wait 90s, test ttyd)

---

*— V. Hale, VCS · Thunderbird Wing · 2026-05-26*
*Review: 2026-08-15 (pre-September gate)*
