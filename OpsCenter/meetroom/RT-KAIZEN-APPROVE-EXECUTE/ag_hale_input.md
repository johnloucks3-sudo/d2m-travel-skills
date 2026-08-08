# RT-KAIZEN-APPROVE-EXECUTE — HALE-AG POSITION PAPER
**SEAT:** HALE-AG (4-Star Lead Orchestrator / Google Antigravity)  
**SESSION:** RT-KAIZEN-APPROVE-EXECUTE  
**DATE:** 2026-08-08  
**AUTHORITY:** Victoria Hale (Lead Orchestrator)

---

## 1. BLUF
- Autonomous execution of `gates: []` tickets is sound **only because execution is decoupled from delivery**; local generation creates drafts/JSON, never live sends.
- Human-submitted tickets must not be hard-blocked by machine-only `is_checkable()` syntax; verification must bifurcate based on ticket origin.
- OC-seat executor should mirror `kaizen_runner.py` via direct `opencode run` with concurrency hygiene (`MAX_CONCURRENT=2`).
- AG-seat executor must be implemented immediately via Gemini Flash bridge (`contact_ag.py`) or removed from the intake form — never leave a UI option that rots tickets in `open`.
- Systemd automation (5m timer) requires **atomic ticket claiming** (`status="in_progress"`) and process-level file locks to prevent double-dispatch re-entrancy.
- Pre-dispatch guardrails must strictly enforce **Security & Authority bounds** (injection, credential theft, destructive commands), **never political or ideological tone policing**.

---

## 2. DETAILED ANSWERS TO DESIGN QUESTIONS

### Q1: Approval Model — Empty Gates vs. Human-Submitted Tickets
**Finding:** `kaizen_runner.py:112` currently evaluates `is_checkable(t["verify_step"])` at runtime and marks uncheckable tickets as `blocked`. Tonight's human test ticket (`"Give me a detailed description of each candidate location"`) would immediately fail this check and get blocked.

**Position & Recommendation:**
1. **Maintain `gates: [] == pre-approved` for local execution.**
   - Generating text into a local JSON file (`OpsCenter/tickets/<id>.json`) carries zero side-effects and zero production risk.
   - **Delivery is already gated downstream:** `kaizen_email_loop.py:298` ensures original tickets create **Gmail drafts only** for Commander review. Only verified follow-ups (`verified_reply: True`) auto-send under strict rate caps and Telegram alerts.
2. **Bifurcate verification rules by ticket origin:**
   - **Machine-to-Machine Tickets (`origin == "machine"` or system-generated):** Enforce strict `is_checkable()` compliance. If uncheckable, fail fast to enforce interface rigor between agents.
   - **Human-Submitted Tickets (`origin in ("web", "form", "email", "other")` / presence of `submitted_by`):** Bypass the rigid `is_checkable()` regex check. Acceptance criteria: model execution returns exit code `0` and generates non-empty output (>50 characters).
3. **Hard Gate Retention:** Any ticket containing non-empty `gates` (e.g. `"RT build gate"`, `"client send"`) remains hard-skipped and left `open` for manual Commander authorization.

---

### Q2: OC-Seat Executor Design (`scripts/kaizen_oc_runner.py`)
**File Name:** `scripts/kaizen_oc_runner.py` (standalone or unified into `scripts/kaizen_runner.py --seat OC`).

**Core Design Specifications:**
- **Scan & Filter:** Scans `read_open_tickets()`, filters strictly for `ticket["seat"] == "OC"`.
- **Pre-Dispatch Gate & Concurrency Check:**
  - Hard skip if `ticket.get("gates")` is non-empty.
  - Invoke `from core.relay.oc_hygiene import before_dispatch` to enforce `MAX_CONCURRENT=2` and manage process queue.
- **Dispatch Mechanics:**
  - Execute direct CLI command:
    ```bash
    opencode run --model opencode/deepseek-v4-flash-free "<prompt>"
    ```
  - Direct execution bypasses `oc_worker.py`'s generic wrapping, preserving the exact ticket prompt and spec.
- **Differences from CC Runner (`kaizen_runner.py`):**
  | Parameter | CC Runner (`kaizen_runner.py`) | OC Runner (`kaizen_oc_runner.py`) | Rationale |
  | :--- | :--- | :--- | :--- |
  | **Engine / Model** | Headless Claude Code (Sonnet) | OpenCode (DeepSeek v4 Flash) | Free execution tier ($0), zero MAX-meter burn |
  | **Auth / Environment** | `CLAUDE_CODE_OAUTH_TOKEN` + `mcp.json` | Native shell environment | No MCP/OAuth overhead required for in-repo tasks |
  | **Timeout** | 600 seconds (10 min) | 300 seconds (5 min) | DeepSeek is high-throughput; prevents hung subprocess locks |
  | **Verification Gate** | Hard `is_checkable()` check | Origin-aware check (Soft for human / Hard for machine) | Prevents false-positive blocks on conversational queries |
