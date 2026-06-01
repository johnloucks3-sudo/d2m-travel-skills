# Conceptual Plan Summary

This document captures the conceptual decisions made during our planning session.

## Part 1: Claude Model Usage Rules & Meter

### 1.1: Tiered Model Selection Logic (The "COS" Rules)

- **Default Model:** Claude Haiku is the standard model for all tasks to conserve resources.
- **Keywords for Haiku:** Tasks containing "Summarize," "List," or "Staff this issue" will explicitly use Haiku.
- **Automatic Escalation to Sonnet:** The COS AI is authorized to use Claude Sonnet when tasks contain the keywords "Analyze," "Synthesize," or "Recommend."
- **Commander Approval for Opus:** Claude Opus is reserved for tasks explicitly marked as "critical" or when the Commander gives direct approval (e.g., "Commander approves OPUS use").
- **Performance Feedback Loop:** Task failures or low-quality outputs are logged. COS will consult this log to preemptively escalate models for similar tasks in the future, improving efficiency over time.
    - **[Claude] Comment:** This is a robust system. The feedback loop is critical for long-term efficiency. I recommend adding a "confidence score" to the log. If Haiku completes an "Analyze" task, but with low confidence, the log should reflect that, providing more nuanced data for COS.
- **Graceful Degradation:** If a model is requested without authorization, the system will fall back to the highest-level authorized model and execute the task.

### 1.2: The Usage Meter

- **Data Source:** An automated process will retrieve usage statistics directly from the Claude desktop application.
    - **[Claude] Comment:** This is the most significant technical challenge. Accessing data from a running desktop application can be brittle. An alternative could be an OCR-based screen reader focused on the specific part of the window, or if an API exists, that would be far more reliable. This task is high-risk.
- **Metrics to Track:**
    1. Session Percent Used
    2. Weekly Points
    3. Sonnet Only Points
- **Access:** The metrics will be available on-demand for you (the Commander) and will be used by the COS AI for its decision-making.
- **Tiered Caution Thresholds & Rules:** The single 70% threshold is replaced with more nuanced rules:
    - **1. Weekly Limit > 70%:** COS uses discretion. It will attempt tasks with Haiku first. Escalation to Sonnet will only occur if Haiku's output is unacceptable.
    - **2. Session Limit > 80%:** The same discretionary rule as the Weekly Limit applies.
    - **3. Sonnet Limit > 80%:** Sonnet use becomes highly restricted and is only approved for tasks predicted to be "short".

---

## Part 2: Telegram Bot Latency & Error Messages

- **Problem:** The "D2M Command Center" bot experiences significant delays and sends an erroneous "maximum number of actions" message when handling complex commands. This is caused by a restrictive safety limit on internal process steps.
- **Conceptual Solution:** A two-pronged approach will be implemented.
    1.  **Higher Limit (A):** The arbitrary action limit will be significantly increased to allow complex but legitimate tasks to complete without interruption.
    2.  **Progress Updates (C):** For very long-running tasks, the bot will be redesigned to send periodic, informative status updates (e.g., "Analysis is 50% complete..."). This will serve the dual purpose of keeping the user informed and resetting any underlying process timers or counters, preventing timeouts.
        - **[Claude] Comment:** Approach A is a good short-term fix. Approach C is the correct long-term architectural solution. It builds a foundation for a more robust, asynchronous task handling system. This should be prioritized.

- **Implementation Note:** Per Commander's instruction, the technical execution of this solution will be tasked to the Claude model at a later date.

---

## Part 3: Goose Self-Monitoring Framework

- **Objective:** To provide proactive, transparent monitoring of goose's own operational limits to ensure system stability and prevent failures.
- **Monitored Metrics:**
    1.  **Tool Call Rate:** Frequency of API/tool calls to prevent server overload.
    2.  **Context Window Saturation:** Percentage of active memory (context) in use.
        - **[Claude] Comment:** Excellent metrics. I recommend adding a third: "Tool Failure Rate." If a specific tool begins failing consistently, it's a critical system health indicator that precedes a total failure. Goose should enter a YELLOW state if a tool fails more than, say, 3 times in a 10-minute window.
- **Status System:** A three-tiered Green/Yellow/Red system will be used.

### Status Tiers:
(The Green/Yellow/Red tiers are well-defined and require no changes.)

---

## Part 4: Daily Tasking Log

- **Objective:** To create a single, persistent, and analyzable log of all tasks to track outcomes and guide future strategy.
- **Storage:** A single Markdown file named `daily_task_log.md` will be created and appended to.
- **Location:** The file will be stored at `/home/john/Thunderbird/daily_task_log.md`
- **Log Entry Structure:** Each entry will be a Markdown block containing all necessary fields.
    - **[Claude] Comment:** The structure is excellent for readability. For machine parsing and trend analysis, consider a dual-format approach. Append the human-readable Markdown, but also append a single line of JSON or CSV to a separate `.log` file. This would make programmatic analysis much faster and less error-prone for goose.
- **Integration:** Morning Report and Trend Analysis are well-defined.

---

## [Claude] Proposed Work Breakdown

This plan requires a blend of high-level logic, system orchestration, and specific tool implementation.

**Best suited for goose (as the Orchestrator/COS):**
- **Core Logic:** Implementing the tiered model selection (COS rules) and the Green/Yellow/Red self-monitoring logic. This is internal to goose's operation.
- **Orchestration:** All file I/O (reading/writing the task log), sending prompts to other models, and presenting information to the Commander. Goose is the master controller of the workflow.
- **Trend Analysis:** Reading the log file and performing the data analysis is a core strength.

**Best suited for Claude (as the Specialist Implementer):**
- **Data Extraction (The Usage Meter):** The high-risk task of getting data from the Claude desktop app should be delegated to a specialist. This requires focused, potentially complex code (OCR, UI automation, or API reverse-engineering) that is outside of goose's main orchestration loop.
- **Telegram Bot Modification:** Modifying the bot's codebase to implement the "Progress Update" feature is a discrete, self-contained coding task perfect for a specialist model. Goose would define the requirements, and Claude would write the new functions for the bot.
- **Dual-Log Format:** If the dual-log (Markdown + JSON) approach is adopted, Claude could be tasked with writing the specific function that takes task data and correctly formats it into both formats.

---
## Part 5: Operational Protocols

### The "Coord" Process
This protocol defines the standard four-step process for Goose-Claude collaboration, as defined by the Commander.
1.  **Commander Tasks:** The Commander initiates a task.
2.  **Goose Transcribes, Tasks, Transmits:** Goose formalizes the task, constructs the necessary prompts/code, and transmits it to the appropriate model (e.g., Claude).
3.  **Claude Receives, Responds, Returns:** The target model executes the task and returns the result.
4.  **Goose Receives, Analyzes, Synthesizes, Replies:** Goose processes the result, synthesizes the key information, and presents the final, actionable output to the Commander.
