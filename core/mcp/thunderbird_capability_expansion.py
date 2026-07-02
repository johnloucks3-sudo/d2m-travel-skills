"""MISSION-037–052: Capability Expansion MCP Tools.
Registered as Wave 4 in travel_mcp_server.py.
Provides: decision log, status brief, client memory cache, wing roster, session checkpoint.
"""
import json
import os
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "OpsCenter"))

from decision_log import query as decision_log_query
from ai_infra.client_memory_cache import get_client, set_client, list_clients
from ops.session_checkpoint import write_checkpoint, read_latest as read_checkpoints

def register_capability_tools(mcp):
    @mcp.tool(name="query_decision_log")
    async def query_decision_log(
        domain: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Query the append-only decision log. Returns recent decisions by domain or all."""
        try:
            results = decision_log_query(domain=domain, limit=limit)
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="get_client_memory")
    async def get_client_memory(client_key: str) -> str:
        """Retrieve cached travel DNA for a client by short name (e.g. 'kuklinski')."""
        try:
            c = get_client(client_key)
            if c:
                return json.dumps(dict(c), indent=2, default=str)
            return json.dumps({"status": "not_found", "client_key": client_key})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="set_client_memory")
    async def set_client_memory(
        client_key: str,
        travel_dna: str,
        preferences: str = "{}",
        comm_style: str = "{}",
        decision_patterns: str = "{}",
        red_flags: str = "[]",
        source_dossier: str = ""
    ) -> str:
        """Store or update client travel DNA cache. All JSON fields as strings."""
        try:
            ts = set_client(
                client_key=client_key,
                travel_dna=json.loads(travel_dna) if isinstance(travel_dna, str) else travel_dna,
                preferences=json.loads(preferences),
                comm_style=json.loads(comm_style),
                decision_patterns=json.loads(decision_patterns),
                red_flags=json.loads(red_flags),
                source_dossier=source_dossier
            )
            return json.dumps({"status": "saved", "client_key": client_key, "updated": ts})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="list_client_cache")
    async def list_client_cache() -> str:
        """List all clients in the memory cache with last-updated timestamps."""
        try:
            clients = list_clients()
            return json.dumps(clients, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="write_session_checkpoint")
    async def write_session_checkpoint(
        task: str,
        files_modified: str = "[]",
        decisions_made: str = "[]",
        next_step: str = ""
    ) -> str:
        """Write a session continuity checkpoint. Call every 15 min during builds."""
        try:
            cp = write_checkpoint(
                task=task,
                files_modified=json.loads(files_modified),
                decisions_made=json.loads(decisions_made),
                next_step=next_step
            )
            return json.dumps({"status": "checkpoint_written", "ts": cp["ts"]})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(name="read_session_checkpoints")
    async def read_session_checkpoints(n: int = 3) -> str:
        """Read the last N session checkpoints for context recovery."""
        try:
            cps = read_checkpoints(n=n)
            return json.dumps(cps, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})
