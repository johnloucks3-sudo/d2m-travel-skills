# PHASE 1 — Opus Routing Rules
## Immediate Implementation: Selective Opus Integration
**Effective:** 2026-04-30  
**Budget Impact:** +$15-20/mo (estimated)  
**Integration Time:** 4 hours  
**Risk Level:** LOW

---

## ROUTING MATRIX

### ✅ ROUTE TO OPUS (High-Impact, High-Context)
| Task | Reason | Est. Monthly |
|------|--------|-------------|
| **Client-facing email (Dani)** | Voice consistency, nuance, client trust | ~8-10 tasks @ 1.5K tokens = $0.15-0.18 |
| **Strategic decisions** | Trade-off analysis, pricing strategy, policy | ~5 tasks @ 2K tokens = $0.10 |
| **Voice-matched copy** | Itinerary narrative, proposal copy, brand tone | ~3-4 tasks @ 3K tokens = $0.18-0.24 |
| **Tiebreaker calls** | When DeepSeek output is marginal or conflicting | ~2-3 tasks @ 1.5K tokens = $0.05-0.07 |
| **Subtotal** | | **$0.48-0.59/day ≈ $14.40-17.70/month** |

### ✅ ROUTE TO DEEPSEEK V3.1 (Bulk, Routine)
| Task | Reason | Est. Monthly |
|------|--------|-------------|
| **Research scanning** | Cruise intel, competitor pricing, market data | ~15 tasks @ 1K tokens = $0.04 |
| **Data extraction** | Form processing, PDF parsing, structured output | ~8 tasks @ 800 tokens = $0.02 |
| **Bulk analysis** | Email history synthesis, log analysis | ~4 tasks @ 2K tokens = $0.02 |
| **Routine reports** | Daily calculations, status summaries | ~10 tasks @ 500 tokens = $0.01 |
| **Subtotal** | | **$0.09/day ≈ $2.70/month** |

---

## IMPLEMENTATION PATTERN

### Layer 1: Model Selection Function
```python
def route_task_to_model(task_type: str, context_length: int, sensitivity: str) -> str:
    """
    Route task to Opus or DeepSeek based on decision matrix.
    
    Rules:
      - Client-facing (email, copy) → OPUS
      - Strategy/tiebreaker → OPUS
      - Bulk research/data → DEEPSEEK
      - Sensitivity=HIGH → OPUS
      - Context>3K + complexity=HIGH → OPUS
    """
    OPUS_TRIGGERS = {
        'dani_email': True,
        'client_copy': True,
        'strategic_decision': True,
        'tiebreaker': True,
        'brand_voice_matching': True,
    }
    
    if task_type in OPUS_TRIGGERS:
        return 'opus'
    
    if sensitivity == 'HIGH' or (context_length > 3000 and 'complex' in task_type.lower()):
        return 'opus'
    
    return 'deepseek'
```

### Layer 2: Dispatch to Correct Backend
```python
def dispatch_task(task_description: str, task_type: str, **kwargs) -> dict:
    model = route_task_to_model(task_type, kwargs.get('context_length', 0), kwargs.get('sensitivity', 'NORMAL'))
    
    if model == 'opus':
        # Use Claude Max (Opus)
        from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
        result = spawn_headless_claude(
            prompt=task_description,
            output_file=kwargs.get('output_file'),
            model="claude-opus-4-7",  # Premium model
            task_name=f"{task_type}_opus"
        )
    else:
        # Use OpenCode (DeepSeek V3.1) — existing system
        from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude
        result = dispatch_to_headless_claude(
            task_description=task_description,
            output_file_path=kwargs.get('output_file'),
            task_name=f"{task_type}_deepseek"
        )
    
    return result
```

### Layer 3: Integration Points
1. **Dani Client Replies** → Call route_task_to_model('dani_email') → dispatch to Opus
2. **Strategic Decisions** → Call route_task_to_model('strategic_decision') → dispatch to Opus
3. **Itinerary Narratives** → Call route_task_to_model('brand_voice_matching') → dispatch to Opus
4. **Research Scanning** → Call route_task_to_model('research_scan') → dispatch to DeepSeek
5. **Tiebreaker (COS)** → Call route_task_to_model('tiebreaker') → dispatch to Opus

---

## COST TRACKING

### Monthly Budget Allocation (Phase 1)
```
OpenCode (DeepSeek core):        $8-12/mo
Opus (high-impact tasks):        $15-20/mo
────────────────────────────────
PHASE 1 TOTAL:                   $23-32/mo
Budget cap utilization:           23-32% of $100
Safety margin:                    $68-77/mo remaining
```

### Cost Alert Thresholds
- ⚠️ YELLOW: $80/month (80% of cap)
- 🔴 RED: $95/month (95% of cap) — halt non-critical Opus, fallback to Sonnet

---

## MONITORING & FALLBACK

### Fallback Trigger (if cost exceeds $80/month)
1. Switch high-volume Opus tasks to Sonnet (cheaper, acceptable quality loss)
2. Reserve Opus for CLIENT-FACING only (email, proposals, copy)
3. All research/strategy falls back to DeepSeek
4. Alert COS: "Budget utilization at 80% — switching to cost-save mode"

### Success Metrics
- ✅ Dani client emails have improved voice consistency (vs. DeepSeek)
- ✅ Strategic decisions show better trade-off analysis (vs. DeepSeek)
- ✅ Monthly cost stays within $23-32/mo band
- ✅ No client-facing quality regression

---

## NEXT MILESTONES
- **2026-05-06:** Phase 1 routing wired, Opus available for strategy tasks
- **2026-06-10:** Phase 2 evaluation (Aider itinerary integration)
- **2026-07-15:** Phase 3 evaluation (Gemini free tier, if budget allows)

---

*Decision made by Opus evaluation 2026-04-30. NO-GO on full Option 1. Remediation path approved for execution.*
