# The Wing: 24/7 Autonomous Operations Manual (Hale-Loop)
**Version:** 1.0  
**Date:** March 29, 2026  
**Status:** ACTIVE  
**Commander:** John Loucks  
**Objective:** Complete Cord-Cut Autonomy by April 10.

---

## 1. CORE ARCHITECTURE: THE HALE-LOOP
The Wing has transitioned from isolated, scheduled Python scripts to a continuous, event-driven Mixture of Agents (MoA) architecture managed by the Chief of Staff (Hale). 

### 1.1 The Operations Center (`~/Thunderbird/OpsCenter/`)
The entire agency runs through three shared files:
*   **`01_TASK_QUEUE.json`:** The single inbox for all triggers (emails, webhooks, timers, Telegram commands). 
*   **`00_COMMAND_LOG.md`:** The chronological ledger of all actions taken by the staff.
*   **`02_SCIF_PUZZLES.json`:** An air-gapped queue exclusively for DeepSeek to solve complex, PII-free logic puzzles.

### 1.2 The Division of Labor (The Sponge vs. The Snipers)
To maximize efficiency and protect Claude rate limits (MAX plan), labor is divided:
*   **The Sponge (Goose + Gemini 3.1-Pro):** Runs 24/7 as the Coordinator (Hale). Gemini reads the queue, assesses complexity, and routes the task. Gemini's massive context window and low cost make it perfect for endless monitoring.
*   **The Snipers (Claude Sonnet/Opus):** The staff (Dani, Luna, ELON, etc.). Claude only wakes up when Hale assigns a specific generative task. Hale determines if the task requires Sonnet (routine) or Opus (complex/emotional).
*   **The Watch Officer (Groq):** Handles instantaneous triage. Parses raw logs and webhooks in milliseconds to drop clean JSON into the queue.

---

## 2. SYSTEM ADMINISTRATION
The Hale-Loop is managed by a background systemd daemon. It survives reboots and terminal closures.

### 2.1 Service Commands
*   **Check Status:** `systemctl --user status thunderbird-overwatch.service`
*   **Stop Service:** `systemctl --user stop thunderbird-overwatch.service`
*   **Restart Service:** `systemctl --user restart thunderbird-overwatch.service`
*   **View Live Logs:** `tail -f /home/john/Thunderbird/OpsCenter/overwatch.log`

### 2.2 Backup Communications
While Telegram is the primary Command & Control (C2) interface, emergency alerts are routed via SMS using the `sendSmsNotification` tool (T-Mobile gateway).

---

## 3. MIGRATION PROGRESS (Phase 2)
*To be updated as we migrate legacy timers and n8n webhooks to the new JSON queue.*

*   [x] Establish OpsCenter directory structure.
*   [x] Write `thunderbird_overwatch.sh` routing daemon.
*   [x] Install daemon as `thunderbird-overwatch.service`.
*   [x] Test SMS backup communication tool.
*   [ ] Migrate `thunderbird-fpd-alert.timer` to write to `01_TASK_QUEUE.json`.
*   [ ] Migrate `thunderbird-innovation-scan.timer` to write to `01_TASK_QUEUE.json`.
*   [ ] Migrate n8n incoming email webhooks to write to `01_TASK_QUEUE.json`.

---

## 4. UPCOMING DEADLINES
*   **April 8:** REVERIE MVP complete (Erik & Melissa McLeod validation).
*   **April 10:** Commander Departure. Full hands-off autonomy engaged.

*This document will be continuously updated as the architecture expands.*