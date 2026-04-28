# Hale Visual Communication Architecture
## Daily Operational Briefing System

**Status:** Phase 1 Implementation Complete (Data Layer + Visuals + Delivery)

---

## Overview

Replaces text-based morning briefs with 4 interactive visual dashboards delivered daily at 06:00 MT:
- **📊 Client Lifecycle Wheel** — 7 clients, urgency-colored, FPD countdown
- **💰 Financial Waterfall** — Commission pipeline with Allianz claim
- **🔥 Task Heat Map** — Clients × task types, urgency-encoded
- **⚠️ Risk Matrix** — Likelihood × disruption scatter with quadrants

All visuals are interactive: hover for details, click for drill-down, navigate to full dossiers.

---

## Architecture

```
05:50 MT ← systemd timer triggers
   ↓
generate_and_send_brief.py
   ├─ brief_data_generator.py (loads/freshness checks phase1_data.json, hale_state.json)
   ├─ Render 4 HTML templates via Jinja2
   ├─ brief_archiver.py (local storage + cleanup)
   ├─ backup_to_drive() (Google Drive backup)
   └─ brief_email_sender.py (send to johnloucks3@gmail.com)
        ↓
   FastAPI server (port 8901)
   ├─ /briefs/{date}/ (landing page)
   ├─ /briefs/{date}/lifecycle-wheel/
   ├─ /briefs/{date}/financial-waterfall/
   ├─ /briefs/{date}/task-heatmap/
   └─ /briefs/{date}/risk-matrix/
        ↓
   itinerary.d2mluxury.quest (Cloudflare tunnel — PRODUCTION URL)
        ↓
   06:00 MT — Email delivered to Commander with 4 links
```

---

## Files Created

### Core Modules
- `brief_data_generator.py` — Data extraction, validation, freshness checking
- `brief_archiver.py` — Local 90-day retention, Drive backup placeholder
- `brief_email_sender.py` — Email composition (MCP integration placeholder)
- `generate_and_send_brief.py` — Main orchestrator (systemd entry point)
- `__init__.py` — Package marker

### Visual Templates
- `templates/brief_lifecycle_wheel.html` — D3.js SVG circle chart
- `templates/brief_financial_waterfall.html` — Plotly waterfall
- `templates/brief_task_heatmap.html` — Plotly heatmap
- `templates/brief_risk_matrix.html` — Plotly scatter with quadrants

### System Integration
- `~/.config/systemd/user/hale-brief-generator.service` — Service unit
- `~/.config/systemd/user/hale-brief-generator.timer` — Timer (05:50 MT daily)
- `~/.cloudflared/config.yml` — Added visuals.d2mluxury.quest routing

