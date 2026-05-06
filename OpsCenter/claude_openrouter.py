"""
claude_openrouter.py
Thunderbird Wing — Headless Claude client via OpenRouter
Drop-in wrapper for use by Hale, Blackboard, or any agent needing Claude inference.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load from Thunderbird .env
load_dotenv(Path("/home/john/Thunderbird/.env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://dreams2memories.com",
    "X-Title": "Thunderbird Wing",
    "Content-Type": "application/json",
}


def ask_claude(
    prompt: str,
    system: str = "You are a helpful AI assistant integrated into the Thunderbird Wing multi-agent system.",
    model: str = "qwen/qwen3.6-plus-04-02:free",  # Cost-optimized reasoning
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """
    Send a prompt to Claude via OpenRouter and return the response text.

    Args:
        prompt:     User message / task
        system:     System prompt (override per agent as needed)
        model:      OpenRouter model string
        max_tokens: Max response tokens
        temperature: Sampling temperature

    Returns:
        Response string from Claude, or error message.
    """
    if not OPENROUTER_API_KEY:
        return "[ERROR] OPENROUTER_API_KEY not found in environment"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        return "[ERROR] OpenRouter request timed out after 120 seconds"
    except requests.exceptions.RequestException as e:
        return f"[ERROR] OpenRouter API error: {e}"
    except (KeyError, IndexError) as e:
        return f"[ERROR] Invalid response format from OpenRouter: {e}"


# Test function
def test_openrouter():
    """Quick test to verify OpenRouter connectivity"""
    print("Testing OpenRouter connection...")

    result = ask_claude(
        "Test message from Thunderbird Wing. Please respond with 'OpenRouter working!'",
        system="You are a test assistant. Respond concisely.",
        max_tokens=50,
        temperature=0.1,
    )

    print(f"Response: {result}")
    return "OpenRouter working!" in result


if __name__ == "__main__":
    success = test_openrouter()
    print(f"Test {'PASSED' if success else 'FAILED'}")
