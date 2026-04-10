#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import google.generativeai as genai

# Using exact keys from the config.yaml
groq_client = AsyncOpenAI(
    api_key="***REMOVED-SECRET***",
    base_url="https://api.groq.com/openai/v1"
)

deepseek_client = AsyncOpenAI(
    api_key="***REMOVED-SECRET***",
    base_url="https://api.deepseek.com"
)

genai.configure(api_key="***REMOVED-SECRET***")

async def test_a7_groq(cal_data):
    print("Starting Groq (A7)...")
    prompt = f"You are Brig Gen Thomas Gauge Sterling (A7). Give a blunt 2-bullet process audit of this schedule. No fluff:\n{cal_data}"
    try:
        response = await groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"\n--- A7 (GROQ - Llama 3) ---\n{response.choices[0].message.content}\n"
    except Exception as e:
        return f"\n--- A7 (GROQ) FAILED ---\n{e}\n"

async def test_a2_deepseek(cal_data):
    print("Starting DeepSeek (A2)...")
    prompt = f"You are Lt Col Marcus Dembe (A2). Extract locations from this schedule and give a 2-sentence recon assessment. Voice: precise, evidence-first:\n{cal_data}"
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat-v3.1",
            messages=[{"role": "user", "content": prompt}]
        )
        return f"\n--- A2 (DEEPSEEK V3) ---\n{response.choices[0].message.content}\n"
    except Exception as e:
        return f"\n--- A2 (DEEPSEEK) FAILED ---\n{e}\n"

async def test_a9_gemini(cal_data):
    print("Starting Gemini (A9)...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"You are Vic Harlan (A9). Analyze the financial implications of this schedule in 2 sentences:\n{cal_data}"
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return f"\n--- A9 (GEMINI 2.5) ---\n{response.text}\n"
    except Exception as e:
        return f"\n--- A9 (GEMINI) FAILED ---\n{e}\n"

async def run_tests(cal_data):
    results = await asyncio.gather(
        test_a7_groq(cal_data),
        test_a2_deepseek(cal_data),
        test_a9_gemini(cal_data)
    )
    
    with open("/home/john/Thunderbird/OpsCenter/collaboration/Stress_Test_Results.md", "w") as f:
        f.write("# TRIPLE VECTOR STRESS TEST RESULTS\n")
        for res in results:
            f.write(res)
    print("Tests complete.")

if __name__ == "__main__":
    raw_data = "2026-04-10 Flight to Santa Ana. 2026-04-13 Flight to Honolulu. 2026-04-18 Flight to TOKYO. 2026-04-19 Stay at Hilton Tokyo Odaiba. 2026-04-30 [EARA] Furlow Cruise Cancellation Penalty Begins"
    asyncio.run(run_tests(raw_data))

