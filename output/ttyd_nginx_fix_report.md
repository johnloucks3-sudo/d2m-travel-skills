# ttyd / nginx Fix Report
**Generated:** 2026-05-16  
**Author:** Col Victoria "Iron Vic" Hale, COS/COO  
**Status:** COMPLETE — Infrastructure is OPERATIONAL

---

## EXECUTIVE SUMMARY

The ttyd/nginx proxy is **already working**. No fix was needed. The previous "bind() Permission Denied" error was a red herring — it was the `nginx -t` test failing because `john` lacks write access to `/var/log/nginx/error.log`, not because the service itself failed. nginx has been running successfully with the ttyd proxy config since 2026-05-13 13:36 MDT.

---

## FINDINGS

### 1. nginx
| Item | Status |
|---|---|
| Binary | `/usr/sbin/nginx` — v1.29.8 |
| Service | ACTIVE, running since 2026-05-13 13:36 MDT |
| Config loaded | `/etc/nginx/vhosts.d/ttyd.conf` — valid, loaded |
| Port 8099 | LISTENING, responding |

**Why `nginx -t` shows "failed" when run as john:**  
nginx test requires write access to `/var/log/nginx/error.log` and `/run/nginx.pid`. The john user doesn't have that access. Running `sudo nginx -T` shows the config is syntactically valid and loaded correctly. The service starts as root and has no permission issue. This was the false alarm.

### 2. ttyd
| Item | Status |
|---|---|
| Process | RUNNING — PID 1844 |
| Command | `/home/john/bin/ttyd --port 3100 --interface 127.0.0.1 --writable bash` |
| Binding | `127.0.0.1:3100` (loopback only — correct) |
| Direct test | `curl http://127.0.0.1:3100/` → HTTP 200 |
| Started | May 13 (same day as nginx reload) |

### 3. nginx → ttyd Proxy
| Item | Status |
|---|---|
| Config file | `/etc/nginx/vhosts.d/ttyd.conf` |
| Listen port | 8099 (IPv4 + IPv6) |
| Server name | `code.d2mluxury.quest` |
| Proxy target | `http://127.0.0.1:3100` |
| WebSocket headers | Present (`Upgrade`, `Connection: upgrade`) |
| Auth | Basic auth enabled — `/etc/nginx/ttyd.htpasswd` |
| Auth user | `john` (bcrypt hash) |
| Proxy test | `curl http://127.0.0.1:8099/` → HTTP 401 (auth gate working) |
| External test | `curl http://192.168.1.198:8099/` → HTTP 401 (externally reachable) |

### 4. nginx.conf include structure
The `include vhosts.d/*.conf;` directive is at the **http block level** (line 133 of nginx.conf), not inside any server block. The commented-out HTTPS server block above it does not affect this include. The parsed config confirms the ttyd server block is loaded as a standalone virtual host. No structural issue.

---

## WHAT WAS TRIED IN THIS DIAGNOSIS

1. Verified nginx binary at `/usr/sbin/nginx` (not in john's PATH — system binary)
2. Confirmed nginx service running since May 13 via systemctl
3. Read `/etc/nginx/nginx.conf` — found `include vhosts.d/*.conf` at http level
4. Read `/etc/nginx/vhosts.d/ttyd.conf` — config is correct and complete
5. Verified `include vhosts.d/*.conf` position via `sudo nginx -T` output
6. Confirmed ttyd process running via `ps aux` — `127.0.0.1:3100`, writable bash
7. Tested `curl http://127.0.0.1:3100/` → 200 (ttyd healthy)
8. Tested `curl http://127.0.0.1:8099/` → 401 (nginx proxy + auth gate healthy)
9. Tested `curl http://192.168.1.198:8099/` → 401 (externally reachable)

---

## CURRENT ttyd CONFIG

```nginx
# /etc/nginx/vhosts.d/ttyd.conf
server {
    listen 8099;
    listen [::]:8099;
    server_name code.d2mluxury.quest;

    auth_basic "Thunderbird Terminal";
    auth_basic_user_file /etc/nginx/ttyd.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;

        # WebSocket support — required for ttyd
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

---

## HOW TO ACCESS

**Local (YOGA):**
```
http://127.0.0.1:8099/
```

**LAN (from any machine on 192.168.x.x):**
```
http://192.168.1.198:8099/
```

**By hostname (if DNS/hosts resolves `code.d2mluxury.quest` to 192.168.1.198):**
```
http://code.d2mluxury.quest:8099/
```

**Credentials:** Username `john` + password (bcrypt hash in `/etc/nginx/ttyd.htpasswd`). Password not known to this session — set with `sudo htpasswd /etc/nginx/ttyd.htpasswd john`.

---

## ONE OPEN ITEM

ttyd is started as a user process (PID 1844, no systemd service). If YOGA reboots, ttyd will not auto-start. Recommend creating a systemd user service:

```bash
# /home/john/.config/systemd/user/ttyd.service
[Unit]
Description=ttyd Web Terminal
After=network.target

[Service]
ExecStart=/home/john/bin/ttyd --port 3100 --interface 127.0.0.1 --writable bash
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

Enable with:
```bash
systemctl --user enable --now ttyd.service
loginctl enable-linger john  # keeps service alive when john is not logged in
```

This is below the Commander gate — Hale can execute on direction.

---

## NEXT STEP

**Zero action required to make ttyd accessible** — it is accessible now at `http://192.168.1.198:8099/`.

Only action needed: **recover the htpasswd password** for the `john` user, or reset it:
```bash
sudo htpasswd /etc/nginx/ttyd.htpasswd john
# Enter new password when prompted
```

If Cloudflare tunnel is pointed at port 8099, `code.d2mluxury.quest` would be reachable over the public internet with the same auth gate.

---

*— Col Victoria "Iron Vic" Hale | Thunderbird Wing | 2026-05-16*
