# Revised Client Lifecycle Architecture
## Event-Driven Anchor Model with Staff Input Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DREAMS2MEMORIES CLIENT LIFECYCLE                        │
│                  Event-Driven Anchor Architecture                          │
└─────────────────────────────────────────────────────────────────────────────┘

                   ┌─────────────────────────────────────┐
                   │           STAFF INPUT FLOW          │
                   │  A2 → A6 → A9 → A3 → CLIENT         │
                   └─────────────────────────────────────┘
                            │
                            ▼

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  NODE 1         │  NODE 2         │  NODE 3         │  NODE 4         │
│ UNPREDICTABLE   │ HARD ANCHORS    │ FLUID TASKS     │ STAFF REVIEW    │
│ TRIGGERS        │ (IMMOVABLE)     │ (CLIENT-DRIVEN) │ GATE            │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│                 │                 │                 │                 │
│ • Initial       │ • Embarkation   │ • Flights       │ • WF-17 Quality │
│   Contact       │   Date          │   Booking       │   Check         │
│ • Deposit Date  │ • Disembarkation│ • Pre/Post      │ • Commander     │
│ • Dream Session │   Date          │   Hotels        │   Approval      │
│                 │ • Final Payment │ • Transfers     │ • Send Gate     │
│                 │   Date (FPD)    │ • Insurance     │                 │
│                 │ • Excursion     │ • Independent   │                 │
│                 │   Windows       │   Bookings      │                 │
│                 │ • Dining Opens  │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘

                          STAFF ASSIGNMENTS:
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│     A2        │  │     A6        │  │     A9        │  │     A3        │
│   DEMBE       │  │    LUNA       │  │     VIC       │  │    DANI      │
│ Research &    │  │ Creative      │  │ Finance &     │  │ Client-      │
│ Market Intel  │  │ Director      │  │ Process       │  │ Facing       │
│               │  │               │  │ Improvement   │  │ Concierge    │
├───────────────┤  ├───────────────┤  ├───────────────┤  ├───────────────┤
│ • Destination │  │ • Narrative   │  │ • Commission  │  │ • Aggregate   │
│   Research    │  │   Copy        │  │   Audit       │  │   Input       │
│ • Cruise Intel│  │ • Emotional   │  │ • Cost        │  │ • Craft       │
│ • Competitor  │  │   Storytelling│  │   Analysis    │  │   Voice       │
│   Analysis    │  │ • Visual      │  │ • ROI         │  │ • Present     │
│ • OSINT       │  │   Identity    │  │ • Budget      │  │   to Client   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                   │                   │                   │
        └───────────────────┼───────────────────┼───────────────────┘
                            │                   │
                            ▼                   ▼

                 ┌─────────────────────────────────────┐
                 │           A3 WORKFLOW               │
                 │  Aggregate → Artist → Advocate       │
                 └─────────────────────────────────────┘
                            │
                            ▼

                 ┌─────────────────────────────────────┐
                 │         CLIENT DELIVERABLE          │
                 │  (Email, Proposal, Itinerary, etc.) │
                 └─────────────────────────────────────┘
                            │
                            ▼

                 ┌─────────────────────────────────────┐
                 │           COMMANDER GATE           │
                 │  WF-17 Review → Send Approval       │
                 └─────────────────────────────────────┘


KEY VISUAL ELEMENTS FOR HTML CHARTS:
● Solid circles   = Hard anchors (immovable dates)
● Dashed circles  = Fluid tasks (client discretion)  
● Color coding    = Paid (green), Window (gold), Embark (navy), Disembark (blue)
● Staff icons     = A2/A6/A9/A3 persona indicators
● Flow arrows     = Data movement between staff
● Today marker    = Red vertical line on timeline

INTEGRATION WITH EXISTING:
- Uses thunderbird_anchor_dates.py T-minus calculations
- Maintains current HTML structure but replaces timeline with nodes
- Adds staff workflow visualization
- Preserves color coding and badge system from current Furlow HTML
```

## Implementation Priority:

1. **Phase_Standardization.md** - Rewrite with node-based architecture
2. **Staff Workflow Diagram** - Visual A2→A6→A9→A3 flow
3. **HTML Charts** - Convert from timeline to anchor nodes + staff integration
4. **Integration** - Wire to anchor date engine for T-minus calculations

The revised architecture addresses Commander's core requirements:
- ✅ "ALWAYS get staff input first" - built into workflow
- ✅ "Extremely flexible but also firm" - anchor nodes + fluid tasks
- ✅ Clear separation of predictable vs client-discretion items
- ✅ Visual representation of data flow through wing staff