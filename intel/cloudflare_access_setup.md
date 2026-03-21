# CLOUDFLARE ACCESS + LASSO MCP GATEWAY — SECURITY HARDENING PLAN
## Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
## Dreams2Memories Travel, LLC
## Date: 2026-03-20
## Classification: INTERNAL — COMMANDER EYES ONLY

---

## ISSUE

The MCP endpoint at `mcp.d2mluxury.quest` is exposed via Cloudflare Tunnel. As of this session, it is bound to localhost and `shell_exec` is disabled. The next hardening layer is Cloudflare Access (perimeter authentication) and optionally Lasso MCP Gateway (inspection/audit proxy). This document provides the exact steps Commander needs to execute via the Cloudflare dashboard and evaluates whether Lasso adds value beyond our current controls.

---

## DISCUSSION

### Current Security Posture (Post-Hardening Sprint)

| Control | Status | Notes |
|---------|--------|-------|
| MCP bound to 127.0.0.1 | DONE | Line 865 of `travel_mcp_server.py` |
| REST API bound to 127.0.0.1 | DONE | Line 1337 of `thunderbird_api.py` |
| `shell_exec` disabled | DONE | Commented out, line 738 of `travel_mcp_server.py` |
| REST API bearer token auth | DONE | `BearerTokenMiddleware` in `thunderbird_api.py` (line 125) |
| MCP server bearer token auth | **NOT DONE** | MCP server has NO authentication layer |
| `.api_token` file permissions | DONE | 600 john:john |
| Cloudflare Access | **NOT DONE** | This document covers setup |
| DNS rebinding protection | DONE | `TransportSecuritySettings` with explicit allowed hosts |

**Critical gap:** The MCP server itself (`travel_mcp_server.py` on port 8765) has NO bearer token middleware. Only the REST API (`thunderbird_api.py` on port 8766) has `BearerTokenMiddleware`. Anyone who reaches `mcp.d2mluxury.quest` through the Cloudflare Tunnel can invoke all 249 MCP tools without authentication. Cloudflare Access is the fix.

---

## PART 1: CLOUDFLARE ACCESS SETUP

### Infrastructure Context

- **Tunnel ID:** `0e0f57b6-33a1-4ed1-b3db-9b886f5add72`
- **Tunnel name:** `thunderbird`
- **cloudflared version:** 2026.3.0
- **Config location:** `/home/john/.cloudflared/config.yml`
- **Tunnel credentials:** `/home/john/.cloudflared/0e0f57b6-33a1-4ed1-b3db-9b886f5add72.json`

### Cloudflare Access CANNOT be configured via cloudflared config.yml

