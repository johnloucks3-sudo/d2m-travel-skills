# TESS Setup — Outside Agents CRM

**TESS** is the booking management CRM provided by Outside Agents (MAGOA). It tracks trips, bookings, clients, commissions, and documents. Thunderbird OS connects via OAuth 2.0 + PKCE and auto-refreshes tokens.

## Credentials needed

- **TESS Client ID** and **TESS Client Secret** — get these at:
  `https://portal.outsideagents.com/settings/api`
- An active Outside Agents agent account

## One-time auth flow

```bash
bash ~/Thunderbird/scripts/tess_authorize.sh
```

The script checks for credentials (env vars → `tess_config.json` → interactive prompt), opens a browser to `auth.outsideagents.com`, catches the callback on `localhost:8089`, exchanges the code for tokens, and runs a live connection test. Tokens are saved to `~/Thunderbird/tess_token.json` and auto-refresh with a 5-minute buffer.

To re-test at any time: `python3 ~/Thunderbird/thunderbird_tess.py --test`

## Features unlocked after auth

- **Bookings** — search, filter by client/status/date, pull booking details
- **Trips** — list and retrieve trip records
- **Clients** — full client roster, individual client lookup
- **Commissions** — summary totals and individual commission records
- **Documents** — upload PDFs, invoices, and itineraries to trip records
- **Client portal tasks** — check task/document completion status per client

## MCP tools (9 total)

`tess_list_trips` · `tess_get_trip` · `tess_get_booking` · `tess_search_bookings` · `tess_get_commissions` · `tess_list_clients` · `tess_get_client` · `tess_upload_document` · `tess_get_client_tasks` · `tess_test_connection`

## Token management

| File | Purpose |
|------|---------|
| `~/Thunderbird/tess_token.json` | Live access + refresh tokens |
| `~/Thunderbird/tess_config.json` | Client ID/Secret (alternative to env vars) |

To revoke: `python3 ~/Thunderbird/thunderbird_tess.py --revoke`