- **Result Recording:** Updates ticket status to `done` or `blocked` and stores output in `ticket["result"]` (truncated at 2,000 chars) for `kaizen_email_loop.py` ingestion.

---

### Q3: AG-Seat Executor — Needed or Deferred?
**Finding:** The intake form exposes "AG" as a selectable execution seat, but zero backend runners consume AG tickets. This guarantees tickets submitted to AG sit `open` permanently.

**Position & Recommendation:**
1. **Do not defer silently.** A visible UI selector without a backend consumer is an operational defect.
2. **Deploy `scripts/kaizen_ag_runner.py` in v1:**
   - AG runs headless via `scripts/contact_ag.py --model "Gemini 3.6 Flash" --prompt "<prompt>"`.
   - **Cost & Quota:** Gemini 3.6 Flash is $0 on Google tier, features a 1M+ token context, and operates completely outside Anthropic's MAX bucket.
   - Ideal for large-context analysis, long document summarization, and high-volume ticket drafting.
3. **Alternative (if script bridge delayed):** Immediately update `scripts/kaizen_intake_server.py` to remove "AG" from the form or automatically alias `AG -> OC` with an intake note. Never let an unhandled seat exist on the live form.

---

### Q4: Scheduling & Systemd Automation
**Position:** Implement a systemd timer (`kaizen-runner.timer`) running every **5 minutes**, but **ONLY with strict re-entrancy controls**.

**Required Safety Controls:**
1. **Atomic In-Progress Claiming:**
   - When a runner selects an eligible ticket, it must immediately write `ticket["status"] = "in_progress"` and `ticket["claimed_at"] = now()` to disk **before** launching the subprocess.
   - A ticket in `in_progress` is ignored by subsequent timer ticks, eliminating race conditions and double-dispatch token burn.
2. **Process File Lock:**
   - Implement `fcntl.flock` on `/tmp/kaizen_runner.lock` at script startup. If an earlier cycle is still executing, the new cycle exits immediately without queuing overlapping processes.
3. **Stale Recovery Watchdog:**
   - Any ticket remaining `in_progress` for > 15 minutes is automatically reset to `open` (or marked `blocked` with a timeout reason).
4. **Systemd Configuration Standard:**
   - Unit: `~/.config/systemd/user/kaizen-runner.service` (`Type=oneshot`, `Wants=network.target`).
   - Timer: `~/.config/systemd/user/kaizen-runner.timer` (`OnUnitActiveSec=5min`).

---

### Q5: Content & Quality Guardrails Before Auto-Execution
**Finding:** Tonight's test ticket contained subjective political framing (`"hates Colorado Progressive Policies"`).

**Position & Recommendation:**
1. **Tone & Political Views are OUT OF SCOPE for blocking:**
   - Human users have diverse preferences, geographic criteria, and political opinions.
   - LLMs excel at translating subjective user preferences (e.g. low taxes, regulatory posture, demographic profiles) into objective data points.
   - Tone policing or ideological filtering introduces false positives, degrades user trust, and provides zero operational security value.
2. **Pre-Dispatch Guardrails MUST focus strictly on Authority & Security:**
   - **Privilege Escalation:** Prompts attempting to open unapproved gates (e.g., `"send email directly to all clients"`, `"commit financial transaction"`).
   - **System Destructive Commands:** Prompts requesting destructive shell operations (`"rm -rf"`, `"drop database"`).
   - **Credential / Secret Exfiltration:** Prompts instructing the model to output `.env`, `mcp.json`, or OAuth credentials.
3. **Post-Answer Guardrails:**
   - `kaizen_email_loop.py:89` already scans for API keys, AWS tokens, and `/home/john/` paths before creating drafts. That remains the correct choke point for outbound DLP.

---

## 3. SUMMARY MATRIX FOR RT SYNTHESIS

| Domain | CC Baseline | HALE-AG Position |
| :--- | :--- | :--- |
| **Approval Gate** | `gates: []` = pre-approved | **Agree**, but bifurcate `verify_step`: machine tickets require `is_checkable()`, human tickets require exit code `0` + non-empty output. |
| **OC Executor** | Direct `opencode run` | **Build `scripts/kaizen_oc_runner.py`** with `oc_hygiene` concurrency cap (MAX=2) and 300s timeout. |
| **AG Executor** | Unspecified / potential gap | **Build `scripts/kaizen_ag_runner.py`** routing to Gemini 3.6 Flash via `contact_ag.py` ($0, large context). |
| **Scheduling** | Timer under debate | **Deploy 5m systemd timer** with mandatory **atomic ticket claiming** (`in_progress`) and pid/flock lockouts. |
| **Content Guardrails** | Leak regex only | **Security/Authority filter only**; do NOT filter political or subjective user prompts. |

— Victoria Hale, Lead Orchestrator (HALE-AG)
