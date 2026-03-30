# JAPAN DEPARTURE READINESS CHECKLIST
# Departure: April 10, 2026 | Return: May 11, 2026
# Author: Claude Sonnet 4.6 | Date: 2026-03-30

---

## WATCHDOG STATUS — CURRENT

Watchdog runs every 2 minutes — CONFIRMED ✅
Auto-restarts crashed services — CONFIRMED ✅
Crash loop detection — CONFIRMED ✅
MCP deep health check — CONFIRMED ✅
Stuck queue detection — CONFIRMED ✅
Telegram alerts independent of C2 bot — CONFIRMED ✅

---

## BEFORE APRIL 10 — REQUIRED

### 1. Fix failed services (currently failing — fix before departure)
  [ ] d2m-intel-telegram.service — investigate and fix or disable cleanly
  [ ] d2m-preflight.service — investigate and fix or disable cleanly
  Reason: failed units mask real failures; want clean green board at departure

### 2. Add daily heartbeat to watchdog
  [ ] Watchdog sends "YOGA alive — all services green" Telegram once daily at 0800 MT
  [ ] Confirms Commander is getting signal from YOGA even when nothing is broken
  [ ] If heartbeat stops arriving → Commander knows YOGA is down

### 3. Add disk space check to watchdog
  [ ] Check / and /home usage every watchdog run
  [ ] Alert if > 85% full
  [ ] Reason: 31 days of logs, intel digests, chat logs could fill disk

### 4. Verify log rotation is working
  [ ] thunderbird-logrotate.timer is installed — confirm it's running
  [ ] Check logs/ directory size now and project 31-day growth
  [ ] Confirm RotatingFileHandler limits on all major log files

### 5. SSE/HTTP migration (mobile MCP access)
  [ ] Convert D2M-COMMAND-HUB to SSE transport on port 8766
  [ ] Bind to Tailscale IP only
  [ ] Add thunderbird-mcp-sse.service with Restart=on-failure
  [ ] Test from mobile on Tailscale — verify all tools reachable
  [ ] Add mcp-sse to watchdog SERVICES dict

### 6. Session checkpoint
  [ ] Create session_checkpoint_latest.md schema
  [ ] Claude writes checkpoint at end of each session before April 10
  [ ] Verify checkpoint restore works from mobile

---

## BEFORE APRIL 10 — RECOMMENDED

### 7. UPS / surge protection on YOGA power
  Physical layer — no software fix for power failure

### 8. Verify Tailscale is set to auto-start on YOGA boot
  [ ] systemctl status tailscaled
  [ ] If YOGA reboots (power blip), Tailscale must reconnect automatically

### 9. Verify lingerd / linger is enabled for user services
  [ ] loginctl enable-linger john
  [ ] Ensures user systemd services survive Commander logout

### 10. Test full recovery scenario before departure
  [ ] Reboot YOGA deliberately
  [ ] Verify all services restart automatically
  [ ] Verify Telegram heartbeat arrives within 3 minutes of boot
  [ ] Verify Tailscale reconnects and mobile MCP works

---

## NICE TO HAVE (if time before April 10)

- Rate limit auto-update via Hale (Phase 2 / Decision 4)
- ADK evaluation first pass
- Routing data baseline snapshot

---
*Update this checklist as items are completed. Goal: all REQUIRED items done by April 8.*
