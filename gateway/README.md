# Thunderbird AI Gateway

OpenAI-compatible AI gateway built on LiteLLM Proxy v1.89.3.
Provides a single shared endpoint for all Wing agents — Claude Code, Codex CLI,
aider, AnythingLLM — connecting simultaneously to the same backend pool.

## Endpoint

```
http://localhost:4000/v1
```

Admin UI: `http://localhost:4000/ui`

## Model Aliases

| Alias | Backend | Cost | Notes |
|---|---|---|---|
| `travel-agent` | Claude Sonnet 4.6 | ~$3/M in | Primary; auto-fails over |
| `travel-agent-fast` | Claude Haiku 4.5 | ~$0.80/M in | Bulk/speed tasks |
| `claude-sonnet` | Anthropic direct | ~$3/M in | |
| `claude-haiku` | Anthropic direct | ~$0.80/M in | |
| `groq-llama` | Groq Llama-3.3-70B | Free | Fast |
| `groq-llama-fast` | Groq Llama-3.1-8B | Free | Very fast |
| `cerebras-llama` | Cerebras Llama-70B | Free (1M/mo) | |
| `grok` | xAI Grok | Paid | |
| `deepinfra-llama` | DeepInfra Llama-70B | Free | |
| `github-gpt4o-mini` | GitHub Models | Free | Azure-backed |

**Failover**: `travel-agent` → groq-llama → cerebras-llama → deepinfra-llama

## Required Environment Variables

Add to `/home/john/Thunderbird/.env`:

```env
LITELLM_MASTER_KEY=sk-tb-gateway-<generate-random>
LITELLM_UI_PASSWORD=<dashboard-password>
```

Active keys (already in .env): `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`,
`XAI_API_KEY`, `DEEPINFRA_API_KEY`, `GITHUB_TOKEN`.

## Start (foreground)

```bash
cd /home/john/Thunderbird/gateway
./start.sh
```

## Install as systemd service (persistent)

```bash
mkdir -p ~/.config/systemd/user
cp /home/john/Thunderbird/systemd/thunderbird-ai-gateway.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now thunderbird-ai-gateway
systemctl --user status thunderbird-ai-gateway
```

## Connect Any Agent

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000/v1",
    api_key="<LITELLM_MASTER_KEY>",
)
response = client.chat.completions.create(
    model="travel-agent",
    messages=[{"role": "user", "content": "Best cruise for Norwegian fjords?"}]
)
```

## Migration from thunderbird_llm_proxy.py

`thunderbird_llm_proxy.py` (port 3002, Groq-only) is superseded.
Update AnythingLLM: `http://localhost:3002/v1` → `http://localhost:4000/v1`, model → `groq-llama`.

## Audit & Cost

- SQLite log: `/home/john/Thunderbird/gateway/audit.db`
- Text log: `/home/john/Thunderbird/logs/ai_gateway.log`
- Dashboard: `http://localhost:4000/ui`
