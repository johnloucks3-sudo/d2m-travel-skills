# Excursion Planner Migration Guide

**Date:** 2026-06-27  
**Target:** Migrate all existing planners to unified template  
**Scope:** Silver Nova (done), then Kuklinski, Furlow/Ely/Nichols, McLeod

---

## Quick Start: For Each Voyage

### Step 1: Prepare voyageData

Create a JSON file with all port/excursion info for the voyage:

```javascript
const voyageData = {
  id: "kuklinski-viking-dec-2026",  // unique ID
  name: "Viking Mars — Panama Canal",
  shipName: "Viking Mars",
  departure: "2026-12-17",
  arrival: "2026-12-31",
  ports: [
    {
      id: "port-1",
      name: "Miami",
      country: "USA",
      code: "MIA",
      flag: "🇺🇸",
      arrTime: "Dec 17, 6:00 PM",
      depTime: "Dec 18, 6:00 PM",
      excursions: [
        {
          id: "kuklinski-exc-1-1",
          name: "Art Deco Walking Tour",
          provider: "GetYourGuide",
          duration: "3h",
          price: 45,
          url: "https://www.getyourguide.com/..."
        },
        {
          id: "kuklinski-exc-1-2",
          name: "Wynwood Street Art Tour",
          provider: "Viator",
          duration: "2h",
          price: 50,
          url: "https://www.viator.com/..."
        },
        // ... more excursions
      ]
    },
    {
      id: "port-2",
      name: "Cartagena",
      country: "Colombia",
      code: "CTG",
      flag: "🇨🇴",
      arrTime: "Dec 20, 7:00 AM",
      depTime: "Dec 21, 6:00 PM",
      excursions: [
        // ... excursions
      ]
    },
    // ... more ports
  ]
};
```

**Data sources:**
- Ship itinerary → port names, times, days
- GetYourGuide / Viator / SeaExplorer → excursion names, prices, durations
- D2M dossier → excursion preselections (if any)

### Step 2: Create planner HTML file

```html
<!DOCTYPE html>
<html>
<head>
  <title>Kuklinski — Viking Mars Dec 2026 | Excursion Planner</title>
  <script src="../storage/excursion_planner_unified.html"></script>
</head>
<body>
  <!-- Unified planner loads here -->
  <script>
    // Bootstrap voyageData
    const voyageData = { /* ... from Step 1 ... */ };
    sessionStorage.setItem('voyageData', JSON.stringify(voyageData));
    
    // Load unified planner frame
    document.body.innerHTML = 
      '<iframe src="../storage/excursion_planner_unified.html" style="width:100%;height:100vh;border:none"></iframe>';
  </script>
</body>
</html>
```

**Simpler approach:** Just open unified planner directly and pass voyageData via sessionStorage from itinerary.

### Step 3: Wire to itinerary

In itinerary HTML, add sync listener:

```javascript
// Listen for planner sync
window.addEventListener('storage', (e) => {
  if (e.key === 'itineraryData' && e.newValue) {
    const itinerary = JSON.parse(e.newValue);
    const excursions = itinerary.excursions[getCurrentVoyageId()];
    if (excursions) {
      updateExcursionLayer(excursions);  // Your function
    }
  }
});

// Load existing excursion selections (if any)
function loadExcursionSelections() {
  const itinerary = JSON.parse(localStorage.getItem('itineraryData') || '{}');
  const voyageId = getCurrentVoyageId();
  return itinerary.excursions?.[voyageId] || {};
}
```

### Step 4: Test

1. Open itinerary page
2. Click "Open Excursion Planner" → opens `/storage/excursion_planner_unified.html`
3. Make selections (e.g., select excursions for 3 ports)
4. Click "📤 Sync to Itinerary"
5. Switch back to itinerary tab
6. Verify excursion selections appear in itinerary
7. Edit planner again → changes should appear in itinerary immediately

---

## Implementation Timeline

### Silver Nova (May 2027) — DONE ✅
- Unified planner: `/storage/excursion_planner_unified.html`
- Old planners archived
- Itinerary syncs active

