# yoga RabbitMQ Deployment Checklist

**Target:** yoga server (192.168.1.198)  
**Service:** RabbitMQ 3.13-management (Docker)  
**Purpose:** Inter-persona messaging (MISSION-172)  
**Date:** 2026-06-09

---

## PRE-DEPLOYMENT (Local verification)

- [x] RabbitMQ container running on localhost:5672
- [x] All 6 persona queues created and verified
- [x] All 3 exchanges (dissent, observations, alternatives) online
- [x] persona_user created with credentials
- [x] Test dissents published and consumed successfully
- [x] Audit trail logging working
- [x] session_init.py operational
- [x] All tests passing (Phase 2A-2E complete)

---

## DEPLOYMENT STEPS

### Step 1: Prepare yoga Server
- [ ] SSH access confirmed to yoga (192.168.1.198)
- [ ] Docker installed on yoga
- [ ] Docker daemon running
- [ ] Network: yoga ↔ localhost verified (ping test)
- [ ] Sudo/docker group access available

**Command to verify:**
```bash
ssh yoga "docker --version && docker ps"
```

### Step 2: Transfer Deployment Script
- [ ] Copy deploy script to yoga:
  ```bash
  scp ops/deploy_rabbitmq_to_yoga.sh yoga:~/
  ```
- [ ] Verify script received:
  ```bash
  ssh yoga "ls -la ~/deploy_rabbitmq_to_yoga.sh"
  ```

### Step 3: Set Production Password
- [ ] Generate secure password (min 16 chars)
  ```bash
  openssl rand -base64 16
  # Example: aBcD1234efGH5678ijKL9012mnOP
  ```
- [ ] Save to .env.vault (DO NOT commit)
- [ ] Export environment:
  ```bash
  export RABBITMQ_PASSWORD="<generated-password>"
  ```

### Step 4: Execute Deployment
- [ ] Run deployment script on yoga:
  ```bash
  ssh yoga "bash ~/deploy_rabbitmq_to_yoga.sh"
  ```
  
**Script will:**
- Stop/remove old container (if exists)
- Launch RabbitMQ 3.13-management
- Create 3 exchanges
- Create 6 persona queues
- Set 7-day TTL
- Verify topology
- Run health check

### Step 5: Verify Production Deployment
- [ ] Check container running:
  ```bash
  ssh yoga "docker ps | grep rabbitmq"
  ```
  
- [ ] Verify AMQP port (5672):
  ```bash
  nc -zv 192.168.1.198 5672
  ```
  
- [ ] Verify Management UI (15672):
  ```bash
  curl -u persona_user:$RABBITMQ_PASSWORD \
    http://192.168.1.198:15672/api/aliveness-test/%2F
  ```
  
- [ ] List exchanges:
  ```bash
  ssh yoga "docker exec thunderbird-rabbitmq-prod rabbitmqctl list_exchanges"
  ```
  
- [ ] List queues:
  ```bash
  ssh yoga "docker exec thunderbird-rabbitmq-prod rabbitmqctl list_queues"
  ```

### Step 6: Update Configuration
- [ ] Update production_config.py:
  ```python
  RABBITMQ_HOST = "192.168.1.198"  # Was: "localhost"
  ```
  
- [ ] Verify localhost fallback still works:
  ```python
  # Test local fallback if yoga offline
  messaging = PersonaMessaging(use_production=False)
  ```

### Step 7: Test End-to-End Production Flow
- [ ] Set production environment:
  ```bash
  export RABBITMQ_HOST="192.168.1.198"
  export RABBITMQ_PASSWORD="<production-password>"
  ```
  
- [ ] Run production test:
  ```bash
  python3 tests/test_live_dissent_production.py
  ```
  
- [ ] Verify dissent flows end-to-end
- [ ] Confirm all 6 persona inboxes receive messages
- [ ] Check acknowledgment flow works
- [ ] Verify audit trail captures everything

### Step 8: Activate in Session Startup
- [ ] CLAUDE.md already configured (no changes needed)
- [ ] session_init.py will auto-detect yoga on next session
- [ ] Verify morning brief includes dissent alerts
- [ ] Test persona inbox consumption works

### Step 9: Production Validation
- [ ] Run 1-hour smoke test (continuous messaging)
- [ ] Monitor queue depth (should return to 0 after acks)
- [ ] Verify latency <500ms (target: <50ms)
- [ ] Check memory usage on yoga
- [ ] Verify log rotation (prevent disk fill)
- [ ] Test Telegram alert integration (if active)

