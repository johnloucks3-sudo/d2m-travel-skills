# Graphiti Self-Host Runbook
## Temporal-Entity Memory Layer for Thunderbird Wing
*Companion to Qdrant semantic recall · Single-box deployment (Lenovo Yoga, Linux)*

---

## 1. WHAT IS GRAPHITI & WHY LAYER WITH QDRANT

**Graphiti** (github.com/getzep/graphiti) is a temporal knowledge graph engine that stores **facts with time bounds** and entity relationships as a property graph. It answers "what happened to [entity] during [timeframe]?" with crisp facts, not semantic similarity.

**Qdrant** (already at 127.0.0.1:6333) is a **vector database** — it stores semantic embeddings and returns "things similar to X" via cosine distance.

**Why both?**
- Qdrant: *"Find memories about 'Spencer flight pricing'" → returns semantically similar past briefs, decisions, intel summaries*
- Graphiti: *"What facts do we know about Erik McLeod between Jun 1 – Jul 1 2026?" → returns birth, bookings, FPD dates, contact history, payment events as a timeline*

They **complement, not compete**. Graphiti is structured (facts + timestamps + entity links); Qdrant is associative (semantic clustering). Together: precise recall + semantic discovery.

---

## 2. BACKEND CHOICE: NEO4J VS FALKORDB

**For single-box (Yoga, 16GB RAM shared with Qdrant + MCP stack):**

**RECOMMEND: FalkorDB** (lighter footprint)
- **Memory:** ~200–400MB base, scales with graph size (Thunderbird: ~500 entities, few thousand facts = ~800MB–1.2GB active)
- **CPU:** Single-threaded ops; scales to 4 cores under load
- **Disk:** ~2–5GB after 12 months of operation (fact accumulation)
- **License:** SSPL (source-available; commercial terms available)
- **Why:** Redis-module design; no separate JVM; runs beside Qdrant without memory contention

**Alternative: Neo4j**
- **Memory:** ~1–2GB minimum (JVM overhead), grows faster
- **CPU:** Lighter ops, but JVM startup + GC pauses visible
- **Disk:** Larger (same data = 1.5x FalkorDB size)
- **Why skip:** Already running Ollama (500MB) + Qdrant (800MB) + Infisical (1GB) + Camofox/SearXNG; Neo4j's JVM adds memory pressure at session boundaries

**Decision:** FalkorDB. Run as Docker container; expose port 6379 (Redis API).

---

## 3. DOCKER-COMPOSE STEPS FOR FALKORDB

**File:** `/home/john/Thunderbird/docker/docker-compose.graphiti.yml`

```yaml
version: '3.8'

services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: falkordb
    ports:
      - "127.0.0.1:6379:6379"
    environment:
      # FalkorDB runs on Redis protocol; no additional config needed
      - SAVEDB=yes
    volumes:
      - falkordb_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  falkordb_data:
    driver: local
```

**Launch:**
```bash
cd /home/john/Thunderbird/docker
docker-compose -f docker-compose.graphiti.yml up -d
docker ps | grep falkordb
```

**Verify:**
```bash
redis-cli -p 6379 ping
# Expected: PONG
```

**Persistence:** FalkorDB persists to `/data` volume (docker volume `thunderbird_falkordb_data`).

---

## 4. INSTALL & RUN GRAPHITI MCP SERVER

**GitHub:** github.com/getzep/graphiti · **MCP:** github.com/getzep/graphiti-mcp

**Install Graphiti MCP server locally:**

```bash
# Clone + install
cd /opt/graphiti-mcp
git clone https://github.com/getzep/graphiti-mcp.git .
npm install

# Create .env (point to FalkorDB)
cat > /opt/graphiti-mcp/.env << 'DOTENV'
GRAPHITI_REDIS_HOST=127.0.0.1
GRAPHITI_REDIS_PORT=6379
GRAPHITI_REDIS_DB=0
GRAPHITI_API_PORT=3000
DOTENV

# Start MCP server
npm start
# Expected output: "Graphiti MCP server listening on port 3000"
```

**Systemd service** (optional, for auto-start):

