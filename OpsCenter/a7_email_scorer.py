#!/usr/bin/env python3
import json
import sys

def score_draft(body_text):
    score = 100
    deductions = []
    
    if "Best," in body_text or "Best regards," in body_text:
        score -= 10
        deductions.append("-10%: Used 'Best' instead of 'Thanks'")
        
    if "Love Group Travel" in body_text:
        score -= 20
        deductions.append("-20%: Used deprecated brand name")
        
    if "raw seafood" in body_text.lower() and "susie" in body_text.lower():
        score -= 30
        deductions.append("-30%: Recommended raw seafood to Susie")

    return {"score": score, "deductions": deductions}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(score_draft(sys.argv[1])))
    else:
        print(json.dumps(score_draft("Thanks, The Wing")))
