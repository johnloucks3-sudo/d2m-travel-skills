# Excursion Planner Archive — Consolidation 2026-06-27

**Status:** ARCHIVED — Superseded by unified planner  
**Reason:** Consolidate orphaned instances, enable bidirectional itinerary sync

---

## Archived Files

### 1. `/cruises_web/excursions_nova.html` (v0.x)
- **Date:** Jun 26, 2026 (last modified 17:12)
- **Status:** Superseded
- **Reason:** Replaced by `/storage/excursion_planner_unified.html`
- **Migration:** Silver Nova selections auto-migrated via localStorage sync on 2026-06-27
- **Archive:** Keep until 2026-07-15 for reference

### 2. `/intel_web/silver-nova-excursions.html` (v0.x old)
- **Date:** Jun 23, 2026 (last modified 16:27)
- **Status:** ORPHANED (no localStorage sync)
- **Reason:** Stateless version; data loss risk
- **Migration:** NONE (this was not in active use)
- **Action:** Safe to delete immediately

### 3. `/storage/tp_templates/tp_2_1_excursion_planning.html` (template)
- **Date:** Template file
- **Status:** Deprecated (replaced by unified)
- **Reason:** TP 2.1 excursion planning now uses unified planner
- **Keep:** As reference if needed for historical docs

### 4. `/storage/tp_templates/arc2_excursion_arc.html` (template)
- **Date:** Template file
- **Status:** Deprecated
- **Reason:** ARC 2 planner now uses unified template
- **Keep:** As reference

---

## Why Consolidation?

### Problem Statement

Before 2026-06-27:
1. **Multiple instances per voyage** — `/cruises_web/` + `/intel_web/` had different localStorage keys
2. **No itinerary sync** — clearing planner didn't update itinerary and vice versa
3. **Orphaned files** — old templates left behind as new planners were created
4. **Data integrity risk** — unclear which planner was authoritative

### Solution

**Single unified planner** with:
- ✅ Bidirectional localStorage sync to itinerary
- ✅ One template for all voyages (Kuklinski, Furlow, McLeod, Loucks, etc.)
- ✅ Auto-debounced syncs (500ms)
- ✅ Explicit "Sync to Itinerary" button for manual control
- ✅ Clear status indicator (✓ Synced, ⟳ Pending)
- ✅ Two-way sync (planner→itinerary AND itinerary→planner)

---

## Migration Status

| Voyage | Planner Status | Itinerary Sync | Owner | ETA |
|--------|---|---|---|---|
| **Silver Nova (May 2027)** | ✅ Unified | ✅ Active | Loucks | 2026-06-27 (DONE) |
| **Kuklinski (Dec 2026)** | 📋 Planned | ⏳ Ready | Kyle | 2026-06-30 |
| **Furlow/Ely/Nichols (Aug 29)** | 📋 Planned | ⏳ Ready | Dani | 2026-07-05 |
| **McLeod (Multi-voyage)** | 📋 Planned | ⏳ Ready | Hale | 2026-07-15 |

---

## Cleanup Timeline

- **2026-06-27:** Consolidation announced, unified planner deployed
- **2026-06-30:** Kuklinski planner deployed (unified)
- **2026-07-01:** Furlow/Ely/Nichols planners deployed (unified)
- **2026-07-15:** McLeod planners deployed (unified)
- **2026-07-31:** Archive old files physically (safe after all voyages migrated)

---

## If Needed

To recover an archived planner:
1. Check git history: `git log -- <path>`
2. Restore via: `git checkout <commit> -- <path>`
3. Manual import: Extract from backup, import selections into itineraryData

---

## New Reference

- **Unified planner:** `/storage/excursion_planner_unified.html`
- **Sync protocol:** `/docs/EXCURSION_PLANNER_SYNC_PROTOCOL.md`
- **Migration guide:** `/docs/EXCURSION_PLANNER_MIGRATION_GUIDE.md`
- **Platform vision:** `/docs/ITINERARY_PLATFORM_VISION_20260626.md`

---

**Archived by:** Hale COS  
**Date:** 2026-06-27  
**Reason:** Consolidation to unified template + bidirectional sync protocol

