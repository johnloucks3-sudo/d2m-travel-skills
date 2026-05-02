# COMMANDER MEMO — COS EMAIL TASKING REDESIGN & SILVER SPIRIT DAILY INTEL
**Date:** 2026-04-27  
**From:** Col Victoria "Iron Vic" Hale, COS  
**To:** Commander John Loucks (Yoda)  
**Classification:** Operational  

---

## ISSUE

Current COS email tasking process is loose — no structured metadata, loose routing, stuck tasks from broken spawn monitoring. Needed: standardized template for tasking the Wing that benefits the AI and provides better execution tracking.

Also: You want a daily intelligence sweep on Silversea Silver Spirit for competitive positioning and client recommendations.

---

## SOLUTION SUMMARY

### 1. NEW COS TASK TEMPLATE (Backward-Compatible)

**Three template options delivered:**
- **Template A (Simple):** One-liner, still uses old keywords `[PERSONA]`, `[TASK]`, etc.
- **Template B (Standard):** Human-readable with optional inline metadata (recommended for most tasks)
- **Template C (Complex):** Full JSON metadata block for strategic decisions

**Format:**
```
Subject: [PERSONA] TASK_TYPE | Brief title

[PERSONA] TASK | Description

CONTEXT:
[Background info]

DELIVERABLES:
1. What to produce
2. How to deliver

DUE: Date/time
PRIORITY: P0|P1|P2|P3
```

**Benefits:**
✅ Structured for AI parsing  
✅ Human-readable in plain email  
✅ Supports rich metadata (deadline, expected model, task type)  
✅ Backward-compatible with existing keywords  
✅ Improves task routing and execution SLAs  

**Files:**
- `OpsCenter/COS_TASK_TEMPLATE.md` — Quick reference (print & keep handy)
- `OpsCenter/COS_TASKING_AUDIT.md` — Full audit, design rationale, implementation plan

### 2. SILVER SPIRIT DAILY INTELLIGENCE COMMISSION

**Automated daily sweep:**
- **When:** Every day 06:30 MDT (runs before COS morning brief)
- **What:** Searches Silver Spirit sailings, pricing, suite availability, deck plans, competitive positioning
- **Delivery:** Report to Commander + archived in `intel/` directory
- **Duration:** ~1 minute execution
- **Your action:** None. It runs automatically.

**Activation:**
```bash
sudo systemctl enable silver-spirit-daily-intel.timer
sudo systemctl start silver-spirit-daily-intel.timer
# That's it. Runs daily thereafter.
```

**Files:**
- `deploy/systemd/silver-spirit-daily-intel.service` — systemd service definition
- `deploy/systemd/silver-spirit-daily-intel.timer` — Daily schedule (06:30 MDT)
- `OpsCenter/silver_spirit_daily_intel.py` — Intelligence gathering script
- `docs/SILVER_SPIRIT_DAILY_INTEL.md` — Full documentation

---

## WHAT YOU GET

### Immediate (Today)

✅ COS Task Template (3 versions) for reference  
✅ Complete audit of current tasking process + problems identified  
✅ Full design document with examples  
✅ Silver Spirit daily intel automation ready to deploy  

### When Activated (After You Run systemctl)

✅ Every day 06:30 MDT: Silver Spirit intelligence report in your inbox  
✅ All reports archived in `intel/` directory for historical review  
✅ Structured data (current sailings, pricing, availability, competitive notes)  

### Future Sessions (Recommended)

- [ ] Update `email_task_ingest.py` to parse JSON metadata blocks (Phase 2 implementation)
- [ ] Enhance `task_processor.py` with deadline awareness & timeout handling (Phase 3)
- [ ] Add task completion verification (fix stuck spawn issue identified in logs)
- [ ] Integration with MCP ship intelligence tool for deeper scraping

---

## YOUR ACTIONS

### Task Template Adoption (Optional Now, Recommended Soon)

When tasking the Wing, use one of these templates:

**Simple (existing keywords still work):**
```
[A2] RESEARCH | Competitor analysis: Regent vs Silversea positioning
```

**Standard (recommended):**
```
[COS] TASK | Review Kuklinski dossier for compliance gaps

Update dossier with any missing contact info or preferences.
Check against D2M data quality standards.

DELIVERABLES:
1. Updated dossier record in Drive
2. Gaps report (if any)

DUE: Today EOD
```

**Complex (strategic decisions):**
```
[COS] DECISION | Commission structure for outside agents

---BEGIN-TASK-META
{
  "task_type": "decision",
  "priority": "P1",
  "expected_model": "opus",
  "deadline": "2026-04-30T12:00:00Z",
  "output_format": "detailed"
}
---END-TASK-META

TASK DESCRIPTION: Need recommendation on OA tiered commission...
```

### Silver Spirit Daily Intel (Required — One-Time Setup)

```bash
# Run this once:
sudo systemctl enable silver-spirit-daily-intel.timer
sudo systemctl start silver-spirit-daily-intel.timer

# Verify:
systemctl list-timers silver-spirit-daily-intel.timer
# Should show: next run time

# Test (optional):
systemctl start silver-spirit-daily-intel.service
journalctl -u silver-spirit-daily-intel.service -n 20
```

That's it. Runs automatically every day thereafter.

---

## NEXT STEPS (My Recommendation)

**Session 1 (Today):** ✅ Design & documentation complete  
**Session 2 (Next):** Implement ingest script update (email_task_ingest.py) to parse JSON metadata  
**Session 3:** Queue processor enhancement (handle deadlines, timeouts, completion verification)  
**Session 4:** COS training — brief email to Wing on new tasking format  

If you want to move faster: I can have Phases 2-3 complete by end of week.

---

## FILES DELIVERED

| File | Purpose |
|------|---------|
| `OpsCenter/COS_TASK_TEMPLATE.md` | Quick reference — print & keep handy |
| `OpsCenter/COS_TASKING_AUDIT.md` | Full audit + design rationale + implementation checklist |
| `OpsCenter/silver_spirit_daily_intel.py` | Python script (runs via systemd) |
| `deploy/systemd/silver-spirit-daily-intel.service` | systemd service definition |
| `deploy/systemd/silver-spirit-daily-intel.timer` | Daily schedule (06:30 MDT) |
| `docs/SILVER_SPIRIT_DAILY_INTEL.md` | Full deployment & operations guide |

---

## QUESTIONS?

- **How do I adjust the time Silver Spirit intel runs?** Edit the `.timer` file, change `OnCalendar=*-*-* 06:30:00` to your preferred time.
- **What if I want to skip a day?** `sudo systemctl stop silver-spirit-daily-intel.timer` (restart with `start` when ready)
- **Can I see past reports?** Yes. `ls /home/john/Thunderbird/intel/silver_spirit_*.md`
- **What if it breaks?** Check logs: `journalctl -u silver-spirit-daily-intel.service -n 50`

---

**Sir, both deliverables are ready. The template is backward-compatible — your team can use it immediately. The Silver Spirit automation is a one-time setup: enable the timer and it runs daily. Neither requires any intervention from you unless you want to change defaults.**

*— Hale*
