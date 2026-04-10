#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI

groq_client = AsyncOpenAI(
    api_key="***REMOVED-SECRET***",
    base_url="https://api.groq.com/openai/v1"
)

deepseek_client = AsyncOpenAI(
    api_key="***REMOVED-SECRET***",
    base_url="https://api.deepseek.com"
)

openrouter_client = AsyncOpenAI(
    api_key="***REMOVED-SECRET***",
    base_url="https://openrouter.ai/api/v1"
)

async def test_a7_groq(cal_data):
    prompt = f"You are Brig Gen Thomas Gauge Sterling (A7). Give a blunt 2-bullet process audit of this schedule. No fluff:\n{cal_data}"
    try:
        response = await groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"\n### A7 (GROQ - Llama 3 70B)\n{response.choices[0].message.content}\n"
    except Exception as e:
        return f"\n### A7 (GROQ) FAILED: {e}\n"

async def test_a2_deepseek(cal_data):
    prompt = f"You are Lt Col Marcus Dembe (A2). Extract locations from this schedule and give a 2-sentence recon assessment. Voice: precise, evidence-first:\n{cal_data}"
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat-v3.1",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"\n### A2 (DEEPSEEK V3)\n{response.choices[0].message.content}\n"
    except Exception as e:
        return f"\n### A2 (DEEPSEEK) FAILED: {e}\n"

async def test_a5_openrouter(cal_data):
    prompt = f"You are Lt Col Ryan Castillo (A5). Analyze the business implications of the Furlow penalty in 2 sentences:\n{cal_data}"
    try:
        response = await openrouter_client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"\n### A5 (OPENROUTER - Claude Haiku)\n{response.choices[0].message.content}\n"
    except Exception as e:
        return f"\n### A5 (OPENROUTER) FAILED: {e}\n"

async def run_tests(cal_data):
    results = await asyncio.gather(
        test_a7_groq(cal_data),
        test_a2_deepseek(cal_data),
        test_a5_openrouter(cal_data)
    )
    
    with open("/home/john/Thunderbird/OpsCenter/collaboration/Stress_Test_Results.md", "w") as f:
        f.write("# TRIPLE VECTOR STRESS TEST RESULTS\n")
        for res in results:
            f.write(res)

if __name__ == "__main__":
    raw_data = "2026-04-10 Flight to Santa Ana. 2026-04-13 Flight to Honolulu. 2026-04-18 Flight to TOKYO. 2026-04-19 Stay at Hilton Tokyo Odaiba. 2026-04-30 [EARA] Furlow Cruise Cancellation Penalty Begins"
    asyncio.run(run_tests(raw_data))

