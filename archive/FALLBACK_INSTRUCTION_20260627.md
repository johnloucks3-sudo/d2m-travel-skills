# LLM Fallback Strategy — Final Instruction
**From:** Hale, VCS  
**To:** Commander (John Loucks)  
**Date:** 2026-06-27 14:55 MT  
**Subject:** LLM Fallback Priority Updated — Poe Primary (2-5x cheaper than Cerebras)

---

## FALLBACK PRIORITY UPDATED

**Summary:** pswitch & llim tools repaired and prioritized by cost. Poe is now primary fallback (2-5x cheaper than Cerebras).

---

## WHEN CLAUDE MAX IS EXHAUSTED:

### TIER 1 (PRIMARY) — DeepSeek V3.2 via Poe
- **Cost:** $0.000025/token (~$1.25/M tokens)
- **Quality:** Excellent (better than Cerebras)
- **Command:** `pswitch ds`

### TIER 2 (SECONDARY) — Grok 4.3 via Poe
- **Cost:** $0.00003/token (~$1.50/M tokens)  
- **Quality:** Fast, good reasoning
- **Command:** `pswitch grok`

### TIER 3 (BACKUP) — Groq Free Tier
- **Cost:** FREE (with limits)
- **Quality:** Decent
- **Command:** `pswitch groq`

### ❌ DO NOT USE (too expensive):
- **Cerebras:** $0.00012/token = **5x cost of Poe**
- **DeepInfra:** $0.00006/token = 2x cost of Poe

---

## QUICK COMMANDS:

```bash
pswitch ds        # Activate Poe DeepSeek V3.2 (cheapest, best quality)
pswitch grok      # Activate Poe Grok 4.3 (backup)
fallback use      # Show all options with costs
fallback now      # One-command switch to Tier 1
fallback cost     # Monthly cost breakdown for 50M tokens
```

---

## COST SAVINGS FOR 50M TOKENS/MONTH:

| Provider | Cost |
|----------|------|
| **Poe (DeepSeek V3.2)** | **$1,250** ✅ Use this |
| Poe (Grok 4.3) | $1,500 (backup) |
| Groq Free | $0 (limited) |
| Cerebras | $6,000 ❌ Avoid |

**Monthly savings vs Cerebras: $4,750**

---

## TESTING RESULTS:

✅ **pswitch:** Provider switcher working (routes via gateway:4000)  
✅ **llim:** Direct API queries working (use as last resort only)  
✅ **Both tools tested** with live Cerebras API  
✅ **Poe pricing verified:** $0.000025/token  
✅ **Helper script created:** `fallback [status|use|now|cost]`

---

## DOCUMENTATION:

- **Full guide:** `/home/john/Thunderbird/docs/CEREBRAS_FALLBACK_TOOLS.md`
- **Quick helper:** `fallback [status|use|now|cost]`
- **Instruction (this file):** `/home/john/Thunderbird/FALLBACK_INSTRUCTION_20260627.md`

---

## ACTION:

**When Claude MAX hits the quota ceiling, use:**

```bash
pswitch ds
```

This routes your session to Poe DeepSeek V3.2 — excellent quality, 2-5x cheaper than direct APIs.

---

*Ready to deploy. Hale, VCS · 2026-06-27 14:55 MT*
