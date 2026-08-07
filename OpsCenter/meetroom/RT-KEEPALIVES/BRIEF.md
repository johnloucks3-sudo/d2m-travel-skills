# RT-KEEPALIVES — War Room review of ALL keep-alive / refresh timers
**Opened:** 2026-08-07 · **Seats:** AG (first) → CC → OC · **Status:** IN SESSION
**Commander goal (2026-08-07):** slim down + consolidate/combine all keep-alive timers; adopt existing software; straight-Linux adaptation; software search & integration. STOP the 30-min attention garbage.

## Inventory (ground truth, both layers)
### systemd user timers/services (active)
| Unit | Interval | Purpose |
|---|---|---|
| claude-oauth-keepalive | 30 min | Claude MAX OAuth refresh |
| d2mconcierge-oauth-keepalive | ~30-90m | d2mconcierge Gmail OAuth refresh |
| johnloucks3-oauth-keepalive | ~30-90m | johnloucks3 Gmail OAuth refresh |
| tess-token-keepalive | 90 min | TESS token refresh |
| keepalive-supervisor | ? | meta-watchdog over all wing keepalives |
| d2m-centrav-warm | 75 min | Centrav burnout keeper (now DISABLED per Commander) |
| d2m-perx-trigger-detector / perx-intel | | Perx rate triggers |
| d2m-portal-live-probe | | portal session live-probe, auto-heal, pages Commander on fail |
| thunderbird-tess-sync | | TESS→dossier sync |

### supertimer tasks (supertimer_infra_bot_state.json)
- claude-oauth · d2mconcierge-oauth · johnloucks3-oauth · tess-token · portal-keepalive · keepalive-supervisor · **centrav-warm (DISABLED now)** · bsk-session-keepalive

### Observed redundancy
- claude-oauth / 2× gmail oauth / tess-token / keepalive-supervisor / bsk logically run in BOTH systemd AND supertimer → duplicate refreshes, duplicate page-risk.

## The failure being divorced
- Centrav-warm: "NOT AUTHENTICATED → attempting headless relogin → browser won't open (persistent profile locked)" every cycle → attention spam. DISABLED (supertimer task enabled:false + systemd units disabled); still to confirm no linger.

## Each seat — deliver a keepalive SLIM PLAN
1. Rank all keepalives: KEEP / MERGE / KILL, with rationale (which are load-bearing vs which just page the Commander with churn).
2. Consolidation: which sets fold into `keepalive-supervisor` (single gatekeeper, merge a idempotent runner) vs which must stay independent (OAuth safety).
3. Straight-Linux adaptation: replace any browser/Playwright-based keepalive (`centrav_warm` auto-relogin, `tess-` etc.) needing a GUI/session with plain HTTPS/token refresh where possible.
4. Existing software / software-search: reuse stdlib `systemd timers` semantics or a single Python scheduler instead of piling many units.
5. Integration gaps: where a merge needs a new small script vs re-launch.
Write RT-KEEPALIVES/{seat}_input.txt. Terse; flag UNVERIFIED. Hidden: do NOT sink tokens re-investigating known state.
## ADDED (Commander) — NEW SOFTWARE SEARCH
Each seat ALSO runs a short NEW-software search (2026) for a single tool/pattern that replaces the keepalive pile — e.g.:
- one OAuth token-refresh daemon/agent covering multiple services,
- a single session/supervisor daemon vs N systemd units,
- straight-Linux-native (no Playwright/browser) session keepers.
Name 2-3 candidates with fit; say ADOPT (replace pile) / PARTIAL (fill one gap) / SKIP.
