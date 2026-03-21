# MCP INFRASTRUCTURE SECURITY AUDIT
## Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
## Dreams2Memories Travel, LLC
## Date: 2026-03-20
## Classification: INTERNAL -- COMMANDER EYES ONLY

---

## ISSUE

The Thunderbird MCP server (port 8765), REST API (port 8766), client portal (port 8780), n8n automation (port 5678), and SSH (port 22) are all exposed to the public internet via Cloudflare Tunnel with **zero authentication on the MCP endpoint**. An attacker with the URL `mcp.d2mluxury.quest` can enumerate all 249 tools and execute any of them -- including `shell_exec`, which runs arbitrary bash commands on YOGA as the `john` user. This is a **critical, exploitable vulnerability** that matches the exact profile identified in the Bitsight and AgentSeal exposed-MCP-server reports.

---

## DISCUSSION

### 1. Exposure Assessment

**Confidence: HIGH** -- verified by direct testing during this audit.

#### What is exposed via Cloudflare Tunnel (config.yml)

| Hostname | Local Service | Auth Required | Status |
|----------|---------------|---------------|--------|
| `mcp.d2mluxury.quest` | `http://localhost:8765` | **NONE** | CRITICAL |
| `api.d2mluxury.quest` | `http://localhost:8766` | API key (X-API-Key header) | MODERATE |
| `portal.d2mluxury.quest` | `http://localhost:8780` | Magic link auth | LOW |
| `n8n.d2mluxury.quest` | `http://localhost:5678` | n8n built-in auth | LOW-MODERATE |
| `ssh.d2mluxury.quest` | `ssh://localhost:22` | SSH keys/password | LOW |

#### Server Binding

Both `travel_mcp_server.py` and `thunderbird_api.py` default to binding on `0.0.0.0` (all interfaces), meaning they accept connections from any network interface -- not just localhost. While the home LAN router provides some NAT protection, the Cloudflare Tunnel bypasses this entirely by design.

#### Firewall Status

**No firewall is active on YOGA.** Tested iptables, firewalld, and nftables -- all returned empty or not-found. The machine has no host-based firewall protecting these services.

### 2. The MCP Server: Full RCE via Public Internet

**Confidence: HIGH** -- confirmed via live testing.

I issued a `tools/list` JSON-RPC call to `https://mcp.d2mluxury.quest/mcp` with zero authentication. The server returned all 249 registered tools. Among the 41 tools I classified as dangerous:

**Remote Code Execution:**
- `shell_exec` -- executes arbitrary bash commands as user `john`, with `shell=True`, no input sanitization, no allowlist. This alone is game over.

**Email/Communication Abuse:**
- `gmail_send_email`, `gmail_create_draft`, `send_sms_notification`, `send_whatsapp`, `bulletin_send`, `send_client_email` -- an attacker could send emails as D2M, spam clients, or exfiltrate data via email.

**Data Exfiltration:**
- `gmail_read_message`, `gmail_search_messages`, `drive_read_document`, `drive_list_files`, `drive_download_file` -- full read access to Gmail and Google Drive.

**Data Destruction:**
- `gmail_trash_message`, `gmail_delete_draft`, `drive_delete_file`, `delete_dossier_api_file`, `delete_task` -- can destroy business records.

**Business System Manipulation:**
- `tess_create_booking`, `tess_update_booking`, `tess_create_client`, `tess_update_client` -- can create or modify records in the TESS booking system.

**The FastMCP server has DNS rebinding protection enabled**, which allowlists `mcp.d2mluxury.quest`, `10.0.0.53`, and the Tailscale IP. This is a defense against browser-based DNS rebinding attacks but provides **zero protection against direct HTTP requests** to the tunnel endpoint. It is not authentication.

### 3. REST API Authentication

**Confidence: HIGH** -- code review confirmed.

The REST API (`thunderbird_api.py`) does require an `X-API-Key` header, verified against a locally generated `api_key.txt` file. This is better than the MCP server's zero auth, but has issues:

- **Single static key** -- no rotation, no expiration, no per-client scoping
- **Key file permissions are 644** (world-readable) -- should be 600
- **Key is logged at startup** (first 8 + last 4 chars) -- information leakage in logs
- **Health endpoint (`/api/health`) requires no auth** -- confirms service existence to scanners
- **No rate limiting** -- brute force against the key space is unconstrained

