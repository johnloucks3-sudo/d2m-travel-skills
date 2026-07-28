"""
theme_tokens.py — Standardized Print-Safe CSS Variables & Styles
Dreams2Memories Travel, LLC | Thunderbird Wing
"""

# Canonical Dark Navy color definitions & variables
DARK_NAVY = "#07076b"
GOLD_ACCENT = "#c8a400"
ACCENT_GREEN = "#1a7a1a"
ACCENT_RED = "#8b0000"

# Print-Safe contrast hex colors for detail text on Dark Navy backgrounds
TEXT_HEADING = "#f7f3ea"      # Crisp off-white
TEXT_BODY = "#e8f1ff"         # Light blue-white
TEXT_MUTED = "#c8dcff"        # Slate blue-white for notes and sub-labels
TEXT_HIGHLIGHT = "#a8c8ff"    # Light sky blue for months/indicators

CSS_VARIABLES_TEMPLATE = f"""
:root {{
    --bg-primary: {DARK_NAVY};
    --border-gold: {GOLD_ACCENT};
    --color-green: {ACCENT_GREEN};
    --color-red: {ACCENT_RED};
    
    --text-heading: {TEXT_HEADING};
    --text-body: {TEXT_BODY};
    --text-muted: {TEXT_MUTED};
    --text-highlight: {TEXT_HIGHLIGHT};
}}
"""

def get_print_safe_stylesheet() -> str:
    """Return the global print-safe CSS rule block to inject into builders."""
    return f"""
    body {{
        font-family: Georgia, serif;
        background: {DARK_NAVY};
        color: {TEXT_HEADING};
        margin: 0;
        padding: 0;
    }}
    .day-num {{
        color: {GOLD_ACCENT};
    }}
    .day-dow {{
        color: {TEXT_MUTED};
    }}
    .date-mon {{
        color: {TEXT_HIGHLIGHT};
    }}
    .date-day {{
        color: {TEXT_BODY};
    }}
    .port-sub {{
        color: {TEXT_MUTED};
    }}
    .exc-lbl {{
        color: {GOLD_ACCENT};
    }}
    .exc-time {{
        color: {TEXT_BODY};
    }}
    .exc-note {{
        color: {TEXT_MUTED};
    }}
    """
