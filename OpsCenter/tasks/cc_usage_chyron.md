## Task: Pull ALL usage data and show it in CC's bottom bar

### Step 1 — Extract Claude MAX usage
Browse to `https://claude.ai/settings/usage`. Read ALL visible metrics:

- session_pct (e.g., 7)
- session_resets_in (e.g., "1hr 48 min")
- all_models_weekly_pct (e.g., 77)
- all_models_resets (e.g., "Thu 9:00 PM")
- sonnet_weekly_pct (e.g., 88)
- sonnet_resets
- claude_design_pct (usually 0)
- monthly_spent_usd (e.g., 55.67)
- monthly_limit_usd (e.g., 100)
- monthly_pct (e.g., 56)
- month_resets (e.g., "Jun 1")
- auto_reload (true/false)

### Step 2 — Extract Poe activity
Browse to `https://poe.com/activity`. Read:
- points_balance (available points, e.g., 466,167)
- points_limit (monthly limit, e.g., 660,000)
- points_used_today/week/month
- subscription_type
- top bots by usage

### Step 3 — POST both reports
```bash
curl -sk -X POST https://192.168.1.198:443/api/report \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: ***REMOVED-SECRET***' \
  -d '{"session_pct":7,"all_models_weekly_pct":77,"sonnet_weekly_pct":88,"monthly_spent_usd":55.67,"monthly_limit_usd":100,"monthly_pct":56,"source":"cc_browse"}'

curl -sk -X POST https://192.168.1.198:443/api/poe-activity \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: ***REMOVED-SECRET***' \
  -d '{"points_balance":466167,"points_limit":660000,"points_used_month":193833,"source":"cc_browse"}'
```
(Use actual numbers, not the samples.)

### Step 4 — Set CC's bottom bar
Now set Claude Code's own status bar to show the chyron. Figure out the mechanism CC uses for persistent status display — check `~/.claude/settings.json`, `CLAUDE.md`, project config, or any `claude config` command. Set it to show:

```
Sonnet 88% | $56/$100 | Poe 466kpts | ZEN 0/hr
```

### Step 5 — Report back
Tell me:
- What numbers you extracted
- Whether both POSTs succeeded
- What mechanism you found for CC's bottom bar and how you set it
