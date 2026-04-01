
import os
import sys
import json
import subprocess
import time

# Ensure project root is on path for venv and modules
project_root = "/home/john/Thunderbird/"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Path to the Goose Slim MCP server
GOOSE_MCP_SERVER_PATH = os.path.join(project_root, "goose_mcp_server.py")
PYTHON_VENV_PATH = os.path.join(project_root, ".venv", "bin", "python")

def call_mcp_tool(tool_name: str, tool_args: dict) -> dict:
    """Calls an MCP tool via the Goose Slim MCP server using stdio JSON-RPC."""
    # 1. Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "Goose MCP Client",
                "version": "1.0"
            }
        },
        "id": 0
    }

    # 2. Tool call request
    tool_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_args
        },
        "id": 1
    }

    # Combine requests, separated by a newline
    combined_input = json.dumps(init_request) + "\n" + json.dumps(tool_request) + "\n"

    try:
        # Execute the MCP server script and pipe combined input to its stdin
        # Use the venv python directly
        process = subprocess.run(
            [PYTHON_VENV_PATH, GOOSE_MCP_SERVER_PATH, "--stdio"],
            input=combined_input,
            capture_output=True,
            text=True,
            check=False, # Do not raise exception for non-zero exit code initially
            timeout=30 # Timeout for the MCP server response
        )

        # Process responses
        responses = process.stdout.strip().split('\n')
        parsed_responses = []
        for resp_str in responses:
            if resp_str:
                try:
                    parsed_responses.append(json.loads(resp_str))
                except json.JSONDecodeError as e:
                    # Log non-JSON output from MCP server, e.g., FastMCP startup messages
                    sys.stderr.write(f"[goose_mcp_client] Non-JSON output from MCP server: {resp_str.strip()}\n")

        if process.stderr:
            sys.stderr.write(f"[goose_mcp_client] MCP server STDERR: {process.stderr}\n")

        # Find the tool call result (id=1)
        tool_call_result = next((r for r in parsed_responses if r.get("id") == 1 and "result" in r), None)
        
        if tool_call_result and "result" in tool_call_result:
            # The result is typically a JSON string from the Python tool wrapper
            return json.loads(tool_call_result["result"])
        elif tool_call_result and "error" in tool_call_result:
            return {"status": "error", "message": tool_call_result["error"]}
        else:
            return {"status": "error", "message": "No valid tool call result found.", "raw_stdout": process.stdout, "raw_stderr": process.stderr}

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "MCP server command timed out."}
    except FileNotFoundError:
        return {"status": "error", "message": f"Python venv or MCP server script not found. Check paths: {PYTHON_VENV_PATH}, {GOOSE_MCP_SERVER_PATH}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: python3 goose_mcp_client.py <tool_name> <json_tool_args>\n")
        sys.exit(1)

    tool_name = sys.argv[1]
    try:
        tool_args = json.loads(sys.argv[2])
    except json.JSONDecodeError:
        sys.stderr.write(f"Invalid JSON for tool arguments: {sys.argv[2]}\n")
        sys.exit(1)

    result = call_mcp_tool(tool_name, tool_args)
    print(json.dumps(result, indent=2))