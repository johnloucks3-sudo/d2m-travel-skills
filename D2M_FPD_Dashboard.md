---
title: D2M — Final Payment Dashboard
---

# D2M Final Payment Dashboard
*Auto-refreshes from dossier frontmatter. Sorted by FPD date.*

## 🔴 Overdue / Due This Week

```dataview
TABLE full_name AS "Client", cruise_line AS "Line", voyage AS "Voyage", fpd AS "FPD", fpd_amount AS "Amount $"
FROM "dossiers"
WHERE fpd != null AND fpd <= date(today) + dur(7 days) AND status = "active"
SORT fpd ASC
```

## 🟡 Due in 30 Days

```dataview
TABLE full_name AS "Client", cruise_line AS "Line", voyage AS "Voyage", fpd AS "FPD", fpd_amount AS "Amount $"
FROM "dossiers"
WHERE fpd != null AND fpd > date(today) AND fpd <= date(today) + dur(30 days) AND status = "active"
SORT fpd ASC
```

## 📋 All Active Bookings

```dataview
TABLE full_name AS "Client", ship AS "Ship", departure AS "Departure", fpd AS "FPD", fpd_amount AS "FPD $"
FROM "dossiers"
WHERE status = "active"
SORT departure ASC
```

## 📅 Departure Calendar (Next 12 Months)

```dataview
TABLE full_name AS "Client", ship AS "Ship", cruise_line AS "Line", departure AS "Departure", return AS "Return"
FROM "dossiers"
WHERE departure != null AND departure >= date(today) AND status = "active"
SORT departure ASC
```
