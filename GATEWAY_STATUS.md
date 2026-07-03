# LiteLLM Gateway Status — 2026-06-27

## Status: ❌ DISABLED (auth layer broken)

### Issue
- Gateway requires authentication but configuration is missing database backend
- Removing `master_key` causes LiteLLM to still enforce auth on health endpoint
- Auth handler incompatible with Prisma-less setup

### Workaround
**Use direct Anthropic (fully functional):**
```bash
pswitch a
```

### Gateway Restart (if needed)
```bash
systemctl --user restart d2m-litellm-gateway.service
```

### To Re-enable Gateway (requires one of):
1. **Full Prisma setup** — Configure SQLite database in litellm_config.yaml
2. **Upgrade LiteLLM** — Use newer version with fixed auth layer
3. **Auth via environment** — Use LITELLM_AUTH_DISABLE=true environment variable
4. **Alternative gateway** — Use max_proxy.py on port 5099 instead

### Current Config Location
`~/.claude/gateway/litellm_config.yaml`

### Service Control
```bash
systemctl --user status d2m-litellm-gateway
systemctl --user restart d2m-litellm-gateway
journalctl --user-unit d2m-litellm-gateway.service -n 20
```

### Why It's Disabled
- pswitch infrastructure allows easy provider switching via environment variables
- Direct Anthropic (pswitch a) works immediately without gateway complexity
- Gateway adds latency and complexity for zero benefit in current setup
- Free providers (Groq, Cerebras) routable via direct API calls instead

**Recommendation:** Keep gateway OFF. Use pswitch for provider switching.
