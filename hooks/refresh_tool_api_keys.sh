#!/bin/bash
# refresh_tool_api_keys.sh — Sync current Claude MAX OAuth token to Goose + Aider configs
# Run on: system timer, Claude Code hook, or manually after Claude Desktop auth refresh

set -euo pipefail

CREDS_FILE="${HOME}/.claude/.credentials.json"
GOOSE_CONFIG="${HOME}/.config/goose/config.yaml"
AIDER_CONFIG="${HOME}/.aider.conf.yml"

if [[ ! -f "$CREDS_FILE" ]]; then
    echo "[refresh_tool_api_keys] CREDS not found: $CREDS_FILE" >&2
    exit 1
fi

TOKEN=$(python3 -c "
import json, sys
c = json.loads(open('$CREDS_FILE').read())
t = c.get('claudeAiOauth', {}).get('accessToken', '')
if not t:
    sys.exit(1)
print(t)
" 2>/dev/null)

if [[ -z "$TOKEN" ]]; then
    echo "[refresh_tool_api_keys] No token in credentials file" >&2
    exit 1
fi

# Update Goose config.yaml (ANTHROPIC_API_KEY line)
if [[ -f "$GOOSE_CONFIG" ]]; then
    python3 - "$GOOSE_CONFIG" "$TOKEN" << 'PYEOF'
import sys, re
cfg_path, token = sys.argv[1], sys.argv[2]
with open(cfg_path) as f:
    content = f.read()
updated = re.sub(
    r"^(ANTHROPIC_API_KEY:\s*')[^']*(')",
    f"\\g<1>{token}\\g<2>",
    content, flags=re.MULTILINE
)
if updated == content:
    # Try without quotes
    updated = re.sub(
        r"^(ANTHROPIC_API_KEY:\s*)(\S+)",
        f"\\g<1>'{token}'",
        content, flags=re.MULTILINE
    )
with open(cfg_path, 'w') as f:
    f.write(updated)
print(f"[refresh_tool_api_keys] Goose updated")
PYEOF
fi

# Update Aider config (anthropic-api-key line)
if [[ -f "$AIDER_CONFIG" ]]; then
    python3 - "$AIDER_CONFIG" "$TOKEN" << 'PYEOF'
import sys, re
cfg_path, token = sys.argv[1], sys.argv[2]
with open(cfg_path) as f:
    content = f.read()
updated = re.sub(
    r"^(anthropic-api-key:\s*).*$",
    f"\\g<1>{token}",
    content, flags=re.MULTILINE
)
with open(cfg_path, 'w') as f:
    f.write(updated)
print(f"[refresh_tool_api_keys] Aider updated")
PYEOF
fi

echo "[refresh_tool_api_keys] Done — token refreshed in Goose + Aider"
