#!/bin/bash
# refresh_aider_goose_token.sh
# Reads current Claude MAX OAuth token from credentials.json
# Updates goose config.yaml and ~/.aider.conf.yml
# Run as cron or after Claude Code session start

CREDS="/home/john/.claude/.credentials.json"
GOOSE_CONFIG="/home/john/.config/goose/config.yaml"
AIDER_CONFIG="/home/john/.aider.conf.yml"

if [[ ! -f "$CREDS" ]]; then
  echo "[$(date)] ERROR: credentials.json not found" >&2
  exit 1
fi

TOKEN=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['claudeAiOauth']['accessToken'])")
EXPIRES=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['claudeAiOauth']['expiresAt'])")

if [[ -z "$TOKEN" ]]; then
  echo "[$(date)] ERROR: empty token" >&2
  exit 1
fi

# Update goose config.yaml
python3 - "$GOOSE_CONFIG" "$TOKEN" << 'PYEOF'
import sys, re
config_path, token = sys.argv[1], sys.argv[2]
content = open(config_path).read()
content = re.sub(r"ANTHROPIC_API_KEY: '.*?'", f"ANTHROPIC_API_KEY: '{token}'", content)
open(config_path, 'w').write(content)
print(f"[goose] ANTHROPIC_API_KEY updated")
PYEOF

# Update aider config
python3 - "$AIDER_CONFIG" "$TOKEN" << 'PYEOF'
import sys, re
config_path, token = sys.argv[1], sys.argv[2]
content = open(config_path).read()
content = re.sub(r"anthropic-api-key: .*", f"anthropic-api-key: {token}", content)
open(config_path, 'w').write(content)
print(f"[aider] anthropic-api-key updated")
PYEOF

echo "[$(date)] Token refreshed. Expires: $EXPIRES"
