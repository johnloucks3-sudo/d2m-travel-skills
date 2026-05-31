#!/usr/bin/env python3
"""Dispatch all 12 mission builds headless. Sonnet for client-facing, Haiku for ops/research."""
import sys, time
from pathlib import Path

# Use foolproof wrapper per SO 24 APR 2026
sys.path.insert(0, str(Path("/home/john/Thunderbird")))
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

HAIKU  = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
BASE   = Path("/home/john/Thunderbird")
OUT    = BASE / "output"
LOGS   = BASE / "logs"
OUT.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

MISSIONS = [
    # (id, model, output_file, prompt)
    (
        "054", SONNET, "mission054_mcleod_silvermuse_t27_validation.md",
        f"""You are Dani, D2M's client concierge. Read these files:
- {BASE}/dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md
- {BASE}/dossiers/McLeod_McGlasson_Multi.md
- {BASE}/dossiers/DOSSIER_SilverMuse_Mediterranean_Jun2026.md

Task: Produce a TP 0.5 Welcome & Booking Validation email for Erik & Melissa McLeod.
Voyage: Silversea Silver Muse, Mediterranean, departs Jun 18 2026.
Rules:
- D2M brand voice: warm, expert, luxury. NOT AI-sounding.
- Opening: "Dear Erik and Melissa,"
- Validate key booking facts from dossier (CONFIRMED claims only — no INFERRED/UNKNOWN in client email).
- Note FPD status and next payment due if present in dossier.
- Close: "Thanks, [Dani signature]"
- Format: plain text email body (no HTML)
- DO NOT include dollar amounts unless confirmed in dossier portal data.

WRITE the complete email draft to: {OUT}/mission054_mcleod_silvermuse_t27_validation.md
Include a one-line status header: ## STATUS: DRAFT — WF-17 PENDING
"""
    ),
    (
        "009", SONNET, "mission009_kuklinski_arc4a_dining.md",
        f"""You are Dani, D2M's client concierge. Read these files:
- {BASE}/dossiers/Kuklinski_Viking_Panama.md
- {BASE}/output/Drafts_for_Client_Lifecycle_Engagement.md

Task: Write ARC4-A Specialty Dining touchpoint email for Kyle Kuklinski.
Voyage: Viking Mars, Panama Canal, departs Dec 17 2026.
ARC4-A = specialty dining pre-booking window opening touchpoint.

Rules:
- D2M brand voice: warm, expert, concise.
- Opening: "Dear Kyle and Jen," (check dossier for partner name)
- Highlight Viking's specialty dining options (Nordic, Italian, Chef's Table, etc.)
- Include call to action: book early, limited availability.
- Reference their specific voyage.
- Close: "Thanks, [Dani signature]"
- Format: plain text email body

WRITE the complete email draft to: {OUT}/mission009_kuklinski_arc4a_dining.md
Include header: ## STATUS: DRAFT — WF-17 PENDING
"""
    ),
    (
        "024", HAIKU, "mission024_mcleod_fpd_status.md",
        f"""Read these dossier files:
- {BASE}/dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md
- {BASE}/dossiers/McLeod_McGlasson_Multi.md

Task: Produce a payment status memo for McLeod/McGlasson bookings.
Extract: booking refs, FPD dates, amounts paid, amounts outstanding, next due dates.
Format as a structured markdown table + action items.
Flag anything OVERDUE in red (use ⚠️ marker).

WRITE the payment status memo to: {OUT}/mission024_mcleod_fpd_status.md
"""
    ),
    (
        "075", HAIKU, "mission075_loucks_dossier_root_cause.md",
        f"""Read these dossier files:
- {BASE}/dossiers/Loucks_Personal_SilverNova_Japan.md (first 200 lines)
- {BASE}/dossiers/Loucks_Regent_Grandeur_3122006.md
- {BASE}/dossiers/DOSSIER_Regent_Loucks_Dec2026_UPDATED.md

Task: Pipeline integrity audit (per SO-PIPELINE-INTEGRITY-20260528).
Look for: conflicting data between files (dates, prices, cabin numbers, booking refs, passenger names).
Classify each field as CONFIRMED / INFERRED / UNKNOWN.
Identify root cause of any discrepancies.
Note which file is authoritative per SO priority order: portal > TESS > dossier.

WRITE the audit report to: {OUT}/mission075_loucks_dossier_root_cause.md
"""
    ),
    (
        "053", HAIKU, "mission053_mcleod_grandeur_review.md",
        f"""Read: {BASE}/dossiers/McLeod_McGlasson_Multi.md

Task: Booking review for McLeod/McGlasson Regent Grandeur (if present in dossier).
Extract: booking ref, cabin, departure date, passengers, payment status, outstanding items.
Note any discrepancies or missing data.
Produce a clean booking summary table.

WRITE the booking review to: {OUT}/mission053_mcleod_grandeur_review.md
"""
    ),
    (
        "026", HAIKU, "mission026_cabin_selection_monitor.md",
        f"""Read these dossier files (scan all):
- {BASE}/dossiers/Kuklinski_Viking_Panama.md
- {BASE}/dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md
- {BASE}/dossiers/Morton_Joshua_Erica_Viking_Panama.md
- {BASE}/dossiers/Nichols_Regent_3078056.md
- {BASE}/dossiers/Furlow_Regent_3071222.md

Task: Cabin selection monitor. For each client/booking:
- Is cabin assigned? (yes/no/unknown)
- Is cabin confirmed with cruise line?
- Any pending selection deadlines?
Produce a table: Client | Voyage | Cabin Status | Action Needed | Deadline

WRITE the monitor report to: {OUT}/mission026_cabin_selection_monitor.md
"""
    ),
    (
        "066", HAIKU, "mission066_web_lead_pipeline_test.md",
        f"""Task: Web lead pipeline status check for D2M.

Check these endpoints (use bash curl commands):
1. https://itinerary.d2mluxury.quest/ — is it live? HTTP status code?
2. https://api.d2mluxury.quest/ — is it live?
3. Check if {BASE}/core/web/ or {BASE}/output/ contains a lead capture form or landing page.

Also check: does a prospect dossier exist in {BASE}/dossiers/ with date 2026-05-28 or newer? (PROSPECT_Test_Lead*.md)

Report: what's live, what's broken, what the lead pipeline looks like end-to-end.

WRITE the pipeline test report to: {OUT}/mission066_web_lead_pipeline_test.md
"""
    ),
    (
        "067", HAIKU, "mission067_norway_perx_pricing.md",
        f"""Task: Norway/Scandinavia luxury cruise pricing research for late Jul / mid-Aug 2027.

Check these sources:
1. Read {BASE}/dossiers/Scandi_Group_Monthly_Brief.md for context on the group.
2. Search {BASE}/intel/ or {BASE}/output/ for any existing Norway 2027 fare data.
3. Check if {BASE}/scripts/ has a fare-watch or Perx scraper script.

Based on available data, produce a pricing landscape summary:
- Cruise lines active on Norway/Scandinavia routes Jul-Aug 2027
- Approximate price ranges per person (suite categories)
- Recommended lines for the D2M client profile (luxury, couples)
- Data gaps that require live scraping

WRITE the pricing report to: {OUT}/mission067_norway_perx_pricing.md
"""
    ),
    (
        "068", HAIKU, "mission068_norway_2027_scan.md",
        f"""Task: Norway/Scandinavia 2027 cruise scan — itinerary options table.

Read {BASE}/dossiers/Scandi_Group_Monthly_Brief.md for group context.
Search {BASE}/intel/ and {BASE}/output/ for any existing Scandinavia 2027 data.

Produce a table of cruise options:
| Line | Ship | Departs | Ends | Ports | Duration | Suite From | Notes |

Focus on: Silversea, Regent, Viking, Seabourn, Ponant.
Date window: Jul 15 – Sep 15 2027.
If no live data available, produce the best-knowledge framework table with [VERIFY] flags.

WRITE the scan table to: {OUT}/mission068_norway_2027_scan.md
"""
    ),
    (
        "069", HAIKU, "mission069_platform_reliability.md",
        f"""Task: Platform reliability audit for Perx, Odysseus, and CruiseComplete.

Check:
1. Search {BASE}/scripts/ and {BASE}/core/ for any Perx/Odysseus/CruiseComplete scraper or connector files.
2. Check {BASE}/logs/ for recent errors related to these platforms.
3. Read {BASE}/OpsCenter/opencode_memory.md for any recent platform failure notes (first 100 lines).

For each platform, report:
- Last known working status
- Any authentication issues
- Any scraping blocks or rate limits
- Recommended next action

WRITE the reliability audit to: {OUT}/mission069_platform_reliability.md
"""
    ),
    (
        "036", HAIKU, "mission036_cost_dashboard_v2.html",
        f"""Task: Build D2M AI Infrastructure Cost Dashboard v2 — tabbed HTML redesign.

First read any existing dashboard: search {BASE}/output/ for *cost*dashboard* or *infra*dashboard* files.
Also check {BASE}/core/ai_infra/ for cost data or router_cost.db schema.

Build a single HTML file with:
- Tab 1: Model Usage (Sonnet/Haiku/Opus — weekly/monthly costs)
- Tab 2: Tool Costs (OpenCode/Groq/DeepSeek/Gemini)
- Tab 3: Routing Rules (which tasks → which model)
- Tab 4: Budget Status (weekly burn vs limits)
- Style: cream background (#f7f3ea), navy headers (#1B2A4A), clean table layout
- Use vanilla JS tabs (no external dependencies)
- Populate with known/placeholder data where live data unavailable

WRITE the complete HTML dashboard to: {OUT}/mission036_cost_dashboard_v2.html
"""
    ),
    (
        "072b", HAIKU, "mission072_dead_link_audit.md",
        f"""Task: Dead link and portal login audit for D2M infrastructure.

Check these (use curl or read config files):
1. https://itinerary.d2mluxury.quest — live?
2. https://api.d2mluxury.quest — live?
3. https://code.d2mluxury.quest — live?
4. Check {BASE}/.env or {BASE}/OpsCenter/config.py for any portal URLs
5. Check {BASE}/core/ for any portal connector files with URLs

For each URL: Status (LIVE/DEAD/UNKNOWN), Last verified, Action needed.
For portals (TESS, Perx, Odysseus): check if auth tokens/cookies exist in known locations.

WRITE the audit report to: {OUT}/mission072_dead_link_audit.md
"""
    ),
]

results = []
print(f"Dispatching {len(MISSIONS)} headless jobs...\n")

for mission_id, model, outfile, prompt in MISSIONS:
    out_path  = OUT  / outfile
    model_tag = "SONNET" if model == SONNET else "HAIKU"

    # Use foolproof wrapper (background mode — each mission runs async)
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=str(out_path),
        model=model,
        task_name=f"mission{mission_id}",
        background=True
    )

    if result.get("status") in ["SPAWNED", "COMPLETED"]:
        pid = result.get("pid", "?")
        results.append((mission_id, model_tag, outfile, pid, out_path))
        print(f"  ✅ MISSION-{mission_id} [{model_tag}] PID={pid} → {outfile}")
    else:
        print(f"  ❌ MISSION-{mission_id} FAILED: {result.get('error', 'unknown error')}")

    time.sleep(0.3)

print(f"\nAll {len(MISSIONS)} dispatched via foolproof wrapper.")
print(f"Monitor logs: tail -f {LOGS}/claude_mission*.log")
print("\nPIDs for tracking:")
for mid, mtag, outf, pid, _ in results:
    print(f"  MISSION-{mid}: PID {pid}")
