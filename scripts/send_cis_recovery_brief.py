#!/usr/bin/env python3
"""Send CIS Recovery Brief to Commander at johnloucks3@gmail.com
via d2mconcierge Gmail (Wing internal intel send — no WF-17 gate).
"""
import sys
import base64
import importlib.util
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load thunderbird_google_auth without inserting core/email into sys.path
# (which would shadow stdlib email module)
spec = importlib.util.spec_from_file_location(
    'thunderbird_google_auth',
    '/home/john/Thunderbird/api/thunderbird_google_auth.py'
)
auth_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_mod)

svc = auth_mod.get_persona_gmail()

HTML_BODY = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body { background-color: #f7f3ea; font-family: Georgia, serif; color: #222; margin: 0; padding: 0; }
  .wrapper { max-width: 780px; margin: 0 auto; background: #f7f3ea; padding: 32px 36px; }
  h1 { color: #003087; font-size: 22px; margin-bottom: 4px; border-bottom: 2px solid #0000ff; padding-bottom: 8px; }
  .subtitle { color: #0000ff; font-size: 13px; margin-top: 4px; margin-bottom: 24px; font-style: italic; }
  h2 { color: #003087; font-size: 16px; margin-top: 28px; margin-bottom: 8px; border-left: 4px solid #0000ff; padding-left: 10px; }
  h3 { color: #003087; font-size: 14px; margin-top: 18px; margin-bottom: 6px; }
  p { line-height: 1.6; margin: 6px 0 12px 0; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0 18px 0; font-size: 13px; }
  th { background-color: #003087; color: #f7f3ea; padding: 7px 10px; text-align: left; }
  td { padding: 6px 10px; border-bottom: 1px solid #d8d0c0; vertical-align: top; }
  tr:nth-child(even) td { background-color: #ede9e0; }
  code { background: #e8e4db; padding: 2px 5px; font-family: monospace; font-size: 12px; border-radius: 3px; }
  pre { background: #e8e4db; padding: 12px; font-size: 12px; overflow-x: auto; border-left: 3px solid #0000ff; margin: 10px 0; }
  .status-ok { color: #2a7a2a; font-weight: bold; }
  .status-warn { color: #cc6600; font-weight: bold; }
  .status-red { color: #cc0000; font-weight: bold; }
  .action-box { background: #fffbe8; border: 1px solid #0000ff; border-radius: 5px; padding: 12px 16px; margin: 12px 0; }
  .sig { margin-top: 32px; border-top: 1px solid #003087; padding-top: 16px; font-size: 13px; color: #555; }
  .timestamp { font-size: 11px; color: #888; margin-top: 6px; }
</style>
</head>
<body>
<div class="wrapper">

  <h1>&#x1F985; CIS RECOVERY BRIEF &mdash; 2026-06-12</h1>
  <div class="subtitle">8-Hour DNS Outage AAR &middot; Spencer Supplier Catalog &middot; Connectivity Plan &middot; Internet Recommendations</div>

  <p><strong>Date:</strong> 2026-06-12 &nbsp;|&nbsp; <strong>Prepared by:</strong> Hale (COS) &nbsp;|&nbsp; <strong>Distribution:</strong> Commander</p>

  <h2>INCIDENT SUMMARY</h2>
  <p><strong>Event:</strong> DNS resolution failure &mdash; 8 hours (approximately 00:35&ndash;08:00 MDT 2026-06-12)<br>
  <strong>Root cause:</strong> Upstream DNS outage at ISP level. <code>oauth2.googleapis.com</code> unreachable.<br>
  <strong>Cascade effect:</strong> 10 systemd keepalive/OAuth services failed simultaneously at ~00:35 MDT. All services depend on DNS to reach external auth endpoints.</p>

  <h2>SECTION 1 &mdash; CIS INFRASTRUCTURE RECOVERY STATUS</h2>
  <table>
    <tr><th>System</th><th>Status</th><th>Last Verified</th><th>Notes</th></tr>
    <tr><td>Centrav B2B (laravel_session)</td><td class="status-ok">&#x2705; LIVE</td><td>08:07 MDT</td><td>Warm-ping confirmed authenticated. Self-healed stale auth_error flag.</td></tr>
    <tr><td>TESS Token</td><td class="status-ok">&#x2705; LIVE</td><td>08:00 MDT</td><td>Keepalive ran twice after DNS recovery.</td></tr>
    <tr><td>d2mconcierge OAuth</td><td class="status-ok">&#x2705; LIVE</td><td>08:00 MDT</td><td>Failed at 07:22 (DNS still recovering), succeeded at 08:00.</td></tr>
    <tr><td>johnloucks3 OAuth</td><td class="status-ok">&#x2705; LIVE</td><td>08:04 MDT</td><td>Recovery chain complete.</td></tr>
    <tr><td>Claude OAuth</td><td class="status-ok">&#x2705; LIVE</td><td>Auto</td><td>Token refreshed on session start.</td></tr>
    <tr><td>Silversea session</td><td class="status-ok">&#x2705; HEALTHY</td><td>File status</td><td><code>status: HEALTHY</code> in session file.</td></tr>
    <tr><td>ITA Matrix</td><td class="status-ok">&#x2705; REACHABLE</td><td>08:35 MDT</td><td>HTTP 200 from yoga.</td></tr>
    <tr><td>d2mluxury.quest (tunnel)</td><td class="status-ok">&#x2705; RESTORED</td><td>08:33 MDT</td><td>Cloudflared restarted; tunnel active on new config. Subdomains serving.</td></tr>
    <tr><td>Regent OA portal (rssc.com)</td><td class="status-warn">&#x26A0;&#xFE0F; DEGRADED</td><td>08:11 MDT</td><td>Portal-keepalive ran but ASPXAUTH cookie NOT refreshed (silent login fail). Old cookies preserved. <code>creds/regent_cookies_oa.json</code> has 1 ASPXAUTH cookie (may still be valid).</td></tr>
    <tr><td>Continuity-recert service</td><td class="status-warn">&#x26A0;&#xFE0F; RED</td><td>08:32 MDT</td><td>Exits RED: 50 missed heartbeat pings (direct result of 8-hour outage). Self-heals as 24h window advances. Non-blocking.</td></tr>
    <tr><td>d2mluxury.quest root domain</td><td class="status-red">&#x1F534; 525 ERROR</td><td>Current</td><td>Blocked on CloudFlare dashboard access. SSL mode &ldquo;Full (Strict)&rdquo; + self-signed cert = 525. Commander action required (see below).</td></tr>
  </table>

  <div class="action-box">
    <strong>Commander action required (60 sec):</strong><br>
    <code>dash.cloudflare.com &rarr; d2mluxury.quest &rarr; SSL/TLS &rarr; Overview &rarr; change Full (Strict) &rarr; Full</code><br>
    <em>OR:</em> Delete A record for d2mluxury.quest &rarr; Hale runs <code>cloudflared tunnel route dns thunderbird d2mluxury.quest</code>
  </div>

  <h2>SECTION 2 &mdash; SPENCER FAMILY ADVENTURE: SUPPLIER CONNECTIVITY</h2>

  <h3>Flight Partners</h3>
  <table>
    <tr><th>Supplier</th><th>URL</th><th>HTTP Status</th><th>Notes</th></tr>
    <tr><td>United Airlines</td><td><a href="https://united.com" style="color:#0000ff;">united.com</a></td><td class="status-red">&#x274C; Bot-blocked</td><td>Use Playwright or browser. Booking window Aug 2026.</td></tr>
    <tr><td>SWISS International</td><td><a href="https://swiss.com" style="color:#0000ff;">swiss.com</a></td><td class="status-red">&#x274C; 403</td><td>Same. Use Playwright.</td></tr>
    <tr><td>Centrav B2B (flight booking)</td><td>centrav.com</td><td class="status-ok">&#x2705; 200 + auth</td><td>Primary flight search tool &mdash; LIVE</td></tr>
    <tr><td>ITA Matrix (fare research)</td><td>matrix.itasoftware.com</td><td class="status-ok">&#x2705; 200</td><td>Use Playwright for searches</td></tr>
  </table>

  <h3>Italy DMC Partners</h3>
  <table>
    <tr><th>Operator</th><th>URL</th><th>HTTP</th><th>Contact</th><th>Priority</th></tr>
    <tr><td>Carrani Tours (Rome/Vatican)</td><td><a href="https://booking.carrani.com" style="color:#0000ff;">booking.carrani.com</a></td><td class="status-ok">&#x2705; 200</td><td>segreteria@carrani.com &middot; +39 06 432181</td><td><strong>RFQ priority</strong></td></tr>
    <tr><td>Renata Travel Luxury DMC</td><td><a href="https://luxury.renatatraveldmc.com" style="color:#0000ff;">renatatraveldmc.com</a></td><td class="status-ok">&#x2705; 200</td><td>Contact form on site</td><td><strong>RFQ priority</strong></td></tr>
    <tr><td>Mama Florence (cooking class)</td><td><a href="https://mamaflorence.com" style="color:#0000ff;">mamaflorence.com</a></td><td class="status-ok">&#x2705; 302</td><td>+39 055 221138</td><td>Book by Jun 17</td></tr>
    <tr><td>Tuscan Lands Travel</td><td><a href="https://tuscanlandstravel.com" style="color:#0000ff;">tuscanlandstravel.com</a></td><td class="status-ok">&#x2705; 200</td><td>Contact form</td><td>Backup Italy op</td></tr>
    <tr><td>Sichef Florence (upgrade)</td><td>sichef-florence.cooking</td><td>Not tested</td><td>Contact form</td><td>Optional upgrade</td></tr>
  </table>

  <h3>Switzerland DMC Partners</h3>
  <table>
    <tr><th>Operator</th><th>URL</th><th>HTTP</th><th>Contact</th><th>Priority</th></tr>
    <tr><td>Artisans of Leisure</td><td><a href="https://artisansofleisure.com" style="color:#0000ff;">artisansofleisure.com</a></td><td class="status-ok">&#x2705; 200</td><td>Quote form</td><td><strong>Recommended single-op</strong></td></tr>
    <tr><td>Private Tours Switzerland</td><td><a href="https://privatetoursswitzerland.com" style="color:#0000ff;">privatetoursswitzerland.com</a></td><td class="status-ok">&#x2705; 200</td><td>Contact form</td><td>Backup/modular</td></tr>
    <tr><td>Zermatters.ch</td><td><a href="https://zermatters.ch" style="color:#0000ff;">zermatters.ch</a></td><td>Not tested</td><td>Booking form</td><td>Matterhorn guides</td></tr>
  </table>

  <h3>Hotel Booking Platforms</h3>
  <table>
    <tr><th>Platform</th><th>URL</th><th>HTTP</th><th>Status</th><th>Notes</th></tr>
    <tr><td>RoomRes</td><td><a href="https://roomres.com" style="color:#0000ff;">roomres.com</a></td><td class="status-ok">&#x2705; 301</td><td>Accessible</td><td>Session&rarr;API technique documented in memory. B2B rates.</td></tr>
    <tr><td>Bedsonline (Hotelbeds)</td><td><a href="https://bedsonline.com" style="color:#0000ff;">bedsonline.com</a></td><td class="status-ok">&#x2705; 301</td><td>Accessible</td><td>Requires B2B registration/credentials</td></tr>
    <tr><td>Tauck Tours</td><td><a href="https://tauck.com" style="color:#0000ff;">tauck.com</a></td><td class="status-ok">&#x2705; 200</td><td>Accessible</td><td>Competitor/reference &mdash; not a booking platform</td></tr>
    <tr><td>Insight Vacations</td><td><a href="https://insightvacations.com" style="color:#0000ff;">insightvacations.com</a></td><td class="status-ok">&#x2705; 301</td><td>Accessible</td><td>Same</td></tr>
  </table>

  <p><strong>Hotels NOT yet researched (gap):</strong> Rome (3-night), Florence (2-night), Interlaken (2-night), Zermatt (3-night), Zurich (1-night)</p>

  <h2>SECTION 3 &mdash; INTERNET CONNECTIVITY DISASTER RECOVERY PLAN</h2>

  <h3>Root Cause Analysis</h3>
  <p>Single ISP dependency + all external services depend on DNS resolution. When ISP DNS fails, entire Wing goes dark. No backup DNS configured, no secondary ISP.</p>

  <h3>Immediate Fixes (implement now, zero cost)</h3>
  <p>1. <strong>Add DNS fallback</strong> &mdash; edit <code>/etc/resolv.conf</code> or use <code>systemd-resolved</code> with fallback nameservers:</p>
  <pre>DNS=8.8.8.8 1.1.1.1
FallbackDNS=9.9.9.9 208.67.222.222</pre>
  <p>This alone would have prevented the cascade (ISP DNS failed &rarr; fall back to Google/CF DNS).</p>
  <p>2. <strong>Add health check with auto-failover in keepalive scripts</strong> &mdash; test DNS before external calls; if DNS fails, use IP-literal fallback for critical OAuth endpoints.</p>

  <h3>ISP Recommendations (Monument CO 80132)</h3>
  <table>
    <tr><th>Provider</th><th>Type</th><th>Speed</th><th>Price</th><th>Contract</th><th>ISP Risk</th></tr>
    <tr><td>Conexon Connect</td><td>Pure fiber (symmetrical)</td><td>2 Gbps &#x2195;</td><td>$99.95/mo</td><td>None</td><td>25% Monument coverage &mdash; verify address first</td></tr>
    <tr><td>Xfinity</td><td>Cable</td><td>Up to 2 Gbps &darr;</td><td>~$50/mo (1G res) &middot; quote for business</td><td>None/1yr</td><td>Broad coverage; asymmetric upload</td></tr>
    <tr style="background:#fffbe8;"><td><strong>T-Mobile Home Internet</strong></td><td><strong>5G Fixed Wireless</strong></td><td>~300&ndash;500 Mbps</td><td><strong>$40&ndash;70/mo</strong></td><td><strong>None</strong></td><td><strong>No contract, no hardware cost &mdash; ideal hot standby</strong></td></tr>
    <tr><td>Starlink</td><td>LEO Satellite</td><td>100&ndash;400 Mbps</td><td>$55&ndash;120/mo + $599 HW</td><td>None</td><td>100% available, 20&ndash;40ms latency</td></tr>
  </table>

  <h3>Recommendation &mdash; 3-tier resilience</h3>
  <p><strong>Tier 1 (primary):</strong> Conexon 2GB fiber &mdash; if it reaches the address, this is the obvious choice. Symmetrical upload matters for a server sending briefs, staging drafts, running cloudflared.</p>
  <p><strong>Tier 2 (hot standby):</strong> T-Mobile Home Internet &mdash; no contract, no hardware cost. Plug in, configure as failover gateway. Activates in 10 minutes during a Tier 1 outage.</p>
  <p><strong>Tier 3 (total blackout):</strong> Starlink &mdash; hardware investment but bulletproof. Worth it if the Wing is processing $100K+ in bookings.</p>
  <p><strong>Dual ISP failover:</strong> Configure yoga&rsquo;s router to use Conexon as WAN1 and T-Mobile as WAN2 with automatic failover via <code>ip route</code> metrics or pfSense/OPNsense. No manual intervention needed when primary goes down.</p>
  <p><strong>Estimated monthly cost for Tier 1+2:</strong> $99.95 (Conexon) + $40&ndash;50 (T-Mobile) = ~$140&ndash;150/mo. For a business generating $20K+ in pipeline commissions, this is the right spend.</p>

  <h2>SECTION 4 &mdash; REGENT PORTAL RECOVERY STEPS</h2>
  <p>The Regent OA portal (rssc.com) session silently failed during/after the outage. Old cookies preserved but may be stale.</p>

  <p><strong>Option A &mdash; Manual re-auth (Commander):</strong></p>
  <ol>
    <li>Navigate to rssc.com &rarr; log in</li>
    <li><code>python3 scripts/portal_login_capture.py</code> (or equivalent) captures fresh cookies</li>
    <li>Portal-keepalive will pick up and maintain from there</li>
  </ol>

  <p><strong>Option B &mdash; Test current session validity:</strong></p>
  <pre>ssh yoga "python3 -c \"
import json
from pathlib import Path
import requests
cookies = {c['name']: c['value'] for c in json.loads(Path('creds/regent_cookies_oa.json').read_text())}
r = requests.get('https://www.rssc.com/en/agents/', cookies=cookies, allow_redirects=False)
print('Status:', r.status_code, '(200=valid, 302=expired)')
\""</pre>

  <h2>OPEN ACTION ITEMS</h2>
  <table>
    <tr><th>#</th><th>Action</th><th>Owner</th><th>Priority</th><th>Deadline</th></tr>
    <tr><td>1</td><td>Fix d2mluxury.quest 525 (CF SSL mode change)</td><td><strong>Commander (60 sec)</strong></td><td class="status-red">P0</td><td>NOW</td></tr>
    <tr><td>2</td><td>Add DNS fallback to <code>/etc/systemd/resolved.conf</code></td><td>Hale</td><td class="status-red">P0</td><td>Today</td></tr>
    <tr><td>3</td><td>Verify Regent OA session validity</td><td>Commander/Hale</td><td class="status-warn">P1</td><td>Today</td></tr>
    <tr><td>4</td><td>Research Conexon address availability at yoga&rsquo;s address</td><td>Commander</td><td class="status-warn">P1</td><td>This week</td></tr>
    <tr><td>5</td><td>Purchase T-Mobile Home Internet as hot standby</td><td>Commander</td><td class="status-warn">P1</td><td>This week</td></tr>
    <tr><td>6</td><td>Submit RFQ to Carrani Tours</td><td>Hale/Commander</td><td>P2</td><td>Jun 17</td></tr>
    <tr><td>7</td><td>Submit RFQ to Renata Travel DMC</td><td>Hale/Commander</td><td>P2</td><td>Jun 17</td></tr>
    <tr><td>8</td><td>Book Mama Florence private cooking class (8 pax)</td><td>Hale</td><td>P2</td><td>Jun 17</td></tr>
    <tr><td>9</td><td>Book Switzerland operator (Artisans of Leisure preferred)</td><td>Hale</td><td>P2</td><td>Jun 17</td></tr>
    <tr><td>10</td><td>Research Rome/Florence/Switzerland hotels for 12 pax</td><td>Dembe (A2)</td><td>P2</td><td>Jun 17</td></tr>
    <tr><td>11</td><td>Set Aug 2026 reminder for live United/SWISS fare pull</td><td>Hale</td><td>P3</td><td>Backlog</td></tr>
  </table>

  <div class="sig">
    <strong>V. Hale, VCS</strong><br>
    Chief of Staff &mdash; Thunderbird Wing, Dreams2Memories Travel, LLC<br>
    <em>Internal Intel Brief &mdash; CIS Recovery AAR</em>
    <div class="timestamp">08:35 MT &middot; 2026-06-12</div>
  </div>

</div>
</body>
</html>"""

PLAIN_TEXT = """CIS RECOVERY BRIEF — 2026-06-12
8-Hour DNS Outage AAR · Spencer Supplier Catalog · Connectivity Plan · Internet Recommendations

See HTML version for full formatted report with tables.

Key items:
- All core systems LIVE and recovered as of 08:35 MDT
- d2mluxury.quest root domain still 525 — Commander action needed (60 sec in CloudFlare)
- Spencer supplier catalog: Italy DMCs (Carrani, Renata, Mama Florence) + Switzerland (Artisans of Leisure) all reachable
- DNS failover fix queued (Hale, P0, today)
- ISP recommendation: Conexon fiber (Tier 1) + T-Mobile Home Internet (Tier 2 hot standby) ~$140-150/mo

11 open action items in table above.

— V. Hale, VCS
08:35 MT · 2026-06-12
"""

TO = "johnloucks3@gmail.com"
SUBJECT = "🦅 CIS RECOVERY BRIEF — Outage AAR + Spencer Supplier Catalog + Connectivity Plan"

msg = MIMEMultipart("alternative")
msg["to"] = TO
msg["from"] = '"V. Hale, VCS — Thunderbird Wing" <d2mconcierge@gmail.com>'
msg["reply-to"] = "d2mconcierge@gmail.com"
msg["subject"] = SUBJECT

msg.attach(MIMEText(PLAIN_TEXT, "plain"))
msg.attach(MIMEText(HTML_BODY, "html"))

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
print(f"SENT — Message ID: {result.get('id')}")
print(f"  To: {TO}")
print(f"  Subject: {SUBJECT}")