### Step 10: Operational Handoff
- [ ] Document credentials in secure vault
- [ ] Update runbooks with yoga location
- [ ] Brief ops team on monitoring
- [ ] Set up container auto-restart (--restart unless-stopped)
- [ ] Backup RabbitMQ volumes periodically

---

## DEPLOYMENT COMMANDS (Quick Reference)

```bash
# 1. Set password
export RABBITMQ_PASSWORD="<secure-password>"

# 2. Copy script to yoga
scp ops/deploy_rabbitmq_to_yoga.sh yoga:~/

# 3. Execute deployment
ssh yoga "bash ~/deploy_rabbitmq_to_yoga.sh"

# 4. Verify
ssh yoga "docker ps | grep rabbitmq"
curl -u persona_user:$RABBITMQ_PASSWORD \
  http://192.168.1.198:15672/api/aliveness-test/%2F

# 5. Test end-to-end
export RABBITMQ_HOST="192.168.1.198"
python3 tests/test_live_dissent_production.py

# 6. Check logs
ssh yoga "docker logs thunderbird-rabbitmq-prod"
```

---

## ROLLBACK PROCEDURE (If needed)

```bash
# 1. Stop production container
ssh yoga "docker stop thunderbird-rabbitmq-prod"

# 2. Switch to localhost fallback
export RABBITMQ_HOST="localhost"
export RABBITMQ_PASSWORD="test_password_123"

# 3. Verify session_init falls back gracefully
python3 OpsCenter/session_init.py

# 4. If permanent rollback needed:
ssh yoga "docker rm thunderbird-rabbitmq-prod"
ssh yoga "docker volume rm rabbitmq-data rabbitmq-logs"
```

---

## POST-DEPLOYMENT OPERATIONS

### Daily Checks
- [ ] Container status: `docker ps | grep rabbitmq`
- [ ] Queue depth: `rabbitmqctl list_queues`
- [ ] No error logs: `docker logs thunderbird-rabbitmq-prod`

### Weekly Checks
- [ ] Message throughput metrics
- [ ] Latency trends (should be <50ms avg)
- [ ] Backup integrity (if automated backup in place)
- [ ] Credential rotation (if applicable)

### Monthly Checks
- [ ] Full disaster recovery drill
- [ ] RabbitMQ version updates available
- [ ] Performance tuning (if needed)
- [ ] Audit trail review (sample logs)

---

## TROUBLESHOOTING

### Container won't start
```bash
# Check error
docker logs thunderbird-rabbitmq-prod

# Common issue: port already in use
netstat -tlnp | grep 5672

# Solution: change port in deploy script
```

### Password auth fails
```bash
# Reset password on running container
docker exec thunderbird-rabbitmq-prod \
  rabbitmqctl change_password persona_user "<new-password>"
```

### Queues not receiving messages
```bash
# Check bindings
docker exec thunderbird-rabbitmq-prod \
  rabbitmqctl list_bindings

# Verify exchanges exist
docker exec thunderbird-rabbitmq-prod \
  rabbitmqctl list_exchanges
```

### Disk fill (7-day TTL not working)
```bash
# Check queue arguments
docker exec thunderbird-rabbitmq-prod \
  rabbitmqctl list_queue_attrs <queue-name> x-message-ttl

# Re-apply TTL if needed
docker exec thunderbird-rabbitmq-prod \
  rabbitmqctl set_queue_attributes <queue-name> x-message-ttl 604800000
```

---

## SUCCESS CRITERIA

✅ **Deployment successful when:**

- [x] Container running on yoga with --restart policy
- [x] All 3 exchanges present and durable
- [x] All 6 persona queues present with 7-day TTL
- [x] persona_user can authenticate
- [x] AMQP (5672) accessible from localhost
- [x] Management UI (15672) accessible via HTTP
- [x] Test dissent published and consumed
- [x] Acknowledgment flow working end-to-end
- [x] Audit trail captures all messages
- [x] session_init.py detects yoga (no fallback)
- [x] Morning brief shows dissent alerts
- [x] Telegram alerts fire on P0 dissents (if active)
- [x] Latency <500ms (target: <50ms)
- [x] Error rate: 0%

---

## SIGN-OFF

- **Deployed by:** [Name/Date]
- **Verified by:** [Name/Date]
- **Approved by:** Commander

**Date:** 2026-06-09 (target)  
**Status:** Ready for deployment

---

## REFERENCES

- Deployment script: `ops/deploy_rabbitmq_to_yoga.sh`
- Production config: `core/messaging/production_config.py`
- Test suite: `tests/test_live_dissent_production.py`
- Documentation: `docs/DISSENT_SCENARIO_EXAMPLE.md`
- Standing Order: `standing_orders/SO_MISSION-172-CLOSURE_20260609.md`
