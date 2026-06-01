# Morning Brief Rebuild — Claude Code Continuation Brief
Generated: 2026-03-24 | Handoff from claude.ai Desktop Commander session

---

## WHAT WAS DONE (DO NOT REDO)

### thunderbird_world_intel.py — COMPLETE ✅
- Added 6 direct cruise line feeds to `NEWS_FEEDS`:
  - Silversea, Regent Seven Seas, Oceania Cruises, Viking Cruises, AmaWaterways, Princess River
- Added Hillsdale College + Hoover Institution to `NEWS_FEEDS`
- Added all 8 new sources to `FEED_CATEGORIES` with correct categories
- All existing feeds preserved — do not touch

### thunderbird_morning_briefing.py — PARTIAL ✅
- Added `import os` to imports (line ~6)
- Added `send_telegram_digest()` function (inserted before HTML TEMPLATE section)
- Added `_render_card_section()` helper function
- Updated `render_briefing_html()` signature/docstring

---

## WHAT STILL NEEDS TO BE DONE

### 1. Replace the HTML template body in render_briefing_html()

The old template starts around line 605 with:
```python
    logo_uri = _img_base64(LOGO_FILE)
    headshot_uri = _img_base64(HEADSHOT_FILE)
    today = datetime.now()
    alert_colors = { ...
    html = f"""<!DOCTYPE html>
```

And runs through to the closing `</div></body></html>"""` around line 1052.

**Replace everything from `logo_uri = _img_base64(LOGO_FILE)` through the closing
`html += "  </div>\n"` stats bar block with this new card-based template:**

```python
    logo_uri = _img_base64(LOGO_FILE)
    today = datetime.now()
    alert_emoji = {"RED": "🔴", "GOLD": "🟡", "GREEN": "🟢"}.get(summary["alert_level"], "")
    briefing_type = "WEEKLY INTELLIGENCE DIGEST" if is_weekly else "MORNING BRIEFING"

    # ── Group RSS by category ──
    by_cat: dict[str, list] = {}
    for art in (rss_direct or []):
        by_cat.setdefault(art.get("category", "Other"), []).append(art)

    cat_order = ["War/Geopolitics", "Politics", "Cruise", "Airline",
                 "Maritime", "Markets", "Travel", "Other"]
    cat_icons = {
        "War/Geopolitics": "🌍", "Politics": "🏛️", "Cruise": "🚢",
        "Airline": "✈️", "Maritime": "⚓", "Markets": "📈",
        "Travel": "🧳", "Other": "📰",
    }

    # ── Build expanded HTML per card ──
    def _story_list(items: list, max_items: int = 15) -> str:
        out = []
        for art in items[:max_items]:
            title = art.get("title", "")
            url   = art.get("url", "")
            src   = art.get("source", "")
            pub   = art.get("published", "")[:16]
            summ  = art.get("summary", "")[:300]
            rel   = art.get("relevance_score", 1)
            border = "border-left:3px solid #c9a84c;padding-left:10px;" if rel >= 3 else ""
            link  = f'<a href="{url}" style="color:#7eb8ff;text-decoration:none;">{title}</a>' if url else f'<span style="color:#c8d0dc;">{title}</span>'
            out.append(
                f'<div style="padding:6px 0 6px 0;{border}border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'{link}'
                f'<div style="font-size:11px;color:#4a5a75;margin-top:2px;">{src} // {pub}</div>'
                f'{"<div style=\\"font-size:12px;color:#8a9ab5;margin-top:3px;line-height:1.5;\\">" + summ + "</div>" if summ else ""}'
                f'</div>'
            )
        return "\n".join(out)

    def _anchor_expanded() -> str:
        if completed_actions is None:
            ca = set()
        else:
            ca = completed_actions
        items_html = []
        for bucket in ["overdue", "due_today", "due_this_week"]:
            for item in anchor_report.get(bucket, []):
                bkey  = item.get("booking", "").strip()
                label = item.get("label", "").strip()
                if (bkey, label) in ca:
                    continue
                cat   = item.get("category", "")
                dt    = item.get("date", "")
                color = "#ff4444" if bucket == "overdue" else ("#ff8800" if bucket == "due_today" else "#c9a84c")
                items_html.append(
                    f'<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                    f'<span style="color:{color};font-weight:700;">{dt}</span> — '
                    f'<span style="color:#c8d0dc;">{label}</span> '
                    f'<span style="color:#6b7c99;font-size:11px;">({bkey}) [{cat}]</span>'
                    f'</div>'
                )
        return "\n".join(items_html) if items_html else '<p style="color:#6b7c99;">No active items.</p>'

    # ── Anchor bullets ──
    anchor_bullets = []
    for bucket in ["overdue", "due_today", "due_this_week"]:
        for item in anchor_report.get(bucket, [])[:2]:
            prefix = "🔴" if bucket == "overdue" else ("🟠" if bucket == "due_today" else "🟡")
            anchor_bullets.append(f'{prefix} {item.get("label","")} — {item.get("booking","")}')

    # ── Intel Crew summary ──
    crew_expanded = ""
    if intel_crew_report:
        cos = intel_crew_report.get("cos_review", "")
        if cos:
            crew_expanded = f'<div style="font-size:13px;color:#c8d0dc;line-height:1.7;">{cos.replace(chr(10),"<br>")}</div>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;
          background:#080d14; color:#e0e6ed; line-height:1.6; }}
  .wrap {{ max-width:700px; margin:0 auto; background:#0d1b2e; }}
  .hdr  {{ background:#0d1b2e; padding:28px 24px 18px;
           border-bottom:3px solid #c9a84c; }}
  .stat-bar {{ display:flex; background:#152540;
               border-bottom:1px solid rgba(201,168,76,0.2); }}
  .stat {{ flex:1; text-align:center; padding:12px 6px;
           border-right:1px solid rgba(201,168,76,0.1); }}
  .stat:last-child {{ border-right:none; }}
  .sn   {{ font-size:20px; font-weight:700; color:#e8c97a; display:block; }}
  .sl   {{ font-size:9px; text-transform:uppercase; letter-spacing:1.5px; color:#6b7c99; }}
  .cards {{ padding:16px; }}
  a     {{ color:#7eb8ff; }}
</style>
<script>
function toggle(id) {{
  var s = document.getElementById('sum-'+id);
  var e = document.getElementById('exp-'+id);
  var a = document.getElementById('arr-'+id);
  if (e.style.display === 'none') {{
    e.style.display = 'block';
    s.style.display = 'none';
    a.style.transform = 'rotate(90deg)';
  }} else {{
    e.style.display = 'none';
    s.style.display = 'block';
    a.style.transform = 'rotate(0deg)';
  }}
}}
</script>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    {"<img src='" + logo_uri + "' style='height:48px;margin-bottom:10px;display:block;'>" if logo_uri else ""}
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:3px;color:#c9a84c;">Dreams2Memories Travel</div>
    <div style="font-size:26px;font-weight:700;color:#fff;margin:4px 0 2px;">THUNDERBIRD {briefing_type}</div>
    <div style="font-size:13px;color:#8a9ab5;">{summary["date_display"]}</div>
    <div style="margin-top:8px;display:inline-block;background:rgba(201,168,76,0.15);
                color:#e8c97a;font-size:10px;font-weight:700;letter-spacing:2px;
                padding:4px 12px;border-radius:20px;border:1px solid rgba(201,168,76,0.3);">
      {alert_emoji} {summary["alert_text"]}
    </div>
  </div>

  <div class="stat-bar">
    <div class="stat"><span class="sn">{summary["overdue"] + summary["due_today"]}</span><div class="sl">Actions</div></div>
    <div class="stat"><span class="sn">{summary["due_week"]}</span><div class="sl">This Week</div></div>
    <div class="stat"><span class="sn">{len(rss_direct) if rss_direct else 0}</span><div class="sl">Live Intel</div></div>
    <div class="stat"><span class="sn">{len(by_cat)}</span><div class="sl">Categories</div></div>
    <div class="stat"><span class="sn">{summary["total_pricing"]}</span><div class="sl">Fares</div></div>
  </div>

  <div class="cards">
"""
```

