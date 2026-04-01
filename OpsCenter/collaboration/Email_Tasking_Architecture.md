# TASKING VIA EMAIL: ARCHITECTURE REVIEW & BUILD PLAN
**To:** Commander (Yoda)
**From:** A7 (Gauge) / Goose

## 1. THE CURRENT STATE (Architecture Review)
Currently, **there is no active listener routing inbound emails into AI tasks**. 
The Wing relies entirely on:
1.  **Telegram C2** (telegram_pager_c2.py / Goose Gateway)
2.  **File-based Inboxes** (claude_inbox.md / goose_inbox.md)
3.  **Manual CLI Execution**

While you have sent emails with "red!" triggers to `d2mconcierge@gmail.com`, the system is deaf to them because:
*   The `safe_cli_gate.py` (STAR Protocol) was built to *guard outbound* tool calls (like preventing unauthorized sends), not to ingest *inbound* emails as commands.
*   There is no cron job or daemon actively pulling the `_gmailSearchMessages` or `_gmailReadThread` tools to check for new directives from `johnloucks3@gmail.com`.

## 2. THE PROPOSED ARCHITECTURE (Email-to-Task Pipeline)
We need a secure, asynchronous pipeline that reads specific emails and converts them into actionable JSON blocks for the new Dormant Scheduler.

### Security Gates (Non-Negotiable)
1.  **Sender Verification:** The system must ONLY accept tasks from `johnloucks3@gmail.com`. Any other sender is ignored.
2.  **Trigger Keyword:** The subject line or body must contain a specific activation phrase (e.g., `[WING-TASK]` or `🔴 RED!`) to separate casual replies from actual commands.

### The Component Flow
1.  **The Fetcher (`email_task_ingest.py`):** 
    *   A lightweight Python script that uses the `ThunderbirdMCP` Gmail tools.
    *   Query: `from:johnloucks3@gmail.com is:unread subject:"RED!"`
    *   Runs on the same 2-minute systemd timer as our upcoming Dormant Scheduler.
2.  **The Parser (Groq / Llama-3):** 
    *   If a matching email is found, the script pulls the body and uses Groq (for maximum speed) to parse the human text into our standard JSON task schema (`task_id`, `priority`, `model`, `instructions`).
3.  **The Router:** 
    *   The generated JSON is dropped directly into the master queue, and the email is marked as "Read" and labelled `[AI-TASKED]` so it isn't processed twice.

## 3. COMMANDER'S DECISION
I can code the `email_task_ingest.py` script right now using the Thunderbird MCP tools I already have access to. 
Shall I begin writing the ingest script, or do you want to wait to integrate it with Claude's overall 2-Minute Scheduler plan?
