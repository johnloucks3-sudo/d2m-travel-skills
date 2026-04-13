#!/usr/bin/env python3
"""
Test OpenRouter Haiku API access
"""

import os
import sys
from openai import OpenAI

# Get API key from environment or use default
api_key = os.environ.get(
    "OPENROUTER_API_KEY",
    "***REMOVED-SECRET***",
)

# Initialize client
client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
)

# Test with cheapest Haiku model (claude-3-haiku)
model = "anthropic/claude-3-haiku"

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Hello! Please respond with 'OpenRouter Haiku working!'",
            }
        ],
        max_tokens=100,
    )

    print(f"✅ Success! Model: {model}")
    print(f"Response: {response.choices[0].message.content}")
    print(f"Usage: {response.usage}")

except Exception as e:
    print(f"❌ Error with model {model}: {e}")
    sys.exit(1)