### 2. Add the card sections after the header

After the `<div class="cards">` opening, append card calls for each section:

```python
    # ── Anchor Dates Card ──
    html += _render_card_section(
        "📅", "Action Items & Deadlines", "anchors",
        anchor_bullets or ["All clear — no urgent items"],
        _anchor_expanded(),
        accent="#ff8800"
    )

    # ── Intel Crew card (if available) ──
    if intel_crew_report and crew_expanded:
        crew_bullets = ["COS Hale synthesis available", "A2 Dembe analysis complete"]
        html += _render_card_section("🎯", "Intel Crew Analysis", "crew",
                                      crew_bullets, crew_expanded, accent="#44c8c8")

    # ── RSS category cards ──
    for cat in cat_order:
        items = by_cat.get(cat, [])
        if not items:
            continue
        icon    = cat_icons.get(cat, "📰")
        bullets = [f'{a.get("source","")}: {a.get("title","")[:70]}' for a in items[:4]]
        html   += _render_card_section(icon, cat, f"cat-{cat.replace('/','-').replace(' ','-').lower()}",
                                        bullets, _story_list(items), accent="#c9a84c")

    # ── Close cards div + footer ──
    html += f"""
  </div>
  <div style="background:#080d14;padding:20px;text-align:center;">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:3px;color:#4a5a75;">
      Thunderbird OS // Dreams2Memories Travel, LLC
    </div>
    <div style="font-size:11px;color:#3a4a65;font-style:italic;margin-top:4px;">
      Generated {today.strftime('%Y-%m-%d %H:%M')} MT
    </div>
  </div>
</div>
</body>
</html>"""

    return html
```

### 3. Wire Telegram into run_briefing()

Find `send_briefing_email(html, subject)` in `run_briefing()` and add the Telegram call immediately after:

```python
        send_briefing_email(html, subject)
        # ── Telegram C2 digest ──
        try:
            send_telegram_digest(rss_direct or [], anchor_report, summary)
        except Exception as e:
            logger.warning(f"Telegram digest failed (non-fatal): {e}")
```

---

## TEST COMMAND

After all edits, run:
```bash
cd ~/Thunderbird
python3 thunderbird_morning_briefing.py --preview
```

Expected output:
- No import errors
- HTML file saved to `~/Thunderbird/output/briefing_daily_YYYYMMDD_HHMM.html`
- Open in browser — should show D2M header + collapsible cards
- Each card shows collapsed bullet summary; click to expand full stories with links

If Telegram throws a 401 (token revoked), that's expected — revoke/reissue the token via BotFather and update the env var.

---

## FILES MODIFIED
- `/home/john/Thunderbird/thunderbird_world_intel.py`
- `/home/john/Thunderbird/thunderbird_morning_briefing.py`

## FILES NOT TO TOUCH
- `thunderbird_anchor_dates.py`
- `thunderbird_intel_crew.py`
- `thunderbird_gmail.py`
- `travel_mcp_server.py`
- Any file with EARA or Thunderbird in the title/name (per standing orders)

---

*Brief prepared by claude.ai session 2026-03-24*