### 4. Credential Exposure

**Confidence: HIGH** -- files reviewed directly.

#### .env files on disk (NOT in git -- .gitignore covers them)

| File | Contents |
|------|----------|
| `.env` | Telegram bot tokens, Commander chat ID, n8n API key (JWT) |
| `.env.keys` | Pinecone API key, GooseAI key, Anthropic API key |
| `.env.telegram` | Dani bot token, Commander chat ID |

#### mcp.json (checked into Claude config, NOT in Thunderbird git)

The `~/.claude/mcp.json` file contains a plaintext n8n JWT bearer token in the `headers` field. If this file is ever committed to a git repo, shared, or backed up to a cloud service, the n8n instance is compromised.

#### Positive findings

- `.gitignore` correctly excludes `.env*`, `api_key.txt`, `*_token.json`, `credentials.json`, and other sensitive files
- No credential files are tracked in git (verified via `git ls-files`)
- The Anthropic API key in `.env.keys` is a legacy key -- current operations use the Max plan ($0), reducing blast radius

### 5. Comparison to Industry Scan Reports

#### Bitsight TRACE Report (Dec 2025)

Bitsight found ~1,000 exposed MCP servers with no authorization. Their findings match our exposure exactly:
- MCP servers exposed over the internet without authorization become proxies for attackers to pivot into databases, file systems, and paid API services
- Servers with `shell_exec` capabilities create "a clear path to full system compromise"
- **Our server has this exact vulnerability.**

