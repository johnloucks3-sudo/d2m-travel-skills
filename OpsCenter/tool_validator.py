#!/usr/bin/env python3
import json
import logging
import subprocess

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [A7 AUDIT] - %(message)s')

def validate_tools():
    logging.info("STARTING PRIORITY 2: MCP TOOL VALIDATION SWEEP")
    
    tools_to_test = [
        "get_port_city_intel",
        "tess_list_clients",
        "search_hotels"
    ]
    
    success_count = 0
    for tool in tools_to_test:
        cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh", 
            tool, 
            json.dumps({}) # Empty payload for dry-run
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if "error" not in res.stdout.lower() and "failed" not in res.stdout.lower():
                success_count += 1
                logging.info(f"Tool {tool} - PASS")
            else:
                logging.warning(f"Tool {tool} - FAIL/WARN: {res.stdout[:100]}")
        except Exception as e:
            logging.error(f"Tool {tool} - TIMEOUT/CRASH: {e}")
            
    logging.info(f"PRIORITY 2 SWEEP COMPLETE. {success_count}/{len(tools_to_test)} Tools Validated.")

if __name__ == "__main__":
    validate_tools()

