#!/usr/bin/env python3
"""
Test: Thunderbird Model Routing Integration
Tests how the incubator will route tasks to different models.
"""

import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("test_routing")

# Add core to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "core"))
from ai_infra.thunderbird_model_router import route_model, estimate_cost, get_all_models

print("=" * 80)
print("THUNDERBIRD MODEL ROUTING TEST")
print("=" * 80)

# Test 1: Incubator large context task
print("\n✓ Test 1: Incubator Phase Review (Large Context Research)")
print("-" * 80)
task_type = "incubator"
content_size = 50_000  # ~50K tokens of research findings
model = route_model(task_type, content_size=content_size)
print(f"Task: {task_type}")
print(f"Content size: {content_size:,} tokens")
print(f"Selected model: {model['model_id']}")
print(f"Context: {model['context']}")
print(f"Cost per million: ${model['cost_per_M']}")
cost = estimate_cost("grok_2m", 50_000, 2_000)
print(f"Est. cost for this run: ${cost['total_cost']:.4f}")
print(f"Rationale: {model['rationale']}")

# Test 2: Brief generation with imagery
print("\n✓ Test 2: Brief Generation with Imagery")
print("-" * 80)
task_type = "brief_generation"
has_images = True
model = route_model(task_type, has_images=has_images)
print(f"Task: {task_type}")
print(f"Has images: {has_images}")
print(f"Selected model: {model['model_id']}")
print(f"Vision support: {model['vision_support']}")
print(f"Speed: {model['speed']}")
cost = estimate_cost("gemini_vision", 100_000, 5_000)
print(f"Est. cost for this run: ${cost['total_cost']:.4f}")
print(f"Rationale: {model['rationale']}")

# Test 3: Cost-optimized analysis
print("\n✓ Test 3: Routine Analysis (Cost Optimized)")
print("-" * 80)
task_type = "routine_analysis"
budget = "minimal"
model = route_model(task_type, budget=budget)
print(f"Task: {task_type}")
print(f"Budget: {budget}")
print(f"Selected model: {model['model_id']}")
print(f"Context: {model['context']}")
cost = estimate_cost("deepseek_optimized", 200_000, 3_000)
print(f"Est. cost for this run: ${cost['total_cost']:.4f}")
print(f"Rationale: {model['rationale']}")

# Test 4: Free tier testing
print("\n✓ Test 4: Testing (Free Tier)")
print("-" * 80)
task_type = "testing"
model = route_model(task_type)
print(f"Task: {task_type}")
print(f"Selected model: {model['model_id']}")
print(f"Cost per million: ${model['cost_per_M']}")
print(f"Context: {model['context']}")
if "rate_limits" in model:
    print(f"Rate limits: {model['rate_limits']}")
cost = estimate_cost("free", 10_000, 500)
print(f"Est. cost for this run: ${cost['total_cost']:.4f}")

# Test 5: Large context requirement
print("\n✓ Test 5: Task Requiring 2M Context")
print("-" * 80)
required_context = 1_500_000
model = route_model("research", required_context=required_context)
print(f"Required context: {required_context:,} tokens")
print(f"Selected model: {model['model_id']}")
print(f"Available context: {model['context']}")
cost = estimate_cost("grok_2m", 1_000_000, 10_000)
print(f"Est. cost for large doc: ${cost['total_cost']:.4f}")

# Summary
print("\n" + "=" * 80)
print("ROUTING SUMMARY")
print("=" * 80)

all_models = get_all_models()
print("\nAvailable Model Tiers:")
for tier, config in all_models.items():
    print(f"\n  {tier.upper()}")
    print(f"    Model: {config['model_id']}")
    print(f"    Context: {config['context']}")
    print(f"    Cost: ${config['cost_per_M']:.3f}/M tokens")
    print(f"    Vision: {'✓' if config.get('vision_support') else '✗'}")
    print(f"    Use cases: {', '.join(config['use_cases'][:3])}...")

# Cost comparison
print("\n" + "=" * 80)
print("COST COMPARISON - Processing 500K tokens with 5K output")
print("=" * 80)

test_cases = [
    ("grok_2m", "Large context research"),
    ("gemini_vision", "Brief with imagery"),
    ("deepseek_optimized", "Routine analysis"),
    ("free", "Testing"),
]

for tier, description in test_cases:
    cost = estimate_cost(tier, 500_000, 5_000)
    print(f"{tier:20s} ({description:25s}): ${cost['total_cost']:.4f}")

print("\n" + "=" * 80)
print("✅ ROUTING TEST COMPLETE")
print("=" * 80)