Source: [Bitsight Blog](https://www.bitsight.com/blog/exposed-mcp-servers-reveal-new-ai-vulnerabilities)

#### AgentSeal Scan (2025-2026)

Scanned 1,808 MCP servers; 66% had at least one security finding. Code execution risks were the most common category.

Source: [AgentSeal Report](https://agentseal.org/blog/mcp-server-security-findings)

#### Astrix State of MCP Security (2025)

Analyzed 5,000+ open-source MCP implementations:
- 88% require credentials, but 53% use insecure static secrets
- Only 8.5% use OAuth
- 82% have path traversal risk, 67% have code injection risk, 34% have command injection risk

Source: [Astrix Report](https://astrix.security/learn/blog/state-of-mcp-server-security-2025/)

#### "8,000+ MCP Servers Exposed" (Feb 2026)

Researchers reported scanning 8,000+ MCP servers visible on the public internet with admin panels, debug endpoints, or API routes exposed without authentication.

Source: [Medium Article](https://cikce.medium.com/8-000-mcp-servers-exposed-the-agentic-ai-security-crisis-of-2026-e8cb45f09115)

**Assessment: Our MCP server is in the exact category these reports describe as critically vulnerable. If Bitsight or AgentSeal scanned our endpoint, we would appear in their findings.**

### 6. Attack Scenario (Threat Model)

An attacker who discovers `mcp.d2mluxury.quest` (via DNS enumeration, certificate transparency logs, or the `mcp` subdomain pattern that Bitsight specifically targets) can:

1. **Enumerate all 249 tools** via `tools/list` (confirmed -- takes <1 second)
2. **Execute `shell_exec`** to run arbitrary commands as `john` on YOGA
3. **Read all email** via Gmail tools -- client PII, booking confirmations, financial data
4. **Send email as D2M** -- phishing clients, reputational destruction
5. **Access/delete Google Drive files** -- proposals, dossiers, booking records
6. **Modify TESS bookings** -- alter client reservations
7. **Pivot to other systems** -- SSH keys, Tailscale, credentials in .env files

Time from discovery to full compromise: **under 60 seconds.**

### 7. Lasso MCP Gateway Evaluation

**Confidence: MODERATE** -- based on public documentation and GitHub repo review. Not hands-on tested.

#### What It Is

Lasso Security's MCP Gateway is an open-source intermediary that sits between LLM clients and MCP servers. Released April 2025. Apache 2.0 license.

- **GitHub:** [lasso-security/mcp-gateway](https://github.com/lasso-security/mcp-gateway)
- **PyPI:** `pip install mcp-gateway` (optional: `mcp-gateway[presidio]` for PII detection)
- **Architecture:** Plugin-based proxy -- intercepts all MCP JSON-RPC traffic

#### What It Adds

| Capability | Description |
|------------|-------------|
| **Request/response sanitization** | Intercepts and scrubs sensitive data (API keys, tokens, PII) |
| **Security scanner** | Analyzes MCP server reputation and risk before loading |
| **Prompt injection detection** | Real-time blocking of injection attempts in tool inputs |
| **Audit logging** | Full trail of every tool invocation |
| **Plugin system** | Extensible guardrails at the request/response level |
| **MCP server blocking** | Auto-blocks servers with poor reputation scores |
| **Credential masking** | Detects and masks Azure secrets, GitHub tokens, AWS keys, JWTs, etc. |

#### How It Would Sit in Our Architecture

```
Current (VULNERABLE):
  Internet -> cloudflared -> localhost:8765 (MCP server, no auth)

With Lasso Gateway:
  Internet -> cloudflared -> Lasso Gateway (:8770) -> localhost:8765 (MCP server)
```

The gateway would proxy all MCP traffic through its plugin pipeline before forwarding to our server. Cloudflared config would point `mcp.d2mluxury.quest` to the gateway port instead of 8765 directly.

#### Limitations

- **Lasso does NOT add authentication by itself** -- it adds guardrails, scanning, and audit logging, but is not a substitute for proper auth (OAuth 2.1, mTLS, or at minimum a bearer token)
- The advanced AI-safety guardrails (jailbreak monitoring, threat detection) require a Lasso API key (commercial tier)
- Open-source version provides basic plugins only
- It is relatively new software (April 2025) with limited production track record
- **It does not solve the root problem** -- an unauthenticated endpoint is still unauthenticated

#### Competing Solutions

| Gateway | Focus | Notes |
|---------|-------|-------|
| **Lasso** | Security-first, plugin guardrails | Best for threat detection |
| **Microsoft mcp-gateway** | Kubernetes, session routing | Enterprise/cloud scale |
| **Docker mcp-gateway** | Container orchestration | Docker-native |
| **Cloudflare Access** | Zero-trust auth layer | Already in our Cloudflare stack |

**Assessment: Lasso is a valuable defense-in-depth layer but is NOT sufficient as a standalone fix. The immediate priority is authentication, not filtering.**

### 8. Additional MCP Threat Vectors

**Confidence: MODERATE** -- based on published research, not direct testing against our server.

| Threat | Description | Our Exposure |
|--------|-------------|--------------|
| **Tool Poisoning** | Malicious instructions embedded in tool descriptions | LOW -- we author our own tools |
| **Rug Pull Attack** | Tool definitions mutate after approval | LOW -- we control the server |
| **Prompt Injection via Tool Output** | Attacker-controlled data in tool responses manipulates the LLM | MODERATE -- tools that scrape external sites could return poisoned content |
| **Cross-Server Data Flow** | Tool chains across servers create exfiltration paths | MODERATE -- our server has both read (Gmail/Drive) and write (email/SMS) tools |

Sources: [Invariant Labs](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks), [Simon Willison](https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/), [CyberArk](https://www.cyberark.com/resources/threat-research-blog/poison-everywhere-no-output-from-your-mcp-server-is-safe)

---

## OPTIONS

### Option 1: Immediate Cloudflare Access Lock-down (Recommended -- hours, not days)

Add Cloudflare Access (Zero Trust) policies to `mcp.d2mluxury.quest` and `api.d2mluxury.quest`. Cloudflare Access is already available on our Cloudflare account (the tunnel infrastructure is in place). This adds authentication before traffic even reaches our servers.

- **Effort:** 1-2 hours configuration
- **Cost:** Free tier covers up to 50 users
- **Effect:** All tunnel-exposed services require authentication before any request reaches the MCP server
- **Limitation:** Requires compatible client (browser, service token, or mTLS cert)

### Option 2: MCP Server Bearer Token Authentication (Recommended -- concurrent with Option 1)

Add a bearer token check to the MCP server's HTTP transport layer, similar to the REST API's X-API-Key pattern. Reject all requests without a valid token.

- **Effort:** 2-4 hours coding + testing
- **Cost:** Zero
- **Effect:** Even if Cloudflare Access is bypassed, the server itself rejects unauthenticated requests

### Option 3: Bind to localhost + Cloudflare Tunnel only (Quick win)

Change default bind from `0.0.0.0` to `127.0.0.1` in both servers. Cloudflare Tunnel connects to localhost anyway, so tunnel access still works. This eliminates LAN-level access to the services.

- **Effort:** 15 minutes
- **Cost:** Zero
- **Effect:** Services only accessible via tunnel (which then needs its own auth -- see Option 1) or local processes

### Option 4: Deploy Lasso MCP Gateway (Defense in depth -- after Options 1-3)

Install Lasso as a proxy layer for audit logging, credential masking, and prompt injection detection. This is the polish layer, not the foundation.

- **Effort:** 4-8 hours setup + testing
- **Cost:** Free (open source core), paid for advanced AI guardrails
- **Effect:** Adds monitoring, PII scrubbing, and injection detection to all MCP traffic

### Option 5: Remove shell_exec from MCP server (Immediate risk reduction)

Remove or disable the `shell_exec` tool from the MCP server entirely. Claude Code already has native shell access -- there is no operational need for this tool to exist on the MCP server.

- **Effort:** 10 minutes
- **Cost:** Zero
- **Effect:** Eliminates the single most dangerous tool from the attack surface

### Option 6: Fix credential file permissions (Immediate)

- `api_key.txt`: Change from 644 to 600
- Verify all `.env*` files are 600
- Remove API key partial logging from startup

- **Effort:** 5 minutes
- **Cost:** Zero

---

## ACTIONS I RECOMMEND TAKING

Priority-ordered. Items 1-4 should be executed within 24 hours. Items 5-6 within the week.

1. **IMMEDIATE (today): Execute Options 5 + 6 + 3** -- Remove `shell_exec` from MCP server, fix file permissions, bind to 127.0.0.1. Total effort: ~30 minutes. This stops the bleeding.

2. **URGENT (today/tomorrow): Execute Option 1** -- Enable Cloudflare Access on `mcp.d2mluxury.quest` and `api.d2mluxury.quest`. This is the single most impactful change -- it puts a proper authentication gate in front of everything.

3. **HIGH (this week): Execute Option 2** -- Add bearer token auth to the MCP server itself. Defense in depth -- do not rely solely on Cloudflare Access.

4. **HIGH (this week): Rotate all credentials** -- After the auth layer is in place, rotate: Telegram bot tokens, n8n API key, Pinecone key, GooseAI key, and the REST API key. Assume they may have been observed.

5. **MODERATE (next week): Execute Option 4** -- Deploy Lasso Gateway for audit logging and injection detection. This is the monitoring/alerting layer.

6. **LOW (ongoing): Implement OAuth 2.1** -- Replace static bearer tokens with proper OAuth. This is the long-term target per OWASP MCP security guidance. Only worth the effort once the immediate fires are out.

---

## INFORMATION GAPS

| Gap | Impact | Collection Plan |
|-----|--------|-----------------|
| Has anyone already discovered/scanned our MCP endpoint? | If yes, may already be compromised | Check Cloudflare analytics for unexpected requests to mcp.d2mluxury.quest; review shell_exec.log |
| Is `mcp.d2mluxury.quest` indexed in Certificate Transparency logs? | CT logs are public and scanned by researchers | Search crt.sh for d2mluxury.quest certificates |
| Are there other Cloudflare Tunnel IDs active? | Second tunnel config found in .cloudflared | Audit both tunnel credential files |
| What access does the `john` user have beyond Thunderbird? | shell_exec runs as john -- blast radius unknown | Audit sudo access, SSH keys, other service accounts |
| Has the n8n JWT in mcp.json been exposed via Claude config sync? | Could grant access to n8n workflows | Check if ~/.claude/ syncs to any cloud service |

---

## BOTTOM LINE

**This is the most critical security finding since Thunderbird went operational.** The MCP server is a fully functional, unauthenticated remote administration tool accessible to anyone on the internet. The `shell_exec` tool alone constitutes complete system compromise. The fact that no incident has occurred yet is luck, not security.

The fix is straightforward and can be implemented in under a day. The question is not whether to act, but how fast.

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence), Dreams2Memories Travel, LLC*

*Sources cited inline. All findings verified by direct testing unless noted otherwise.*
