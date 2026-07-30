# ADVERSARIAL PARITY AUDIT: TCD (AppSheet) vs. Slack App Home

## CAPABILITY PARITY TABLE

| CAPABILITY | COVERED | WHAT IS LOST | SEVERITY |
| :--- | :--- | :--- | :--- |
| **Cascade Delete (`status->Delete`)** | YES | None. Button + confirm modal maps well to `writeback.py:136`. | LOW |
| **Close without delete (`status->Closed`)** | YES | None. Action button maps cleanly to `writeback.py:158`. | LOW |
| **Stage transition (`stage` P-D-T-A-C)** | YES | None. `static_select` block maps to `writeback.py:249`. | LOW |
| **Create Task (`[CREATE_TASK_REQUESTED]`)** | YES | None. Dedicated button replaces the text marker (`writeback.py:410`). | LOW |
| **Append Comments (`comments` edit)** | **NO** | Slack App Home UI blocks *do not support threads*. Threads only exist on channel/DM messages. To replicate AppSheet's inline text editing (`writeback.py:323`), you must pop a Modal just to type a comment. | **FATAL** |
| **Natively Edit Any Field (Modify)** | PARTIAL | AppSheet's grid natively allows editing `title`, `priority`, etc. To replicate this, you must build and maintain a massive generic Slack Modal with inputs for every field in `item_model.py:14-30`. | HIGH |
| **Multi-tab Organization** | **NO** | `multi_tab.py:45-158` collects into 5 distinct tabs (CommanderReview, Missions, ELON 77, TechScans, Next7). Slack App Home is a single, unorganized vertical scroll feed. Spatial organization is completely destroyed. | **FATAL** |
| **Bulk Triage / Mass Operations** | **NO** | A spreadsheet allows drag-filling "Closed" across 20 rows in one second. Slack requires 20 discrete button clicks, triggering 20 individual API round-trips to update the UI. | HIGH |
| **Long-form Content Reading** | PARTIAL | Slack `section` blocks are hard-capped at 3000 characters. `item_model.py:24` `body` fields (like full intel reports) will aggressively truncate. | MODERATE |

---

## WHAT THE PLAN MISSED ENTIRELY

**1. Slack App Home UI Blocks CANNOT be Threaded**
The plan assumes "comments append => thread reply on the card". This is technically impossible. App Home views are built from Layout Blocks, not messages. They do not have timestamps, permalinks, or thread capabilities. If you attempt to use channel DMs to get threads, you lose the static "dashboard" concept entirely.

**2. The 100-Block Hard Cap destroys visibility**
Slack imposes a strict 100-block limit on `views.publish` for App Home. A single TCD item requires at least 2 blocks (Section for text + Actions for buttons). With `tcd/multi_tab.py:160` logging 200+ items across sources, you will hit the cap at ~50 items. The proposed "+N more" footer means 150 items are invisible by default—which completely recreates the "items aging unseen" problem the Commander built TCD to solve.

**3. AppSheet's Batched Sync vs. Slack's Rate Limits**
`writeback.py:469-598` `process_once()` is designed around a batched, offline diff of spreadsheet state. Slack is highly synchronous. Every button click (Close, Stage Move) must hit a server endpoint, compute the new state, and call `views.publish` to refresh the Commander's screen. Slack rate limits `views.publish` to 1 per second. If the Commander rapid-fires 5 triage decisions, the App Home will lag, drop inputs, or hit HTTP 429 Rate Limit errors.

**4. Silver Back-Gate Error Surfacing**
`writeback.py:271` details how Silver's front-frame `HOLD` silently appends to the `comments` column so the Commander sees the exact failure reason without leaving the app. In Slack, surfacing a dynamic failure string onto a specific card requires the backend to reconstruct and republish the *entire 100-block array* just to inject the warning text into that one item's section block.

**5. Native Offline Capabilities**
AppSheet works on a plane, caching edits and syncing when reconnected. Slack is completely dead without an active connection.

**Conclusion:**
Moving to Slack replaces a highly flexible, batched data plane (Google Sheets) with a rigid, rate-limited presentation layer. You lose bulk editing, tabbed organization, and offline triage, while slamming directly into hard Slack API limits (100 blocks, 3000 chars, no App Home threads). This is a severe architectural downgrade for a Commander dashboard.
