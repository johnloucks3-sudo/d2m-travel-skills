# Phase 4: Permission & Handoff Strategy

## 1. Security Perimeter (Lockdown)
To prevent unauthorized or bypass execution of the `mcp2cli` tool, we will restrict binary access at the Linux OS level.

### Step-by-Step Command Plan:
1.  **Create Security Group:**
    ```bash
    sudo groupadd wing_gate
    ```
2.  **Add Gatekeeper Process to Group:**
    ```bash
    sudo usermod -a -G wing_gate john
    ```
3.  **Restrict Binary Access:**
    (Assuming `mcp2cli` is in `/usr/local/bin/mcp2cli`)
    ```bash
    sudo chgrp wing_gate /usr/local/bin/mcp2cli
    sudo chmod 750 /usr/local/bin/mcp2cli
    # 750: Owner (root) can do everything, Group (wing_gate) can execute, Others (world) can do nothing.
    ```

## 2. Handoff Strategy (Legacy → Gate)
We will perform a "Soft-Switch" to ensure no downtime for your operational agents.

### The Migration Steps:
1.  **Preparation:** Deploy `safe_cli_gate.py` as a standalone background process.
2.  **Verification:** Point the `claude_inbox_watcher.py` (via configuration) to the new `safe_cli_gate.py` endpoint instead of raw `mcp2cli` calls.
3.  **Monitoring:** Run both systems for 24 hours. The legacy system (Hale-Loop/Watcher) will be the primary, and the new `safe_cli_gate` will log "Shadow Executions" (simulated tool calls without actually changing state) to verify the PII/Directive filter accuracy.
4.  **Final Cutover:** Once `star_protocol_log` confirms 100% accurate filtering, decommission the `claude_inbox_watcher.py` process and make the `safe_cli_gate` the primary authority.

## 3. Commander Review
- **Permission Model:** Are these restrictions sufficient for the level of security you require?
- **Migration:** Does the "Shadow Execution" (dry-run) period of 24 hours meet your risk-mitigation standards?
