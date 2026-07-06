"""
Emotion + sentiment word lists for the lexicon-based fallback scorer in
sentiment_analyzer.py. Pure data, no dependencies — always available even
when the Claude API path is unavailable.
"""

# Emotion tag -> phrases that signal it. Matched as case-insensitive substrings.
EMOTION_LEXICON = {
    "enthusiasm": [
        "can't wait", "cant wait", "so excited", "excited", "thrilled",
        "amazing", "wonderful", "looking forward", "pumped", "stoked",
        "exciting", "love this", "fantastic", "incredible", "best trip",
        "yes!", "absolutely", "can't stop thinking about",
    ],
    "concern": [
        "worried", "concerned", "nervous", "anxious", "unsure",
        "hesitant", "not sure if", "uneasy", "apprehensive", "troubling",
        "is this a problem", "what if", "worried about", "a bit nervous",
        "concerned about", "not comfortable",
    ],
    "confusion": [
        "confused", "don't understand", "dont understand", "unclear",
        "not sure what", "what does this mean", "i'm lost", "im lost",
        "mixed up", "don't get it", "dont get it", "clarify",
        "clarification", "which one is", "i'm confused", "can you explain",
    ],
    "satisfaction": [
        "thank you so much", "thanks so much", "really appreciate",
        "we appreciate", "grateful", "exactly what we wanted",
        "very happy", "very pleased", "so pleased", "satisfied",
        "great job", "well done", "exceeded our expectations",
        "we love it", "perfect, thank you", "couldn't be happier",
        "couldnt be happier",
    ],
}

# General polarity words for the -1..+1 sentiment score. Weight = magnitude.
POSITIVE_WORDS = {
    "great": 0.5, "love": 0.6, "excellent": 0.7, "perfect": 0.7,
    "wonderful": 0.6, "amazing": 0.7, "fantastic": 0.7, "thank": 0.4,
    "thanks": 0.4, "appreciate": 0.5, "excited": 0.6, "happy": 0.5,
    "pleased": 0.5, "beautiful": 0.4, "best": 0.5, "awesome": 0.6,
    "smooth": 0.3, "easy": 0.3, "helpful": 0.4, "impressed": 0.5,
}

NEGATIVE_WORDS = {
    "worried": -0.5, "concerned": -0.5, "problem": -0.5, "issue": -0.4,
    "confused": -0.4, "frustrated": -0.6, "disappointed": -0.6,
    "unhappy": -0.6, "delay": -0.3, "delayed": -0.3, "cancel": -0.5,
    "cancelled": -0.5, "wrong": -0.4, "mistake": -0.4, "unclear": -0.3,
    "difficult": -0.3, "annoyed": -0.5, "upset": -0.6, "never": -0.3,
    "complaint": -0.6,
}

NEGATIONS = {"not", "n't", "no", "never", "without"}
INTENSIFIERS = {"very": 1.4, "really": 1.3, "extremely": 1.6, "so": 1.3}
