# Infrastructure Fix Campaign — Teaching Manual
**2026-05-22** | Hale (JET/OpenCode) | Campaign: MISSION-056, 057, 058

---

## MISSION-057: MCP Import Path Shadowing

### Problem
`from mcp.server.fastmcp import FastMCP` in `core/mcp/travel_mcp_server.py` raised `ModuleNotFoundError` because the directory `core/mcp/` (which has an `__init__.py`) shadows the installed `mcp` pip package at `/home/john/.local/lib/python3.13/site-packages/mcp/`.

### Root Cause
Python's import resolution: when `core/` is on `PYTHONPATH` and the script directory is `core/mcp/`, `sys.path[0]` = the script directory = `core/mcp/`. Python finds `core/mcp/` (with `__init__.py`) as the `mcp` package BEFORE it finds the installed `mcp` in site-packages.

Also, `mcp_launcher_core.sh` included `core/mcp/` in PYTHONPATH explicitly (line 22), which meant it appeared TWICE in sys.path.

### Fix
Added a sys.path reorder at the top of `travel_mcp_server.py` (lines 117-124):
```python
# Fix import shadowing: core/mcp/ directory shadows the installed mcp pip package.
_site_dir = None
for _p in list(sys.path):
    if 'site-packages' in _p and _p not in sys.path[:1]:
        _site_dir = _p
        sys.path.remove(_p)
        sys.path.insert(0, _p)
        break
```

This moves site-packages to `sys.path[0]`, so the installed `mcp` package resolves before `core/mcp/`.

### Alternative Approaches Considered
1. **Rename `core/mcp/` to `core/mcp_tools/`** — rejected because 84+ references across the codebase would need updating
2. **Remove `core/mcp/` from PYTHONPATH** — rejected because it's still at sys.path[0] as script directory
3. **Add site-packages before script dir in launcher** — not portable across environments

### Verification
```python
python3 -c "
import sys
sys.path.insert(0, '/home/john/Thunderbird/core/mcp')
# Apply fix
for _p in list(sys.path):
    if 'site-packages' in _p and _p not in sys.path[:1]:
        sys.path.remove(_p)
        sys.path.insert(0, _p)
        break
from mcp.server.fastmcp import FastMCP
print('OK:', FastMCP)
"
```
Output: `OK: <class 'mcp.server.fastmcp.server.FastMCP'>`

### Key Insight
The installed `mcp` package's path is `/home/john/.local/lib/python3.13/site-packages/mcp/`. The project's `core/mcp/` directory only needs to be on sys.path for flat imports from files within that directory. Since `travel_mcp_server.py` IS the script being executed, its directory is always at sys.path[0]. The fix ensures site-packages takes priority for the `mcp` name.

---

## MISSION-056: n8n Drive-Upload Webhook (HTTP 500)

### Problem
`POST /webhook/drive-upload` returned HTTP 500 with:
```json
{"code":0,"message":"No Respond to Webhook node found in the workflow"}
```

### Root Cause
n8n v2.12.3 has a bug with `responseMode: "responseNode"` — the webhook handler at `webhook-helpers.ts:554` searches for `n8n-nodes-base.respondToWebhook` nodes in the workflow but fails to find them, even though they clearly exist in the DB and API responses. The nodes are properly saved in the `workflow_entity.nodes` column with type `n8n-nodes-base.respondToWebhook`, and the API returns them correctly. But the webhook executor uses a different code path that doesn't find them.

### Fix
Changed webhook trigger `responseMode` from `"responseNode"` to `"lastNode"`:

```python
# Python via n8n public API
for n in wf['nodes']:
    if n.get('type') == 'n8n-nodes-base.webhook':
        n['parameters']['responseMode'] = 'lastNode'
```

Then saved via PUT + deactivate/activate cycle:
```bash
# GET current workflow
curl -s http://localhost:5678/api/v1/workflows/{id} -H "X-N8N-API-KEY: $KEY"
# PUT updated workflow (exclude active — it's read-only via API)
curl -s -X PUT http://localhost:5678/api/v1/workflows/{id} -H "X-N8N-API-KEY: $KEY" -d '{...}'
# Deactivate/reactivate to re-register webhook
curl -s -X POST http://localhost:5678/api/v1/workflows/{id}/deactivate -H "X-N8N-API-KEY: $KEY"
curl -s -X POST http://localhost:5678/api/v1/workflows/{id}/activate -H "X-N8N-API-KEY: $KEY"
```

