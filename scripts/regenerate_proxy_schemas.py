#!/usr/bin/env python3
"""
Regenerate proxy_schemas.json by starting each conditional server briefly.

Run this when:
  - A proxied server is updated (new tools added)
  - proxy_schemas.json is missing or corrupt
  - Adding a new server to the proxy

Usage:
  cd ~/Thunderbird
  python3 scripts/regenerate_proxy_schemas.py

  # Regenerate only specific servers:
  python3 scripts/regenerate_proxy_schemas.py apify firecrawl
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from thunderbird_mcp_proxy import (
    PROXY_SERVERS,
    SCHEMA_CACHE_PATH,
    SuspendedServer,
    build_schemas_for,
    load_schema_cache,
    save_schema_cache,
)


async def main():
    target_servers = sys.argv[1:] if len(sys.argv) > 1 else list(PROXY_SERVERS.keys())
    invalid = [n for n in target_servers if n not in PROXY_SERVERS]
    if invalid:
        print(f"Unknown servers: {invalid}. Valid: {list(PROXY_SERVERS.keys())}")
        sys.exit(1)

    print(f"Regenerating schemas for: {target_servers}")

    suspended = {
        name: SuspendedServer(name, PROXY_SERVERS[name])
        for name in target_servers
    }

    schemas = await build_schemas_for(target_servers, suspended)

    # Merge with existing cache (preserves untouched servers)
    existing = load_schema_cache()
    existing.update(schemas)
    save_schema_cache(existing)

    print(f"\nDone. Schema cache: {SCHEMA_CACHE_PATH}")
    total = sum(len(v) for v in schemas.values())
    for name, tools in schemas.items():
        print(f"  {name}: {len(tools)} tools")
    print(f"  Total: {total} tools proxied")


if __name__ == "__main__":
    asyncio.run(main())
