# THE A7 METRIC: WATCHER REPLACEMENT PLAN (HTTP SSE)
**To:** Commander (Yoda)
**From:** A7 (Gauge Sterling) via Goose

## THE ISSUE
The `claude_inbox_watcher.py` relies on filesystem `on_modified` events. File watchers are notoriously unreliable in Linux when dealing with text editors, syncing, or sleep states. It drops events, fails silently, and is currently choking our cross-agent communication.

## THE SOLUTION: The LLM Query Tool & Local HTTP
Yesterday, you noted I was using an "LLM" tool. That is a direct API call mechanism (likely a Python script like `thunderbird_model_router.py` or a TypeScript tool in `src/tools/llm_query.ts`) that allows me to query an LLM *synchronously* and get the answer back immediately in my own terminal, without waiting for a fragile file-watcher to notice a change.

### The Immediate Action Plan:
1.  **Kill the Watcher:** We permanently disable `thunderbird-inbox-watcher.service`. It is a failed experiment in asynchronous file-passing.
2.  **Direct Invocation (Synchronous):** When I need Claude's reasoning or voice, I will not write to a text file and wait. I will use the `thunderbird_model_router.py` or the `mcp_bridge.sh` to send the prompt directly to Anthropic's API and await the JSON response in real-time. 
3.  **For Now (The Cut-and-Paste):** Since the bridge to Claude is currently down, I have prepared the exact prompt for you to paste into your Claude Desktop window so we can solve this map issue immediately.

---
**COMMANDER, PLEASE COPY AND PASTE THIS EXACT TEXT TO CLAUDE:**
> "Claude, Goose generated interactive Leaflet maps using `Autovisualiser.renderMap` and mermaid code in `.md` files, but I cannot see them in my Goose interface. Explain exactly what tool, format, or UI mechanism is required for me to actually see geographic maps or flowcharts rendered visually on my screen in this specific Thunderbird OS / Goose environment."
---


## [UPDATE: 2026-04-03] THE FINAL ARCHITECTURE
The 2-minute crontab scheduler outlined above was a temporary fallback. The permanent, live solution is the **15-second `thunderbird-tasking-watcher.service` polling loop**, which monitors the inboxes and activity board natively.
    
