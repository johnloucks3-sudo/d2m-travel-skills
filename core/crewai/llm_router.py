#!/usr/bin/env python3
"""LLM Router for CrewAI Bridge
Routes tasks to Groq (primary), DeepSeek (reasoning), OpenRouter (quick/free).
Anthropic key is NEVER used for spend — it's a Poe routing decoy.
"""
import os, sys
from dotenv import load_dotenv

# Load parent .env for keys
load_dotenv('/home/john/Thunderbird/.env')
load_dotenv('/home/john/Thunderbird/crewai_bridge/.env.llm')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

DEEPSEEK_BASE = "https://openrouter.ai/api/v1"
DEEPSEEK_MODEL = "deepseek/deepseek-chat-v3.1"

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat-v3.1"
OPENROUTER_FREE = "deepseek/deepseek-chat-v3.1"

# NEVER use these for actual API calls
_ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')  # DECOY — DO NOT TOUCH

def get_orchestrator_llm():
    """Primary CrewAI LLM — Groq Llama 3.3 70B"""
    try:
        from crewai.llm import LLM
        return LLM(
            model=f"groq/{GROQ_MODEL}",
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE,
            temperature=0.1,
        )
    except Exception as e:
        print(f"[WARN] Groq LLM failed, falling back to DeepSeek: {e}")
        return get_reasoning_llm()

def get_reasoning_llm():
    """Heavy reasoning — DeepSeek Chat"""
    try:
        from crewai.llm import LLM
        return LLM(
            model=f"openai/{DEEPSEEK_MODEL}",
            api_key=DEEPSEEK_API_KEY,
            base_url=f"{DEEPSEEK_BASE}/v1",
            temperature=0.1,
        )
    except Exception as e:
        print(f"[WARN] DeepSeek LLM failed, falling back to OpenRouter: {e}")
        return get_router_llm()

def get_router_llm():
    """Quick routing — OpenRouter DeepSeek V3.1"""
    try:
        from crewai.llm import LLM
        return LLM(
            model="openai/" + OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE,
            temperature=0.3,
        )
    except Exception as e:
        print(f"[WARN] OpenRouter LLM failed: {e}")
        return None

def get_free_llm():
    """Free research — OpenRouter free tier"""
    try:
        from crewai.llm import LLM
        return LLM(
            model="openai/" + OPENROUTER_FREE,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE,
            temperature=0.3,
        )
    except Exception as e:
        print(f"[WARN] Free LLM failed: {e}")
        return get_router_llm()

def cost_estimate(tokens_used: int, model: str = "groq") -> float:
    """Estimated cost per M tokens"""
    rates = {
        "groq": (0.00, 0.00),          # Free tier currently
        "deepseek": (0.14, 0.28),       # $0.14/M prompt, $0.28/M completion
        "openrouter": (0.14, 0.28),     # DeepSeek V3.1
        "free": (0.00, 0.00),
    }
    prompt_rate, comp_rate = rates.get(model, (0.50, 1.50))
    return (tokens_used / 1_000_000) * (prompt_rate + comp_rate) / 2

if __name__ == "__main__":
    print("=== LLM Router Test ===")
    print(f"Groq key: {'SET' if GROQ_API_KEY else 'MISSING'}")
    print(f"DeepSeek key: {'SET' if DEEPSEEK_API_KEY else 'MISSING'}")
    print(f"OpenRouter key: {'SET' if OPENROUTER_API_KEY else 'MISSING'}")
    llm = get_orchestrator_llm()
    if llm:
        print(f"Orchestrator LLM: {llm}")
    else:
        print("Orchestrator LLM: FAILED to initialize")