### n8n Authentication Discovery
- **Public API** (not REST API): `http://localhost:5678/api/v1/*` with `X-N8N-API-KEY` header
- **REST/Internal API** (`/rest/*`): requires cookie/session auth, no API key
- The key in `.env` is the PUBLIC API key (aud: "public-api")
- API key stored in `user_api_keys` SQLite table with scope: workflow CRUD, activate/deactivate

### n8n Version
v2.12.3 — significantly behind latest stable (v2.20.7+). Security advisories from May 2026 flagged Critical RCE vulnerabilities. **Recommend upgrading.**

### Webhook Registration
Webhooks are registered in `webhook_entity` SQLite table when a workflow with a webhook trigger is activated. The route is the webhook path:
- Entry: `(workflow_id, path, method, node_name, ...)`
- Activation is the trigger for registration

### Alternative
Standalone upload script exists at `scripts/drive_upload_robust.py` — bypasses n8n entirely using direct googleapiclient. This is the fallback if n8n remains unreliable.

---

## MISSION-058: Agent Silent Failure Retry Pattern

### Problem
Some task dispatches (especially with cheap models like Kimi K2 or Poe Haiku) return empty or fail silently — no output, no error. Example: Silver Ray scan returned empty with no error trace.

### Fix
Added `_spawn_with_retry()` wrapper to `spawn_headless_claude` in `core/ai_infra/thunderbird_headless_spawn.py`:

**Retry behavior:**
- Maximum 3 attempts (initial + 2 retries)
- Retry triggers: TimeoutExpired, SpawnFailed, SilentFailure (output file empty)
- Fatal errors (binary not found, creds missing): no retry, fail fast
- Model escalation on each retry: haiku → sonnet → opus
- Task name gets `_retry1`, `_retry2` suffix for log traceability

**Code structure:**
```python
def _spawn_with_retry(prompt, output_path, log_file, model, task_name, env, timeout, usage_file, retries=2, attempt=1):
    result = _spawn_synchronous(...)
    if result.get("status") == "COMPLETED":
        if output exists and non-empty:
            return result
        else:
            result = {"status": "SILENT_FAILURE", "can_retry": True}
    if result.get("can_retry") and attempt <= retries:
        # escalate model tier
        return _spawn_with_retry(..., attempt + 1)
    return result
```

### Key Design Decisions
1. **Background mode not retried** — can't know completion state without polling; caller responsibility
2. **Model escalation** — matches compact doctrine: retry with a smarter model
3. **3 attempts max** — prevent infinite loops, match compact's "3 retries then escalate"
4. **Output verification** — catches silent failures by checking file size > 0

---

## Infrastructure Automation Patterns

### Pattern 1: Always test the API before assuming
The n8n issue showed that the file on disk (`workflows/n8n_drive_upload.json`) had correct nodes, but the ACTIVE workflow in n8n was different. Always test the live system, not the config files.

### Pattern 2: n8n API vs REST API
n8n has two API surfaces with different auth:
| Surface | Path Prefix | Auth |
|---------|-------------|------|
| Public API | `/api/v1/` | `X-N8N-API-KEY` header |
| Internal REST | `/rest/` | Cookie/session only |

Check `user_api_keys` table in SQLite to find valid keys.

### Pattern 3: sys.path shadowing is silent
`sys.path[0]` (script directory) always takes priority. If a script directory name matches a pip package name, Python silently shadows the package. Diagnosis:
```python
python3 -c "import mcp; print(mcp.__file__)"
```
If it shows a project path instead of site-packages, shadowing is happening.

### Pattern 4: Webhook registration != webhook execution
In n8n, webhook registration (webhook_entity table) and webhook execution (workflow resolution) are separate code paths. A webhook can be registered but fail execution if the workflow structure isn't compatible with the response mode.
