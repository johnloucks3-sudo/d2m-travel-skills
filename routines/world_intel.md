# Routine: /world-intel
## Travel Intelligence — Destination Watch

Check travel intelligence for current and upcoming client destinations:

1. **Travel advisories** (US State Dept / UK FCDO) — any level changes for active client destinations
2. **Weather events** — hurricanes, storms, heat waves affecting cruise ports or resorts
3. **Strikes / disruptions** — airport strikes, rail strikes, port labor actions
4. **Entry requirements** — visa changes, passport validity rules, health requirements
5. **Local events** — festivals, holidays, major events affecting travel

If I provide a client list with destinations, check each one. Otherwise, give a global overview of notable changes.

Output: one section per client trip, formatted as:
```
**CLIENT NAME** — Destination, Dates
🟢 Advisory: Level X
⚠️ Weather: [alert if any]
ℹ️ Entry: [changes]
```