```ini
[Unit]
Description=Graphiti MCP Server
After=docker.service falkordb.service
Wants=falkordb.service

[Service]
Type=simple
WorkingDirectory=/opt/graphiti-mcp
ExecStart=/usr/bin/node /opt/graphiti-mcp/dist/index.js
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Save as:** `/etc/systemd/system/graphiti-mcp.service`

```bash
sudo systemctl daemon-reload
sudo systemctl enable graphiti-mcp.service
sudo systemctl start graphiti-mcp.service
systemctl status graphiti-mcp.service
```

---

## 5. REGISTER GRAPHITI MCP IN CLAUDE CODE & OPENCODE

### Claude Code (Claude Settings JSON)

**File:** `~/.claude/mcp.json` (or via Claude Web Settings → MCP → Add Server)

```json
{
  "mcpServers": {
    "graphiti": {
      "command": "node",
      "args": ["/opt/graphiti-mcp/dist/index.js"],
      "env": {
        "GRAPHITI_REDIS_HOST": "127.0.0.1",
        "GRAPHITI_REDIS_PORT": "6379"
      }
    }
  }
}
```

**Restart Claude Code** (kill + relaunch in VS Code).

**Verify in Claude Code terminal:**
```bash
mcp call graphiti ping
# Expected: { "status": "ok", "timestamp": "2026-07-02T..." }
```

### OpenCode (opencode.json)

**File:** `~/.opencode/opencode.json` (or project root `opencode.json`)

```json
{
  "mcp": {
    "graphiti": {
      "command": "node",
      "args": ["/opt/graphiti-mcp/dist/index.js"],
      "env": {
        "GRAPHITI_REDIS_HOST": "127.0.0.1",
        "GRAPHITI_REDIS_PORT": "6379"
      }
    }
  }
}
```

**Restart OpenCode daemon:**
```bash
opencode --stop
sleep 2
opencode --start
opencode status
```

---

## 6. SMOKE TEST: WRITE FROM ONE ENGINE, READ FROM THE OTHER

**From Claude Code terminal:**

```bash
# Write a fact: Erik McLeod booked Regent Grandeur on 2026-06-01
mcp call graphiti add_fact \
  --entity "Erik_McLeod_Grandeur_2984034" \
  --fact "Booking reference: 2984034 | Ship: Regent Grandeur | Departure: 19-Dec-2026" \
  --timestamp "2026-06-01T00:00:00Z" \
  --metadata '{"client":"McLeod","ship":"Regent","fpd":"2026-07-22"}'

# Expected response: { "fact_id": "f_abc123...", "stored": true }
```

**From OpenCode terminal:**

```bash
# Read the fact back
opencode mcp graphiti query_entity --entity "Erik_McLeod_Grandeur_2984034"

# Expected: timeline of facts with timestamps
```

**If both return data:** ✅ Shared memory is live.

---

## 7. RISKS & CAVEATS FOR SINGLE-BOX

| Risk | Mitigation |
|------|-----------|
| **Memory contention** (Qdrant + Ollama + FalkorDB + MCP stack) | Monitor `free -h` hourly; set Docker swap limits per container. Alert if <2GB free. |
| **FalkorDB persistence lag** | Sync-to-disk every 60s by default; data loss = ~1 min of facts if host crashes. Acceptable for transient operational data. |
| **No HA/failover** | Single box = no replication. Backup FalkorDB volume weekly: `docker run --rm -v thunderbird_falkordb_data:/data -v /backup:/backup ubuntu cp -r /data /backup/falkordb_$(date +%Y%m%d)`. |
| **Graph query complexity** | Graphiti queries scale O(n) with entity count. Thunderbird: <5K entities = <50ms per query. Monitor `/opt/graphiti-mcp/logs/` for slowness. |
| **Redis port collision** | Port 6379 is FalkorDB (Redis-compatible). Ensure no other Redis instance running on same port. |

**Backup cron (add to ~/.local/share/cron/crontab):**
```
0 2 * * 0 docker run --rm -v thunderbird_falkordb_data:/data -v /mnt/backup:/backup ubuntu bash -c 'cp -r /data /backup/falkordb_'$(date +\%Y\%m\%d)' && find /backup -name falkordb_* -mtime +30 -exec rm -rf {} \;'
```

---

## NEXT STEPS (Post-Deployment)

1. **Integrate fact-write into lifecycle:** Dani/Hale lifecycle touchpoint sends → auto-log facts to Graphiti (e.g., "TP 1.1 sent to Erik McLeod" as a fact with timestamp)
2. **Temporal queries in briefs:** Morning brief includes "McLeod facts since 2026-06-01" (timeline of all interactions)
3. **Entity linking:** Link clients ↔ bookings ↔ FPDs as edges; query "what bookings are at FPD risk in 14 days" as a Graphiti traversal
4. **Sync Qdrant + Graphiti:** On fact-write to Graphiti, embed fact-text + send to Qdrant (structured fact becomes searchable embedding)

---

**Owner:** Hale (COS) · **Maintenance:** Sterling (A7) · **Monitor:** CI daily (`scripts/ci_daily_routine.py`)

*Runbook v1.0 · 2026-07-02 · Thunderbird Wing*
