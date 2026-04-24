#!/usr/bin/env python3
"""
multi_model_orchestrator.py
MCP-compatible multi-model orchestration skill for Thunderbird
Provides 9-model spectrum analysis with Claude MAX synthesis
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MULTI-MODEL] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/multi_model.log"),
        logging.StreamHandler()
    ]
)

class MultiModelOrchestrator:
    """Orchestrates multiple free models for luxury travel analysis"""
    
    def __init__(self):
        self.openrouter_api_key = "***REMOVED-SECRET***"
        
        # THOS Personas mapped to optimized non-Claude models
        self.persona_models = [
            # Core Leadership (higher quality models)
            ("x-ai/grok-4.1-fast", "COLONEL HALE", "Chief of Staff - Orchestration, Priorities, Staff Sync"),
            ("openai/gpt-4o-mini", "NAIA EXEC", "Voice & Visual Leader - Client Copy, Brand Tone, Commander's Intent"),
            
            # Primary A-Staff (Balanced models)
            ("x-ai/grok-4.1-fast", "A1 NAVARRO", "Intake & Client Profile Architect - Travel DNA, Dani Brief, Luna Brief"),
            ("x-ai/grok-4.1-fast", "A2 DEMBE", "Research & Market Intelligence - Destination Intel, Cruise Analysis"),
            ("openai/gpt-4o-mini", "A3 DANI", "Luxury Travel Concierge - Client Questions, Booking Queries"),
            ("x-ai/grok-4.1-fast", "A5 CASTILLO", "Strategy & Business Growth - Pricing Strategy, Growth Vectors"),
            ("openai/gpt-4o-mini", "A6 LUNA", "Creative Director - Narrative Copy, Emotional Travel Writing"),
            ("x-ai/grok-4.1-fast", "A8 REYES", "Experience Architect - Travel DNA → Cruise/Cabin/Excursion Mapping"),
            ("openai/gpt-4o-mini", "A9 HARLAN", "Finance & Process Improvement - Commission Audits, ROI, Budget"),
            
            # Special Staff
            ("x-ai/grok-4.1-fast", "CH PADRE", "Ethics & Morale - Wisdom, Ethical Checks, Perspective"),
            ("x-ai/grok-4.1-fast", "A12 ELON", "Innovation & Disruption - Automation, First-Principles Redesign")
        ]
    
    def process_with_openrouter(self, model_id: str, prompt: str) -> Dict[str, Any]:
        """Process task using OpenRouter API"""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )

            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a luxury travel expert providing specialized analysis for Dreams2Memories Travel.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
            )

            result = response.choices[0].message.content
            cost = response.usage.total_tokens * 0.0000002  # Estimate

            return {
                "success": True,
                "result": result,
                "cost": cost,
                "model": model_id,
            }

        except Exception as e:
            logging.error(f"OpenRouter error with {model_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": model_id,
            }
    
    def process_with_claude_max(self, prompt: str) -> Dict[str, Any]:
        """Process task using Claude MAX via OAuth"""
        try:
            import subprocess
            import os
            
            # Clear conflicting environment variables
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_BASE_URL", None)
            
            result = subprocess.run(
                ["claude", "--dangerously-skip-permissions", "-p", prompt],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "result": result.stdout,
                    "cost": 0.0,  # Claude MAX is $0 via OAuth
                    "model": "Claude MAX (OAuth)",
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "model": "Claude MAX (OAuth)",
                }

        except Exception as e:
            logging.error(f"Claude MAX error: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": "Claude MAX (OAuth)",
            }
    
    def thos_persona_analysis(self, prompt: str, max_cost: float = 0.05) -> Dict[str, Any]:
        """Run THOS persona analysis with Claude MAX synthesis"""
        logging.info(f"Starting THOS persona analysis with 10-persona orchestration")
        
        results = []
        total_cost = 0.0
        
        # Get perspectives from all THOS personas
        for model_id, persona, role in self.persona_models:
            if total_cost >= max_cost:
                logging.warning(f"Cost limit reached (${total_cost:.6f}), skipping remaining personas")
                break
                
            persona_prompt = f"""You are {persona} - {role} for Dreams2Memories Travel.
            
            QUESTION: {prompt}
            
            Provide your distinctive professional perspective from your specific role.
            Focus on your area of expertise within the Thunderbird OS operational model.
            Consider how your perspective contributes to the 12-persona team structure.
            
            Respond with specific, actionable insights for Commander John Loucks.
            Format your response in character as {persona}."""
            
            result = self.process_with_openrouter(model_id, persona_prompt)
            
            if result["success"]:
                cost = result.get("cost", 0)
                total_cost += cost
                
                results.append({
                    "persona": persona,
                    "role": role,
                    "analysis": result["result"],
                    "cost": cost,
                    "model": model_id,
                })
                logging.info(f"✓ {persona} perspective: ${cost:.6f}")
            else:
                logging.warning(f"✗ {persona} failed: {result.get('error')}")
        
        # Synthesize with Claude MAX as COS Hale
        if results:
            synthesis_prompt = f"""COS HALE SYNTHESIS - THOS PERSONA ORCHESTRATION
            
            You are Colonel Victoria "Iron Vic" Hale, Chief of Staff for Dreams2Memories Travel.
            You have received tactical assessments from each wing staff persona on the following issue:
            
            QUESTION: {prompt}
            
            PERSONA ASSESSMENTS:
            
            {"\n\n".join([f"## {r['persona']} ({r['role']}):\n{r['analysis']}" for r in results])}
            
            Your mission is to synthesize these 10 tactical perspectives into a single operational order.
            
            As COS Hale, you must:
            1. Extract the most critical insights from each persona
            2. Identify synergies and contradictions between perspectives  
            3. Leverage the full 12-persona operational advantage
            4. Formulate an actionable command decision for Commander John Loucks
            5. Specify which personas should execute which components
            6. Include any necessary risk mitigations
            
            Provide your synthesis in standard COS Hale format:
            - EXECUTIVE SUMMARY (1-2 sentences)
            - KEY INSIGHTS (bullet points from each persona)
            - ACTIONABLE ORDER (numbered commands with persona assignments)
            - RISK ASSESSMENT (P1/P2/P3 priorities)
            - TIMELINE & DELIVERABLES
            
            Remember: You orchestrate the wing. Your synthesis should reflect the combined intelligence
            of all 10 personas while maintaining operational clarity and decisiveness."""
            
            max_result = self.process_with_claude_max(synthesis_prompt)
            
            if max_result["success"]:
                return {
                    "success": True,
                    "result": max_result["result"],
                    "total_cost": total_cost,
                    "persona_assessments": results,
                    "synthesis_cost": 0.0,
                    "model": "THOS 10-Persona + COS Hale Synthesis",
                    "synthesized_by": "COS Hale (Claude MAX OAuth)",
                }
            else:
                # Fallback: Use Grok for synthesis if Claude MAX fails
                fallback_result = self.process_with_openrouter("x-ai/grok-4.1-fast", synthesis_prompt)
                if fallback_result["success"]:
                    return {
                        "success": True,
                        "result": fallback_result["result"],
                        "total_cost": total_cost + fallback_result.get("cost", 0),
                        "persona_assessments": results,
                        "synthesis_cost": fallback_result.get("cost", 0),
                        "model": "THOS 10-Persona + Grok Synthesis",
                        "synthesized_by": "x-ai/grok-4.1-fast",
                    }
        
        return {
            "success": False,
            "error": "THOS persona analysis failed",
            "total_cost": total_cost,
        }
    
    def mcp_handler(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """MCP-compatible handler for multi-model requests"""
        try:
            if request.get("method") == "thos_persona_analysis":
                params = request.get("params", {})
                prompt = params.get("prompt", "")
                max_cost = params.get("max_cost", 0.05)
                
                result = self.thos_persona_analysis(prompt, max_cost)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result,
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": "Method not found"},
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32000, "message": f"Internal error: {e}"},
            }

def main():
    """Test the THOS persona orchestrator"""
    orchestrator = MultiModelOrchestrator()
    
    test_prompt = """How should Dreams2Memories Travel structure its multi-model AI 
    system to leverage THOS personas effectively while minimizing costs?
    
    Consider:
    - Model assignments for each persona
    - Orchestration strategy  
    - Cost optimization
    - Operational efficiency
    - Quality vs. cost tradeoffs"""
    
    print("🚀 Testing THOS Persona Orchestrator...")
    result = orchestrator.thos_persona_analysis(test_prompt)
    
    if result["success"]:
        print(f"✅ Success! Total cost: ${result['total_cost']:.6f}")
        print(f"Model: {result['model']}")
        print(f"Synthesized by: {result['synthesized_by']}")
        print("\n" + "="*80)
        print("COS HALE SYNTHESIS:")
        print("="*80)
        print(result["result"])
        
        print(f"\nGenerated {len(result['persona_assessments'])} persona assessments")
        for assessment in result["persona_assessments"]:
            print(f"  - {assessment['persona']}: ${assessment['cost']:.6f}")
    else:
        print(f"❌ Failed: {result.get('error')}")

if __name__ == "__main__":
    main()