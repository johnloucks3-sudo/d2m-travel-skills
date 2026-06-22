#!/bin/bash
# fix_d2m_ssl_525.sh — Fix d2mluxury.quest Cloudflare 525 SSL error
# ROOT CAUSE: nginx only listens on :80 (no SSL). Cloudflare 525 = SSL handshake fail to origin.
# COMMANDER: Run this script on YOGA with: ssh yoga "sudo bash" then paste commands below
# OR: Run '! ssh -t yoga' in Claude Code terminal and run manually.
#
# FIX PATH A — Certbot/Let's Encrypt (preferred, free, auto-renew)
# NOTE: Cloudflare must be set to "Flexible" SSL mode BEFORE running certbot,
# then switch back to "Full" after cert is installed.

set -e

DOMAIN="d2mluxury.quest"
EMAIL="johnloucks3@gmail.com"

# Step 1: Install certbot
zypper install -y certbot python3-certbot-nginx

# Step 2: Temporarily set Cloudflare SSL to "Flexible" (or pause proxy for domain)
echo "ACTION NEEDED: Set Cloudflare SSL/TLS to 'Flexible' before continuing"
echo "Cloudflare Dashboard → SSL/TLS → Overview → Flexible"
read -p "Press ENTER after setting Cloudflare to Flexible mode..."

# Step 3: Create minimal nginx vhost for apex domain (HTTP only, for certbot challenge)
cat > /etc/nginx/vhosts.d/d2m-apex.conf << 'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name d2mluxury.quest www.d2mluxury.quest;
    location / {
        return 301 https://www.d2mluxury.quest$request_uri;
    }
}
NGINX

nginx -t && systemctl reload nginx

# Step 4: Get Let's Encrypt certificate
certbot certonly --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL"

# Step 5: Configure nginx with SSL
cat > /etc/nginx/vhosts.d/d2m-apex.conf << 'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name d2mluxury.quest www.d2mluxury.quest;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name d2mluxury.quest www.d2mluxury.quest;

    ssl_certificate /etc/letsencrypt/live/d2mluxury.quest/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/d2mluxury.quest/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        return 200 "Dreams2Memories Travel\n";
        add_header Content-Type text/plain;
    }
}
NGINX

nginx -t && systemctl reload nginx

# Step 6: Switch Cloudflare SSL back to "Full" or "Full (Strict)"
echo "ACTION: Switch Cloudflare SSL/TLS back to 'Full' (or 'Full Strict')"
echo "Verify: curl -sI https://d2mluxury.quest | head -5"

# Step 7: Set up auto-renewal
systemctl enable --now certbot-renew.timer
echo "Done. d2mluxury.quest SSL configured. 525 error should be resolved."