Access policies are managed exclusively through:
1. Cloudflare Zero Trust Dashboard (https://one.dash.cloudflare.com/)
2. Cloudflare API
3. Terraform

The `config.yml` only controls tunnel routing (which hostnames → which local services). Access policies are a separate layer applied at Cloudflare's edge.

---

### Step-by-Step: Add Cloudflare Access Application for MCP

#### Step 1: Enable One-Time PIN Identity Provider

1. Go to **Cloudflare Zero Trust Dashboard** → https://one.dash.cloudflare.com/
2. Navigate to **Integrations** → **Identity providers**
3. Click **Add new identity provider**
4. Select **One-time PIN**
5. Click **Save**

This enables email-based OTP authentication — no external IdP required.

#### Step 2: Create Access Application for MCP

1. Navigate to **Access controls** → **Applications**
2. Click **Add an application**
3. Select **Self-hosted**
4. Configure:
   - **Application name:** `D2M MCP Server`
   - **Session duration:** `24 hours` (or shorter for higher security)
   - **Application domain:** `mcp.d2mluxury.quest`

#### Step 3: Create Allow Policy (Commander Only)

1. **Policy name:** `Commander Access`
2. **Action:** `Allow`
3. **Include rule:**
   - **Selector:** `Emails`
   - **Value:** `johnloucks3@gmail.com`
4. (Optional) Add `d2mconcierge@gmail.com` if automated systems need access
5. **Require rule** (optional but recommended):
   - **Selector:** `Login Methods`
   - **Value:** `One-time PIN`

This means ONLY `johnloucks3@gmail.com` can authenticate, and they must use the email OTP flow.

#### Step 4: Create Service Token for Automated Access

For Chromebook → Yoga MCP calls (Claude CLI, n8n workflows, etc.):

1. Navigate to **Access controls** → **Service credentials** → **Service Tokens**
2. Click **Create Service Token**
3. **Name:** `D2M-MCP-Automation`
4. **Duration:** `1 year`
5. **SAVE THE CREDENTIALS IMMEDIATELY** — the Client Secret is shown only once:
   - `CF-Access-Client-Id: <CLIENT_ID>`
   - `CF-Access-Client-Secret: <CLIENT_SECRET>`
6. Store these in `/home/john/Thunderbird/.cf_service_token` with `chmod 600`

#### Step 5: Add Service Token to MCP Access Policy

1. Go back to the `D2M MCP Server` application
2. Add a second policy:
   - **Policy name:** `Automation Service Token`
   - **Action:** `Service Auth`
   - **Include rule:**
     - **Selector:** `Service Token`
     - **Value:** `D2M-MCP-Automation`

#### Step 6: Update Chromebook MCP Config

Update `~/.claude/mcp.json` on the Chromebook to include the service token headers:

```json
{
  "mcpServers": {
    "dreams2memories": {
      "url": "https://mcp.d2mluxury.quest/mcp",
      "headers": {
        "CF-Access-Client-Id": "<CLIENT_ID>",
        "CF-Access-Client-Secret": "<CLIENT_SECRET>"
      }
    }
  }
}
```

#### Step 7: Repeat for Other Endpoints (Recommended)

Apply the same Access application pattern to:

| Hostname | Priority | Notes |
|----------|----------|-------|
| `mcp.d2mluxury.quest` | **CRITICAL** | No app-layer auth at all |
| `api.d2mluxury.quest` | HIGH | Has bearer token, but defense-in-depth |
| `n8n.d2mluxury.quest` | MODERATE | Has built-in auth |
| `ssh.d2mluxury.quest` | LOW | SSH keys already strong |
| `portal.d2mluxury.quest` | LOW | Client-facing, magic link auth |

---

### Important Notes

- **Email allowlist:** If Gmail scanning is enabled, allowlist `noreply@notify.cloudflare.com` for OTP delivery
- **OTP expiry:** PINs expire after 10 minutes
- **CF_Authorization cookie:** After successful auth, Cloudflare sets a JWT cookie — subsequent requests don't re-prompt
- **No cloudflared restart needed:** Access policies are applied at Cloudflare's edge, not in the tunnel daemon
- **Alternative single-header auth:** Service tokens can be sent via a single `Authorization` header instead of two CF headers — configure `read_service_tokens_from_header` on the application if preferred

---

## PART 2: LASSO MCP GATEWAY EVALUATION

### What Is It

Lasso MCP Gateway (v1.2.1, MIT license) is a Python-based security proxy that sits between an LLM client and MCP servers. It intercepts all MCP tool calls and responses, applying configurable security plugins.

- **GitHub:** https://github.com/lasso-security/mcp-gateway
- **PyPI:** https://pypi.org/project/mcp-gateway/
- **Install:** `pip install mcp-gateway`
- **Python:** >=3.10
- **Status:** Beta (Development Status 4)

### Architecture

```
LLM Client (Claude CLI / Chromebook)
    ↓
Cloudflare Tunnel (mcp.d2mluxury.quest)
    ↓
[Cloudflare Access — perimeter auth]     ← NEW (this plan)
    ↓
[Lasso MCP Gateway — inspection proxy]  ← EVALUATED (this section)
    ↓
travel_mcp_server.py (localhost:8765)    ← EXISTING
```

Lasso would run as a local process on YOGA, proxying requests to the real MCP server. It reads an `mcp.json` config listing backend MCP servers and exposes itself as a single MCP endpoint.

### Security Plugin Matrix

| Plugin | PII Masking | Token/Secret Masking | Custom Policy | Prompt Injection Detection | Harmful Content Detection |
|--------|:-----------:|:--------------------:|:-------------:|:-------------------------:|:------------------------:|
| `basic` (free) | No | Yes | No | No | No |
| `presidio` (free, local) | Yes | No | No | No | No |
| `lasso` (requires API key) | Yes | Yes | Yes | Yes | Yes |

#### `basic` plugin (free, no API key)
- Masks: Azure secrets, GitHub tokens, GCP/AWS keys, JWT tokens, Slack webhooks, HuggingFace tokens
- Zero external dependencies

#### `presidio` plugin (free, local)
- Detects: credit cards, IP addresses, emails, phone numbers, SSNs
- Runs locally via Microsoft Presidio
- Install: `pip install mcp-gateway[presidio]`

#### `lasso` plugin (requires Lasso API key)
- Full stack: PII + secrets + prompt injection + harmful content + custom policy
- Calls Lasso's cloud API for real-time checking
- Requires signup at lasso.security

### Additional Features

- **Security scanner:** `mcp-gateway --scan` analyzes MCP servers for malicious tool descriptions and reputation risks
- **Audit logging:** `xetrack` plugin logs all tool calls to SQLite with timestamps, server names, capability names
- **Server reputation scoring:** GitHub/marketplace data analysis, blocks servers below score threshold of 30

### How It Would Be Configured for D2M

```json
{
  "mcpServers": {
    "mcp-gateway": {
      "command": "mcp-gateway",
      "args": [
        "--mcp-json-path", "/home/john/Thunderbird/mcp_backend.json",
        "-p", "basic", "presidio"
      ]
    }
  }
}
```

Where `mcp_backend.json` points to the real MCP server:

```json
{
  "mcpServers": {
    "dreams2memories": {
      "command": "python",
      "args": ["/home/john/Thunderbird/travel_mcp_server.py"]
    }
  }
}
```

### Verdict: Is Lasso Worth Adding?

**No — not at this time.** Here is the assessment:

| Factor | Assessment |
|--------|-----------|
| **Does it add auth?** | No. It assumes the transport layer handles auth. |
| **Does it add audit logging?** | Yes, via `xetrack` plugin (SQLite). But we can add logging to our own server trivially. |
| **Prompt injection detection?** | Only via paid `lasso` plugin (cloud API). Not useful for our single-user setup. |
| **PII masking?** | Useful for multi-tenant. We are single-user (Commander). Low value. |
| **Secret masking?** | `basic` plugin catches leaked tokens in responses. Moderate value. |
| **Complexity cost?** | Adds another process, another config file, another failure point. |
| **Maturity?** | Beta (v1.2.1). PyPI shows limited adoption. |

**Recommendation:** Cloudflare Access + bearer token auth on the MCP server itself provides stronger security with less complexity. Lasso adds value primarily for multi-tenant/enterprise scenarios where you need to inspect and sanitize traffic between untrusted LLM agents and MCP backends. For D2M's single-Commander architecture, the attack surface it addresses is already covered by:

1. **Cloudflare Access** — perimeter auth (who can reach the endpoint)
2. **Bearer token** — application auth (who can call tools)
3. **localhost binding** — network isolation (no direct access)
4. **`shell_exec` disabled** — capability restriction (no RCE even if breached)

**Revisit if:** D2M adds external agents, client-facing MCP endpoints, or multi-user access to the MCP server.

---

## PART 3: REMAINING HARDENING ACTIONS

### Priority 0: RESTART ALL SERVICES (CRITICAL)

The hardening script detected that all four services (ports 8765, 8766, 8780, 5678) are **still listening on 0.0.0.0** despite the code now defaulting to 127.0.0.1. The running processes predate the localhost binding fix and were never restarted.

**This means the services are directly reachable on the LAN (10.0.0.x) and via Tailscale, bypassing Cloudflare Access entirely.**

Fix:
```bash
# Restart MCP server (PID 769505)
# Restart REST API (PID 1314)
# Restart Portal (PID 712124)
# Restart n8n (PID 726055)
# Then verify with: ss -tlnp | grep -E ':(8765|8766|8780|5678)'
# All should show 127.0.0.1, not 0.0.0.0
```

### Priority 1: Add MCP Server Bearer Token Auth

The REST API (`thunderbird_api.py`) has `BearerTokenMiddleware`. The MCP server (`travel_mcp_server.py`) does **not**. This is the most important remaining gap.

Options:
1. Add ASGI middleware to FastMCP (similar pattern to `thunderbird_api.py`)
2. Use Cloudflare Access as the sole auth layer (acceptable if configured correctly)
3. Both (defense-in-depth — recommended)

### Priority 2: Cloudflare Access (This Document)

Execute Steps 1-7 above via the Cloudflare dashboard.

### Priority 3: Rotate API Token

After Cloudflare Access is live, rotate `.api_token` as a precaution:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))" > /home/john/Thunderbird/.api_token
chmod 600 /home/john/Thunderbird/.api_token
# Restart MCP and API servers
```

### Priority 4: Add `.cf_service_token` to .gitignore

Already handled in this session — see `.gitignore` update.

---

## OPTIONS

1. **Cloudflare Access only** — fast, zero code changes, covers all tunnel endpoints
2. **Cloudflare Access + MCP bearer token** — defense-in-depth, recommended
3. **Cloudflare Access + MCP bearer token + Lasso** — maximum layers, overkill for current scale

## ACTIONS I RECOMMEND TAKING

1. Execute Cloudflare Access Steps 1-7 via dashboard (30 minutes)
2. Add bearer token middleware to `travel_mcp_server.py` (separate task)
3. Store CF service token credentials in `/home/john/Thunderbird/.cf_service_token` with `chmod 600`
4. Update Chromebook `mcp.json` with CF service token headers
5. Test MCP connectivity from Chromebook after Access is enabled
6. Skip Lasso for now — revisit only if multi-user MCP access is needed

---

## SOURCES

- [Cloudflare Access — Self-Hosted Application Setup](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)
- [Cloudflare Access — Service Tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/)
- [Cloudflare Access — One-Time PIN Login](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- [Cloudflare Access — Access Policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)
- [Lasso MCP Gateway — GitHub](https://github.com/lasso-security/mcp-gateway)
- [Lasso MCP Gateway — PyPI](https://pypi.org/project/mcp-gateway/)
- [Lasso Security Press Release](https://www.businesswire.com/news/home/20250417840621/en/Lasso-Releases-First-Open-Source-Security-Gateway-for-MCP)

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, D2M Travel*