### Kuklinski (Viking Mars Dec 2026) — NEXT
**ETA:** 2026-06-30  
**Files:**
- Planner: `/cruises_web/excursions_kuklinski_viking.html` (or embed in itinerary)
- Sync protocol: Unified (no new code)
- Budget: $2,500 (Panama Canal + Caribbean)

**Data sources:**
- Viking Mars itinerary (12 days)
- GetYourGuide Panama Canal excursions
- Viator Caribbean port excursions
- Client preferences from dossier

### Furlow / Ely-Darrow / Nichols (Aug 29) — NEXT
**ETA:** 2026-07-05  
**Complexity:** GROUP voyage (one ship, three couple views)  
**Files:**
- Shared planner: `/cruises_web/excursions_grandeur_aug29.html`
- Sync saves to `itineraryData.excursions.grandeur-aug-2026`
- Itinerary renders separate sections per couple

**Group sync behavior:**
- All three couples see same excursion pool
- Each couple's selections isolated (e.g., Furlow[port-1] ≠ Nichols[port-1])
- Budget per couple separate

### McLeod (Multi-voyage) — NEXT
**ETA:** 2026-07-15  
**Complexity:** Vertical (3 voyages × 2 people = 6 planner instances)  
**Files:**
- Planner 1: Grandeur Dec 2026 (19 days)
- Planner 2: Princess Discovery Mar 2027 (14 days)
- Planner 3: Regent Prestige Dec 2027 (21 days)
- Sync protocol: One `itineraryData.excursions` per voyage ID

---

## File Organization

### Old structure (problematic)

```
/cruises_web/excursions_nova.html              ← different instances
/intel_web/silver-nova-excursions.html        ← orphaned
/storage/tp_templates/tp_2_1_excursion_planning.html ← unused template
```

### New structure (consolidated)

```
/storage/excursion_planner_unified.html        ← single template, all voyages
/cruises_web/excursions_kuklinski_viking.html ← wrapper for Kuklinski (optional, calls unified)
/cruises_web/excursions_grandeur_aug29.html   ← wrapper for Furlow/Ely/Nichols (optional)
/cruises_web/excursions_mcleod_grandeur.html  ← wrapper for McLeod Grandeur (optional)

OLD → ARCHIVE
/archive/excursions_nova_original_20260623.html
/archive/silver-nova-excursions_original_20260623.html
/archive/tp_2_1_excursion_planning_original.html
```

---

## Testing Checklist

For each new planner:

- [ ] Planner loads with correct voyage name & ports
- [ ] Excursion list populated per port
- [ ] Budget meter updates when selections change
- [ ] Selections persist on page reload (localStorage works)
- [ ] Click "📤 Sync to Itinerary" → itinerary updates
- [ ] Edit planner again → changes sync automatically (500ms delay)
- [ ] Itinerary can read selections from localStorage
- [ ] Clear all → itinerary shows cleared state
- [ ] Two browsers open: change in one → other sees update (cross-tab sync via storage events)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Planner doesn't load voyageData | Ensure `sessionStorage.setItem('voyageData', ...)` runs BEFORE opening planner |
| Sync button does nothing | Check browser console for errors; verify `itineraryData` key exists |
| Old planner still being used | Update all bookmarks/links to point to `/storage/excursion_planner_unified.html` |
| Selections clear unexpectedly | Check for competing localStorage keys; use unique voyageId per trip |
| Multi-user edits conflict | Not supported in v1; add last-writer-wins timestamp logic for v2 |

---

## Reference Docs

- **Sync protocol:** `/docs/EXCURSION_PLANNER_SYNC_PROTOCOL.md`
- **Unified planner code:** `/storage/excursion_planner_unified.html`
- **Itinerary vision:** `/docs/ITINERARY_PLATFORM_VISION_20260626.md`
- **Mission:** MISSION-802 (Grandeur Aug 29 research)

---

**Archive old planners after migration completes.**

