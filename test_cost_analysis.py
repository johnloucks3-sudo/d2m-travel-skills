#!/usr/bin/env python3
"""
Cost analysis for different models
"""

import os
from openai import OpenAI

api_key = os.environ.get(
    "OPENROUTER_API_KEY",
    "***REMOVED-SECRET***",
)
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

# Test models with pricing
test_prompt = """Please analyze this travel request and provide a brief response:

Client: John and Sarah, celebrating 10th anniversary
Destination: Caribbean cruise
Dates: June 15-22, 2026
Budget: $5,000-$7,000
Preferences: All-inclusive, balcony cabin, premium dining

What would you recommend?"""

models = [
    "anthropic/claude-3-haiku",  # $0.25/$1.25 per 1M
    "anthropic/claude-3.5-haiku",  # $0.8/$4 per 1M
    "anthropic/claude-haiku-4.5",  # $1/$5 per 1M
    "openrouter/qwen/qwen3.6-plus-04-02:free",     # ~$0.305 per 1M total
]

print("Testing model costs for travel analysis task...")
print("=" * 60)

for model in models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a luxury travel specialist."},
                {"role": "user", "content": test_prompt},
            ],
            max_tokens=300,
        )

        cost = response.usage.cost if hasattr(response.usage, "cost") else "Unknown"
        print(f"\n✅ {model}")
        print(f"   Cost: ${cost}")
        print(
            f"   Tokens: {response.usage.total_tokens} (Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens})"
        )
        print(f"   Response preview: {response.choices[0].message.content[:100]}...")

    except Exception as e:
        print(f"\n❌ {model}")
        print(f"   Error: {e}")
