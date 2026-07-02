# Excursion Planner Sync Protocol v1.0

**Status:** Active as of 2026-06-27  
**Architecture:** Unified planner + bidirectional itinerary sync via localStorage  
**Applies to:** All voyage excursion planners (Nova, Kuklinski, Furlow/Ely/Nichols, McLeod, Loucks)

---

## Problem Statement

Before consolidation (2026-06-27):
- Multiple excursion planner instances existed per voyage (e.g., `cruises_web/` + `intel_web/`)
- No sync with itinerary — clearing planner didn't affect itinerary and vice versa
- Orphaned planners with different localStorage keys
- No single source of truth

**This protocol eliminates orphaned instances and guarantees bidirectional sync.**

---

## Architecture

### Single Planner per Voyage

```
/storage/excursion_planner_unified.html
  ├─ Loads voyageData from sessionStorage
  ├─ Stores selections in localStorage under key: `excursion_planner_{voyageId}`
  ├─ Syncs selections to `itineraryData` in localStorage on change (debounced 500ms)
  └─ Listens for changes from itinerary and re-renders
```

### localStorage Keys

| Key | Purpose | Scope | Owner |
|-----|---------|-------|-------|
| `excursion_planner_{voyageId}` | Selections in planner UI | Per voyage | Excursion Planner |
| `itineraryData` | Full itinerary (master state) | Per client | Itinerary |
| `itineraryData.excursions.{voyageId}` | Excursion selections (copy from planner) | Per voyage | Sync write |

### Data Flow

```
User selects excursion in Planner
     ↓
Save to localStorage[`excursion_planner_{voyageId}`]
     ↓
Trigger auto-sync (500ms debounce)
     ↓
Read itineraryData from localStorage
     ↓
Update itineraryData.excursions[{voyageId}] = {selections}
     ↓
Save back to localStorage[`itineraryData`]
     ↓
Mark as "Synced" (✓ indicator)
     ↓
Itinerary listens for storage change event
     ↓
Itinerary re-renders with new excursion selections
```

---

## Implementation

### 1. Create Planner for New Voyage

**File:** `/storage/excursion_planner_unified.html` (single template for all voyages)

**Bootstrap voyageData into sessionStorage before opening planner:**

```javascript
// In your itinerary or booking page
const voyageData = {
  id: "nova-may-2027",  // Must be unique & match itinerary
  name: "Silver Nova — Mediterranean",
  shipName: "Silver Nova",
  departure: "2027-05-05",
  arrival: "2027-05-21",
  ports: [
    {
      id: "port-1",
      name: "Barcelona",
      country: "Spain",
      code: "BCN",
      flag: "🇪🇸",
      arrTime: "May 5, 8:00 AM",
      depTime: "May 6, 6:00 PM",
      excursions: [
        {
          id: "exc-1-1",
          name: "Sagrada Familia & Park Güell",
          provider: "GetYourGuide",
          duration: "5h",
          price: 95,
          url: "https://..."
        },
        // ... more excursions
      ]
    },
    // ... more ports
  ]
};

sessionStorage.setItem('voyageData', JSON.stringify(voyageData));
window.open('/storage/excursion_planner_unified.html', '_blank');
```

### 2. Itinerary Listens for Sync

**In your itinerary HTML/app:**

```javascript
// Listen for changes from planner
window.addEventListener('storage', (e) => {
  if (e.key === 'itineraryData' && e.newValue) {
    const itinerary = JSON.parse(e.newValue);
    // Update your itinerary UI with new excursion selections
    renderExcursionLayer(itinerary.excursions);
  }
});

// On page load, check if planner has pushed new data
function loadExcursionSelections() {
  const itinerary = JSON.parse(localStorage.getItem('itineraryData') || '{}');
  const voyageId = getCurrentVoyageId();
  if (itinerary.excursions && itinerary.excursions[voyageId]) {
    return itinerary.excursions[voyageId];
  }
  return {};
}
```

### 3. Planner Reads from Itinerary (Two-Way)

**If itinerary changes, planner auto-syncs in:**

