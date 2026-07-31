#!/usr/bin/env bash
# claude_oauth_keepalive.sh — keeps Max OAuth token alive
# Cron: add via: crontab -e
#   */90 * * * * /home/john/Thunderbird/hooks/claude_oauth_keepalive.sh
LOG="/home/john/Thunderbird/logs/oauth_keepalive.log"
mkdir -p /home/john/Thunderbird/logs
# Local token freshness check — reads ~/.claude/.credentials.json directly without LLM inference
python3 -c '
import json, os, time, datetime
cred_path = os.path.expanduser("~/.claude/.credentials.json")
log_path = "/home/john/Thunderbird/logs/oauth_keepalive.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)
now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

if not os.path.exists(cred_path):
    with open(log_path, "a") as f:
        f.write(f"[{now_ts}] keepalive WARN: credentials file missing\n")
    exit(1)

try:
    with open(cred_path) as f:
        data = json.load(f)
    oauth = data.get("claudeAiOauth", {})
    exp_ms = oauth.get("expiresAt", 0)
    ref_exp_ms = oauth.get("refreshTokenExpiresAt", 0)
    now_ms = time.time() * 1000
    
    exp_hours = (exp_ms - now_ms) / (1000 * 3600)
    ref_days = (ref_exp_ms - now_ms) / (1000 * 86400)
    
    if exp_hours > 0 or ref_days > 0:
        msg = f"[{now_ts}] keepalive OK (OAuth token valid, expires in {exp_hours:.1f}h, refresh in {ref_days:.1f}d)\n"
    else:
        msg = f"[{now_ts}] keepalive WARN: OAuth token expired\n"
    
    with open(log_path, "a") as f:
        f.write(msg)
except Exception as e:
    with open(log_path, "a") as f:
        f.write(f"[{now_ts}] keepalive WARN: check failed: {e}\n")
    exit(1)
'

