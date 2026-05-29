#!/bin/bash
# MCP Health Check — monitors Thunderbird MCP server
# Usage: ./mcp_health_check.sh
# Exit: 0 = healthy, 1 = unhealthy

SERVICE="thunderbird-mcp.service"
PORT=8765
HOST="127.0.0.1"

# Check if service is active
if ! systemctl --user is-active --quiet "$SERVICE"; then
    echo "FAIL: Service $SERVICE is not active"
    exit 1
fi

# Check if port is listening via Python (reliable across systems)
python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('$HOST', $PORT))
    s.close()
    if result == 0:
        exit(0)
    else:
        print('FAIL: Cannot connect to $HOST:$PORT')
        exit(1)
except Exception as e:
    print(f'FAIL: {e}')
    exit(1)
" || exit 1

echo "OK: MCP server healthy (service active, port listening)"
exit 0