```javascript
// Already in planner: listens for storage changes
window.addEventListener('storage', onStorageChange);

function onStorageChange(e) {
  if (e.key === 'itineraryData' && e.newValue) {
    syncFromItinerary();  // Planner reads back
    render();
  }
}
```

---

## URL Patterns (Recommended)

```
/storage/excursion_planner_unified.html
  ?voyageId=nova-may-2027           (optional, can load from sessionStorage)
  &budget=3000                       (optional, override max budget)
  &readOnly=false                    (optional, disable editing)
```

Example:
```html
<a href="/storage/excursion_planner_unified.html?voyageId=nova-may-2027&budget=2500" 
   target="_blank">Open Planner</a>
```

---

## Consolidation Status (2026-06-27)

### Active Planners

- ✅ `/storage/excursion_planner_unified.html` — **LIVE** (replaces all others)

### Archived Planners (Orphaned)

- ⚠️ `/cruises_web/excursions_nova.html` — **SUPERSEDED** (archive or delete)
- ⚠️ `/intel_web/silver-nova-excursions.html` — **ORPHANED** (archive or delete)
- ⚠️ `/storage/tp_templates/tp_2_1_excursion_planning.html` — **TEMPLATE** (keep for reference)

### Migration Path

For any existing planner in use:
1. Open planner in browser
2. Ensure all selections are complete
3. Click **"📤 Sync to Itinerary"** button
4. Open itinerary in new tab — should see selections
5. Close old planner tab
6. Bookmark only `/storage/excursion_planner_unified.html`

---

## Sync Indicators

### Planner UI Status Bar

| Icon | Status | Meaning |
|------|--------|---------|
| ✓ Synced | Green | Selections saved to itinerary |
| ⟳ Pending | Gold | Debouncing; will sync in 500ms |
| ❌ Error | Red | Sync failed (check browser console) |

### Sync Timing

- **Auto-sync debounce:** 500ms (prevents excessive writes)
- **Manual sync:** Click "📤 Sync to Itinerary" button
- **Two-way:** Itinerary can also push changes back to planner

---

## Configuration

Edit `/storage/excursion_planner_unified.html` line ~75:

```javascript
const CONFIG = {
  storageKeyPrefix: 'excursion_planner_',
  itineraryStorageKey: 'itineraryData',
  maxBudget: 3000,                  // ← Change per voyage
  syncDebounceMs: 500               // ← Sync delay
};
```

---

## Known Limitations & Future

- **Single browser/device:** localStorage is per-origin. Planner and itinerary must be on same domain.
- **Cross-tab sync:** Works via storage events (automatic when tabs on same domain).
- **Multi-user edit:** Not supported yet. Recommendation: add timestamp + last-writer-wins logic if needed.
- **Offline support:** Works fully offline; syncs when back online.

---

## Troubleshooting

### Selections don't sync to itinerary

1. Check browser console (F12 → Console) for errors
2. Ensure `itineraryData` exists in localStorage (not just planner key)
3. Verify `voyageId` matches between planner and itinerary
4. Click "📤 Sync to Itinerary" button manually
5. Hard refresh (Ctrl+Shift+R) to clear stale storage

### Planner doesn't load voyageData

1. Ensure `sessionStorage.setItem('voyageData', ...)` runs BEFORE opening planner
2. Check that voyageData has required fields: `id`, `ports`, `ports[].excursions`
3. Open planner in same browser tab/window (sessionStorage is per-window)

### Old planner still showing

1. Check which planner file is open: URL should be `/storage/excursion_planner_unified.html`
2. Clear browser cache (Ctrl+Shift+Delete)
3. Update bookmarks/links to use unified planner only

---

## Migration Timeline

- **2026-06-27:** Unified planner deployed, sync protocol active
- **2026-06-30:** Kuklinski Viking Mars planner launches (unified template)
- **2026-07-01:** Furlow/Ely/Nichols Aug 29 planners launch (unified)
- **2026-07-15:** McLeod multi-voyage planners (unified)
- **2026-08-01:** All old planners archived/deleted

---

## Reference

- **Unified planner:** `/storage/excursion_planner_unified.html`
- **Related:** `/docs/ITINERARY_PLATFORM_VISION_20260626.md`
- **Status:** [[project_itinerary_platform_vision.md]]

