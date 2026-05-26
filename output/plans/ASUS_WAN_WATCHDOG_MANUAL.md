# ASUS Router — Enable WAN Watchdog (Manual Steps)
**Time required:** 5 minutes | **Router:** 192.168.50.1 (ASUS ROG)
**Why:** Self-heals WAN outage in <5 min without Commander intervention (replaces the May 2026 manual reboot incident)

---

## STEP-BY-STEP

1. Open browser → `http://192.168.50.1` → login with your admin credentials

2. Navigate: **Advanced Settings** → **WAN** (left sidebar)

3. Select tab: **Internet Connection**

4. Scroll to **"WAN DNS Setting"** section — look for:
   - **"Ping to check Internet connection"** (some firmware labels this **"Enable Internet Connection Monitor"**)

5. Set these values:
   - **Ping IP Address:** `8.8.8.8` (Google DNS — reliable, never goes down)
   - **Interval:** `30` seconds
   - **Max failures before reboot:** `3` (= 90 seconds before auto-reboot)

6. Click **Apply**

---

## ALTERNATE PATH (if not visible on WAN page)

Some ASUS ROG firmware puts this under:
- **Tools** → **Reboot Schedule** (for scheduled reboots — less ideal, but backup)
- **Administration** → **System** → **"Enable Telnet"** then SSH in and set via nvram:
  ```
  nvram set wan_ping_x=1
  nvram set wan_ping_ip=8.8.8.8
  nvram commit
  ```

---

## WHAT THIS DOES

- Every 30 seconds, router pings 8.8.8.8
- If 3 consecutive pings fail (90 sec) → router reboots its WAN interface
- This is exactly what would have fixed the May 2026 outage (modem/router needed reboot)
- After WAN comes back, cloudflared tunnel reconnects automatically within 60 sec

---

## SUCCESS CRITERION

From Belize: WAN drops → self-heals in < 5 min ✅
(Meets Goal criterion #1 from `GOAL_Belize_Internet_Connectivity.md`)

---

*— V. Hale, VCS | 2026-05-26 | Router admin credentials required — cannot automate*