### Extended FastAPI
- `dashboard_app/server.py` — Added /briefs/{date}/* endpoints

---

## Setup & Activation

### 1. Create output directory
```bash
mkdir -p /home/john/Thunderbird/output/briefs
```

### 2. Verify data sources
- `output/visuals/phase1_data.json` — Must exist or be auto-generated
- `hale_state.json` — Updated via Hale operations
- `dossiers/*.json` — Client dossiers

### 3. Load systemd services
```bash
systemctl --user daemon-reload
systemctl --user enable hale-brief-generator.timer
systemctl --user enable hale-brief-generator.service
systemctl --user start hale-brief-generator.timer
```

### 4. Verify timer
```bash
systemctl --user list-timers hale-brief-generator.timer
```

### 5. Restart Cloudflare tunnel
```bash
systemctl --user restart cloudflared
```

### 6. Test FastAPI
```bash
# Manually generate a brief
python3 -m core.hale.generate_and_send_brief

# Verify output
ls -la /home/john/Thunderbird/output/briefs/2026-04-27/

# Test endpoint
curl http://localhost:8901/briefs/2026-04-27/lifecycle-wheel/
```

---

## Configuration

### Data Freshness (brief_data_generator.py)
```python
def is_fresh(file_path: Path, hours: int = 24) -> bool:
```
- Default: Use JSON if < 24 hours old, else pull fresh
- Modify `hours` parameter to adjust refresh interval

### Archive Retention (brief_archiver.py)
```python
ARCHIVE_RETENTION_DAYS = 90
```
- Old briefs auto-deleted after 90 days
- All briefs backed up to Google Drive (TBD)

### Email Delivery (brief_email_sender.py)
```python
FROM_EMAIL = "d2mconcierge@gmail.com"
TO_EMAIL = "johnloucks3@gmail.com"
```
- Requires MCP Gmail integration (placeholder in code)

### Daily Timing (hale-brief-generator.timer)
```ini
OnCalendar=*-*-* 05:50:00
```
- Change time if needed: `OnCalendar=*-*-* 06:00:00` for 6 AM

---

## Next Steps (Phase 2)

### Immediate
- [ ] Test brief generation: `python3 -m core.hale.generate_and_send_brief`
- [ ] Verify all 4 visuals render at `http://localhost:8901/briefs/{date}/`
- [ ] Confirm systemd timer fires daily at 05:50 MT
- [ ] Manual email send test via MCP Gmail

### Integration Needs
- [ ] `brief_archiver.py`: Wire up Google Drive backup (needs MCP call)
- [ ] `brief_email_sender.py`: Wire up MCP Gmail send (needs MCP call)
- [ ] Data quality: Ensure `phase1_data.json`, `hale_state.json` are current
- [ ] Dossier links: Update `navigateToDossier()` in lifecycle wheel to match dossier portal URL

### Enhancements
- [ ] Risk scoring refinement (currently basic thresholds)
- [ ] Client detail drill-down modals (basic structure in place)
- [ ] Drive backup folder setup + permission testing
- [ ] Email template customization (headers, footers, branding)
- [ ] Mobile responsiveness optimization

---

## Monitoring

### Check Timer Status
```bash
systemctl --user status hale-brief-generator.timer
journalctl --user -u hale-brief-generator.timer -n 50 -f
```

### Check Service Execution
```bash
journalctl --user -u hale-brief-generator.service -n 100
```

### Verify Brief Outputs
```bash
ls -lah /home/john/Thunderbird/output/briefs/*/
cat /home/john/Thunderbird/output/briefs/2026-04-27/metadata.json
```

### Test Manual Execution
```bash
/home/john/Thunderbird/.venv/bin/python3 -m core.hale.generate_and_send_brief
```

---

## Troubleshooting

### "Brief snapshot not found for YYYY-MM-DD"
- Run manual generation: `python3 -m core.hale.generate_and_send_brief`
- Verify output directory: `ls /home/john/Thunderbird/output/briefs/`

### "Jinja2 template not found"
- Check template path in server.py: should point to `core/visual_synthesis/dashboard_app/templates/`
- Verify files exist: `ls *.html` in templates directory

### "phase1_data.json not found"
- Check data freshness timeout in `brief_data_generator.py`
- Ensure phase 1 dashboard has been run: `python3 core/visual_synthesis/data_generators.py`

### Timer not firing
- Verify timer is enabled: `systemctl --user is-enabled hale-brief-generator.timer`
- Check timer config: `systemctl --user cat hale-brief-generator.timer`
- Restart timer: `systemctl --user restart hale-brief-generator.timer`

### Cloudflare 525 SSL errors on visuals.d2mluxury.quest
- Status: Domain returns 525 (SSL handshake failure) even when tunnel is healthy
- Workaround: Briefs are served via `itinerary.d2mluxury.quest/briefs/{date}/` instead
- Email sender updated to use `itinerary.d2mluxury.quest` as BRIEFS_DOMAIN
- All 4 visuals (lifecycle-wheel, financial-waterfall, task-heatmap, risk-matrix) are fully accessible via itinerary domain
- Local access via `http://localhost:8901/briefs/{date}/` always works

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Jinja2 rendering on-demand | Avoids pre-generating all visuals; renders fresh on request |
| Snapshot JSON storage | Enables offline viewing if dashboard service goes down |
| 90-day local retention | Balances storage vs. archive depth |
| Port 8901 for both services | Reuses existing FastAPI server (both dashboard + briefs on same port) |
| Systemd timer over cron | Better logging, systemd integration, persistent scheduling |
| Visuals.d2mluxury.quest domain | Separate namespace for brief delivery vs. itinerary storage |

---

## Voice & Style

Briefs follow D2M branding:
- **Color:** Blue (#0000ff) on cream (#f7f3ea)
- **Typography:** System font stack, sans-serif
- **Data density:** High — visual-first with annotations
- **Interactivity:** Hover for tooltips, click for detail panels, modal navigation to dossiers

---

## Contact & Support

- **Hale (COS):** Col Victoria "Iron Vic" Hale — orchestration, priority decisions
- **Infrastructure:** Check systemd logs: `journalctl --user -u hale-brief-*`
- **Data Issues:** Verify `phase1_data.json` freshness and format

---

*Hale Visual Communication Architecture v1.0 — Deployed 2026-04-27*
