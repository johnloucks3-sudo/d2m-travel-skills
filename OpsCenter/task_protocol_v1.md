# GOLD STANDARD TASK COORDINATION PROTOCOL v1
# HALE Persona-to-Persona Coordination System
Date: 2026-05-14
Status: ACTIVE

## Overview
This protocol defines the failsafe coordination system between HALE personas (ALPHA/BRAVO) and wing staff. It eliminates communication failures through mandated verification checkpoints and real-time audit trails.

## Core Principles
1. **No Silent Failures** - Every task status is tracked and verified
2. **5-Minute ETC Maximum** - Any task exceeding 5 minutes triggers escalation
3. **Mandatory Verification** - Completion requires independent verification
4. **Real-Time Audit Trail** - Every state transition is logged
5. **Fail-Safe Routing** - Stalled tasks escalate through defined paths

## Task Format
```
NEXUS: <task_description> ETC: <minutes> NLT: <timestamp>
```
**Example:** `NEXUS: Update client dossier for Morton group ETC: 3m NLT: 15:30 MT`

## State Machine
```
PENDING → IN_PROGRESS → AWAITING_VERIFICATION → COMPLETE
                     ↓                        ↓
                     ESCALATED → RESOLVED
```

## File Infrastructure
- **Task Registry:** `/OpsCenter/task_registry.json` - Active task status
- **Audit Trail:** `/logs/persona_handoff_audit.jsonl` - All transitions
- **Escalation Matrix:** `/OpsCenter/escalation_matrix.json` - Response paths
- **Verification:** `/OpsCenter/verification_checkpoint.py` - Completion validation

## Verification Checkpoint
All tasks must pass verification before COMPLETE:
```python
verify_completion(task_id, output_path, expected_artifacts)
```
Check includes: file existence, content validation, timestamp recency.

## Escalation Paths
1. **0-2 min:** Task owner works (ALPHA/BRAVO)
2. **2-4 min:** Task polling every 30s by watchdog
3. **4-5 min:** Escalate to partner persona (ALPHA→BRAVO)
4. **5+ min:** Commander alert via Telegram (critical priority)

## Dashboard Monitoring
```bash
# Real-time task monitoring
watch -n 5 'tail -n 10 /OpsCenter/task_registry.json && echo "---" && tail -n 5 /logs/persona_handoff_audit.jsonl'

# Health check
python3 /OpsCenter/verification_checkpoint.py --health
```

## Usage Examples

### 1. Task BRAVO from ALPHA
```bash
echo "NEXUS: Analyze Lyons FPD status and recommend action ETC: 4m NLT: $(date -d '+4 minutes' '+%H:%M MT')" >> /OpsCenter/collaboration/opencode_inbox.md
```

### 2. Monitor Active Task
```bash
python3 /OpsCenter/verification_checkpoint.py --status BRAVO-TASK-001
```

### 3. Force Verification
```bash
python3 /OpsCenter/verification_checkpoint.py --verify --task BRAVO-TASK-001 --artifact /output/lyons_analysis.md
```

## Implementation Status
✅ Protocol defined  
✅ File structure created  
✅ Verification system implemented  
✅ Escalation matrix defined  
✅ Audit logging active  

## Testing Protocol
1. Send test task: `NEXUS: TEST-PROTOCOL-001 ETC: 1m NLT: now+1m`
2. Monitor registry for state transitions
3. Verify completion artifacts exist
4. Audit trail should show full PDCA loop

## Maintenance
- Daily audit log rotation
- Weekly escalation matrix review
- Monthly protocol performance review against KPIs

## KPIs
- Task completion rate: ≥98%
- Average ETC variance: ≤±1 minute  
- Verification success rate: 100%
- Escalation frequency: <5% of tasks

---
**Protocol Owner:** HALE BRAVO  
**Last Updated:** 2026-05-14  
**Version:** v1.0 (Gold Standard)