#!/usr/bin/env python3
"""
run_spectrum_analysis.py
Run the 9-model spectrum analysis on the luxury travel question
"""

import sys
import os
sys.path.append('/home/john/Thunderbird')

from agents.thunderbird_model_dispatcher import ModelDispatcher

def main():
    dispatcher = ModelDispatcher()
    
    question = """How do we effectively use multiple free models to achieve a result that is greater than one expensive model? 
    How can a luxury travel agency owner with 12 personas use multiple models to beat Claude Opus?"""
    
    print("🚀 Starting 9-Model Spectrum Analysis...")
    print(f"Question: {question}")
    print("-" * 80)
    
    result = dispatcher.spectrum_analysis(question, 'SPECTRUM-001')
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    if result.get("success"):
        print(f"✅ SUCCESS! Total cost: ${result.get('total_cost', 0):.6f}")
        print(f"Model: {result.get('model', 'N/A')}")
        print("\nFINAL SYNTHESIS:")
        print("-" * 40)
        print(result.get("result", "No result"))
        
        # Show perspectives if available
        if "perspectives" in result:
            print(f"\nGenerated {len(result['perspectives'])} expert perspectives")
            for perspective in result["perspectives"]:
                print(f"  - {perspective['role']}: ${perspective['cost']:.6f}")
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        print(f"Cost incurred: ${result.get('total_cost', 0):.6f}")

if __name__ == "__main__":
    main()