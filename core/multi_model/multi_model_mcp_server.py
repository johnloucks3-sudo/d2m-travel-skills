#!/usr/bin/env python3
"""
multi_model_mcp_server.py
MCP server for multi-model orchestration - integrates with Thunderbird MCP system
"""

import json
import sys
import logging
from pathlib import Path

# Add Thunderbird core to path
sys.path.insert(0, '/home/john/Thunderbird')

from core.multi_model.multi_model_orchestrator import MultiModelOrchestrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MULTI-MODEL MCP] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/multi_model_mcp.log"),
        logging.StreamHandler()
    ]
)

class MultiModelMCPServer:
    def __init__(self):
        self.orchestrator = MultiModelOrchestrator()
        
    def handle_stdin(self):
        """Handle MCP requests via stdin/stdout"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request = json.loads(line.strip())
                response = self.handle_request(request)
                
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except Exception as e:
                logging.error(f"Error handling request: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {"code": -32000, "message": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
    
    def handle_request(self, request: dict) -> dict:
        """Handle individual MCP requests"""
        method = request.get("method")
        
        if method == "thos_persona_analysis":
            return self.orchestrator.mcp_handler(request)
        elif method == "list_tools":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "thos_persona_analysis",
                            "description": "Run THOS 10-persona analysis with COS Hale synthesis",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string", "description": "Analysis prompt for THOS personas"},
                                    "max_cost": {"type": "number", "description": "Max cost in dollars", "default": 0.05}
                                },
                                "required": ["prompt"]
                            }
                        }
                    ]
                }
            }
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "multi-model-orchestrator",
                        "version": "1.0.0"
                    }
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": "Method not found"}
            }

def main():
    """Main entry point for MCP server"""
    server = MultiModelMCPServer()
    
    # Test mode if called directly
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_prompt = "Test multi-model analysis for luxury travel"
        result = server.orchestrator.spectrum_analysis(test_prompt)
        print(json.dumps(result, indent=2))
    else:
        server.handle_stdin()

if __name__ == "__main__":
    main()