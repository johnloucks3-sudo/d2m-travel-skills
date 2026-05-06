
# Auto-generated skill: flight_lookup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("flight_lookup")

@mcp.tool()
def execute_flight_lookup(query: str):
    """A tool to look up flight prices"""
    return f"Executed flight_lookup with: {query}"
