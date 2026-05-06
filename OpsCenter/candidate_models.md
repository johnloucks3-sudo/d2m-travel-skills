# OpenRouter Candidate Model List for D2M Travel
# Goal: Reduce costs, maintain performance for specific Thunderbird tasks (ops, intel, logic)

## High-Efficiency Bulk / Logic / Routing (Cost: <$0.10/M tokens)
- IBM: Granite 4.0 Micro ($0.000000017 / 1M)
- Meta: Llama 3.1 8B Instruct ($0.00000002 / 1M)
- Mistral: Mistral Nemo ($0.00000002 / 1M)
- Meta: Llama 3.2 1B Instruct ($0.000000027 / 1M)

## High-Reasoning / Judgement / Persona (Claude/Opus/Sonnet)
- Anthropic: Claude 3.5 Sonnet
- Anthropic: Claude 3.5 Opus

## Intelligence / Multimodal / Synthesis
- Google: Gemini 3.1 Flash-Lite (Our current default)
- Google: Gemini 2.0 Flash-Lite

## Image Generation (Evaluated)
- **Black Forest Labs: FLUX.2 Pro** ($0.03/MP) — *Recommended for production quality/consistency.*
- **ByteDance Seed: Seedream 4.5** ($0.04/image) — *Strong candidate for editing consistency.*
- **Sourceful: Riverflow V2 Fast** ($0.03/image) — *Most efficient if low-latency/standardized sizing is preferred.*
- **Google: Nano Banana Pro** ($2M input/$12M output tokens) — *Overkill for general tasks but best for complex infographics/diagrams via Search grounding.*

---
### Image Strategy for D2M
- **Default:** Avoid for standard dossiers (Jinja2/WeasyPrint is superior for brand).
- **Candidate for specialized tasks:** FLUX.2 Pro (for photorealistic reference) or Nano Banana Pro (if we need to generate branded infographics or localized diagrams for itineraries).
