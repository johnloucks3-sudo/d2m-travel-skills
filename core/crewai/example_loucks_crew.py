#!/usr/bin/env python3
"""Example: Loucks 32-Day Trip Validation via CrewAI Bridge.
Uses Groq (orchestrator) as primary LLM. Falls back to DeepSeek if needed.
Writes output to /home/john/Thunderbird/output/loucks_crewai_validation.txt
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crew_runner import run_crew

TASK = """
Validate the complete Loucks 32-day Pacific journey (Apr 10 - May 11, 2026):
1. Date chain: verify all segments connect with no gaps
2. Document check: passport expiration, 6-month rule for Japan/Canada
3. Timing conflicts: connection times, boarding windows
4. Financial audit: sum all costs, verify against dossier totals
5. Dining cross-reference: Loucks vs Westbrook shared bookings
6. Excursion conflicts: same port, different bookings
7. Open items: unbooked transfers, pending upgrades, visa requirements
8. Risk assessment: flag anything that could go wrong

Source files are in /home/john/Thunderbird/dossiers/
Write the validation report to /home/john/Thunderbird/output/loucks_crewai_validation.txt
""".strip()

if __name__ == "__main__":
    print("Running Loucks 32-Day Validation Crew")
    print("LLM: Groq Llama 3.3 70B (orchestrator tier)")
    result = run_crew(
        task_text=TASK,
        llm_tier="orchestrator",
        output_file="/home/john/Thunderbird/output/loucks_crewai_validation.txt"
    )
    
    if result["status"] == "success":
        print("\nValidation complete.")
        print(f"Output: /home/john/Thunderbird/output/loucks_crewai_validation.txt")
    else:
        print(f"\nError: " + str(result.get('error', 'unknown')))
        sys.exit(1)
