#!/usr/bin/env python3
"""
Test OpenRouter Haiku 4.5 API access
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

# Test with newest Haiku model (claude-haiku-4.5)
model = "anthropic/claude-haiku-4.5"

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Hello Haiku 4.5! Please respond with 'Haiku 4.5 working!'",
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
