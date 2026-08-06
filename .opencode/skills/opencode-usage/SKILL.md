# Opencode GO Usage Capture

Capture OpenCode usage from the opencode.ai workspace Usage page and report it
by day with a running total.

## Trigger
"opencode usage", "opencode go usage", "capture usage", "usage report", "this month's usage", "how much did opencode cost"

## What it does
Reads the Usage page (`https://opencode.ai/workspace/<WORKSPACE>/usage`) via bsk
(browser-skill CLI), aggregates the request log by day, and prints a per-day
table with a running total. Also captures the per-model and per-session split.

## Steps
1. **Open the usage page** (Commander usually has it open — find the tab):
   ```bash
   S=$(bsk session start 2>/dev/null | tail -1)
   bsk navigate "https://opencode.ai/workspace/<WORKSPACE_ID>/usage" --session "$S"
   sleep 8
   ```
   Find the workspace id from the open browser tab, or `bsk tab list --session $S --scope user`
   and grep for `opencode`.

2. **Read the rendered table rows** — aggregate by day / model / session:
   ```bash
   bsk evaluate "$(cat /tmp/agg_usage.js)" --session "$S" --json
   ```
   The aggregator JS (`/tmp/agg_usage.js`, below) walks `table tr` cells
   (DATE MODEL INPUT OUTPUT COST SESSION) and sums per day.

3. **For the full month (beyond the latest ~50 rows):** the page's data comes from
   `/_server` (the opencode.ai RPC proxy). Capture it by hooking `window.fetch`
   and triggering a filter change, or navigate to the Usage page with the
   network hook armed in a parent window. The rendered table typically caps at
   the latest 50 requests — be transparent that only that slice is readable
   from the DOM.

## Aggregator JS (per-day running total)
```js
(()=>{var rows=Array.from(document.querySelectorAll('table tr')).slice(1);
var byDay={};var reD=/(Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul)\s+(\d{1,2})/;
var reC=/\$([0-9.]+)/;
rows.forEach(function(tr){var c=Array.from(tr.querySelectorAll('td')).map(function(x){return (x.textContent||'').replace(/\s+/g,' ').trim()});
if(c.length<6)return;
var d=c[0].match(reD);var day=d?d[0]:c[0];
var i=parseInt((c[2]||'0').replace(/[^0-9]/g,'')),o=parseInt((c[3]||'0').replace(/[^0-9]/g,''));
var m=c[4].match(reC),cc=m?parseFloat(m[1]):0;
if(!byDay[day])byDay[day]={req:0,in:0,out:0,cost:0};
byDay[day].req++;byDay[day].in+=i;byDay[day].out+=o;byDay[day].cost+=cc;});
var out=[];Object.keys(byDay).forEach(function(d){out.push({day:d,req:byDay[d].req,in:byDay[d].in,out:byDay[d].out,cost:+byDay[d].cost.toFixed(4)});});
out.sort(function(a,b){return a.day<b.day?-1:1});
var run=0;out.forEach(function(r){run+=r.cost;r.running_total=+run.toFixed(4);});
return JSON.stringify(out);})()
```

## Output format (report to Commander)
| Day | Requests | Input tok | Output tok | Cost | Running total |
|-----|----------|-----------|------------|------|---------------|
| Aug 6, 2026 | 50 | 25,022,976 | 18,694 | $0.0769 | $0.0769 |

Plus model + session split lines.

## Notes / constraints
- The Usage SPA is React; row text is in per-char spans — use `textContent`
  + whitespace normalize, not `innerText`.
- The DOM shows only the latest ~50 requests. Full-month by-day totals need
  the `/_server` API capture (SPA-fragile) or the page's canvas chart (not
  text-readable). Report the DOM slice honestly.
- Cleanup: `bsk session stop "$S"` when done.
- Commander doctrine: if the capture is partial, say so — never pad the number.